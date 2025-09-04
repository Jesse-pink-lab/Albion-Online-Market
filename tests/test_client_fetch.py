from services import albion_client_fetch as fetcher


class DummySession:
    def __init__(self, resp=None, exc=None):
        self.resp = resp
        self.exc = exc
        self.called = False

    def get(self, url, timeout):
        self.called = True
        if self.exc:
            raise self.exc
        return self.resp


class DummyResp:
    def __init__(self, content=b"data"):
        self.content = content

    def raise_for_status(self):
        pass


def test_fetch_success(monkeypatch):
    resp = DummyResp(b"ok")
    session = DummySession(resp=resp)
    monkeypatch.setattr(fetcher, "get_shared_session", lambda: session)
    assert fetcher.fetch_latest_windows_client() == b"ok"
    assert session.called


def test_fetch_failure(monkeypatch):
    session = DummySession(exc=RuntimeError("boom"))
    monkeypatch.setattr(fetcher, "get_shared_session", lambda: session)
    assert fetcher.fetch_latest_windows_client() is None
    assert session.called
