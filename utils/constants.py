"""Shared constants for the Albion Trade Optimizer project."""

from __future__ import annotations

# Maximum age for market data records in hours (default: 180 days)
MAX_DATA_AGE_HOURS = 4320  # 180 days

# Base URL for item icons; ``{id}`` will be replaced with the item identifier.
# The endpoint also accepts enchantment suffixes and ``?quality=`` parameters.
ICON_BASE = "https://render.albiononline.com/v1/item/{id}.png"

__all__ = ["MAX_DATA_AGE_HOURS", "ICON_BASE"]
