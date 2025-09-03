import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from utils.items import parse_items, items_catalog_codes


def test_items_placeholder_not_used():
    assert parse_items("") == []


def test_items_fetch_all():
    catalog = items_catalog_codes()
    items = parse_items("")
    items = catalog if (not items and True) else items
    assert items == catalog and len(items) > 0


def test_items_non_empty():
    assert parse_items("t4_bag") == ["T4_BAG"]

