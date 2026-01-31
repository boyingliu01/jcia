# 🚀 JCIA 工程纪律快捷命令 - 快速入门

## ⚡ 一分钟快速开始

### 步骤 1: 重新加载 VS Code (如果刚修改了配置)
```
Ctrl + Shift + P
输入: Reload Window
回车
```

### 步骤 2: 打开终端
```
Ctrl + ~ (波浪号)
或
Ctrl + Shift + ~ (波浪号)
```

### 步骤 3: 使用快捷命令
```powershell
/check    # 运行完整工程纪律检查 (6项)
```

## 📋 所有可用命令

| 命令 | 功能 | 快捷键 |
|------|------|---------|
| `/check` | 📊 **完整工程纪律检查 (6项)** | `Ctrl+Shift+A` ⭐ |
| `/lint` | 📝 代码规范检查 | `Ctrl+Shift+C` `Ctrl+Shift+L` |
| `/format` | 🎨 代码格式化 | `Ctrl+Shift+C` `Ctrl+Shift+F` |
| `/typecheck` | 🔍 类型检查 | `Ctrl+Shift+C` `Ctrl+Shift+T` |
| `/security` | 🔒 安全扫描 | `Ctrl+Shift+C` `Ctrl+Shift+S` |
| `/test` | 🧪 单元测试 | `Ctrl+Shift+C` `Ctrl+Shift+U` |
| `/test-cov` | 📊 带覆盖率的测试 | - |
| `/all` | 🔄 运行所有检查 | - |
| `/clean` | 🧹 清理构建产物 | - |
| `/commit` | 📝 Git 提交代码 (交互式) | - |
| `/commit-auto` | 🤖 Git 提交代码 (自动消息) | - |
| `/save` | 💾 Git 快速保存 | - |
| `/status` | 📊 Git 状态 | - |
| `/log` | 📋 Git 日志 | - |


## 🎯 三种使用方式

### 方式 1: 终端命令 (推荐) ⭐

```powershell
# 在 VS Code 终端中输入
PS> /check
PS> /test
PS> /format
```

### 方式 2: VS Code 任务面板

```
1. Ctrl + Shift + P (打开命令面板)
2. 输入: Tasks: Run Task
3. 选择任务，例如:
   - /check - 工程纪律完整检查
   - /lint - 代码规范检查 (Ruff)
   - /test - 运行单元测试 (Pytest)
```

### 方式 3: 快捷键

```
Ctrl + Shift + A    # 运行 /check (最常用！)
Ctrl + Shift + B    # 显示任务面板
```

## 📝 /check 命令执行内容

执行顺序（约40秒）：

1. ✅ Ruff Lint - 代码规范检查 (~8s)
2. ✅ Ruff Import - 导入排序检查 (~7s)
3. ✅ Ruff Format - 代码格式化 (~5s)
4. ✅ Pyright - 类型检查 (~11s)
5. ✅ Bandit - 安全扫描 (~5s)
6. ✅ Pytest - 单元测试 (~7s)

**结果**: 所有检查通过 → 可以提交代码！

## 🚨 常见使用场景

### 场景 1: 刚完成代码修改
```powershell
/check    # 运行完整检查
```

### 场景 2: 只想格式化代码
```powershell
/format    # 只格式化，不运行其他检查
```

### 场景 3: 只想运行测试
```powershell
/test      # 只运行测试，不运行其他检查
```

### 场景 4: 分步检查
```powershell
/lint        # 先检查代码规范
/format       # 然后格式化
/typecheck    # 再检查类型
/test         # 最后运行测试
```

### 场景 5: 提交代码到 Git
```powershell
/commit       # 交互式提交 (输入提交信息)
/commit-auto   # 自动提交 (使用自动消息)
/save         # 快速保存当前成果
```

### 场景 6: 查看 Git 状态和历史
```powershell
/status       # 查看当前 Git 状态
/log          # 查看最近10条提交
```


### 场景 5: 查看覆盖率
```powershell
/test-cov   # 运行测试并显示覆盖率
```

## 🔧 配置文件说明

### .vscode/tasks.json
VS Code 任务配置文件，定义了所有快捷任务：
- 任务标签（如 `/check - 工程纪律完整检查`）
- 执行命令
- 工作目录
- 显示选项

### .vscode/keybindings.json
VS Code 快捷键配置文件：
- `Ctrl+Shift+A` - 运行 `/check`
- 其他组合键用于特定任务

### scripts/init_aliases.ps1
PowerShell 别名初始化脚本：
- 定义了 `/check`, `/lint`, `/format` 等命令
- 在新终端中自动加载

## 📚 完整文档

- **快捷命令详细指南**: [QUICK_COMMANDS.md](mdc:.codebuddy/QUICK_COMMANDS.md)
- **工程纪律检查清单**: [DISCIPLINE_CHECKLIST.md](mdc:.codebuddy/DISCIPLINE_CHECKLIST.md)
- **项目配置指南**: [AGENTS.md](mdc:AGENTS.md)

## ⚠️ 注意事项

### 必须在 VS Code 终端中使用
- ✅ 正确: VS Code 集成终端
- ❌ 错误: 系统 PowerShell 或 CMD

### 命令前缀是斜杠
- ✅ 正确: `/check`
- ❌ 错误: `check` 或 `\check`

### 检查失败必须修复
- ❌ 不能跳过失败的检查
- ❌ 不能使用 `git commit --no-verify`
- ✅ 必须修复所有问题后重新运行 `/check`

## 🎓 学习提示

### 第一次使用
1. 重新加载 VS Code 窗口
2. 打开新终端
3. 输入 `/check`
4. 观察执行过程
5. 等待所有检查通过

### 推荐工作流
```
1. 编写代码
2. /check (自动运行6项检查)
3. 修复问题（如果有）
4. 重新运行 /check
5. 所有通过后提交
```

### 记住快捷键
```
Ctrl + Shift + A    # 最重要！一键运行完整检查
Ctrl + Shift + B    # 打开任务面板
```

---

**就这么简单！** 使用 `/check` 命令，一键完成所有工程纪律检查，无需每次输入长命令！🎉
