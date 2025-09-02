from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional, Sequence

from logging_config import get_logger
from utils.pecheck import is_valid_win64_exe

log = get_logger(__name__)

DEFAULT_PROG_FILES = r"C:\Program Files\Albion Data Client\albiondata-client.exe"


def _candidate_info(path: str) -> tuple[bool, int]:
    exists = os.path.isfile(path)
    size = os.path.getsize(path) if exists else 0
    return exists, size


def find_client(user_override: Optional[str], project_dir: Optional[str]) -> Optional[str]:
    """Find a valid albiondata-client executable.

    Candidates are checked in order: ``user_override`` -> ``DEFAULT_PROG_FILES`` ->
    ``<project_dir>\\bin\\albiondata-client.exe``.  Each candidate is validated
    with :func:`is_valid_win64_exe` and the outcome is logged.  The first valid
    path is returned or ``None`` if none validate.
    """
    candidates = []
    if user_override:
        candidates.append(user_override)
    candidates.append(DEFAULT_PROG_FILES)
    if project_dir:
        candidates.append(str(Path(project_dir) / "bin" / "albiondata-client.exe"))

    for cand in candidates:
        exists, size = _candidate_info(cand)
        if exists:
            valid, reason = is_valid_win64_exe(cand)
        else:
            valid, reason = False, "file does not exist"
        log.info(
            "Albion client candidate: %s -> valid=%s (%s) size=%s",
            cand,
            valid,
            reason,
            size,
        )
        if valid:
            return cand
    return None


def launch_client(client_path: str, args: Sequence[str] = ()) -> subprocess.Popen:
    """Validate and launch the albiondata-client executable.

    :raises RuntimeError: if WinError 216 occurs or validation fails.
    """
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
    """Best-effort capture of ``--version`` output from the subprocess."""
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
