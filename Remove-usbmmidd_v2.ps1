# 1. 自动查找并移除所有 USB Mobile Monitor 虚拟显示器设备节点
Get-PnpDevice | Where-Object { $_.FriendlyName -like "*USB Mobile Monitor*" } | ForEach-Object {
    Write-Host "正在卸载设备节点: $($_.InstanceId)" -ForegroundColor Yellow
    pnputil /remove-device $_.InstanceId
}

# 2. (可选) 清理系统驱动库中缓存的第三方 INF 驱动包
Get-WindowsDriver -Online | Where-Object { $_.ProviderName -like "*Amyuni*" -or $_.OriginalFileName -like "*usbmmidd*" } | ForEach-Object {
    Write-Host "正在从驱动库清除驱动包: $($_.Driver)" -ForegroundColor Red
    pnputil /delete-driver $_.Driver /uninstall /force
}