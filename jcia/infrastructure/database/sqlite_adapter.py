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

    def execute_write(self, query: str, params: tuple[Any, ...] = ()) -> int:
        """执行写入并返回自增ID.

        Args:
            query: SQL 写入语句
            params: 写入参数

        Returns:
            int: 自增主键ID
        """
        if self._connection is None:
            raise RuntimeError("Database not connected")
        cursor = self._connection.cursor()
        cursor.execute(query, params)
        self._connection.commit()
        row_id = cursor.lastrowid or 0
        cursor.close()
        return int(row_id)

    def execute_non_query(self, query: str, params: tuple[Any, ...] = ()) -> int:
        """执行更新/删除并返回影响行数.

        Args:
            query: SQL 更新/删除语句
            params: 查询参数

        Returns:
            int: 影响行数
        """
        if self._connection is None:
            raise RuntimeError("Database not connected")
        cursor = self._connection.cursor()
        cursor.execute(query, params)
        self._connection.commit()
        affected = cursor.rowcount or 0
        cursor.close()
        return int(affected)

    def _create_tables(self) -> None:
        """创建数据库表."""
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS test_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                commit_hash TEXT NOT NULL,
                commit_message TEXT,
                branch_name TEXT,
                run_type TEXT NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                status TEXT NOT NULL,
                total_tests INTEGER DEFAULT 0,
                passed_tests INTEGER DEFAULT 0,
                failed_tests INTEGER DEFAULT 0,
                skipped_tests INTEGER DEFAULT 0,
                error_tests INTEGER DEFAULT 0,
                total_duration_ms INTEGER DEFAULT 0,
                coverage_json TEXT,
                metadata_json TEXT
            )
        """
        )
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                test_class TEXT NOT NULL,
                test_method TEXT NOT NULL,
                status TEXT NOT NULL,
                duration_ms INTEGER DEFAULT 0,
                error_message TEXT,
                stack_trace TEXT,
                coverage_data_json TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES test_runs (id)
            )
        """
        )
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS test_diffs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                baseline_run_id INTEGER NOT NULL,
                regression_run_id INTEGER NOT NULL,
                test_class TEXT NOT NULL,
                test_method TEXT NOT NULL,
                baseline_status TEXT,
                regression_status TEXT,
                diff_type TEXT NOT NULL DEFAULT "",
                analysis_result TEXT DEFAULT "PENDING",
                analysis_reason TEXT,
                reviewed_by TEXT,
                reviewed_at TIMESTAMP,
                FOREIGN KEY (baseline_run_id) REFERENCES test_runs (id),
                FOREIGN KEY (regression_run_id) REFERENCES test_runs (id)
            )
        """
        )
