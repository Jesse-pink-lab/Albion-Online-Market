from __future__ import annotations
import os, sys, subprocess, threading, signal, shutil, platform
from dataclasses import dataclass
from typing import Optional, Callable, List


def _base_dir() -> str:
    return getattr(sys, "_MEIPASS", os.path.abspath(os.path.dirname(__file__)))


def _app_root() -> str:
    # services/ -> project root
    return os.path.abspath(os.path.join(_base_dir(), ".."))


def _bin_dir() -> str:
    # PyInstaller bundles binaries under ./bin in dist
    root = _app_root()
    p = os.path.join(root, "bin")
    if not os.path.isdir(p):
        # when frozen, _MEIPASS may contain bin directly
        p = os.path.join(_base_dir(), "bin")
    return p


def is_linux() -> bool:
    return sys.platform.startswith("linux")


def is_windows() -> bool:
    return os.name == "nt"


def npcap_installed() -> bool:
    if not is_windows():
        return False
    # Check service or DLL presence
    system32 = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "System32")
    return os.path.exists(os.path.join(system32, "Npcap")) or os.path.exists(os.path.join(system32, "drivers", "npcap.sys"))


def libpcap_present() -> bool:
    if sys.platform == "darwin":
        try:
            result = subprocess.run(["/usr/sbin/tcpdump", "-D"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return result.returncode == 0
        except Exception:
            return False
    if not is_linux():
        return False
    path = shutil.which('ldconfig')
    if path:
        try:
            out = subprocess.check_output([path, '-p'], text=True, stderr=subprocess.DEVNULL)
            if 'libpcap.so' in out:
                return True
        except Exception:
            pass
    candidates = ["/usr/lib/libpcap.so", "/usr/lib/x86_64-linux-gnu/libpcap.so"]
    return any(os.path.exists(p) for p in candidates)


@dataclass
class UploaderConfig:
    enabled: bool = True
    interface: Optional[str] = None
    enable_websocket: bool = True
    ingest_base: str = "http+pow://albion-online-data.com"  # default AODP PoW ingest
    no_cpu_limit: bool = False
    binary_path_win: Optional[str] = None  # override, else use ./bin/albiondata-client.exe
    binary_path_linux: Optional[str] = None  # override, else use ./bin/albiondata-client


class UploaderProcess:
    def __init__(self, cfg: UploaderConfig, on_log: Optional[Callable[[str], None]] = None):
        self.cfg = cfg
        self.proc: Optional[subprocess.Popen] = None
        self.on_log = on_log or (lambda line: None)

    def _resolve_binary(self) -> str:
        if is_windows():
            if self.cfg.binary_path_win:
                return self.cfg.binary_path_win
            return os.path.join(_bin_dir(), "albiondata-client.exe")
        else:
            if self.cfg.binary_path_linux:
                return self.cfg.binary_path_linux
            return os.path.join(_bin_dir(), "albiondata-client")

    def _build_args(self) -> List[str]:
        exe = self._resolve_binary()
        args = [exe, f"-publicIngestBaseUrls={self.cfg.ingest_base}"]
        if self.cfg.enable_websocket:
            args.append("-enableWebsockets")
        if self.cfg.no_cpu_limit:
            args.append("-noCPULimit")
        if self.cfg.interface:
            args.append(f"-interface={self.cfg.interface}")
        return args

    def _validate_binary_path(self, exe: str) -> List[str]:
        issues: List[str] = []
        if not os.path.isabs(exe):
            issues.append("Uploader path must be absolute.")
        elif not os.path.exists(exe):
            issues.append(f"Uploader not found at {exe}.")
        elif not is_windows() and not os.access(exe, os.X_OK):
            issues.append(f"Uploader at {exe} is not executable.")
        return issues

    def preflight_warnings(self) -> List[str]:
        warn = []
        if is_windows() and not npcap_installed():
            warn.append("Npcap not detected. Install Npcap to enable packet capture: https://npcap.com")
        if is_linux() and not libpcap_present():
            warn.append("libpcap not detected. Install libpcap (e.g., `sudo apt-get install -y libpcap0.8`).")
        exe = self._resolve_binary()
        warn.extend(self._validate_binary_path(exe))
        return warn

    def start(self) -> None:
        if self.proc and self.proc.poll() is None:
            return
        if not self.cfg.enabled:
            return
        issues = self.preflight_warnings()
        if issues:
            raise RuntimeError("; ".join(issues))
        args = self._build_args()
        kwargs = {}
        if is_windows():
            CREATE_NO_WINDOW = 0x08000000
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            kwargs['creationflags'] = CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP
        self.proc = subprocess.Popen(
            args,
            cwd=_app_root(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            **kwargs
        )
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self) -> None:
        if not self.proc or not self.proc.stdout:
            return
        for line in self.proc.stdout:
            self.on_log(line.rstrip())

    def stop(self, timeout: float = 5.0) -> None:
        if not self.proc or self.proc.poll() is not None:
            return
        try:
            if is_windows():
                try:
                    self.proc.send_signal(signal.CTRL_BREAK_EVENT)
                except Exception:
                    pass
            else:
                self.proc.terminate()
            self.proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                self.proc.kill()
            except Exception:
                pass
        finally:
            self.proc = None
