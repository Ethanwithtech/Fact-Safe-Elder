# 🚀 项目自动迁移脚本 - 迁移到D盘
# PowerShell脚本，用于将项目从Desktop迁移到D盘

param(
    [string]$TargetPath = "D:\Projects\Fact-Safe-Elder",
    [switch]$CleanInstall = $true
)

Write-Host "🛡️ AI守护系统 - 项目迁移工具" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green

# 1. 创建目标目录
Write-Host "📁 创建目标目录: $TargetPath" -ForegroundColor Yellow
try {
    New-Item -ItemType Directory -Path $TargetPath -Force | Out-Null
    Write-Host "✅ 目录创建成功" -ForegroundColor Green
}
catch {
    Write-Host "❌ 目录创建失败: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# 2. 复制项目文件
Write-Host "📋 复制项目文件..." -ForegroundColor Yellow
try {
    $sourceFiles = @(
        "*.md", "*.ps1", "*.json", "*.yml", "*.yaml", "*.txt", "*.env*",
        "frontend", "backend", "scripts", "docs", ".gitignore", "start.sh"
    )
    
    foreach ($pattern in $sourceFiles) {
        $items = Get-ChildItem -Path $pattern -ErrorAction SilentlyContinue
        if ($items) {
            Copy-Item -Path $items -Destination $TargetPath -Recurse -Force
            Write-Host "  ✓ 已复制: $pattern" -ForegroundColor Gray
        }
    }
    Write-Host "✅ 项目文件复制完成" -ForegroundColor Green
}
catch {
    Write-Host "❌ 文件复制失败: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# 3. 清理和重新安装依赖
if ($CleanInstall) {
    Write-Host "🧹 清理旧依赖..." -ForegroundColor Yellow
    
    # 删除node_modules
    $nodeModulesPath = Join-Path $TargetPath "frontend\node_modules"
    if (Test-Path $nodeModulesPath) {
        Remove-Item -Path $nodeModulesPath -Recurse -Force
        Write-Host "  ✓ 已删除 node_modules" -ForegroundColor Gray
    }
    
    # 删除Python缓存
    $pycachePaths = Get-ChildItem -Path $TargetPath -Name "__pycache__" -Recurse -Directory
    foreach ($path in $pycachePaths) {
        Remove-Item -Path (Join-Path $TargetPath $path) -Recurse -Force
        Write-Host "  ✓ 已删除 Python缓存: $path" -ForegroundColor Gray
    }
}

# 4. 重新安装前端依赖
Write-Host "📦 安装前端依赖..." -ForegroundColor Yellow
try {
    Push-Location (Join-Path $TargetPath "frontend")
    
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        npm install --silent
        Write-Host "✅ 前端依赖安装完成" -ForegroundColor Green
    } else {
        Write-Host "⚠️  未找到npm，请手动安装前端依赖" -ForegroundColor Yellow
    }
    
    Pop-Location
}
catch {
    Write-Host "❌ 前端依赖安装失败: $($_.Exception.Message)" -ForegroundColor Red
    Pop-Location
}

# 5. 检查Python环境
Write-Host "🐍 检查Python环境..." -ForegroundColor Yellow
try {
    Push-Location (Join-Path $TargetPath "backend")
    
    if (Get-Command python -ErrorAction SilentlyContinue) {
        Write-Host "  ✓ Python环境已就绪" -ForegroundColor Gray
        Write-Host "  💡 请手动运行: pip install -r requirements.txt" -ForegroundColor Cyan
    } elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
        Write-Host "  ✓ Python3环境已就绪" -ForegroundColor Gray
        Write-Host "  💡 请手动运行: pip3 install -r requirements.txt" -ForegroundColor Cyan
    } else {
        Write-Host "  ⚠️  未找到Python，请先安装Python环境" -ForegroundColor Yellow
    }
    
    Pop-Location
}
catch {
    Write-Host "❌ Python检查失败: $($_.Exception.Message)" -ForegroundColor Red
    Pop-Location
}

# 6. 创建启动脚本
Write-Host "🚀 创建启动脚本..." -ForegroundColor Yellow
$startScript = @"
# 🛡️ AI守护系统启动脚本 - D盘版本
Write-Host "启动AI守护系统..." -ForegroundColor Green

# 检查Docker
if (Get-Command docker -ErrorAction SilentlyContinue) {
    Write-Host "使用Docker启动服务..." -ForegroundColor Yellow
    docker-compose up --build -d
    
    Write-Host "服务启动完成！" -ForegroundColor Green
    Write-Host "前端访问: http://localhost:3000" -ForegroundColor Cyan
    Write-Host "后端API: http://localhost:8000" -ForegroundColor Cyan
} else {
    Write-Host "Docker未安装，请手动启动服务" -ForegroundColor Yellow
    Write-Host "前端: cd frontend && npm start" -ForegroundColor Cyan
    Write-Host "后端: cd backend && python -m uvicorn app.main:app --reload" -ForegroundColor Cyan
}
"@

$startScript | Out-File -FilePath (Join-Path $TargetPath "start-system.ps1") -Encoding UTF8
Write-Host "✅ 启动脚本创建完成" -ForegroundColor Green

# 7. 生成迁移报告
Write-Host "📊 生成迁移报告..." -ForegroundColor Yellow
$report = @"
# 🎉 项目迁移完成报告

## ✅ 迁移信息
- **源路径**: C:\Users\dyc06\Desktop\Fact-Safe-Elder
- **目标路径**: $TargetPath
- **迁移时间**: $(Get-Date)
- **迁移状态**: 成功

## 📁 迁移内容
- ✅ 所有源代码文件
- ✅ 配置文件和文档
- ✅ Docker配置
- ✅ 项目依赖列表

## 🔧 后续操作
1. **安装Python依赖**:
   ```
   cd "$TargetPath\backend"
   pip install -r requirements.txt
   ```

2. **启动系统**:
   ```
   cd "$TargetPath"
   .\start-system.ps1
   ```

3. **访问系统**:
   - 前端: http://localhost:3000
   - 后端: http://localhost:8000

## 💡 提示
- 删除原Desktop版本前，请确认新版本运行正常
- 建议创建Git仓库进行版本管理
- 定期备份项目文件

---
迁移工具版本: 1.0
生成时间: $(Get-Date)
"@

$report | Out-File -FilePath (Join-Path $TargetPath "迁移报告.md") -Encoding UTF8

# 8. 完成
Write-Host ""
Write-Host "🎉 项目迁移完成！" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host "新项目路径: $TargetPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "后续步骤:" -ForegroundColor Yellow
Write-Host "1. cd `"$TargetPath`"" -ForegroundColor Gray
Write-Host "2. .\start-system.ps1  # 启动系统" -ForegroundColor Gray
Write-Host "3. 访问 http://localhost:3000" -ForegroundColor Gray
Write-Host ""
Write-Host "如有问题，请查看 '迁移报告.md' 文件" -ForegroundColor Yellow

