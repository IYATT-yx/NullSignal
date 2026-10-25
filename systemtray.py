"""
file: systemtray.py
description: 托盘图标
author: IYATT-yx
copyright:  Copyright (c) 2026 IYATT-yx.
            Licensed under the MIT License. See LICENSE file in the project root for full license information.
"""
import pystray
import tkinter as tk
from threading import Thread
from PIL import Image

class SystemTray(Thread):
    def __init__(self, root: tk.Tk, iconPath: str, name: str, extraMenuList: list[pystray.MenuItem] = []):
        """初始化系统托盘图标

        Args:
            root (tk.Tk): 主窗口
        """
        super().__init__()
        self.root = root
        self.extraMenuList = extraMenuList
        self.iconPath = iconPath
        self.name = name

        # 设置为守护线程
        self.daemon = True

    def showWindow(self):
        """显示主窗口"""
        self.root.after(0, self.root.deiconify)

    def stopSystemTray(self):
        self.icon.stop()

    def run(self):
        """启动托盘图标"""
        menu = pystray.Menu(
            pystray.MenuItem('打开窗口', self.showWindow, default=True),
            *self.extraMenuList
        )

        img = Image.open(self.iconPath)
        self.icon = pystray.Icon(self.name, img, self.name, menu)
        self.icon.run()