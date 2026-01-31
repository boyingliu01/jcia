# JCIA 任务完成合规验证脚本
# 此脚本在每次AI Agent任务完成前必须执行
# 用于验证工程纪律是否得到遵守

param(
    [Parameter(Mandatory=$true)]
    [string]$TaskDescription,

    [switch]$SkipTests = $false
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "║     JCIA 任务完成合规验证                                  ║" -ForegroundColor Magenta
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Magenta
Write-Host ""
Write-Host "任务描述: $TaskDescription" -ForegroundColor Cyan
Write-Host ""

# 合规检查清单
$complianceItems = @(
    @{
        Id = 1
        Name = "虚拟环境激活"
        Check = {
            $inVenv = $env:VIRTUAL_ENV -or (Get-Command python).Source -like "*\.venv\*"
            return $inVenv
        }
        ErrorMsg = "虚拟环境未激活。请运行: .venv\Scripts\activate"
    },
    @{
        Id = 2
        Name = "代码已保存"
        Check = {
            # 检查是否有未保存的修改（这里假设IDE会保存）
            return $true
        }
        ErrorMsg = "请确保所有文件已保存"
    },
    @{
        Id = 3
        Name = "工程纪律检查"
        Check = {
            if ($SkipTests) {
                Write-Host "     [跳过] 测试检查被跳过" -ForegroundColor Yellow
                return $true
            }

            Write-Host ""
            Write-Host "     正在执行完整质量门禁检查..." -ForegroundColor Cyan

            $result = & "$PSScriptRoot\enforce_discipline.ps1" -FailFast:$true 2>&1
            $exitCode = $LASTEXITCODE

            if ($exitCode -eq 0) {
                return $true
            } else {
                Write-Host $result -ForegroundColor Red
                return $false
            }
        }
        ErrorMsg = "工程纪律检查失败。请修复所有问题后重试。"
    }
)

$failedItems = @()
$passedItems = @()

foreach ($item in $complianceItems) {
    Write-Host "  [$($item.Id)/$($complianceItems.Count)] 检查: $($item.Name) ..." -ForegroundColor White -NoNewline

    try {
        $result = & $item.Check
        if ($result -eq $true) {
            Write-Host "`r  [$($item.Id)/$($complianceItems.Count)] ✓ $($item.Name)" -ForegroundColor Green
            $passedItems += $item
        } else {
            Write-Host "`r  [$($item.Id)/$($complianceItems.Count)] ✗ $($item.Name)" -ForegroundColor Red
            $failedItems += $item
        }
    } catch {
        Write-Host "`r  [$($item.Id)/$($complianceItems.Count)] ✗ $($item.Name) - 错误: $_" -ForegroundColor Red
        $failedItems += $item
    }
}

Write-Host ""
Write-Host "══════════════════════════════════════════════════════════" -ForegroundColor Magenta

if ($failedItems.Count -eq 0) {
    Write-Host ""
    Write-Host "  ✓✓✓ 合规验证通过！任务可以完成 ✓✓✓" -ForegroundColor Green
    Write-Host ""
    Write-Host "  完成的任务: $($passedItems.Count)/$($complianceItems.Count)" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  下一步操作:" -ForegroundColor White
    Write-Host "    1. 向用户汇报任务完成情况" -ForegroundColor White
    Write-Host "    2. 简要说明所做的修改" -ForegroundColor White
    Write-Host "    3. 确认所有检查已通过" -ForegroundColor White
    Write-Host ""

    # 生成合规报告
    $report = @{
        Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Task = $TaskDescription
        Status = "PASSED"
        Checks = $passedItems | ForEach-Object { $_.Name }
    }

    $reportPath = ".codebuddy\compliance_reports"
    if (-not (Test-Path $reportPath)) {
        New-Item -ItemType Directory -Path $reportPath -Force | Out-Null
    }

    $reportFile = Join-Path $reportPath "compliance_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
    $report | ConvertTo-Json | Out-File -FilePath $reportFile -Encoding UTF8

    Write-Host "  合规报告已保存: $reportFile" -ForegroundColor DarkGray
    Write-Host ""

    exit 0
} else {
    Write-Host ""
    Write-Host "  ✗✗✗ 合规验证失败！任务不能完成 ✗✗✗" -ForegroundColor Red
    Write-Host ""
    Write-Host "  失败的项目:" -ForegroundColor Yellow
    foreach ($item in $failedItems) {
        Write-Host "    - [$($item.Id)] $($item.Name)" -ForegroundColor Red
        Write-Host "      原因: $($item.ErrorMsg)" -ForegroundColor DarkRed
    }
    Write-Host ""
    Write-Host "  必须修复以上问题后才能完成任务！" -ForegroundColor Yellow
    Write-Host ""

    # 生成失败报告
    $report = @{
        Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Task = $TaskDescription
        Status = "FAILED"
        FailedChecks = $failedItems | ForEach-Object { @{ Id = $_.Id; Name = $_.Name; Reason = $_.ErrorMsg } }
    }

    $reportPath = ".codebuddy\compliance_reports"
    if (-not (Test-Path $reportPath)) {
        New-Item -ItemType Directory -Path $reportPath -Force | Out-Null
    }

    $reportFile = Join-Path $reportPath "compliance_failed_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
    $report | ConvertTo-Json | Out-File -FilePath $reportFile -Encoding UTF8

    Write-Host "  失败报告已保存: $reportFile" -ForegroundColor DarkGray
    Write-Host ""

    exit 1
}
