from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional, Sequence

from logging_config import get_logger
from utils.pecheck import is_valid_win64_exe
from .albion_client_fetch import fetch_latest_windows_client

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
            fetch_latest_windows_client(str(MANAGED_CLIENT), prefer_installer=False)
            valid, _ = _log_candidate(MANAGED_CLIENT)
            if valid:
                return str(MANAGED_CLIENT)
        except Exception as exc:  # pragma: no cover - network issues
            log.error("Download failed: %s", exc)
    return None


def _probe_version(client_path: str) -> None:
    """Best-effort version probe."""
    try:
        subprocess.run(
            [client_path, "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=5,
            check=False,
        )
    except Exception as exc:  # pragma: no cover - diagnostic only
        log.debug("Version probe failed: %r", exc)


def _looks_like_flag_rejection(output: str) -> bool:
    s = output.lower()
    return ("flag provided but not defined" in s) or ("usage of" in s)


def launch_client_with_fallback(
    client_path: str, preferred_flags: Sequence[str] | tuple[str, ...] = ()
) -> subprocess.Popen:
    valid, reason = is_valid_win64_exe(client_path)
    if not valid:
        raise RuntimeError(
            f"Invalid albiondata-client.exe at {client_path}: {reason}"
        )

    _probe_version(client_path)

    def _try(flags: Sequence[str]) -> subprocess.Popen:
        cmd = [client_path, *flags]
        log.info("Launching albiondata-client: %r", cmd)
        try:
            p = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
            )
            try:
                out = p.communicate(timeout=2)[0] or b""
            except subprocess.TimeoutExpired:
                try:
                    p.kill()
                except Exception:
                    pass
                return subprocess.Popen([client_path, *flags], close_fds=True)
            else:
                text = out.decode("utf-8", "replace")
                if p.returncode and _looks_like_flag_rejection(text):
                    log.warning(
                        "Client rejected flags %s; output: %s",
                        list(flags),
                        text.strip(),
                    )
                    raise RuntimeError("Flags rejected")
                if p.returncode == 0 and ("version" in text.lower()):
                    return subprocess.Popen([client_path, *flags], close_fds=True)
                return subprocess.Popen([client_path, *flags], close_fds=True)
        except RuntimeError:
            raise
        except Exception as exc:
            log.error("Initial try failed for flags %s: %r", list(flags), exc)
            raise

    if preferred_flags:
        try:
            proc = _try(preferred_flags)
        except RuntimeError:
            log.info("Retrying with NO flags due to flag rejection")
            proc = _try(())
        except Exception:
            log.info("Retrying with NO flags due to launch error")
            proc = _try(())
    else:
        proc = _try(())

    log.info("Started PID=%s", getattr(proc, "pid", None))
    return proc


def launch_client(client_path: str, args: Sequence[str] = ()) -> subprocess.Popen:
    return launch_client_with_fallback(client_path, args)


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
