# 贡献指南

感谢您对 JCIA (Java Code Impact Analyzer) 的关注！我们欢迎所有形式的贡献。

## 如何贡献

### 报告 Bug

如果您发现了 bug，请：

1. 在 [GitHub Issues](https://github.com/your-org/jcia/issues) 搜索现有 issue
2. 如果没有找到，创建新的 issue
3. 在 issue 中提供：
   - 清晰的标题和描述
   - 重现步骤
   - 期望行为
   - 实际行为
   - 环境信息（Python 版本、操作系统）
   - 相关日志或错误信息

### 提出新功能

1. 在 [GitHub Issues](https://github.com/your-org/jcia/issues) 创建 feature request
2. 描述新功能的用途和价值
3. 讨论实现方案
4. 等待社区反馈

### 提交代码

#### 1. Fork 仓库

```bash
# Fork 仓库到您的 GitHub 账户
git clone https://github.com/your-username/jcia.git
cd jcia
```

#### 2. 创建分支

```bash
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/your-bug-fix
```

#### 3. 设置开发环境

```bash
# 创建虚拟环境
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows PowerShell

# 安装开发依赖
pip install -e ".[dev]"

# 配置 pre-commit hooks
pre-commit install
```

#### 4. 遵循开发规范

**TDD 流程**：
1. 编写失败的测试
2. 编写代码使测试通过
3. 重构代码
4. 确保所有测试通过

**代码风格**：
- 遵循 PEP 8 规范
- 使用 4 空格缩进
- 最大行长度 100 字符
- 使用 Python 3.10+ 类型语法（`str | None`）

**提交信息格式**：
```
<type>(<scope>): <subject>

<body>

<footer>
```

类型（type）：
- `feat` - 新功能
- `fix` - Bug 修复
- `docs` - 文档更新
- `style` - 代码格式
- `refactor` - 重构
- `test` - 测试相关
- `chore` - 构建/工具相关

示例：
```
feat(adapters): implement Gradle build adapter

Add Gradle adapter to parse Gradle projects and extract
build dependencies.

Closes #123
```

#### 5. 运行测试和质量检查

```bash
# 运行测试
make test

# 运行代码质量检查
make check

# 查看覆盖率
pytest tests/unit --cov=jcia --cov-report=html
```

**质量标准**：
- 所有测试必须通过
- 代码覆盖率 ≥ 80%
- 无 lint 错误
- 无类型错误
- 无安全漏洞

#### 6. 提交更改

```bash
git add .
git commit -m "feat: add your feature"
```

#### 7. 推送并创建 Pull Request

```bash
git push origin feature/your-feature-name
```

然后在 GitHub 上创建 Pull Request。

## Pull Request 检查清单

在提交 PR 之前，确保：

- [ ] 代码遵循项目规范
- [ ] 所有测试通过（`make test`）
- [ ] 代码覆盖率达标（≥ 80%）
- [ ] 无 lint 错误（`make lint`）
- [ ] 无类型错误（`pyright jcia tests`）
- [ ] 无安全漏洞（`make security`）
- [ ] 添加了必要的测试
- [ ] 更新了文档（如需要）
- [ ] 提交信息清晰描述了更改
- [ ] PR 描述说明了更改的目的

## 代码审查流程

1. 自动 CI 检查必须通过
2. 至少一名维护者审查代码
3. 解决所有审查评论
4. 更新 PR 以反映更改
5. 维护者批准后合并

## 开发环境

### 目录结构

```
jcia/
├── cli/                    # 命令行界面
├── core/                   # 核心业务逻辑
│   ├── entities/           # 领域实体
│   ├── interfaces/         # 抽象接口
│   ├── services/          # 领域服务
│   └── use_cases/        # 应用用例
├── adapters/               # 外部系统适配器
│   ├── ai/               # AI 服务
│   ├── database/         # 数据库
│   ├── git/              # Git 仓库
│   └── maven/            # Maven 项目
├── infrastructure/         # 基础设施
│   ├── config/           # 配置管理
│   ├── database/         # 数据库实现
│   ├── fs/              # 文件系统
│   └── logging/         # 日志
├── reports/               # 报告生成
└── tests/                 # 测试
    ├── unit/             # 单元测试
    └── integration/      # 集成测试
```

### 依赖管理

主要依赖在 `pyproject.toml` 中管理。

添加新依赖：
```bash
pip install new-package
pip freeze > requirements.txt
```

然后更新 `pyproject.toml` 中的依赖列表。

## 测试指南

### 单元测试

```python
import pytest

def test_example() -> None:
    """测试示例."""
    # Arrange
    input_value = 5

    # Act
    result = some_function(input_value)

    # Assert
    assert result == 10
```

### 集成测试

```python
def test_integration_with_real_system() -> None:
    """集成测试示例."""
    # 测试与真实系统的集成
    pass
```

### 使用 Fixtures

```python
@pytest.fixture
def sample_data() -> dict:
    """创建测试数据."""
    return {"key": "value"}

def test_with_fixture(sample_data: dict) -> None:
    """使用 fixture 的测试."""
    assert sample_data["key"] == "value"
```

## 文档指南

### 代码文档

使用 Google 风格的 docstring：

```python
def calculate_impact_score(
    changes: int,
    depth: int,
    weight: float = 1.0
) -> float:
    """计算影响评分.

    Args:
        changes: 变更数量
        depth: 影响深度
        weight: 权重因子

    Returns:
        float: 影响评分

    Raises:
        ValueError: 如果参数无效

    Example:
        >>> calculate_impact_score(5, 3)
        15.0
    """
    return changes * depth * weight
```

### 用户文档

更新以下文档（如需要）：
- `README.md` - 项目概述
- `CHANGELOG.md` - 版本变更记录
- `docs/` - 详细文档

## 发布流程

1. 更新版本号（`pyproject.toml`）
2. 更新 `CHANGELOG.md`
3. 创建 Git tag
4. 推送到 GitHub
5. GitHub Actions 自动发布到 PyPI

## 获取帮助

- 📧 邮件：support@example.com
- 💬 讨论：[GitHub Discussions](https://github.com/your-org/jcia/discussions)
- 🐛 问题：[GitHub Issues](https://github.com/your-org/jcia/issues)

## 行为准则

- 尊重所有贡献者
- 建设性反馈
- 保持专业和礼貌
- 专注于代码和想法，而非个人
- 遵循项目规范

## 许可证

通过贡献代码，您同意您的贡献将在 [MIT License](LICENSE) 下发布。
