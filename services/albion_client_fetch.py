from __future__ import annotations

import os
import tempfile
from pathlib import Path

import requests

from logging_config import get_logger
from utils.pecheck import is_valid_win64_exe

log = get_logger(__name__)

DOWNLOAD_URL = (
    "https://github.com/ao-data/albiondata-client/releases/latest/download/albiondata-client.exe"
)


def safe_atomic_write(dest: Path, data: bytes) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(dest.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, dest)
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass


def validate_or_raise(path: Path) -> None:
    valid, reason = is_valid_win64_exe(str(path))
    if not valid:
        raise RuntimeError(f"invalid albiondata-client.exe: {reason}")


def download_client(dest_path: Path, url: str = DOWNLOAD_URL) -> Path:
    headers = {"User-Agent": "AlbionTradeOptimizer/1.0"}
    log.info("Downloading Albion Data Client from %s", url)
    resp = requests.get(url, timeout=30, headers=headers)
    resp.raise_for_status()
    safe_atomic_write(dest_path, resp.content)
    size = dest_path.stat().st_size
    log.info("Downloaded %s bytes to %s", size, dest_path)
    validate_or_raise(dest_path)
    return dest_path
