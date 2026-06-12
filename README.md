# 智能仓储 AGV 数字孪生仿真系统

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Pygame](https://img.shields.io/badge/Pygame-2.0+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

一个基于 Python + Pygame 的智能仓储 AGV 调度仿真系统，支持多车协同、路径规划、冲突避免和性能优化。

[功能特性](#功能特性) • [快速开始](#快速开始) • [使用教程](#使用教程) • [项目结构](#项目结构) • [核心算法](#核心算法)

</div>

---

## 📖 项目简介

本项目实现了一个完整的智能仓储数字孪生仿真系统，模拟真实仓库中 AGV（自动导引车）的调度和运行情况。通过可视化界面，可以直观地观察不同调度策略的效果，为仓储优化提供决策支持。

### 🎯 应用场景

- **仓储物流优化**：测试和优化 AGV 调度算法
- **算法验证**：验证路径规划、任务分配等算法的有效性
- **教学演示**：展示智能仓储系统的工作原理
- **性能分析**：对比不同调度策略的性能指标

---

## ✨ 功能特性

### 核心功能

- 🔲 **40×30 网格地图**：模拟真实仓库布局，包含货架区、通道、打包台、充电站
- 🚗 **多 AGV 协同**：支持 10 台 AGV 同时运行，状态机管理
- 📦 **智能订单系统**：自动生成订单，支持多种货物类型
- 🎯 **最优任务分配**：基于匈牙利算法的 AGV-订单匹配
- 🛤️ **A* 路径规划**：支持基础版和时间窗版本
- 🚦 **冲突避免**：时空预留表机制，防止 AGV 碰撞
- 🔧 **死锁恢复**：自动检测和解决死锁情况
- 📊 **实时统计**：订单完成率、平均等待时间、AGV 利用率等

### 可视化功能

- 🖥️ **实时渲染**：Pygame 驱动的 2D 可视化界面
- 📈 **性能仪表盘**：右侧面板显示关键性能指标
- 🗺️ **路径显示**：可切换显示 AGV 规划路径
- 🔥 **热力图**：显示仓库拥堵情况
- ⏱️ **时间窗可视化**：显示 AGV 预留的时空资源
- 🎮 **交互控制**：支持暂停、策略切换、速度调节

### 调度策略

- **简单策略**：基础的任务分配和路径规划
- **高级策略**：包含时间窗预留、死锁恢复、拥堵感知等优化

---

## 🚀 快速开始

### 系统要求

- Python 3.8 或更高版本
- Pygame 2.0 或更高版本
- Windows/Linux/macOS 操作系统

### 安装步骤

1. **克隆仓库**

```bash
git clone https://github.com/liuliuqiu378/zhinengcangchu.git
cd zhinengcangchu
```

2. **安装依赖**

```bash
pip install pygame
```

3. **运行仿真**

```bash
python main.py
```

### 验证安装

运行成功后，你将看到一个包含仓库地图和性能仪表盘的窗口：

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
└──────────────────────────────────┴──────────────┘
```

---

## 📚 使用教程

### 基本操作

#### 快捷键

| 按键 | 功能 |
|------|------|
| `SPACE` | 暂停/继续仿真 |
| `P` | 显示/隐藏 AGV 路径 |
| `H` | 显示/隐藏拥堵热力图 |
| `T` | 显示/隐藏时间窗预留 |
| `S` | 切换调度策略 |
| `1` | 正常速度 (1x) |
| `2` | 2 倍速 (2x) |
| `5` | 5 倍速 (5x) |
| `ESC` | 退出程序 |

#### 鼠标交互

- **左键拖拽 AGV**：手动移动 AGV 位置
- **观察 AGV 状态**：不同颜色表示不同状态

### AGV 状态说明

| 状态 | 颜色 | 说明 |
|------|------|------|
| 空闲 (IDLE) | 灰色 | 等待任务分配 |
| 前往取货 (MOVING_TO_PICK) | 蓝色 | 移动到货架位置 |
| 取货中 (PICKING) | 黄色 | 在货架处取货 |
| 前往打包 (MOVING_TO_PACK) | 绿色 | 运送货物到打包台 |
| 前往充电 (MOVING_TO_CHARGE) | 红色 | 电量不足，前往充电站 |
| 充电中 (CHARGING) | 紫色 | 在充电站充电 |
| 等待中 (WAITING) | 橙色 | 等待路径或资源 |
| 死锁恢复 (DEADLOCK_RECOVERY) | 粉色 | 正在解决死锁 |

### 性能指标

右侧仪表盘显示以下关键指标：

- **仿真时间**：当前仿真的运行时间
- **调度策略**：当前使用的调度算法
- **订单统计**：总订单数、已完成、待处理
- **完成率**：订单完成百分比
- **平均等待时间**：订单从生成到分配的平均时间
- **平均完成时间**：订单从生成到完成的平均时间
- **AGV 利用率**：AGV 工作时间占比
- **吞吐量**：单位时间内完成的订单数
- **冲突次数**：AGV 路径冲突检测次数
- **死锁次数**：检测到的死锁次数

---

## 📁 项目结构

```
zhinengcangchu/
├── main.py              # 程序入口和主循环
├── config.py            # 系统配置常量
├── models.py            # 数据模型定义
├── algorithms.py        # 核心算法实现
├── simulation.py        # 仿真引擎
├── renderer.py          # 渲染器
├── test.py              # 单元测试
├── map_config.json      # 地图配置文件
├── tutorial.md          # 详细教程文档
├── README.md            # 项目说明文档
└── .gitignore          # Git 忽略文件配置
```

### 文件说明

#### [main.py](main.py)
- 程序入口，初始化仿真引擎和渲染器
- 处理用户输入（键盘、鼠标事件）
- 主循环控制仿真更新和渲染

#### [config.py](config.py)
- 系统配置参数
- 窗口尺寸、网格设置、颜色定义
- AGV 参数、订单生成参数
- 调度策略常量

#### [models.py](models.py)
- **WarehouseMap**：仓库地图模型
- **AGV**：自动导引车模型
- **Order**：订单模型
- **OrderGenerator**：订单生成器
- 状态枚举定义

#### [algorithms.py](algorithms.py)
- **ReservationTable**：时空预留表
- **Scheduler**：任务调度器
- **A* 路径规划**：基础版和时间窗版
- **匈牙利算法**：最优任务分配
- **冲突检测**：多车冲突识别
- **死锁恢复**：死锁检测和解决

#### [simulation.py](simulation.py)
- **SimulationEngine**：仿真引擎核心
- **SimulationStats**：统计数据管理
- Tick 驱动的仿真循环
- 策略切换和性能监控

#### [renderer.py](renderer.py)
- **Renderer**：Pygame 渲染器
- 地图、AGV、订单的可视化
- 仪表盘和统计信息显示
- 路径、热力图、时间窗渲染

#### [map_config.json](map_config.json)
- 仓库布局配置
- 货架区域定义
- 打包台和充电站位置

---

## 🔬 核心算法

### 1. A* 路径规划

实现两种版本的 A* 算法：

#### 基础 A*
```python
def astar_base(start, goal, grid, agv_id=None)
```
- 经典 A* 算法，寻找最短路径
- 使用曼哈顿距离作为启发函数
- 考虑障碍物（货架）碰撞

#### 时间窗 A*
```python
def astar_timewindow(start, goal, grid, reservation_table, start_time, agv_id)
```
- 扩展 A* 算法，考虑时间维度
- 使用时空预留表避免冲突
- 支持等待和重新规划

### 2. 匈牙利算法

用于最优 AGV-订单分配：

```python
def hungarian_assignment(cost_matrix)
```
- 构建成本矩阵（距离、等待时间等）
- 求解最小成本匹配
- 实现任务的全局最优分配

### 3. 时空预留表

防止 AGV 碰撞的核心机制：

```python
class ReservationTable:
    def reserve(self, x, y, t, agv_id)
    def is_reserved(self, x, y, t, exclude_agv=None)
```
- 记录每个时空格子的占用情况
- 路径规划时检查预留冲突
- 支持预留清理和更新

### 4. 冲突检测与避免

#### 冲突类型
- **顶点冲突**：多车同时到达同一位置
- **边冲突**：多车同时交换位置
- **跟随冲突**：后车追上前车

#### 解决策略
- **等待**：在原地等待冲突消除
- **重新规划**：寻找替代路径
- **优先级调整**：根据任务紧急程度调整

### 5. 死锁恢复

自动检测和解决死锁：

```python
def detect_deadlock(agvs, reservation_table)
def resolve_deadlock(deadlock_agvs, grid, reservation_table)
```
- 构建等待图检测循环等待
- 识别死锁涉及的 AGV
- 执行撤退操作打破死锁

---

## ⚙️ 配置说明

### 地图配置 ([map_config.json](map_config.json))

```json
{
  "shelf_regions": [
    {"x": 2, "y": 1, "w": 5, "h": 2}
  ],
  "pack_stations": [
    {"x": 5, "y": 27}
  ],
  "charge_stations": [
    {"x": 35, "y": 5}
  ]
}
```

### 系统参数 ([config.py](config.py))

#### 窗口设置
```python
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900
MAP_WIDTH = 1000
```

#### 网格设置
```python
GRID_COLS = 40
GRID_ROWS = 30
CELL_SIZE = 25
```

#### AGV 参数
```python
DEFAULT_AGV_COUNT = 10
AGV_SPEED = 2.0  # 格子/秒
AGV_BATTERY_MAX = 100.0
AGV_BATTERY_LOW_THRESHOLD = 20.0
```

#### 仿真参数
```python
TICK_RATE = 60  # FPS
SIM_DT = 1.0 / TICK_RATE  # 仿真时间步长
RESERVATION_HORIZON = 100  # 预留时间窗长度
```

---

## 🧪 测试

运行单元测试：

```bash
python test.py
```

测试覆盖：
- 地图加载和验证
- AGV 状态转换
- 路径规划算法
- 任务分配算法
- 冲突检测机制

---

## 📊 性能优化

### 当前性能

- 支持 10 台 AGV 实时仿真
- 60 FPS 流畅渲染
- 低延迟路径规划

### 优化方向

- [ ] 多线程路径规划
- [ ] 空间分区加速冲突检测
- [ ] 批量订单处理
- [ ] GPU 加速渲染

---

## 🛠️ 开发计划

### 已完成 ✅

- [x] 基础仿真框架
- [x] A* 路径规划
- [x] 任务调度系统
- [x] 冲突避免机制
- [x] 可视化界面
- [x] 性能统计

### 进行中 🚧

- [ ] 更多调度策略
- [ ] 动态地图支持
- [ ] 历史数据回放

### 计划中 📋

- [ ] 机器学习优化
- [ ] 多层仓库支持
- [ ] Web 界面
- [ ] 分布式仿真

---

## 🤝 贡献指南

欢迎贡献代码、报告问题或提出建议！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 👥 作者

- **liuliuqiu378** - 项目维护者

---

## 🙏 致谢

- Pygame 社区提供的优秀游戏开发框架
- A* 算法和匈牙利算法的开源实现参考
- 智能仓储领域的研究者和实践者

---

## 📞 联系方式

- 项目主页：[https://github.com/liuliuqiu378/zhinengcangchu](https://github.com/liuliuqiu378/zhinengcangchu)
- 问题反馈：[Issues](https://github.com/liuliuqiu378/zhinengcangchu/issues)

---

<div align="center">

**如果这个项目对你有帮助，请给一个 ⭐️ Star！**

Made with ❤️ by liuliuqiu378

</div>