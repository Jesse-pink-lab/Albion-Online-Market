from pathlib import Path
import pytest

from services import albion_client


def test_resolution_order(monkeypatch, tmp_path):
    appdata = tmp_path / "AppData" / "AlbionTradeOptimizer" / "bin"
    appdata.mkdir(parents=True)
    managed = appdata / "albiondata-client.exe"
    prog = tmp_path / "Program Files" / "Albion Data Client" / "albiondata-client.exe"
    prog.parent.mkdir(parents=True)
    override = tmp_path / "override.exe"
    for p in (managed, prog, override):
        p.write_text("x")

    monkeypatch.setattr(albion_client, "APPDATA_BIN", appdata)
    monkeypatch.setattr(albion_client, "MANAGED_CLIENT", managed)
    monkeypatch.setattr(albion_client, "DEFAULT_PROG_FILES", str(prog))

    monkeypatch.setattr(
        "services.albion_client.is_valid_win64_exe",
        lambda p: (True, "ok") if p == str(override) else (False, "bad"),
    )
    assert albion_client.find_client(str(override)) == str(override)

    monkeypatch.setattr(
        "services.albion_client.is_valid_win64_exe",
        lambda p: (True, "ok") if p == str(managed) else (False, "bad"),
    )
    assert albion_client.find_client(None) == str(managed)

    monkeypatch.setattr(
        "services.albion_client.is_valid_win64_exe",
        lambda p: (True, "ok") if p == str(prog) else (False, "bad"),
    )
    assert albion_client.find_client(None) == str(prog)


def test_embedded_fallback(monkeypatch, tmp_path):
    appdata = tmp_path / "AppData" / "AlbionTradeOptimizer" / "bin"
    managed = appdata / "albiondata-client.exe"
    emb = tmp_path / "embedded" / "resources" / "windows" / "albiondata-client.exe"
    emb.parent.mkdir(parents=True)
    emb.write_text("x")

    monkeypatch.setattr(albion_client, "APPDATA_BIN", appdata)
    monkeypatch.setattr(albion_client, "MANAGED_CLIENT", managed)
    monkeypatch.setattr(
        "services.albion_client._embedded_client_path", lambda: emb
    )
    monkeypatch.setattr(
        "services.albion_client.is_valid_win64_exe",
        lambda p: (True, "ok"),
    )

    result = albion_client.find_client(None)
    assert result == str(managed)
    assert managed.exists()
