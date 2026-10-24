"""
file: NullSignal.py
description: 息屏工具
author: IYATT-yx
copyright:  Copyright (c) 2026 IYATT-yx.
            Licensed under the MIT License. See LICENSE file in the project root for full license information.
"""
import ctypes
import tkinter as tk
from ui import NullSignalApp

if __name__ == '__main__':
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    mainWindow = tk.Tk()
    app = NullSignalApp(mainWindow)
    mainWindow.mainloop()