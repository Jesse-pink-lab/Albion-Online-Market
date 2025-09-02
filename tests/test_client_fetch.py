import pytest
from pathlib import Path

from services.albion_client_fetch import download_client


class DummyResp:
    def __init__(self, data: bytes):
        self.content = data

    def raise_for_status(self) -> None:
        pass


def test_download_client_valid(monkeypatch, tmp_path):
    dest = tmp_path / "client.exe"

    def fake_get(url, timeout, headers):
        return DummyResp(b"data")

    monkeypatch.setattr("services.albion_client_fetch.requests.get", fake_get)
    monkeypatch.setattr(
        "utils.pecheck.is_valid_win64_exe", lambda p: (True, "ok")
    )

    download_client(dest)
    assert dest.exists()


def test_download_client_invalid(monkeypatch, tmp_path):
    dest = tmp_path / "client.exe"

    def fake_get(url, timeout, headers):
        return DummyResp(b"data")

    monkeypatch.setattr("services.albion_client_fetch.requests.get", fake_get)
    monkeypatch.setattr(
        "utils.pecheck.is_valid_win64_exe", lambda p: (False, "bad")
    )

    with pytest.raises(RuntimeError):
        download_client(dest)
