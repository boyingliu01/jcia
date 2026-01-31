# Pytest 测试脚本 (PowerShell)

$ErrorActionPreference = "Continue"

$projectPath = "e:\Study\LLM\Java代码变更影响分析"
$outputPath = "e:\Study\LLM\Java代码变更影响分析\test_output"

Set-Location $projectPath

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Pytest 单元测试报告" -ForegroundColor Cyan
Write-Host "开始时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 确保输出目录存在
if (-not (Test-Path $outputPath)) {
    New-Item -ItemType Directory -Path $outputPath -Force | Out-Null
}

# 执行单元测试
python -m pytest tests/unit -v --tb=short 2>&1 | Tee-Object -FilePath "$outputPath\pytest_results.txt"

$exitCode = $LASTEXITCODE

Write-Host ""
Write-Host "测试退出码: $exitCode" -ForegroundColor $(if ($exitCode -eq 0) { "Green" } else { "Red" })
Write-Host "结束时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

exit $exitCode
