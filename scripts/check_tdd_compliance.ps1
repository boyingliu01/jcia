# TDD 合规性检查脚本（PowerShell版本）
#
# 检查测试文件和实现文件的创建时间，确保遵循 TDD 原则
# - 测试文件必须早于实现文件创建
# - 禁止先实现后测试的开发方式

param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)

Write-Host "═" * 60 -ForegroundColor Cyan
Write-Host "TDD 合规性检查" -ForegroundColor Cyan
Write-Host "═" * 60 -ForegroundColor Cyan
Write-Host "项目根目录: $ProjectRoot"
Write-Host ""

# 获取测试文件和实现文件配对
function Get-FilePairs {
    param([string]$ProjectRoot)

    $filePairs = @()

    # 遍历 tests/unit 目录下的测试文件
    $testFiles = Get-ChildItem -Path "$ProjectRoot\tests\unit" -Filter "test_*.py" -Recurse -File

    Write-Host "测试文件数量: $($testFiles.Count)"

    foreach ($testFile in $testFiles) {
        # 解析路径
        # E:\Study\LLM\Java代码变更影响分析\tests\unit\adapters\test_git\test_pydriller_adapter.py
        $testFullPath = $testFile.FullName
        $relPath = $testFullPath.Replace("$ProjectRoot\tests\unit\", "")

        Write-Host "处理: $relPath"

        # 分割路径: adapters\test_git\test_pydriller_adapter.py
        $parts = $relPath.Split([IO.Path]::DirectorySeparatorChar)

        # 适配器目录映射
        # test_git -> git
        # test_maven -> maven
        # test_ai -> ai
        if ($parts.Length -ge 2 -and $parts[1].StartsWith("test_")) {
            $parts[1] = $parts[1].Substring(5)  # 移除 test_ 前缀
        } elseif ($parts[0].StartsWith("test_")) {
            $parts[0] = $parts[0].Substring(5)
        }

        # 构建实现文件路径
        $implPath = Join-Path $ProjectRoot "jcia"
        foreach ($part in $parts) {
            $implPath = Join-Path $implPath $part
        }

        Write-Host "  实现路径: $implPath"

        # 检查实现文件是否存在
        if (Test-Path $implPath) {
            $filePairs += @{
                TestFile = $testFile.FullName
                ImplFile = $implPath
            }
        }
    }

    return $filePairs
}

# 检查 TDD 合规性
function Test-TDDCompliance {
    param([array]$FilePairs)

    $allCompliant = $true
    $violations = @()

    foreach ($pair in $FilePairs) {
        $testTime = (Get-Item $pair.TestFile).LastWriteTime
        $implTime = (Get-Item $pair.ImplFile).LastWriteTime
        $diff = ($testTime - $implTime).TotalSeconds

        # 测试文件必须早于或等于实现文件时间
        # 允许2分钟的容差（批量创建）
        if ($testTime -gt $implTime -and $diff -gt 120) {
            $allCompliant = $false
            $violations += @{
                TestFile = $pair.TestFile
                ImplFile = $pair.ImplFile
                TestTime = $testTime
                ImplTime = $implTime
                DiffSeconds = $diff
            }
        }
    }

    return $allCompliant, $violations
}

# 打印违规信息
function Show-Violations {
    param([array]$Violations)

    Write-Host "❌ TDD 合规性检查失败！" -ForegroundColor Red
    Write-Host ""
    Write-Host "发现以下违规（测试文件晚于实现文件创建）:" -ForegroundColor Yellow
    Write-Host ""

    foreach ($v in $Violations) {
        $relTest = $v.TestFile.Replace($ProjectRoot, "")
        $relImpl = $v.ImplFile.Replace($ProjectRoot, "")
        Write-Host "  📄 测试文件: $relTest" -ForegroundColor Yellow
        Write-Host "  💻 实现文件: $relImpl" -ForegroundColor Yellow
        Write-Host "  ⏰ 时间差: $($v.DiffSeconds.ToString('0.0')) 秒（测试文件晚）" -ForegroundColor Yellow
        Write-Host ""
    }

    Write-Host "📝 TDD 原则要求:" -ForegroundColor Cyan
    Write-Host "  1. 先编写测试代码（红阶段）" -ForegroundColor White
    Write-Host "  2. 运行测试确认失败" -ForegroundColor White
    Write-Host "  3. 实现功能代码让测试通过（绿阶段）" -ForegroundColor White
    Write-Host "  4. 重构优化代码（蓝阶段）" -ForegroundColor White
    Write-Host ""
    Write-Host "请按照 TDD 流程重新开发！" -ForegroundColor Red
}

# 主逻辑
try {
    # 获取文件配对
    $filePairs = Get-FilePairs -ProjectRoot $ProjectRoot
    Write-Host "找到 $($filePairs.Count) 对测试/实现文件`n"

    if ($filePairs.Count -eq 0) {
        Write-Host "⚠️  未找到测试/实现文件对，跳过检查" -ForegroundColor Yellow
        exit 0
    }

    # 检查合规性
    $allCompliant, $violations = Test-TDDCompliance -FilePairs $filePairs

    if ($allCompliant) {
        Write-Host "✅ TDD 合规性检查通过！" -ForegroundColor Green
        Write-Host "   所有 $($filePairs.Count) 个文件对都遵循 TDD 原则" -ForegroundColor Green
        exit 0
    } else {
        Show-Violations -Violations $violations
        exit 1
    }
} catch {
    Write-Host "❌ 检查过程出错: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
