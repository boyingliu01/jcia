# Semantic test review (2026-02-01)

1) Persistence schema drops critical TestRun/TestResult fields.
   - Tables in jcia/infrastructure/database/sqlite_adapter.py:103-148 and writes in sqlite_repository.py:35-168 only store hash/run_type/basic counts.
   - Domain requires commit_message, branch_name, skipped/error counts, duration, coverage, metadata (jcia/core/entities/test_run.py:169-185) and stack_trace/coverage_data/timestamp for results (jcia/core/entities/test_run.py:103-112), but these are neither persisted nor asserted in tests (tests/unit/infrastructure/test_database/test_sqlite_repository.py).
   - Regression reporting and impact analytics will lose data even when entities supply it.

2) Git adapter ignores rename/source path and method-level detail.
   - _convert_file_change in jcia/adapters/git/pydriller_adapter.py:155-171 only maps filename/insertions/deletions; old_path and method_changes remain empty, so rename tracking and method-level impact are lost.
   - Existing tests (tests/unit/adapters/test_git/test_pydriller_adapter.py) only assert counts, so this gap stays hidden.

3) Volcengine adapter mislabels provider and risk semantics.
   - provider returns AIProvider.OPENAI (jcia/adapters/ai/volcengine_adapter.py:63) even though the adapter is for Volcengine, so callers cannot route/configure per vendor; tests enforce the wrong label.
   - _extract_risk_level returns MEDIUM unless the string literally contains HIGH/LOW (lines 454-470), and tests only check the value is in {HIGH,MEDIUM,LOW}; high-risk responses can be silently downgraded.

4) Test-file detection is Unix-only.
   - FileChange.is_test_file uses "/test/" substring only (jcia/core/entities/change_set.py:96-102). On Windows paths like "src\\test\\ServiceTest.java" it returns False, so test selection misses Java tests on the project’s target platform. The test case uses forward slashes and doesn’t expose this.
