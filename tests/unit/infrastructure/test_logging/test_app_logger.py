"""AppLogger 日志封装单元测试."""

from __future__ import annotations

import logging
from io import StringIO

from jcia.infrastructure.logging.logger import AppLogger


class TestAppLogger:
    """AppLogger 行为测试."""

    def test_get_logger_is_singleton_and_no_duplicate_handlers(self) -> None:
        """同名 logger 应复用且不重复添加 handler."""
        logger1 = AppLogger.get_logger("jcia-test", level=logging.DEBUG)
        logger2 = AppLogger.get_logger("jcia-test", level=logging.DEBUG)

        assert logger1 is logger2
        assert len(logger1.handlers) == 1

    def test_default_level_and_propagation(self) -> None:
        """默认等级应为 INFO 且不向上冒泡."""
        logger = AppLogger.get_logger("jcia-default")

        assert logger.level == logging.INFO
        assert logger.propagate is False

    def test_log_output_written_to_stream(self) -> None:
        """输出应写入提供的流."""
        stream = StringIO()
        logger = AppLogger.get_logger("jcia-stream", stream=stream)

        logger.info("hello world")

        contents = stream.getvalue()
        assert "hello world" in contents
        assert len(logger.handlers) == 1
