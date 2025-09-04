from PySide6.QtCore import QObject, QThread, Signal
import time
import logging

log = logging.getLogger(__name__)


class RefreshWorker(QObject):
    """Background worker to refresh market data."""

    finished = Signal(dict)
    progress = Signal(int, str)
    error = Signal(str)

    def __init__(self, params: dict, settings=None, itemsEdit=None):
        super().__init__()
        self.params = params
        self.settings = settings
        # optional text edit providing comma separated item list
        if itemsEdit is not None:
            self.itemsEdit = itemsEdit
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        start = time.perf_counter()
        self.progress.emit(1, "Starting market refresh...")
        try:
            from services.market_prices import STORE
            from datasources.http import get_shared_session
            from core.health import mark_online_on_data_success

            server = self.params.get("server")
            cities_sel = self.params.get("cities", "")
            qual_sel = self.params.get("qualities", "")
            fetch_all = self.params.get("fetch_all", True)
            items_text = self.itemsEdit.text() if hasattr(self, "itemsEdit") else ""

            norm = STORE.fetch_prices(
                server=server,
                items_edit_text=items_text,
                cities_sel=cities_sel,
                qual_sel=qual_sel,
                fetch_all=fetch_all,
                session=get_shared_session(),
                settings=self.settings,
                on_progress=lambda p, m: self.progress.emit(p, m),
                cancel=lambda: self._cancel,
            )
            if norm:
                mark_online_on_data_success()
            elapsed = time.perf_counter() - start
            log.info(
                "Market refresh completed: items=%s records=%s elapsed=%.2fs",
                len(norm), len(norm), elapsed,
            )
            summary = {"items": len(norm), "records": len(norm)}
            self.finished.emit({"ok": True, "elapsed": elapsed, "result": summary})
        except Exception as e:  # pragma: no cover - unexpected errors
            log.exception("RefreshWorker failed: %s", e)
            self.error.emit(str(e))
