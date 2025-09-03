from PySide6.QtCore import QObject, Signal


class AppSignals(QObject):
    """Central application-wide signals bus."""

    market_data_ready = Signal(dict)
    market_rows_updated = Signal(list)
    health_changed = Signal(object)


signals = AppSignals()
