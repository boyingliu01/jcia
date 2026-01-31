# WSL → PowerShell 迁移检查清单

## ✅ 已完成的配置变更

### 1. 文档文件

- [x] **AGENTS.md**
  - ✅ 第25-26行：更新开发环境说明
  - ✅ 第171-181行：更新测试环境为PowerShell
  - ✅ 第487行：删除WSL相关说明
  - ✅ 第499行：更新测试运行环境说明

- [x] **PROJECT_CONSTITUTION.md**
  - ✅ 第641行：测试环境改为PowerShell
  - ✅ 第649-650行：更新虚拟环境激活命令

- [x] **plan.md**
  - ✅ 第688行：开发规范更新为PowerShell环境

- [x] **plan.json**
  - ✅ 第592行：`testingEnvironment`更新为"PowerShell (Windows)"

### 2. 脚本文件

- [x] **删除的脚本**
  - ✅ scripts/run_pytest_wsl.sh
  - ✅ scripts/run_pytest.sh
  - ✅ scripts/dev_workflow.sh

- [x] **新增的PowerShell脚本**
  - ✅ scripts/run_pytest.ps1
  - ✅ scripts/dev_workflow.ps1

### 3. 配置文件

- [x] **Makefile**
  - ✅ 添加Windows/Unix平台检测
  - ✅ 更新虚拟环境路径（Windows使用`\Scripts\`，Unix使用`/bin/`）
  - ✅ 更新clean命令支持PowerShell

- [x] **.pre-commit-config.yaml**
  - ✅ 已兼容PowerShell（无需修改）

- [x] **.vscode/settings.json**（新增）
  - ✅ 设置默认终端为PowerShell
  - ✅ 配置终端profiles
  - ✅ 配置文件排除规则

- [x] **.vscode/launch.json**（新增）
  - ✅ Python调试配置
  - ✅ 测试运行配置

- [x] **.vscode/tasks.json**（新增）
  - ✅ Python路径配置

### 4. 文档新增

- [x] **ENV_MIGRATION_WSL_TO_POWERSHELL.md**
  - ✅ 详细的迁移说明
  - ✅ 环境配置步骤
  - ✅ 常用命令示例

- [x] **IDE_SETUP_POWERSHELL.md**
  - ✅ VS Code终端配置指南
  - ✅ 常见问题解决方案
  - ✅ 验证步骤

### 5. 清理工作

- [x] **test_output/pytest_results.txt**
  - ✅ 删除旧的WSL测试结果

## 🔄 需要用户执行的步骤

### 1. 重启VS Code
```powershell
# 关闭VS Code，然后重新打开
code "E:\Study\LLM\Java代码变更影响分析"
```

### 2. 检查默认终端
1. 按 `Ctrl+`` 打开新终端
2. 查看终端标题，应该显示"PowerShell"
3. 如果仍然显示"WSL"，参考IDE_SETUP_POWERSHELL.md

### 3. 检查执行策略
如果激活虚拟环境时报错，运行：
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 4. 验证配置
```powershell
# 进入项目目录
cd E:\Study\LLM\Java代码变更影响分析

# 检查.vscode目录是否存在
Get-ChildItem -Directory | Where-Object {$_.Name -eq ".vscode"}

# 检查PowerShell是否为默认终端
# （在VS Code终端中查看标题栏）
```

### 5. 激活虚拟环境
```powershell
.venv\Scripts\Activate.ps1
```

### 6. 运行测试验证
```powershell
python -m pytest tests/unit -v
```

## 📋 配置文件对照表

| 配置项 | WSL/Linux | PowerShell | 状态 |
|--------|-----------|------------|------|
| 虚拟环境激活 | `source .venv/bin/activate` | `.venv\Scripts\Activate.ps1` | ✅ 已更新 |
| Python路径 | `.venv/bin/python` | `.venv\Scripts\python.exe` | ✅ 已更新 |
| 项目路径 | `/mnt/e/Study/...` | `e:\Study\...` | ✅ 已更新 |
| 测试脚本 | `.sh` | `.ps1` | ✅ 已替换 |
| VS Code终端 | WSL | PowerShell | ✅ 已配置 |
| Makefile | Unix-only | Windows+Unix | ✅ 已更新 |

## 🔍 验证清单

### 环境验证
- [ ] VS Code默认终端显示为"PowerShell"
- [ ] 可以运行`python --version`
- [ ] 可以激活虚拟环境`.venv\Scripts\Activate.ps1`
- [ ] 可以运行测试`python -m pytest tests/unit -v`

### 功能验证
- [ ] Make命令正常工作（如果安装了Make）
- [ ] PowerShell脚本`.\scripts\run_pytest.ps1`可以执行
- [ ] `make check`通过（如果可用）
- [ ] `make test`通过（如果可用）

### 文档验证
- [ ] 文档中的路径格式统一为Windows格式
- [ ] 没有残留的WSL相关引用
- [ ] 所有脚本使用PowerShell语法

## ⚠️ 注意事项

### 1. .gitignore配置
`.vscode/`已在.gitignore中，这是正确的，因为IDE配置不应该提交到Git。

### 2. Makefile兼容性
- 如果需要在Windows上使用`make`命令，需要安装[Gnu Make for Windows](https://gnuwin32.sourceforge.net/packages/make.htm)
- 如果不想安装Make，可以直接使用PowerShell脚本

### 3. 执行策略问题
如果遇到"无法加载脚本"的错误，需要设置PowerShell执行策略：
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 4. 临时文件清理
旧的WSL测试结果文件`test_output/pytest_results.txt`已删除，新的测试将在PowerShell环境下生成。

## 📚 参考文档

- [ENV_MIGRATION_WSL_TO_POWERSHELL.md](ENV_MIGRATION_WSL_TO_POWERSHELL.md) - 详细的迁移说明
- [IDE_SETUP_POWERSHELL.md](IDE_SETUP_POWERSHELL.md) - VS Code配置指南
- [AGENTS.md](AGENTS.md) - Agent开发指南
- [PROJECT_CONSTITUTION.md](PROJECT_CONSTITUTION.md) - 项目宪法

## 🚀 下一步

配置验证完成后，可以继续：

1. **运行测试验证环境**：
   ```powershell
   python -m pytest tests/unit -v
   ```

2. **开始开发工作**：
   ```powershell
   .\scripts\dev_workflow.ps1
   ```

3. **继续阶段5任务**（适配器层实现）

---

**检查清单版本**: 1.0.0
**最后更新**: 2026-01-31
**维护者**: JCIA Team
