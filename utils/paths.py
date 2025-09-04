from pathlib import Path
try:
    from platformdirs import user_data_dir, user_log_dir
except Exception:
    try:
        from appdirs import user_data_dir, user_log_dir  # type: ignore
    except Exception:
        import os
        def user_data_dir(appname, appauthor=None):
            return os.path.join(os.environ.get("APPDATA", "."), appname)
        def user_log_dir(appname, appauthor=None):
            return os.path.join(os.environ.get("APPDATA", "."), appname, "logs")

APP_NAME = "AlbionTradeOptimizer"
APP_VENDOR = "Albion"

DATA_DIR = Path(user_data_dir(APP_NAME, APP_VENDOR))
LOG_DIR = Path(user_log_dir(APP_NAME, APP_VENDOR))
DB_DIR = DATA_DIR / "data"
DB_PATH = DB_DIR / "albion_trade.db"
CONFIG_PATH = DATA_DIR / "config.yaml"


def init_app_paths() -> None:
    for _p in (DATA_DIR, LOG_DIR, DB_DIR):
        _p.mkdir(parents=True, exist_ok=True)

    legacy_config = Path("config.yaml")
    if not CONFIG_PATH.exists() and legacy_config.exists():
        CONFIG_PATH.write_bytes(legacy_config.read_bytes())

    legacy_db = Path("data") / "albion_trade.db"
    if not DB_PATH.exists() and legacy_db.exists():
        DB_PATH.write_bytes(legacy_db.read_bytes())
