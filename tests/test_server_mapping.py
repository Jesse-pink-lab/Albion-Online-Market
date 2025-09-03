import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from datasources.aodp_url import base_for


def test_server_mapping_keys():
    assert base_for('west').startswith('https://west')
    assert base_for('east').startswith('https://east')
    assert base_for('europe').startswith('https://europe')
    # unknown keys fall back to europe
    assert base_for('americas').startswith('https://europe')
    assert base_for('asia').startswith('https://europe')
