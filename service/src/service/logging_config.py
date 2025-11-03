"""Logging configuration for Text2SQL service."""

import sys
from pathlib import Path

from loguru import logger


def configure_logging(log_level: str = "INFO", enable_file_logging: bool = False):
    """
    Configure loguru for the Text2SQL service.

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR)
        enable_file_logging: Whether to enable file logging
    """
    logger.remove()

    logger.add(
        sys.stdout,
        format="<cyan>{time:YYYY-MM-DD HH:mm:ss.SSS}</cyan> | <level>{level: <8}</level> | <white>{name}:{function}:{line} - {message}</white>",
        level=log_level,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    if enable_file_logging:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        # All logs
        logger.add(
            "logs/text2sql_{time:YYYY-MM-DD}.log",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            level="DEBUG",
            rotation="500 MB",
            retention="30 days",
            compression="zip",
            backtrace=True,
            diagnose=True,
        )

        logger.add(
            "logs/errors_{time:YYYY-MM-DD}.log",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            level="ERROR",
            rotation="100 MB",
            retention="90 days",
            compression="zip",
            backtrace=True,
            diagnose=True,
        )

        logger.info(f"File logging enabled. Logs directory: {log_dir.absolute()}")


configure_logging(log_level="INFO", enable_file_logging=False)
