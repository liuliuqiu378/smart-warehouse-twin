# main.py - 入口和主循环

import sys
import os
import pygame

# 确保工作目录正确
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from config import TICK_RATE, SIM_DT, MAP_WIDTH, CELL_SIZE, CELL_EMPTY, CELL_SHELF
from simulation import SimulationEngine
from renderer import Renderer
from models import AGVState


def main():
    # 初始化仿真引擎和渲染器
    engine = SimulationEngine(
        map_config_path='map_config.json',
        agv_count=10,
        strategy='advanced'
    )
    renderer = Renderer()

    clock = pygame.time.Clock()
    running = True

    # 拖拽状态
    dragging_agv = None
    drag_offset = (0, 0)

    while running:
        # 事件处理
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    engine.toggle_pause()
                elif event.key == pygame.K_p:
                    engine.show_paths = not engine.show_paths
                elif event.key == pygame.K_h:
                    engine.show_heatmap = not engine.show_heatmap
                elif event.key == pygame.K_t:
                    engine.show_timewindow = not engine.show_timewindow
                elif event.key == pygame.K_s:
                    engine.switch_strategy()
                elif event.key == pygame.K_RIGHT:
                    engine.speed_up()
                elif event.key == pygame.K_LEFT:
                    engine.speed_down()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos

                # 检查仪表盘按钮
                if renderer.handle_button_click(event.pos, engine):
                    continue

                # 地图区域交互
                grid_pos = renderer.screen_to_grid(mx, my)
                if grid_pos:
                    gx, gy = grid_pos

                    if event.button == 1:  # 左键
                        # 检查是否点击了AGV（拖拽）
                        agv = engine.get_agv_at(gx, gy)
                        if agv:
                            dragging_agv = agv
                        else:
                            # 添加/移除障碍
                            if engine.warehouse_map.grid[gy][gx] == CELL_EMPTY:
                                engine.add_obstacle(gx, gy)
                                renderer.invalidate_map()
                            elif engine.warehouse_map.grid[gy][gx] == CELL_SHELF:
                                engine.remove_obstacle(gx, gy)
                                renderer.invalidate_map()

                    elif event.button == 3:  # 右键
                        # 创建紧急订单
                        engine.add_manual_order(gx, gy)

            elif event.type == pygame.MOUSEBUTTONUP:
                if dragging_agv:
                    mx, my = event.pos
                    grid_pos = renderer.screen_to_grid(mx, my)
                    if grid_pos:
                        engine.move_agv_to(dragging_agv, *grid_pos)
                    dragging_agv = None

            elif event.type == pygame.MOUSEMOTION:
                renderer.update_hover(event.pos)
                if dragging_agv:
                    mx, my = event.pos
                    grid_pos = renderer.screen_to_grid(mx, my)
                    if grid_pos:
                        # 实时更新AGV渲染位置
                        dragging_agv.render_x = (mx - renderer.grid_to_screen(0, 0)[0]) / CELL_SIZE
                        dragging_agv.render_y = (my - renderer.grid_to_screen(0, 0)[1]) / CELL_SIZE

        # 仿真步进
        engine.tick(SIM_DT)

        # 渲染
        renderer.render(engine)

        # 帧率控制
        clock.tick(TICK_RATE)

    pygame.quit()
    sys.exit()


if __name__ == '__main__':
    main()
