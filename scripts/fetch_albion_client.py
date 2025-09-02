"""Download the official Windows Albion Data Client for release builds."""
from __future__ import annotations

from pathlib import Path
import sys

from services.albion_client_fetch import download_client, DOWNLOAD_URL


def main() -> int:
    dest = Path("resources/windows/albiondata-client.exe")
    try:
        download_client(dest, DOWNLOAD_URL)
    except Exception as exc:  # pragma: no cover - build time
        print(f"Failed to fetch albiondata-client.exe: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
