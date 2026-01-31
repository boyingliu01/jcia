# JCIA 开发工作流脚本 (PowerShell)
# 用于日常开发中的质量检查

$ErrorActionPreference = "Continue"

$projectPath = "e:\Study\LLM\Java代码变更影响分析"
Set-Location $projectPath

# 检查虚拟环境是否存在
$venvPath = ".venv\Scripts\Activate.ps1"
if (-not (Test-Path $venvPath)) {
    Write-Host "❌ 虚拟环境不存在，请先运行 python -m venv .venv" -ForegroundColor Red
    exit 1
}

# 激活虚拟环境
& $venvPath

Write-Host "🔄 JCIA 开发工作流" -ForegroundColor Cyan
Write-Host "==================" -ForegroundColor Cyan

# 格式化代码
Write-Host ""
Write-Host "🎨 格式化代码..." -ForegroundColor Yellow
ruff format jcia tests

# 自动修复问题
Write-Host ""
Write-Host "🔧 自动修复代码问题..." -ForegroundColor Yellow
ruff check --fix jcia tests; if ($LASTEXITCODE -ne 0) { Write-Host "部分问题需要手动修复" -ForegroundColor Yellow }

# 运行类型检查
Write-Host ""
Write-Host "🔍 类型检查..." -ForegroundColor Yellow
pyright jcia tests; if ($LASTEXITCODE -ne 0) { Write-Host "类型检查发现问题" -ForegroundColor Yellow }

# 运行测试
Write-Host ""
Write-Host "🧪 运行测试..." -ForegroundColor Yellow
python -m pytest tests/unit -v --tb=short

Write-Host ""
Write-Host "✅ 工作流完成！" -ForegroundColor Green
