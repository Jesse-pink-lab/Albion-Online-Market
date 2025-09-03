import re

def qualities_to_csv(selection) -> str:
    s = (selection or "").strip().lower()
    if not s or s in ("all", "all qualities"):
        return "1,2,3,4,5"
    nums = re.findall(r"\d+", s)
    if nums:
        return ",".join(nums)
    # already CSV-like? keep only digits
    return ",".join([p for p in s.replace(" ", "").split(",") if p.isdigit()]) or "1,2,3,4,5"

def cities_to_list(selection, default_all: list[str]) -> list[str]:
    if not selection or str(selection).strip().lower() in ("all", "all cities"):
        return list(default_all)
    return [c.strip() for c in str(selection).split(",") if c.strip()]
