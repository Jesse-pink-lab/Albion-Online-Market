import pytest
from pathlib import Path

from utils import items


def test_load_catalog_io_fallback(monkeypatch, tmp_path):
    items.load_catalog.cache_clear()
    def bad_reader():
        raise FileNotFoundError("nope")
    monkeypatch.setattr(items, 'read_master_catalog', bad_reader)
    tmp = tmp_path / 'items.txt'
    tmp.write_text('A\nB\n')
    monkeypatch.setattr(items, 'CATALOG_FILE', tmp)
    assert items.load_catalog() == ['A', 'B']


def test_load_catalog_parse_error(monkeypatch):
    items.load_catalog.cache_clear()
    def bad_reader():
        raise ValueError('bad')
    monkeypatch.setattr(items, 'read_master_catalog', bad_reader)
    with pytest.raises(ValueError):
        items.load_catalog()
