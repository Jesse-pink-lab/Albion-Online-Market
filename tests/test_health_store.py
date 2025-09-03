import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

import types
from core.health import health_store, ping_aodp


class DummyResp:
    def __init__(self, status):
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400 and self.status_code != 429:
            raise Exception("error")


def test_health_requires_three_failures():
    statuses = [500, 500, 500]

    def fake_get(url, timeout=None):
        return DummyResp(statuses.pop(0))

    session = types.SimpleNamespace(get=fake_get)
    health_store.aodp_online = True
    health_store.fail_count = 0
    ping_aodp("http://x", session)
    assert health_store.aodp_online
    ping_aodp("http://x", session)
    assert health_store.aodp_online
    ping_aodp("http://x", session)
    assert not health_store.aodp_online


def test_health_429_is_online():
    statuses = [429]

    def fake_get(url, timeout=None):
        return DummyResp(statuses.pop(0))

    session = types.SimpleNamespace(get=fake_get)
    health_store.aodp_online = False
    health_store.fail_count = 5
    ping_aodp("http://x", session)
    assert health_store.aodp_online and health_store.fail_count == 0
