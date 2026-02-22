# JCIA 项目开发计划

## 项目概述

JCIA (Java Code Impact Analyzer) 是一个Python工具，用于分析Java代码变更的影响范围，支持Maven项目，具有调用链分析、测试生成和回归测试功能。采用清洁架构原则，在领域层、应用层和基础设施层之间有清晰的分离。

---

## 项目目标

### 核心目标
开发一个自动化工具，帮助开发团队在代码变更后快速识别影响范围，智能选择需要运行的测试用例，并提供回归分析能力。

### 要解决的问题

1. **变更影响识别困难**
   - 开发者难以准确判断代码修改影响了哪些模块
   - 缺乏自动化的影响范围分析工具
   - 容易遗漏受影响的测试用例

2. **测试选择效率低**
   - 运行全部测试耗时过长
   - 缺乏基于变更的智能测试选择策略
   - 无法精确识别需要回归测试的用例

3. **回归分析不充分**
   - 难以判断测试失败是否是真正的回归问题
   - 缺乏基线测试和回归测试的对比分析
   - 无法自动识别意外的测试失败

4. **覆盖数据利用不足**
   - 覆盖率数据未被有效利用
   - 缺乏基于覆盖率的测试生成建议
   - 无法自动为未覆盖代码生成测试

### 预期价值

1. **提升开发效率**
   - 减少30-50%的测试执行时间（通过智能测试选择）
   - 自动化影响分析，节省人工评估时间
   - 快速定位受影响的代码模块

2. **提高代码质量**
   - 确保变更影响的代码都有测试覆盖
   - 自动识别回归问题
   - 提供测试生成建议

3. **降低维护成本**
   - 减少因变更导致的意外缺陷
   - 提供清晰的变更影响报告
   - 支持持续集成流水线集成

---

## 设计方案

### 整体架构

采用**清洁架构（Clean Architecture）**，确保业务逻辑与外部依赖解耦：

```
┌─────────────────────────────────────────────────────┐
│                  Adapters Layer                   │
│  (Git, Maven, AI Services, Database)           │
└───────────────┬─────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────┐
│             Infrastructure Layer                │
│  (Repository Implementations, Config, Logging)    │
└───────────────┬─────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────┐
│              Use Cases Layer                   │
│  (Business Orchestration, Transaction Boundaries)  │
└───────┬───────────────┬──────────────────────┘
        │               │
┌───────▼───────────┐  ┌─▼────────────────────┐
│  Services Layer   │  │   Entities Layer     │
│ (Domain Logic)   │  │ (Domain Model)      │
└─────────────────┘  └──────────────────────┘
```

### 核心设计原则

1. **依赖倒置原则（DIP）**
   - 高层模块不依赖低层模块，都依赖抽象
   - 接口定义在核心层，实现在基础设施层
   - 便于单元测试和依赖注入

2. **单一职责原则（SRP）**
   - 每个类/模块只负责一个职责
   - 实体只包含业务逻辑
   - 用例负责编排和协调

3. **开闭原则（OCP）**
   - 通过接口扩展功能，无需修改核心代码
   - 适配器模式支持多种外部系统集成
   - 策略模式支持不同的测试选择算法

### 核心工作流

```
1. 变更分析阶段
   ├─ 获取Git提交差异
   ├─ 识别变更的文件和方法
   └─ 生成变更集合（ChangeSet）

2. 影响分析阶段
   ├─ 构建调用链图
   ├─ 识别上游和下游依赖
   ├─ 评估影响严重程度
   └─ 生成影响图（ImpactGraph）

3. 测试选择阶段
   ├─ STARTS算法选择优先测试
   ├─ 基于覆盖率补充测试
   ├─ 基于影响范围选择测试
   └─ 生成测试用例列表

4. 测试执行阶段
   ├─ 执行基线测试（如有）
   ├─ 执行回归测试
   ├─ 收集测试结果和覆盖率
   └─ 生成测试运行报告

5. 回归分析阶段
   ├─ 对比基线和回归测试结果
   ├─ 识别新增失败和新增通过
   ├─ 判断是否为回归问题
   └─ 生成对比报告
```

---

## 技术选型

### 开发语言：Python 3.10+

**选择理由**：
- 丰富的生态和第三方库
- 清晰的语法和强大的类型系统
- 优秀的测试和代码质量工具
- AI/LLM集成便利

**关键依赖**：
- **pydriller**：Git仓库分析（提取提交差异）
- **networkx**：调用链图构建和分析
- **pyyaml**：配置文件解析
- **click**：命令行界面框架
- **pydantic**：数据验证和序列化
- **rich**：美观的终端输出
- **pytest**：测试框架
- **ruff**：代码质量工具
- **pyright**：静态类型检查

### 测试框架：pytest

**选择理由**：
- 成熟稳定，社区活跃
- 强大的fixture系统
- 丰富的插件生态
- 内置覆盖率支持
- 清晰的测试报告

### 代码质量：ruff + pyright + bandit

**选择理由**：
- **ruff**：快速、现代化的linter，替代多个工具
- **pyright**：微软开发的类型检查器，严格模式
- **bandit**：Python安全漏洞扫描

### 数据库：SQLite / PostgreSQL

**选择理由**：
- **SQLite**：开发和小规模部署，无服务器
- **PostgreSQL**：生产环境，支持高并发和复杂查询
- 通过仓储抽象，支持灵活切换

### 架构模式：Clean Architecture + Repository Pattern

**选择理由**：
- 业务逻辑与外部依赖解耦
- 便于单元测试（mock接口）
- 支持多种实现（适配器）
- 符合SOLID原则

---

## 核心功能

### 1. 变更影响分析

**功能描述**：分析Git提交，识别变更的代码及其影响范围

**技术实现**：
- 使用PyDriller解析Git仓库
- 识别文件级和方法级变更
- 构建调用链图
- 计算影响深度和严重程度

**输出**：
- 变更的文件列表
- 变更的方法列表
- 影响的方法图（上游/下游）
- 严重程度评估（HIGH/MEDIUM/LOW）

### 2. 智能测试选择

**功能描述**：基于变更影响范围，智能选择需要运行的测试用例

**技术实现**：
- STARTS算法（Static Test Assignment for Regression Test Selection）
- 基于调用链优先级排序
- 结合覆盖率数据补充测试
- 支持多种选择策略

**输出**：
- 优先级排序的测试用例列表
- 选择理由说明
- 预估执行时间

### 3. 回归分析

**功能描述**：对比基线测试和回归测试结果，识别回归问题

**技术实现**：
- 保存基线测试结果
- 执行回归测试
- 对比测试状态变化
- 识别意外失败

**输出**：
- 测试差异列表（新增失败、新增通过、稳定失败等）
- 回归问题标识
- 分析结果和建议

### 4. 测试生成

**功能描述**：基于变更和覆盖率，生成测试用例建议

**技术实现**：
- 集成AI服务（LLM）
- 分析未覆盖的代码
- 生成测试代码框架
- 基于变更点生成测试

**输出**：
- 生成的测试代码
- 覆盖率改进建议
- 测试优先级建议

### 5. 多格式报告

**功能描述**：生成多种格式的测试和影响分析报告

**技术实现**：
- HTML报告（可视化图表）
- JSON报告（机器可读）
- Markdown报告（文档集成）
- 控制台输出（实时反馈）

**输出**：
- 详细的测试执行报告
- 变更影响可视化
- 覆盖率统计
- 回归问题汇总

---

## 目标用户和使用场景

### 目标用户

1. **后端开发工程师**
   - 需要评估代码变更影响范围
   - 希望快速验证变更是否破坏现有功能
   - 关注回归测试效率

2. **测试工程师**
   - 需要选择回归测试用例
   - 关注测试覆盖率提升
   - 需要生成测试用例

3. **DevOps工程师**
   - 集成到CI/CD流水线
   - 需要自动化测试选择
   - 关注测试报告生成

4. **技术负责人**
   - 关注代码质量和变更影响
   - 需要团队协作工具
   - 需要可视化报告

### 典型使用场景

**场景1：代码提交后的快速验证**
```
开发者提交代码
  ↓
自动分析变更影响范围
  ↓
智能选择需要运行的测试
  ↓
执行测试并生成报告
  ↓
快速发现回归问题
```

**场景2：大规模重构前的风险评估**
```
开发者规划重构
  ↓
分析重构影响范围
  ↓
生成完整的影响图
  ↓
评估风险和制定测试计划
  ↓
重构后全面验证
```

**场景3：持续集成流水线**
```
代码提交到main分支
  ↓
CI触发JCIA分析
  ↓
运行选择性回归测试
  ↓
生成报告并通知团队
  ↓
失败则阻止合并
```

**场景4：测试覆盖率提升**
```
运行测试并收集覆盖率
  ↓
识别未覆盖的代码
  ↓
使用AI生成测试建议
  ↓
开发者补充测试用例
  ↓
提升整体覆盖率
```

---

## 非功能性需求

### 性能要求

1. **分析性能**
   - 单次提交分析 < 10秒
   - 影响图构建 < 5秒
   - 测试选择 < 3秒

2. **测试执行**
   - 支持1000+测试用例
   - 选择性测试比全量测试快50%+

### 可靠性要求

1. **准确性**
   - 变更识别准确率 > 99%
   - 影响分析准确率 > 95%
   - 回归识别准确率 > 90%

2. **稳定性**
   - 支持大规模Git仓库（100万+行代码）
   - 处理并发CI任务
   - 错误恢复和重试机制

### 可扩展性要求

1. **架构扩展**
   - 支持新的Git托管平台（GitLab, Bitbucket等）
   - 支持多种构建工具（Gradle等）
   - 支持自定义测试选择策略

2. **性能扩展**
   - 分布式测试执行
   - 缓存机制优化
   - 并行分析能力

### 可用性要求

1. **易用性**
   - 清晰的命令行界面
   - 详细的错误提示
   - 丰富的文档和示例

2. **可维护性**
   - 模块化设计
   - 完整的单元测试
   - 代码覆盖率 > 80%

3. **可集成性**
   - 支持CI/CD集成
   - 提供REST API（未来）
   - 支持插件扩展（未来）

---

## 13阶段开发计划

### 阶段 1：项目初始化 ✅
**目标**：建立项目基础结构和配置

**交付物**：
- 项目目录结构
- 配置文件（pyproject.toml, Makefile等）
- 开发环境设置（虚拟环境、依赖管理）
- 代码质量工具配置（ruff, pyright, pytest, bandit）
- Pre-commit hooks配置

**状态**：已完成

---

### 阶段 2：代码质量工具配置 ✅
**目标**：配置完整的代码质量保证工具链

**交付物**：
- Ruff配置（linting和formatting）
- Pyright类型检查配置
- Pytest测试框架配置
- Bandit安全扫描配置
- Pre-commit hooks集成
- Makefile自动化命令

**状态**：已完成

---

### 阶段 3：核心接口定义 ✅
**目标**：定义核心领域层的抽象接口

**交付物**：
- 变更分析器接口（ChangeAnalyzer）
- 调用链分析器接口（CallChainAnalyzer）
- 工具包装器接口（ToolWrapper）
- 仓储接口（TestRunRepository, TestResultRepository等）
- 测试运行器接口（TestSelector, TestGenerator, TestExecutor）

**实现位置**：
- `jcia/core/interfaces/analyzer.py`
- `jcia/core/interfaces/call_chain_analyzer.py`
- `jcia/core/interfaces/repository.py`
- `jcia/core/interfaces/test_runner.py`
- `jcia/core/interfaces/tool_wrapper.py`

**状态**：已完成

---

### 阶段 4：领域实体实现 ✅
**目标**：实现核心领域实体和数据模型

**交付物**：

#### 变更集合模块
- `ChangeSet`：变更集合实体
- `FileChange`：文件变更
- `MethodChange`：方法变更
- `CommitInfo`：提交信息
- 枚举：`ChangeType`, `ChangeStatus`

#### 影响图模块
- `ImpactGraph`：影响图
- `ImpactNode`：影响节点
- `ImpactEdge`：影响边
- 枚举：`ImpactType`, `ImpactSeverity`

#### 测试用例模块
- `TestCase`：测试用例
- `TestSuite`：测试套件
- 枚举：`TestPriority`, `TestType`

#### 测试运行模块
- `TestRun`：测试运行
- `TestResult`：测试结果
- `TestDiff`：测试差异
- `TestComparison`：测试对比
- `CoverageData`：覆盖率数据
- 枚举：`TestStatus`, `RunType`, `RunStatus`

**实现位置**：
- `jcia/core/entities/change_set.py`
- `jcia/core/entities/impact_graph.py`
- `jcia/core/entities/test_case.py`
- `jcia/core/entities/test_run.py`

**单元测试**：
- `tests/unit/core/test_change_set.py`
- `tests/unit/core/test_impact_graph.py`
- `tests/unit/core/test_test_case.py`
- `tests/unit/core/test_test_run.py`

**状态**：已完成
**测试状态**：56个测试全部通过，覆盖率达标

---

### 阶段 5：适配器层实现
**目标**：实现与外部系统的适配器

**交付物**：
- PyDriller适配器（Git仓库分析）
- Maven适配器（Maven项目处理）
- AI服务适配器（LLM集成）
- 数据库适配器（SQLite/PostgreSQL）

**实现位置**：
- `jcia/adapters/git/`
- `jcia/adapters/maven/`
- `jcia/adapters/ai/`
- `jcia/adapters/database/`

**状态**：待开始

---

### 阶段 6：基础设施层实现
**目标**：实现基础设施服务

**交付物**：
- 仓储实现（基于数据库）
- 配置管理服务
- 日志服务
- 文件系统服务

**实现位置**：
- `jcia/infrastructure/database/`
- `jcia/infrastructure/config/`
- `jcia/infrastructure/logging/`

**状态**：待开始

---

### 阶段 7：领域服务实现
**目标**：实现核心领域逻辑服务

**交付物**：
- 变更影响分析服务
- 调用链构建服务
- 测试选择服务（STARTS算法）
- 测试生成服务

**实现位置**：
- `jcia/core/services/impact_analyzer.py`
- `jcia/core/services/call_chain_builder.py`
- `jcia/core/services/test_selector.py`
- `jcia/core/services/test_generator.py`

**状态**：待开始

---

### 阶段 8：应用用例实现 ✅
**目标**：实现应用层的业务用例

**交付物**：
- 分析变更影响用例
- 生成测试用例
- 执行回归测试用例
- 生成测试报告用例

**实现位置**：
- `jcia/core/use_cases/analyze_impact.py`
- `jcia/core/use_cases/generate_tests.py`
- `jcia/core/use_cases/run_regression.py`
- `jcia/core/use_cases/generate_report.py`

**单元测试**：
- `tests/unit/use_cases/test_analyze_impact.py`
- `tests/unit/use_cases/test_generate_tests.py`
- `tests/unit/use_cases/test_run_regression.py`

**状态**：已完成
**测试状态**：29个测试全部通过

---

### 阶段 9：CLI命令行工具
**目标**：实现命令行界面

**交付物**：
- analyze命令（分析变更影响）
- test命令（生成和运行测试）
- report命令（生成报告）
- config命令（配置管理）

**实现位置**：
- `jcia/cli/`

**状态**：待开始

---

### 阶段 10：报告生成模块
**目标**：实现多格式报告生成

**交付物**：
- HTML报告生成器
- JSON报告生成器
- Markdown报告生成器
- 控制台输出格式化

**实现位置**：
- `jcia/reports/html.py`
- `jcia/reports/json.py`
- `jcia/reports/markdown.py`
- `jcia/reports/console.py`

**状态**：待开始

---

### 阶段 11：集成测试
**目标**：完整的端到端测试

**交付物**：
- 完整工作流测试
- 与真实Git仓库集成测试
- 与Maven项目集成测试
- 性能测试

**测试位置**：
- `tests/integration/`

**状态**：待开始

---

### 阶段 12：文档完善
**目标**：完整的用户和开发者文档

**交付物**：
- 用户手册（使用指南）
- API文档
- 开发者指南（贡献指南）
- 架构文档

**实现位置**：
- `docs/user_guide.md`
- `docs/api.md`
- `docs/developer_guide.md`
- `docs/architecture.md`

**状态**：待开始

---

### 阶段 13：CI/CD和部署
**目标**：自动化构建和部署流程

**交付物**：
- GitHub Actions CI/CD配置
- Docker镜像构建
- PyPI包发布
- 版本发布流程

**实现位置**：
- `.github/workflows/`
- `Dockerfile`
- `docker-compose.yml`

**状态**：待开始

---

## 当前进度

**已完成阶段**：4 / 13
**当前阶段**：阶段 5 - 适配器层实现
**测试覆盖率**：实体层 100%，接口层 0%（预期）

## 技术栈

- **语言**：Python 3.10+
- **测试框架**：pytest
- **代码质量**：ruff, pyright, bandit
- **依赖管理**：pip, pyproject.toml
- **外部依赖**：pydriller, pyyaml, click, pydantic, rich

## 开发规范

- 严格遵循TDD（测试驱动开发）
- 所有代码提交前必须通过质量检查
- 虚拟环境开发（避免PEP 668问题）
- PowerShell环境测试（Windows）
- 覆盖率要求：80%以上（接口层除外）

## 下一步行动

1. 开始阶段5：适配器层实现
2. 优先实现PyDriller Git适配器（核心功能）
3. 编写适配器单元测试
4. 验证适配器与实体的集成
