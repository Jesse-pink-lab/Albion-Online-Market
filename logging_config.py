from __future__ import annotations

import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler

from platformdirs import user_log_dir

_LOG_CONFIGURED = False

FORMAT = (
    "%(asctime)s | %(levelname)s | %(name)s | pid=%(process)d tid=%(threadName)s | %(message)s"
)


def _log_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        path = base / "AlbionTradeOptimizer" / "logs"
    else:
        path = Path(user_log_dir("AlbionTradeOptimizer"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_logger(name: str) -> logging.Logger:
    """Return a logger configured for the application."""
    global _LOG_CONFIGURED
    if not _LOG_CONFIGURED:
        log_dir = _log_dir()
        file_handler = RotatingFileHandler(
            log_dir / "app.log", maxBytes=2 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(FORMAT))

        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(logging.Formatter(FORMAT))

        root = logging.getLogger()
        root.setLevel(logging.DEBUG)
        root.addHandler(file_handler)
        root.addHandler(stream_handler)
        root.info("Log file: %s", file_handler.baseFilename)
        _LOG_CONFIGURED = True
    return logging.getLogger(name)
