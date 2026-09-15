# JCIA 发布手册（RELEASE RUNBOOK）

> 适用范围：把 JCIA 发布到 PyPI 并创建对应的 GitHub Release。
> 本手册中的每一条断言都在 2026-09-15 的 v0.2.0 发布过程中实测核实过；
> 未核实的推断一律标注为「待核实」，不得当作依据。

---

## 0. 发布模型一览

```
打附注标签 v<X.Y.Z>  ──▶  git push origin v<X.Y.Z>
                                 │
                                 ├─ 本地 pre-push 钩子（Gate MW 代码走查门）
                                 │    证据过期 / 共识不足 ──▶ 整体 push 失败，无副作用
                                 │
                                 ▼
                    .github/workflows/release.yml
                                 │
        ┌────────────────────────┼─────────────────────────┐
        ▼                        ▼                         ▼
   build                   publish-pypi              github-release
 （可逆，失败即停）      （不可逆！版本号永久占用）      needs: [build, publish-pypi]
```

关键设计（**已在 HEAD 的实现中核实**）：

- 不可逆步骤 `publish-pypi` 排在 `github-release` **之前**：包真正可从 PyPI 安装后才对外宣布 Release，
  避免留下指向未发布版本的公开 Release。
- `concurrency.cancel-in-progress: false`：发布运行不允许被后续 push 取消。
- `permissions` 在 job 级整体覆盖 workflow 级，各 job 只拿自己需要的最小权限。

---

## 1. 发布前硬性前置（缺一即失败）

### 1.1 PyPI 侧：Trusted Publishing（OIDC）已注册

本项目**不使用 API token**。`release.yml` 通过 `id-token: write` 换取短期 OIDC token 上传，
因此要求 PyPI 账户侧存在匹配的 publisher。

入口：登录 pypi.org → **Your account** → 侧边栏 **Publishing** → *Add a new publisher* → 选 **GitHub**。

字段（逐字标签取自 PyPI 开源仓库 `warehouse/templates/manage/account/publishing.html`）：

| 页面标签 | 填什么 | 本项目取值 |
|---|---|---|
| `PyPI Project Name` | 发布时将要创建/匹配的项目名 | `jcia` |
| `Owner` | GitHub 组织名或用户名（**不是** "Repository owner"） | `boyingliu01` |
| `Repository name` | 仓库名 | `jcia` |
| `Workflow name` | ⚠️ 字段 id 是 `workflow_filename`，要填**文件名**，不是 YAML 里的 `name: Release` | `release.yml` |
| `Environment name` | optional，须与 workflow 中 `environment:` 一致 | `pypi` |

**两道硬门槛**（同样核实自 warehouse 模板源码）：

1. 账户**未开启 2FA** → 整个 publisher 表单被一段警告 callout 整体替换，看不到任何字段。
2. 主邮箱**未验证**（`pending_oidc_enabled = user.has_primary_verified_email`）→ `Add` 按钮渲染为 disabled。

**pending publisher 不预留项目名**。名字在首次真实上传时才被创建，
在此之前任何人抢注 `jcia` 都会让 publisher 失效。注册与发布之间不要留时间窗。

核实命令：

```powershell
# 返回 404 表示名字仍空闲；返回 200 表示已被占用（含被自己占用）
curl -s -o NUL -w "%{http_code}" https://pypi.org/pypi/jcia/json
```

### 1.2 PyPI 侧登录遇到 "Unrecognized device"

从新设备/新浏览器登录会跳到 `/account/confirm-login/`，需要点邮件确认
（发件人 `noreply@pypi.org`，主题 `Unrecognized login to your PyPI account`）。
该确认链接有约 15 分钟限流。**自动化浏览器会话无法替你完成这一步**——
它要求人类点击邮箱里的链接。

### 1.3 本地侧：Gate MW 走查证据必须新鲜

pre-push 钩子校验 `.code-walkthrough-result.json`：

- 证据绑定的 commit 必须等于**当前 checkout 的 HEAD**（不是被推的 ref）
- TTL 恰好 **1 小时**，`expires` 过期即拒绝
- `consensus_ratio` 必须落在 `[0.90, 1]`，且专家数恰好 3 位
- 判定必须为 `APPROVED`

> ⚠️ 时间戳必须由可信时钟签发。若证据文件被编辑器回退成旧的 Python 时钟版本，
> 会出现「本地看着没问题、push 被拦」的现象。

---

## 2. 标准发布步骤

```powershell
# ── 步骤 1：工作区必须干净（禁止 git add -A 兜底）
git status --porcelain          # 期望：无输出
git pull --ff-only              # 确保 HEAD == origin/master

# ── 步骤 2：版本三源一致性（release.yml 里也有同样的守卫，本地先跑一次省一趟 CI）
python -c "import tomllib;print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"
python -c "import jcia;print(jcia.__version__)"

# ── 步骤 3：打附注标签（指向当前 HEAD）
git tag -a v0.2.0 -m "release: v0.2.0"

# ── 步骤 4：断言标签 peel 到 HEAD —— 这是最容易出错的一步
git rev-list -n1 v0.2.0         # 必须与 git rev-parse HEAD 逐字相等
git rev-parse HEAD

# ── 步骤 5：确认实际会被 CI 执行的那份 workflow 就是评审过的版本
git show v0.2.0:.github/workflows/release.yml | Select-String 'github-release|Guard|Smoke'
git diff --stat v0.2.0 -- .github/workflows/release.yml   # 期望：无输出

# ── 步骤 6：签发新鲜证据（TTL 1 小时，签发后立刻推送，不要中途去做别的事）
# ── 步骤 7：推送标签
git push origin v0.2.0
```

**为什么步骤 4 最关键**：GitHub Actions 对 tag push 是**从标签所指的 commit** 解析 workflow 的。
如果修复提交之后只更新了证据、忘了重签字确保标签指向新 SHA，
CI 会静默地跑一份**旧版 release.yml**——旧版没有版本守卫、没有安装烟测、甚至没有 `github-release` job。
Gate MW 结构上抓不到这种失败模式，因为它比对的是 commit diff，不是标签 peel 目标。

取标签 peel 目标的完整取证姿势（`for-each-ref` 的第一个字段是**标签对象**的 SHA，不是 commit）：

```powershell
git for-each-ref --format='%(objectname) %(objecttype) *%(*objectname)' refs/tags/v0.2.0
#                                                     ^^^^^^^^^^^^^^^^ 带 * 的才是 peel 后的 commit
```

只跑 `git rev-parse v0.2.0` 会把标签对象 SHA 误当成 commit，这是本项目评审中真实踩过两次的坑。

---

## 3. 发布物内容自查（已自动化进 CI）

`build` job 的 *Guard distribution against placeholder contacts* 步骤调用
`scripts/check_dist_placeholders.py`，解开 wheel 与 sdist 的**每一个成员**，
命中 `example.(org|com|net)` 即 `exit 1` 并逐行报出位置。

理由：`pyproject.toml` 的 `readme = "README.md"` 会把整篇 README 塞进
`METADATA` 的 long_description，发布后**永久渲染在 PyPI 项目页上，不可编辑，yank 也保留历史**。
占位邮箱一旦漏出去，只能靠下一个版本号覆盖叙事。

本地预跑（与 CI 是同一份实现，不存在漂移）：

```powershell
python -m build
python scripts/check_dist_placeholders.py   # 期望：placeholder guard OK
```

守卫实现刻意放在 `scripts/` 而非 `docs/` 或仓库根：已核实 `scripts/` **不进 sdist**，
否则守卫脚本自己写的匹配模式会被自己扫出来（同目录下的 `init_test_repo.py` 就含 `test@example.com`）。

已核实事实：

- sdist **不含** `tests/`（0 个成员），全成员扫描不会因测试夹具里的 `example.com` 误报。
- sdist 与 wheel 均**不含** `promotion/`，该目录下的占位邮箱不进任何发布物。
- `twine check` **不拦** markdown 正文里的占位邮箱——它只校验元数据格式，所以必须有上面这道专用守卫。

---

## 4. 发布后验证

```powershell
# 1. CI 三个 job 全绿
gh run list --workflow=release.yml --limit 3
gh run view <run-id> --log-failed

# 2. 从 PyPI 干净安装并跑通 CLI（这才是真正的验收）
python -m venv _verify
./_verify/bin/python -m pip install --no-cache-dir jcia
./_verify/bin/jcia --version        # 期望输出含 0.2.0

# 3. GitHub Release 存在且状态位正确
gh release view v0.2.0
```

---

## 5. 故障恢复

### 5.1 publish 成功后 github-release 失败

`publish-pypi` 已带 `skip-existing: "true"`（上游默认为 `false`）。
因此 **Re-run all jobs** 是可用的恢复路径：PyPI 会以 409 拒绝重复上传同一文件，
该步骤吞掉 409 继续成功，从而让下游 `github-release` 得以前进。

> 已核实语义边界（twine 源码级）：`skip-existing` 作用域是「版本 + 文件名」，
> 仅吞掉 409 与消息含 `already exist` 的 400；其余 400/5xx 依然 fail。
> 所以它不会掩盖真实的上传错误。

若不开关（历史遗留场景）：publish 成功后 Re-run 会在 `publish-pypi` 直接 400 失败，
而 `github-release` 因 `needs` 不满足永不执行，形成
「PyPI 有版本、GitHub Release 缺失」且 UI 最直觉的恢复按钮无效 的终态。
此时只能手动创建：

```powershell
gh run view <run-id> --job <build-job-id> --download dist
gh release create v0.2.0 dist/* --title v0.2.0 --generate-notes --latest
```

### 5.2 改 Release 的状态位

**已核实能力面**：`gh release upload` 只有 `--clobber`（覆盖附件），改状态位必须用 `gh release edit`：

```powershell
gh release edit v0.2.0 --draft=false
gh release edit v0.2.0 --prerelease
gh release edit v0.2.0 --latest
gh release edit v0.2.0 --verify-tag
```

### 5.3 版本号已在 PyPI 上占用，但内容有问题

PyPI **不允许覆盖**已上传的版本，唯一手段是 yank：

```powershell
# yank 后 pip 默认不再选该版本，但项目页与历史永久保留
# 正解是发一个补丁版本 0.2.1，并在 CHANGELOG 说明
```

---

## 6. 待核实事项（不要当成已知事实使用）

- GitHub 端 `pypi` environment 的 `protection_rules` 目前实测为空、`can_admins_bypass: true`。
  是否为发布所必需、是否应加 required reviewer，未做结论。
- `release.yml` 中 `github-release` 的预发布标签判定为
  `*-alpha*|*-beta*|*-rc*|*pre*|*dev*`。已核实该模式**不覆盖** `v0.2.0rc1` / `v1.0.0-RC1`
  这类无连字符/大写形态，会被误标为 `--latest`。本次 `v0.2.0` 为稳定版，不触发该缺口；
  未来发 RC 前须先补此判定。
