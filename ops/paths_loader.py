import json
from pathlib import Path

CONFIG = None


def load_config():
    global CONFIG
    if CONFIG is not None:
        return CONFIG
    p = Path(__file__).parent / "paths_config.json"
    if not p.exists():
        CONFIG = {}
    else:
        try:
            CONFIG = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            CONFIG = {}
    return CONFIG


def get_path(name):
    cfg = load_config()
    return cfg.get(name)
