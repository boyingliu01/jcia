# JCIA AI Agent 工程纪律合规检查清单

> ⚠️ **强制执行**: 每次代码修改后，必须完成以下全部检查才能提交代码！

## 强制检查流程（必须按顺序执行）

### Phase 1: 代码质量检查

- [ ] **1. Ruff Lint 检查** - 代码规范符合项目标准
  ```powershell
  .venv\Scripts\python -m ruff check jcia tests
  ```
  - 期望输出: `All checks passed!`
  - 如有错误，先尝试自动修复: `ruff check jcia tests --fix`

- [ ] **2. Ruff Import 排序检查** - 导入顺序符合 PEP 8
  ```powershell
  .venv\Scripts\python -m ruff check --select I jcia tests
  ```
  - 期望输出: `All checks passed!`

- [ ] **3. Ruff Format 格式化** - 代码格式统一
  ```powershell
  .venv\Scripts\python -m ruff format jcia tests
  ```
  - 期望输出: `X files already formatted` 或 `X files reformatted`

### Phase 2: 类型安全检查

- [ ] **4. Pyright 静态类型检查** - 所有类型注解正确
  ```powershell
  .venv\Scripts\python -m pyright jcia tests
  ```
  - 期望输出: `0 errors, 0 warnings`
  - 常见错误:
    - `dict[str, any]` → `dict[str, Any]` (需要导入 `from typing import Any`)
    - 使用 `str | None` 替代 `Optional[str]`
    - `@dataclass` 的列表字段使用 `field(default_factory=list)`

### Phase 3: 安全扫描

- [ ] **5. Bandit 安全漏洞扫描** - 无安全隐患
  ```powershell
  .venv\Scripts\python -m bandit -r jcia -c pyproject.toml
  ```
  - 期望输出: `No issues identified.`

### Phase 4: 功能测试

- [ ] **6. 单元测试全部通过** - 所有测试用例通过
  ```powershell
  .venv\Scripts\python -m pytest tests/unit -v
  ```
  - 期望输出: `X passed, 0 failed, 0 skipped`
  - 如果有测试失败，必须修复后才能提交
  - 注意: 测试间状态污染问题（批量失败但单独通过）需检查 `@patch` 路径

### Phase 5: 集成验证

- [ ] **7. 快速功能验证** - 关键功能可用
  ```powershell
  .venv\Scripts\python -c "import jcia; print('✓ 模块导入成功')"
  ```

## 一键完整检查脚本

使用以下命令执行**所有检查**：

```powershell
# 方法1: 使用强制纪律脚本（推荐）
powershell -ExecutionPolicy Bypass -File scripts/enforce_discipline.ps1

# 方法2: 使用 Makefile
make check && make test-unit

# 方法3: 手动顺序执行
ruff check jcia tests
ruff check --select I jcia tests
ruff format jcia tests
pyright jcia tests
bandit -r jcia -c pyproject.toml
pytest tests/unit -v
```

## 提交前必须满足的条件

| 检查项 | 通过标准 | 失败后操作 |
|--------|----------|-----------|
| Ruff Lint | 0 errors, 0 warnings | 执行 `ruff check --fix` 后手动修复剩余问题 |
| Ruff Format | 所有文件已格式化 | 执行 `ruff format jcia tests` |
| Pyright | 0 errors, 0 warnings | 手动修复类型错误 |
| Bandit | No issues identified | 手动修复安全问题 |
| Pytest | 100% tests passed | 修复测试或代码直至通过 |

## 常见错误快速修复

### 错误1: 类型注解问题
```python
# ❌ 错误
def func(data: any) -> dict[str, any]:

# ✅ 正确
from typing import Any
def func(data: Any) -> dict[str, Any]:
```

### 错误2: Mock 测试路径问题
```python
# ❌ 错误 - 批量测试时 patch 不生效
@patch("pydriller.Repository")

# ✅ 正确 - patch 实际导入路径
@patch("jcia.adapters.git.pydriller_adapter.Repository")
```

### 错误3: 返回值配置错误
```python
# ❌ 错误
mock_run.return.return_value = "..."

# ✅ 正确
mock_run.return_value = Mock(stdout="...", returncode=0)
```

## 工程纪律红线 ❌

以下行为**严格禁止**：

1. **禁止跳过检查**: 不允许使用 `git commit --no-verify` 绕过 pre-commit hooks
2. **禁止选择性检查**: 不能只运行部分检查，必须执行完整流程
3. **禁止提交未测试代码**: 所有代码必须通过单元测试
4. **禁止忽略类型错误**: 不能滥用 `# type: ignore` 抑制类型检查
5. **禁止降低覆盖率**: 新增代码必须保持 80%+ 覆盖率

## 检查失败时的处理流程

```
1. 发现检查失败
   ↓
2. 查看详细错误信息
   ↓
3. 修复问题（可以请求帮助）
   ↓
4. 重新运行完整检查流程
   ↓
5. 所有检查通过后，才能执行 git commit
```

## 合规声明

每次提交代码前，必须在提交信息中确认已完成所有检查：

```bash
git commit -m "feat: add new feature

- 实现 XXX 功能
- 添加单元测试
- 工程纪律检查: [✓] Ruff [✓] Pyright [✓] Bandit [✓] Pytest"
```

---

**记住: 质量是每个人的责任，工程纪律是质量的保障！**
