# JCIA 工程纪律强制执行脚本 V2 (修复版)
param(
    [switch]$AutoFix = $false,
    [switch]$FailFast = $true
)

$ErrorActionPreference = "Continue"
$exitCode = 0
$failedChecks = @()

# 颜色定义
$Colors = @{
    Success = "Green"
    Error = "Red"
    Warning = "Yellow"
    Info = "Cyan"
    Title = "Magenta"
}

function Write-Header {
    param([string]$Title)
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor $Colors.Title
    Write-Host "║  $Title" -ForegroundColor $Colors.Title -NoNewline
    Write-Host "$(" " * (52 - $Title.Length))║" -ForegroundColor $Colors.Title
    Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor $Colors.Title
    Write-Host ""
}

function Write-CheckStart {
    param([string]$Name)
    Write-Host "  [执行] $Name ..." -ForegroundColor $Colors.Info -NoNewline
}

function Write-CheckResult {
    param(
        [string]$Name,
        [bool]$Success,
        [string]$Duration,
        [string]$Message = ""
    )
    if ($Success) {
        Write-Host "`r  [✓ PASS] $Name ($Duration)" -ForegroundColor $Colors.Success
        if ($Message) {
            Write-Host "         $Message" -ForegroundColor $Colors.Info
        }
    } else {
        Write-Host "`r  [✗ FAIL] $Name ($Duration)" -ForegroundColor $Colors.Error
        if ($Message) {
            Write-Host "         $Message" -ForegroundColor $Colors.Error
        }
    }
}

function Run-Check {
    param(
        [string]$Name,
        [string]$Command,
        [string]$FixCommand = ""
    )

    Write-CheckStart -Name $Name
    $startTime = Get-Date

    try {
        # 使用 cmd /c 运行命令以确保正确的输出捕获
        $result = cmd /c "$Command 2>&1"
        $exitCode = $LASTEXITCODE

        $duration = ((Get-Date) - $startTime).ToString("ss\.fff") + "s"

        if ($exitCode -eq 0) {
            Write-CheckResult -Name $Name -Success $true -Duration $duration
            return $true
        } else {
            Write-CheckResult -Name $Name -Success $false -Duration $duration -Message "检查失败，退出码: $exitCode"
            Write-Host ""
            Write-Host "--- 输出 ---" -ForegroundColor $Colors.Warning
            Write-Host $result -ForegroundColor $Colors.Error
            Write-Host "--- 结束 ---" -ForegroundColor $Colors.Warning

            if ($AutoFix -and $FixCommand) {
                Write-Host ""
                Write-Host "  [自动修复] 尝试执行: $FixCommand" -ForegroundColor $Colors.Warning
                cmd /c "$FixCommand"
            }

            return $false
        }
    } catch {
        $duration = ((Get-Date) - $startTime).ToString("ss\.fff") + "s"
        Write-CheckResult -Name $Name -Success $false -Duration $duration -Message $_.Exception.Message
        return $false
    }
}

# ═══════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════

Write-Header -Title "JCIA 工程纪律强制检查"

Write-Host "环境检查:" -ForegroundColor $Colors.Info
Write-Host "  虚拟环境: $(if (Test-Path ".venv") { "✓ 存在" } else { "✗ 缺失" })" -ForegroundColor $(if (Test-Path ".venv") { $Colors.Success } else { $Colors.Error })
Write-Host "  Python: $(.venv\Scripts\python --version 2>&1)" -ForegroundColor $Colors.Info
Write-Host "  工作目录: $(Get-Location)" -ForegroundColor $Colors.Info
Write-Host ""

# 检查虚拟环境
if (-not (Test-Path ".venv")) {
    Write-Host "✗ 错误: 虚拟环境不存在，请先运行: python -m venv .venv" -ForegroundColor $Colors.Error
    exit 1
}

# 执行检查
Write-Host "开始执行完整质量门禁检查..." -ForegroundColor $Colors.Info
Write-Host ""

$ruffPass = Run-Check -Name "1. Ruff Lint 代码规范检查" -Command ".venv\Scripts\python -m ruff check jcia tests"
if (-not $ruffPass) {
    $failedChecks += "1. Ruff Lint 代码规范检查"
    if ($FailFast) { Write-Host ""; Write-Host "  检查失败，停止后续检查" -ForegroundColor Yellow }
}

$ruffImportPass = Run-Check -Name "2. Ruff Import 排序检查" -Command ".venv\Scripts\python -m ruff check --select I jcia tests"
if (-not $ruffImportPass) {
    $failedChecks += "2. Ruff Import 排序检查"
    if ($FailFast) { Write-Host ""; Write-Host "  检查失败，停止后续检查" -ForegroundColor Yellow }
}

$formatPass = Run-Check -Name "3. Ruff Format 代码格式化" -Command ".venv\Scripts\python -m ruff format jcia tests --check"
if (-not $formatPass) {
    $failedChecks += "3. Ruff Format 代码格式化"
    if ($FailFast) { Write-Host ""; Write-Host "  检查失败，停止后续检查" -ForegroundColor Yellow }
}

$pyrightPass = Run-Check -Name "4. Pyright 静态类型检查" -Command ".venv\Scripts\python -m pyright jcia tests"
if (-not $pyrightPass) {
    $failedChecks += "4. Pyright 静态类型检查"
    if ($FailFast) { Write-Host ""; Write-Host "  检查失败，停止后续检查" -ForegroundColor Yellow }
}

$banditPass = Run-Check -Name "5. Bandit 安全漏洞扫描" -Command ".venv\Scripts\python -m bandit -r jcia -c pyproject.toml -f txt"
if (-not $banditPass) {
    $failedChecks += "5. Bandit 安全漏洞扫描"
    if ($FailFast) { Write-Host ""; Write-Host "  检查失败，停止后续检查" -ForegroundColor Yellow }
}

$pytestPass = Run-Check -Name "6. Pytest 单元测试" -Command ".venv\Scripts\python -m pytest tests/unit -v --tb=short -q"
if (-not $pytestPass) {
    $failedChecks += "6. Pytest 单元测试"
}
# ═══════════════════════════════════════════════════════════
# 总结报告
# ═══════════════════════════════════════════════════════════

Write-Host ""
Write-Host "══════════════════════════════════════════════════════════" -ForegroundColor $Colors.Title

if ($failedChecks.Count -eq 0) {
    Write-Host ""
    Write-Host "  ✓✓✓ 所有检查通过！工程纪律合格 ✓✓✓" -ForegroundColor $Colors.Success
    Write-Host ""
    Write-Host "  你现在可以安全地提交代码：" -ForegroundColor $Colors.Info
    Write-Host "    git add ." -ForegroundColor White
    Write-Host "    git commit -m '你的提交信息'" -ForegroundColor White
    Write-Host ""
    exit 0
} else {
    Write-Host ""
    Write-Host "  ✗✗✗ 工程纪律检查失败！禁止提交代码 ✗✗✗" -ForegroundColor $Colors.Error
    Write-Host ""
    Write-Host "  失败的检查:" -ForegroundColor $Colors.Warning
    foreach ($failed in $failedChecks) {
        Write-Host "    - $failed" -ForegroundColor $Colors.Error
    }
    Write-Host ""
    Write-Host "  修复步骤:" -ForegroundColor $Colors.Info
    if ($AutoFix) {
        Write-Host "    1. 自动修复已尝试，请检查修改结果" -ForegroundColor White
    } else {
        Write-Host "    1. 运行 'make format' 自动修复格式问题" -ForegroundColor White
        Write-Host "    2. 运行 'make lint' 查看详细错误" -ForegroundColor White
    }
    Write-Host "    3. 手动修复剩余问题" -ForegroundColor White
    Write-Host "    4. 重新运行此脚本直到通过" -ForegroundColor White
    Write-Host ""
    exit 1
}
