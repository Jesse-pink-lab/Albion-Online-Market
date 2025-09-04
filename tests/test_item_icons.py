import pathlib

import sys
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from services import item_icons


class DummyResp:
    status_code = 200

    def __init__(self):
        self.content = b"data"

    def raise_for_status(self):
        pass


class DummySession:
    def __init__(self):
        self.calls = 0

    def get(self, url, timeout):
        self.calls += 1
        return DummyResp()


def test_fetch_icon_bytes_uses_shared_session_and_cache(monkeypatch):
    session = DummySession()
    monkeypatch.setattr(item_icons, "get_shared_session", lambda: session)

    data1 = item_icons.fetch_icon_bytes("item", 1)
    assert data1 == b"data"
    data2 = item_icons.fetch_icon_bytes("item", 1)
    assert data2 == b"data"
    assert session.calls == 1
