# 从零搭建智能仓储 AGV 数字孪生仿真系统

## 完整教学文档

---

# 第一章 项目总览：我们在做什么？

## 1.1 什么是数字孪生？

想象你有一个真实的仓库，里面有几十台 AGV（自动导引车）在跑来跑去取货送货。**数字孪生**就是在电脑里建一个"虚拟的仓库"，用算法模拟这些 AGV 的行为，让你能直观地看到调度效果、发现问题、优化策略——而不用在真实仓库里做实验。

## 1.2 这个项目做什么？

我们用 **Python + Pygame** 构建一个 2D 仓库仿真系统：

- 一个 40×30 的网格地图，模拟仓库布局（货架、通道、打包台、充电站）
- 10 台 AGV 在地图上移动，接收订单、前往取货、送到打包台
- 核心算法实时调度：路径规划、冲突避免、死锁恢复
- 右侧仪表盘实时展示性能数据
- 支持两种策略对比：简单策略 vs 高级策略

## 1.3 最终效果

运行 `python main.py` 后你会看到：

```
┌──────────────────────────────────┬──────────────┐
│                                  │  AGV Digital  │
│    [货架区] [货架区] [货架区]     │    Twin       │
│                                  │              │
│    🚗→  [货架区] [货架区]        │  Sim: 45.2s  │
│         🚗→                      │  Strategy:   │
│    [货架区] [货架区] [货架区]     │  Advanced    │
│                                  │              │
│         P        P        P      │  Completed:32│
│                                  │  Pending: 5  │
│                                  │  ...         │
│                                  │  [1x][2x][5x]│
└──────────────────────────────────┴──────────────┘
```

## 1.4 你会学到什么？

| 知识点 | 章节 |
|--------|------|
| 如何设计网格地图和仓库布局 | 第二章 |
| A* 路径规划算法（简单版 + 时间窗版） | 第三章 |
| 匈牙利算法做最优任务分配 | 第四章 |
| 多车冲突检测与死锁恢复 | 第五章 |
| 仿真引擎的 tick 驱动架构 | 第六章 |
| Pygame 渲染和交互系统 | 第七章 |
| 从零搭建完整项目的工程方法 | 全文 |

---

# 第二章 地图与场景建模

## 2.1 为什么用网格地图？

真实仓库的地面是连续的，但仿真中我们把它**离散化**成网格。就像棋盘一样，每个格子要么是通道（可走），要么是货架（不可走）。这样做的好处：

1. **计算简单**：A* 等算法在离散网格上效率极高
2. **碰撞检测容易**：只需检查格子是否被占据
3. **可视化直观**：一个格子画一个方块就行

## 2.2 网格设计

我们选择 **40 列 × 30 行** 的网格，每个格子 25×25 像素：

```python
# config.py
GRID_COLS = 40
GRID_ROWS = 30
CELL_SIZE = 25  # 像素
```

四种格子类型：

```python
CELL_EMPTY = 0          # 空地（通道），AGV 可走
CELL_SHELF = 1          # 货架，AGV 不可走
CELL_PACK_STATION = 2   # 打包台，订单交付终点
CELL_CHARGE_STATION = 3 # 充电站，AGV 充电
```

## 2.3 仓库布局

地图从 JSON 配置文件加载，方便更换布局：

```json
{
  "shelf_regions": [
    {"x": 2, "y": 1, "w": 5, "h": 2},
    ...
  ],
  "pack_stations": [
    {"x": 5, "y": 27},
    {"x": 15, "y": 27},
    {"x": 25, "y": 27},
    {"x": 35, "y": 27}
  ],
  "charge_stations": [
    {"x": 1, "y": 0},
    {"x": 38, "y": 0},
    {"x": 1, "y": 29},
    {"x": 38, "y": 29}
  ]
}
```

布局逻辑：
- **货架区**：8 行 × 5 列排列，每块 5×2 格，行间留 3 格通道
- **打包台**：4 个，集中在底部第 27 行
- **充电站**：4 个，在仓库四角

## 2.4 取货点的计算

取货点不是手动指定的，而是**自动计算**的——紧邻货架的通道格就是取货点：

```python
def _compute_pick_points(self):
    for (sx, sy) in self.shelf_positions:
        for dx, dy in [(0,-1), (0,1), (-1,0), (1,0)]:
            nx, ny = sx + dx, sy + dy
            if self.grid[ny][nx] == CELL_EMPTY:
                self.pick_points.append((nx, ny))
```

逻辑：遍历每个货架格，检查上下左右 4 个方向，如果是空地就标记为取货点。

## 2.5 货物类型系统

不同货架存放不同货物，我们定义了 8 种货物类型：

```python
GOODS_TYPES = [
    {"name": "电子", "color": (100, 150, 255), "symbol": "E"},
    {"name": "服装", "color": (255, 130, 170), "symbol": "C"},
    {"name": "食品", "color": (130, 220, 130), "symbol": "F"},
    ...
]
```

分配规则：**同一行的货架存同一种货物**，按行号循环分配：

```python
shelf_rows = sorted(set(y for x, y in self.shelf_positions))
row_goods = {}
for i, row in enumerate(shelf_rows):
    row_goods[row] = i % len(GOODS_TYPES)
```

这样在渲染时，货架会显示对应货物的颜色和符号，一眼就能看出哪个区域存什么。

## 2.6 WarehouseMap 类完整结构

```
WarehouseMap
├── grid[30][40]          # 二维网格数组
├── pack_stations[]       # 打包台坐标列表
├── charge_stations[]     # 充电站坐标列表
├── shelf_positions[]     # 货架坐标列表
├── pick_points[]         # 取货点坐标列表
├── shelf_goods{}         # 货架→货物类型映射
├── pick_point_goods{}    # 取货点→货物类型映射
├── heatmap[30][40]       # 热力图数据
│
├── load_from_json()      # 加载地图配置
├── _compute_pick_points()# 计算取货点+分配货物
├── is_walkable()         # 判断是否可走
├── get_walkable_neighbors()# 获取4方向邻居
├── add_obstacle()        # 动态添加障碍
├── remove_obstacle()     # 动态移除障碍
├── update_heatmap()      # 更新热力图
├── get_random_pick_point()# 随机取货点
├── get_nearest_pack_station()# 最近打包台
└── get_nearest_charge_station()# 最近充电站
```

---

# 第三章 路径规划：A* 算法

## 3.1 为什么需要路径规划？

AGV 从 A 点到 B 点，不能穿墙，要绕过货架。路径规划就是找到一条**最短可行路径**。

## 3.2 基础 A* 算法

A* 是最经典的寻路算法，核心思想：**从起点开始，每次选择"最有希望"的格子探索，直到找到终点**。

### 3.2.1 核心公式

```
f(n) = g(n) + h(n)
```

- `g(n)`：从起点到 n 的**实际代价**（走了几步）
- `h(n)`：从 n 到终点的**估计代价**（启发函数）
- `f(n)`：总估计代价，越小越优先探索

### 3.2.2 启发函数：曼哈顿距离

我们的 AGV 只能上下左右走（不能斜走），所以用曼哈顿距离：

```python
def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])
```

例如从 (2,3) 到 (5,7)，曼哈顿距离 = |5-2| + |7-3| = 3+4 = 7。

### 3.2.3 算法流程

```
1. 把起点放入 open_set，g(起点)=0
2. 循环：
   a. 从 open_set 中取出 f 值最小的节点 current
   b. 如果 current == 终点，回溯路径，结束
   c. 遍历 current 的4个邻居：
      - 如果邻居是墙或已被占据，跳过
      - 计算 tentative_g = g(current) + 1
      - 如果 tentative_g < g(邻居)，更新邻居的 g、f、came_from
      - 把邻居加入 open_set
3. open_set 空了还没找到终点 → 无路径
```

### 3.2.4 代码实现

```python
def astar_simple(warehouse_map, start, goal, occupied_positions=None):
    if start == goal:
        return [start]

    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score = {start: 0}

    while open_set:
        _, current = heapq.heappop(open_set)

        if current == goal:
            # 回溯路径
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            path.reverse()
            return path

        for nx, ny in warehouse_map.get_walkable_neighbors(*current):
            neighbor = (nx, ny)
            # 避开其他AGV占据的位置（目标点例外）
            if neighbor in occupied_positions and neighbor != goal:
                continue
            tentative_g = g_score[current] + 1

            if tentative_g < g_score.get(neighbor, float('inf')):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f = tentative_g + heuristic(neighbor, goal)
                heapq.heappush(open_set, (f, neighbor))

    return None  # 无路径
```

**关键点**：
- `heapq` 是 Python 的最小堆，保证每次取出 f 值最小的节点
- `occupied_positions` 是其他 AGV 当前占据的位置集合，规划时绕开
- `neighbor != goal`：即使目标点被占据也允许规划到（到达时会等对方让开）

## 3.3 带时间窗的 A*

基础 A* 只考虑空间（不撞墙），但多车场景还要考虑**时间**——两个 AGV 不能在同一时刻到达同一格。

### 3.3.1 核心思想

把搜索状态从 `(x, y)` 扩展为 `(x, y, t)`，即"在时刻 t 位于 (x,y)"。同时维护一个**预留表**，记录每个时空位置被哪辆 AGV 占用。

### 3.3.2 预留表

```python
class ReservationTable:
    def __init__(self):
        self.reservations = {}  # (x, y, t) -> agv_id

    def reserve(self, x, y, t, agv_id):
        self.reservations[(x, y, t)] = agv_id

    def is_reserved(self, x, y, t, exclude_agv=None):
        key = (x, y, t)
        if key in self.reservations:
            if exclude_agv and self.reservations[key] == exclude_agv:
                return False  # 自己的预留不算冲突
            return True
        return False
```

### 3.3.3 算法差异

与简单 A* 的区别：

| 特性 | 简单 A* | 时间窗 A* |
|------|---------|-----------|
| 搜索状态 | (x, y) | (x, y, t) |
| 冲突检查 | 只检查墙壁 | 检查预留表 + 对向冲突 |
| 可选动作 | 4方向移动 | 4方向移动 + **原地等待** |
| 等待代价 | 无 | 1.5（比移动高，鼓励移动） |
| 拥塞惩罚 | 无 | 根据热力图动态调整 |

### 3.3.4 对向冲突检测

两车对向交换位置是最常见的冲突：

```
时刻 t:   AGV_A 在 (3,5), AGV_B 在 (4,5)
时刻 t+1: AGV_A 要去 (4,5), AGV_B 要去 (3,5)
→ 两车"穿过"对方，这在现实中不可能！
```

检测方法：如果 AGV_A 的下一格是 AGV_B 的当前位置，且 AGV_B 的下一格是 AGV_A 的当前位置，则存在对向冲突。

### 3.3.5 拥塞惩罚

高级策略还会计算拥塞图，让 A* 自动避开拥堵区域：

```python
if congestion_map:
    congestion = congestion_map[ny][nx]
    move_cost += congestion * 0.5  # 拥堵区域代价更高
```

---

# 第四章 任务分配：匈牙利算法

## 4.1 问题场景

假设现在有 5 个待处理订单和 3 辆空闲 AGV，怎么分配最合理？

| | 订单1 | 订单2 | 订单3 | 订单4 | 订单5 |
|---|---|---|---|---|---|
| AGV0 | 3 | 7 | 2 | 9 | 5 |
| AGV1 | 6 | 1 | 8 | 4 | 3 |
| AGV2 | 5 | 4 | 3 | 2 | 7 |

数字是曼哈顿距离（AGV 到取货点的距离）。我们希望**总距离最小**。

## 4.2 两种策略

### 4.2.1 简单策略：随机分配

```python
def random_assignment(num_agvs, num_orders):
    available_agvs = list(range(num_agvs))
    random.shuffle(available_agvs)
    assignments = []
    for i in range(min(num_agvs, num_orders)):
        assignments.append((available_agvs[i], i))
    return assignments
```

随机打乱 AGV 顺序，依次分配订单。简单但效率低。

### 4.2.2 高级策略：匈牙利算法

匈牙利算法能在多项式时间内找到**全局最优分配**，使总代价最小。

```python
def hungarian_assignment(cost_matrix):
    from scipy.optimize import linear_sum_assignment
    import numpy as np
    cost = np.array(cost_matrix)
    row_ind, col_ind = linear_sum_assignment(cost)
    return list(zip(row_ind.tolist(), col_ind.tolist()))
```

我们直接调用 scipy 的实现，它内部用的是 Jonker-Volgenant 算法，比经典匈牙利算法更快。

### 4.2.3 贪心回退

如果没装 scipy，回退到贪心算法：

```python
def greedy_assignment(cost_matrix):
    # 收集所有(代价, AGV, 订单)并排序
    entries = []
    for i, row in enumerate(cost_matrix):
        for j, cost in enumerate(row):
            entries.append((cost, i, j))
    entries.sort()

    # 贪心选最小代价
    used_rows, used_cols = set(), set()
    for cost, i, j in entries:
        if i not in used_rows and j not in used_cols:
            assignments.append((i, j))
            used_rows.add(i)
            used_cols.add(j)
```

## 4.3 代价矩阵构建

代价 = 曼哈顿距离 + 低电量惩罚：

```python
def build_cost_matrix(available_agvs, pending_orders, warehouse_map):
    for agv in agv_list:
        for order in order_list:
            dist = abs(agv.grid_x - order.pick_x) + abs(agv.grid_y - order.pick_y)
            if agv.battery < 30:
                dist += 50  # 低电量AGV代价增大，减少分配
            row.append(dist)
```

---

# 第五章 冲突检测与死锁恢复

## 5.1 为什么需要冲突处理？

路径规划只保证单车不撞墙，但多车同时运行时会出现：

1. **顶点冲突**：两车同时到达同一格
2. **边冲突**：两车对向交换位置
3. **死锁**：多车互相等待，形成环路

## 5.2 顶点冲突检测

```python
# 检查两辆车的路径是否有"同一时刻同一位置"
time_pos1 = {(t, x, y) for x, y, t in path1}
time_pos2 = {(t, x, y) for x, y, t in path2}
conflicts = time_pos1 & time_pos2  # 集合交集
```

## 5.3 边冲突检测

```python
# 检查两车是否在相邻时间步交换位置
for k in range(len(path1) - 1):
    for m in range(len(path2) - 1):
        if path1[k]的位置 == path2[m+1]的位置 and path1[k+1]的位置 == path2[m]的位置:
            if 时间也匹配:
                → 边冲突！
```

## 5.4 冲突解决：优先级协商

每辆 AGV 有一个优先级（ID 越小优先级越高）。冲突时**低优先级让路**：

```python
def resolve_conflicts(conflicts, agvs, ...):
    for conflict in conflicts:
        # 确定低优先级AGV
        if conflict.agv1.priority < conflict.agv2.priority:
            low_agv = conflict.agv2
        else:
            low_agv = conflict.agv1

        # 低优先级AGV等待并清空路径
        low_agv.start_waiting(0.5)
        low_agv.clear_path()
```

## 5.5 死锁检测：环路检测

死锁是多车互相等待形成的环路。例如：

```
AGV_A 等 AGV_B 让路 → AGV_B 等 AGV_C 让路 → AGV_C 等 AGV_A 让路
→ 形成环路，谁也不会动
```

检测方法：构建**等待关系图**，用 DFS 找环路：

```python
def detect_deadlock(agvs):
    # 构建等待图：AGV_A 等 AGV_B → 图中有 A→B 的边
    wait_graph = defaultdict(set)
    for agv in waiting_agvs:
        if agv.path:
            next_pos = agv.path[0]
            for other in agvs:
                if other.pos == next_pos:
                    wait_graph[agv.id].add(other.id)

    # DFS检测环路
    for agv_id in wait_graph:
        cycle = dfs(agv_id, [])
        if cycle:
            cycles.append(cycle)
```

## 5.6 死锁恢复：牺牲者绕行

找到环路后，选择**优先级最低的 AGV** 作为牺牲者，强制重规划：

```python
def resolve_deadlock(cycles, agvs, ...):
    victim = 优先级最低的AGV
    victim.clear_path()

    # 尝试找绕行路径
    path = astar_simple(warehouse_map, victim.pos, goal, occupied)
    if path:
        victim.set_path(path[1:])
        victim.state = original_state  # 恢复原状态继续任务
    else:
        # 实在绕不过去，放弃任务
        victim.current_order.state = PENDING  # 订单回到待分配
        victim.current_order = None
        victim.state = IDLE
```

## 5.7 对向堵死：超时重规划

两车在窄通道面对面，互相挡路，谁也过不去。我们用**被挡计时器**解决：

```python
# AGV 被挡时累加计时
if blocked:
    self.blocked_timer += dt
    return False

# 成功移动时重置
self.blocked_timer = 0.0
```

超过 1.5 秒被挡，触发重规划：

```python
def _reroute_blocked_agvs(self):
    for agv in self.agvs:
        if agv.blocked_timer < 1.5:
            continue

        if agv.priority >= blocker.priority:
            # 低优先级：后退让路
            retreat = _find_retreat_for_reroute(agv, blocker)
            agv.set_path(path_to_retreat)
            agv.state = RETREAT  # 避让状态
        else:
            # 高优先级：重新A*绕路
            path = astar_simple(map, agv.pos, goal, occupied)
            agv.set_path(path)
```

## 5.8 打包台堵死：IDLE 让位

AGV 完成送货后停在打包台，后续 AGV 被挡住。解决方案：

1. **打包台不停靠**：AGV 目标改为打包台**旁边**的空格
2. **IDLE 自动让位**：站在关键位置的 IDLE AGV 自动移走

```python
def _move_idle_from_critical_positions(self):
    for agv in self.agvs:
        if agv.state != IDLE:
            continue
        if agv.pos in critical_positions:
            retreat = _find_retreat_position(agv)  # BFS找附近空地
            agv.state = RETREAT
            agv.set_path(path_to_retreat)
```

---

# 第六章 仿真引擎

## 6.1 Tick 驱动架构

仿真引擎采用**固定时间步**（tick）驱动，每帧执行一次 tick：

```
每帧(1/60秒) → tick(dt)
```

每个 tick 按固定顺序执行 10 个步骤：

```
┌─────────────────────────────────────────┐
│  1. 生成新订单（泊松分布）                │
│  2. 低电量AGV → 触发充电                 │
│  3. 任务分配（匈牙利/随机）               │
│  4. 计算拥塞图（高级策略）                │
│  5. 路径规划（时间窗A*/简单A*）           │
│  6. 冲突检测与解决                        │
│  7. 死锁检测与恢复                        │
│  8. 对向堵死重规划                        │
│  9. IDLE AGV让开关键位置                  │
│ 10. 更新AGV位置 + 统计                    │
└─────────────────────────────────────────┘
```

**为什么是这个顺序？**

- 先生成订单、分配任务（1-3），AGV 才有目标
- 再规划路径（4-5），AGV 才知道怎么走
- 然后处理冲突和死锁（6-8），确保安全
- 最后让 IDLE AGV 让位（9），避免堵路
- 更新位置和统计（10），完成本轮

## 6.2 订单生成：泊松过程

真实仓库的订单到达是随机的，我们用**泊松过程**模拟：

```python
def _generate_interval(self):
    return random.expovariate(1.0 / self.mean_interval)
```

`expovariate` 生成指数分布的随机数，均值是 `mean_interval`（1.5 秒）。这意味着：
- 大部分时间订单间隔较短
- 偶尔会有较长的空闲期
- 整体平均每 1.5 秒来一个订单

## 6.3 AGV 状态机

每辆 AGV 有 9 种状态，形成状态机：

```
                    ┌──────────┐
         分配订单    │          │
    IDLE ──────────→│MOVING_TO │
     ↑              │  PICK    │──→ 到达取货点
     │              └──────────┘        │
     │                                  ↓
     │                            ┌──────────┐
     │                            │ PICKING  │──→ 取货完成
     │                            └──────────┘        │
     │                                                  ↓
     │              ┌──────────┐                  ┌──────────┐
     │              │MOVING_TO │←─────────────────│ 送到打包 │
     │              │  PACK    │                  │  台旁边  │
     │              └──────────┘        │
     │                     到达打包台   ↓
     │                         ┌──────┐
     └─────────────────────────│ IDLE │
                               └──────┘

    特殊状态：
    - MOVING_TO_CHARGE: 前往充电站
    - CHARGING: 充电中 → 充满 → IDLE
    - WAITING: 被挡等待 → 超时 → 恢复原状态
    - RETREAT: 避让后退 → 到达 → IDLE
    - DEADLOCK_RECOVERY: 死锁恢复（当前未使用）
```

## 6.4 AGV 移动与平滑渲染

AGV 的移动分两层：

1. **逻辑层**：`grid_x, grid_y` 是当前所在的网格坐标（整数）
2. **渲染层**：`render_x, render_y` 是屏幕上的浮点坐标，用于平滑插值

```python
def _move_along_path(self, dt, warehouse_map, other_agvs):
    # 累加移动进度
    self.move_progress += self.speed * dt

    if self.move_progress >= 1.0:
        # 到达下一格，更新逻辑坐标
        self.grid_x, self.grid_y = self.path[0]
        self.render_x = float(self.grid_x)  # 对齐
        self.move_progress = 0.0
    else:
        # 平滑插值
        nx, ny = self.path[0]
        self.render_x = self.grid_x + (nx - self.grid_x) * self.move_progress
        self.render_y = self.grid_y + (ny - self.grid_y) * self.move_progress
```

这样 AGV 在视觉上是平滑移动的，而不是一格一格跳。

## 6.5 实时碰撞检测

AGV 移动前检查下一格是否被占据：

```python
# 检查下一格
for other in other_agvs:
    if other.grid_x == next_pos[0] and other.grid_y == next_pos[1]:
        blocked = True  # 被挡住了

# 检查对向冲突
if other.path and other.path[0] == my_pos and my_next == other.pos:
    if my_priority > other_priority:
        blocked = True  # 优先级低，让路
```

## 6.6 电量模型

```python
# 移动消耗
self.battery -= AGV_BATTERY_DRAIN_MOVE  # 0.08/格

# 待机消耗
self.battery -= AGV_BATTERY_DRAIN_IDLE * dt * 60  # 0.005/tick

# 充电
self.battery += AGV_BATTERY_CHARGE_RATE * dt * 60  # 0.5/tick

# 低电量自动触发充电
if agv.battery <= 20.0:
    → 取消当前任务
    → 规划前往充电站
    → 到达后充电
    → 充满回到 IDLE
```

---

# 第七章 渲染与交互

## 7.1 Pygame 基础

Pygame 是 Python 的 2D 游戏库，核心循环：

```python
while running:
    for event in pygame.event.get():  # 处理事件
        ...

    screen.fill(BG_COLOR)             # 清屏
    # 绘制所有内容...
    pygame.display.flip()             # 刷新显示
    clock.tick(60)                    # 控制帧率
```

## 7.2 坐标转换

网格坐标和屏幕像素坐标的转换：

```python
def grid_to_screen(self, gx, gy):
    sx = MAP_OFFSET_X + gx * CELL_SIZE
    sy = MAP_OFFSET_Y + gy * CELL_SIZE
    return (sx, sy)

def screen_to_grid(self, sx, sy):
    gx = (sx - MAP_OFFSET_X) // CELL_SIZE
    gy = (sy - MAP_OFFSET_Y) // CELL_SIZE
    return (gx, gy) if 0 <= gx < COLS and 0 <= gy < ROWS else None
```

## 7.3 地图渲染（带缓存）

地图是静态的，不需要每帧重绘。我们用 `map_surface` 缓存：

```python
def _draw_map(self, warehouse_map):
    if self.map_dirty or self.map_surface is None:
        self.map_surface = pygame.Surface((MAP_WIDTH, MAP_HEIGHT))
        # 绘制所有格子...
        self.map_dirty = False

    self.screen.blit(self.map_surface, (0, 0))  # 直接贴图
```

只在地图变化时（添加/移除障碍）才重绘，大幅提升性能。

### 货架渲染

货架根据货物类型着色：

```python
if cell == CELL_SHELF:
    goods_idx = warehouse_map.shelf_goods.get((x, y), 0)
    goods_info = GOODS_TYPES[goods_idx]
    # 混合颜色
    shelf_color = (
        (COLOR_SHELF[0] + goods_info["color"][0]) // 2,
        (COLOR_SHELF[1] + goods_info["color"][1]) // 2,
        (COLOR_SHELF[2] + goods_info["color"][2]) // 2,
    )
    pygame.draw.rect(surface, shelf_color, rect)
    # 绘制货物符号
    text = font.render(goods_info["symbol"], True, (220, 220, 220))
```

## 7.4 AGV 渲染

每辆 AGV 绘制 4 层：

```
┌──────────────┐
│ ■ 电量条      │  ← 绿/黄/红三色
│┌────────────┐│
││     3      ││  ← ID 编号
││   (主体)   ││  ← AGV 颜色 + 状态边框
│└────────────┘│
│         [E]  │  ← 载货标识（货物颜色方块）
└──────────────┘
```

任务目标标记：
- 前往取货：目标点闪烁圆圈 + 连线到 AGV
- 前往送货：打包台闪烁方框

## 7.5 路径渲染

用半透明折线绘制每辆 AGV 的规划路径：

```python
path_surface = pygame.Surface((MAP_WIDTH, MAP_HEIGHT), pygame.SRCALPHA)
for agv in agvs:
    if agv.path:
        points = [(agv.render_x, agv.render_y)] + agv.path
        screen_points = [grid_to_screen(p) for p in points]
        pygame.draw.lines(path_surface, (*agv.color, 120), False, screen_points, 2)
screen.blit(path_surface, (0, 0))
```

**性能优化**：所有路径共用一个 Surface，而不是每条路径创建一个。

## 7.6 热力图

叠加半透明红-绿蒙层，显示通道访问频率：

```python
for y in range(rows):
    for x in range(cols):
        val = heatmap[y][x]
        if val > 0:
            intensity = min(val / MAX_VISITS, 1.0)
            r = int(255 * intensity)      # 红 = 热门
            g = int(255 * (1 - intensity)) # 绿 = 冷门
            pygame.draw.rect(surface, (r, g, 0, ALPHA), rect)
```

## 7.7 仪表盘

右侧 400px 宽的仪表盘，从上到下：

1. **标题**：AGV Digital Twin
2. **仿真时间**：Sim Time: 45.2s
3. **策略标识**：Advanced (Hungarian+TW) / Simple (Random+A*)
4. **货物图例**：8 种货物的颜色+符号
5. **统计卡片**：完成数、待处理数、平均等待时间、平均完成时间、AGV 利用率、冲突数、死锁数
6. **吞吐量折线图**：最近 200 个 5 秒窗口的订单/秒
7. **AGV 状态列表**：每辆 AGV 的颜色、状态、货物信息
8. **控制按钮**：速度(暂停/1x/2x/5x/10x)、策略切换、显示切换(路径/热力图/时间窗)
9. **快捷键提示**

## 7.8 交互功能

| 操作 | 效果 |
|------|------|
| 左键点击空地 | 添加临时障碍 |
| 左键点击货架 | 移除障碍 |
| 左键点击 AGV + 拖拽 | 移动 AGV 位置（调试） |
| 右键点击地图 | 创建紧急订单 |
| 空格键 | 暂停/继续 |
| P 键 | 切换路径显示 |
| H 键 | 切换热力图 |
| S 键 | 切换调度策略 |
| 左/右方向键 | 减速/加速 |

---

# 第八章 订单生命周期

## 8.1 完整流程

一个订单从创建到完成经历 5 个状态：

```
PENDING → ASSIGNED → PICKING → DELIVERING → COMPLETED
  │          │          │           │
  │          │          │           └─ AGV送到打包台旁
  │          │          └─ AGV到达取货点，取货2秒
  │          └─ 调度器分配给某辆AGV
  └─ 泊松过程生成，等待分配
```

## 8.2 时间记录

每个订单记录 4 个时间戳：

```python
order.create_time      # 创建时间
order.assign_time      # 分配时间 → wait_time = assign_time - create_time
order.pick_start_time  # 取货开始时间
order.complete_time    # 完成时间 → total_time = complete_time - create_time
```

## 8.3 订单与货物的关联

每个订单携带货物类型：

```python
class Order:
    def __init__(self, pick_x, pick_y, pack_x, pack_y, goods_type=0):
        self.goods_type = goods_type  # 货物类型索引
```

货物类型在订单创建时根据取货点位置自动确定：

```python
goods_type = warehouse_map.pick_point_goods.get(pick_point, 0)
```

---

# 第九章 系统架构与分层设计

## 9.1 分层架构

```
┌─────────────────────────────────────────┐
│           展示层 (renderer.py)           │
│   地图渲染 / AGV渲染 / 仪表盘 / 交互    │
├─────────────────────────────────────────┤
│          仿真核心 (simulation.py)        │
│   tick驱动 / 订单生成 / 位置更新 / 统计  │
├─────────────────────────────────────────┤
│          算法服务 (algorithms.py)        │
│   A* / 匈牙利 / 冲突检测 / 死锁恢复     │
├─────────────────────────────────────────┤
│          数据存储 (models.py)            │
│   WarehouseMap / AGV / Order            │
├─────────────────────────────────────────┤
│          配置层 (config.py)              │
│   常量 / 颜色 / 参数                    │
└─────────────────────────────────────────┘
```

**依赖方向**：上层依赖下层，下层不依赖上层。

## 9.2 文件职责

| 文件 | 行数 | 职责 |
|------|------|------|
| `config.py` | ~130 | 所有配置常量，改参数只改这个文件 |
| `models.py` | ~430 | 数据模型：地图、AGV、订单 |
| `algorithms.py` | ~570 | 纯算法：A*、匈牙利、冲突检测 |
| `simulation.py` | ~440 | 仿真引擎：tick 流水线、调度逻辑 |
| `renderer.py` | ~530 | 渲染层：所有 Pygame 绘制 |
| `main.py` | ~110 | 入口：事件循环 |
| `map_config.json` | ~100 | 地图配置：货架/打包台/充电站位置 |

## 9.3 数据流

```
用户操作 → main.py 事件处理
              ↓
    SimulationEngine.tick(dt)
              ↓
    ┌─ 1. OrderGenerator.update() → 新订单
    ├─ 2. _handle_low_battery()   → 充电任务
    ├─ 3. Scheduler.assign_orders() → AGV←→订单配对
    ├─ 4. compute_congestion_map() → 拥塞数据
    ├─ 5. Scheduler.plan_path()    → A*路径
    ├─ 6. detect_conflicts()       → 冲突列表
    ├─ 7. detect_deadlock()        → 死锁环路
    ├─ 8. _reroute_blocked_agvs()  → 重规划
    ├─ 9. _move_idle_from_critical_positions() → 让位
    └─10. AGV.update()             → 位置更新
              ↓
    Renderer.render(engine) → 屏幕
```

---

# 第十章 性能优化要点

## 10.1 地图缓存

地图是静态的，只在变化时重绘：

```python
if self.map_dirty or self.map_surface is None:
    # 重绘地图...
    self.map_dirty = False
```

## 10.2 路径渲染合并

所有 AGV 的路径共用一个半透明 Surface：

```python
path_surface = pygame.Surface((MAP_WIDTH, MAP_HEIGHT), pygame.SRCALPHA)
for agv in agvs:
    pygame.draw.lines(path_surface, ...)
screen.blit(path_surface, (0, 0))
```

而不是每条路径创建一个 Surface（10 辆 AGV 就省了 9 个 Surface 创建）。

## 10.3 A* 避开被占位置

路径规划时直接把其他 AGV 的位置当作"临时障碍"，减少后续碰撞：

```python
occupied = {(a.grid_x, a.grid_y) for a in all_agvs if a.id != agv.id}
path = astar_simple(map, start, goal, occupied)
```

## 10.4 打包台旁停靠

AGV 不站到打包台格子上，而是停到旁边空格，避免堵住打包台：

```python
goal = _find_adjacent_free_cell(pack_pos, agv)
```

---

# 第十一章 从零搭建的步骤

如果你想从零开始搭建这个项目，建议按以下顺序：

## Step 1：创建配置文件

```bash
# 先写 config.py，定义所有常量
# 这一步不需要任何依赖
```

## Step 2：创建地图配置

```bash
# 写 map_config.json，定义仓库布局
# 可以用纸笔画出布局，然后转成坐标
```

## Step 3：实现数据模型

```bash
# 写 models.py
# 先实现 WarehouseMap（加载地图、判断可行走）
# 再实现 AGV（状态、移动）
# 最后实现 Order 和 OrderGenerator
```

## Step 4：实现算法

```bash
# 写 algorithms.py
# 先实现 astar_simple（最基础）
# 测试：能否找到路径？
# 再实现 astar_with_time_windows
# 再实现匈牙利分配
# 最后实现冲突检测和死锁恢复
```

## Step 5：实现仿真引擎

```bash
# 写 simulation.py
# 先实现基本的 tick 循环
# 逐步添加：订单生成 → 任务分配 → 路径规划 → 冲突处理
```

## Step 6：实现渲染

```bash
# 写 renderer.py
# 先画地图（验证布局正确）
# 再画 AGV（验证移动逻辑）
# 最后画仪表盘和交互
```

## Step 7：整合入口

```bash
# 写 main.py
# 连接仿真引擎和渲染器
# 添加事件处理
```

## Step 8：安装依赖并运行

```bash
pip install pygame numpy scipy
python main.py
```

---

# 第十二章 扩展方向

## 12.1 更多算法

- **D* Lite**：动态环境下的增量式重规划
- **CBS（Conflict-Based Search）**：最优多车路径规划
- **强化学习**：用 DQN/PPO 训练调度策略

## 12.2 更丰富的场景

- 多层仓库（立体货架）
- AGV 故障模拟
- 临时通道封闭
- 订单优先级（紧急订单插队）

## 12.3 数据分析

- 导出仿真数据为 CSV
- 生成性能报告
- 对比不同策略的长时间运行效果

## 12.4 可视化增强

- 3D 视角渲染
- AGV 动画（旋转、加速）
- 订单流向动画

---

# 附录 A：完整文件清单

| 文件 | 说明 |
|------|------|
| `config.py` | 系统配置常量（窗口、网格、颜色、AGV参数、货物类型等） |
| `map_config.json` | 仓库布局配置（货架区域、打包台、充电站、AGV起始位置） |
| `models.py` | 数据模型（WarehouseMap、AGV、Order、OrderGenerator） |
| `algorithms.py` | 核心算法（A*、匈牙利、冲突检测、死锁恢复、拥塞控制、调度器） |
| `simulation.py` | 仿真引擎（tick流水线、统计、交互接口） |
| `renderer.py` | Pygame渲染（地图、AGV、路径、热力图、仪表盘、按钮） |
| `main.py` | 程序入口（事件循环、键盘鼠标处理） |

# 附录 B：快捷键一览

| 按键 | 功能 |
|------|------|
| Space | 暂停/继续 |
| P | 切换路径显示 |
| H | 切换热力图 |
| T | 切换时间窗显示 |
| S | 切换调度策略 |
| ← | 减速 |
| → | 加速 |
| Esc | 退出 |
| 左键点击空地 | 添加障碍 |
| 左键点击货架 | 移除障碍 |
| 左键拖拽AGV | 移动AGV位置 |
| 右键点击地图 | 创建紧急订单 |

# 附录 C：AGV 状态说明

| 状态 | 含义 | 边框颜色 | 行为 |
|------|------|----------|------|
| IDLE | 空闲 | 绿色 | 等待分配任务 |
| MOVING_TO_PICK | 前往取货 | 青色 | 沿路径移动到取货点 |
| PICKING | 取货中 | 黄色 | 原地停留2秒 |
| MOVING_TO_PACK | 前往打包 | 青色 | 沿路径移动到打包台旁 |
| MOVING_TO_CHARGE | 前往充电 | 黄色 | 沿路径移动到充电站旁 |
| CHARGING | 充电中 | 黄色 | 原地充电直到满 |
| WAITING | 等待 | 红色 | 等待计时器倒计 |
| RETREAT | 避让 | 橄榄色 | 后退到空地让路 |
| DEADLOCK_RECOVERY | 死锁恢复 | 红色 | 绕行恢复（预留） |

# 附录 D：货物类型一览

| 符号 | 名称 | 颜色 |
|------|------|------|
| E | 电子 | 蓝色 (100,150,255) |
| C | 服装 | 粉色 (255,130,170) |
| F | 食品 | 绿色 (130,220,130) |
| D | 日用 | 黄色 (220,200,100) |
| M | 医药 | 紫色 (200,130,255) |
| B | 图书 | 棕色 (180,140,100) |
| T | 玩具 | 橙色 (255,180,80) |
| S | 运动 | 青色 (100,220,220) |
