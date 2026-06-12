#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能仓储系统演示录制工具

使用此脚本可以自动录制软件运行界面并生成GIF演示文件。

依赖安装：
pip install opencv-python numpy pyautogui imageio pillow

使用方法：
1. 运行此脚本
2. 在3秒倒计时后启动你的智能仓储系统
3. 录制30秒后自动停止并生成GIF
"""

import cv2
import numpy as np
import pyautogui
import time
import imageio
import os
from datetime import datetime


class DemoRecorder:
    """演示录制器"""

    def __init__(self, output_dir='docs', duration=30, fps=10, quality='medium'):
        """
        初始化录制器

        Args:
            output_dir: 输出目录
            duration: 录制时长（秒）
            fps: 帧率
            quality: 质量 ('low', 'medium', 'high')
        """
        self.output_dir = output_dir
        self.duration = duration
        self.fps = fps
        self.quality = quality

        # 质量设置
        self.quality_settings = {
            'low': {'scale': 600, 'fps': 8},
            'medium': {'scale': 800, 'fps': 10},
            'high': {'scale': 1000, 'fps': 12}
        }

        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

    def get_recording_region(self):
        """获取录制区域"""
        print("\n请选择录制方式：")
        print("1. 全屏录制")
        print("2. 自定义区域录制")
        print("3. 窗口录制")

        choice = input("请输入选择 (1-3): ").strip()

        if choice == '1':
            # 全屏录制
            screen_width, screen_height = pyautogui.size()
            return (0, 0, screen_width, screen_height)
        elif choice == '2':
            # 自定义区域
            print("\n请输入录制区域（像素）：")
            x = int(input("起始X坐标: "))
            y = int(input("起始Y坐标: "))
            width = int(input("宽度: "))
            height = int(input("高度: "))
            return (x, y, width, height)
        elif choice == '3':
            # 窗口录制
            print("\n请将鼠标移动到要录制的窗口上，3秒后自动捕获窗口位置...")
            time.sleep(3)
            x, y = pyautogui.position()
            print(f"捕获位置: ({x}, {y})")
            # 假设窗口大小，实际可以使用win32gui获取精确窗口
            width, height = 1000, 700
            return (x, y, width, height)
        else:
            print("无效选择，使用默认设置")
            return (100, 100, 1000, 700)

    def record_demo(self):
        """录制演示"""
        print("=" * 50)
        print("智能仓储系统演示录制工具")
        print("=" * 50)

        # 获取录制区域
        region = self.get_recording_region()
        x, y, width, height = region

        print(f"\n录制设置:")
        print(f"区域: ({x}, {y}, {width}, {height})")
        print(f"时长: {self.duration}秒")
        print(f"帧率: {self.fps} FPS")
        print(f"质量: {self.quality}")

        # 倒计时
        print("\n准备录制...")
        for i in range(3, 0, -1):
            print(f"{i}...")
            time.sleep(1)

        print("开始录制！请运行智能仓储系统展示功能")
        print("提示：可以展示AGV移动、订单完成、状态切换等功能")

        # 开始录制
        frames = []
        start_time = time.time()

        try:
            while time.time() - start_time < self.duration:
                # 截图
                screenshot = pyautogui.screenshot(region=region)

                # 转换为OpenCV格式
                frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                frames.append(frame)

                # 显示进度
                elapsed = time.time() - start_time
                progress = (elapsed / self.duration) * 100
                print(f"\r录制进度: {progress:.1f}% ({len(frames)} 帧)", end='')

                # 控制帧率
                time.sleep(1 / self.fps)

        except KeyboardInterrupt:
            print("\n用户中断录制")

        print(f"\n录制完成！共录制 {len(frames)} 帧")

        return frames

    def save_gif(self, frames, filename='demo.gif'):
        """保存为GIF"""
        if not frames:
            print("没有录制到任何帧！")
            return None

        output_path = os.path.join(self.output_dir, filename)

        print(f"\n正在生成GIF...")

        # 质量设置
        settings = self.quality_settings[self.quality]
        target_width = settings['scale']
        target_fps = settings['fps']

        # 调整帧大小
        print(f"调整图片大小到宽度 {target_width} 像素...")
        resized_frames = []
        for frame in frames:
            height, width = frame.shape[:2]
            ratio = target_width / width
            target_height = int(height * ratio)
            resized = cv2.resize(frame, (target_width, target_height))
            resized_frames.append(resized)

        # 保存GIF
        print(f"保存GIF到 {output_path}...")
        imageio.mimsave(
            output_path,
            resized_frames,
            fps=target_fps,
            loop=0  # 无限循环
        )

        # 获取文件大小
        file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB

        print(f"\n✅ GIF已成功保存！")
        print(f"文件路径: {output_path}")
        print(f"文件大小: {file_size:.2f} MB")
        print(f"帧数: {len(resized_frames)}")
        print(f"帧率: {target_fps} FPS")
        print(f"尺寸: {target_width}x{target_height}")

        return output_path

    def take_screenshots(self, count=3):
        """拍摄静态截图"""
        print("\n" + "=" * 50)
        print("静态截图拍摄")
        print("=" * 50)

        screenshots = []

        for i in range(count):
            print(f"\n准备拍摄第 {i+1} 张截图...")
            print("请设置好软件界面，5秒后自动拍摄...")

            for j in range(5, 0, -1):
                print(f"{j}...")
                time.sleep(1)

            # 截图
            screenshot = pyautogui.screenshot()
            screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

            # 保存
            filename = f"screenshot{i+1}.png"
            output_path = os.path.join(self.output_dir, filename)
            cv2.imwrite(output_path, screenshot)

            screenshots.append(output_path)
            print(f"✅ 第 {i+1} 张截图已保存: {output_path}")

            if i < count - 1:
                input("按Enter继续拍摄下一张...")

        return screenshots


def main():
    """主函数"""
    print("🎬 智能仓储系统演示录制工具\n")

    # 创建录制器
    recorder = DemoRecorder(
        output_dir='docs',
        duration=30,
        fps=10,
        quality='medium'
    )

    # 选择录制模式
    print("请选择录制模式：")
    print("1. 录制GIF演示")
    print("2. 拍摄静态截图")
    print("3. 两者都做")

    choice = input("请输入选择 (1-3): ").strip()

    if choice in ['1', '3']:
        # 录制GIF
        frames = recorder.record_demo()
        if frames:
            recorder.save_gif(frames, 'demo.gif')

    if choice in ['2', '3']:
        # 拍摄截图
        recorder.take_screenshots(3)

    print("\n" + "=" * 50)
    print("录制完成！")
    print("=" * 50)
    print("\n下一步：")
    print("1. 检查 docs/ 目录中的文件")
    print("2. 如果满意，提交到Git")
    print("3. 推送到GitHub，README.md会自动显示演示")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        input("\n按Enter退出...")