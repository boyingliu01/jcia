# 修复pytest-cov问题

Write-Host "🔍 检查pytest和pytest-cov..." -ForegroundColor Cyan

# 检查虚拟环境
$venvPython = ".venv\Scripts\python.exe"
$venvPip = ".venv\Scripts\pip.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "❌ 虚拟环境Python不存在" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "📋 当前虚拟环境中的包：" -ForegroundColor Yellow
& $venvPip list | findstr pytest

Write-Host ""
Write-Host "🔧 重新安装pytest和pytest-cov..." -ForegroundColor Yellow

# 先卸载
& $venvPip uninstall pytest pytest-cov -y 2>$null

# 安装兼容版本
& $venvPip install pytest==8.3.5 pytest-cov==5.0.0

Write-Host ""
Write-Host "✅ 安装完成，验证中..." -ForegroundColor Yellow

# 验证
& $venvPython -m pytest --version

Write-Host ""
Write-Host "🧪 运行测试验证..." -ForegroundColor Yellow
& $venvPython -m pytest tests/unit -v --tb=short
