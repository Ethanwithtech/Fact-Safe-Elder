# 快速解决方案：使用手机热点
# 这个脚本会引导您完成所有步骤

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "📱 局域网访问问题 - 快速解决方案" -ForegroundColor Yellow
Write-Host "============================================================`n" -ForegroundColor Cyan

Write-Host "🔍 问题诊断：" -ForegroundColor Yellow
Write-Host "您连接的是 HKBU（学校）网络，该网络很可能启用了 AP 隔离" -ForegroundColor White
Write-Host "这会阻止同一网络下的设备互相访问（安全措施）`n" -ForegroundColor White

Write-Host "✅ 推荐解决方案：使用手机热点" -ForegroundColor Green
Write-Host "这是最简单、最可靠的方法！`n" -ForegroundColor Green

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "📋 操作步骤：" -ForegroundColor Yellow
Write-Host "============================================================`n" -ForegroundColor Cyan

Write-Host "步骤 1️⃣：在手机上开启热点" -ForegroundColor Cyan
Write-Host "   - 打开手机设置" -ForegroundColor White
Write-Host "   - 找到'个人热点'或'便携式热点'" -ForegroundColor White
Write-Host "   - 开启热点，记住热点名称和密码`n" -ForegroundColor White

$continue = Read-Host "完成步骤 1 后，按回车继续"

Write-Host "`n步骤 2️⃣：电脑连接到手机热点" -ForegroundColor Cyan
Write-Host "   - 断开当前的 HKBU Wi-Fi" -ForegroundColor White
Write-Host "   - 连接到手机热点`n" -ForegroundColor White

$continue = Read-Host "完成步骤 2 后，按回车继续"

Write-Host "`n步骤 3️⃣：（可选）关闭 VPN" -ForegroundColor Cyan
Write-Host "   - 检测到 NordVPN 正在运行" -ForegroundColor Yellow
Write-Host "   - 建议暂时关闭 VPN 以避免干扰`n" -ForegroundColor Yellow

$closeVPN = Read-Host "是否已关闭 VPN？(y/n，或直接回车跳过)"

Write-Host "`n步骤 4️⃣：配置防火墙" -ForegroundColor Cyan
Write-Host "   - 正在检查管理员权限..." -ForegroundColor White

$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if ($isAdmin) {
    Write-Host "   ✅ 已确认管理员权限" -ForegroundColor Green
    Write-Host "   - 正在添加防火墙规则..." -ForegroundColor White
    
    try {
        netsh advfirewall firewall delete rule name="Python HTTP Server 8080" 2>$null
        netsh advfirewall firewall add rule name="Python HTTP Server 8080" dir=in action=allow protocol=TCP localport=8080 | Out-Null
        Write-Host "   ✅ 防火墙规则添加成功！`n" -ForegroundColor Green
    } catch {
        Write-Host "   ⚠️  防火墙规则添加失败，但可以继续尝试`n" -ForegroundColor Yellow
    }
} else {
    Write-Host "   ⚠️  未检测到管理员权限" -ForegroundColor Yellow
    Write-Host "   - 如果访问失败，请以管理员身份重新运行此脚本`n" -ForegroundColor Yellow
}

Write-Host "步骤 5️⃣：启动服务器" -ForegroundColor Cyan
Write-Host "   - 正在启动问卷服务器...`n" -ForegroundColor White

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "🚀 准备启动服务器" -ForegroundColor Green
Write-Host "============================================================`n" -ForegroundColor Cyan

Write-Host "即将运行: python serve_quiz.py`n" -ForegroundColor Yellow

$continue = Read-Host "按回车启动服务器"

# 启动服务器
python serve_quiz.py

