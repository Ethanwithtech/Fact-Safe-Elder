# 从 GitHub Release 下载模型附件（需已发布 Release）
# 用法（在仓库根目录执行）:
#   .\scripts\download_models_from_release.ps1 -Tag "v1.0.0-models"
#
# 修改下面 $Owner $Repo 为你的 GitHub 用户名和仓库名

param(
    [string]$Tag = "v1.0.0-models",
    [string]$Owner = "Ethanwithtech",
    [string]$Repo = "Fact-Safe-Elder"
)

$ErrorActionPreference = "Stop"
# 脚本位于 仓库/scripts/，项目根为上一级
$root = Resolve-Path (Join-Path $PSScriptRoot "..")

$assets = @(
    @{ Name = "best_text_model.pt"; Dest = "best_text_model.pt" }
    @{ Name = "simple_ai_model.joblib"; Dest = "models\trained\simple_ai_model.joblib" }
)

foreach ($a in $assets) {
    $url = "https://github.com/$Owner/$Repo/releases/download/$Tag/$($a.Name)"
    $out = Join-Path $root $a.Dest
    $dir = Split-Path $out -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    Write-Host "Downloading: $url"
    try {
        Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing
        Write-Host "OK -> $out"
    } catch {
        Write-Warning "Skip or failed (file may not exist in this release): $($a.Name)"
    }
}

Write-Host "`nDone. If downloads failed, open the Release page in browser and download manually."
Write-Host "See: docs/GITHUB_RELEASE_模型分发完整指南.md"
