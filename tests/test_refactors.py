import logging
import threading
import time
import pytest
from requests import exceptions as rqexc

from services.netlimit import TokenBucket
from core import health
from datasources import aodp as aodp_mod
from datasources.http import get_shared_session
from services.market_prices import STORE


def test_token_bucket_no_deadlock():
    bucket = TokenBucket(rate_per_sec=1.0, capacity=1)
    times = []

    def worker():
        bucket.acquire()
        times.append(time.time())

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)
    start = time.time()
    t1.start(); t2.start()
    t1.join(2)
    t2.join(2)
    end = time.time()
    assert len(times) == 2
    assert end - start < 1.8


def test_ping_aodp_timeout_logs(monkeypatch, caplog):
    class DummySession:
        def get(self, *a, **k):
            raise rqexc.Timeout("boom")
    monkeypatch.setattr(health, "get_shared_session", lambda: DummySession())
    with caplog.at_level(logging.WARNING):
        ok = health.ping_aodp("europe")
    assert ok is False
    assert "AODP ping failed" in caplog.text


def test_process_history_record_error_handling(monkeypatch):
    client = aodp_mod.AODPClient({})
    assert client._process_history_record({"location": "Lymhurst"}) is None

    class DummyDate:
        @staticmethod
        def fromisoformat(s):
            raise RuntimeError("boom")

    monkeypatch.setattr(aodp_mod, "datetime", DummyDate)
    with pytest.raises(RuntimeError):
        client._process_history_record({
            "item_type_id": "T4", "location": "Lymhurst", "avg_price": 1, "timestamp": "2020-01-01T00:00:00Z"
        })


def test_get_shared_session_thread_local():
    main_sess = get_shared_session()
    other = []
    def worker():
        other.append(get_shared_session())
    t = threading.Thread(target=worker)
    t.start(); t.join()
    assert other and other[0] is not main_sess


def test_aodp_client_uses_shared_session():
    sess = get_shared_session()
    client = aodp_mod.AODPClient({})
    assert client.session is get_shared_session()


def test_shared_session_headers():
    sess = get_shared_session()
    assert sess.headers.get("Accept") == "application/json"
    assert "AlbionTradeOptimizer" in sess.headers.get("User-Agent", "")


def test_latest_rows_returns_copy():
    STORE.clear()
    STORE._latest_rows = [{"a": 1}]
    out = STORE.latest_rows()
    out.append({"a": 2})
    assert STORE.latest_rows() == [{"a": 1}]
