import sys, pathlib

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from utils.items import parse_items, load_catalog


def test_items_placeholder_not_used():
    assert parse_items("", False) == []


def test_items_fetch_all(monkeypatch):
    catalog = load_catalog()
    items = parse_items("", True)
    assert items == catalog and len(items) > 0
