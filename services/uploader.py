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
    if not is_linux():
        return False
    # heuristic: ldconfig listing or common .so
    try:
        out = subprocess.check_output(["/sbin/ldconfig", "-p"], text=True, stderr=subprocess.DEVNULL)
        return "libpcap.so" in out
    except Exception:
        # fallback checks
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
            if self.cfg.binary_path_win and os.path.exists(self.cfg.binary_path_win):
                return self.cfg.binary_path_win
            cand = os.path.join(_bin_dir(), "albiondata-client.exe")
            return cand
        else:
            if self.cfg.binary_path_linux and os.path.exists(self.cfg.binary_path_linux):
                return self.cfg.binary_path_linux
            cand = os.path.join(_bin_dir(), "albiondata-client")
            return cand

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

    def preflight_warnings(self) -> List[str]:
        warn = []
        if is_windows() and not npcap_installed():
            warn.append("Npcap not detected. Install Npcap to enable packet capture: https://npcap.com")
        if is_linux() and not libpcap_present():
            warn.append("libpcap not detected. Install libpcap (e.g., `sudo apt-get install -y libpcap0.8`).")
        exe = self._resolve_binary()
        if not os.path.exists(exe):
            warn.append(f"Uploader binary not found at {exe}.")
        return warn

    def start(self) -> None:
        if self.proc and self.proc.poll() is None:
            return
        if not self.cfg.enabled:
            return
        args = self._build_args()
        creationflags = 0x08000000 if is_windows() else 0  # CREATE_NO_WINDOW
        self.proc = subprocess.Popen(
            args,
            cwd=_app_root(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=creationflags
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
            if is_windows() and hasattr(signal, "CTRL_BREAK_EVENT"):
                self.proc.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                self.proc.terminate()
            self.proc.wait(timeout=timeout)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass
        finally:
            self.proc = None
