from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from .signals import signals

logger = logging.getLogger(__name__)


@dataclass
class HealthStore:
    """Application health status."""

    aodp_online: bool = False
    last_checked: Optional[datetime] = None


health_store = HealthStore()


def update_aodp_status(online: bool) -> HealthStore:
    """Update AODP online status and emit signal."""

    health_store.aodp_online = online
    health_store.last_checked = datetime.now(timezone.utc)
    logger.info("Health change: aodp_online=%s", online)
    signals.health_changed.emit(health_store)
    return health_store
