# 设计文档 v2 — Issue #23「wheel 资源守卫改进与 find_test_classes 契约固化」

> 依据: `build/_r2_requirements.md`（R1 需求评审两轮 3/3 APPROVED，consensus 1.0）
> v1 已获用户批准（DR-001，2026-09-23）；v2 修订响应 Delphi 设计 Round 1（0 critical / 7 major）
> 状态: **已冻结** — Round 2 复评 3/3 APPROVED（consensus 1.0，2026-09-23，0 critical）；§4.2 为
> Round 2 non-blocking 意见的 BUILD 落地清单

## 0. v1→v2 修订摘要（R2 设计 Round 1 响应）

- 7 条 major 全部落地（详见 §4.1）；采纳 minor：exclude 规则收窄、sdist 前缀候选集、
  find 回退规则固化、tar `./` 剥离、`[project]` 缺键转 ValueError、测试映射表、
  验证计划定稿、CHANGELOG 精简、monkeypatch 隔离注明
- 明示不改/降级的 minor：frozen dataclass 含 Path（Path 不可变，无实害）；
  release.yml 清理陈旧 `dist/`（超出本 issue 范围，列入非目标）

## 1. 设计目标与约束

- 8 项 REQ 全部闭环；守卫零静默路径（一切不确定形态 fail-closed）
- 不引入运行时依赖（`tomli` 仅 dev extra 且仅 <3.11）；不改守卫 CLI 用法
- 兼容 Python 3.10/3.11/3.12（单测矩阵）；**门禁运行时显式为 Python 3.12**：
  ci.yml 矩阵含 3.12，release.yml `ubuntu-latest` + bash + Python 3.12
  （setup-python@v5，L19/L26 已核实），仅装 build/twine，守卫仅需标准库；
  3.10 分支由 dev extra 的 tomli 条件依赖兜底（见 §3.3）
- 守卫文档化用法为 `python -m build`（双产物）；solo-wheel 构建将 fail-closed
  （D6，见 §3.1），属有意收紧

## 2. 影响面（文件清单）

| 文件 | 变更类型 |
|------|----------|
| `scripts/check_wheel_assets.py` | 核心重写（派生/三态 loader/sdist/.py 对账/性能/注释） |
| `tests/unit/scripts/test_check_wheel_assets.py` | 大改（helper + 现有 11 条改造 + 新增 ~20 条） |
| `jcia/adapters/tools/source_code_call_graph_adapter.py` | `find_test_classes`：空串守卫 + docstring 四节契约 |
| `tests/unit/adapters/test_tools/test_source_code_call_graph_adapter.py` | +4 边界测试 |
| `pyproject.toml` | dev extra 加 `tomli` 条件依赖；package-data 注释改写（去"人工同步"） |
| `.github/workflows/release.yml` | 构建前 clean 步骤（`build/` + `*.egg-info`） |
| `CHANGELOG.md` | `[Unreleased]` 记录（草案见 §7，含 D6 行为变更声明） |
| `CONTRIBUTING.md` | PR 检查清单 +1 条（公开 API 变更 → CHANGELOG，含具体判定例） |

## 3. 模块设计

### 3.1 scripts/check_wheel_assets.py

**D6（新增决策）— dist 必须同时含 wheel 与 sdist，对称 fail-closed**

- 依据：release.yml L51-52 用 `python -m build` 全量构建，发布的 dist 天然双产物；
  守卫是发布门禁，产物缺失必须响亮失败（零静默路径）
- 影响：本地 `python -m build --wheel` 场景将报 FileNotFoundError，错误消息提示
  「run `python -m build`（同时构建 sdist）」；docstring 用法同步更新
- 同步落点：REQ-06 验收清单补充本条；CHANGELOG Changed 条目（§7）；
  新增测试 `test_dist_without_sdist_raises`（现有 `test_dist_without_wheel_raises`
  语义不变——缺 wheel 仍报错，二者对称不冲突）

**TOML 加载（REQ-01，import 形态固化为可测语义）**

```python
def _toml_loader() -> ModuleType:
    # 函数内延迟导入：每次调用重新执行 import 语句 -> 在调用时刻查 sys.modules，
    # 使 monkeypatch.setitem(sys.modules, "tomllib", None) 真实触发 ImportError
    # （Python 官方语义：sys.modules 中值为 None 时 import 抛 ImportError）。
    # 形态固定为 `import tomllib`（模块对象），禁止 `from tomllib import loads`。
    try:
        import tomllib  # noqa: PLC0415  (Python>=3.11 内置)
        return tomllib
    except ImportError:
        pass
    try:
        import tomli  # noqa: PLC0415  (3.10 回退，dev extra 条件依赖)
        return tomli
    except ImportError as exc:
        raise ImportError(
            "TOML 解析器不可用：Python>=3.11 自带 tomllib；"
            "3.10 请安装 dev extra（pip install -e '.[dev]'，含 tomli）"
        ) from exc


def _load_pyproject(path: Path) -> dict:
    # path.read_text(encoding="utf-8") -> _toml_loader().loads(text)
    # 缺失 -> FileNotFoundError（含路径）；损坏 -> TOMLDecodeError（main 映射退出码 1）
```

三态测试手法（monkeypatch 自动还原，严格隔离）：
1. 常态：真实环境可 import（3.11+ → tomllib；3.10 → 已装 tomli）
2. 回退态：`monkeypatch.setitem(sys.modules, "tomllib", None)` + 注入 fake
   `tomli` 模块（`types.ModuleType` + loads）→ 返回 fake tomli
3. 双缺态：tomllib 与 tomli 均置 None → ImportError（消息含安装指引）

**配置派生（全部 fail-closed）**

```python
def _derive_resource_dirs(pyproject, repo_root: Path) -> tuple[tuple[Path, str], ...]
def _derive_package_roots(pyproject, repo_root: Path) -> tuple[str, ...]
def _derive_sdist_prefix_candidates(pyproject) -> tuple[str, ...]
@dataclass(frozen=True)
class GuardConfig:
    resource_dirs: tuple[tuple[Path, str], ...]
    package_roots: tuple[str, ...]
    sdist_prefix_candidates: tuple[str, ...]
    repo_root: Path
def _load_config(pyproject_path: Path) -> GuardConfig   # repo_root = pyproject_path.resolve().parent
```

- **resource_dirs**：键 `K`→包目录 `K.replace(".","/")`；值仅 `<rel>/*`；
  键含 `*` / 非该形态 / 空 values / 空集 → ValueError（含条目原文）；
  **v2 新增**：`(repo_root / 包目录 / rel).is_dir()` 为假 → ValueError（含条目原文）
  ——与包根存在性校验对称，消除"目录被删/改名 → 枚举空真静默通过"路径
- **package_roots**：`find.include` 每 pattern 取首个通配符前字面前缀、去尾 `.`；
  前缀含 `.`（子包 pattern）或为空 → ValueError；find 缺失时读
  `[tool.setuptools].packages` 显式列表（**v2 固化**：逐项取首个 dot 前顶层段、
  保序去重；项含 `*` 或首段为空 → ValueError）；
  派生包根在 repo_root 下不存在目录 → ValueError；空集 → ValueError
- **exclude 规则（v2 收窄）**：逐 pattern 取字面前缀 `e`，逐派生包根 `r`：
  `e` 为空 → ValueError；`e.startswith(r + ".")` → 合法（子包排除，docstring 声明
  「对账范围 = wheel 内 {root}/ 下的成员，子包排除不影响单向 .py 对账」）；
  否则若 `r.startswith(e)`（含相等/祖先，如 `jcia*` / `j*`）→ ValueError
  （可能整体排除某包根）；其余（如兄弟域 `tests*`）→ 合法。现有配置
  `include=["jcia*"], exclude=["tests*"]` 在新旧规则下均通过
- **sdist_prefix_candidates（v2 扩展）**：候选 = 去重{原始 name、PEP 503 形式
  `re.sub(r"[-_.]+","-",name).lower()`、下划线形式 `re.sub(r"[-_.]+","_",name).lower()`}
  各 + `f"-{version}/"`；`[project]` 或 name/version 缺失 → ValueError
  （消息含缺失键名）；version 不做 PEP 440 归一化（同上 fail-closed 方向）；
  docstring 声明「仅适用于静态版本声明（动态版本如 setuptools-scm 不在支持范围）」

**check() 新流程（REQ-04 性能：成员读取全部提到循环外）**

```python
def check(dist_dir=DIST_DIR, config: GuardConfig | None = None) -> list[str]:
    config = config or _load_config(_default_pyproject_path())
    wheels = dist/*.whl      # 空 -> FileNotFoundError
    sdists = dist/*.tar.gz   # 空 -> FileNotFoundError（D6 对称 fail-closed）
    members_by_wheel = {w: _wheel_members(w) for w in wheels}   # 每 wheel 仅打开一次
    members_by_sdist = {s: _sdist_members(s) for s in sdists}
    # ① 正向资源：wheel 成员 == wheel_prefix + name；sdist 成员 == sdist_prefix + wheel_prefix + name
    #    任一 sdist 前缀候选均不匹配 -> ValueError（消息含候选集与实测 top-level 集合）
    # ② 反向资源顶层（仅 wheel）：tail 含 "/" 跳过；点文件 is_file() 天然接受（有意不对称，REQ-05）
    # ③ 反向 .py 对账（仅 wheel，REQ-02b）：方向 = 产物→源码（见下）
```

- **③ 路径安全（v2 固化）**：成员名经 `PurePosixPath(member)` 校验——绝对路径或含
  `".."` 段 → 报错；拼接用 `config.repo_root.joinpath(*parts)`；`repo_root` 唯一来源
  为 `_load_config`（= pyproject 所在目录 resolve），check() 内不重算
- **③ 单向性显式声明（v2 固化，docstring + 设计）**：断言方向为「wheel 成员在源码树
  必须存在」，捕获陈旧成员逃逸（issue §2 原始向量：build/lib 残留 + SOURCES.txt 缓存）；
  反方向（源码 .py 漏打包）**不在断言内**，理由：陈旧缓存只会产生多余成员而非缺失
  （漏打包非该向量的失效形态），且漏打包由 setuptools 包发现保证、若发生将在导入期
  以 ImportError 响亮暴露（非静默向量）——与"零静默路径"目标不冲突
- **③ 流程**：成员以任一 `{root}/` 开头且 `.endswith(".py")`，排除 `__pycache__`；
  在 `_SOURCE_LESS_PY_ALLOWLIST`（预留常量，当前 `frozenset()`）中则豁免；
  `repo_root/成员` 不存在 → 报 stale
- **作用域边界（docstring 如实写明，v2 补充）**：`dist-info` 成员、非包根成员、
  顶层散落 `.py`、资源前缀下嵌套的非 `.py` 陈旧文件均不在断言内；生成 `.py` 默认报警，
  未来引入时加入白名单常量
- **tar `./` 前缀（v2）**：`_sdist_members` 读取时剥离成员名前导 `./` 再参与匹配
  （容忍未来构建后端差异），补对应 fixture 用例
- 点文件规则 sdist 与 wheel 一致（`.gitkeep` 豁免）；空真明确接受
- `main()`：FileNotFoundError / TOMLDecodeError / ValueError / OSError / BadZipFile /
  TarError → 退出码 1，消息含路径与异常类型

### 3.2 find_test_classes（REQ-03 / REQ-07）

```python
def find_test_classes(self, class_name: str) -> list[str]:
    """[四节契约]
    1. 输入形态: FQN 或简单类名（str）；FQN 取最后一段；非 str（含 None）为未定义行为
    2. 匹配规则: 缓存类简单名精确等于 {Simple}Test 或 Test{Simple}
    3. 不匹配情形: ServiceTests 等变体、子串近似名、无字面命名的嵌套类
    4. 返回值: 匹配类 FQN 列表；无匹配或空简单名 -> []
    """
    simple = class_name.rsplit(".", maxsplit=1)[-1]
    if simple == "":          # 严格空串判断（不吞 None 等 falsy 输入）
        return []
```

- `"   "` 纯空白：走正常流程自然无命中（测试锁定，不特判）
- 行为变化（`""` / `"com.example."` 由虚假命中改为 `[]`）→ REQ-08 CHANGELOG 记录

### 3.3 pyproject.toml

```toml
dev = [ ..., "tomli>=2.0; python_version < '3.11'",  # 守卫 TOML 回退（3.10 CI 矩阵）
]
```
`[tool.setuptools.package-data]` 注释改写：声明"守卫从本表自动派生，无需人工同步"。

### 3.4 release.yml（REQ-02a）

"Install build tooling" 与 "Build sdist and wheel" 之间插入：

```yaml
      - name: Clean stale incremental caches
        # build/lib 与 *.egg-info/SOURCES.txt 都是 setuptools 增量缓存：
        # 陈旧成员可能被重新打包且无告警。守卫的 stale 断言是出口兜底，
        # 这里从入口确定性消除（issue #23-REQ-02）。
        # glob 语义（v2 说明）：runner 为 ubuntu-latest，默认 shell bash；
        # `*.egg-info` 无匹配时 bash 将字面量传给 rm，`-f` 抑制"不存在"错误，
        # 步骤恒成功；有匹配时正常删除。
        run: rm -rf build *.egg-info
```

### 3.5 CHANGELOG.md / CONTRIBUTING.md（REQ-08）

见 §7 草案；CONTRIBUTING 新增条目的判定例具体化（**v2**）：
「移除/重命名公开函数或参数、改默认值/返回结构，或修复了可观察的行为召回变化
（例：find_test_classes 空串由虚假命中改为返回 []，见 #23）」。

## 4. R2 需求评审 5 条 major 的落地决议（v1 保留）

| # | 意见摘要 | 决议 |
|---|----------|------|
| 1 | release.yml 环境未核实（tomli 依赖闭环缺口） | **已核实**：release.yml 用 Python **3.12**（setup-python@v5），tomllib 内置；守卫仅需标准库，无需改版本。断言写入 §1 约束 |
| 2 | `_toml_loader` 三态测试手法可能假绿 | **已强化**（§3.1）：import 形态固化 + 每次调用重执行 import + 官方 None 语义 |
| 3 | 包根派生边界：子包 pattern / exclude 重叠 | **已定稿并收窄**（§3.1 exclude 三重规则） |
| 4 | sdist 前缀 name/version 规范化未说明 | **已扩展**（§3.1 候选集） |
| 5 | `None` falsy 与"出类型契约"表述不一致 | **定稿**：严格空串判断 `simple == ""`；非 str 为未定义行为（docstring 第 1 节） |

## 4.1 R2 设计评审（Delphi design Round 1）7 条 major 落地

| # | 意见摘要（匿名） | 决议（v2 修订） |
|---|------------------|------------------|
| 1 | check() sdist 缺失硬约束超出 REQ-06 授权、破坏本地 solo-wheel、须显式声明 | **保留 fail-closed（D6）但全量显式化**：REQ-06 验收补充断言；CHANGELOG Changed 条目；docstring 用法改 `python -m build`；错误消息含修复提示；新增对称测试。现有 `test_dist_without_wheel_raises` 语义不变 |
| 2 | REQ-02b 单向性未说明「漏打包」方向 | **显式声明单向 + 理由**（§3.1 ③）：陈旧向量本质单向（多余成员）；漏打包方向失效时以 ImportError 响亮暴露，非静默路径 |
| 3 | 三态 loader 测试未固化 import 形态（假绿风险） | **定稿**（§3.1）：`import tomllib` 模块形态、函数内延迟导入每次重执行、`sys.modules[name]=None` 官方语义；测试注入 fake tomli |
| 4 | release.yml clean 步骤 glob/bash 语义未说明 | **说明**（§3.4）：ubuntu-latest 默认 bash；`-f` 抑制无匹配错误，步骤恒成功 |
| 5 | sdist 前缀 name 归一化场景未覆盖 | **扩展**（§3.1）：候选集（原值/PEP503/下划线）+ 单测锁定派生字符串（name 含 `-`/`_` 样例）；错误消息列出候选与实测 top-level |
| 6 | resource_dirs 缺存在性 fail-closed（与包根不对称） | **采纳**（§3.1）：派生期 `is_dir()` 校验 → ValueError（含条目原文）+ 负向用例 |
| 7 | .py 对账路径拼接安全性 | **固化**（§3.1 ③）：PurePosixPath 校验（拒绝对路径/`..`）+ joinpath 拼接 + repo_root 单一来源 + 负向用例 |

采纳的 minor（v2）：exclude 规则收窄（合法子包排除不再误拒）；`[project]` 缺键转
ValueError（含键名）；find 缺失回退 packages 的转换规则固化；游离顶层 `.py` 与
`dist-info` 一并列入 docstring 边界清单；tar `./` 剥离 + fixture；现有 11 条测试
→ 改造后映射表（§5）；REQ-04 定性统一为"结构性重写的一部分（成员读取提到循环外），
零行为变化，以现有测试全绿客观验证"；§8 负向实测定稿为"fixture dist 删资源断言报错，
不触碰真实 dist"；CHANGELOG 精简 find_test_classes 表述。

明示不改/降级：frozen dataclass 含 Path（无实害）；release.yml 清理陈旧 `dist/`
（超本 issue 范围，列入非目标）。

## 4.2 Round 2 复评 non-blocking 意见 → BUILD 落地清单

Round 2 裁决：3/3 APPROVED（consensus 1.0，0 critical；3 条 major 被明示"不阻塞进入 BUILD"）。
以下为逐条落地安排（在对应 slice 内实现，作为 BUILD 验收的一部分）：

| # | 意见（匿名摘录） | BUILD 落地 | Slice |
|---|------------------|-----------|-------|
| 1 | D6 正当性依赖 release.yml 现状；若未来改 `--wheel` 分步构建将误报 | docstring 与 CHANGELOG 写明**显式前提**「守卫假定发布链路全量构建（`python -m build`）」；单测 `test_dist_without_sdist_raises` 锁定 solo-wheel 失败路径（防未来放宽回归） | S2/S5 |
| 2 | exclude 子包规则正确性仅靠推理 | 用真实子包排除样例（r=`jcia`、e=`jcia.tests`）锁定"合法且对账范围不受影响" | S1 |
| 3 | sdist 候选集可能仍不匹配（version 不归一化） | docstring 明示「候选集非穷尽，不匹配即 fail-closed（保守方向）」 | S2 |
| 4 | 「漏打包由 setuptools 包发现保证」是经验性论断 | docstring 标注该假设（namespace/build_py 定制时需复核） | S3 |
| 5 | PurePosixPath 未覆盖含反斜杠成员名（Windows 拼接风险） | 成员名校验一并拒绝反斜杠（含负向用例）；docstring 声明威胁模型（成员名恒为类 POSIX 形式） | S3 |
| 6 | ② 反向资源"仅 wheel"未列入边界清单 | docstring 边界清单补「sdist 不参与反向断言」 | S2 |
| 7 | dist 残留旧版本 sdist → 候选不匹配 fail-closed 未声明 | docstring 一句注明；清理方式 `rm -rf dist` | S2 |
| 8 | `test_missing_declared_source_dir_raises` 改造 vs 新增含糊 | **明确为新增独立用例**（资源目录缺失 → ValueError）；原用例保留原语义（显式 source_dir 缺失 → 报错） | S1 |
| 9 | §1 环境表述易误读 | 已改为「门禁运行时=3.12；单测矩阵=3.10–3.12（tomli 条件依赖兜底）」 | §1 已修 |

## 5. 测试策略（新增/修改清单）

**tests/unit/scripts/test_check_wheel_assets.py**

helper：`_write_wheel`（现有）、`_write_sdist(path, prefix, members)`、`_config(source_dir, **kw)`（构造 GuardConfig）

现有 11 条 → 改造后映射（v2 表）：

| 现有测试 | 改造后 |
|----------|--------|
| test_all_resources_packaged | 注入 GuardConfig + dist 配 sdist fixture（双产物） |
| test_missing_resource_is_reported | 同上 |
| test_dotfiles_are_exempt | wheel 与 sdist 双断言 `.gitkeep` 豁免 |
| test_every_wheel_is_checked | 多 wheel + sdist fixture（遍历语义不变） |
| test_missing_dist_dir_raises | 不变 |
| test_dist_without_wheel_raises | 不变（缺 wheel 仍报错）；**新增对称用例** test_dist_without_sdist_raises |
| test_missing_declared_source_dir_raises | 保留 + 派生期存在性校验新用例（资源目录缺失） |
| test_stale_wheel_member_is_reported | 保留（REQ-02b 方向 ③） |
| test_wheel_subdir_members_are_ignored | 保留 |
| TestMainExitCodes ×3 | 不变（新增的 ValueError/FileNotFoundError 路径已含） |

新增（~20 条）：
- REQ-01：真实 pyproject 派生 → `((jcia/reports/templates, "jcia/reports/templates/"),)`；
  多键/多值合并；fail-closed ×5（通配键/非法 pattern/空 values/空集/目录缺失）；
  loader 三态 ×3（常态/回退态/双缺态）
- REQ-02：stale `jcia/foo.py` 报错；合法 `.py` 不误报；`dist-info` 不参与；白名单豁免；
  路径安全负向（`../` 成员报错）；包根派生 fail-closed（子包 pattern/exclude 祖先重叠/
  目录不存在/空集/find 缺失回退 packages/回退项含 `*`）
- REQ-06：sdist 缺资源报错（消息含 sdist 名）；仅 `.gitkeep` 通过；前缀不匹配
  ValueError（消息含候选与 top-level）；候选集派生单测（name 含 `-`/`_`）；sdist 内
  `.py` 不参与反向；`./` 前缀 fixture
- D6：dist 无 sdist → FileNotFoundError（对称）

**tests/unit/adapters/test_tools/test_source_code_call_graph_adapter.py**
- +4：`""` → []；`"com.example."` → []；`"   "` → []；`"com.example.Outer$Inner"` → [] 且不抛

**覆盖率**：scripts/ 不在 cov 门槛（cov 仅 jcia）；守卫新逻辑全部经直接单测覆盖；
adapter 覆盖率保持。

## 6. 实施顺序（TDD，6 slices）

| Slice | 内容 | REQ | 验证 |
|-------|------|-----|------|
| S1 | 守卫派生（含资源目录存在性、exclude 三重规则、sdist 候选集）+ 三态 loader + fail-closed + pyproject dev 依赖 | REQ-01 | pytest 脚本测试子集全绿 |
| S2 | sdist 正向 + 候选前缀匹配 + `./` 剥离 + 诊断；性能提循环外；点文件注释 | REQ-06/04/05 | 同上 |
| S3 | clean 步骤 + `.py` 对账（路径安全 + 单向声明）+ docstring 边界 | REQ-02 | 同上 |
| S4 | find_test_classes 契约 + 边界 + 4 测试 | REQ-03/07 | adapter 测试全绿 |
| S5 | CHANGELOG（含 D6 条目）+ CONTRIBUTING | REQ-08 | 人工核查格式 |
| S6 | 全链路验证 | — | 见 §8 |

每 slice 遵守 RED→GREEN→REFACTOR；slice 完成后跑
`pytest tests/unit/scripts tests/unit/adapters/test_tools -q` 无回归。

## 7. CHANGELOG 草案 v2（BUILD 定稿）

```markdown
### Added
- 资源守卫改为从 pyproject `[tool.setuptools.package-data]` 自动派生（消除双源维护，#23-REQ-01）
- 守卫新增 sdist 资源断言与「源码树不存在的包内 .py」反查（#23-REQ-02/REQ-06）
- CONTRIBUTING PR 检查清单新增公开 API 变更记录项（#23-REQ-08）

### Changed
- 守卫要求 dist 同时包含 wheel 与 sdist（solo-wheel 构建将 fail-closed；发布用
  `python -m build` 全量构建不受影响）（#23-REQ-06）
- **公开 API 行为变更**：修复 find_test_classes 对空字符串输入返回虚假匹配的问题
  （现返回 []；该方法当前无生产调用方）（#23-REQ-07）
- release.yml 构建前清理 build/ 与 *.egg-info（消除 setuptools 增量缓存污染，#23-REQ-02）
- dev 依赖新增 tomli 条件依赖（<3.11 守卫 TOML 回退，#23-REQ-01）
```

## 8. 验证计划 v2（Phase 4 复用）

1. `pytest tests/unit -v --cov=jcia --cov-fail-under=80`（本地 3.12 全量）
2. 真实链路：`python -m build`（双产物）→ `python scripts/check_wheel_assets.py`
   （对真实 dist 期望 OK）；负向实测定稿：对 fixture dist 删除 1 个资源文件后断言
   守卫报错（不触碰真实 dist）
3. `ruff check` + `ruff format --check`（两守卫文件 + 全仓）；`pyright jcia tests`；
   `lint-imports`
4. F15 复核：`git ls-files "jcia/**/*.py"` 确认无生成物；3.10 分支由 CI 矩阵覆盖
   （本地以 sys.modules 模拟）
5. 生成的 `requirements-reviewed.json` / `design-reviewed.json` 已就位（R1/R2 门禁）

## 9. 风险与回滚

| 风险 | 缓解 |
|------|------|
| 守卫变严（dist 必须含 sdist）影响本地 solo-wheel 构建 | D6 显式化：docstring 用法 `python -m build`；错误消息含修复提示；CHANGELOG 记录 |
| `.py` 对账未来对生成文件误报 | 白名单常量 + docstring 政策；当前无生成物（F15 复核） |
| sdist 前缀与项目名归一化差异 | 候选集（原值/PEP503/下划线）容忍 + 诊断打印候选与实测 top-level |
| 3.10 回退路径真机差异 | CI 3.10 作业覆盖 + 本地 sys.modules 模拟测试 |
| 回滚 | 守卫为单文件 release 门禁；如需回退可 revert 该文件与其测试，无数据迁移 |

## 10. 非目标（v2 显式记录）

- 清理陈旧 `dist/` 产物（twine 上传期冲突可见，非静默；超出本 issue 范围）
- `scripts/check_dist_placeholders.py` 与守卫的合并重构
- 动态版本（setuptools-scm）支持（docstring 声明的支持边界）
