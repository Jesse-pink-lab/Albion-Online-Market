from services.uploader import UploaderConfig, UploaderProcess, is_windows, is_linux
import pytest


def test_arg_building():
    cfg = UploaderConfig(enabled=True, interface="Ethernet 2", enable_websocket=True, ingest_base="http+pow://albion-online-data.com")
    up = UploaderProcess(cfg)
    args = up._build_args()
    assert any("http+pow://" in a for a in args)
    assert any(a.startswith("-interface=") for a in args)


def test_binary_resolution(tmp_path, monkeypatch):
    monkeypatch.setattr('services.uploader._bin_dir', lambda: str(tmp_path))
    fname = "albiondata-client.exe" if is_windows() else "albiondata-client"
    p = tmp_path / fname
    p.write_text("test")
    if not is_windows():
        p.chmod(0o755)
    cfg = UploaderConfig()
    up = UploaderProcess(cfg)
    assert up._resolve_binary() == str(p)


@pytest.mark.skipif(not is_linux(), reason="linux only")
def test_preflight_warn_libpcap(monkeypatch, tmp_path):
    monkeypatch.setattr('services.uploader._bin_dir', lambda: str(tmp_path))
    monkeypatch.setattr('services.uploader.libpcap_present', lambda: False)
    up = UploaderProcess(UploaderConfig())
    warns = up.preflight_warnings()
    assert any('libpcap' in w for w in warns)


@pytest.mark.skipif(not is_windows(), reason="windows only")
def test_preflight_warn_npcap(monkeypatch, tmp_path):
    monkeypatch.setattr('services.uploader._bin_dir', lambda: str(tmp_path))
    monkeypatch.setattr('services.uploader.npcap_installed', lambda: False)
    up = UploaderProcess(UploaderConfig())
    warns = up.preflight_warnings()
    assert any('Npcap' in w for w in warns)
