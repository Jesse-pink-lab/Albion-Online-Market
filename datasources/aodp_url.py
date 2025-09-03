from __future__ import annotations

SERVER_BASE = {
    "west":   "https://west.albion-online-data.com",
    "east":   "https://east.albion-online-data.com",
    "europe": "https://europe.albion-online-data.com",
}
DEFAULT_CITIES = [
    "Bridgewatch","Caerleon","Fort Sterling","Lymhurst","Martlock","Thetford","Black Market"
]

def base_for(server: str | None) -> str:
    return SERVER_BASE.get((server or "europe").lower(), SERVER_BASE["europe"])

def build_prices_request(base: str, items: list[str], cities: list[str], quals_csv: str):
    """
    Returns (url, params) for v2 prices, with LOWERCASE path.
    We pass query via 'params=' so spaces get encoded correctly.
    """
    url = f"{base}/api/v2/stats/prices/{','.join(items)}.json"   # lowercase 'api/v2/stats/prices'
    params = {"locations": ",".join(cities), "qualities": quals_csv}
    return url, params
