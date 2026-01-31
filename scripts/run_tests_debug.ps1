# 运行测试并捕获详细错误

cd "E:\Study\LLM\Java代码变更影响分析"

Write-Host "Running tests..." -ForegroundColor Cyan

# 使用python直接运行pytest
$output = & .venv\Scripts\python.exe -m pytest tests/unit -v --tb=short 2>&1

# 输出到控制台
$output | ForEach-Object { Write-Host $_ }

# 保存到文件
$output | Out-File -FilePath "test_output\test_debug.log" -Encoding UTF8

Write-Host "`nTest output saved to test_output\test_debug.log" -ForegroundColor Green
