# JCIA 项目 - 自动安装 Dev-Workflow (Python版本)

$ErrorActionPreference = "Stop"

Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   Dev-Workflow 安装 - JCIA Python 项目              ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# 配置
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DevWorkflowRoot = "$ProjectRoot/Dev-workflow"
$UserHome = $env:USERPROFILE
$TargetRoot = "$UserHome\.dev-workflow"

Write-Host "项目根目录: $ProjectRoot" -ForegroundColor Gray
Write-Host "Dev-Workflow 源: $DevWorkflowRoot" -ForegroundColor Gray
Write-Host "安装目标: $TargetRoot" -ForegroundColor Gray
Write-Host ""

# 检查源目录
if (-not (Test-Path $DevWorkflowRoot)) {
    Write-Host "❌ 错误: Dev-workflow 目录不存在" -ForegroundColor Red
    exit 1
}

# 步骤 1: 复制核心原则层到用户目录
Write-Host "步骤 1/3: 安装核心原则层" -ForegroundColor Yellow
Write-Host "------------------------" -ForegroundColor Gray
Write-Host ""

$coreSource = "$DevWorkflowRoot/core"
$coreTarget = "$TargetRoot/core"

# 创建目标目录
if (-not (Test-Path $coreTarget)) {
    New-Item -ItemType Directory -Path $coreTarget -Force | Out-Null
    Write-Host "✅ 创建目录: $coreTarget" -ForegroundColor Green
}

# 复制文件
$coreFiles = Get-ChildItem -Path $coreSource -Recurse -File
foreach ($file in $coreFiles) {
    $relativePath = $file.FullName.Substring($coreSource.Length + 1)
    $destPath = Join-Path $coreTarget $relativePath

    $destDir = Split-Path -Parent $destPath
    if (-not (Test-Path $destDir)) {
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    }

    Copy-Item -Path $file.FullName -Destination $destPath -Force
    Write-Host "  ✓ $($file.Name)" -ForegroundColor White
}

Write-Host "✅ 核心原则层安装完成" -ForegroundColor Green
Write-Host ""

# 步骤 2: 复制 Python 工具链到用户目录
Write-Host "步骤 2/3: 安装 Python 工具链" -ForegroundColor Yellow
Write-Host "------------------------" -ForegroundColor Gray
Write-Host ""

$pythonSource = "$DevWorkflowRoot/toolchains/python"
$pythonTarget = "$TargetRoot/toolchains/python"

# 创建目标目录
if (-not (Test-Path $pythonTarget)) {
    New-Item -ItemType Directory -Path $pythonTarget -Force | Out-Null
}

# 复制 Python 工具链文件
Copy-Item -Path "$pythonSource/*" -Destination $pythonTarget -Recurse -Force

Write-Host "✅ Python 工具链安装完成" -ForegroundColor Green
Write-Host ""

# 步骤 3: 复制管理脚本
Write-Host "步骤 3/3: 安装管理脚本" -ForegroundColor Yellow
Write-Host "------------------------" -ForegroundColor Gray
Write-Host ""

$scriptsSource = "$DevWorkflowRoot/scripts"
$scriptsTarget = "$TargetRoot/scripts"

# 创建目标目录
if (-not (Test-Path $scriptsTarget)) {
    New-Item -ItemType Directory -Path $scriptsTarget -Force | Out-Null
}

# 复制脚本文件
Copy-Item -Path "$scriptsSource/*.psm1" -Destination $scriptsTarget -Force

Write-Host "✅ 管理脚本安装完成" -ForegroundColor Green
Write-Host ""

# 步骤 4: 在项目中创建 .speckit 目录（SDD工作流）
Write-Host "步骤 4/5: 初始化 SDD 工作流" -ForegroundColor Yellow
Write-Host "------------------------" -ForegroundColor Gray
Write-Host ""

$speckitDir = "$ProjectRoot/.speckit"
if (-not (Test-Path $speckitDir)) {
    New-Item -ItemType Directory -Path $speckitDir -Force | Out-Null
    Write-Host "✅ 创建 .speckit 目录" -ForegroundColor Green
} else {
    Write-Host "✓ .speckit 目录已存在" -ForegroundColor White
}

# 复制 SDD 模板
$speckitTemplates = "$DevWorkflowRoot/core/speckit"
Copy-Item -Path "$speckitTemplates/*.template" -Destination $speckitDir -Force
Write-Host "  ✓ 复制 SDD 模板" -ForegroundColor White

# 创建宪法文件
$constitutionFile = "$speckitDir/constitution.md"
if (-not (Test-Path $constitutionFile)) {
    @"
# JCIA 项目宪法

## 项目使命

JCIA (Java Code Impact Analyzer) 致力于帮助开发团队：
- 快速识别代码变更影响范围
- 智能选择测试用例
- 自动分析回归问题
- 提升测试覆盖率

## 核心价值观

1. **质量优先**: 代码质量和测试覆盖率是首要目标
2. **持续改进**: 不断优化工具和流程
3. **用户导向**: 简化开发者日常工作
4. **技术卓越**: 采用最佳实践和现代技术

## 开发原则

- 遵循 TDD (测试驱动开发)
- 遵循 Clean Architecture (清洁架构)
- 遵循 Clean Code (清洁代码)
- 遵循 SOLID 原则
- 遵循 SDD (规格驱动开发)

## 项目目标

- 提供准确的变更影响分析
- 支持 Maven 项目
- 提供智能测试选择
- 自动生成回归测试报告
- 集成 CI/CD 流程

---
"创建时间: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
"@ | Out-File -FilePath $constitutionFile -Encoding utf8
    Write-Host "  ✓ 创建 constitution.md" -ForegroundColor White
}

Write-Host "✅ SDD 工作流�完成" -ForegroundColor Green
Write-Host ""

# 步骤 5: 创建代码审查清单
Write-Host "步骤 5/5: 创建代码审查清单" -ForegroundColor Yellow
Write-Host "------------------------" -ForegroundColor Gray
Write-Host ""

$checklistFile = "$ProjectRoot/code-review-checklist.md"
$checklistTemplate = "$DevWorkflowRoot/core/principles/code-review-checklist.md"

if (Test-Path $checklistTemplate) {
    Copy-Item -Path $checklistTemplate -Destination $checklistFile -Force
    Write-Host "✅ 代码审查清单已创建" -ForegroundColor Green
} else {
    Write-Host "⚠️  检查清单模板不存在，跳过" -ForegroundColor Yellow
}

Write-Host ""

# 完成
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                   安装完成！                              ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

Write-Host "安装位置: $TargetRoot" -ForegroundColor Cyan
Write-Host ""
Write-Host "已安装组件:" -ForegroundColor Yellow
Write-Host "  ✓ 核心原则层" -ForegroundColor White
Write-Host "  ✓ Python 工具链" -ForegroundColor White
Write-Host "  ✓ 管理脚本" -ForegroundColor White
Write-Host "  ✓ SDD 工作流模板" -ForegroundColor White
Write-Host "  ✓ 代码审查清单" -ForegroundColor White
Write-Host ""

Write-Host "核心原则文档位于: $TargetRoot/core/principles/" -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步操作:" -ForegroundColor Yellow
Write-Host "1. 阅读核心原则文档了解开发规范" -ForegroundColor White
Write-Host "2. 开始新功能前使用 TDD 流程（红-绿-蓝）" -ForegroundColor White
Write-Host "3. 使用 .speckit 进行 SDD 规格驱动开发" -ForegroundColor White
Write-Host "4. 提交代码前检查 code-review-checklist.md" -ForegroundColor White
Write-Host ""
Write-Host "主要文档:" -ForegroundColor Cyan
Write-Host "  - README.md: 完整使用指南" -ForegroundColor White
Write-Host "  - QUICK_START.md: 快速开始" -ForegroundColor White
Write-Host "  - $TargetRoot/core/principles/sdd-workflow.md: SDD 工作流" -ForegroundColor White
Write-Host "  - $TargetRoot/core/principles/tdd-workflow.md: TDD 工作流" -ForegroundColor White
Write-Host "  - $TargetRoot/core/principles/clean-architecture.md: 清洁架构" -ForegroundColor White
