# 开发环境迁移说明 (WSL → PowerShell)

## 概述

本文档记录了JCIA项目从WSL/Linux环境迁移到Windows PowerShell环境的所有配置变更。

## 修改的文件

### 1. AGENTS.md

**变更内容**：
- 第25-26行：将"Testing should run in WSL/Linux environment, not directly in Windows PowerShell"改为"Testing should run in PowerShell (Windows) environment"
- 第26行：将"All scripts assume activation of virtual environment (`source .venv/bin/activate`)"改为"All scripts assume activation of virtual environment (`.venv\Scripts\activate`)"
- 第171-181行：将"Testing (WSL/Linux)"改为"Testing (PowerShell)"
- 第172-180行：将所有`.venv/bin/python`命令改为`python`命令（激活虚拟环境后）
- 第487行：删除了"Run pytest directly in PowerShell on Windows (use WSL or virtual environment)"这一行
- 第499行：将"Run tests in WSL environment with virtual environment activated"改为"Run tests in PowerShell with virtual environment activated"

### 2. PROJECT_CONSTITUTION.md

**变更内容**：
- 第641行：将"WSL/Linux 环境（用于测试）"改为"PowerShell (Windows)"
- 第649-650行：将"激活虚拟环境（WSL/Linux）"和`source .venv/bin/activate`改为"激活虚拟环境 (PowerShell)"和`.venv\Scripts\Activate.ps1`
- 第647-660行：更新了环境配置命令，使用PowerShell语法

### 3. scripts/

**删除的文件**：
- `scripts/run_pytest_wsl.sh` - WSL专用测试脚本
- `scripts/run_pytest.sh` - 旧的Linux测试脚本
- `scripts/dev_workflow.sh` - 旧的Linux开发工作流脚本

**新增的文件**：
- `scripts/run_pytest.ps1` - PowerShell测试脚本
- `scripts/dev_workflow.ps1` - PowerShell开发工作流脚本

#### scripts/run_pytest.ps1
- 使用PowerShell语法
- 路径格式：`e:\Study\LLM\Java代码变更影响分析` (Windows格式)
- 命令格式：`python -m pytest tests/unit -v --tb=short`
- 输出文件：`test_output\pytest_results.txt`

#### scripts/dev_workflow.ps1
- 使用PowerShell语法
- 虚拟环境激活：`& .venv\Scripts\Activate.ps1`
- 包含格式化、lint、类型检查、测试等完整工作流

### 4. Makefile

**变更内容**：
- 添加了Windows/Unix平台检测：
  ```makefile
  ifeq ($(OS),Windows_NT)
      VENV_PYTHON := $(VENV_DIR)\Scripts\python.exe
      VENV_PIP := $(VENV_DIR)\Scripts\pip.exe
  else
      VENV_PYTHON := $(VENV_DIR)/bin/python
      VENV_PIP := $(VENV_DIR)/bin/pip
  endif
  ```
- 所有命令改为直接使用`python`而不是`$(VENV_PYTHON)`（激活虚拟环境后）
- `clean`目标添加了Windows PowerShell命令支持

### 5. .pre-commit-config.yaml

**无需修改**：已使用`python -m pytest`格式，在PowerShell中兼容

## 环境配置步骤

### Windows PowerShell 环境初始化

```powershell
# 1. 进入项目目录
cd e:\Study\LLM\Java代码变更影响分析

# 2. 创建虚拟环境
python -m venv .venv

# 3. 激活虚拟环境
.venv\Scripts\Activate.ps1

# 4. 安装开发依赖
pip install -e ".[dev]"

# 5. 配置 pre-commit hooks
pre-commit install

# 6. 验证环境
make check
make test
```

### 常用命令

#### 运行测试

```powershell
# 运行所有单元测试
python -m pytest tests/unit -v

# 运行特定测试文件
python -m pytest tests/unit/core/test_change_set.py -v

# 运行带覆盖率的测试
python -m pytest tests/unit -v --cov=jcia

# 使用脚本运行测试
.\scripts\run_pytest.ps1
```

#### 代码质量检查

```powershell
# 格式化代码
python -m ruff format jcia tests

# Lint检查
python -m ruff check jcia tests

# 类型检查
python -m pyright jcia tests

# 安全扫描
python -m bandit -r jcia -c pyproject.toml

# 使用Makefile（需要安装Gnu Make for Windows）
make check
```

#### 开发工作流

```powershell
# 使用PowerShell脚本
.\scripts\dev_workflow.ps1
```

## 重要注意事项

### 1. 虚拟环境路径

- **WSL/Linux**: `.venv/bin/python`, `.venv/bin/pip`
- **Windows PowerShell**: `.venv\Scripts\python.exe`, `.venv\Scripts\pip.exe`

### 2. 路径分隔符

- **WSL/Linux**: `/` (正斜杠)
- **Windows PowerShell**: `\` (反斜杠)，但Python通常接受`/`

### 3. 激活虚拟环境

- **WSL/Linux**: `source .venv/bin/activate`
- **Windows PowerShell**: `.venv\Scripts\Activate.ps1`

### 4. Makefile兼容性

- Makefile已更新，支持Windows和Unix平台
- 如果要在Windows上使用`make`命令，需要安装[Gnu Make for Windows](https://gnuwin32.sourceforge.net/packages/make.htm)
- 或者直接使用PowerShell脚本作为替代

### 5. 执行策略

如果遇到PowerShell执行策略限制，运行：
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## 迁移清单

- [x] 更新 AGENTS.md 中的环境说明
- [x] 更新 PROJECT_CONSTITUTION.md 中的环境配置
- [x] 删除旧的WSL脚本文件
- [x] 创建PowerShell版本脚本
- [x] 更新Makefile以支持Windows
- [x] 验证pre-commit配置兼容性
- [ ] 测试所有PowerShell脚本
- [ ] 更新CI/CD配置（如需要）

## 回滚计划

如果需要回滚到WSL环境：

1. 恢复 AGENTS.md 和 PROJECT_CONSTITUTION.md 的WSL配置
2. 删除PowerShell脚本，恢复Bash脚本
3. 恢复Makefile到Unix-only版本
4. 重新配置环境以使用WSL

## 相关文档

- [AGENTS.md](AGENTS.md) - Agent开发指南
- [PROJECT_CONSTITUTION.md](PROJECT_CONSTITUTION.md) - 项目宪法
- [README.md](README.md) - 项目说明

---

**文档版本**: 1.0.0
**最后更新**: 2026-01-31
**维护者**: JCIA Team
