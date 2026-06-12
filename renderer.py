# renderer.py - Pygame 渲染层

import pygame
import math
from collections import deque

from config import (
    WINDOW_WIDTH, WINDOW_HEIGHT, MAP_WIDTH, MAP_HEIGHT,
    DASHBOARD_WIDTH, DASHBOARD_HEIGHT, CELL_SIZE,
    MAP_OFFSET_X, MAP_OFFSET_Y, GRID_COLS, GRID_ROWS,
    CELL_EMPTY, CELL_SHELF, CELL_PACK_STATION, CELL_CHARGE_STATION,
    COLOR_BG, COLOR_GRID_LINE, COLOR_EMPTY, COLOR_SHELF, COLOR_SHELF_BORDER,
    COLOR_PACK_STATION, COLOR_CHARGE_STATION, COLOR_AISLE,
    AGV_COLORS, AGV_SIZE,
    COLOR_STATUS_IDLE, COLOR_STATUS_MOVING, COLOR_STATUS_PICKING,
    COLOR_STATUS_CHARGING, COLOR_STATUS_WAITING, COLOR_STATUS_DEADLOCK,
    DASHBOARD_BG, DASHBOARD_CARD_BG, DASHBOARD_CARD_BORDER,
    DASHBOARD_TEXT, DASHBOARD_HIGHLIGHT, DASHBOARD_WARNING,
    DASHBOARD_DANGER, DASHBOARD_SUCCESS,
    DASHBOARD_BUTTON, DASHBOARD_BUTTON_HOVER, DASHBOARD_BUTTON_ACTIVE,
    HEATMAP_ALPHA, HEATMAP_MAX_VISITS,
    FONT_SIZE_SMALL, FONT_SIZE_MEDIUM, FONT_SIZE_LARGE, FONT_SIZE_TITLE,
    STRATEGY_SIMPLE, STRATEGY_ADVANCED, SPEED_MULTIPLIERS, GOODS_TYPES
)
from models import AGVState, OrderState


class Renderer:
    """主渲染器"""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("智能仓储 AGV 数字孪生仿真系统")

        # 字体
        self.font_small = pygame.font.SysFont(None, FONT_SIZE_SMALL)
        self.font_medium = pygame.font.SysFont(None, FONT_SIZE_MEDIUM)
        self.font_large = pygame.font.SysFont(None, FONT_SIZE_LARGE)
        self.font_title = pygame.font.SysFont(None, FONT_SIZE_TITLE)

        # 地图Surface（缓存）
        self.map_surface = None
        self.map_dirty = True

        # 热力图Surface
        self.heatmap_surface = pygame.Surface((MAP_WIDTH, MAP_HEIGHT), pygame.SRCALPHA)

        # 仪表盘按钮区域
        self.buttons = {}
        self.hovered_button = None

        # 拖拽状态
        self.dragging_agv = None

    def grid_to_screen(self, gx, gy):
        """网格坐标转屏幕坐标"""
        sx = MAP_OFFSET_X + gx * CELL_SIZE
        sy = MAP_OFFSET_Y + gy * CELL_SIZE
        return (sx, sy)

    def screen_to_grid(self, sx, sy):
        """屏幕坐标转网格坐标"""
        gx = (sx - MAP_OFFSET_X) // CELL_SIZE
        gy = (sy - MAP_OFFSET_Y) // CELL_SIZE
        if 0 <= gx < GRID_COLS and 0 <= gy < GRID_ROWS:
            return (int(gx), int(gy))
        return None

    def render(self, engine):
        """渲染一帧"""
        self.screen.fill(COLOR_BG)

        # 渲染地图
        self._draw_map(engine.warehouse_map)

        # 渲染热力图
        if engine.show_heatmap:
            self._draw_heatmap(engine.warehouse_map)

        # 渲染路径
        if engine.show_paths:
            self._draw_paths(engine.agvs)

        # 渲染AGV
        self._draw_agvs(engine.agvs)

        # 渲染订单标记
        self._draw_order_markers(engine.orders)

        # 渲染仪表盘
        self._draw_dashboard(engine)

        pygame.display.flip()

    def invalidate_map(self):
        """标记地图需要重绘"""
        self.map_dirty = True

    def _draw_map(self, warehouse_map):
        """绘制仓库地图"""
        if self.map_dirty or self.map_surface is None:
            self.map_surface = pygame.Surface((MAP_WIDTH, MAP_HEIGHT))
            self.map_surface.fill(COLOR_BG)

            for y in range(warehouse_map.rows):
                for x in range(warehouse_map.cols):
                    sx, sy = self.grid_to_screen(x, y)
                    cell = warehouse_map.grid[y][x]

                    if cell == CELL_SHELF:
                        # 根据货物类型着色
                        goods_idx = warehouse_map.shelf_goods.get((x, y), 0)
                        goods_info = GOODS_TYPES[goods_idx % len(GOODS_TYPES)]
                        base_color = COLOR_SHELF
                        # 混合货物颜色到货架底色
                        shelf_color = (
                            (base_color[0] + goods_info["color"][0]) // 2,
                            (base_color[1] + goods_info["color"][1]) // 2,
                            (base_color[2] + goods_info["color"][2]) // 2,
                        )
                        pygame.draw.rect(self.map_surface, shelf_color,
                                         (sx + 1, sy + 1, CELL_SIZE - 2, CELL_SIZE - 2))
                        pygame.draw.rect(self.map_surface, COLOR_SHELF_BORDER,
                                         (sx + 1, sy + 1, CELL_SIZE - 2, CELL_SIZE - 2), 1)
                        # 货物类型符号
                        symbol_text = self.font_small.render(goods_info["symbol"], True, (220, 220, 220))
                        self.map_surface.blit(symbol_text, (sx + CELL_SIZE // 2 - symbol_text.get_width() // 2,
                                                              sy + CELL_SIZE // 2 - symbol_text.get_height() // 2))
                    elif cell == CELL_PACK_STATION:
                        pygame.draw.rect(self.map_surface, COLOR_PACK_STATION,
                                         (sx + 1, sy + 1, CELL_SIZE - 2, CELL_SIZE - 2))
                        # 绘制P标记
                        text = self.font_small.render("P", True, (255, 255, 255))
                        self.map_surface.blit(text, (sx + CELL_SIZE // 2 - text.get_width() // 2,
                                                      sy + CELL_SIZE // 2 - text.get_height() // 2))
                    elif cell == CELL_CHARGE_STATION:
                        pygame.draw.rect(self.map_surface, COLOR_CHARGE_STATION,
                                         (sx + 1, sy + 1, CELL_SIZE - 2, CELL_SIZE - 2))
                        text = self.font_small.render("C", True, (255, 255, 255))
                        self.map_surface.blit(text, (sx + CELL_SIZE // 2 - text.get_width() // 2,
                                                      sy + CELL_SIZE // 2 - text.get_height() // 2))
                    else:
                        pygame.draw.rect(self.map_surface, COLOR_EMPTY,
                                         (sx + 1, sy + 1, CELL_SIZE - 2, CELL_SIZE - 2))

            # 绘制网格线
            for x in range(warehouse_map.cols + 1):
                sx = MAP_OFFSET_X + x * CELL_SIZE
                pygame.draw.line(self.map_surface, COLOR_GRID_LINE,
                                 (sx, MAP_OFFSET_Y), (sx, MAP_OFFSET_Y + warehouse_map.rows * CELL_SIZE))
            for y in range(warehouse_map.rows + 1):
                sy = MAP_OFFSET_Y + y * CELL_SIZE
                pygame.draw.line(self.map_surface, COLOR_GRID_LINE,
                                 (MAP_OFFSET_X, sy), (MAP_OFFSET_X + warehouse_map.cols * CELL_SIZE, sy))

            self.map_dirty = False

        self.screen.blit(self.map_surface, (0, 0))

    def _draw_heatmap(self, warehouse_map):
        """绘制热力图叠加层"""
        self.heatmap_surface.fill((0, 0, 0, 0))

        max_val = max(max(row) for row in warehouse_map.heatmap) or 1

        for y in range(warehouse_map.rows):
            for x in range(warehouse_map.cols):
                val = warehouse_map.heatmap[y][x]
                if val > 0:
                    intensity = min(val / HEATMAP_MAX_VISITS, 1.0)
                    r = int(255 * intensity)
                    g = int(255 * (1 - intensity))
                    sx, sy = self.grid_to_screen(x, y)
                    pygame.draw.rect(self.heatmap_surface, (r, g, 0, HEATMAP_ALPHA),
                                     (sx, sy, CELL_SIZE, CELL_SIZE))

        self.screen.blit(self.heatmap_surface, (0, 0))

    def _draw_paths(self, agvs):
        """绘制AGV路径"""
        path_surface = pygame.Surface((MAP_WIDTH, MAP_HEIGHT), pygame.SRCALPHA)

        for agv in agvs:
            if agv.path and len(agv.path) > 0:
                # 从当前位置到路径起点
                points = [(agv.render_x, agv.render_y)]
                for px, py in agv.path:
                    points.append((px, py))

                if len(points) >= 2:
                    # 转换为屏幕坐标
                    screen_points = []
                    for px, py in points:
                        sx = MAP_OFFSET_X + px * CELL_SIZE + CELL_SIZE // 2
                        sy = MAP_OFFSET_Y + py * CELL_SIZE + CELL_SIZE // 2
                        screen_points.append((sx, sy))

                    color = (*agv.color[:3],)  # 确保是3元组
                    if len(screen_points) >= 2:
                        pygame.draw.lines(path_surface, (*color, 120), False, screen_points, 2)

        self.screen.blit(path_surface, (0, 0))

    def _draw_agvs(self, agvs):
        """绘制AGV"""
        for agv in agvs:
            # 计算屏幕位置
            sx = MAP_OFFSET_X + agv.render_x * CELL_SIZE + CELL_SIZE // 2
            sy = MAP_OFFSET_Y + agv.render_y * CELL_SIZE + CELL_SIZE // 2

            # 状态颜色
            status_color = self._get_status_color(agv.state)

            # 绘制AGV主体（圆角矩形）
            half = AGV_SIZE // 2
            rect = pygame.Rect(sx - half, sy - half, AGV_SIZE, AGV_SIZE)
            pygame.draw.rect(self.screen, agv.color, rect, border_radius=4)
            pygame.draw.rect(self.screen, status_color, rect, 2, border_radius=4)

            # 绘制ID
            id_text = self.font_small.render(str(agv.id), True, (0, 0, 0))
            self.screen.blit(id_text, (sx - id_text.get_width() // 2,
                                        sy - id_text.get_height() // 2))

            # 绘制电量条
            bar_width = AGV_SIZE
            bar_height = 3
            bar_x = sx - half
            bar_y = sy - half - 5
            battery_ratio = agv.battery / 100.0

            pygame.draw.rect(self.screen, (60, 60, 60), (bar_x, bar_y, bar_width, bar_height))
            bar_color = DASHBOARD_SUCCESS if battery_ratio > 0.3 else (
                DASHBOARD_WARNING if battery_ratio > 0.15 else DASHBOARD_DANGER)
            pygame.draw.rect(self.screen, bar_color,
                             (bar_x, bar_y, int(bar_width * battery_ratio), bar_height))

            # 载货标识 + 货物类型
            if agv.current_order:
                goods_idx = agv.current_order.goods_type
                goods_info = GOODS_TYPES[goods_idx % len(GOODS_TYPES)]
                goods_color = goods_info["color"]

                if agv.state in (AGVState.MOVING_TO_PACK, AGVState.PICKING):
                    # 已取货：显示货物色块
                    pygame.draw.rect(self.screen, goods_color,
                                     (sx + half - 6, sy - half, 6, 6))
                elif agv.state == AGVState.MOVING_TO_PICK:
                    # 前往取货：显示目标货物类型小圆点
                    pygame.draw.circle(self.screen, goods_color, (sx + half, sy - half), 3)
                    pygame.draw.circle(self.screen, (255, 255, 255), (sx + half, sy - half), 3, 1)

            # 绘制任务目标标记（在目标位置闪烁）
            if agv.current_order:
                if agv.state == AGVState.MOVING_TO_PICK:
                    # 取货目标：在取货点画闪烁框
                    target_sx = MAP_OFFSET_X + agv.current_order.pick_x * CELL_SIZE + CELL_SIZE // 2
                    target_sy = MAP_OFFSET_Y + agv.current_order.pick_y * CELL_SIZE + CELL_SIZE // 2
                    goods_idx = agv.current_order.goods_type
                    goods_color = GOODS_TYPES[goods_idx % len(GOODS_TYPES)]["color"]
                    if int(pygame.time.get_ticks() / 400) % 2 == 0:
                        pygame.draw.circle(self.screen, goods_color, (target_sx, target_sy), 5, 2)
                        # 连线到AGV
                        pygame.draw.line(self.screen, (*goods_color, ), (sx, sy), (target_sx, target_sy), 1)
                elif agv.state == AGVState.MOVING_TO_PACK:
                    # 送货目标：在打包台画闪烁框
                    target_sx = MAP_OFFSET_X + agv.current_order.pack_x * CELL_SIZE + CELL_SIZE // 2
                    target_sy = MAP_OFFSET_Y + agv.current_order.pack_y * CELL_SIZE + CELL_SIZE // 2
                    goods_idx = agv.current_order.goods_type
                    goods_color = GOODS_TYPES[goods_idx % len(GOODS_TYPES)]["color"]
                    if int(pygame.time.get_ticks() / 400) % 2 == 0:
                        pygame.draw.rect(self.screen, goods_color,
                                         (target_sx - 6, target_sy - 6, 12, 12), 2)

    def _get_status_color(self, state):
        """获取状态对应的颜色"""
        colors = {
            AGVState.IDLE: COLOR_STATUS_IDLE,
            AGVState.MOVING_TO_PICK: COLOR_STATUS_MOVING,
            AGVState.MOVING_TO_PACK: COLOR_STATUS_MOVING,
            AGVState.MOVING_TO_CHARGE: COLOR_STATUS_CHARGING,
            AGVState.PICKING: COLOR_STATUS_PICKING,
            AGVState.CHARGING: COLOR_STATUS_CHARGING,
            AGVState.WAITING: COLOR_STATUS_WAITING,
            AGVState.DEADLOCK_RECOVERY: COLOR_STATUS_DEADLOCK,
            AGVState.RETREAT: (180, 180, 100),
        }
        return colors.get(state, COLOR_STATUS_IDLE)

    def _draw_order_markers(self, orders):
        """绘制订单标记"""
        for order in orders:
            if order.state == OrderState.PENDING:
                sx, sy = self.grid_to_screen(order.pick_x, order.pick_y)
                goods_color = GOODS_TYPES[order.goods_type % len(GOODS_TYPES)]["color"]
                # 闪烁效果
                if int(pygame.time.get_ticks() / 500) % 2 == 0:
                    pygame.draw.circle(self.screen, goods_color,
                                       (sx + CELL_SIZE // 2, sy + CELL_SIZE // 2), 5)
                    pygame.draw.circle(self.screen, (255, 255, 255),
                                       (sx + CELL_SIZE // 2, sy + CELL_SIZE // 2), 5, 1)

    def _draw_dashboard(self, engine):
        """绘制右侧仪表盘"""
        dx = MAP_WIDTH  # 仪表盘起始X
        panel_rect = pygame.Rect(dx, 0, DASHBOARD_WIDTH, DASHBOARD_HEIGHT)
        pygame.draw.rect(self.screen, DASHBOARD_BG, panel_rect)
        pygame.draw.line(self.screen, DASHBOARD_CARD_BORDER, (dx, 0), (dx, DASHBOARD_HEIGHT), 2)

        y = 15

        # 标题
        title = self.font_title.render("AGV Digital Twin", True, DASHBOARD_HIGHLIGHT)
        self.screen.blit(title, (dx + DASHBOARD_WIDTH // 2 - title.get_width() // 2, y))
        y += 40

        # 仿真时间
        time_text = self.font_medium.render(
            f"Sim Time: {engine.sim_time:.1f}s", True, DASHBOARD_TEXT)
        self.screen.blit(time_text, (dx + 20, y))
        y += 30

        # 策略标识
        strategy_name = "Advanced (Hungarian+TW)" if engine.strategy == STRATEGY_ADVANCED else "Simple (Random+A*)"
        strategy_color = DASHBOARD_SUCCESS if engine.strategy == STRATEGY_ADVANCED else DASHBOARD_WARNING
        strategy_text = self.font_medium.render(f"Strategy: {strategy_name}", True, strategy_color)
        self.screen.blit(strategy_text, (dx + 20, y))
        y += 30

        # 货物图例
        legend_label = self.font_small.render("Goods:", True, DASHBOARD_TEXT)
        self.screen.blit(legend_label, (dx + 20, y))
        lx = dx + 70
        for i, goods in enumerate(GOODS_TYPES):
            if lx + 45 > dx + DASHBOARD_WIDTH - 10:
                lx = dx + 70
                y += 16
            pygame.draw.rect(self.screen, goods["color"], (lx, y + 2, 10, 10))
            gtext = self.font_small.render(goods["symbol"], True, DASHBOARD_TEXT)
            self.screen.blit(gtext, (lx + 12, y))
            lx += 45
        y += 22

        # 统计卡片
        y = self._draw_stat_card(dx + 15, y, "Completed Orders",
                                  str(engine.stats.completed_orders), DASHBOARD_SUCCESS)
        y = self._draw_stat_card(dx + 15, y, "Pending Orders",
                                  str(engine.stats.pending_orders), DASHBOARD_WARNING)
        y = self._draw_stat_card(dx + 15, y, "Avg Wait Time",
                                  f"{engine.stats.avg_wait_time:.1f}s", DASHBOARD_HIGHLIGHT)
        y = self._draw_stat_card(dx + 15, y, "Avg Complete Time",
                                  f"{engine.stats.avg_complete_time:.1f}s", DASHBOARD_HIGHLIGHT)
        y = self._draw_stat_card(dx + 15, y, "AGV Utilization",
                                  f"{engine.stats.agv_utilization * 100:.1f}%", DASHBOARD_SUCCESS)
        y = self._draw_stat_card(dx + 15, y, "Conflicts",
                                  str(engine.stats.conflict_count), DASHBOARD_DANGER)
        y = self._draw_stat_card(dx + 15, y, "Deadlocks",
                                  str(engine.stats.deadlock_count), DASHBOARD_DANGER)
        y += 10

        # 吞吐量图表
        y = self._draw_throughput_chart(dx + 15, y, engine.stats.throughput_history)
        y += 15

        # AGV状态列表
        y = self._draw_agv_status_list(dx + 15, y, engine.agvs)
        y += 15

        # 控制按钮
        y = self._draw_controls(dx + 15, y, engine)
        y += 15

        # 快捷键提示
        y = self._draw_shortcuts(dx + 15, y)

    def _draw_stat_card(self, x, y, label, value, color):
        """绘制统计卡片"""
        card_w = DASHBOARD_WIDTH - 30
        card_h = 42
        card_rect = pygame.Rect(x, y, card_w, card_h)
        pygame.draw.rect(self.screen, DASHBOARD_CARD_BG, card_rect, border_radius=5)
        pygame.draw.rect(self.screen, DASHBOARD_CARD_BORDER, card_rect, 1, border_radius=5)

        label_text = self.font_small.render(label, True, DASHBOARD_TEXT)
        self.screen.blit(label_text, (x + 10, y + 5))

        value_text = self.font_large.render(value, True, color)
        self.screen.blit(value_text, (x + card_w - value_text.get_width() - 10, y + 8))

        return y + card_h + 5

    def _draw_throughput_chart(self, x, y, throughput_history):
        """绘制吞吐量折线图"""
        chart_w = DASHBOARD_WIDTH - 30
        chart_h = 80
        chart_rect = pygame.Rect(x, y, chart_w, chart_h)
        pygame.draw.rect(self.screen, DASHBOARD_CARD_BG, chart_rect, border_radius=5)
        pygame.draw.rect(self.screen, DASHBOARD_CARD_BORDER, chart_rect, 1, border_radius=5)

        label = self.font_small.render("Throughput (orders/s)", True, DASHBOARD_TEXT)
        self.screen.blit(label, (x + 10, y + 5))

        if len(throughput_history) >= 2:
            max_val = max(throughput_history) or 1
            points = []
            for i, val in enumerate(throughput_history):
                px = x + 10 + (i / max(len(throughput_history) - 1, 1)) * (chart_w - 20)
                py = y + chart_h - 10 - (val / max_val) * (chart_h - 25)
                points.append((px, py))

            if len(points) >= 2:
                pygame.draw.lines(self.screen, DASHBOARD_HIGHLIGHT, False, points, 2)

        return y + chart_h + 5

    def _draw_agv_status_list(self, x, y, agvs):
        """绘制AGV状态列表"""
        label = self.font_medium.render("AGV Status", True, DASHBOARD_HIGHLIGHT)
        self.screen.blit(label, (x, y))
        y += 25

        for agv in agvs[:15]:  # 最多显示15个
            status_color = self._get_status_color(agv.state)
            state_name = {
                AGVState.IDLE: "Idle",
                AGVState.MOVING_TO_PICK: "ToPick",
                AGVState.MOVING_TO_PACK: "ToPack",
                AGVState.MOVING_TO_CHARGE: "ToChg",
                AGVState.PICKING: "Picking",
                AGVState.CHARGING: "Chg",
                AGVState.WAITING: "Wait",
                AGVState.DEADLOCK_RECOVERY: "Deadlock",
                AGVState.RETREAT: "Retreat",
            }.get(agv.state, "?")

            # AGV颜色方块
            pygame.draw.rect(self.screen, agv.color, (x, y + 2, 12, 12), border_radius=2)
            # 状态指示点
            pygame.draw.circle(self.screen, status_color, (x + 18, y + 8), 4)

            # 货物信息
            goods_str = ""
            if agv.current_order:
                goods_name = GOODS_TYPES[agv.current_order.goods_type % len(GOODS_TYPES)]["name"]
                if agv.state == AGVState.MOVING_TO_PICK:
                    goods_str = f" ->{goods_name}"
                elif agv.state in (AGVState.MOVING_TO_PACK, AGVState.PICKING):
                    goods_str = f" [{goods_name}]->P"
                # 货物颜色小方块
                goods_color = GOODS_TYPES[agv.current_order.goods_type % len(GOODS_TYPES)]["color"]
                pygame.draw.rect(self.screen, goods_color, (x + 18, y + 2, 6, 6))

            text = self.font_small.render(
                f"#{agv.id} {state_name}{goods_str}", True, DASHBOARD_TEXT)
            self.screen.blit(text, (x + 28, y))

            y += 18

        return y

    def _draw_controls(self, x, y, engine):
        """绘制控制按钮"""
        # 速度控制
        label = self.font_medium.render("Speed Control", True, DASHBOARD_HIGHLIGHT)
        self.screen.blit(label, (x, y))
        y += 25

        speed_names = ["Pause", "1x", "2x", "5x", "10x"]
        btn_w = 65
        btn_h = 28
        for i, name in enumerate(speed_names):
            bx = x + i * (btn_w + 5)
            btn_rect = pygame.Rect(bx, y, btn_w, btn_h)

            is_active = (i == engine.speed_index) or (i == 0 and engine.paused)
            is_hovered = self.hovered_button == f"speed_{i}"

            if is_active:
                color = DASHBOARD_BUTTON_ACTIVE
            elif is_hovered:
                color = DASHBOARD_BUTTON_HOVER
            else:
                color = DASHBOARD_BUTTON

            pygame.draw.rect(self.screen, color, btn_rect, border_radius=4)
            text = self.font_small.render(name, True, (255, 255, 255))
            self.screen.blit(text, (bx + btn_w // 2 - text.get_width() // 2,
                                     y + btn_h // 2 - text.get_height() // 2))
            self.buttons[f"speed_{i}"] = btn_rect

        y += btn_h + 15

        # 策略切换按钮
        strategy_label = "Switch to Simple" if engine.strategy == STRATEGY_ADVANCED else "Switch to Advanced"
        btn_rect = pygame.Rect(x, y, DASHBOARD_WIDTH - 30, 32)
        is_hovered = self.hovered_button == "strategy"
        color = DASHBOARD_BUTTON_HOVER if is_hovered else DASHBOARD_BUTTON
        pygame.draw.rect(self.screen, color, btn_rect, border_radius=5)
        text = self.font_medium.render(strategy_label, True, (255, 255, 255))
        self.screen.blit(text, (x + (DASHBOARD_WIDTH - 30) // 2 - text.get_width() // 2,
                                 y + 16 - text.get_height() // 2))
        self.buttons["strategy"] = btn_rect

        y += 42

        # 显示切换按钮
        toggle_labels = [
            ("show_paths", "Paths", engine.show_paths),
            ("show_heatmap", "Heatmap", engine.show_heatmap),
            ("show_timewindow", "TimeWin", engine.show_timewindow),
        ]

        btn_w2 = (DASHBOARD_WIDTH - 40) // 3
        for i, (key, label_text, active) in enumerate(toggle_labels):
            bx = x + i * (btn_w2 + 5)
            btn_rect = pygame.Rect(bx, y, btn_w2, 28)
            is_hovered = self.hovered_button == key
            color = DASHBOARD_BUTTON_ACTIVE if active else (
                DASHBOARD_BUTTON_HOVER if is_hovered else DASHBOARD_BUTTON)
            pygame.draw.rect(self.screen, color, btn_rect, border_radius=4)
            text = self.font_small.render(label_text, True, (255, 255, 255))
            self.screen.blit(text, (bx + btn_w2 // 2 - text.get_width() // 2,
                                     y + 14 - text.get_height() // 2))
            self.buttons[key] = btn_rect

        y += 38

        return y

    def _draw_shortcuts(self, x, y):
        """绘制快捷键提示"""
        shortcuts = [
            "P: Paths  H: Heatmap  T: TimeWin",
            "Space: Pause  S: Strategy",
            "Left/Right: Speed",
            "Left-click: Add obstacle",
            "Right-click: Add order",
            "Drag AGV to move (debug)",
        ]
        for text_str in shortcuts:
            text = self.font_small.render(text_str, True, (120, 120, 130))
            self.screen.blit(text, (x, y))
            y += 16

        return y

    def handle_button_click(self, pos, engine):
        """处理按钮点击"""
        for name, rect in self.buttons.items():
            if rect.collidepoint(pos):
                if name.startswith("speed_"):
                    idx = int(name.split("_")[1])
                    if idx == 0:
                        engine.paused = not engine.paused
                    else:
                        engine.paused = False
                        engine.speed_index = idx
                elif name == "strategy":
                    engine.switch_strategy()
                elif name == "show_paths":
                    engine.show_paths = not engine.show_paths
                elif name == "show_heatmap":
                    engine.show_heatmap = not engine.show_heatmap
                elif name == "show_timewindow":
                    engine.show_timewindow = not engine.show_timewindow
                return True
        return False

    def update_hover(self, pos):
        """更新鼠标悬停状态"""
        self.hovered_button = None
        for name, rect in self.buttons.items():
            if rect.collidepoint(pos):
                self.hovered_button = name
                break
