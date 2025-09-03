def qualities_to_csv(selection) -> str:
    """
    Map UI 'Quality' selection to API CSV of ints.
    Accepted UI values (examples): 'All', 'Normal (1)', 'Good (2)', 'Outstanding (3)', 'Excellent (4)', or numeric list.
    Return '1,2,3,4' for 'All'. Ensure we return only digits separated by commas.
    """
    s = (selection or "").strip().lower()
    if not s or s == "all":
        return "1,2,3,4"
    import re
    nums = re.findall(r"\d+", s)
    if nums:
        return ",".join(nums)
    return ",".join([p for p in s.replace(" ", "").split(",") if p.isdigit()])

def cities_to_list(selection, default_all: list[str]) -> list[str]:
    """
    UI 'Cities' selection -> list of city names. If 'All Cities' or empty -> default_all.
    """
    if not selection or str(selection).strip().lower() in ("all", "all cities"):
        return default_all
    return [c.strip() for c in str(selection).split(",") if c.strip()]
