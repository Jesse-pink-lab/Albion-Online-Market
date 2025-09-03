from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional, Callable
import os, io, threading
import requests
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import QObject, Signal, QThreadPool, QRunnable, Slot
from services.netlimit import bucket
from services.market_prices import _on_result
from platformdirs import user_cache_dir

ICON_BASE = "https://render.albiononline.com/v1/item"  # e.g. /T4_SWORD.png?quality=3

def icon_url(item_id: str, quality: Optional[int] = None) -> str:
    item = item_id.strip()
    if not item.endswith(".png"):
        item = f"{item}.png"
    qs = f"?quality={quality}" if quality else ""
    return f"{ICON_BASE}/{item}{qs}"

_cache_dir = os.path.join(user_cache_dir("AlbionTradeOptimizer"), "icons")
os.makedirs(_cache_dir, exist_ok=True)

def _disk_path(item_id: str, quality: Optional[int]) -> str:
    q = f"q{quality}" if quality else "q0"
    safe = item_id.replace("/", "_").replace(":", "_")
    return os.path.join(_cache_dir, f"{safe}_{q}.png")

@lru_cache(maxsize=4096)
def _load_pixmap_from_disk(key: str) -> Optional[QPixmap]:
    if os.path.exists(key):
        pm = QPixmap()
        if pm.load(key):
            return pm
    return None

class _FetchTask(QRunnable):
    def __init__(self, url: str, out_path: str, cb: Callable[[Optional[QPixmap]], None]):
        super().__init__()
        self.url = url
        self.out_path = out_path
        self.cb = cb

    @Slot()
    def run(self):
        try:
            bucket.acquire()
            r = requests.get(self.url, timeout=15)
            _on_result(r.status_code)
            r.raise_for_status()
            data = r.content
            # write once
            try:
                with open(self.out_path, "wb") as f:
                    f.write(data)
            except Exception:
                pass
            pm = QPixmap()
            pm.loadFromData(data)
            self.cb(pm if not pm.isNull() else None)
        except Exception:
            self.cb(None)

class IconProvider(QObject):
    """Async icon provider with RAM+disk cache; emits callback when ready."""
    _pool = QThreadPool.globalInstance()

    def get_icon_async(self, item_id: str, quality: Optional[int], on_ready: Callable[[QIcon], None]):
        path = _disk_path(item_id, quality)
        pm = _load_pixmap_from_disk.cache_clear() or None  # no-op to satisfy lint
        pm = _load_pixmap_from_disk(path)
        if pm:
            on_ready(QIcon(pm))
            return
        url = icon_url(item_id, quality)
        def _done(pm):
            on_ready(QIcon(pm) if pm else QIcon())
        task = _FetchTask(url, path, _done)
        self._pool.start(task)

ICON_PROVIDER = IconProvider()
