# 允许局域网访问 - 需要管理员权限运行
# 右键点击此文件，选择"以管理员身份运行"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "🔓 配置防火墙以允许局域网访问" -ForegroundColor Yellow
Write-Host "============================================================`n" -ForegroundColor Cyan

# 检查是否以管理员身份运行
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "❌ 错误: 需要管理员权限！" -ForegroundColor Red
    Write-Host "`n请按以下步骤操作:" -ForegroundColor Yellow
    Write-Host "1. 右键点击此文件 (允许局域网访问.ps1)" -ForegroundColor White
    Write-Host "2. 选择 '以管理员身份运行'" -ForegroundColor White
    Write-Host "`n或者在管理员 PowerShell 中运行:" -ForegroundColor Yellow
    Write-Host "   .\允许局域网访问.ps1" -ForegroundColor Cyan
    Write-Host ""
    Read-Host "按回车键退出"
    exit 1
}

Write-Host "✅ 已确认管理员权限`n" -ForegroundColor Green

# 添加防火墙规则
try {
    Write-Host "📝 正在添加防火墙规则..." -ForegroundColor Yellow
    
    # 先删除可能存在的旧规则
    netsh advfirewall firewall delete rule name="Python HTTP Server 8080" 2>$null
    
    # 添加新规则
    $result = netsh advfirewall firewall add rule name="Python HTTP Server 8080" dir=in action=allow protocol=TCP localport=8080
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ 防火墙规则添加成功！" -ForegroundColor Green
        Write-Host "`n端口 8080 现在已经允许局域网访问" -ForegroundColor Green
    } else {
        throw "添加规则失败"
    }
} catch {
    Write-Host "❌ 添加防火墙规则失败: $_" -ForegroundColor Red
    Write-Host "`n您也可以手动添加规则:" -ForegroundColor Yellow
    Write-Host "1. 打开 Windows Defender 防火墙" -ForegroundColor White
    Write-Host "2. 点击 '高级设置'" -ForegroundColor White
    Write-Host "3. 点击 '入站规则' -> '新建规则'" -ForegroundColor White
    Write-Host "4. 选择 '端口' -> TCP -> 特定本地端口: 8080" -ForegroundColor White
    Write-Host "5. 选择 '允许连接'" -ForegroundColor White
    Write-Host ""
    Read-Host "按回车键退出"
    exit 1
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "🎉 配置完成！" -ForegroundColor Green
Write-Host "============================================================`n" -ForegroundColor Cyan

Write-Host "现在您可以:" -ForegroundColor Yellow
Write-Host "1. 运行 python serve_quiz.py 启动服务器" -ForegroundColor White
Write-Host "2. 其他设备通过局域网地址访问问卷" -ForegroundColor White
Write-Host ""

# 显示当前 IP 地址
Write-Host "📍 您的局域网 IP 地址:" -ForegroundColor Cyan
Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -like "192.168.*" -or $_.IPAddress -like "172.*" -or $_.IPAddress -like "10.*"} | ForEach-Object {
    Write-Host "   http://$($_.IPAddress):8080/keto-mom-interactive-quiz.html" -ForegroundColor Green
}

Write-Host ""
Read-Host "按回车键退出"

