"""SQLiteAdapter 单元测试."""

import pytest

from jcia.infrastructure.database.sqlite_adapter import SQLiteAdapter


class TestSQLiteAdapter:
    """SQLiteAdapter 测试类."""

    def test_adapter_name_returns_sqlite(self) -> None:
        """测试适配器名称."""
        # Arrange
        adapter = SQLiteAdapter(":memory:")

        # Act
        name = adapter.adapter_name

        # Assert
        assert name == "sqlite"

    def test_execute_requires_connection(self) -> None:
        """测试未连接时执行查询抛出异常."""
        # Arrange
        adapter = SQLiteAdapter(":memory:")

        # Act & Assert
        with pytest.raises(RuntimeError):
            adapter.execute("SELECT 1")

    def test_connect_creates_tables(self) -> None:
        """测试连接时创建必要表."""
        # Arrange
        adapter = SQLiteAdapter(":memory:")

        # Act
        adapter.connect()
        tables = adapter.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        adapter.disconnect()

        # Assert
        table_names = {row[0] for row in tables}
        assert {"test_diffs", "test_results", "test_runs"}.issubset(table_names)

    def test_disconnect_resets_connection(self) -> None:
        """测试断开连接重置状态."""
        # Arrange
        adapter = SQLiteAdapter(":memory:")

        # Act
        adapter.connect()
        adapter.disconnect()

        # Assert
        assert adapter.is_connected() is False

    def test_execute_write_returns_lastrowid(self) -> None:
        """测试写入返回自增ID."""
        # Arrange
        adapter = SQLiteAdapter(":memory:")
        adapter.connect()

        # Act
        row_id = adapter.execute_write(
            """
            INSERT INTO test_runs (
                commit_hash,
                run_type,
                start_time,
                status,
                total_tests,
                passed_tests,
                failed_tests
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "abc123",
                "baseline",
                "2024-01-01T00:00:00",
                "completed",
                1,
                1,
                0,
            ),
        )
        adapter.disconnect()

        # Assert
        assert row_id == 1

    def test_execute_non_query_returns_rowcount(self) -> None:
        """测试更新/删除返回影响行数."""
        # Arrange
        adapter = SQLiteAdapter(":memory:")
        adapter.connect()
        row_id = adapter.execute_write(
            """
            INSERT INTO test_runs (
                commit_hash,
                run_type,
                start_time,
                status,
                total_tests,
                passed_tests,
                failed_tests
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "abc123",
                "baseline",
                "2024-01-01T00:00:00",
                "pending",
                1,
                1,
                0,
            ),
        )

        # Act
        affected = adapter.execute_non_query(
            "UPDATE test_runs SET status = ? WHERE id = ?",
            ("completed", row_id),
        )
        adapter.disconnect()

        # Assert
        assert affected == 1
