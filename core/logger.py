"""Logging configuration using Rich."""

import io
import logging
import os
import sys
from rich.logging import RichHandler
from rich.console import Console


def _make_utf8_console() -> Console:
    """Create a Rich Console that works on Windows terminals with cp1252."""
    try:
        # Try wrapping stdout in a UTF-8 text wrapper so Rich can emit emoji
        wrapper = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
        )
        return Console(file=wrapper, force_terminal=True)
    except Exception:
        # Fallback: plain console, no colours / emoji on very old terminals
        return Console(force_terminal=False)


def setup_logger(name: str, log_file: str = 'logs/prospector.log') -> logging.Logger:
    """Setup and return a structured logger with console and file handlers."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        # File handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)

        # Console handler with Rich (UTF-8 safe)
        console = _make_utf8_console()
        rich_handler = RichHandler(console=console, rich_tracebacks=True)
        rich_handler.setLevel(logging.INFO)
        rich_formatter = logging.Formatter('%(message)s')
        rich_handler.setFormatter(rich_formatter)

        logger.addHandler(file_handler)
        logger.addHandler(rich_handler)

    return logger
