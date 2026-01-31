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
