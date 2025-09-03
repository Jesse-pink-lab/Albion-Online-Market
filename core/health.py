from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import requests

from .signals import signals

logger = logging.getLogger(__name__)


@dataclass
class HealthStore:
    """Application health status with simple failure tracking."""

    aodp_online: bool = True
    fail_count: int = 0
    last_checked: Optional[datetime] = None


health_store = HealthStore()


def _emit_change() -> None:
    logger.info("Health change: aodp_online=%s", health_store.aodp_online)
    signals.health_changed.emit(health_store)


def update_aodp_status(online: bool) -> HealthStore:
    """Directly set the online flag and reset fail counter."""

    health_store.aodp_online = online
    health_store.fail_count = 0
    health_store.last_checked = datetime.now(timezone.utc)
    _emit_change()
    return health_store


def ping_aodp(base_url: str, session: Optional[requests.Session] = None) -> bool:
    """Ping the AODP API to update health status.

    The same base URL used for price requests is hit with a tiny
    endpoint.  Consecutive failures are counted and only after three
    failures will the ``aodp_online`` flag flip to ``False``.  HTTP 429
    responses are treated as *online* (rate limited) and reset the fail
    counter.
    """

    session = session or requests.Session()
    url = f"{base_url}/api/v2/stats/prices/T4_BAG.json?locations=Lymhurst&qualities=1"
    try:
        resp = session.get(url, timeout=(5, 10))
        if resp.status_code == 429:
            # Rate limited but server is reachable
            if not health_store.aodp_online or health_store.fail_count != 0:
                health_store.aodp_online = True
                health_store.fail_count = 0
                health_store.last_checked = datetime.now(timezone.utc)
                _emit_change()
            return True
        resp.raise_for_status()
        if not health_store.aodp_online or health_store.fail_count != 0:
            health_store.aodp_online = True
            health_store.fail_count = 0
            health_store.last_checked = datetime.now(timezone.utc)
            _emit_change()
        else:
            health_store.last_checked = datetime.now(timezone.utc)
        return True
    except Exception:  # pragma: no cover - requests mocked in tests
        health_store.fail_count += 1
        health_store.last_checked = datetime.now(timezone.utc)
        if health_store.fail_count >= 3 and health_store.aodp_online:
            health_store.aodp_online = False
            _emit_change()
        return False


__all__ = ["health_store", "update_aodp_status", "ping_aodp"]
