# JCIA 开源前安全审查清单

**审查日期**: 2026-02-27
**审查范围**: 全项目扫描
**最后更新**: 2026-02-27

---

## 状态说明

- [ ] 待修复
- [x] 已修复
- [~] 部分修复

---

## 一、高风险问题 (必须修复)

### 1.1 API密钥泄露

- [x] **文件**: `tests/integration/adapters/test_ai/test_volcengine_adapter_integration.py`
  - **行号**: 21
  - **问题**: 硬编码API密钥 `803de240-5683-4ce3-9cbd-0ad5192db942`
  - **风险**: 严重 - API密钥泄露可能导致未授权访问
  - **修复状态**: 已修复 - 重写为从环境变量读取，使用 pytest fixture

- [x] **文件**: `report/project_status_report.md`
  - **行号**: 97
  - **问题**: 文档中记录了相同的API密钥
  - **风险**: 高 - 文档可能被公开访问
  - **修复状态**: 已修复 - 替换为通用描述

### 1.2 内部路径泄露

- [x] **文件**: `dev-workflow/scripts/InstallCore.psm1`
  - **行号**: 14, 23
  - **问题**: 硬编码个人路径
  - **修复状态**: 已修复 - 使用通用路径

### 1.3 内部URL和域名

- [x] **文件**: `promotion/quickstart.md`
  - **问题**: 内部域名和Jira链接
  - **修复状态**: 已修复 - 替换为GitHub链接

- [x] **文件**: `.jcia.yaml.example`
  - **问题**: 内部服务地址
  - **修复状态**: 已修复 - 改为公开示例地址

- [x] **文件**: `promotion/demo_script.md`
  - **问题**: 内部Wiki链接
  - **修复状态**: 已修复 - 替换为GitHub链接

---

## 二、中风险问题 (建议修复)

### 2.1 内部邮箱地址

- [x] `promotion/summary.md` - 已修复
- [x] `promotion/quickstart.md` - 已修复
- [x] `promotion/poster_content.md` - 已修复
- [x] `promotion/email_template.md` - 已修复
- [x] `promotion/demo_script.md` - 已修复

### 2.2 内部推广材料

- [x] **文件**: `promotion/email_template.md`
  - **问题**: 标题为"JCIA 内部推广邮件模板"
  - **修复状态**: 已修复 - 重写为开源推广模板

- [x] **文件**: `promotion/summary.md`
  - **问题**: 描述"帮助公司同事了解和使用"
  - **修复状态**: 已修复 - 重写为开源社区推广

### 2.3 测试逻辑问题

- [x] **文件**: `tests/integration/adapters/test_ai/test_volcengine_adapter_integration.py`
  - **问题**: 跳过条件写反了
  - **修复状态**: 已修复 - 使用 pytest fixture 重构

---

## 三、低风险问题 (可选修复)

### 3.1 生成的报告文件

- [x] **目录**: `report/`
  - **修复状态**: 已修复 - 将 `report/*.html` 添加到 `.gitignore`

### 3.2 dev-workflow 目录

- [ ] **目录**: `dev-workflow/`
  - **问题**: 开发工作流配置目录
  - **建议**: 评估是否需要在开源版本中保留

### 3.3 示例配置中的内部名称

- [x] **文件**: `.jcia.yaml.example`
  - **修复状态**: 已修复 - 改为 `your-org`

---

## 四、新增文件

- [x] 创建 `.env.example` - 环境变量配置模板

---

## 五、验证清单

修复完成后，执行以下验证:

```bash
# 1. 确认无API密钥残留
grep -r "803de240" . --include="*.py" --include="*.md"
# 预期: 无输出

# 2. 确认无内部邮箱
grep -r "@company.com" . --include="*.md" --include="*.py" --include="*.yaml"
# 预期: 无输出

# 3. 确认 .env 在 .gitignore 中
grep "\.env" .gitignore
# 预期: 有输出

# 4. 运行安全扫描
bandit -r jcia -c pyproject.toml
# 预期: 无高危问题

# 5. 运行测试
python -m pytest tests/unit -v
# 预期: 全部通过
```

---

## 六、重要提醒

⚠️ **必须立即操作**:

即使代码中的API密钥已被移除，该密钥 `803de240-5683-4ce3-9cbd-0ad5192db942` 已经提交到 Git 历史中。请务必：

1. **立即在火山引擎控制台重置此密钥**
2. 考虑使用 `git filter-branch` 或 `BFG Repo-Cleaner` 从 Git 历史中彻底删除
3. 如果已推送到远程仓库，考虑强制推送（需团队协调）

---

## 七、修复摘要

| 类别 | 总数 | 已修复 | 待处理 |
|------|------|--------|--------|
| 高风险 | 5 | 5 | 0 |
| 中风险 | 8 | 8 | 0 |
| 低风险 | 3 | 2 | 1 |
| **总计** | **16** | **15** | **1** |

**待处理项**: `dev-workflow/` 目录是否保留，需项目维护者评估决策。