import os
import sys
from pathlib import Path

import pytest

from utils.pecheck import is_valid_win64_exe


def test_invalid_file_is_rejected(tmp_path):
    p = tmp_path / "bad.exe"
    p.write_text("Not an exe")
    valid, reason = is_valid_win64_exe(str(p))
    assert not valid
    assert reason == "not MZ"


@pytest.mark.skipif(os.name != 'nt', reason='windows only')
def test_known_windows_binary():
    path = Path(os.environ.get('WINDIR', r'C:\\Windows')) / 'System32' / 'notepad.exe'
    if not path.exists():
        pytest.skip('notepad.exe not available')
    valid, reason = is_valid_win64_exe(str(path))
    assert valid, reason
