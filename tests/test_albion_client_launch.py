import logging
import subprocess

from logging_config import get_logger

from services.albion_client import launch_client_with_fallback


class _PopenMock:
    """Simple Popen mock to control communicate behaviour."""

    def __init__(self, cmd, behavior):
        self.cmd = cmd
        self._behavior = behavior
        self.returncode = behavior.get("returncode")
        self.pid = behavior.get("pid", 1234)

    def communicate(self, timeout=None):  # pragma: no cover - behavior driven
        if "exc" in self._behavior:
            raise self._behavior["exc"]
        return self._behavior.get("output", b""), b""

    def kill(self):  # pragma: no cover - not relevant for test behaviour
        pass


def _prepare_popen(monkeypatch, behaviors):
    calls = []

    def fake_popen(cmd, **kwargs):
        behavior = behaviors[len(calls)]
        proc = _PopenMock(cmd, behavior)
        calls.append(proc)
        return proc

    monkeypatch.setattr("services.albion_client.subprocess.Popen", fake_popen)
    return calls


def _patch_common(monkeypatch):
    get_logger("test")
    monkeypatch.setattr(
        "services.albion_client.is_valid_win64_exe", lambda p: (True, "")
    )


def test_flag_rejection_triggers_fallback(monkeypatch, caplog):
    _patch_common(monkeypatch)

    monkeypatch.setattr(
        "services.albion_client.subprocess.run",
        lambda *a, **kw: subprocess.CompletedProcess(a[0], 0, b"", b""),
    )

    behaviors = [
        {
            "output": b"flag provided but not defined: -minimize\n",
            "returncode": 1,
        },
        {"exc": subprocess.TimeoutExpired(cmd="x", timeout=2)},
        {},
    ]
    calls = _prepare_popen(monkeypatch, behaviors)

    with caplog.at_level(logging.INFO):
        proc = launch_client_with_fallback("client.exe", ["-minimize"])

    assert calls[0].cmd == ["client.exe", "-minimize"]
    assert calls[1].cmd == ["client.exe"]
    assert calls[2].cmd == ["client.exe"]
    assert proc is calls[2]
    assert "Client rejected flags" in caplog.text


def test_preferred_flags_work(monkeypatch):
    _patch_common(monkeypatch)

    monkeypatch.setattr(
        "services.albion_client.subprocess.run",
        lambda *a, **kw: subprocess.CompletedProcess(a[0], 0, b"", b""),
    )

    behaviors = [
        {"exc": subprocess.TimeoutExpired(cmd="x", timeout=2)},
        {},
    ]
    calls = _prepare_popen(monkeypatch, behaviors)

    proc = launch_client_with_fallback("client.exe", ["-minimize"])

    assert calls[0].cmd == ["client.exe", "-minimize"]
    assert calls[1].cmd == ["client.exe", "-minimize"]
    assert proc is calls[1]


def test_version_probe_failure_ignored(monkeypatch):
    _patch_common(monkeypatch)

    monkeypatch.setattr(
        "services.albion_client.subprocess.run",
        lambda *a, **kw: (_ for _ in ()).throw(OSError("missing")),
    )

    behaviors = [
        {"exc": subprocess.TimeoutExpired(cmd="x", timeout=2)},
        {},
    ]
    calls = _prepare_popen(monkeypatch, behaviors)

    proc = launch_client_with_fallback("client.exe", [])

    assert calls[0].cmd == ["client.exe"]
    assert calls[1].cmd == ["client.exe"]
    assert proc is calls[1]

