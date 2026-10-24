"""
file: config.py
description: 路径与常量配置
author: IYATT-yx
copyright:  Copyright (c) 2026 IYATT-yx.
            Licensed under the MIT License. See LICENSE file in the project root for full license information.
"""
import os

def getBaseDir():
    '''获取当前程序运行根目录'''
    return os.path.dirname(os.path.abspath(__file__))

def getDriverDir():
    '''获取 usbmmidd_v2 驱动目录路径'''
    return os.path.join(getBaseDir(), 'usbmmidd_v2')

def getIconPath():
    '''获取图标路径'''
    return os.path.join(getBaseDir(), 'icon.ico')