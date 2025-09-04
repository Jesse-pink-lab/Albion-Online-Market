import importlib.util
import pathlib


def test_paths_import_fallback(monkeypatch):
    """platformdirs and appdirs missing -> fallback function works."""
    orig_find_spec = importlib.util.find_spec

    def fake_find_spec(name, *args, **kwargs):
        if name in {"platformdirs", "appdirs"}:
            return None
        return orig_find_spec(name, *args, **kwargs)

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)

    spec = importlib.util.spec_from_file_location(
        "tmp_paths",
        pathlib.Path(__file__).resolve().parents[1] / "utils" / "paths.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[operator]

    path = mod.user_data_dir("TestApp", "Vendor")
    assert "TestApp" in path
