import sys, pathlib

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from utils.items import parse_items_input


def test_items_placeholder_not_used():
    items = parse_items_input("", False, [])
    assert items == []
