# JCIA 项目命令别名初始化脚本
# 此脚本添加工程纪律检查的快捷命令到当前 PowerShell 会话

# 设置工作目录
$projectRoot = if (Test-Path ".git") { Get-Location } else { Split-Path -Parent $PSScriptRoot }

if ($null -eq $projectRoot) {
    $projectRoot = Split-Path -Parent $PSScriptRoot
}

$scriptPath = Join-Path $projectRoot "scripts"

Write-Host "📋 JCIA 工程纪律快捷命令已加载" -ForegroundColor Cyan
Write-Host ""
Write-Host "可用命令 (在 VS Code 中使用 Ctrl+Shift+P 或终端直接输入):" -ForegroundColor Yellow
Write-Host ""
Write-Host "  /check     - 工程纪律完整检查 (6项检查)" -ForegroundColor Green
Write-Host "  /check-fast - 快速检查 (lint+type+unit)" -ForegroundColor Green
Write-Host "  /check-full - 全量检查 (pre-commit 等效)" -ForegroundColor Green
Write-Host "  /lint      - 代码规范检查 (Ruff)" -ForegroundColor Green
Write-Host "  /format    - 代码格式化 (Ruff)" -ForegroundColor Green
Write-Host "  /typecheck - 类型检查 (Pyright)" -ForegroundColor Green
Write-Host "  /security  - 安全扫描 (Bandit)" -ForegroundColor Green
Write-Host "  /test      - 运行单元测试 (Pytest)" -ForegroundColor Green
Write-Host "  /test-cov  - 带覆盖率的测试" -ForegroundColor Green
Write-Host "  /all       - 运行所有检查" -ForegroundColor Green
Write-Host "  /clean     - 清理构建产物" -ForegroundColor Green
Write-Host "  /review    - 代码走查 (diff)" -ForegroundColor Green
Write-Host "  /commit    - Git 提交代码 (交互式)" -ForegroundColor Green
Write-Host "  /commit-lite - Git 提交代码 (不跑全量检查)" -ForegroundColor Green
Write-Host "  /commit-auto - Git 提交代码 (自动消息)" -ForegroundColor Green
Write-Host "  /save      - Git 快速保存" -ForegroundColor Green
Write-Host "  /status    - Git 状态" -ForegroundColor Green
Write-Host "  /log       - Git 日志" -ForegroundColor Green


Write-Host ""
Write-Host "快捷键:" -ForegroundColor Yellow
Write-Host "  Ctrl+Shift+A - 运行工程纪律完整检查" -ForegroundColor Cyan
Write-Host ""

# 定义快捷命令函数
function Invoke-Check {
    param([string]$Task = "check")
    $checkScript = Join-Path $scriptPath "enforce_discipline.ps1"

    switch ($Task.ToLower()) {
        "check" {
            Write-Host "🔍 运行工程纪律完整检查..." -ForegroundColor Cyan
            powershell -ExecutionPolicy Bypass -File $checkScript
        }
        "check-fast" {
            Write-Host "⚡ 运行快速检查 (lint+type+unit)..." -ForegroundColor Cyan
            .venv\Scripts\python -m ruff check jcia tests
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
            .venv\Scripts\python -m pyright jcia tests
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
            .venv\Scripts\python -m pytest tests/unit -q
        }
        "check-full" {
            Write-Host "🧪 运行全量检查 (pre-commit 等效)..." -ForegroundColor Cyan
            powershell -ExecutionPolicy Bypass -File $checkScript
        }

        "lint" {
            Write-Host "📝 运行代码规范检查..." -ForegroundColor Cyan
            .venv\Scripts\python -m ruff check jcia tests
        }
        "format" {
            Write-Host "🎨 运行代码格式化..." -ForegroundColor Cyan
            .venv\Scripts\python -m ruff format jcia tests
        }
        "typecheck" {
            Write-Host "🔍 运行类型检查..." -ForegroundColor Cyan
            .venv\Scripts\python -m pyright jcia tests
        }
        "security" {
            Write-Host "🔒 运行安全扫描..." -ForegroundColor Cyan
            .venv\Scripts\python -m bandit -r jcia -c pyproject.toml
        }
        "test" {
            Write-Host "🧪 运行单元测试..." -ForegroundColor Cyan
            .venv\Scripts\python -m pytest tests/unit -v --tb=short -q
        }
        "test-cov" {
            Write-Host "🧪 运行单元测试 (带覆盖率)..." -ForegroundColor Cyan
            .venv\Scripts\python -m pytest tests/unit -v --cov=jcia --cov-report=term-missing
        }
        "all" {
            Write-Host "🔄 运行所有检查..." -ForegroundColor Cyan
            Invoke-Check "lint"
            Invoke-Check "format"
            Invoke-Check "typecheck"
            Invoke-Check "security"
            Invoke-Check "test"
        }
        "clean" {
            Write-Host "🧹 清理构建产物..." -ForegroundColor Cyan
            Remove-Item -Path build, dist, *.egg-info, htmlcov, .pytest_cache, .mypy_cache, .ruff_cache -Recurse -Force -ErrorAction SilentlyContinue
            Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
            Get-ChildItem -Recurse -File -Filter *.pyc | Remove-Item -Force -ErrorAction SilentlyContinue
            Write-Host "✓ 清理完成" -ForegroundColor Green
        }
        "commit" {
            Write-Host "📝 Git 提交代码..." -ForegroundColor Cyan
            $message = Read-Host -Prompt '输入提交信息: '
            if ($message) {
                git add .
                git commit -m $message
                Write-Host "✓ 提交成功" -ForegroundColor Green
            } else {
                Write-Host "✗ 提交取消" -ForegroundColor Yellow
            }
        }
        "commit-lite" {
            Write-Host "📝 Git 提交代码 (不跑全量检查)..." -ForegroundColor Cyan
            $message = Read-Host -Prompt '输入提交信息: '
            if ($message) {
                git add .
                git commit -m $message
                Write-Host "✓ 提交成功 (未运行全量检查)" -ForegroundColor Green
            } else {
                Write-Host "✗ 提交取消" -ForegroundColor Yellow
            }
        }

        "commit-auto" {
            Write-Host "📝 Git 自动提交..." -ForegroundColor Cyan
            $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm'
            git add .
            git commit -m "chore: auto commit at $timestamp"
            Write-Host "✓ 自动提交完成" -ForegroundColor Green
        }
        "save" {
            Write-Host "💾 Git 快速保存..." -ForegroundColor Cyan
            $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm'
            git add .
            git commit -m "chore: save progress at $timestamp"
            Write-Host "✓ 快速保存完成" -ForegroundColor Green
        }
        "status" {

            Write-Host "📊 Git 状态..." -ForegroundColor Cyan
            git status
        }
        "log" {
            Write-Host "📋 Git 日志 (最近10条)..." -ForegroundColor Cyan
            git log --oneline -10
        }
        "review" {
            Write-Host "📋 显示 diff 摘要 (未暂存/已暂存)..." -ForegroundColor Cyan
            Write-Host "--- 未暂存 ---" -ForegroundColor Yellow
            git diff --stat
            Write-Host "--- 已暂存 ---" -ForegroundColor Yellow
            git diff --cached --stat
            Write-Host "🧭 提示: 深度代码走查请在 CodeBuddy 中运行 code-explorer 代理。" -ForegroundColor Yellow
        }
        default {
            Write-Host "❌ 未知命令: $Task" -ForegroundColor Red
            Write-Host "可用命令: check, check-fast, check-full, lint, format, typecheck, security, test, test-cov, all, clean, review, commit, commit-lite, commit-auto, status, log, save" -ForegroundColor Yellow
        }
    }
}


# 导出函数
Export-ModuleMember -Function Invoke-Check

# 创建别名
Set-Alias -Name "/check" -Value Invoke-Check
Set-Alias -Name "/check-fast" -Value { Invoke-Check "check-fast" }
Set-Alias -Name "/check-full" -Value { Invoke-Check "check-full" }
Set-Alias -Name "/lint" -Value { Invoke-Check "lint" }
Set-Alias -Name "/format" -Value { Invoke-Check "format" }
Set-Alias -Name "/typecheck" -Value { Invoke-Check "typecheck" }
Set-Alias -Name "/security" -Value { Invoke-Check "security" }
Set-Alias -Name "/test" -Value { Invoke-Check "test" }
Set-Alias -Name "/test-cov" -Value { Invoke-Check "test-cov" }
Set-Alias -Name "/all" -Value { Invoke-Check "all" }
Set-Alias -Name "/clean" -Value { Invoke-Check "clean" }
Set-Alias -Name "/review" -Value { Invoke-Check "review" }
Set-Alias -Name "/commit" -Value { Invoke-Check "commit" }
Set-Alias -Name "/commit-lite" -Value { Invoke-Check "commit-lite" }
Set-Alias -Name "/commit-auto" -Value { Invoke-Check "commit-auto" }
Set-Alias -Name "/save" -Value { Invoke-Check "save" }
Set-Alias -Name "/status" -Value { Invoke-Check "status" }
Set-Alias -Name "/log" -Value { Invoke-Check "log" }



Write-Host "✓ 命令别名已加载到当前会话" -ForegroundColor Green
Write-Host ""
Write-Host "使用示例:" -ForegroundColor Yellow
Write-Host "  /check       # 运行完整工程纪律检查" -ForegroundColor White
Write-Host "  /check-fast  # 快速检查 (lint+type+unit)" -ForegroundColor White
Write-Host "  /check-full  # 全量检查 (pre-commit 等效)" -ForegroundColor White
Write-Host "  /test        # 只运行测试" -ForegroundColor White
Write-Host "  /format       # 只格式化代码" -ForegroundColor White
Write-Host "  /review      # 显示 diff 摘要" -ForegroundColor White
Write-Host "  /commit      # 提交代码 (交互式)" -ForegroundColor White
Write-Host "  /commit-lite # 提交代码 (不跑全量检查)" -ForegroundColor White
Write-Host "  /commit-auto  # 提交代码 (自动消息)" -ForegroundColor White
Write-Host "  /save        # 快速保存当前成果" -ForegroundColor White
Write-Host "" 


