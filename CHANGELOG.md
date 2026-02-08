# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- PROJECT_CONSTITUTION.md - 项目宪法，定义开发原则和流程
- AGENTS.md - Agent 开发指南（更新）
- plan.md - 项目开发计划文档
- plan.json - 项目开发计划（JSON 格式）
- README.md - 完整的项目介绍和快速开始指南
- CONTRIBUTING.md - 详细的贡献指南

### Implemented
- 完整的适配器层实现（Git, Maven, AI, Database）
- 完整的基础设施层实现（Config, Logging, FileSystem, Database）
- 完整的领域服务层实现（ImpactAnalysis, CallChainBuilder, TestSelection, TestGeneration）
- 完整的 CLI 命令行工具（analyze, test, regression, report, config）
- 完整的报告生成模块（HTML, JSON, Markdown）
- 完整的集成测试

### Fixed
- 修复 TestSuiteResult 类的 pytest 收集警告
- 修复 AnalyzeImpactUseCase 的 is_empty() 方法调用
- 修复测试文件中的重复代码和错误断言
- 修复 CLI 中的类型错误和 lint 问题

### Testing
- 所有单元测试通过（332 个测试）
- 测试覆盖率 89%（目标 ≥ 80%）
- 适配器层测试覆盖率 > 90%
- 基础设施层测试覆盖率 > 80%
- 服务层测试覆盖率 > 80%
- 用例层测试覆盖率 > 85%

### Development
- Pre-commit hooks 配置
- 代码质量工具（Ruff, Pyright, Bandit）
- Makefile 自动化命令

---

## [0.1.0] - 2026-01-31

### Added
- 项目初始化和基础结构
- Clean Architecture 架构框架
- 核心接口定义（Interfaces Layer）
  - ChangeAnalyzer - 变更分析器接口
  - CallChainAnalyzer - 调用链分析器接口
  - ToolWrapper - 工具包装器接口
  - TestRunRepository - 测试运行仓储接口
  - TestSelector - 测试选择器接口
  - TestGenerator - 测试生成器接口
  - TestExecutor - 测试执行器接口
- 领域实体实现（Entities Layer）
  - ChangeSet - 变更集合
  - FileChange - 文件变更
  - MethodChange - 方法变更
  - CommitInfo - 提交信息
  - ImpactGraph - 影响图
  - ImpactNode - 影响节点
  - ImpactEdge - 影响边
  - TestCase - 测试用例
  - TestSuite - 测试套件
  - TestRun® - 测试运行
  - TestResult - 测试结果
  - TestDiff - 测试差异
  - TestComparison - 测试对比
  - CoverageData - 覆盖率数据
- 枚举类型
  - ChangeType, ChangeStatus
  - ImpactType, ImpactSeverity
  - TestPriority, TestType
  - TestStatus, RunType, RunStatus
- 代码质量工具配置
  - Ruff (linting + formatting)
  - Pyright (type checking - strict mode)
  - Pytest (testing framework)
  - Bandit (security scanning)
  - Pre-commit hooks
- Makefile 自动化命令
- 虚拟环境支持
- 配置文件模板 (.jcia.yaml.example)

### Implemented
- 领域实体的完整单元测试（56个测试，100% 通过）
- 类型安全（Pyright strict mode）
- 代码覆盖率（实体层 100%）

### Documentation
- AGENTS.md - Agent 开发指南
- README.md - 项目介绍
- setup.py - 安装脚本
- requirements.txt / requirements-dev.txt - 依赖管理

---

## [0.0.1] - 2026-01-30

### Added
- Project skeleton creation
- Initial directory structure
- Basic configuration files

---

[Unreleased]: https://github.com/your-org/jcia/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/your-org/jcia/releases/tag/v0.1.0
[0.0.1]: https://github.com/your-org/jcia/releases/tag/v0.0.1
