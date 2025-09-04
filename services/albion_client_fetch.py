from __future__ import annotations

import gzip
import io
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Iterable, Optional, Callable

import requests
from services.netlimit import bucket
from services.market_prices import _on_result

from logging_config import get_logger
from utils.pecheck import is_valid_win64_exe

log = get_logger(__name__)

GITHUB_API_LATEST = "https://api.github.com/repos/ao-data/albiondata-client/releases/latest"
DEFAULT_PROG_FILES = (
    Path(os.environ.get("ProgramFiles", r"C:\\Program Files"))
    / "Albion Data Client"
    / "albiondata-client.exe"
)


class FetchError(RuntimeError):
    pass


def _pick_windows_asset(assets: Iterable[dict[str, Any]], prefer_installer: bool) -> Optional[dict[str, Any]]:
    def match(predicate):
        for asset in assets:
            name = asset.get("name", "").lower()
            if predicate(name):
                return asset
        return None

    order: list[Callable[[str], bool]]
    if prefer_installer:
        order = [
            lambda n: n.endswith("installer.exe"),
            lambda n: n.endswith("update-windows-amd64.exe.gz"),
        ]
    else:
        order = [
            lambda n: n.endswith("update-windows-amd64.exe.gz"),
            lambda n: n.endswith("installer.exe"),
        ]
    for pred in order:
        asset = match(pred)
        if asset:
            return asset
    return match(lambda n: "windows" in n and "amd64" in n and n.endswith(".zip"))


def _gunzip_bytes_to_file(data: bytes, dest_exe_path: str) -> None:
    dest = Path(dest_exe_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with gzip.GzipFile(fileobj=io.BytesIO(data)) as gz:
        extracted = gz.read()
    with open(dest, "wb") as f:
        f.write(extracted)
        f.flush()
        os.fsync(f.fileno())


def _save_bytes(data: bytes, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


def fetch_latest_windows_client(dest_exe_path: str, prefer_installer: bool = False) -> str:
    dest = Path(dest_exe_path)
    try:
        log.info("Fetching latest Albion Data Client release info")
        bucket.acquire()
        resp = requests.get(GITHUB_API_LATEST, timeout=30)
        _on_result(getattr(resp, "status_code", 200))
        resp.raise_for_status()
        release = resp.json()
    except (requests.exceptions.RequestException, json.JSONDecodeError) as exc:
        log.exception("Failed to query GitHub releases: %s", exc)
        raise FetchError("Failed to query GitHub releases") from exc

    asset = _pick_windows_asset(release.get("assets", []), prefer_installer)
    if not asset:
        raise FetchError("No Windows asset found in latest release")

    name = asset.get("name", "")
    url = asset.get("browser_download_url")
    log.info("Chosen asset %s (%s)", name, url)

    try:
        bucket.acquire()
        dl_resp = requests.get(url, timeout=60)
        _on_result(getattr(dl_resp, "status_code", 200))
        dl_resp.raise_for_status()
        data = dl_resp.content
    except requests.exceptions.RequestException as exc:
        log.exception("Failed to download asset: %s", exc)
        raise FetchError("Failed to download Albion Data Client") from exc

    if name.endswith(".exe.gz"):
        log.info("Decompressing gzip asset %s", name)
        _gunzip_bytes_to_file(data, dest_exe_path)
    elif name.endswith("installer.exe"):
        tmp_dir = Path(tempfile.mkdtemp())
        installer_path = tmp_dir / name
        _save_bytes(data, installer_path)
        log.info("Running installer %s", installer_path)
        try:
            subprocess.run([str(installer_path), "/S"], check=True)
        except subprocess.CalledProcessError as exc:
            log.warning("Silent installer run failed: %s", exc)
            if prefer_installer:
                shutil.rmtree(tmp_dir, ignore_errors=True)
                log.info("Falling back to portable download")
                return fetch_latest_windows_client(dest_exe_path, prefer_installer=False)
            raise FetchError("Failed to execute installer") from exc
        try:
            shutil.copy2(DEFAULT_PROG_FILES, dest)
        except OSError as exc:
            log.exception("Installer did not produce expected exe: %s", exc)
            raise FetchError("Installer did not produce expected exe") from exc
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
    elif name.endswith(".zip"):
        log.info("Extracting zip asset %s", name)
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            exe_name = next((n for n in zf.namelist() if n.lower().endswith(".exe")), None)
            if not exe_name:
                raise FetchError("Zip asset missing exe")
            zf.extract(exe_name, dest.parent)
            os.replace(dest.parent / exe_name, dest)
    else:
        raise FetchError(f"Unsupported asset type: {name}")

    ok, reason = is_valid_win64_exe(str(dest))
    log.info("Downloaded client validation: %s (%s)", ok, reason)
    if not ok:
        raise FetchError(f"Downloaded client invalid: {reason}")
    size = dest.stat().st_size
    log.info("Albion client ready at %s size=%s", dest, size)
    return str(dest)
