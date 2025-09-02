import logging
from pathlib import Path

from logging_config import get_logger
from services import albion_client


def test_backend_skips_launch_on_invalid(monkeypatch, tmp_path, caplog):
    get_logger('test')  # configure logging
    fake = tmp_path / 'albiondata-client.exe'
    fake.write_text('dummy')

    monkeypatch.setattr('utils.pecheck.is_valid_win64_exe', lambda p: (False, 'wrong machine 0x014C'))

    launched = {}
    def fake_launch(*args, **kwargs):
        launched['called'] = True
    monkeypatch.setattr('services.albion_client.launch_client', fake_launch)

    with caplog.at_level(logging.ERROR):
        client = albion_client.find_client(str(fake), str(tmp_path))
        if not client:
            logging.getLogger('backend').error("Albion Data Client not found or invalid. Install the 64-bit client under 'C:\\Program Files\\Albion Data Client\\' or set a valid path in Settings.")
        else:
            albion_client.launch_client(client)

    assert 'Albion Data Client not found or invalid' in caplog.text
    assert 'called' not in launched
