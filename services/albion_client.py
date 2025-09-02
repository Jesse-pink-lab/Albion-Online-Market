from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional, Sequence

from logging_config import get_logger
from utils.pecheck import is_valid_win64_exe
from .albion_client_fetch import download_client

log = get_logger(__name__)

DEFAULT_PROG_FILES = r"C:\Program Files\Albion Data Client\albiondata-client.exe"
APPDATA_BIN = Path(os.environ.get("APPDATA", "")) / "AlbionTradeOptimizer" / "bin"
MANAGED_CLIENT = APPDATA_BIN / "albiondata-client.exe"
EMBEDDED_REL = Path("resources/windows/albiondata-client.exe")


def managed_client_path() -> str:
    return str(MANAGED_CLIENT)


def _candidate_info(path: Path) -> tuple[bool, int]:
    exists = path.is_file()
    size = path.stat().st_size if exists else 0
    return exists, size


def _embedded_client_path() -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base / EMBEDDED_REL


def _log_candidate(path: Path) -> tuple[bool, str]:
    exists, size = _candidate_info(path)
    if exists:
        valid, reason = is_valid_win64_exe(str(path))
    else:
        valid, reason = False, "file does not exist"
    log.info(
        "Albion client candidate: %s -> valid=%s (%s) size=%s",
        path,
        valid,
        reason,
        size,
    )
    return valid, reason


def ensure_managed_from_embedded() -> str:
    emb = _embedded_client_path()
    valid, reason = _log_candidate(emb)
    if not valid:
        raise RuntimeError(f"Embedded albiondata-client.exe invalid: {reason}")
    APPDATA_BIN.mkdir(parents=True, exist_ok=True)
    shutil.copy2(emb, MANAGED_CLIENT)
    log.info("Copied embedded Albion client from %s to %s", emb, MANAGED_CLIENT)
    return str(MANAGED_CLIENT)


def find_client(
    user_override: Optional[str],
    project_dir: Optional[str] = None,
    ask_download: Optional[Callable[[], bool]] = None,
) -> Optional[str]:
    candidates = []
    if user_override:
        candidates.append(Path(user_override))
    candidates.append(MANAGED_CLIENT)
    candidates.append(Path(DEFAULT_PROG_FILES))

    for cand in candidates:
        valid, _ = _log_candidate(cand)
        if valid:
            return str(cand)

    emb = _embedded_client_path()
    valid, _ = _log_candidate(emb)
    if valid:
        try:
            return ensure_managed_from_embedded()
        except Exception as exc:  # pragma: no cover - copy failure
            log.error("Failed to copy embedded client: %s", exc)

    if ask_download and ask_download():
        try:
            download_client(MANAGED_CLIENT)
            return str(MANAGED_CLIENT)
        except Exception as exc:  # pragma: no cover - network issues
            log.error("Download failed: %s", exc)
    return None


def launch_client(client_path: str, args: Sequence[str] = ()) -> subprocess.Popen:
    valid, reason = is_valid_win64_exe(client_path)
    if not valid:
        raise RuntimeError(f"Invalid albiondata-client.exe at {client_path}: {reason}")
    cmd = [client_path, *args]
    log.info("Launching albiondata-client: %s", cmd)
    try:
        proc = subprocess.Popen(cmd, close_fds=True)
        log.info("Started PID=%s", proc.pid)
        return proc
    except OSError as exc:  # pragma: no cover - hard to trigger
        if getattr(exc, "winerror", None) == 216:
            msg = (
                "Windows cannot run this albiondata-client.exe (WinError 216). "
                "Install the official 64-bit Windows build and set its path in Settings."
            )
            log.error(msg)
            raise RuntimeError(msg) from exc
        log.exception("Failed to launch albiondata-client: %s", exc)
        raise


def capture_subproc_version(client_path: str, timeout: float = 3.0) -> None:
    try:
        res = subprocess.run(
            [client_path, "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            text=True,
            close_fds=True,
        )
        log.debug(
            "albiondata-client --version rc=%s stdout=%r stderr=%r",
            res.returncode,
            res.stdout.strip(),
            res.stderr.strip(),
        )
    except Exception as exc:  # pragma: no cover - diagnostic only
        log.debug("Failed to capture albiondata-client version: %s", exc)
