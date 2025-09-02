from pathlib import Path
import pytest

from services import albion_client


def setup_paths(tmp_path):
    appdata = tmp_path / "AppData" / "AlbionTradeOptimizer" / "bin"
    managed = appdata / "albiondata-client.exe"
    prog = tmp_path / "Program Files" / "Albion Data Client" / "albiondata-client.exe"
    override = tmp_path / "override.exe"
    appdata.mkdir(parents=True, exist_ok=True)
    prog.parent.mkdir(parents=True, exist_ok=True)
    return appdata, managed, prog, override


def test_resolution_override(monkeypatch, tmp_path):
    appdata, managed, prog, override = setup_paths(tmp_path)
    override.write_text("x")

    monkeypatch.setattr(albion_client, "APPDATA_BIN", appdata)
    monkeypatch.setattr(albion_client, "MANAGED_CLIENT", managed)
    monkeypatch.setattr(albion_client, "DEFAULT_PROG_FILES", str(prog))
    monkeypatch.setattr(
        albion_client,
        "is_valid_win64_exe",
        lambda p: (True, "ok") if p == str(override) else (False, "bad"),
    )

    assert albion_client.find_client(str(override)) == str(override)


def test_resolution_appdata(monkeypatch, tmp_path):
    appdata, managed, prog, _ = setup_paths(tmp_path)
    managed.write_text("x")

    monkeypatch.setattr(albion_client, "APPDATA_BIN", appdata)
    monkeypatch.setattr(albion_client, "MANAGED_CLIENT", managed)
    monkeypatch.setattr(albion_client, "DEFAULT_PROG_FILES", str(prog))
    monkeypatch.setattr(
        albion_client,
        "is_valid_win64_exe",
        lambda p: (True, "ok") if p == str(managed) else (False, "bad"),
    )

    assert albion_client.find_client(None) == str(managed)


def test_resolution_program_files(monkeypatch, tmp_path):
    appdata, managed, prog, _ = setup_paths(tmp_path)
    prog.write_text("x")

    monkeypatch.setattr(albion_client, "APPDATA_BIN", appdata)
    monkeypatch.setattr(albion_client, "MANAGED_CLIENT", managed)
    monkeypatch.setattr(albion_client, "DEFAULT_PROG_FILES", str(prog))
    monkeypatch.setattr(
        albion_client,
        "is_valid_win64_exe",
        lambda p: (True, "ok") if p == str(prog) else (False, "bad"),
    )

    assert albion_client.find_client(None) == str(prog)


def test_embedded_copies(monkeypatch, tmp_path):
    appdata, managed, prog, _ = setup_paths(tmp_path)
    emb = tmp_path / "emb" / "resources" / "windows" / "albiondata-client.exe"
    emb.parent.mkdir(parents=True)
    emb.write_text("x")

    monkeypatch.setattr(albion_client, "APPDATA_BIN", appdata)
    monkeypatch.setattr(albion_client, "MANAGED_CLIENT", managed)
    monkeypatch.setattr(albion_client, "DEFAULT_PROG_FILES", str(prog))
    monkeypatch.setattr(albion_client, "_embedded_client_path", lambda: emb)
    monkeypatch.setattr(
        albion_client,
        "is_valid_win64_exe",
        lambda p: (True, "ok"),
    )

    result = albion_client.find_client(None)
    assert result == str(managed)
    assert managed.exists()


def test_download_called(monkeypatch, tmp_path):
    appdata, managed, prog, _ = setup_paths(tmp_path)

    monkeypatch.setattr(albion_client, "APPDATA_BIN", appdata)
    monkeypatch.setattr(albion_client, "MANAGED_CLIENT", managed)
    monkeypatch.setattr(albion_client, "DEFAULT_PROG_FILES", str(prog))
    monkeypatch.setattr(albion_client, "_embedded_client_path", lambda: Path("missing"))
    monkeypatch.setattr(
        albion_client,
        "is_valid_win64_exe",
        lambda p: (True, "ok") if p == str(managed) else (False, "bad"),
    )

    called = {}

    def fake_fetch(dest, prefer_installer=False):
        called["yes"] = True
        dest_path = Path(dest)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_text("x")
        return str(dest_path)

    monkeypatch.setattr(albion_client, "fetch_latest_windows_client", fake_fetch)

    result = albion_client.find_client(None, ask_download=lambda: True)
    assert result == str(managed)
    assert called
