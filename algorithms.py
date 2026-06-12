# algorithms.py - 核心算法：A*路径规划、匈牙利分配、冲突检测、死锁恢复

import heapq
import random
import time
from collections import defaultdict

from models import AGVState, OrderState
from config import (
    RESERVATION_HORIZON, PATH_MAX_LENGTH, STRATEGY_SIMPLE, STRATEGY_ADVANCED
)


# ==================== 预留表 ====================

class ReservationTable:
    """时空预留表，记录每个(格,时间)被哪辆AGV占用"""

    def __init__(self):
        self.reservations = {}  # (x, y, t) -> agv_id

    def reserve(self, x, y, t, agv_id):
        self.reservations[(x, y, t)] = agv_id

    def is_reserved(self, x, y, t, exclude_agv=None):
        key = (x, y, t)
        if key in self.reservations:
            if exclude_agv is not None and self.reservations[key] == exclude_agv:
                return False
            return True
        return False

    def clear_agv(self, agv_id):
        """清除某AGV的所有预留"""
        to_remove = [k for k, v in self.reservations.items() if v == agv_id]
        for k in to_remove:
            del self.reservations[k]

    def clear_all(self):
        self.reservations.clear()

    def reserve_path(self, path_with_time, agv_id):
        """预留整条路径"""
        for x, y, t in path_with_time:
            if t < RESERVATION_HORIZON:
                self.reserve(x, y, t, agv_id)

    def get_agv_at(self, x, y, t):
        """获取某时刻某位置的AGV ID"""
        return self.reservations.get((x, y, t), None)


# ==================== A* 路径规划 ====================

def heuristic(a, b):
    """曼哈顿距离启发函数"""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def astar_simple(warehouse_map, start, goal, occupied_positions=None):
    """简单A*，避开其他AGV当前位置"""
    if start == goal:
        return [start]

    if occupied_positions is None:
        occupied_positions = set()

    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score = {start: 0}

    while open_set:
        _, current = heapq.heappop(open_set)

        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            path.reverse()
            return path

        for nx, ny in warehouse_map.get_walkable_neighbors(*current):
            neighbor = (nx, ny)
            # 跳过被其他AGV占据的位置（目标点除外）
            if neighbor in occupied_positions and neighbor != goal:
                continue
            tentative_g = g_score[current] + 1

            if tentative_g < g_score.get(neighbor, float('inf')):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f = tentative_g + heuristic(neighbor, goal)
                heapq.heappush(open_set, (f, neighbor))

    return None  # 无路径


def astar_with_time_windows(warehouse_map, start, goal, reservation_table,
                             agv_id, start_time=0, congestion_map=None):
    """带时间窗的A*，考虑其他AGV的预留和拥塞"""
    if start == goal:
        return [(start[0], start[1], start_time)]

    # 状态: (x, y, t)
    open_set = []
    start_state = (start[0], start[1], start_time)
    heapq.heappush(open_set, (0, start_state))
    came_from = {}
    g_score = {start_state: 0}
    max_t = start_time + RESERVATION_HORIZON

    while open_set:
        _, current = heapq.heappop(open_set)
        cx, cy, ct = current

        if (cx, cy) == goal:
            # 重建路径
            path = []
            state = current
            while state in came_from:
                path.append(state)
                state = came_from[state]
            path.append(start_state)
            path.reverse()
            return path

        if ct >= max_t:
            continue

        # 生成邻居：4方向移动 + 原地等待
        next_time = ct + 1
        candidates = []

        for nx, ny in warehouse_map.get_walkable_neighbors(cx, cy):
            candidates.append((nx, ny))

        candidates.append((cx, cy))  # 等待

        for nx, ny in candidates:
            # 检查预留冲突
            if reservation_table.is_reserved(nx, ny, next_time, exclude_agv=agv_id):
                continue

            # 检查边冲突（两车对向交换位置）
            if (nx, ny) != (cx, cy):  # 不是等待
                if reservation_table.is_reserved(cx, cy, next_time, exclude_agv=agv_id):
                    # 当前位置下一时刻被占用，不能离开（对向冲突）
                    pass  # 允许离开，因为对向车会进入当前位置
                # 检查对向移动冲突
                other_agv = reservation_table.get_agv_at(nx, ny, ct)
                if other_agv is not None and other_agv != agv_id:
                    if reservation_table.is_reserved(cx, cy, next_time, exclude_agv=agv_id):
                        if reservation_table.get_agv_at(cx, cy, next_time) == other_agv:
                            continue  # 对向冲突，跳过

            next_state = (nx, ny, next_time)

            # 计算移动代价
            move_cost = 1
            if (nx, ny) == (cx, cy):
                move_cost = 1.5  # 等待代价略高，鼓励移动

            # 拥塞惩罚
            if congestion_map and 0 <= ny < len(congestion_map) and 0 <= nx < len(congestion_map[0]):
                congestion = congestion_map[ny][nx]
                move_cost += congestion * 0.5

            tentative_g = g_score[current] + move_cost

            if tentative_g < g_score.get(next_state, float('inf')):
                came_from[next_state] = current
                g_score[next_state] = tentative_g
                f = tentative_g + heuristic((nx, ny), goal)
                heapq.heappush(open_set, (f, next_state))

    return None  # 无路径


def path_with_time_to_simple(path_with_time):
    """将带时间的路径转换为简单路径"""
    if not path_with_time:
        return []
    return [(x, y) for x, y, t in path_with_time]


# ==================== 匈牙利算法（任务分配） ====================

def hungarian_assignment(cost_matrix):
    """
    匈牙利算法求解最优分配
    输入: cost_matrix[i][j] = AGV i 完成订单 j 的代价
    输出: [(agv_index, order_index), ...] 最优分配对
    """
    try:
        from scipy.optimize import linear_sum_assignment
        import numpy as np
        cost = np.array(cost_matrix)
        if cost.size == 0:
            return []
        row_ind, col_ind = linear_sum_assignment(cost)
        return list(zip(row_ind.tolist(), col_ind.tolist()))
    except ImportError:
        # 回退到贪心算法
        return greedy_assignment(cost_matrix)


def greedy_assignment(cost_matrix):
    """贪心分配：每次选最小代价的配对"""
    if not cost_matrix or not cost_matrix[0]:
        return []

    assignments = []
    used_rows = set()
    used_cols = set()

    # 收集所有(代价, 行, 列)并排序
    entries = []
    for i, row in enumerate(cost_matrix):
        for j, cost in enumerate(row):
            if cost < float('inf'):
                entries.append((cost, i, j))
    entries.sort()

    for cost, i, j in entries:
        if i not in used_rows and j not in used_cols:
            assignments.append((i, j))
            used_rows.add(i)
            used_cols.add(j)

    return assignments


def random_assignment(num_agvs, num_orders):
    """随机分配"""
    assignments = []
    available_agvs = list(range(num_agvs))
    random.shuffle(available_agvs)
    for i in range(min(num_agvs, num_orders)):
        assignments.append((available_agvs[i], i))
    return assignments


def build_cost_matrix(available_agvs, pending_orders, warehouse_map):
    """构建代价矩阵：AGV到取货点的曼哈顿距离"""
    if not available_agvs or not pending_orders:
        return [], [], []

    cost_matrix = []
    agv_list = list(available_agvs)
    order_list = list(pending_orders)

    for agv in agv_list:
        row = []
        for order in order_list:
            dist = abs(agv.grid_x - order.pick_x) + abs(agv.grid_y - order.pick_y)
            # 考虑电量因素
            if agv.battery < 30:
                dist += 50  # 低电量时代价增大
            row.append(dist)
        cost_matrix.append(row)

    return cost_matrix, agv_list, order_list


# ==================== 冲突检测与解决 ====================

class ConflictType:
    VERTEX = "vertex"  # 顶点冲突：两车同时到达同一格
    EDGE = "edge"      # 边冲突：两车对向交换位置


class Conflict:
    def __init__(self, conflict_type, agv1, agv2, position, time_step):
        self.type = conflict_type
        self.agv1 = agv1
        self.agv2 = agv2
        self.position = position
        self.time_step = time_step


def detect_conflicts(agvs, reservation_table):
    """检测所有AGV路径之间的冲突"""
    conflicts = []

    # 收集所有有路径的AGV
    active_agvs = [agv for agv in agvs if agv.path_with_time]

    for i in range(len(active_agvs)):
        for j in range(i + 1, len(active_agvs)):
            agv1 = active_agvs[i]
            agv2 = active_agvs[j]

            path1 = agv1.path_with_time
            path2 = agv2.path_with_time

            if not path1 or not path2:
                continue

            # 检查顶点冲突：同一时刻同一位置
            time_pos1 = {(t, x, y) for x, y, t in path1}
            time_pos2 = {(t, x, y) for x, y, t in path2}
            conflicts_set = time_pos1 & time_pos2
            for t, x, y in conflicts_set:
                conflicts.append(Conflict(
                    ConflictType.VERTEX, agv1, agv2, (x, y), t
                ))

            # 检查边冲突（对向交换位置）
            for k in range(len(path1) - 1):
                x1a, y1a, t1a = path1[k]
                x1b, y1b, t1b = path1[k + 1]
                for m in range(len(path2) - 1):
                    x2a, y2a, t2a = path2[m]
                    x2b, y2b, t2b = path2[m + 1]
                    if t1a == t2a and t1b == t2b:
                        if (x1a, y1a) == (x2b, y2b) and (x1b, y1b) == (x2a, y2a):
                            conflicts.append(Conflict(
                                ConflictType.EDGE, agv1, agv2, (x1a, y1a), t1a
                            ))

    return conflicts


def resolve_conflicts(conflicts, agvs, warehouse_map, reservation_table, strategy):
    """解决冲突：低优先级AGV等待或重规划"""
    resolved = set()
    for conflict in conflicts:
        agv1_id = conflict.agv1.id if hasattr(conflict.agv1, 'id') else conflict.agv1
        agv2_id = conflict.agv2.id if hasattr(conflict.agv2, 'id') else conflict.agv2

        if (agv1_id, agv2_id) in resolved or (agv2_id, agv1_id) in resolved:
            continue

        # 确定低优先级AGV
        if conflict.agv1.priority < conflict.agv2.priority:
            low_agv = conflict.agv2
        else:
            low_agv = conflict.agv1

        # 低优先级AGV等待
        if strategy == STRATEGY_ADVANCED:
            low_agv.start_waiting(0.5)
            # 清除其路径预留
            reservation_table.clear_agv(low_agv.id)
            low_agv.clear_path()
        else:
            low_agv.start_waiting(0.3)
            low_agv.clear_path()

        resolved.add((agv1_id, agv2_id))


# ==================== 死锁检测与恢复 ====================

def detect_deadlock(agvs):
    """
    检测死锁：构建等待关系图，检测环路
    返回: 死锁环路列表
    """
    # 检查所有等待中的AGV
    waiting_agvs = [agv for agv in agvs if agv.state == AGVState.WAITING]

    if len(waiting_agvs) < 2:
        return []

    # 构建等待图
    wait_graph = defaultdict(set)
    for agv in waiting_agvs:
        if agv.path:
            next_pos = agv.path[0]
            # 找出占据该位置的AGV
            for other in agvs:
                if other.id != agv.id and other.grid_x == next_pos[0] and other.grid_y == next_pos[1]:
                    wait_graph[agv.id].add(other.id)

    # DFS检测环路
    cycles = []
    visited = set()
    rec_stack = set()

    def dfs(node, path):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in wait_graph.get(node, set()):
            if neighbor not in visited:
                cycle = dfs(neighbor, path)
                if cycle:
                    return cycle
            elif neighbor in rec_stack:
                # 找到环路
                cycle_start = path.index(neighbor)
                return path[cycle_start:]

        path.pop()
        rec_stack.discard(node)
        return None

    for agv_id in wait_graph:
        if agv_id not in visited:
            cycle = dfs(agv_id, [])
            if cycle:
                cycles.append(cycle)

    return cycles


def resolve_deadlock(cycles, agvs, warehouse_map, reservation_table):
    """死锁恢复：选择优先级最低的AGV强制绕行"""
    agv_dict = {agv.id: agv for agv in agvs}
    # 计算所有AGV占据的位置
    occupied = {(a.grid_x, a.grid_y) for a in agvs}

    for cycle in cycles:
        # 选择优先级最低（数值最大）的AGV作为牺牲者
        victim_id = max(cycle, key=lambda aid: agv_dict[aid].priority if aid in agv_dict else 999)
        victim = agv_dict.get(victim_id)

        if victim:
            victim.deadlock_count += 1
            reservation_table.clear_agv(victim.id)
            victim.clear_path()

            # 记住原来的状态（WAITING状态的prev_state才是真正的原始状态）
            original_state = victim.prev_state if victim.state == AGVState.WAITING else victim.state
            was_moving_to_pick = (original_state == AGVState.MOVING_TO_PICK)

            # 尝试找一条绕行路径
            if victim.current_order:
                if was_moving_to_pick:
                    goal = (victim.current_order.pick_x, victim.current_order.pick_y)
                else:
                    goal = (victim.current_order.pack_x, victim.current_order.pack_y)

                # 移除victim自己的位置
                victim_occupied = occupied - {(victim.grid_x, victim.grid_y)}
                path = astar_simple(warehouse_map, victim.pos, goal, victim_occupied)
                if path and len(path) > 1:
                    victim.set_path(path[1:])
                    # 恢复原状态，AGV会沿新路径继续任务
                    victim.state = original_state
                else:
                    # 无法找到路径，放弃任务
                    if victim.current_order:
                        victim.current_order.state = OrderState.PENDING
                        victim.current_order.assigned_agv = None
                    victim.current_order = None
                    victim.state = AGVState.IDLE


# ==================== 拥塞控制 ====================

def compute_congestion_map(warehouse_map, agvs):
    """计算拥塞热力图，用于调整路径代价"""
    congestion = [[0.0] * warehouse_map.cols for _ in range(warehouse_map.rows)]

    for agv in agvs:
        if agv.path:
            # 当前位置附近增加拥塞度
            for px, py in agv.path[:10]:  # 只看前10步
                if 0 <= py < warehouse_map.rows and 0 <= px < warehouse_map.cols:
                    congestion[py][px] += 0.3
                    # 扩散到邻居
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nx, ny = px + dx, py + dy
                        if 0 <= ny < warehouse_map.rows and 0 <= nx < warehouse_map.cols:
                            congestion[ny][nx] += 0.1

    return congestion


# ==================== 调度器 ====================

class Scheduler:
    """统一调度器，支持策略切换"""

    def __init__(self, strategy=STRATEGY_ADVANCED):
        self.strategy = strategy
        self.reservation_table = ReservationTable()
        self.conflict_count = 0
        self.deadlock_count = 0

    def assign_orders(self, available_agvs, pending_orders, warehouse_map, sim_time):
        """分配订单给AGV"""
        if not available_agvs or not pending_orders:
            return []

        assignments = []

        if self.strategy == STRATEGY_ADVANCED:
            cost_matrix, agv_list, order_list = build_cost_matrix(
                available_agvs, pending_orders, warehouse_map
            )
            if cost_matrix:
                result = hungarian_assignment(cost_matrix)
                for agv_idx, order_idx in result:
                    if agv_idx < len(agv_list) and order_idx < len(order_list):
                        assignments.append((agv_list[agv_idx], order_list[order_idx]))
        else:
            # 简单策略：随机分配
            agv_list = list(available_agvs)
            order_list = list(pending_orders)
            result = random_assignment(len(agv_list), len(order_list))
            for agv_idx, order_idx in result:
                if agv_idx < len(agv_list) and order_idx < len(order_list):
                    assignments.append((agv_list[agv_idx], order_list[order_idx]))

        return assignments

    def plan_path(self, agv, goal, warehouse_map, start_time=0, congestion_map=None,
                  all_agvs=None):
        """为AGV规划路径，避开其他AGV当前位置"""
        start = agv.pos

        # 计算其他AGV占据的位置
        occupied = set()
        if all_agvs:
            for other in all_agvs:
                if other.id != agv.id:
                    occupied.add((other.grid_x, other.grid_y))

        if self.strategy == STRATEGY_ADVANCED:
            path_wt = astar_with_time_windows(
                warehouse_map, start, goal, self.reservation_table,
                agv.id, start_time, congestion_map
            )
            if path_wt:
                simple_path = path_with_time_to_simple(path_wt)
                # 预留路径
                self.reservation_table.reserve_path(path_wt, agv.id)
                agv.set_path(simple_path[1:] if len(simple_path) > 1 else [],
                             path_wt[1:] if len(path_wt) > 1 else [])
                return True
            else:
                # 回退到简单A*
                path = astar_simple(warehouse_map, start, goal, occupied)
                if path and len(path) > 1:
                    agv.set_path(path[1:])
                    return True
                return False
        else:
            path = astar_simple(warehouse_map, start, goal, occupied)
            if path and len(path) > 1:
                agv.set_path(path[1:])
                return True
            return False

    def detect_and_resolve_conflicts(self, agvs, warehouse_map):
        """检测并解决冲突"""
        conflicts = detect_conflicts(agvs, self.reservation_table)
        self.conflict_count += len(conflicts)

        if conflicts:
            resolve_conflicts(conflicts, agvs, warehouse_map,
                              self.reservation_table, self.strategy)

        return len(conflicts)

    def detect_and_resolve_deadlock(self, agvs, warehouse_map):
        """检测并解决死锁"""
        from models import AGVState

        # 简化版死锁检测：检查等待中的AGV
        waiting_agvs = [agv for agv in agvs if agv.state == AGVState.WAITING]

        if len(waiting_agvs) >= 2:
            # 检查是否形成环路
            cycles = detect_deadlock(agvs)
            if cycles:
                self.deadlock_count += len(cycles)
                resolve_deadlock(cycles, agvs, warehouse_map, self.reservation_table)
                return len(cycles)

        return 0

    def clear_agv_reservations(self, agv_id):
        """清除AGV的预留"""
        self.reservation_table.clear_agv(agv_id)

    def reset_reservations(self):
        """重置所有预留"""
        self.reservation_table.clear_all()
