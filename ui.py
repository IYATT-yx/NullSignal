"""
file: ui.py
description: GUI 主界面 & 交互逻辑
author: IYATT-yx
copyright:  Copyright (c) 2026 IYATT-yx.
            Licensed under the MIT License. See LICENSE file in the project root for full license information.
"""
import os
import threading
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import pystray
import keyboard

from buildtime import buildTime
from config import getIconPath
from win32utils import verifyDriverFiles, executeBlackoutSequence
from powerchecker import fetchPowerRequests
from autostart import AutoStartManager
from systemtray import SystemTray

class NullSignalApp:
    def __init__(self, root, hidewindow: bool=False):
        self.root = root
        self.name = 'NullSignal'
        self.fullName = 'NullSignal 息屏工具'
        self.root.title(f'{self.fullName} by IYATT-yx {buildTime}')
        self.root.geometry('560x460')
        self.root.resizable(True, True)

        # 初始化自启动设置
        AutoStartManager.init(projectName=self.name, args=['--hide'], mode=AutoStartManager.MODE_TASK_SCHEDULER)

        # 点击关闭隐藏窗口
        self.root.protocol("WM_DELETE_WINDOW", lambda: self.root.withdraw())

        self.iconPath = getIconPath()
        self.setupWindowIcon()

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        self.isRunningBlackout = False

        # 主界面
        self.initUi()
        # 托盘
        self.systemTray = None
        self.initSystemTray()
        self.systemTray.start()
        
        self.refreshBlockerStatus()

        # 隐藏窗口
        if hidewindow:
            self.root.withdraw()

        # 注册快捷键
        keyboard.add_hotkey('ctrl+shift+alt+a', lambda: self.root.after(0, self.sleepButton.invoke))

    def setupWindowIcon(self):
        '''设置 Tkinter 窗口和任务栏图标'''
        if os.path.exists(self.iconPath):
            try:
                self.root.iconbitmap(self.iconPath)
            except Exception as e:
                print(f'窗口图标加载失败: {e}')

    def updateProgressText(self, text, color='orange'):
        '''线程安全的状态文本更新方法'''
        self.root.after(0, lambda: self.statusLabel.config(text=text, foreground=color))

    def initSystemTray(self):
        enumList = [
            pystray.MenuItem('触发硬件黑屏(Ctrl+Shift+Alt+A)', self.sleepButton.invoke),
            pystray.MenuItem('退出程序', self.quitApp)
        ]
        self.systemTray = SystemTray(self.root, self.iconPath, self.fullName, enumList)

    def quitApp(self):
        if self.systemTray is not None:
            self.systemTray.stopSystemTray()
        self.root.after(0, self.root.destroy)

    def initUi(self):
        # 顶栏控制面板
        self.topPanel = ttk.Frame(self.root, padding=10)
        self.topPanel.grid(row=0, column=0, sticky='ew')

        self.sleepButton = ttk.Button(self.topPanel, text=' 触发硬件黑屏(Ctrl+Shift+Alt+A) ', command=self.triggerBlackout)
        self.sleepButton.pack(side=tk.LEFT, padx=5)

        self.refreshButton = ttk.Button(self.topPanel, text='刷新阻止程序', command=self.refreshBlockerStatus)
        self.refreshButton.pack(side=tk.LEFT, padx=5)

        self.statusLabel = ttk.Label(self.topPanel, text='就绪', foreground='gray')
        self.statusLabel.pack(side=tk.RIGHT, padx=5)

        # 中央诊断显示区
        self.middlePanel = ttk.LabelFrame(self.root, text='以管理员身份运行可查看 阻止系统定时息屏 的程序：', padding=10)
        self.middlePanel.grid(row=1, column=0, sticky='nsew', padx=10, pady=(5, 10))
        self.middlePanel.columnconfigure(0, weight=1)
        self.middlePanel.rowconfigure(0, weight=1)

        self.displayArea = tk.Text(self.middlePanel, wrap=tk.WORD, font=('Consolas', 10))
        self.scrollBar = ttk.Scrollbar(self.middlePanel, orient=tk.VERTICAL, command=self.displayArea.yview)
        self.displayArea.configure(yscrollcommand=self.scrollBar.set)

        self.displayArea.grid(row=0, column=0, sticky='nsew')
        self.scrollBar.grid(row=0, column=1, sticky='ns')

        # 底部设置开机自启动
        self.bottomPanel = ttk.Frame(self.root, padding=10)
        self.bottomPanel.grid(row=2, column=0, sticky='ew', padx=10, pady=(5, 10))

        isAutoStart, err = AutoStartManager.checkAutoStart()
        if err is not None:
            messagebox.showerror("错误", f"检测开机自启动状态失败: {err}")
            exit(1)
        self.isAutoStart = tk.BooleanVar(value=isAutoStart)
        self.autoStartCheckbutton = ttk.Checkbutton(self.bottomPanel, text='开机自启动', variable=self.isAutoStart, command=self.toggleAutoStart)
        self.autoStartCheckbutton.pack(side=tk.LEFT, padx=5)

    def toggleAutoStart(self):
        if self.isAutoStart.get():
            res, err = AutoStartManager.setAutoStart()
            if err is not None:
                self.isAutoStart.set(False)
                messagebox.showerror("错误", f"设置开机自启动失败: {err}")
        else:
            res, err = AutoStartManager.unsetAutoStart()
            if err is not None:
                self.isAutoStart.set(True)
                messagebox.showerror("错误", f"取消开机自启动失败: {err}")

    def triggerBlackout(self):
        '''立即启动黑屏序列'''
        if self.isRunningBlackout:
            return

        filesOk, errText = verifyDriverFiles()
        if not filesOk:
            messagebox.showerror("驱动文件缺失", f"无法启动黑屏切换：\n{errText}\n\n使用 Nuitka 打包时请包含 --include-data-dir=usbmmidd_v2=usbmmidd_v2 参数。")
            return

        self.sleepButton.config(state=tk.DISABLED)
        self.root.update_idletasks()
        self.isRunningBlackout = True
        self.sleepButton.config(state=tk.DISABLED)
        self.updateProgressText('正在初始化...', 'orange')
        
        executeBlackoutSequence(
            onProgressCallback=self.updateProgressText,
            onCompleteCallback=self.onBlackoutComplete,
            onErrorCallback=self.onBlackoutError
        )
        self.sleepButton.config(state=tk.NORMAL)

    def onBlackoutError(self, errorMsg):
        '''黑屏执行异常时的回调'''
        self.root.after(0, lambda: messagebox.showerror("错误", f"黑屏过程中发生错误:\n{errorMsg}"))

    def onBlackoutComplete(self):
        self.root.after(0, self.resetUiState)

    def resetUiState(self):
        self.isRunningBlackout = False
        self.sleepButton.config(state=tk.NORMAL)
        self.statusLabel.config(text='就绪', foreground='gray')

    def refreshBlockerStatus(self):
        self.statusLabel.config(text='正在检测...', foreground='blue')
        self.refreshButton.config(state=tk.DISABLED)
        threading.Thread(target=self.asyncFetchWorker, daemon=True).start()

    def asyncFetchWorker(self):
        requestData = fetchPowerRequests()
        self.root.after(0, self.updateUiDisplay, requestData)

    def updateUiDisplay(self, requestData):
        self.displayArea.config(state=tk.NORMAL)
        self.displayArea.delete('1.0', tk.END)

        if 'ERROR' in requestData:
            self.displayArea.insert(tk.END, '\n'.join(requestData['ERROR']))

        hasActiveBlocker = False
        targetCategories = [
            ('DISPLAY', '【显示器 (阻止息屏)】'),
            ('SYSTEM', '【系统 (阻止休眠)】'),
            ('AWAYMODE', '【离开模式】'),
            ('EXECUTION', '【执行状态】'),
            ('PERFBOOST', '【性能提升】')
        ]

        for catKey, catTitle in targetCategories:
            categoryItems = requestData.get(catKey, [])
            if categoryItems:
                hasActiveBlocker = True
                self.displayArea.insert(tk.END, f'{catTitle}\n', 'categoryHeader')
                for itemDetail in categoryItems:
                    self.displayArea.insert(tk.END, f'  • {itemDetail}\n')
                self.displayArea.insert(tk.END, '\n')

        if not hasActiveBlocker:
            self.displayArea.insert(tk.END, '当前没有任何程序阻止显示器息屏或系统休眠。\n', 'cleanState')

        self.displayArea.tag_config('categoryHeader', font=('Consolas', 10, 'bold'), foreground='#0056b3')
        self.displayArea.tag_config('cleanState', foreground='green')

        self.displayArea.config(state=tk.DISABLED)
        if not self.isRunningBlackout:
            self.statusLabel.config(text='就绪', foreground='gray')
        self.refreshButton.config(state=tk.NORMAL)