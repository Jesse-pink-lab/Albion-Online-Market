import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import types
from core.health import store, ping_aodp
import datasources.aodp_url as aurl


class DummyResp:
    def __init__(self, status, data=None):
        self.status_code = status
        self._data = data or []

    def raise_for_status(self):
        if self.status_code >= 400 and self.status_code not in (429, 200):
            raise Exception("error")

    def json(self):
        return self._data


def test_health_requires_three_failures(monkeypatch):
    statuses = [500, 500, 500]

    def fake_get(url, params=None, timeout=None):
        return DummyResp(statuses.pop(0))

    session = types.SimpleNamespace(get=fake_get)
    monkeypatch.setattr(aurl, "base_for", lambda s: s)
    store.aodp_online = True
    store._fails = 0
    ping_aodp("west", session)
    assert store.aodp_online
    ping_aodp("west", session)
    assert store.aodp_online
    ping_aodp("west", session)
    assert not store.aodp_online


def test_health_429_is_online(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        return DummyResp(429)

    session = types.SimpleNamespace(get=fake_get)
    monkeypatch.setattr(aurl, "base_for", lambda s: s)
    store.aodp_online = False
    store._fails = 5
    ping_aodp("west", session)
    assert store.aodp_online and store._fails == 0


def test_success_resets_failures(monkeypatch):
    statuses = [500, 200]

    def fake_get(url, params=None, timeout=None):
        return DummyResp(statuses.pop(0))

    session = types.SimpleNamespace(get=fake_get)
    monkeypatch.setattr(aurl, "base_for", lambda s: s)
    store.aodp_online = True
    store._fails = 0
    ping_aodp("west", session)
    assert store._fails == 1
    ping_aodp("west", session)
    assert store.aodp_online and store._fails == 0

