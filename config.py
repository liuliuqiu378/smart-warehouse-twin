# config.py - 系统配置常量

# ==================== 窗口 ====================
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 900
MAP_WIDTH = 1000
MAP_HEIGHT = 900
DASHBOARD_WIDTH = 400
DASHBOARD_HEIGHT = 900

# ==================== 网格 ====================
GRID_COLS = 40
GRID_ROWS = 30
CELL_SIZE = 25  # min(1000/40, 900/30)

# 地图偏移（居中显示）
MAP_OFFSET_X = (MAP_WIDTH - GRID_COLS * CELL_SIZE) // 2
MAP_OFFSET_Y = (MAP_HEIGHT - GRID_ROWS * CELL_SIZE) // 2

# ==================== 格子类型 ====================
CELL_EMPTY = 0
CELL_SHELF = 1
CELL_PACK_STATION = 2
CELL_CHARGE_STATION = 3

# ==================== 货物类型 ====================
GOODS_TYPES = [
    {"name": "电子", "color": (100, 150, 255), "symbol": "E"},
    {"name": "服装", "color": (255, 130, 170), "symbol": "C"},
    {"name": "食品", "color": (130, 220, 130), "symbol": "F"},
    {"name": "日用", "color": (220, 200, 100), "symbol": "D"},
    {"name": "医药", "color": (200, 130, 255), "symbol": "M"},
    {"name": "图书", "color": (180, 140, 100), "symbol": "B"},
    {"name": "玩具", "color": (255, 180, 80), "symbol": "T"},
    {"name": "运动", "color": (100, 220, 220), "symbol": "S"},
]

# ==================== 颜色 ====================
COLOR_BG = (30, 30, 35)
COLOR_GRID_LINE = (50, 50, 55)
COLOR_EMPTY = (55, 55, 60)
COLOR_SHELF = (40, 50, 70)
COLOR_SHELF_BORDER = (55, 65, 90)
COLOR_PACK_STATION = (50, 120, 70)
COLOR_CHARGE_STATION = (160, 140, 40)
COLOR_AISLE = (70, 70, 75)

# AGV 颜色
AGV_COLORS = [
    (255, 140, 50),   # 橙
    (50, 200, 200),   # 青
    (100, 220, 100),  # 绿
    (220, 100, 100),  # 红
    (180, 130, 220),  # 紫
    (220, 200, 80),   # 黄
    (100, 150, 220),  # 蓝
    (220, 130, 180),  # 粉
    (150, 200, 150),  # 浅绿
    (200, 150, 100),  # 棕
    (130, 180, 220),  # 浅蓝
    (220, 180, 130),  # 浅橙
    (180, 220, 130),  # 青柠
    (130, 130, 220),  # 靛蓝
    (220, 130, 130),  # 鲑鱼
    (170, 170, 100),  # 橄榄
    (100, 170, 170),  # 水鸭
    (170, 100, 170),  # 紫红
    (200, 200, 100),  # 卡其
    (100, 200, 150),  # 薄荷
]

# 状态指示色
COLOR_STATUS_IDLE = (100, 200, 100)
COLOR_STATUS_MOVING = (50, 200, 200)
COLOR_STATUS_PICKING = (220, 200, 80)
COLOR_STATUS_CHARGING = (180, 160, 50)
COLOR_STATUS_WAITING = (220, 80, 80)
COLOR_STATUS_DEADLOCK = (255, 50, 50)

# ==================== AGV 参数 ====================
DEFAULT_AGV_COUNT = 10
AGV_SPEED = 3.0          # 格/秒
AGV_BATTERY_MAX = 100.0
AGV_BATTERY_DRAIN_MOVE = 0.08   # 每格消耗
AGV_BATTERY_DRAIN_IDLE = 0.005  # 每tick消耗
AGV_BATTERY_CHARGE_RATE = 0.5   # 每tick充电
AGV_BATTERY_LOW_THRESHOLD = 20.0
AGV_PICK_TIME = 2.0      # 取货耗时（秒）
AGV_SIZE = CELL_SIZE - 6  # 绘制尺寸

# ==================== 订单参数 ====================
ORDER_INTERVAL_MEAN = 1.5   # 泊松分布均值（秒）
MAX_PENDING_ORDERS = 50

# ==================== 仿真 ====================
TICK_RATE = 60
SIM_DT = 1.0 / TICK_RATE
SPEED_MULTIPLIERS = [0, 1, 2, 5, 10]

# ==================== 路径规划 ====================
PATH_MAX_LENGTH = 300
RESERVATION_HORIZON = 150
ASTAR_TIMEOUT_MS = 10

# ==================== 调度策略 ====================
STRATEGY_SIMPLE = "simple"       # 随机分配 + 简单A*
STRATEGY_ADVANCED = "advanced"   # 匈牙利分配 + 时间窗A*

# ==================== 仪表盘 ====================
DASHBOARD_BG = (25, 25, 30)
DASHBOARD_CARD_BG = (40, 40, 48)
DASHBOARD_CARD_BORDER = (60, 60, 70)
DASHBOARD_TEXT = (200, 200, 210)
DASHBOARD_HIGHLIGHT = (100, 200, 255)
DASHBOARD_WARNING = (255, 180, 50)
DASHBOARD_DANGER = (255, 80, 80)
DASHBOARD_SUCCESS = (80, 200, 120)
DASHBOARD_BUTTON = (50, 60, 80)
DASHBOARD_BUTTON_HOVER = (70, 80, 110)
DASHBOARD_BUTTON_ACTIVE = (80, 130, 200)

# ==================== 热力图 ====================
HEATMAP_ALPHA = 80
HEATMAP_MAX_VISITS = 50

# ==================== 字体 ====================
FONT_NAME = None  # 使用默认字体
FONT_SIZE_SMALL = 14
FONT_SIZE_MEDIUM = 18
FONT_SIZE_LARGE = 24
FONT_SIZE_TITLE = 28

# ==================== 交互 ====================
CLICK_ADD_OBSTACLE = 1   # 左键
CLICK_ADD_ORDER = 3      # 右键
CLICK_DRAG_AGV = 1       # 左键拖拽

# 键盘快捷键
KEY_TOGGLE_PATHS = pygame_key_p = 112  # P
KEY_TOGGLE_HEATMAP = pygame_key_h = 104  # H
KEY_TOGGLE_TIMEWINDOW = pygame_key_t = 116  # T
KEY_SPEED_UP = pygame_key_right = 275
KEY_SPEED_DOWN = pygame_key_left = 276
KEY_PAUSE = pygame_key_space = 32
KEY_SWITCH_STRATEGY = pygame_key_s = 115
