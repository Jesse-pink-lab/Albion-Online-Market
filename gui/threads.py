from PySide6.QtCore import QObject, QThread, Signal
import time
import traceback
import logging

log = logging.getLogger(__name__)


class RefreshWorker(QObject):
    """Background worker to refresh market data."""

    finished = Signal(dict)
    progress = Signal(int, str)
    error = Signal(str)

    def __init__(self, params: dict):
        super().__init__()
        self.params = params
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        start = time.perf_counter()
        self.progress.emit(1, "Starting market refresh...")
        try:
            from datasources import aodp

            result = aodp.refresh_prices(
                **self.params,
                on_progress=lambda p, m: self.progress.emit(p, m),
                should_cancel=lambda: self._cancel,
            )
            elapsed = time.perf_counter() - start
            self.finished.emit({"ok": True, "elapsed": elapsed, "result": result})
        except Exception as e:  # pragma: no cover - unexpected errors
            log.exception("RefreshWorker failed: %s", e)
            self.error.emit(str(e))
