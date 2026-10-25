"""
file: autostart.py
description: 开机自启动管理。支持注册表与 Windows 任务计划程序双方案
author: IYATT-yx
copyright:  Copyright (c) 2026 IYATT-yx.
            Licensed under the MIT License. See LICENSE file in the project root for full license information.
"""
import winreg
import os
import sys
import subprocess


class AutoStartConstant:
    """路径及系统配置常量"""
    REGISTRY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
    TASK_TRIGGER_EVENT = "ONLOGON"
    TASK_RUN_LEVEL = "HIGHEST"

class AutoStartBase:
    """自启动公共基类"""
    projectName = None
    '''自启动项目名'''
    isPackaged = '__compiled__' in globals()
    '''是否被 Nuitka 打包'''
    programFilePath = os.path.abspath(sys.argv[0])
    '''程序文件路径'''
    commandStr = None
    '''自启动命令'''

    @classmethod
    def setProjectName(cls, projectName: str):
        '''设置自启动项目名

        Args:
            projectName (str): 项目名
        '''
        cls.projectName = projectName

    @classmethod
    def setArgs(cls, args: list[str] | None = None):
        '''设置自启动命令的参数（必须调用此方法进行初始化）

        Args:
            args (list[str] | None): 命令行参数列表
        '''
        baseCommand = f'"{cls.programFilePath}"' if cls.isPackaged else f'"{sys.executable}" "{cls.programFilePath}"'
        if args is None:
            cls.commandStr = baseCommand
        else:
            formattedArgs = []
            for arg in args:
                if ' ' in arg and not (arg.startswith('"') and arg.endswith('"')):
                    formattedArgs.append(f'"{arg}"')
                else:                                          
                    formattedArgs.append(arg)
            cls.commandStr = f'{baseCommand} {" ".join(formattedArgs)}'


class AutoStart(AutoStartBase):
    """注册表开机自启动方案"""
    autoStartRegPath = AutoStartConstant.REGISTRY_PATH
    '''自启动注册表配置路径'''

    @classmethod
    def setAutoStart(cls) -> tuple[bool, Exception | None]:
        """设置开机自启动

        Returns:
            tuple[bool, Exception | None]: (是否设置成功, 错误信息)
        """
        if cls.projectName is None:
            return False, RuntimeError('未设置自启动项目名')
        if cls.commandStr is None:
            return False, RuntimeError('未调用 setArgs 方法设置自启动命令')
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                cls.autoStartRegPath,
                0,
                winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(key, cls.projectName, 0, winreg.REG_SZ, cls.commandStr)
            winreg.CloseKey(key)
            return True, None
        except Exception as e:
            return False, e

    @classmethod
    def unsetAutoStart(cls) -> tuple[bool, Exception | None]:
        """取消开机自启动

        Returns:
            tuple[bool, Exception | None]: (是否取消成功, 错误信息)
        """
        if cls.projectName is None:
            return False, RuntimeError('未设置自启动项目名')
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                cls.autoStartRegPath,
                0,
                winreg.KEY_SET_VALUE
            )
            winreg.DeleteValue(key, cls.projectName)
            winreg.CloseKey(key)
            return True, None
        except FileNotFoundError:
            return True, RuntimeError('未设置自启动，无需取消')
        except Exception as e:
            return False, e

    @classmethod
    def checkAutoStart(cls) -> tuple[bool, Exception | None]:
        """检查是否设置开机自启动

        Returns:
            tuple[bool, Exception | None]: (是否设置自启动, 错误信息)
        """
        if cls.projectName is None:
            return False, RuntimeError('未设置自启动项目名')
        if cls.commandStr is None:
            return False, RuntimeError('未调用 setArgs 方法设置自启动命令')
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                cls.autoStartRegPath,
                0,
                winreg.KEY_READ
            )
            value, _ = winreg.QueryValueEx(key, cls.projectName)
            winreg.CloseKey(key)
            if value == cls.commandStr:
                return True, None
            else:
                return False, None
        except FileNotFoundError:
            return False, None
        except Exception as e:
            return False, e


class TaskSchedulerAutoStart(AutoStartBase):
    """Windows 任务计划程序开机自启动方案"""

    @classmethod
    def setAutoStart(cls) -> tuple[bool, Exception | None]:
        if cls.projectName is None:
            return False, RuntimeError('未设置自启动项目名')
        if cls.commandStr is None:
            return False, RuntimeError('未调用 setArgs 方法设置自启动命令')
        try:
            cmd = [
                'schtasks', '/Create', '/F',
                '/TN', cls.projectName,
                '/TR', cls.commandStr,
                '/SC', AutoStartConstant.TASK_TRIGGER_EVENT,
                '/RL', AutoStartConstant.TASK_RUN_LEVEL
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if res.returncode == 0:
                return True, None
            else:
                return False, RuntimeError(f"创建计划任务失败: {res.stderr.strip()}")
        except Exception as e:
            return False, e

    @classmethod
    def unsetAutoStart(cls) -> tuple[bool, Exception | None]:
        if cls.projectName is None:
            return False, RuntimeError('未设置自启动项目名')
        try:
            cmd = ['schtasks', '/Delete', '/F', '/TN', cls.projectName]
            res = subprocess.run(cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if res.returncode == 0:
                return True, None
            else:
                if "找不到" in res.stderr or "not found" in res.stderr.lower():
                    return True, RuntimeError('未设置自启动，无需取消')
                return False, RuntimeError(f"删除计划任务失败: {res.stderr.strip()}")
        except Exception as e:
            return False, e

    @classmethod
    def checkAutoStart(cls) -> tuple[bool, Exception | None]:
        if cls.projectName is None:
            return False, RuntimeError('未设置自启动项目名')
        if cls.commandStr is None:
            return False, RuntimeError('未调用 setArgs 方法设置自启动命令')
        try:
            cmd = ['schtasks', '/Query', '/TN', cls.projectName, '/FO', 'LIST', '/V']
            res = subprocess.run(cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if res.returncode == 0:
                if cls.commandStr in res.stdout:
                    return True, None
                else:
                    return False, None
            else:
                return False, None
        except Exception as e:
            return False, e

class AutoStartManager:
    """自启动统一管理入口"""
    MODE_REGISTRY = "registry"
    MODE_TASK_SCHEDULER = "task_scheduler"

    selectedStrategy = None

    @staticmethod
    def init(projectName: str, args: list[str] | None = None, mode: str = MODE_TASK_SCHEDULER):
        """初始化自启动管理器

        Args:
            projectName (str): 项目名称
            args (list[str] | None): 自启动命令行参数列表
            mode (str): 模式选择，AutoStartManager.MODE_REGISTRY 或 AutoStartManager.MODE_TASK_SCHEDULER
        """
        if mode == AutoStartManager.MODE_REGISTRY:
            AutoStartManager.selectedStrategy = AutoStart
        else:
            AutoStartManager.selectedStrategy = TaskSchedulerAutoStart

        AutoStartManager.selectedStrategy.setProjectName(projectName)
        AutoStartManager.selectedStrategy.setArgs(args)

    @staticmethod
    def setAutoStart() -> tuple[bool, Exception | None]:
        if AutoStartManager.selectedStrategy is None:
            return False, RuntimeError('未初始化自启动管理器')
        return AutoStartManager.selectedStrategy.setAutoStart()

    @staticmethod
    def unsetAutoStart() -> tuple[bool, Exception | None]:
        if AutoStartManager.selectedStrategy is None:
            return False, RuntimeError('未初始化自启动管理器')
        return AutoStartManager.selectedStrategy.unsetAutoStart()

    @staticmethod
    def checkAutoStart() -> tuple[bool, Exception | None]:
        if AutoStartManager.selectedStrategy is None:
            return False, RuntimeError('未初始化自启动管理器')
        return AutoStartManager.selectedStrategy.checkAutoStart()