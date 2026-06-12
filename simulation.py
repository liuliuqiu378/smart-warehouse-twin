# simulation.py - 仿真引擎核心

import json
import random
import time as time_module
from collections import deque

from config import (
    DEFAULT_AGV_COUNT, STRATEGY_SIMPLE, STRATEGY_ADVANCED,
    AGV_BATTERY_LOW_THRESHOLD, SPEED_MULTIPLIERS, MAX_PENDING_ORDERS
)
from models import WarehouseMap, AGV, AGVState, Order, OrderGenerator, OrderState
from algorithms import Scheduler, compute_congestion_map


class SimulationStats:
    """仿真统计数据"""

    def __init__(self):
        self.total_orders = 0
        self.completed_orders = 0
        self.pending_orders = 0
        self.avg_wait_time = 0.0
        self.avg_complete_time = 0.0
        self.agv_utilization = 0.0
        self.conflict_count = 0
        self.deadlock_count = 0
        self.throughput_history = deque(maxlen=200)  # 吞吐量历史
        self.completed_in_window = 0
        self.window_start = 0.0
        self.window_duration = 5.0  # 统计窗口（秒）

    @property
    def completion_rate(self):
        if self.total_orders == 0:
            return 0.0
        return self.completed_orders / self.total_orders

    @property
    def current_throughput(self):
        if self.throughput_history:
            return self.throughput_history[-1]
        return 0.0

    def update(self, sim_time, agvs, orders):
        """更新统计数据"""
        self.total_orders = len(orders)
        self.completed_orders = sum(1 for o in orders if o.state == OrderState.COMPLETED)
        self.pending_orders = sum(1 for o in orders if o.state == OrderState.PENDING)

        # 平均等待时间
        completed = [o for o in orders if o.state == OrderState.COMPLETED]
        if completed:
            self.avg_wait_time = sum(o.wait_time for o in completed) / len(completed)
            self.avg_complete_time = sum(o.total_time for o in completed) / len(completed)

        # AGV利用率（非空闲时间占比）
        if agvs:
            total_time = sum(a.total_work_time for a in agvs)
            idle_time = sum(a.total_idle_time for a in agvs)
            if total_time > 0:
                self.agv_utilization = 1.0 - (idle_time / total_time)

        # 吞吐量
        if sim_time - self.window_start >= self.window_duration:
            throughput = self.completed_in_window / self.window_duration
            self.throughput_history.append(throughput)
            self.completed_in_window = 0
            self.window_start = sim_time

    def record_completion(self):
        self.completed_in_window += 1


class SimulationEngine:
    """仿真引擎"""

    def __init__(self, map_config_path='map_config.json', agv_count=DEFAULT_AGV_COUNT,
                 strategy=STRATEGY_ADVANCED):
        self.warehouse_map = WarehouseMap()
        self.warehouse_map.load_from_json(map_config_path)
        self.map_config_path = map_config_path

        self.agvs = []
        self.orders = []
        self.order_generator = OrderGenerator(self.warehouse_map)
        self.scheduler = Scheduler(strategy)
        self.stats = SimulationStats()
        self.strategy = strategy

        # 仿真状态
        self.sim_time = 0.0
        self.speed_index = 2  # 默认1x速度
        self.paused = False
        self.running = True

        # 显示选项
        self.show_paths = True
        self.show_heatmap = False
        self.show_timewindow = False

        # 初始化AGV
        self._init_agvs(agv_count)

        # 拥塞图
        self.congestion_map = None

    def _init_agvs(self, count):
        """初始化AGV"""
        with open(self.map_config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        start_positions = data.get('agv_start_positions', [])

        for i in range(count):
            if i < len(start_positions):
                pos = start_positions[i]
                agv = AGV(pos['x'], pos['y'], agv_id=i)
            else:
                # 随机放置在空地上
                while True:
                    x = random.randint(0, self.warehouse_map.cols - 1)
                    y = random.randint(0, self.warehouse_map.rows - 1)
                    if self.warehouse_map.is_walkable(x, y):
                        agv = AGV(x, y, agv_id=i)
                        break

            self.agvs.append(agv)

        AGV._next_id = count

    @property
    def speed_multiplier(self):
        return SPEED_MULTIPLIERS[self.speed_index]

    def toggle_pause(self):
        self.paused = not self.paused

    def speed_up(self):
        if self.speed_index < len(SPEED_MULTIPLIERS) - 1:
            self.speed_index += 1

    def speed_down(self):
        if self.speed_index > 0:
            self.speed_index -= 1

    def switch_strategy(self):
        """切换调度策略"""
        if self.strategy == STRATEGY_SIMPLE:
            self.strategy = STRATEGY_ADVANCED
        else:
            self.strategy = STRATEGY_SIMPLE
        self.scheduler.strategy = self.strategy
        self.scheduler.reset_reservations()

    def tick(self, dt):
        """推进一个tick"""
        if self.paused:
            return

        actual_dt = dt * self.speed_multiplier
        self.sim_time += actual_dt

        # 1. 生成新订单
        new_orders = self.order_generator.update(actual_dt, self.sim_time)
        for order in new_orders:
            if len([o for o in self.orders if o.state == OrderState.PENDING]) < MAX_PENDING_ORDERS:
                self.orders.append(order)

        # 2. 检查低电量AGV，触发充电
        self._handle_low_battery()

        # 3. 任务分配
        self._assign_orders()

        # 4. 计算拥塞图
        if self.strategy == STRATEGY_ADVANCED:
            self.congestion_map = compute_congestion_map(self.warehouse_map, self.agvs)

        # 5. 路径规划（为需要路径的AGV规划）
        self._plan_paths()

        # 6. 冲突检测与解决
        self._resolve_conflicts()

        # 7. 死锁检测与恢复
        self._resolve_deadlocks()

        # 8. 对向堵死检测：被挡太久的AGV重规划路径
        self._reroute_blocked_agvs()

        # 9. IDLE AGV让开关键位置（打包台/充电站/取货点）
        self._move_idle_from_critical_positions()

        # 10. 更新AGV位置（传入其他AGV列表用于实时碰撞检测）
        for agv in self.agvs:
            prev_order = agv.current_order
            other_agvs = [a for a in self.agvs if a.id != agv.id]
            moved = agv.update(actual_dt, self.warehouse_map, other_agvs)
            # 检查订单完成（AGV完成订单后current_order变为None）
            if prev_order is not None and agv.current_order is None and agv.is_idle():
                prev_order.complete_time = self.sim_time
                self.stats.record_completion()

        # 9. 更新统计
        self._update_stats()

    def _handle_low_battery(self):
        """处理低电量AGV"""
        for agv in self.agvs:
            if agv.needs_charging() and agv.state not in (AGVState.CHARGING, AGVState.MOVING_TO_CHARGE):
                # 取消当前任务
                if agv.current_order:
                    agv.current_order.state = OrderState.PENDING
                    agv.current_order.assigned_agv = None
                    agv.current_order = None

                self.scheduler.clear_agv_reservations(agv.id)
                agv.clear_path()

                # 前往充电站
                charge_pos = self.warehouse_map.get_nearest_charge_station(agv.grid_x, agv.grid_y)
                if charge_pos:
                    agv.state = AGVState.MOVING_TO_CHARGE
                    # 充电站目标：找旁边的空格
                    goal = self._find_adjacent_free_cell(charge_pos, agv)
                    if goal is None:
                        goal = charge_pos
                    success = self.scheduler.plan_path(
                        agv, goal, self.warehouse_map,
                        int(self.sim_time), self.congestion_map, self.agvs
                    )
                    if not success:
                        # 无法规划路径，直接传送（紧急情况）
                        agv.start_charging(charge_pos)

    def _assign_orders(self):
        """分配订单给空闲AGV"""
        available_agvs = [a for a in self.agvs if a.is_available()]
        pending_orders = [o for o in self.orders if o.state == OrderState.PENDING]

        if not available_agvs or not pending_orders:
            return

        assignments = self.scheduler.assign_orders(
            available_agvs, pending_orders, self.warehouse_map, self.sim_time
        )

        for agv, order in assignments:
            agv.assign_order(order)
            order.assign_time = self.sim_time

    def _plan_paths(self):
        """为需要路径的AGV规划路径"""
        for agv in self.agvs:
            if not agv.path:
                if agv.current_order and agv.state == AGVState.MOVING_TO_PICK:
                    goal = (agv.current_order.pick_x, agv.current_order.pick_y)
                    self.scheduler.plan_path(
                        agv, goal, self.warehouse_map,
                        int(self.sim_time), self.congestion_map, self.agvs
                    )
                elif agv.current_order and agv.state == AGVState.MOVING_TO_PACK:
                    # 打包台目标：找打包台旁边的空格，避免多车堵在P上
                    pack_pos = (agv.current_order.pack_x, agv.current_order.pack_y)
                    goal = self._find_adjacent_free_cell(pack_pos, agv)
                    if goal is None:
                        goal = pack_pos  # 回退到原目标
                    self.scheduler.plan_path(
                        agv, goal, self.warehouse_map,
                        int(self.sim_time), self.congestion_map, self.agvs
                    )
                elif agv.state == AGVState.MOVING_TO_CHARGE:
                    charge_pos = self.warehouse_map.get_nearest_charge_station(agv.grid_x, agv.grid_y)
                    if charge_pos:
                        # 充电站目标：找充电站旁边的空格
                        goal = self._find_adjacent_free_cell(charge_pos, agv)
                        if goal is None:
                            goal = charge_pos
                        self.scheduler.plan_path(
                            agv, goal, self.warehouse_map,
                            int(self.sim_time), self.congestion_map, self.agvs
                        )

    def _find_adjacent_free_cell(self, center_pos, requesting_agv):
        """找一个关键位置旁边的空格（不被其他AGV占据），用于AGV停靠"""
        occupied = {(a.grid_x, a.grid_y) for a in self.agvs if a.id != requesting_agv.id}
        cx, cy = center_pos
        # 优先选择不被占据的相邻格
        for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
            nx, ny = cx + dx, cy + dy
            if self.warehouse_map.is_walkable(nx, ny) and (nx, ny) not in occupied:
                return (nx, ny)
        # 回退：选择任何可行走的相邻格
        for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
            nx, ny = cx + dx, cy + dy
            if self.warehouse_map.is_walkable(nx, ny):
                return (nx, ny)
        return None

    def _resolve_conflicts(self):
        """检测并解决冲突"""
        conflict_count = self.scheduler.detect_and_resolve_conflicts(
            self.agvs, self.warehouse_map
        )
        self.stats.conflict_count = self.scheduler.conflict_count

    def _reroute_blocked_agvs(self):
        """对向堵死检测：被挡超过阈值的AGV重规划路径（绕路或后退让行）"""
        BLOCKED_THRESHOLD = 1.5  # 被挡1.5秒触发重规划

        for agv in self.agvs:
            if agv.blocked_timer < BLOCKED_THRESHOLD:
                continue
            if not agv.path:
                continue
            if agv.state in (AGVState.IDLE, AGVState.CHARGING, AGVState.PICKING, AGVState.RETREAT):
                continue

            # 找出挡路的AGV
            next_pos = agv.path[0]
            blocker = None
            for other in self.agvs:
                if other.id == agv.id:
                    continue
                if other.grid_x == next_pos[0] and other.grid_y == next_pos[1]:
                    blocker = other
                    break

            if blocker is None:
                # 没有直接挡路者，可能是对向冲突，直接重规划
                agv.blocked_timer = 0.0
                agv.clear_path()
                self.scheduler.clear_agv_reservations(agv.id)
                continue

            # 优先级低的AGV让路：后退或绕行
            if agv.priority >= blocker.priority:
                # 自己优先级低，需要让路
                agv.deadlock_count += 1
                agv.blocked_timer = 0.0
                agv.clear_path()
                self.scheduler.clear_agv_reservations(agv.id)

                # 尝试后退：找当前位置旁边一个不被占据的空格
                retreat = self._find_retreat_for_reroute(agv, blocker)
                if retreat:
                    from algorithms import astar_simple
                    occupied = {(a.grid_x, a.grid_y) for a in self.agvs if a.id != agv.id}
                    # 临时把挡路者位置从occupied移除，让A*能规划绕行路径
                    occupied.discard((blocker.grid_x, blocker.grid_y))
                    path = astar_simple(self.warehouse_map, agv.pos, retreat, occupied)
                    if path and len(path) > 1:
                        agv.set_path(path[1:])
                        agv.state = AGVState.RETREAT
                    else:
                        # 无法后退，等待
                        agv.state = AGVState.IDLE
                        if agv.current_order:
                            agv.current_order.state = OrderState.PENDING
                            agv.current_order.assigned_agv = None
                            agv.current_order = None
                else:
                    # 无处可退，放弃任务
                    agv.state = AGVState.IDLE
                    if agv.current_order:
                        agv.current_order.state = OrderState.PENDING
                        agv.current_order.assigned_agv = None
                        agv.current_order = None
            else:
                # 自己优先级高，对方应该让路，但对方没让
                # 强制重规划自己的路径绕过去
                agv.blocked_timer = 0.0
                agv.clear_path()
                self.scheduler.clear_agv_reservations(agv.id)

                # 确定最终目标
                if agv.current_order:
                    if agv.state == AGVState.MOVING_TO_PICK:
                        goal = (agv.current_order.pick_x, agv.current_order.pick_y)
                    elif agv.state == AGVState.MOVING_TO_PACK:
                        pack_pos = (agv.current_order.pack_x, agv.current_order.pack_y)
                        goal = self._find_adjacent_free_cell(pack_pos, agv) or pack_pos
                    else:
                        goal = agv.pos
                else:
                    goal = None

                if goal:
                    from algorithms import astar_simple
                    occupied = {(a.grid_x, a.grid_y) for a in self.agvs if a.id != agv.id}
                    path = astar_simple(self.warehouse_map, agv.pos, goal, occupied)
                    if path and len(path) > 1:
                        agv.set_path(path[1:])

    def _find_retreat_for_reroute(self, agv, blocker):
        """为被挡AGV找一个后退位置（远离挡路者的方向）"""
        occupied = {(a.grid_x, a.grid_y) for a in self.agvs}

        # 计算远离挡路者的方向
        dx = agv.grid_x - blocker.grid_x
        dy = agv.grid_y - blocker.grid_y

        # 优先尝试远离挡路者的方向
        preferred_dirs = []
        if dx != 0:
            preferred_dirs.append((1 if dx > 0 else -1, 0))
        if dy != 0:
            preferred_dirs.append((0, 1 if dy > 0 else -1))
        # 也加上垂直方向
        if dx != 0:
            preferred_dirs.append((0, 1))
            preferred_dirs.append((0, -1))
        if dy != 0:
            preferred_dirs.append((1, 0))
            preferred_dirs.append((-1, 0))

        for ddx, ddy in preferred_dirs:
            nx, ny = agv.grid_x + ddx, agv.grid_y + ddy
            if (self.warehouse_map.is_walkable(nx, ny) and
                (nx, ny) not in occupied):
                return (nx, ny)

        # 回退：BFS找最近的空地
        from collections import deque as bfs_deque
        queue = bfs_deque([(agv.grid_x, agv.grid_y, 0)])
        visited = {(agv.grid_x, agv.grid_y)}
        while queue:
            x, y, dist = queue.popleft()
            if dist > 8:
                break
            for nx, ny in self.warehouse_map.get_walkable_neighbors(x, y):
                if (nx, ny) in visited:
                    continue
                visited.add((nx, ny))
                if (nx, ny) not in occupied:
                    return (nx, ny)
                queue.append((nx, ny, dist + 1))

        return None

    def _resolve_deadlocks(self):
        """检测并解决死锁"""
        deadlock_count = self.scheduler.detect_and_resolve_deadlock(
            self.agvs, self.warehouse_map
        )
        self.stats.deadlock_count = self.scheduler.deadlock_count

    def _move_idle_from_critical_positions(self):
        """IDLE的AGV如果站在关键位置（打包台/充电站/取货点），自动让开"""
        # 关键位置集合
        critical_positions = set()
        for px, py in self.warehouse_map.pack_stations:
            critical_positions.add((px, py))
        for cx, cy in self.warehouse_map.charge_stations:
            critical_positions.add((cx, cy))

        # 检查是否有其他AGV正在前往某些位置
        needed_positions = set()
        for agv in self.agvs:
            if agv.path:
                target = agv.path[-1] if agv.path else None
                if target:
                    needed_positions.add(target)

        for agv in self.agvs:
            if agv.state != AGVState.IDLE:
                continue
            pos = (agv.grid_x, agv.grid_y)
            # IDLE AGV站在打包台/充电站，或站在其他AGV需要前往的位置
            if pos in critical_positions or pos in needed_positions:
                # 找一个附近的空地移过去
                retreat = self._find_retreat_position(agv)
                if retreat and retreat != pos:
                    # 直接用A*规划路径，设置RETREAT状态
                    from algorithms import astar_simple
                    occupied = {(a.grid_x, a.grid_y) for a in self.agvs if a.id != agv.id}
                    path = astar_simple(self.warehouse_map, pos, retreat, occupied)
                    if path and len(path) > 1:
                        agv.state = AGVState.RETREAT
                        agv.set_path(path[1:])

    def _find_retreat_position(self, agv):
        """为IDLE AGV找一个附近的空地（不在打包台/充电站上、不被其他AGV占据）"""
        occupied = {(a.grid_x, a.grid_y) for a in self.agvs}

        critical_positions = set()
        for px, py in self.warehouse_map.pack_stations:
            critical_positions.add((px, py))
        for cx, cy in self.warehouse_map.charge_stations:
            critical_positions.add((cx, cy))

        # BFS找最近的非关键空地
        from collections import deque as bfs_deque
        queue = bfs_deque([(agv.grid_x, agv.grid_y, 0)])
        visited = {(agv.grid_x, agv.grid_y)}

        while queue:
            x, y, dist = queue.popleft()
            if dist > 15:
                break

            for nx, ny in self.warehouse_map.get_walkable_neighbors(x, y):
                if (nx, ny) in visited:
                    continue
                visited.add((nx, ny))

                if (nx, ny) not in critical_positions and (nx, ny) not in occupied:
                    return (nx, ny)

                queue.append((nx, ny, dist + 1))

        return None

    def _update_stats(self):
        """更新统计数据"""
        self.stats.update(self.sim_time, self.agvs, self.orders)

    def add_obstacle(self, grid_x, grid_y):
        """添加临时障碍"""
        return self.warehouse_map.add_obstacle(grid_x, grid_y)

    def remove_obstacle(self, grid_x, grid_y):
        """移除障碍"""
        return self.warehouse_map.remove_obstacle(grid_x, grid_y)

    def add_manual_order(self, grid_x, grid_y):
        """在指定位置创建紧急订单"""
        if self.warehouse_map.is_walkable(grid_x, grid_y):
            order = self.order_generator.create_manual_order(grid_x, grid_y, self.sim_time)
            if order:
                self.orders.append(order)
                return order
        return None

    def get_agv_at(self, grid_x, grid_y):
        """获取指定位置的AGV"""
        for agv in self.agvs:
            if agv.grid_x == grid_x and agv.grid_y == grid_y:
                return agv
        return None

    def move_agv_to(self, agv, grid_x, grid_y):
        """拖拽AGV到新位置（调试用）"""
        if self.warehouse_map.is_walkable(grid_x, grid_y):
            self.scheduler.clear_agv_reservations(agv.id)
            agv.clear_path()
            agv.grid_x = grid_x
            agv.grid_y = grid_y
            agv.render_x = float(grid_x)
            agv.render_y = float(grid_y)
            return True
        return False
