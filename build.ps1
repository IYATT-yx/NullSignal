$startTime = Get-Date

py -3.14 -m venv venv
.\venv\Scripts\Activate.ps1
python.exe -m pip install --upgrade pip
pip install nuitka==4.2.2

Set-Content -Path ".\buildtime.py" -Value "buildTime = '$(Get-Date -Format 'yyyyMMdd_HHmmss')'" -Encoding UTF8

nuitka --standalone `
--windows-uac-admin `
--windows-console-mode=disable `
--lto=yes `
--no-deployment-flag=self-contained `
--enable-plugin=tk-inter `
--windows-company-name="IYATT-yx" `
--windows-product-name="NullSignal 息屏工具" `
--windows-file-description="NullSignal 息屏工具" `
--windows-product-version="1.0.0.0" `
--windows-file-version="1.0.0.0" `
--copyright="Copyright (C) 2026 IYATT-yx. All Rights Reserved." `
--windows-icon-from-ico=.\icon.ico `
--include-data-file=.\icon.ico=.\ `
--output-dir=dist `
--output-filename=NullSignal_win_amd64 `
.\NullSignal.py

$distDir = ".\dist\NullSignal.dist"
$targetExe = Join-Path $distDir "NullSignal_win_amd64.exe"

#  检查打包结果并自动补充资源文件夹
if ($LASTEXITCODE -eq 0 -and (Test-Path $targetExe)) {
    Write-Host "`n[+] Nuitka 编译成功！开始复制依赖文件..." -ForegroundColor Green

    # 复制 usbmmidd_v2 驱动文件夹
    if (Test-Path ".\usbmmidd_v2") {
        Copy-Item -Path ".\usbmmidd_v2" -Destination $distDir -Recurse -Force
        Write-Host "  -> 已成功递归复制 usbmmidd_v2 驱动目录" -ForegroundColor Gray
    } else {
        Write-Warning "  ! 未找到源文件夹 .\usbmmidd_v2，请检查路径"
    }

    $endTime = Get-Date
    $elapsedTime = New-TimeSpan -Start $startTime -End $endTime
    Write-Host "`n[✔] 所有资源处理完毕，程序构建总用时：$($elapsedTime.TotalSeconds) 秒" -ForegroundColor Cyan
} else {
    Write-Error "`n[❌] Nuitka 打包失败或未能生成最终 EXE 文件，已终止后续复制流程。"
}