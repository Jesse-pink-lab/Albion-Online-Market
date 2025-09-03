import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from utils.params import qualities_to_csv


def test_qualities_to_csv_label():
    assert qualities_to_csv('Normal (1)') == '1'


def test_qualities_to_csv_all():
    assert qualities_to_csv('All') == '1,2,3,4,5'


def test_qualities_to_csv_preserves_digits():
    assert qualities_to_csv('1,2,3') == '1,2,3'

