# TASK-021 性能基准对比记录（远程调用集成前后）

- **状态**: ✅ 完成
- **执行日期**: 2026-09-22
- **测试对象**: `jenkins/`（与历史基线完全相同的规模口径：5 commits / 23 files / 1887 java files / 2347 classes / 181513 methods，四期运行完全一致）
- **测试脚本**: `tests/performance/benchmark_impact_analysis.py`
- **本次证据**: `benchmark_report_20260922_210642.json` / `.txt`（干净跑）

---

## 1. 结论

1. **无性能回归**。与集成前（2026-02-22，两次基线）对比，干净环境下所有可比项均处于历史波动区间或明显更优；总计 **88.3s**，低于两次历史基线的 107.0s / 145.8s。
2. **基准方法学缺陷已确认**：脚本为单次采样、无负载隔离，对本机并发负载极敏感——同一操作在同机实测波动 1.2s ~ 107.9s（≈88×）。跨期对比只作量级参考，不宜作精细回归判定。
3. **一次污染跑已废弃**：20:55 跑（三项 CRITICAL）为并发负载下的失真数据，其报告已删除，不作为任何结论依据。

---

## 2. 对比数据（同机、同仓库、同规模指标）

| 操作 | 02-22 #1 (15:06) | 02-22 #2 (15:46) | 09-22 污染跑 (20:55，废) | 09-22 干净跑 (21:06) |
|------|-----------------|-----------------|------------------------|---------------------|
| git_analysis | 16,674 ms | 24,226 ms | 107,912 ms | **1,226 ms** |
| call_chain_analysis | 29,962 ms | 43,865 ms | 80,995 ms | **36,542 ms** |
| full_analysis | 47,595 ms | 64,922 ms | 120,492 ms | **37,772 ms** |
| **总计** | **106,984 ms** | **145,765 ms** | 322,181 ms | **88,291 ms** |

- 规模指标四期完全一致（见文件头），说明 jenkins 仓库与输入范围未变。
- 瓶颈分级：污染跑 3 项 CRITICAL → 干净跑 2 项 HIGH（无 CRITICAL）。
- 干净跑与历史最快的 #1 比：git 约 13.6× 更快、full 约 1.26× 更快；call_chain 36.5s 位于历史两次（30.0s / 43.9s）的波动带内。

## 3. 污染跑废弃过程（可复现）

| 步骤 | 结果 |
|------|------|
| 20:55 跑 | git_analysis 107,912 ms，较历史基线 +345%，三项 CRITICAL |
| 探针 1（提交枚举分解） | `Git()` init 0.01s / commit 解析 0.28s / is_ancestor 0.17s / iter_commits 0.16s，合计 ≈0.6s |
| 探针 2（同基准调用路径） | `PyDrillerAdapter.analyze_commits` 实测 **1.57s**（files=23 / methods=6，与基准报告数字一字不差） |
| 根因 | pydriller 2.11 为全 lazy 架构（`Commit.modified_files`、`ModifiedFile.changed_methods` 在属性访问时才计算 diff / lizard 解析），对 CPU 抢占尤其敏感；后台执行期间与其它重负载叠加导致膨胀 |
| 21:06 干净重跑 | git_analysis 1,225.7 ms，全项恢复正常 |
| 处置 | `benchmark_report_20260922_205544.json/.txt` 已删除；探针脚本已删除（build/ 下，均为临时产物） |

## 4. 附注：排查中发现的两项非性能观察（未修复，供后续跟进）

### 4.1 methods_changed 8 → 6（依赖版本漂移，非本项目代码变更引入）

- **现象**：2026-02 两次基线均为 8，2026-09 两次均为 6（files_changed=23 恒定）。
- **对照实验**：同一 pydriller 2.11 下，旧路径（`Repository.traverse_commits`）与新路径（GitPython range + `get_commit_from_gitpython`）识别出的 Java 方法位点一致（均为 6 个：ViewTest.java 5 + MyViewTest.java 1）；且 2026-02 时点的 adapter 实现（`d867a8d`）同样只对 Java 文件提取方法。
- **归因（推断）**：`pydriller>=2.6.0` 未 pin 版本，2.6→2.11 升级中 lizard 对内部类方法位点的识别口径变化。
- **影响**：方法计数口径变化，仅影响影响面统计展示；文件级变更集（23）不变。
- **建议**：视需要 pin 依赖版本，或在文档中显式记录口径基线。

### 4.2 内部类方法全限定名畸形（既有解析缺陷）

- **现象**：`ViewTest.java` 内部类 `BrokenView` 的方法产出 `.BrokenView::Issue( "SECURITY-2171")` 形式——`class_name` 为空、`method_name` 含 `::` 嵌套段。
- **成因**：lizard 对 Java 内部类方法给出 `name="BrokenView::Issue"`，`_convert_method_change` 的 `.` 分隔解析逻辑无法处理 `::` 嵌套形态。
- **影响**：`ChangeSet.changed_methods` 中此类名称无法与调用图的全限定名（`hudson.model.ViewTest.BrokenView.Issue`）匹配；当前主链路（`analyze_impact.py` / CLI）仅消费其**计数**，故现无实际功能损失；若未来下游按名匹配（test selection / 影响传播）会漏配。
- **建议**：作为独立缺陷评估修复（可转 issue 跟进），修复时按 TDD 先固化 `::` 嵌套类用例。

## 5. 建议（非阻塞）

1. **基准脚本健壮化**：重复采样（≥3 次取中位数）+ 结果离散度输出 + 采样前负载预检（如 CPU 空闲率），否则不可纳入 CI 作回归门。
2. **call_chain_analysis 仍是最大单项成本**（干净跑 36.5s，占 41%）：javalang 单线程解析 1386 个源文件的固有成本，可作独立优化项评估（并行解析 / 增量缓存，历史报告 §4.5 亦提及）。
