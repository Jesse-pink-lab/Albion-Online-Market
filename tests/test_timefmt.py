from datetime import datetime, timedelta, timezone
import sys, pathlib

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from utils.timefmt import to_utc, rel_age, fmt_tooltip


def test_to_utc_parses_strings():
    dt = to_utc("2024-01-01T00:00:00")
    assert dt.tzinfo == timezone.utc
    assert fmt_tooltip(dt).endswith("Z")


def test_rel_age_formats():
    now = datetime.now(timezone.utc)
    assert rel_age(now - timedelta(seconds=59)) == "59s"
    assert rel_age(now - timedelta(minutes=2)) == "2m"


def test_rel_age_and_tooltip_accept_str():
    iso = "2024-01-02T03:04:05Z"
    assert fmt_tooltip(iso) == "2024-01-02 03:04:05Z"
    assert isinstance(rel_age(iso), str)
