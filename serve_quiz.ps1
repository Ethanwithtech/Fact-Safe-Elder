Param(
    [int]$Port = 8080
)

$scriptDir = Split-Path $MyInvocation.MyCommand.Path -Parent
Set-Location $scriptDir

$env:QUIZ_FILE = "keto-mom-interactive-quiz.html"

if (-not (Test-Path $env:QUIZ_FILE)) {
    Write-Host "找不到 $env:QUIZ_FILE ，请确认文件在当前目录。" -ForegroundColor Red
    exit 1
}

Write-Host "启动本地HTTP服务器，端口 $Port (可被同一网段访问)..." -ForegroundColor Yellow

$job = Start-Job -ScriptBlock {
    param($PortParam)
    python -m http.server $PortParam --bind 0.0.0.0
} -ArgumentList $Port

Start-Sleep -Seconds 2

$ipInfo = Get-NetIPAddress -AddressFamily IPv4 -PrefixOrigin Dhcp | Where-Object { $_.InterfaceAlias -notmatch "Loopback" }

if ($ipInfo) {
    $ip = $ipInfo[0].IPAddress
    $url = "http://$ip`:$Port/keto-mom-interactive-quiz.html"
    Write-Host "请在同一网络的设备访问：$url" -ForegroundColor Green
} else {
    Write-Host "未能自动获取IPv4地址，请手动执行 ipconfig 查看。" -ForegroundColor Yellow
}

Write-Host "按 Ctrl + C 停止服务器，或在新窗口执行 Stop-Job $($job.Id) && Remove-Job $($job.Id)" -ForegroundColor Cyan

Wait-Job $job

