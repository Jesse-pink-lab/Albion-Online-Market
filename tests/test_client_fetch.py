import gzip
import io
from pathlib import Path

import pytest
import requests

from services import albion_client_fetch as fetcher


class DummyResp:
    def __init__(self, data=None, json_data=None):
        self.content = data
        self._json = json_data

    def raise_for_status(self):
        pass

    def json(self):
        return self._json


def _compress(data: bytes) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
        gz.write(data)
    return buf.getvalue()


def test_pick_installer(monkeypatch, tmp_path):
    assets = [
        {"name": "albiondata-client-amd64-installer.exe", "browser_download_url": "u"}
    ]
    resp_release = DummyResp(json_data={"assets": assets})
    resp_dl = DummyResp(data=b"installer")
    calls = []

    def fake_get(url, timeout):
        calls.append(url)
        return resp_dl if url == "u" else resp_release

    monkeypatch.setattr(fetcher.requests, "get", fake_get)
    monkeypatch.setattr(fetcher, "DEFAULT_PROG_FILES", tmp_path / "pf" / "albiondata-client.exe")
    fetcher.DEFAULT_PROG_FILES.parent.mkdir(parents=True)
    fetcher.DEFAULT_PROG_FILES.write_bytes(b"exe")
    monkeypatch.setattr(fetcher.subprocess, "run", lambda *a, **k: None)
    monkeypatch.setattr(fetcher, "is_valid_win64_exe", lambda p: (True, "ok"))

    dest = tmp_path / "dest.exe"
    assert (
        fetcher.fetch_latest_windows_client(str(dest), prefer_installer=True)
        == str(dest)
    )
    assert dest.read_bytes() == b"exe"
    assert calls == [fetcher.GITHUB_API_LATEST, "u"]


def test_pick_gz(monkeypatch, tmp_path):
    data = _compress(b"exe")
    assets = [
        {"name": "update-windows-amd64.exe.gz", "browser_download_url": "u"}
    ]
    resp_release = DummyResp(json_data={"assets": assets})
    resp_dl = DummyResp(data=data)

    def fake_get(url, timeout):
        return resp_dl if url == "u" else resp_release

    monkeypatch.setattr(fetcher.requests, "get", fake_get)
    monkeypatch.setattr(fetcher, "is_valid_win64_exe", lambda p: (True, "ok"))

    dest = tmp_path / "dest.exe"
    fetcher.fetch_latest_windows_client(str(dest))
    assert dest.read_bytes() == b"exe"


def test_no_windows_asset(monkeypatch):
    resp_release = DummyResp(json_data={"assets": []})
    monkeypatch.setattr(fetcher.requests, "get", lambda u, timeout: resp_release)
    with pytest.raises(fetcher.FetchError):
        fetcher.fetch_latest_windows_client("x")


def test_download_error(monkeypatch):
    def fake_get(url, timeout):
        raise requests.Timeout("boom")

    monkeypatch.setattr(fetcher.requests, "get", fake_get)
    with pytest.raises(fetcher.FetchError):
        fetcher.fetch_latest_windows_client("x")
