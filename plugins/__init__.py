# Hermes plugins package & DevMind Marketplace Engine
import importlib.util
import sys
from pathlib import Path

try:
    _plugins_py = Path(__file__).parent.parent / "plugins.py"
    if _plugins_py.exists():
        _spec = importlib.util.spec_from_file_location("_plugins_root_module", str(_plugins_py))
        _mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        plugin_engine = getattr(_mod, "plugin_engine", None)
    else:
        plugin_engine = None
except Exception:
    plugin_engine = None
