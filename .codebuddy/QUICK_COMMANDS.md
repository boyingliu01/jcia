# JCIA 工程纪律快捷命令使用指南

## 🚀 快速开始

在 VS Code 终端中，使用以下斜杠命令快速执行工程纪律检查：

```powershell
/check       # 运行工程纪律完整检查 (6项)
```

## 📋 可用快捷命令

| 命令 | 说明 | 快捷键 |
|--------|------|---------|
| `/check` | 工程纪律完整检查 (6项全部执行) | `Ctrl+Shift+A` |
| `/lint` | 代码规范检查 (Ruff) | `Ctrl+Shift+C` `Ctrl+Shift+L` |
| `/format` | 代码格式化 (Ruff) | `Ctrl+Shift+C` `Ctrl+Shift+F` |
| `/typecheck` | 类型检查 (Pyright) | `Ctrl+Shift+C` `Ctrl+Shift+T` |
| `/security` | 安全扫描 (Bandit) | `Ctrl+Shift+C` `Ctrl+Shift+S` |
| `/test` | 运行单元测试 (Pytest) | `Ctrl+Shift+C` `Ctrl+Shift+U` |
| `/test-cov` | 带覆盖率的测试 | - |
| `/all` | 运行所有检查 (lint+format+typecheck+security+test) | - |
| `/clean` | 清理构建产物 | - |
| `/commit` | Git 提交代码 (交互式) | - |
| `/commit-auto` | Git 提交代码 (自动消息) | - |
| `/save` | Git 快速保存 | - |
| `/status` | Git 状态 | - |
| `/log` | Git 日志 | - |


## 🔧 使用方式

### 方式1: VS Code 终端 (推荐)

1. 打开 VS Code 终端 (`Ctrl+~`)
2. 输入命令：`/check`
3. 按回车执行

```powershell
PS E:\Study\LLM\Java代码变更影响分析> /check
```

### 方式2: VS Code 任务面板

1. 按 `Ctrl+Shift+P` 打开命令面板
2. 输入 "Tasks: Run Task"
3. 选择任务：
   - `/check - 工程纪律完整检查`
   - `/lint - 代码规范检查 (Ruff)`
   - `/format - 代码格式化 (Ruff)`
   - 等等...

### 方式3: 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+Shift+A` | 运行工程纪律完整检查 |
| `Ctrl+Shift+C` `Ctrl+Shift+D` | 运行工程纪律完整检查 |

### 方式4: VS Code 侧边栏

1. 按 `Ctrl+Shift+B` 显示运行任务
2. 在任务列表中双击执行

## 📝 /check 命令详解

`/check` 命令执行以下6项检查：

1. ✅ **Ruff Lint** - 代码规范检查
   - 自动修复简单的 linting 问题
   - 输出：`All checks passed!`

2. ✅ **Ruff Import** - 导入排序检查
   - 确保符合 PEP 8 导入规范
   - 输出：`All checks passed!`

3. ✅ **Ruff Format** - 代码格式化
   - 检查代码格式是否符合标准
   - 输出：`38 files left unchanged`

4. ✅ **Pyright** - 静态类型检查
   - 严格的类型检查
   - 输出：`0 errors, 0 warnings`

5. ✅ **Bandit** - 安全漏洞扫描
   - Python 安全最佳实践检查
   - 输出：`No issues identified.`

6. ✅ **Pytest** - 单元测试
   - 运行所有单元测试
   - 输出：`68 passed, 0 failed`

### 执行结果示例

```
╔══════════════════════════════════════════════════════════╗
║  JCIA 工程纪律强制检查                                       ║
╚══════════════════════════════════════════════════════════╝

环境检查:
  虚拟环境: ✓ 存在
  Python: Python 3.13.9
  工作目录: E:\Study\LLM\Java代码变更影响分析

开始执行完整质量门禁检查...

  [执行] 1. Ruff Lint 代码规范检查 ...  [✓ PASS] 1. Ruff Lint 代码规范检查 (05.536s)
  [执行] 2. Ruff Import 排序检查 ...  [✓ PASS] 2. Ruff Import 排序检查 (05.236s)
  [执行] 3. Ruff Format 代码格式化 ...  [✓ PASS] 3. Ruff Format 代码格式化 (04.296s)
  [执行] 4. Pyright 静态类型检查 ...  [✓ PASS] 4. Pyright 静态类型检查 (08.455s)
  [执行] 5. Bandit 安全漏洞扫描 ...  [✓ PASS] 5. Bandit 安全漏洞扫描 (03.445s)
  [执行] 6. Pytest 单元测试 ...  [✓ PASS] 6. Pytest 单元测试 (09.421s)

══════════════════════════════════════════════════════════

  ✓✓✓ 所有检查通过！工程纪律合格 ✓✓✓

  你现在可以安全地提交代码：
    git add .
    git commit -m '你的提交信息'
```

## 🔍 检查失败时的处理

如果某项检查失败，会显示详细错误信息：

```
  [✗ FAIL] 4. Pyright 静态类型检查 (08.455s)
         检查失败，输出见下方

--- 错误输出 ---
  e:\Study\LLM\Java代码变更影响分析\jcia\adapters\git\pydriller_adapter.py
    e:\...\pydriller_adapter.py:58:24 - error: Argument of type "str | None" cannot be assigned...
--- 结束 ---
```

### 修复步骤

1. 查看错误信息
2. 修复代码问题
3. 重新运行 `/check`
4. 确保所有检查通过

## 🎯 推荐工作流程

### 开发后检查

```powershell
# 完成代码修改后
/check        # 运行完整检查

# 或分步检查
/lint         # 先检查代码规范
/format       # 再格式化代码
/typecheck    # 然后检查类型
/test         # 最后运行测试
```

### 提交前检查

```powershell
# 确保所有检查通过
/check

# 如果通过
/save
```


### 只运行特定检查

```powershell
# 只格式化代码
/format

# 只运行测试
/test

# 只检查类型
/typecheck
```

## 📝 配置文件说明

### .vscode/tasks.json
定义了 VS Code 任务：
- `/check - 工程纪律完整检查` (默认任务)
- `/lint - 代码规范检查 (Ruff)`
- `/format - 代码格式化 (Ruff)`
- `/typecheck - 类型检查 (Pyright)`
- `/security - 安全扫描 (Bandit)`
- `/test - 运行单元测试 (Pytest)`
- `/test-cov - 带覆盖率的测试`
- `/clean - 清理构建产物`
- `/commit - Git 提交代码 (交互式)`
- `/commit-auto - Git 提交代码 (自动消息)`
- `/save - Git 快速保存`
- `/status - Git 状态`
- `/log - Git 日志`


### .vscode/keybindings.json
定义了快捷键：
- `Ctrl+Shift+A` - 运行 `/check` (工程纪律完整检查)
- `Ctrl+Shift+C` `Ctrl+Shift+L` - 运行 `/lint`
- `Ctrl+Shift+C` `Ctrl+Shift+F` - 运行 `/format`
- 等等...

### scripts/init_aliases.ps1
PowerShell 别名初始化脚本：
- 创建 `/check`, `/lint`, `/format` 等命令别名
- 可以在终端中直接使用

## 🚀 首次使用

### 1. 重新加载 VS Code
修改配置文件后，重新加载 VS Code 窗口：
- 按 `Ctrl+Shift+P`
- 输入 "Reload Window"
- 选择 `Developer: Reload Window`

### 2. 在新终端中测试
1. 打开新终端 (`Ctrl+Shift+~`)
2. 输入 `/check`
3. 按回车执行

### 3. 验证快捷键
1. 按 `Ctrl+Shift+A`
2. 应该自动运行 `/check` 命令

## ⚡ 常见问题

### Q: 为什么命令不起作用？
A: 确保在 VS Code 终端中，而不是系统 PowerShell。

### Q: 如何查看所有可用任务？
A: 按 `Ctrl+Shift+B` 打开任务面板。

### Q: 可以自定义快捷键吗？
A: 可以，在 `.vscode/keybindings.json` 中修改。

### Q: 如何添加更多命令？
A: 在 `.vscode/tasks.json` 中添加新任务定义。

---

**提示**: 所有命令都在项目 `.codebuddy/DISCIPLINE_CHECKLIST.md` 中有详细说明。
