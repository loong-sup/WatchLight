# 文件说明：本文件属于 基础设施层。
# 主要职责：实现 logging 相关能力。
# 阅读提示：提供日志、路径、错误等基础能力。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Structured logging setup using structlog."""

import logging
import sys
from typing import Any

import structlog


def setup_logging(level: str = "info", json_format: bool = True) -> None:
    """Configure structlog with JSON or console output."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )


def get_logger(subsystem: str) -> Any:
    """Get a logger bound to a subsystem name."""
    return structlog.get_logger(subsystem=subsystem)
