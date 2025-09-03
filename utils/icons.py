from urllib.parse import quote


def item_icon_url(item_id: str, quality: int | None = None, size: int = 64) -> str:
    iid = (item_id or "").strip()
    # item_id may already contain @enchant (e.g., T5_BAG@2) — leave as is
    q = f"&quality={int(quality)}" if quality else ""
    sz = max(32, min(int(size), 256))
    return f"https://render.albiononline.com/v1/item/{quote(iid)}.png?size={sz}{q}"
