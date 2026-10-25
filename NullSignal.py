"""
file: NullSignal.py
description: 息屏工具
author: IYATT-yx
copyright:  Copyright (c) 2026 IYATT-yx.
            Licensed under the MIT License. See LICENSE file in the project root for full license information.
"""
import ctypes
import tkinter as tk
from tkinter import messagebox
import sys
import os
import datetime
import traceback

from ui import NullSignalApp

def checkSingleInstance(mutexName="NullSignal_Unique_Mutex_IYATT"):
    """使用 Windows 互斥体 (Mutex) 检查单实例运行"""
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW(None, False, mutexName)
    if kernel32.GetLastError() == 183:
        return False
    return True

if __name__ == '__main__':
    try:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        if not checkSingleInstance():
            tempRoot = tk.Tk()
            tempRoot.withdraw()
            messagebox.showwarning("提示", "程序已经在运行中，请查看右下角系统托盘图标！")
            tempRoot.destroy()
            sys.exit(0)

        mainWindow = tk.Tk()
        hideWindow = True if '--hide' in sys.argv else False
        app = NullSignalApp(mainWindow, hidewindow=hideWindow)
        mainWindow.mainloop()
    except Exception as e:
        try:
            log_path = os.path.join(os.path.dirname(sys.argv[0]), "NullSignalError.log")
            with open(log_path, "w", encoding="utf-8") as f:
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"Crash Time: {current_time}\n")
                f.write(traceback.format_exc())
                f.write("-" * 40 + "\n")
        except Exception:
            pass
        
        # 尝试弹窗提示用户（如果 tkinter 还能用）
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("程序崩溃", f"发生严重错误，已生成 error.log 文件。\n错误信息: {str(e)}")
            root.destroy()
        except Exception:
            pass
        
        sys.exit(1)