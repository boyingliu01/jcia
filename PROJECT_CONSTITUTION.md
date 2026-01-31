# JCIA 项目宪法

> **项目愿景**：开发一个自动化工具，帮助开发团队在代码变更后快速识别影响范围，智能选择需要运行的测试用例，并提供回归分析能力。

> **核心价值**：提升开发效率30-50%，确保代码质量，降低维护成本

---

## 第一部分：开发原则

### 1.1 测试驱动开发 (TDD)

**TDD 是 JCIA 项目的核心开发方法**，必须严格遵循以下循环：

```
Red → Green → Refactor
```

#### TDD 循环规则

1. **编写测试用例（Red）**
   - 在实现任何功能代码之前，先编写失败的测试用例
   - 测试用例必须清晰描述预期行为
   - 测试命名遵循 `test_{method_name}_{scenario}` 格式
   - 运行测试，确认测试失败（Red 阶段）

2. **实现功能代码（Green）**
   - 编写最少量的代码使测试通过
   - 不编写不必要的代码
   - 运行测试，确认所有测试通过（Green 阶段）

3. **重构代码（Refactor）**
   - 在保持测试通过的前提下优化代码
   - 改善代码结构和可读性
   - 确保重构后测试仍然通过
   - 运行类型检查和代码质量工具

#### TDD 违规行为清单

❌ **禁止**：
- 先写功能代码，后写测试
- 为了通过测试而修改测试逻辑
- 跳过 TDD 循环中的任何一个阶段
- 编写过大的测试（一个测试只验证一个行为）
- 使用 `pytest.skip` 跳过失败的测试而不是修复

✅ **强制**：
- 新功能必须先有测试
- 每次提交必须通过所有测试
- 重构前必须确保有足够的测试覆盖
- 使用 fixtures 减少测试代码重复

### 1.2 代码质量标准

#### 代码覆盖率要求

- **整体覆盖率**：≥ 80%
- **实体层覆盖率**：≥ 95%
- **服务层覆盖率**：≥ 85%
- **适配器层覆盖率**：≥ 75%
- **接口层覆盖率**：不要求（仅包含抽象方法）

#### 代码质量门禁

所有代码在提交前必须通过以下检查：

```powershell
make check  # 包含：lint + type check + security
make test   # 包含：测试 + 覆盖率检查
```

**提交检查流程**：
1. `ruff check` - Lint 检查
2. `ruff format` - 代码格式检查
3. `pyright` - 静态类型检查（strict 模式）
4. `bandit` - 安全漏洞扫描
5. `pytest` - 单元测试执行
6. `pytest --cov` - 覆盖率检查（≥ 80%）

### 1.3 类型安全

#### 类型注解要求

- 所有公共函数必须包含类型注解
- 使用 Python 3.10+ 语法：`str | None` 而不是 `Optional[str]`
- 使用 `TYPE_CHECKING` 避免循环导入

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jcia.core.entities.test_run import TestRun

def analyze_commits(
    from_commit: str,
    to_commit: str | None = None
) -> ChangeSet:
    ...
```

#### 类型安全违规

❌ **禁止**：
- 使用 `any` 类型（必须有明确类型）
- 使用 `# type: ignore` 压制类型错误
- 使用 `@ts-expect-error` 或 `@ts-ignore`

✅ **强制**：
- 运行 `pyright` 严格模式类型检查
- 修复所有类型错误后再提交
- 使用 `dataclass` 自动生成类型注解

---

## 第二部分：架构约束

### 2.1 清洁架构原则

JCIA 严格遵循清洁架构，依赖方向必须始终指向核心：

```
Adapters → Infrastructure → Use Cases → Services → Entities
```

#### 依赖规则

1. **Entities（核心层）**
   - ❌ 不依赖任何外部模块
   - ✅ 只包含纯业务逻辑和数据模型
   - ✅ 使用 `@dataclass` 定义实体

2. **Services（领域服务）**
   - ❌ 不依赖 Adapters 或 Infrastructure
   - ✅ 只依赖 Entities
   - ✅ 协调多个实体的业务逻辑

3. **Use Cases（应用用例）**
   - ❌ 不直接依赖 Adapters
   - ✅ 通过接口（Interfaces）依赖 Infrastructure
   - ✅ 编排业务流程和事务边界

4. **Infrastructure（基础设施）**
   - ❌ 不依赖 Adapters
   - ✅ 实现核心层定义的接口
   - ✅ 处理数据持久化、配置、日志

5. **Adapters（适配器层）**
   - ✅ 依赖所有内部层
   - ✌ 桥接外部系统（Git, Maven, AI, Database）
   - ✌ 转换外部数据为领域实体

#### 跨层违规检查

使用以下命令验证依赖方向：

```powershell
# 检查是否有跨层违规导入
ruff check --select I jcia
```

### 2.2 依赖倒置原则 (DIP)

#### 接口定义规则

- 所有接口定义在 `jcia/core/interfaces/` 目录
- 使用 `ABC` 和 `@abstractmethod` 定义抽象接口
- 实现在 `jcia/infrastructure/` 或 `jcia/adapters/` 目录

```python
# 正确：接口在核心层
# jcia/core/interfaces/analyzer.py
class ChangeAnalyzer(ABC):
    @abstractmethod
    def analyze_commits(self, from_commit: str) -> ChangeSet:
        pass

# 正确：实现在基础设施层
# jcia/infrastructure/git/pydriller_adapter.py
class PyDrillerAdapter(ChangeAnalyzer):
    def analyze_commits(self, from_commit: str) -> ChangeSet:
        ...
```

---

## 第三部分：测试规范

### 3.1 测试结构

#### 目录结构

```
tests/
├── unit/
│   ├── core/
│   │   ├── test_change_set.py
│   │   ├── test_impact_graph.py
│   │   └── test_test_run.py
│   ├── adapters/
│   │   ├── test_git_adapter.py
│   │   └── test_maven_adapter.py
│   └── infrastructure/
│       └── test_database_repository.py
└── integration/
    ├── test_full_workflow.py
    └── test_git_integration.py
```

### 3.2 测试命名规范

#### 测试类命名

- 格式：`Test{ClassName}`
- 示例：`TestChangeSet`, `TestImpactGraph`, `TestPyDrillerAdapter`

#### 测试方法命名

- 格式：`test_{method_name}_{scenario}`
- 示例：
  - `test_add_file_change_success`
  - `test_analyze_commits_with_invalid_hash_raises_error`
  - `test_is_java_file_returns_true_for_java_extension`

#### 测试标记

```python
@pytest.mark.unit
def test_unit_behavior() -> None:
    ...

@pytest.mark.integration
@pytest.mark.slow
def test_integration_test() -> None:
    ...
```

### 3.3 测试模式

#### AAA 模式（Arrange-Act-Assert）

每个测试方法应遵循 AAA 模式：

```python
def test_add_file_change_increases_count(self) -> None:
    # Arrange (准备)
    change_set = ChangeSet()
    file_change = FileChange(file_path="Service.java")

    # Act (执行)
    change_set.add_file_change(file_change)

    # Assert (断言)
    assert len(change_set.file_changes) == 1
```

#### Fixture 使用

使用 fixtures 减少重复代码：

```python
@pytest.fixture
def sample_file_change() -> FileChange:
    return FileChange(file_path="Service.java")

@pytest.fixture
def sample_change_set() -> ChangeSet:
    return ChangeSet()

def test_add_file_change_with_fixture(
    sample_change_set: ChangeSet,
    sample_file_change: FileChange
) -> None:
    sample_change_set.add_file_change(sample_file_change)
    assert len(sample_change_set.file_changes) == 1
```

---

## 第四部分：CI/CD 流程

### 4.1 持续集成 (CI)

#### 提交前检查

所有开发者必须配置 pre-commit hooks：

```powershell
make install-dev  # 包含 pre-commit hooks 安装
```

**Pre-commit hooks 自动执行**：
1. `ruff --fix` - 自动修复 lint 问题
2. `ruff format` - 自动格式化代码
3. `pyright` - 类型检查
4. `bandit` - 安全扫描
5. `pytest tests/unit -v` - 运行单元测试

如果任何一个检查失败，提交将被阻止。

#### CI 流水线

GitHub Actions 自动在每次 push 时执行：

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"

      - name: Run linter
        run: make lint

      - name: Run type check
        run: pyright jcia tests

      - name: Run security scan
        run: make security

      - name: Run tests
        run: make test

      - name: Upload coverage report
        uses: codecov/codecov-action@v3
```

### 4.2 持续部署 (CD)

#### 版本发布流程

1. **提交所有更改**
   ```powershell
   git add .
   git commit -m "feat: implement new feature"
   ```

2. **更新版本号** (手动或自动)
   - 编辑 `pyproject.toml` 中的 `version`
   - 遵循语义化版本 (SemVer)：`MAJOR.MINOR.PATCH`

3. **创建 Git tag**
   ```powershell
   git tag v0.1.0
   git push origin main --tags
   ```

4. **自动触发发布**
   - GitHub Actions 检测到 tag
   - 构建分发包
   - 发布到 PyPI
   - 生成发布说明

#### 发布检查清单

在发布新版本前，确认：

- [ ] 所有测试通过
- [ ] 代码覆盖率 ≥ 80%
- [ ] 无 lint 错误
- [ ] 无类型错误
- [ ] 无安全漏洞
- [ ] 文档已更新（README, CHANGELOG.md）
- [ ] 版本号已更新
- [ ] CHANGELOG.md 包含本次变更说明

---

## 第五部分：代码风格

### 5.1 命名约定

| 类型 | 格式 | 示例 |
|------|------|------|
| 类名 | `PascalCase` | `ChangeAnalyzer`, `ImpactGraph` |
| 函数/方法 | `snake_case` | `analyze_commits`, `get_upstream_impact` |
| 常量 | `UPPER_SNAKE_CASE` | `MAX_DEPTH`, `DEFAULT_TIMEOUT` |
| 私有成员 | `_leading_underscore` | `_internal_method`, `_cache` |
| 枚举 | `PascalCase` | `ChangeType`, `ImpactSeverity` |
| 枚举值 | lowercase | `ChangeType.ADD = "add"` |

### 5.2 导入顺序

```python
# 1. 标准库
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

# 2. 第三方库
from pydantic import BaseModel
from rich.console import Console

# 3. 本地导入
from jcia.core.entities.change_set import ChangeSet
from jcia.core.interfaces.analyzer import ChangeAnalyzer
```

### 5.3 文档字符串

使用 Google 风格的 docstring：

```python
def analyze_commits(
    self,
    from_commit: str,
    to_commit: str | None = None
) -> ChangeSet:
    """分析指定提交范围的变更.

    Args:
        from_commit: 起始提交哈希
        to_commit: 结束提交哈希（默认为HEAD）

    Returns:
        ChangeSet: 变更集合，包含所有变更的文件和方法

    Raises:
        AnalysisError: 分析过程中发生错误
        GitError: Git操作失败

    Example:
        ```python
        analyzer = PyDrillerAdapter(repo_path)
        changes = analyzer.analyze_commits("abc123", "def456")
        ```
    """
```

---

## 第六部分：错误处理

### 6.1 异常定义

所有自定义异常继承自 `Exception`：

```python
class JCIAError(Exception):
    """JCIA 基础异常类."""
    pass

class AnalysisError(JCIAError):
    """分析过程错误."""
    pass

class GitError(JCIAError):
    """Git 操作错误."""
    pass

class TestExecutionError(JCIAError):
    """测试执行错误."""
    pass
```

### 6.2 错误处理原则

❌ **禁止**：
- 使用空 `except:` 块
- 使用 `except Exception:` 吞噬所有异常
- 在非入口点使用 `sys.exit()`

✅ **强制**：
- 捕获特定异常类型
- 记录错误日志
- 在适当层次向上抛出异常
- 使用 `logging` 模块记录错误

```python
import logging

logger = logging.getLogger(__name__)

try:
    result = self.analyzer.analyze_commits(from_commit)
except GitError as e:
    logger.error(f"Git operation failed: {e}")
    raise AnalysisError(f"Failed to analyze commits: {e}") from e
```

---

## 第七部分：安全要求

### 7.1 敏感信息

❌ **禁止**：
- 在代码中硬编码密码、API密钥、令牌
- 在日志中记录敏感信息
- 在 git 仓库中提交 `.env` 文件

✅ **强制**：
- 使用环境变量存储敏感信息
- 使用 `.env.example` 作为模板
- 确保 `.env` 在 `.gitignore` 中

### 7.2 依赖安全

- 定期运行 `pip-audit` 检查依赖漏洞
- 及时更新依赖到安全版本
- 使用 `bandit` 扫描安全漏洞

```powershell
pip install pip-audit
pip-audit
bandit -r jcia -c pyproject.toml
```

---

## 第八部分：性能要求

### 8.1 性能目标

- **单次提交分析**：< 10 秒
- **影响图构建**：< 5 秒
- **测试选择**：< 3 秒
- **支持测试用例数**：1000+
- **选择性测试加速**：≥ 50%

### 8.2 性能测试

对关键路径进行性能测试：

```python
import time

def test_analyze_commits_performance():
    start_time = time.time()
    # 执行操作
    result = analyzer.analyze_commits("abc123")
    elapsed_time = time.time() - start_time

    assert elapsed_time < 10, f"Analysis took {elapsed_time:.2f}s, expected < 10s"
```

---

## 第九部分：文档要求

### 9.1 必需文档

- [ ] `README.md` - 项目介绍和快速开始
- [ ] `CHANGELOG.md` - 版本变更记录
- [ ] `AGENTS.md` - Agent 开发指南
- [ ] `PROJECT_CONSTITUTION.md` - 项目宪法（本文件）
- [ ] `.jcia.yaml.example` - 配置文件模板

### 9.2 API 文档

- 所有公共类必须有 docstring
- 所有公共方法必须有 docstring
- 参数类型和返回类型必须清晰说明
- 提供使用示例

---

## 第十部分：项目管理

### 10.1 Git 工作流

#### 分支策略

- `main` - 主分支（生产代码）
- `develop` - 开发分支
- `feature/*` - 功能分支
- `bugfix/*` - 修复分支
- `hotfix/*` - 紧急修复分支

#### 提交消息格式

使用 Conventional Commits 格式：

```
<type>(<scope>): <subject>

<body>

<footer>
```

**类型 (type)**：
- `feat` - 新功能
- `fix` - Bug 修复
- `docs` - 文档更新
- `style` - 代码格式（不影响功能）
- `refactor` - 重构
- `test` - 测试相关
- `chore` - 构建/工具相关

**示例**：
```
feat(adapters): implement PyDriller git adapter

Add PyDriller adapter to parse Git repository and extract
commit differences including file-level and method-level changes.

Closes #123
```

### 10.2 Code Review

#### PR 检查清单

在合并 PR 前，确认：

- [ ] CI 流水线通过
- [ ] 代码覆盖率没有下降
- [ ] 至少 1 人 Code Review 通过
- [ ] 所有评论已解决或讨论
- [ ] 提交历史干净（无 squash merge 混乱）
- [ ] 文档已更新（如有必要）
- [ ] 没有调试代码（print, 断点等）

---

## 第十一部分：开发环境

### 11.1 必需工具

- Python 3.10+
- 虚拟环境（.venv）
- Git
- PowerShell (Windows)

### 11.2 环境配置

```powershell
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境 (PowerShell)
.venv\Scripts\Activate.ps1

# 安装开发依赖
pip install -e ".[dev]"

# 配置 pre-commit hooks
pre-commit install

# 验证环境
make check
make test
```

### 11.3 IDE 配置

**推荐 IDE**：VS Code, PyCharm

**必需插件**：
- Python 扩展
- Pylance / Pyright
- Ruff
- pytest

---

## 附录：常用命令

```powershell
# 开发环境
make install-dev      # 安装所有依赖
make setup-hooks      # 配置 pre-commit hooks

# 代码质量
make lint             # 运行 linter
make format           # 格式化代码
make check            # 完整检查（lint + type + security）
make security         # 安全扫描

# 测试
make test             # 运行所有测试
make test-unit        # 运行单元测试
make test-integration # 运行集成测试

# 单独运行测试
pytest tests/unit/core/test_change_set.py -v
pytest tests/unit/core/test_change_set.py::TestChangeSet::test_changed_files -v

# 类型检查
pyright jcia tests

# 覆盖率报告
pytest tests/unit --cov=jcia --cov-report=html --cov-report=term-missing

# 清理
make clean            # 清理构建产物
```

---

## 宪法修订历史

| 版本 | 日期 | 修订内容 | 作者 |
|------|------|----------|------|
| 1.0.0 | 2026-01-31 | 初始版本，定义核心原则和流程 | Sisyphus |

---

**本宪法的所有规则必须严格遵守。项目成功依赖于每个人都遵循这些原则。**
