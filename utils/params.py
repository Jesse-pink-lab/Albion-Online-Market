import re
from typing import Iterable, List, Set

ROYAL_CITIES: Set[str] = {
    "Bridgewatch",
    "Fort Sterling",
    "Lymhurst",
    "Martlock",
    "Thetford",
    "Caerleon",
}

def qualities_to_csv(selection) -> str:
    if isinstance(selection, (list, tuple)):
        nums = [str(int(x)) for x in selection if str(x).isdigit()]
        return ",".join(nums) if nums else "1,2,3,4,5"
    s = (selection or "").strip().lower()
    if not s or s in ("all", "all qualities"):
        return "1,2,3,4,5"
    nums = re.findall(r"\d+", s)
    if nums:
        return ",".join(nums)
    # already CSV-like? keep only digits
    return ",".join([p for p in s.replace(" ", "").split(",") if p.isdigit()]) or "1,2,3,4,5"

def cities_to_list(selection, default_all: list[str]) -> list[str]:
    # Accept list or CSV string; blank/All -> default_all
    if isinstance(selection, (list, tuple)):
        return list(selection) if selection else list(default_all)
    if not selection or str(selection).strip().lower() in ("all", "all cities"):
        return list(default_all)
    return [c.strip() for c in str(selection).split(",") if c.strip()]


def parse_quality_input(selection) -> List[int]:
    """Return list of quality integers or [1..5] for "all"."""

    if isinstance(selection, Iterable) and not isinstance(selection, (str, bytes)):
        nums = [int(x) for x in selection if str(x).isdigit()]
        return nums or [1, 2, 3, 4, 5]
    s = (selection or "").strip().lower()
    if not s or s in ("all", "all qualities"):
        return [1, 2, 3, 4, 5]
    nums = re.findall(r"\d+", s)
    return [int(n) for n in nums] if nums else [1, 2, 3, 4, 5]


def parse_city_selection(selection, default_all: Iterable[str]) -> Set[str]:
    """Return a set of city names based on ``selection``."""

    if isinstance(selection, Iterable) and not isinstance(selection, (str, bytes)):
        sel = {str(c).strip() for c in selection if str(c).strip()}
        return sel or set(default_all)
    s = (selection or "").strip().lower()
    if not s or s in ("all", "all cities"):
        return set(default_all)
    if s == "royal cities only":
        return set(ROYAL_CITIES)
    if s == "black market only":
        return {"Black Market"}
    return {c.strip() for c in str(selection).split(",") if c.strip()}


__all__ = [
    "qualities_to_csv",
    "cities_to_list",
    "parse_quality_input",
    "parse_city_selection",
    "ROYAL_CITIES",
]
