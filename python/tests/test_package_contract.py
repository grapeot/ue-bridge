import importlib

from ue_bridge import Connection, UEBridge, UECommandError, UEConnectionError


def test_canonical_package_exports_public_symbols():
    assert UEBridge is not None
    assert Connection is not None
    assert UECommandError is not None
    assert UEConnectionError is not None


def test_canonical_module_imports_resolve():
    assert importlib.import_module("ue_bridge.cli") is not None
    assert importlib.import_module("ue_bridge.bridge") is not None
    assert importlib.import_module("ue_bridge.connection") is not None


def test_legacy_src_import_still_works_for_compatibility():
    legacy = importlib.import_module("src")
    assert hasattr(legacy, "UEBridge")
