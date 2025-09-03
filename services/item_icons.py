from __future__ import annotations
import os, hashlib, threading, requests
from PySide6.QtCore import QObject, Signal, QThreadPool, QRunnable, Slot, QMetaObject, Qt
from PySide6.QtGui import QPixmap
from utils.icons import item_icon_url
from services.netlimit import bucket
from services.market_prices import _on_result


class IconReady(QObject):
    ready = Signal(str, QPixmap)  # url, pixmap


class _FetchTask(QRunnable):
    def __init__(self, url: str, cache_dir: str, signaler: IconReady, timeout: float = 8.0):
        super().__init__()
        self.url, self.cache_dir, self.signaler, self.timeout = url, cache_dir, signaler, timeout
    def run(self):
        key = hashlib.md5(self.url.encode()).hexdigest()+".png"
        path = os.path.join(self.cache_dir, key)
        try:
            if os.path.isfile(path) and os.path.getsize(path) > 0:
                pm = QPixmap(path)
                if not pm.isNull():
                    QMetaObject.invokeMethod(self.signaler, "ready", Qt.QueuedConnection, 
                                             args=[self.url, pm])
                    return
            bucket.acquire()
            r = requests.get(self.url, timeout=self.timeout)
            _on_result(r.status_code)
            r.raise_for_status()
            os.makedirs(self.cache_dir, exist_ok=True)
            with open(path, "wb") as f: f.write(r.content)
            pm = QPixmap()
            pm.loadFromData(r.content)
            if not pm.isNull():
                QMetaObject.invokeMethod(self.signaler, "ready", Qt.QueuedConnection, 
                                         args=[self.url, pm])
        except Exception:
            # swallow; we'll keep placeholder
            pass


class ItemIconProvider(QObject):
    _instance_lock = threading.Lock()
    _instance: "ItemIconProvider|None" = None

    @classmethod
    def instance(cls, cache_dir: str) -> "ItemIconProvider":
        with cls._instance_lock:
            if not cls._instance:
                cls._instance = cls(cache_dir)
            return cls._instance

    def __init__(self, cache_dir: str):
        super().__init__()
        self.cache_dir = cache_dir
        self.pool = QThreadPool.globalInstance()
        self.signaler = IconReady()
        self.signaler.setParent(self)
        self.signaler.ready.connect(self._on_ready)
        self._mem: dict[str, QPixmap] = {}
        self._pending: set[str] = set()
        self._subscribers: dict[str, list[callable]] = {}

    def _on_ready(self, url: str, pm: QPixmap):
        self._mem[url] = pm
        for cb in self._subscribers.pop(url, []):
            try: cb(pm)
            except Exception: pass

    def get(self, item_id: str, quality: int | None, size: int, on_ready: callable) -> QPixmap:
        url = item_icon_url(item_id, quality, size)
        if url in self._mem:
            return self._mem[url]
        # queue fetch
        self._subscribers.setdefault(url, []).append(on_ready)
        if url not in self._pending:
            self._pending.add(url)
            self.pool.start(_FetchTask(url, self.cache_dir, self.signaler))
        return QPixmap()  # placeholder (empty)
