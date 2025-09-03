SERVER_BASE = {
  "west":   "https://west.albion-online-data.com",
  "east":   "https://east.albion-online-data.com",
  "europe": "https://europe.albion-online-data.com",
}
DEFAULT_CITIES = ["Bridgewatch","Caerleon","Fort Sterling","Lymhurst","Martlock","Thetford","Black Market"]

def base_for(server: str) -> str:
    return SERVER_BASE.get((server or "europe").lower(), SERVER_BASE["europe"])

def build_prices_url(base: str, items_csv: str, cities_csv: str, quals_csv: str) -> str:
    # endpoint path MUST be lowercase; params must be CSV
    return f"{base}/api/v2/stats/prices/{items_csv}.json?locations={cities_csv}&qualities={quals_csv}"
