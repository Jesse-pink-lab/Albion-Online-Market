from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import requests

from datasources.aodp_url import base_for, build_prices_url
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
    base = base_for(base_url)
    url = build_prices_url(base, "T4_BAG", "Lymhurst", "1")
    try:
        resp = session.get(url, timeout=(3, 5))
        code = resp.status_code
        if code == 429:
            online = True
        else:
            resp.raise_for_status()
            online = True
        if online:
            if not health_store.aodp_online or health_store.fail_count != 0:
                health_store.aodp_online = True
                health_store.fail_count = 0
                health_store.last_checked = datetime.now(timezone.utc)
                _emit_change()
            else:
                health_store.last_checked = datetime.now(timezone.utc)
            logger.info(
                "Health ping: %s status=%s online=%s fails=%d",
                url,
                code,
                True,
                health_store.fail_count,
            )
            return True
    except Exception:  # pragma: no cover - requests mocked in tests
        health_store.fail_count += 1
        health_store.last_checked = datetime.now(timezone.utc)
        if health_store.fail_count >= 3 and health_store.aodp_online:
            health_store.aodp_online = False
            _emit_change()
        logger.info(
            "Health ping: %s status=%s online=%s fails=%d",
            url,
            "err",
            False,
            health_store.fail_count,
        )
        return False


__all__ = ["health_store", "update_aodp_status", "ping_aodp"]
