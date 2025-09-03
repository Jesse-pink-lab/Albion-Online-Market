import re

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
