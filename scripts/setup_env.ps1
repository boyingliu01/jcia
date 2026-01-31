# JCIA PowerShell 环境初始化脚本

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "JCIA 环境初始化" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$projectPath = "E:\Study\LLM\Java代码变更影响分析"
$venvPath = "$projectPath\.venv"

# 检查Python是否可用
Write-Host "🔍 检查Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python版本: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ 未找到Python，请先安装Python 3.10+" -ForegroundColor Red
    exit 1
}

# 创建虚拟环境
Write-Host ""
Write-Host "📦 创建虚拟环境..." -ForegroundColor Yellow
if (Test-Path $venvPath) {
    Write-Host "✅ 虚拟环境已存在" -ForegroundColor Green
} else {
    try {
        python -m venv .venv
        Write-Host "✅ 虚拟环境创建成功" -ForegroundColor Green
    } catch {
        Write-Host "❌ 虚拟环境创建失败: $_" -ForegroundColor Red
        exit 1
    }
}

# 激活虚拟环境
Write-Host ""
Write-Host "🔌 激活虚拟环境..." -ForegroundColor Yellow
try {
    & "$venvPath\Scripts\Activate.ps1"
    Write-Host "✅ 虚拟环境已激活" -ForegroundColor Green
} catch {
    Write-Host "❌ 激活虚拟环境失败: $_" -ForegroundColor Red
    Write-Host "请运行以下命令设置执行策略：" -ForegroundColor Yellow
    Write-Host "  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Cyan
    exit 1
}

# 升级pip
Write-Host ""
Write-Host "⬆️  升级pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip -q

# 安装开发依赖
Write-Host ""
Write-Host "📥 安装开发依赖..." -ForegroundColor Yellow
try {
    pip install -e ".[dev]" -q
    Write-Host "✅ 开发依赖安装成功" -ForegroundColor Green
} catch {
    Write-Host "❌ 安装依赖失败: $_" -ForegroundColor Red
    exit 1
}

# 配置pre-commit hooks
Write-Host ""
Write-Host "🔗 配置pre-commit hooks..." -ForegroundColor Yellow
try {
    pre-commit install
    Write-Host "✅ pre-commit hooks配置成功" -ForegroundColor Green
} catch {
    Write-Host "⚠️  pre-commit配置失败（可忽略）: $_" -ForegroundColor Yellow
}

# 验证安装
Write-Host ""
Write-Host "🔍 验证安装..." -ForegroundColor Yellow
$packages = @("pytest", "pytest-cov", "ruff", "pyright")
$missing = @()

foreach ($package in $packages) {
    $installed = pip show $package 2>$null
    if ($installed) {
        Write-Host "  ✅ $package" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $package (缺失)" -ForegroundColor Red
        $missing += $package
    }
}

if ($missing.Count -gt 0) {
    Write-Host ""
    Write-Host "⚠️  以下包未安装: $($missing -join ', ')" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✅ 环境初始化完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步：" -ForegroundColor Cyan
Write-Host "  1. 运行测试: python -m pytest tests/unit -v" -ForegroundColor White
Write-Host "  2. 质量检查: make check" -ForegroundColor White
Write-Host "  3. 开发工作流: .\scripts\dev_workflow.ps1" -ForegroundColor White
Write-Host ""
