import pytest
from pathlib import Path

from engine.config import ConfigManager, ConfigError


def test_server_default_and_roundtrip(tmp_path):
    cfg_path = tmp_path / 'config.yaml'
    cm = ConfigManager(config_path=str(cfg_path))
    cfg = cm.load_config()
    assert cfg['aodp']['server'] == 'europe'
    cfg['uploader']['enabled'] = False
    cfg['logging']['level'] = 'DEBUG'
    cm.save_config(cfg)
    cm2 = ConfigManager(config_path=str(cfg_path))
    loaded = cm2.load_config()
    assert loaded['uploader']['enabled'] is False
    assert loaded['logging']['level'] == 'DEBUG'


def test_load_missing_returns_defaults(tmp_path):
    cfg_path = tmp_path / 'missing.yaml'
    cm = ConfigManager(config_path=str(cfg_path))
    assert cm.load_config() == cm.get_default_config()


def test_corrupt_yaml_raises(tmp_path):
    cfg_path = tmp_path / 'cfg.yaml'
    cfg_path.write_text('[')
    cm = ConfigManager(config_path=str(cfg_path))
    with pytest.raises(ConfigError):
        cm.load_config()


def test_permission_error(monkeypatch, tmp_path):
    cfg_path = tmp_path / 'cfg.yaml'
    cfg_path.write_text('x')
    cm = ConfigManager(config_path=str(cfg_path))

    def bad_open(*a, **k):
        raise PermissionError("nope")

    monkeypatch.setattr(Path, 'open', lambda self, *a, **k: bad_open())
    with pytest.raises(ConfigError):
        cm.load_config()
