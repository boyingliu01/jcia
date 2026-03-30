# JCIA - Java Code Impact Analyzer

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)]
[![License](https://img.shields.io/badge/license-MIT-green.svg)]
[![Code Coverage](https://img.shields.io/badge/coverage-89%25-brightgreen.svg)]

**JCIA** 是一个 Python 工具，用于分析 Java 代码变更的影响范围，智能选择需要运行的测试用例，并提供回归分析能力。

## 特性

- 🔍 **变更代码影响分析** - 自动分析 Git 提交，识别变更的文件和方法
- 📊 **影响图构建** - 构建调用链图，计算受影响的类和方法
- 🎯 **智能测试选择** - 基于 STARTS 算法和影响范围选择测试用例
- 🤖 **AI 测试生成** - 集成 LLM 服务，自动生成测试用例建议
- 📈 **多格式报告** - 支持 HTML、JSON、Markdown 格式报告
- 🔄 **回归分析** - 对比基线测试和回归测试结果，识别回归问题

## 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/your-org/jcia.git
cd jcia

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows PowerShell

# 安装依赖
pip install -e ".[dev]"
```

### 配置

创建配置文件 `jcia.yaml`（可选）：

```yaml
repository:
  path: /path/to/your/java/project

analyzer:
  max_depth: 10
  include_test_files: false

report:
  format: html
  output_dir: ./reports

ai:
  provider: volcengine
  model: gpt-4
```

### 使用

```bash
# 分析变更影响
jcia analyze --repo-path /path/to/repo --from-commit abc123 --to-commit def456

# 生成测试用例
jcia test --repo-path /path/to/project --target-class com.example.Service

# 执行回归测试
jcia regression --repo-path /path/to/project --baseline-commit abc123 --regression-commit def456

# 生成报告
jcia report --format html --output ./report.html

# 配置管理
jcia config --show
jcia config --set analyzer.max_depth=15
```

## 核心概念

### 变更分析

JCIA 使用 PyDriller 解析 Git 仓库，识别：

- 文件级变更（新增、修改、删除、重命名）
- 方法级变更（方法签名变更）
- 提交信息（作者、时间、消息）

### 影响图

影响图展示代码变更的传播路径：

- **直接影响** - 直接调用变更方法的代码
- **间接影响** - 通过调用链间接影响的代码
- **严重程度** - HIGH/MEDIUM/LOW
- **影响深度** - 变更传播的最大深度

### 测试选择

JCIA 支持多种测试选择策略：

- **ALL** - 运行所有测试
- **STARTS** - 使用 STARTS 算法选择
- **IMPACT_BASED** - 基于影响范围选择
- **HYBRID** - 混合策略

## 架构

JCIA 采用**清洁架构**（Clean Architecture）：

```
Adapters Layer (Git, Maven, AI, Database)
    ↓
Infrastructure Layer (Repositories, Config, Logging)
    ↓
Use Cases Layer (Business Orchestration)
    ↓
Services Layer (Domain Logic)
    ↓
Entities Layer (Domain Models)
```

### 依赖规则

- 外部依赖（Git、Maven、AI）在适配器层
- 业务逻辑在核心层
- 核心层不依赖适配器层
- 通过接口（ABC）解耦

## 开发

### 设置开发环境

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 配置 pre-commit hooks
make setup-hooks
```

### 运行测试

```bash
# 运行所有测试
make test

# 运行单元测试
pytest tests/unit -v

# 运行集成测试
pytest tests/integration -v

# 运行带覆盖率的测试
pytest tests/unit --cov=jcia --cov-report=html
```

### 代码质量

```bash
# Lint 检查
make lint

# 格式化代码
make format

# 类型检查
pyright jcia tests

# 安全扫描
make security

# 完整检查
make check
```

## 配置选项

### CLI 选项

| 命令 | 选项 | 说明 |
|-------|------|------|
| `analyze` | `--repo-path` | Git 仓库路径 |
| | `--from-commit` | 起始提交哈希 |
| | `--to-commit` | 结束提交哈希 |
| | `--commit-range` | 提交范围（如 abc123..def456）|
| | `--max-depth` | 最大追溯深度 |
| `test` | `--repo-path` | 项目路径 |
| | `--target-class` | 目标类（可多次使用）|
| | `--coverage-file` | 覆盖率报告文件 |
| | `--min-confidence` | 最低置信度阈值 |
| `regression` | `--repo-path` | 项目路径 |
| | `--baseline-commit` | 基线提交 |
| | `--regression-commit` | 回归提交 |
| | `--execute-coverage` | 执行并收集覆盖率 |
| | `--save-results` | 保存测试结果 |

### 环境变量

| 变量 | 说明 |
|-------|------|
| `VOLCENGINE_ACCESS_KEY` | Volcengine 访问密钥 |
| `VOLCENGINE_SECRET_KEY` | Volcengine 密钥 |
| `VOLCENGINE_APP_ID` | Volcengine 应用 ID |

## 性能

- 单次提交分析：< 10 秒
- 影响图构建：< 5 秒
- 测试选择：< 3 秒
- 支持 1000+ 测试用例
- 选择性测试加速：≥ 50%

## 许可证

[MIT License](LICENSE)

## 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详细信息。

## 支持

- 📧 Email: jcia-dev@example.org
- 🐛 Issues: [GitHub Issues](https://github.com/your-org/jcia/issues)
- 📖 Docs: [项目文档](https://github.com/your-org/jcia#readme)

## 更新日志

查看 [CHANGELOG.md](CHANGELOG.md) 了解版本历史。

## 致谢

感谢所有贡献者和开源项目的支持：

- [PyDriller](https://github.com/ishepard/pydriller) - Git 仓库分析
- [Click](https://click.palletsprojects.com/) - 命令行界面
- [Pytest](https://docs.pytest.org/) - 测试框架
