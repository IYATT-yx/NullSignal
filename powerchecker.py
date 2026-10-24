"""
file: powerchecker.py
description: 电源阻止程序检测 (powercfg /requests)
author: IYATT-yx
copyright:  Copyright (c) 2026 IYATT-yx.
            Licensed under the MIT License. See LICENSE file in the project root for full license information.
"""
import subprocess

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