import pathlib
import sys

import pytest

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from store.db import DatabaseManager
from sqlalchemy.exc import SQLAlchemyError


def test_db_init_sqlalchemy_error(monkeypatch, caplog):
    mgr = DatabaseManager({})

    def boom(*args, **kwargs):
        raise SQLAlchemyError("boom")

    monkeypatch.setattr("store.db.create_engine", boom)
    with pytest.raises(SQLAlchemyError):
        mgr.initialize_database()
    assert any("Database initialization failed" in r.message for r in caplog.records)


def test_db_init_other_error(monkeypatch):
    mgr = DatabaseManager({})

    def boom(*args, **kwargs):
        raise ValueError("nope")

    monkeypatch.setattr("store.db.create_engine", boom)
    with pytest.raises(ValueError):
        mgr.initialize_database()
