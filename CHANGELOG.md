# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [0.2.0] - 2026-09-14

> 首个正式发布版本：在既有累计功能之上完成发布就绪收尾——补齐 LICENSE、接入 CI/CD、校正仓库元数据与文档一致性，版本升至 0.2.0（Beta）。

### Release Readiness
- 新增根目录 `LICENSE`（MIT），与 `pyproject.toml` / README 的许可证声明对齐
- 新增 GitHub Actions：`ci.yml`（ruff / format / import-linter / pyright / mypy / bandit + Python 3.10–3.12 测试矩阵 + 覆盖率门槛 ≥ 80% + 集成测试非阻断）与 `release.yml`（`v[0-9]*` tag 触发：版本/标签一致性守卫 → `python -m build` + `twine check` + 安装烟测 → PyPI trusted publishing（OIDC）→ 成功后才创建附带产物的 GitHub Release；权限按 job 最小化，不可逆步骤先行以避免"有 Release 无包"的半成品发布）
- 消除版本多源漂移：`setup.py` 退化为裸 `setup()` 骨架，`pyproject.toml` 成为 name/version/dependencies/entry-points/packages 的唯一权威源（原 `setup.py` 仍声明 `version=0.1.0` 与已废弃入口 `jcia.cli:cli`，虽被 `[project]` 覆盖但属潜在隐患）；`promotion/faq.md` 移除废弃的 `python setup.py install` 建议
- 发布元数据校正：`[project.urls]` 及 README / `promotion/*` / `docs/*` / `scripts/*` 中的占位 `github.com/your-org/jcia` 全量替换为真实仓库 `github.com/boyingliu01/jcia`
- 版本 `0.1.0 → 0.2.0`（`pyproject` / `jcia.__version__` / CLI `--version` 统一为单一来源，CLI 改读 `jcia.__version__`）；`Development Status` 由 `3 - Alpha` 升级为 `4 - Beta`
- README 命令行与实况对齐：移除不存在的 `jcia regression` 命令与 `jcia report --output`（实际为必填 `--output-dir`），补齐 `report` / `config` 选项，覆盖率 badge `89% → 93%`
- 修复 `tests/unit/cli/test_main.py` 遗留的 `PT001`（`@pytest.fixture()` 空括号），使全量 `ruff check jcia tests` 通过
- 消除占位邮箱外泄：README「支持」章节的 `jcia-dev@example.org` 经 `readme = "README.md"` 进入 `METADATA` 的 `long_description`，发布后会永久渲染在 PyPI 项目页且不可编辑（yank 亦保留历史），故删除该行、支持渠道只保留 GitHub Issues；同时删除 `jcia/__init__.py` 中全仓零引用的 `__email__ = "jcia@example.com"`（实测已随 wheel 与 sdist 分发）
- `release.yml` 加固：`build` 在 `twine check` 后调用新增的 `scripts/check_dist_placeholders.py`，解开 wheel 与 sdist 的每个成员逐行扫描占位域名（`twine check` 只校验元数据格式、pre-push 的 Gate MW 只比对 commit diff，二者结构上都抓不到这类缺陷）；`publish-pypi` 显式 `skip-existing: "true"`——上游默认为 `false`，一旦发布成功后误点 Re-run all jobs 必返 409，而 `github-release` 因 `needs` 不满足永不执行，会形成「PyPI 已发布、GitHub Release 缺失且 UI 无恢复路径」的终态
- 新增 `docs/RELEASE_RUNBOOK.md`：只收录已实测核实的发布流程——PyPI trusted publisher 字段逐字取值（标签取自 warehouse 模板源码，其中「Workflow name」实际要求填文件名）、2FA 与已验证主邮箱两道硬门槛、标签必须 peel 到 HEAD 的取证姿势、故障恢复路径

### Added
- PROJECT_CONSTITUTION.md - 项目宪法，定义开发原则和流程
- AGENTS.md - Agent 开发指南（更新）
- plan.md - 项目开发计划文档
- plan.json - 项目开发计划（JSON 格式）
- README.md - 完整的项目介绍和快速开始指南
- CONTRIBUTING.md - 详细的贡献指南
- gRPC 远程调用适配器 `jcia/adapters/tools/remote_call/grpc_adapter.py`（`GrpcRemoteCallAdapter`，识别 `XxxGrpc.new(Blocking)Stub`），已接入 `CompositeRemoteCallAdapter`（issue #16）
- 服务发现抽象：`ServiceRegistry` ABC（`jcia/core/interfaces/service_registry.py`，含 `ServiceInfo`）+ `MockServiceRegistry`（`jcia/adapters/tools/service_registry/`）（issue #16）
- 分层领域知识库 `AGENTS.md`：`jcia/adapters/tools/`、`jcia/adapters/tools/remote_call/`、`jcia/core/services/`（issue #17）

### Implemented
- 完整的适配器层实现（Git, Maven, AI, Database）
- 完整的基础设施层实现（Config, Logging, FileSystem, Database）
- 完整的领域服务层实现（ImpactAnalysis, CallChainBuilder, TestSelection, TestGeneration）
- 完整的 CLI 命令行工具（analyze, test, regression, report, config）
- 完整的报告生成模块（HTML, JSON, Markdown）
- 完整的集成测试
- Phase 4 跨服务远程调用集成：`analyze` 命令新增 `--detect-remote-calls` 开关，将远程调用检测（Dubbo/Feign/HTTP/MQ）融合进影响图并启用多维度严重度评分；采用向后兼容的可选依赖注入（默认关闭），涉及 analyze_impact 用例、ImpactAnalysisService 与 CLI
- 架构分层 CI 强制：`[tool.importlinter]` 定义 4 个 contract（主分层栈 + core 禁依赖外层 + infrastructure/reports 限制），`architecture.yaml` 声明同步；`Makefile` 新增 `arch-check` 目标，pre-commit Gate 6 修复（扩展检测 pyproject 配置 + 依据 `lint-imports` 退出码阻断）

### Changed
- 重命名 Adapters 层数据库门面 `jcia/adapters/database/sqlite_adapter.py` → `sqlite_database_adapter.py`（类 `SQLiteDatabaseAdapter`），消除与基础设施层 `jcia/infrastructure/database/sqlite_adapter.py`（类 `SQLiteAdapter`）的**同名文件歧义**；两层文件名各自与类名对齐（符合 `pydriller_adapter.py` → `PyDrillerAdapter` 约定）。同步更新唯一导入点、单测与 AGENTS/CLAUDE/PROJECT_STATUS 文档；数据库相关 35 个单测全绿
- 对齐 ruff 版本至 `0.15.5`（`requirements-dev.txt` + `pyproject.toml` 钉版），消除 venv(0.1.9) 与 pre-commit hook(0.15.5) 的规则集漂移；配置层豁免根脚本角色性规则（T201/E501/C901/PLR1722/G003/SLF001 via `/*.py` per-file-ignores）与既有惰性导入设计（全局豁免 PLC0415），并修复真实告警
- `RemoteCallDetectionService.__init__` 改为**强制注入** `analyzer: RemoteCallAnalyzer`（DIP）， concrete 实现改由组合根 `jcia/cli/main.py` 提供；同步调整相关单测构造

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
- Delphi 三模型交叉走查（whalecloud g-qwen3.8-flash / g-deepseek-v4-flash / g-glm-5.3-flash）发现的缺陷修复：
  - CLI 入口点解析错误（Critical）：`setup.py` 声明 `jcia.cli:main` 而 `jcia/cli/__init__.py` 仅导出 `cli`，`main` 属性实际解析为 import 系统自动绑定的 `jcia.cli.main` 子模块对象（不可调用），安装后的 `jcia` 命令启动即抛 TypeError；`__init__.py` 显式增加 `main = cli` 别名、`setup.py` 入口改为 `jcia.cli:cli`，并新增入口点回归测试
  - `PyDrillerAdapter._collect_commits` 增加祖先关系校验：from_commit 非 to_commit 祖先时，简单 range `<from>..<to>` 会静默返回两分支间的意外提交集，现显式抛 `ValueError`（`from == to` 闭区间语义经测试锁定不变）
  - 移除 `source_code_call_graph_adapter._scan_project` 的 `"/test/" in str(f)` 过滤：该过滤在 Windows 反斜杠路径下失效，且与 `find_test_classes`（依赖测试类缓存做变更→测试选择）功能矛盾，POSIX 上会破坏该功能；改为注释说明测试类必须保留并以测试锁定

### Testing
- 测试套件：1005 passed / 31 skipped（含 Delphi 走查后新增的 4 个回归测试）
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

[Unreleased]: https://github.com/boyingliu01/jcia/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/boyingliu01/jcia/releases/tag/v0.2.0
[0.1.0]: https://github.com/boyingliu01/jcia/releases/tag/v0.1.0
[0.0.1]: https://github.com/boyingliu01/jcia/releases/tag/v0.0.1
