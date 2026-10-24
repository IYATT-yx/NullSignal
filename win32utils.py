"""
file: win32utils.py
description: Win32 API、系统电源与虚拟显示驱动管理
author: IYATT-yx
copyright:  Copyright (c) 2026 IYATT-yx.
            Licensed under the MIT License. See LICENSE file in the project root for full license information.
"""
import os
import time
import subprocess
import ctypes
from config import getDriverDir

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

def runCmd(cmd, cwdDir):
    return subprocess.run(cmd, shell=True, cwd=cwdDir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def enableVirtualDisplay(onProgress=None):
    '''挂载/激活虚拟屏'''
    drvDir = getDriverDir()

    if not isDriverInstalled():
        filesOk, errText = verifyDriverFiles()
        if not filesOk:
            raise FileNotFoundError(errText)

        if onProgress:
            onProgress('首次运行，正在向系统注入虚拟显示驱动...')
        runCmd('deviceinstaller64.exe install usbmmidd.inf usbmmidd', drvDir)

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
            enableVirtualDisplay(onProgress=onProgressCallback)
            
            if onProgressCallback: onProgressCallback("正在切换为黑屏模式...")
            time.sleep(0.3)
            
            subprocess.run('displayswitch.exe /external', shell=True)

            if onProgressCallback: onProgressCallback("已进入黑屏 (移动鼠标可退出)...")

            initialPos = POINT()
            user32.GetCursorPos(ctypes.byref(initialPos))
            currentPos = POINT()

            while True:
                time.sleep(0.1)
                user32.GetCursorPos(ctypes.byref(currentPos))
                if abs(currentPos.x - initialPos.x) > 5 or abs(currentPos.y - initialPos.y) > 5:
                    break

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

    import threading
    threading.Thread(target=worker, daemon=True).start()