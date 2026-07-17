"""Canary test (T-001): core modules import without starting the server.

If any of these imports executes side effects that bind sockets or spawn
threads at import time, this test is the tripwire.
"""
import importlib


def test_import_chain_models():
    assert importlib.import_module("chain.models") is not None


def test_import_session_manager():
    assert importlib.import_module("actions.session_manager") is not None


def test_import_server_module():
    """Importing server must not start Flask; it only defines main()."""
    mod = importlib.import_module("server")
    assert hasattr(mod, "main") or hasattr(mod, "app")
