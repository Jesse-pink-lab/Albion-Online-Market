from services.uploader import UploaderConfig, UploaderProcess, is_windows, is_linux
import pytest
import subprocess
import signal


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


def test_binary_override_validation(tmp_path):
    # relative path rejection
    cfg = UploaderConfig(binary_path_linux='rel' if not is_windows() else None,
                         binary_path_win='rel.exe' if is_windows() else None)
    up = UploaderProcess(cfg)
    warns = up.preflight_warnings()
    assert any('absolute' in w for w in warns)

    # non-executable on POSIX
    if not is_windows():
        p = tmp_path / 'uploader'
        p.write_text('test')
        p.chmod(0o644)
        cfg = UploaderConfig(binary_path_linux=str(p))
        up = UploaderProcess(cfg)
        warns = up.preflight_warnings()
        assert any('not executable' in w for w in warns)


class DummyProc:
    def __init__(self, should_timeout=False):
        self.stdout = []
        self.should_timeout = should_timeout
        self.sent = []
        self.terminated = False
        self.killed = False
        self.returncode = None

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        if self.should_timeout:
            raise subprocess.TimeoutExpired('cmd', timeout)
        self.returncode = 0

    def send_signal(self, sig):
        self.sent.append(sig)

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True


def test_lifecycle_start_stop(monkeypatch):
    procs = []

    def fake_popen(args, **kwargs):
        proc = DummyProc(should_timeout=True)
        proc.kwargs = kwargs
        procs.append(proc)
        return proc

    monkeypatch.setattr('services.uploader.subprocess.Popen', fake_popen)
    monkeypatch.setattr('services.uploader.UploaderProcess.preflight_warnings', lambda self: [])
    up = UploaderProcess(UploaderConfig())
    up.start()
    up.start()
    assert len(procs) == 1  # idempotent
    up.stop(timeout=0)
    assert procs[0].killed


@pytest.mark.skipif(not is_windows(), reason="windows only")
def test_windows_creationflags_and_signal(monkeypatch):
    procs = []

    def fake_popen(args, **kwargs):
        proc = DummyProc(should_timeout=True)
        proc.kwargs = kwargs
        procs.append(proc)
        return proc

    monkeypatch.setattr('services.uploader.subprocess.Popen', fake_popen)
    monkeypatch.setattr('services.uploader.UploaderProcess.preflight_warnings', lambda self: [])
    up = UploaderProcess(UploaderConfig())
    up.start()
    flags = procs[0].kwargs.get('creationflags', 0)
    assert flags & 0x00000200  # CREATE_NEW_PROCESS_GROUP
    up.stop(timeout=0)
    assert any(sig == signal.CTRL_BREAK_EVENT for sig in procs[0].sent)
