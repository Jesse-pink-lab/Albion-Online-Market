from engine.config import ConfigManager


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
