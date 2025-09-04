from typing import Optional
import logging

from datasources.http import get_shared_session

log = logging.getLogger(__name__)


def fetch_latest_windows_client() -> Optional[bytes]:
    """
    Download the latest Windows client binary (or release manifest) and return its bytes.
    Caller is responsible for persisting/processing.
    """
    url = "https://updates.albiononline.com/client/windows/latest"
    s = get_shared_session()
    try:
        r = s.get(url, timeout=30)
        r.raise_for_status()
        return r.content
    except Exception as e:  # pragma: no cover - network failure
        log.warning("Failed to fetch latest Windows client: %s", e)
        return None
