import json
from pathlib import Path
from datetime import datetime

CONFIG_DIR = Path.home() / ".config" / "bspwm-layout-manager"
LAYOUTS_FILE = CONFIG_DIR / "layouts.json"


def init_storage():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not LAYOUTS_FILE.exists():
        LAYOUTS_FILE.write_text(json.dumps({}))


def load_all() -> dict:
    init_storage()
    return json.loads(LAYOUTS_FILE.read_text())


def save_layout(name: str, layout: dict):
    layouts = load_all()
    layout["name"] = name
    layout["saved_at"] = datetime.now().isoformat()
    layouts[name] = layout
    LAYOUTS_FILE.write_text(json.dumps(layouts, indent=2))


def delete_layout(name: str) -> bool:
    layouts = load_all()
    if name not in layouts:
        return False
    del layouts[name]
    LAYOUTS_FILE.write_text(json.dumps(layouts, indent=2))
    return True


def get_layout(name: str) -> dict | None:
    return load_all().get(name)


def list_layouts() -> list[str]:
    return list(load_all().keys())
