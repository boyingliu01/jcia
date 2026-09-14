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
- Phase 4 跨服务远程调用集成：`analyze` 命令新增 `--detect-remote-calls` 开关，将远程调用检测（Dubbo/Feign/HTTP/MQ）融合进影响图并启用多维度严重度评分；采用向后兼容的可选依赖注入（默认关闭），涉及 analyze_impact 用例、ImpactAnalysisService 与 CLI

### Changed
- 重命名 Adapters 层数据库门面 `jcia/adapters/database/sqlite_adapter.py` → `sqlite_database_adapter.py`（类 `SQLiteDatabaseAdapter`），消除与基础设施层 `jcia/infrastructure/database/sqlite_adapter.py`（类 `SQLiteAdapter`）的**同名文件歧义**；两层文件名各自与类名对齐（符合 `pydriller_adapter.py` → `PyDrillerAdapter` 约定）。同步更新唯一导入点、单测与 AGENTS/CLAUDE/PROJECT_STATUS 文档；数据库相关 35 个单测全绿

### Fixed
- 修复 TestSuiteResult 类的 pytest 收集警告
- 修复 AnalyzeImpactUseCase 的 is_empty() 方法调用
- 修复测试文件中的重复代码和错误断言
- 修复 CLI 中的类型错误和 lint 问题
- 修复 openai_adapter 的 None 安全隐患（构建 messages 时的潜在解引用）
- 为 codeql / starts / java_all_call_graph / skywalking 适配器补充类型注解，消除 mypy 严格模式报错
- 创建 jcia/cli/__init__.py，修复 AGENTS.md 记录的 CLI 入口点缺失问题（entry point 指向 jcia.cli.main:cli）
- 补齐 jcia/infrastructure/database/__init__.py 包标记
- 修复 PyDrillerAdapter 变更文件路径缺陷：原用 `ModifiedFile.filename`（仅 basename，如 `CspFilter.java`）作为 `file_path`，导致下游 `repo_path / file_path` 无法定位磁盘文件，远程调用检测恒报 "File not found" 并返回 0 结果；改用 `new_path`（相对仓库根的完整路径）并统一分隔符为正斜杠，缺失时回退 `filename`。该缺陷此前因单测 mock 把 `filename` 设为完整路径而被掩盖

### Testing
- 测试套件：991 passed / 31 skipped
- 实测总覆盖率 84% → 93%（目标 ≥ 80%）；Adapters 层覆盖率 78.04% → 93%（目标 ≥ 75%）
- 新增 4 个工具适配器单元测试，将薄弱环节拉满：
  - `skywalking_call_chain_adapter` 33% → 100%
  - `java_all_call_graph_adapter` 61% → 100%（mock `subprocess.run`/`urllib.request.urlopen` 隔离 Java/下载边界，覆盖缓存/解析/注解/远程调用识别/服务拓扑各分支）
  - `maven_surefire_test_executor` 61% → 100%（mock `subprocess.run` 隔离 Maven 边界，覆盖增量测试/覆盖率报告/JaCoCo 配置/结果解析）
  - `openai_adapter` 63% → 99%（`sys.modules` 注入 fake `openai` 模块覆盖真实客户端路径与 ImportError 回退、重试退避；仅 1 行为不可达死代码）
- 新增 SkyWalkingAdapter 单元测试（34 例）：mock `_execute_graphql`/`requests.post` 隔离网络边界，覆盖率 13% → 100%
- 新增 4 个 PyDriller 路径回归测试（new_path 全路径 / 反斜杠归一化 / filename 回退 / test 文件识别）
- 重构 pydriller 集成测试改用可靠的 GitPython commit range，消除 3 个 flaky 用例
- 测试 fixture 做 hermetic 隔离，移除对真实外部环境的隐式依赖
- 修正 volcengine 集成测试对 provider 的错误断言（普通 Enum 成员不等于字符串）
- 新增 tests.* 的 mypy override，对齐 pyright 对测试代码的既定放宽

### Development
- Pre-commit hooks 配置
- 代码质量工具（Ruff, Pyright, Bandit）
- Makefile 自动化命令
- 覆盖率门配置：omit 根目录一次性脚本，对齐 source=["jcia"]（实测总覆盖率 81%）
- mypy 配置对齐项目主类型检查器 pyright 的既定放宽策略
- 新增 architecture.yaml，以机器可读形式记录 Clean Architecture 分层依赖规则

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
