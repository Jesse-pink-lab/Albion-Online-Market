import logging
import requests
from requests import exceptions as rqexc
from datasources.http import get_shared_session
from datasources.aodp_url import base_for, build_prices_request
from core.signals import signals
from services.netlimit import bucket
from services.market_prices import _on_result

log = logging.getLogger(__name__)

class HealthStore:
    def __init__(self):
        self.aodp_online = False
        self._fails = 0

    def set_online(self, online: bool):
        if online != self.aodp_online:
            self.aodp_online = online
            log.info("Health change: aodp_online=%s", online)
            signals.health_changed.emit(self)


store = HealthStore()
# Backwards compat alias for widgets importing health_store
health_store = store


def ping_aodp(server: str):
    sess = get_shared_session()
    base = base_for(server)
    url, params = build_prices_request(base, ["T4_BAG"], ["Lymhurst"], "1")
    try:
        bucket.acquire()
        r = sess.get(url, params=params, timeout=(3, 5))
        code = r.status_code
        _on_result(code)
        if code in (429, 200):
            _ = r.json() if code == 200 else None
            store._fails = 0
            store.set_online(True)
            return True
        store._fails += 1
    except (rqexc.Timeout, rqexc.ConnectionError, rqexc.HTTPError) as e:
        store._fails += 1
        log.warning("AODP ping failed (%s): %s", type(e).__name__, e)
        if store._fails >= 3:
            store.set_online(False)
        return False
    if store._fails >= 3:
        store.set_online(False)
    return store.aodp_online


def mark_online_on_data_success():
    store._fails = 0
    store.set_online(True)
