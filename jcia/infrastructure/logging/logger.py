"""应用日志封装."""

from __future__ import annotations

import logging
import sys
from typing import IO


class AppLogger:
    """集中管理应用 Logger，避免重复配置."""

    _configured: set[str] = set()

    @classmethod
    def get_logger(
        cls,
        name: str = "jcia",
        level: int = logging.INFO,
        stream: IO[str] | None = None,
    ) -> logging.Logger:
        """获取配置好的 logger，确保单例和无重复 handler.

        Args:
            name: logger 名称
            level: 日志级别
            stream: 可选输出流，默认 stdout

        Returns:
            logging.Logger: 已配置的 logger 实例
        """

        logger = logging.getLogger(name)
        if name not in cls._configured:
            logger.setLevel(level)
            logger.propagate = False

            handler_stream: IO[str] = stream if stream is not None else sys.stdout
            handler = logging.StreamHandler(handler_stream)
            handler.setLevel(level)
            handler.setFormatter(
                logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
            )
            logger.addHandler(handler)

            cls._configured.add(name)
        return logger

    @classmethod
    def reset(cls) -> None:
        """仅用于测试，清理已配置的 logger."""

        for name in list(cls._configured):
            logger = logging.getLogger(name)
            logger.handlers.clear()
            cls._configured.discard(name)
