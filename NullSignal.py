"""
file: NullSignal.py
description: 息屏工具
author: IYATT-yx
copyright:  Copyright (c) 2026 IYATT-yx.
            Licensed under the MIT License. See LICENSE file in the project root for full license information.
"""
import os
import time
import subprocess
import threading
import ctypes
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

from buildtime import buildTime

# ----------------------------------------------------------------------
# Win32 API & 系统电源/驱动管理
# ----------------------------------------------------------------------
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

esContinuous = 0x80000000
esSystemRequired = 0x00000001

class POINT(ctypes.Structure):
    _fields_ = [('x', ctypes.c_long), ('y', ctypes.c_long)]

def verifyDriverFiles():
    '''检查驱动文件夹和关键文件是否存在'''
    drvDir = getDriverDir()
    requiredFiles = ['deviceinstaller64.exe', 'usbmmidd.inf']
    
    if not os.path.exists(drvDir):
        return False, f"未找到驱动目录: {drvDir}"
    
    for fileName in requiredFiles:
        filePath = os.path.join(drvDir, fileName)
        if not os.path.exists(filePath):
            return False, f"驱动关键文件缺失: {fileName}\n路径: {filePath}"
            
    return True, ""

def isDriverInstalled():
    '''检查系统中是否已经存在 usbmmidd 设备节点'''
    try:
        startupInfo = subprocess.STARTUPINFO()
        startupInfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        result = subprocess.run(
            ['pnputil', '/enum-devices', '/deviceid', 'usbmmidd'],
            capture_output=True,
            text=True,
            encoding='oem',
            startupinfo=startupInfo,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        output = result.stdout.lower()
        if 'usb mobile monitor' in output:
            return True
    except Exception as e:
        print(f'pnputil 驱动检查异常: {e}')

    return False

def isVirtualDisplayEnabled():
    '''检查当前系统中是否已存在/启用了虚拟显示器 (usbmmidd)'''
    try:
        startupInfo = subprocess.STARTUPINFO()
        startupInfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        # 使用 wmic 检查是否已挂载该虚拟显示设备
        output = subprocess.check_output(
            'wmic path Win32_PnPEntity where "Name like \'%USB Mobile Monitor%\'" get Name',
            shell=True,
            text=True,
            startupinfo=startupInfo,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return "USB Mobile Monitor" in output
    except Exception:
        return False

def runCmd(cmd, cwdDir):
    return subprocess.run(cmd, shell=True, cwd=cwdDir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def getBaseDir():
    '''获取当前程序运行根目录'''
    return os.path.dirname(__file__)

def getDriverDir():
    '''获取 usbmmidd_v2 驱动目录路径'''
    return os.path.join(getBaseDir(), 'usbmmidd_v2')

def enableVirtualDisplay(onProgress=None):
    '''挂载/激活虚拟屏'''
    drvDir = getDriverDir()

    # 只有在系统中完全找不到该 PnP 设备时，才跑耗时极长的首次安装
    if not isDriverInstalled():
        filesOk, errText = verifyDriverFiles()
        if not filesOk:
            raise FileNotFoundError(errText)

        if onProgress:
            onProgress('首次运行，正在向系统注入虚拟显示驱动...')
        runCmd('deviceinstaller64.exe install usbmmidd.inf usbmmidd', drvDir)

    # 已安装驱动时，直接激活已有屏，耗时在毫秒级
    if onProgress:
        onProgress('正在激活虚拟显示屏...')
    runCmd('deviceinstaller64.exe enableidd 1', drvDir)

def disableVirtualDisplay():
    '''关闭虚拟显示屏'''
    drvDir = getDriverDir()
    if os.path.exists(drvDir):
        runCmd('deviceinstaller64.exe enableidd 0', drvDir)

def executeBlackoutSequence(onProgressCallback=None, onCompleteCallback=None, onErrorCallback=None):
    '''黑屏核心逻辑：挂载虚拟屏 -> 强切显示 -> 监测鼠标复原'''
    def worker():
        kernel32.SetThreadExecutionState(esContinuous | esSystemRequired)
        try:
            # 激活虚拟显示器
            enableVirtualDisplay(onProgress=onProgressCallback)
            
            # 准备切换显示拓扑
            if onProgressCallback: onProgressCallback("正在切换为黑屏模式...")
            time.sleep(0.3)
            
            subprocess.run('displayswitch.exe /external', shell=True)

            # 进入监听鼠标恢复阶段
            if onProgressCallback: onProgressCallback("已进入黑屏 (移动鼠标可退出)...")

            initialPos = POINT()
            user32.GetCursorPos(ctypes.byref(initialPos))
            currentPos = POINT()

            while True:
                time.sleep(0.1)
                user32.GetCursorPos(ctypes.byref(currentPos))
                if abs(currentPos.x - initialPos.x) > 5 or abs(currentPos.y - initialPos.y) > 5:
                    break

            # 退出阶段
            if onProgressCallback: onProgressCallback("检测到动作，正在恢复显示...")
        except Exception as e:
            if onErrorCallback:
                onErrorCallback(str(e))
        finally:
            subprocess.run('displayswitch.exe /internal', shell=True)
            time.sleep(0.5)
            
            if onProgressCallback: onProgressCallback("正在清理虚拟设备...")
            disableVirtualDisplay()
            
            kernel32.SetThreadExecutionState(esContinuous)
            if onCompleteCallback:
                onCompleteCallback()

    threading.Thread(target=worker, daemon=True).start()

# ----------------------------------------------------------------------
# 电源阻止程序检测 (powercfg /requests)
# ----------------------------------------------------------------------
def fetchPowerRequests():
    try:
        startupInfo = subprocess.STARTUPINFO()
        startupInfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        rawOutput = subprocess.check_output(
            ['powercfg', '/requests'],
            text=True,
            encoding='oem',
            startupinfo=startupInfo,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
    except Exception as err:
        return {'ERROR': [f'获取电源状态失败: {err}']}

    parsedResults = {}
    currentCategory = None

    for line in rawOutput.splitlines():
        trimmedLine = line.strip()
        if not trimmedLine:
            continue

        if trimmedLine.endswith(':') and trimmedLine.isupper():
            currentCategory = trimmedLine[:-1]
            parsedResults[currentCategory] = []
        elif currentCategory:
            if trimmedLine not in ('无。', 'None.'):
                parsedResults[currentCategory].append(trimmedLine)

    return parsedResults

# ----------------------------------------------------------------------
# GUI 主界面 & 系统托盘
# ----------------------------------------------------------------------
class NullSignalApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f'NullSignal 息屏工具 by IYATT-yx {buildTime}')
        self.root.geometry('560x460')
        self.root.resizable(True, True)

        self.iconPath = os.path.join(getBaseDir(), 'icon.ico')
        self.setupWindowIcon()

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        self.isRunningBlackout = False

        self.initUi()
        self.refreshBlockerStatus()

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

    def initUi(self):
        # 顶栏控制面板
        self.topPanel = ttk.Frame(self.root, padding=10)
        self.topPanel.grid(row=0, column=0, sticky='ew')

        self.sleepButton = ttk.Button(self.topPanel, text=' 触发硬件黑屏 ', command=self.triggerBlackout)
        self.sleepButton.pack(side=tk.LEFT, padx=5)

        self.refreshButton = ttk.Button(self.topPanel, text='刷新阻止程序', command=self.refreshBlockerStatus)
        self.refreshButton.pack(side=tk.LEFT, padx=5)

        self.statusLabel = ttk.Label(self.topPanel, text='就绪', foreground='gray')
        self.statusLabel.pack(side=tk.RIGHT, padx=5)

        # 中央诊断显示区
        self.middlePanel = ttk.LabelFrame(self.root, text=' 当前阻止显示器息屏 / 系统休眠的程序 (powercfg) ', padding=10)
        self.middlePanel.grid(row=1, column=0, sticky='nsew', padx=10, pady=(5, 10))
        self.middlePanel.columnconfigure(0, weight=1)
        self.middlePanel.rowconfigure(0, weight=1)

        self.displayArea = tk.Text(self.middlePanel, wrap=tk.WORD, font=('Consolas', 10))
        self.scrollBar = ttk.Scrollbar(self.middlePanel, orient=tk.VERTICAL, command=self.displayArea.yview)
        self.displayArea.configure(yscrollcommand=self.scrollBar.set)

        self.displayArea.grid(row=0, column=0, sticky='nsew')
        self.scrollBar.grid(row=0, column=1, sticky='ns')

    def hideToTray(self):
        self.root.withdraw()

    def showFromTray(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def triggerBlackout(self):
        '''立即启动黑屏序列'''
        if self.isRunningBlackout:
            return

        filesOk, errText = verifyDriverFiles()
        if not filesOk:
            messagebox.showerror("驱动文件缺失", f"无法启动黑屏切换：\n{errText}\n\n使用 Nuitka 打包时请包含 --include-data-dir=usbmmidd_v2=usbmmidd_v2 参数。")
            return
        
        self.isRunningBlackout = True
        self.sleepButton.config(state=tk.DISABLED)
        self.updateProgressText('正在初始化...', 'orange')
        
        executeBlackoutSequence(
            onProgressCallback=self.updateProgressText,
            onCompleteCallback=self.onBlackoutComplete,
            onErrorCallback=self.onBlackoutError
        )

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

if __name__ == '__main__':
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    mainWindow = tk.Tk()
    app = NullSignalApp(mainWindow)
    mainWindow.mainloop()