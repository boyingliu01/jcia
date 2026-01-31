"""SQLite 数据库适配器实现."""

import sqlite3
from typing import Any


class SQLiteAdapter:
    """SQLite 数据库适配器.

    实现 TestRunRepository, TestResultRepository, TestDiffRepository 接口。
    """

    def __init__(self, db_path: str) -> None:
        """初始化适配器.

        Args:
            db_path: 数据库文件路径
        """
        self._db_path = db_path
        self._connection: sqlite3.Connection | None = None

    @property
    def adapter_name(self) -> str:
        """返回适配器名称."""
        return "sqlite"

    def connect(self) -> None:
        """连接到数据库."""
        if self._connection is None:
            self._connection = sqlite3.connect(self._db_path)
            self._create_tables()

    def disconnect(self) -> None:
        """断开数据库连接."""
        if self._connection:
            self._connection.close()
            self._connection = None

    def is_connected(self) -> bool:
        """检查是否已连接."""
        return self._connection is not None

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
        """执行 SQL 查询.

        Args:
            query: SQL 查询语句
            params: 查询参数

        Returns:
            List[tuple]: 查询结果
        """
        if self._connection is None:
            raise RuntimeError("Database not connected")
        cursor = self._connection.cursor()
        cursor.execute(query, params)
        result = cursor.fetchall()
        cursor.close()
        return result

    def _create_tables(self) -> None:
        """创建数据库表."""
        self.execute("""
            CREATE TABLE IF NOT EXISTS test_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                commit_hash TEXT NOT NULL,
                run_type TEXT NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                status TEXT NOT NULL,
                total_tests INTEGER DEFAULT 0,
                passed_tests INTEGER DEFAULT 0,
                failed_tests INTEGER DEFAULT 0
            )
        """)
        self.execute("""
            CREATE TABLE IF NOT EXISTS test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                test_class TEXT NOT NULL,
                test_method TEXT NOT NULL,
                status TEXT NOT NULL,
                duration_ms INTEGER DEFAULT 0,
                error_message TEXT,
                FOREIGN KEY (run_id) REFERENCES test_runs (id)
            )
        """)
        self.execute("""
            CREATE TABLE IF NOT EXISTS test_diffs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                baseline_run_id INTEGER NOT NULL,
                regression_run_id INTEGER NOT NULL,
                test_class TEXT NOT NULL,
                test_method TEXT NOT NULL,
                baseline_status TEXT NOT NULL,
                regression_status TEXT NOT NULL,
                FOREIGN KEY (baseline_run_id) REFERENCES test_runs (id),
                FOREIGN KEY (regression_run_id) REFERENCES test_runs (id)
            )
        """)
