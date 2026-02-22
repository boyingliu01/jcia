# VS Code终端配置指南（PowerShell环境）

## 问题说明

在VS Code中创建新终端时，如果不是"PowerShell"，说明IDE的终端配置未使用PowerShell。本指南说明如何将默认终端更改为PowerShell。


## 解决方案

### 方法1：使用项目级配置（推荐）

我们已经在项目根目录创建了`.vscode/settings.json`配置文件，它会自动将此项目的默认终端设置为PowerShell。

**验证步骤**：

1. 关闭VS Code
2. 重新打开项目
3. 按 `Ctrl+`` 或点击"终端" → "新建终端"
4. 应该看到终端标题显示为"PowerShell"


### 方法2：手动设置VS Code默认终端

如果方法1不生效，可以手动设置：

1. 打开VS Code设置：`Ctrl+,` 或 `文件` → `首选项` → `设置`
2. 搜索：`terminal integrated default profile windows`
3. 选择：`PowerShell`
4. 保存设置

### 方法3：检查VS Code用户设置

确保全局设置中没有覆盖项目设置：

1. 打开设置：`Ctrl+,`
2. 搜索：`terminal integrated profiles windows`
3. 检查PowerShell配置是否存在且正确

## 已创建的配置文件

### .vscode/settings.json

```json
{
  "terminal.integrated.defaultProfile.windows": "PowerShell",
  "terminal.integrated.profiles.windows": {
    "PowerShell": {
      "source": "PowerShell",
      "icon": "terminal-powershell"
    }
  }
}
```

这个配置会：
- 将PowerShell设置为默认终端
- 显示PowerShell图标
- 排除临时文件和缓存目录

## 验证配置

### 检查当前终端

打开VS Code终端后，运行：

```powershell
# 查看当前Shell
$PSVersionTable.PSVersion

# 查看Python位置
where.exe python

# 查看Python版本
python --version
```

预期输出：
- PowerShell版本应该显示（如5.1或7.x）
- Python路径应该指向`.venv\Scripts\python.exe`（如果虚拟环境已激活）

### 检查虚拟环境激活

```powershell
# 激活虚拟环境
.venv\Scripts\Activate.ps1

# 验证Python路径
where.exe python

# 应该看到：E:\Study\LLM\Java代码变更影响分析\.venv\Scripts\python.exe
```

## 常见问题

### Q1: 激活虚拟环境时提示"无法加载，因为在此系统上禁止运行脚本"

**解决方案**：
```powershell
# 以管理员身份打开PowerShell，执行：
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Q2: 终端仍然不是PowerShell

**检查清单**：
- [ ] `.vscode/settings.json`文件是否存在于项目根目录
- [ ] VS Code是否已重启
- [ ] 用户设置是否覆盖了项目设置
- [ ] 工作区设置是否优先级正确

### Q3: 多个项目配置冲突

如果其他项目需要不同终端，而本项目需要PowerShell：

- 项目级设置（`.vscode/settings.json`）会覆盖用户级设置
- 只需要在本项目创建`.vscode/settings.json`即可


## 完整的开发环境初始化

### 1. 打开VS Code
```powershell
code "E:\Study\LLM\Java代码变更影响分析"
```

### 2. 创建虚拟环境（如果还没有）
```powershell
python -m venv .venv
```

### 3. 激活虚拟环境
```powershell
.venv\Scripts\Activate.ps1
```

### 4. 安装依赖
```powershell
pip install -e ".[dev]"
```

### 5. 配置pre-commit hooks
```powershell
pre-commit install
```

### 6. 验证环境
```powershell
make check
make test
```

## VS Code终端切换

如果需要临时切换终端：

### 切换到PowerShell
```
1. 点击终端标题栏右侧的下拉箭头
2. 选择"PowerShell"
```


## 相关配置文件

- `.vscode/settings.json` - VS Code项目设置（终端、Python路径等）
- `.vscode/launch.json` - VS Code调试配置
- `.vscode/tasks.json` - VS Code任务配置

## 下一步

配置完成后，可以继续进行项目开发：

```powershell
# 运行测试
python -m pytest tests/unit -v

# 运行开发工作流
.\scripts\dev_workflow.ps1

# 运行特定测试
python -m pytest tests/unit/core/test_change_set.py -v
```

---

**文档版本**: 1.0.0
**最后更新**: 2026-01-31
**维护者**: JCIA Team
