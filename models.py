# models.py - 数据模型：WarehouseMap, AGV, Order

import json
import random
import math
from enum import Enum, auto

from config import (
    GRID_COLS, GRID_ROWS, CELL_EMPTY, CELL_SHELF, CELL_PACK_STATION,
    CELL_CHARGE_STATION, AGV_COLORS, AGV_SPEED, AGV_BATTERY_MAX,
    AGV_BATTERY_DRAIN_MOVE, AGV_BATTERY_DRAIN_IDLE, AGV_BATTERY_CHARGE_RATE,
    AGV_BATTERY_LOW_THRESHOLD, AGV_PICK_TIME, ORDER_INTERVAL_MEAN,
    MAX_PENDING_ORDERS, DEFAULT_AGV_COUNT, GOODS_TYPES
)


# ==================== 枚举 ====================

class AGVState(Enum):
    IDLE = auto()
    MOVING_TO_PICK = auto()
    PICKING = auto()
    MOVING_TO_PACK = auto()
    MOVING_TO_CHARGE = auto()
    CHARGING = auto()
    WAITING = auto()
    DEADLOCK_RECOVERY = auto()
    RETREAT = auto()  # 避让：从关键位置移开

    def is_busy(self):
        return self != AGVState.IDLE


class OrderState(Enum):
    PENDING = auto()
    ASSIGNED = auto()
    PICKING = auto()
    DELIVERING = auto()
    COMPLETED = auto()


# ==================== 仓库地图 ====================

class WarehouseMap:
    def __init__(self):
        self.cols = GRID_COLS
        self.rows = GRID_ROWS
        self.grid = [[CELL_EMPTY] * self.cols for _ in range(self.rows)]
        self.pack_stations = []   # [(x, y), ...]
        self.charge_stations = [] # [(x, y), ...]
        self.shelf_positions = [] # [(x, y), ...]
        self.pick_points = []     # [(x, y), ...] 货架旁可取货的通道格
        self.heatmap = [[0] * self.cols for _ in range(self.rows)]
        # 货架货物映射：(x,y) -> goods_type_index
        self.shelf_goods = {}
        # 取货点货物映射：(x,y) -> goods_type_index（取货点旁边的货架存放的货物）
        self.pick_point_goods = {}

    def load_from_json(self, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.cols = data.get('grid_cols', GRID_COLS)
        self.rows = data.get('grid_rows', GRID_ROWS)
        self.grid = [[CELL_EMPTY] * self.cols for _ in range(self.rows)]

        # 放置货架
        for region in data.get('shelf_regions', []):
            x, y, w, h = region['x'], region['y'], region['w'], region['h']
            for r in range(y, min(y + h, self.rows)):
                for c in range(x, min(x + w, self.cols)):
                    self.grid[r][c] = CELL_SHELF
                    self.shelf_positions.append((c, r))

        # 放置打包台
        for st in data.get('pack_stations', []):
            x, y = st['x'], st['y']
            if 0 <= x < self.cols and 0 <= y < self.rows:
                self.grid[y][x] = CELL_PACK_STATION
                self.pack_stations.append((x, y))

        # 放置充电站
        for st in data.get('charge_stations', []):
            x, y = st['x'], st['y']
            if 0 <= x < self.cols and 0 <= y < self.rows:
                self.grid[y][x] = CELL_CHARGE_STATION
                self.charge_stations.append((x, y))

        # 计算取货点：货架旁的空地
        self._compute_pick_points()

    def _compute_pick_points(self):
        """找出所有紧邻货架的通道格作为取货点，并分配货物类型"""
        self.pick_points = []
        self.pick_point_goods = {}
        seen = set()
        # 按行分组货架，每行分配一种货物类型
        shelf_rows = sorted(set(y for x, y in self.shelf_positions))
        row_goods = {}
        for i, row in enumerate(shelf_rows):
            row_goods[row] = i % len(GOODS_TYPES)

        for (sx, sy) in self.shelf_positions:
            for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                nx, ny = sx + dx, sy + dy
                if 0 <= nx < self.cols and 0 <= ny < self.rows:
                    if self.grid[ny][nx] == CELL_EMPTY and (nx, ny) not in seen:
                        self.pick_points.append((nx, ny))
                        seen.add((nx, ny))
                        # 该取货点的货物类型取决于相邻货架所在行
                        self.pick_point_goods[(nx, ny)] = row_goods.get(sy, 0)

        # 同时给每个货架格子分配货物类型
        self.shelf_goods = {}
        for (sx, sy) in self.shelf_positions:
            self.shelf_goods[(sx, sy)] = row_goods.get(sy, 0)

    def is_walkable(self, x, y):
        if 0 <= x < self.cols and 0 <= y < self.rows:
            return self.grid[y][x] != CELL_SHELF
        return False

    def get_walkable_neighbors(self, x, y):
        neighbors = []
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            nx, ny = x + dx, y + dy
            if self.is_walkable(nx, ny):
                neighbors.append((nx, ny))
        return neighbors

    def add_obstacle(self, x, y):
        if 0 <= x < self.cols and 0 <= y < self.rows:
            if self.grid[y][x] == CELL_EMPTY:
                self.grid[y][x] = CELL_SHELF
                self.shelf_positions.append((x, y))
                self._compute_pick_points()
                return True
        return False

    def remove_obstacle(self, x, y):
        if 0 <= x < self.cols and 0 <= y < self.rows:
            if self.grid[y][x] == CELL_SHELF:
                self.grid[y][x] = CELL_EMPTY
                if (x, y) in self.shelf_positions:
                    self.shelf_positions.remove((x, y))
                self._compute_pick_points()
                return True
        return False

    def update_heatmap(self, x, y):
        if 0 <= x < self.cols and 0 <= y < self.rows:
            self.heatmap[y][x] += 1

    def get_random_pick_point(self):
        if self.pick_points:
            return random.choice(self.pick_points)
        return None

    def get_nearest_pack_station(self, x, y):
        if not self.pack_stations:
            return None
        return min(self.pack_stations, key=lambda p: abs(p[0] - x) + abs(p[1] - y))

    def get_nearest_charge_station(self, x, y):
        if not self.charge_stations:
            return None
        return min(self.charge_stations, key=lambda p: abs(p[0] - x) + abs(p[1] - y))


# ==================== AGV ====================

class AGV:
    _next_id = 0

    def __init__(self, x, y, agv_id=None):
        if agv_id is not None:
            self.id = agv_id
        else:
            self.id = AGV._next_id
            AGV._next_id += 1

        self.grid_x = x
        self.grid_y = y
        self.render_x = float(x)
        self.render_y = float(y)
        self.state = AGVState.IDLE
        self.prev_state = AGVState.IDLE
        self.path = []           # [(x, y), ...] 剩余路径
        self.path_with_time = [] # [(x, y, t), ...] 带时间的路径（用于预留表）
        self.current_order = None
        self.battery = AGV_BATTERY_MAX
        self.speed = AGV_SPEED
        self.color = AGV_COLORS[self.id % len(AGV_COLORS)]
        self.priority = self.id  # 优先级，数值越小越高
        self.wait_timer = 0.0
        self.pick_timer = 0.0
        self.move_progress = 0.0  # 0~1 当前格到下一格的进度
        self.blocked_timer = 0.0  # 被阻挡的累计时间
        self.total_move_time = 0.0
        self.total_idle_time = 0.0
        self.total_work_time = 0.0
        self.orders_completed = 0
        self.wait_count = 0
        self.deadlock_count = 0

    @property
    def pos(self):
        return (self.grid_x, self.grid_y)

    @pos.setter
    def pos(self, value):
        self.grid_x, self.grid_y = value

    def is_idle(self):
        return self.state == AGVState.IDLE

    def is_available(self):
        """是否可分配新任务"""
        return self.state == AGVState.IDLE and self.battery > AGV_BATTERY_LOW_THRESHOLD

    def needs_charging(self):
        return self.battery <= AGV_BATTERY_LOW_THRESHOLD

    def assign_order(self, order):
        self.current_order = order
        order.assign(self.id)
        self.state = AGVState.MOVING_TO_PICK

    def set_path(self, path, path_with_time=None):
        self.path = path
        self.path_with_time = path_with_time or []
        self.move_progress = 0.0

    def clear_path(self):
        self.path = []
        self.path_with_time = []
        self.move_progress = 0.0

    def update(self, dt, warehouse_map, other_agvs=None):
        """更新AGV状态，返回是否移动了"""
        self.total_work_time += dt
        moved = False

        if other_agvs is None:
            other_agvs = []

        if self.state == AGVState.IDLE:
            self.total_idle_time += dt
            self.battery -= AGV_BATTERY_DRAIN_IDLE * dt * 60
            return False

        elif self.state == AGVState.MOVING_TO_PICK or self.state == AGVState.MOVING_TO_PACK or self.state == AGVState.MOVING_TO_CHARGE or self.state == AGVState.RETREAT:
            moved = self._move_along_path(dt, warehouse_map, other_agvs)

        elif self.state == AGVState.PICKING:
            self.pick_timer -= dt
            if self.pick_timer <= 0:
                if self.current_order:
                    self.current_order.start_delivering()
                self.state = AGVState.MOVING_TO_PACK

        elif self.state == AGVState.CHARGING:
            self.battery += AGV_BATTERY_CHARGE_RATE * dt * 60
            if self.battery >= AGV_BATTERY_MAX:
                self.battery = AGV_BATTERY_MAX
                self.state = AGVState.IDLE

        elif self.state == AGVState.WAITING:
            self.wait_timer -= dt
            self.total_idle_time += dt
            if self.wait_timer <= 0:
                self.state = self.prev_state if self.prev_state != AGVState.WAITING else AGVState.IDLE

        elif self.state == AGVState.DEADLOCK_RECOVERY:
            moved = self._move_along_path(dt, warehouse_map, other_agvs)

        self.battery = max(0, self.battery)
        return moved

    def _move_along_path(self, dt, warehouse_map, other_agvs=None):
        """沿路径移动，返回是否移动了。other_agvs用于实时碰撞检测"""
        if other_agvs is None:
            other_agvs = []

        if not self.path:
            # 到达目的地
            if self.state == AGVState.MOVING_TO_PICK and self.current_order:
                self.state = AGVState.PICKING
                self.pick_timer = AGV_PICK_TIME
                self.current_order.start_picking()
            elif self.state == AGVState.MOVING_TO_PACK and self.current_order:
                self.current_order.complete()
                self.orders_completed += 1
                self.current_order = None
                self.state = AGVState.IDLE
            elif self.state == AGVState.MOVING_TO_CHARGE:
                self.state = AGVState.CHARGING
            elif self.state == AGVState.RETREAT:
                # 避让完成，回到IDLE
                self.state = AGVState.IDLE
            return False

        # 实时碰撞检测：检查下一格是否被其他AGV占据
        next_pos = self.path[0]
        blocked = False
        for other in other_agvs:
            if other.id == self.id:
                continue
            # 其他AGV当前占据下一格
            if other.grid_x == next_pos[0] and other.grid_y == next_pos[1]:
                # 如果自己是避让状态，其他IDLE AGV应该让路
                if self.state == AGVState.RETREAT and other.state == AGVState.IDLE:
                    continue  # IDLE AGV会被_move_idle_from_critical_positions移走
                blocked = True
                break
            # 对向冲突：其他AGV的下一格是我当前位置，且我的下一格是它当前位置
            if other.path:
                other_next = other.path[0]
                if (other_next[0] == self.grid_x and other_next[1] == self.grid_y and
                    next_pos[0] == other.grid_x and next_pos[1] == other.grid_y):
                    # 优先级低的让路；避让状态优先级最高
                    my_prio = -1 if self.state == AGVState.RETREAT else self.priority
                    other_prio = -1 if other.state == AGVState.RETREAT else other.priority
                    if my_prio > other_prio:
                        blocked = True
                        break

        if blocked:
            # 被阻挡，原地等待，累加阻挡计时
            self.blocked_timer += dt
            self.total_idle_time += dt
            return False

        # 成功前进，重置阻挡计时
        self.blocked_timer = 0.0

        # 计算移动进度
        cells_per_second = self.speed
        self.move_progress += cells_per_second * dt

        if self.move_progress >= 1.0:
            # 到达下一个路径点
            self.grid_x, self.grid_y = next_pos
            self.render_x = float(self.grid_x)
            self.render_y = float(self.grid_y)
            self.path.pop(0)
            if self.path_with_time:
                self.path_with_time.pop(0)
            self.move_progress = 0.0
            self.battery -= AGV_BATTERY_DRAIN_MOVE
            self.total_move_time += dt
            warehouse_map.update_heatmap(self.grid_x, self.grid_y)
            return True
        else:
            # 平滑插值
            if self.path:
                nx, ny = self.path[0]
                self.render_x = self.grid_x + (nx - self.grid_x) * self.move_progress
                self.render_y = self.grid_y + (ny - self.grid_y) * self.move_progress
            return False

    def start_charging(self, charge_pos):
        """前往充电站充电"""
        self.grid_x, self.grid_y = charge_pos
        self.render_x = float(self.grid_x)
        self.render_y = float(self.grid_y)
        self.state = AGVState.CHARGING
        self.clear_path()

    def start_waiting(self, duration=0.5):
        """进入等待状态"""
        if self.state != AGVState.WAITING:
            self.prev_state = self.state
        self.state = AGVState.WAITING
        self.wait_timer = duration
        self.wait_count += 1


# ==================== 订单 ====================

class Order:
    _next_id = 0

    def __init__(self, pick_x, pick_y, pack_x, pack_y, goods_type=0):
        self.id = Order._next_id
        Order._next_id += 1
        self.pick_x = pick_x
        self.pick_y = pick_y
        self.pack_x = pack_x
        self.pack_y = pack_y
        self.goods_type = goods_type  # 货物类型索引
        self.state = OrderState.PENDING
        self.assigned_agv = None
        self.create_time = 0.0
        self.assign_time = None
        self.pick_start_time = None
        self.deliver_start_time = None
        self.complete_time = None

    @property
    def pick_pos(self):
        return (self.pick_x, self.pick_y)

    @property
    def pack_pos(self):
        return (self.pack_x, self.pack_y)

    @property
    def wait_time(self):
        if self.assign_time is not None:
            return self.assign_time - self.create_time
        return 0.0

    @property
    def total_time(self):
        if self.complete_time is not None:
            return self.complete_time - self.create_time
        return 0.0

    def assign(self, agv_id):
        self.assigned_agv = agv_id
        self.state = OrderState.ASSIGNED

    def start_picking(self):
        self.state = OrderState.PICKING

    def start_delivering(self):
        self.state = OrderState.DELIVERING

    def complete(self):
        self.state = OrderState.COMPLETED


# ==================== 订单生成器 ====================

class OrderGenerator:
    def __init__(self, warehouse_map, mean_interval=ORDER_INTERVAL_MEAN):
        self.warehouse_map = warehouse_map
        self.mean_interval = mean_interval
        self.time_since_last = 0.0
        self.next_interval = self._generate_interval()

    def _generate_interval(self):
        """泊松分布生成订单间隔"""
        return random.expovariate(1.0 / self.mean_interval)

    def update(self, dt, sim_time):
        """更新订单生成器，返回新订单列表"""
        new_orders = []
        self.time_since_last += dt

        while self.time_since_last >= self.next_interval:
            self.time_since_last -= self.next_interval
            self.next_interval = self._generate_interval()

            pick_point = self.warehouse_map.get_random_pick_point()
            if pick_point:
                pack_station = self.warehouse_map.get_nearest_pack_station(*pick_point)
                if pack_station:
                    # 获取该取货点的货物类型
                    goods_type = self.warehouse_map.pick_point_goods.get(pick_point, 0)
                    order = Order(pick_point[0], pick_point[1],
                                  pack_station[0], pack_station[1], goods_type)
                    order.create_time = sim_time
                    new_orders.append(order)

        return new_orders

    def create_manual_order(self, pick_x, pick_y, sim_time):
        """手动创建紧急订单"""
        pack_station = self.warehouse_map.get_nearest_pack_station(pick_x, pick_y)
        if pack_station:
            goods_type = self.warehouse_map.pick_point_goods.get((pick_x, pick_y), 0)
            order = Order(pick_x, pick_y, pack_station[0], pack_station[1], goods_type)
            order.create_time = sim_time
            return order
        return None
