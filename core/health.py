import logging, requests
from datasources.aodp_url import base_for, build_prices_request
from core.signals import signals

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

def ping_aodp(active_server: str, session: requests.Session):
    base = base_for(active_server)
    url, params = build_prices_request(base, ["T4_BAG"], ["Lymhurst"], "1")
    try:
        r = session.get(url, params=params, timeout=(3,5))
        code = r.status_code
        if code == 429:
            store._fails = 0
            store.set_online(True); return
        if code == 200:
            _ = r.json()
            store._fails = 0
            store.set_online(True); return
        store._fails += 1
    except Exception:
        store._fails += 1
    if store._fails >= 3:
        store.set_online(False)

def mark_online_on_data_success():
    store._fails = 0
    store.set_online(True)
