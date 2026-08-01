import os
import sys
from pathlib import Path


def _app_dir() -> Path:
    """Folder holding the running .exe (once built) or the project root (running from source)."""
    if getattr(sys, "frozen", False):   # True inside a PyInstaller-built exe
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def _load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return values


_ENV_FILE_VALUES = _load_env_file(_app_dir() / "config.env")

def resource_path(relative_path: str) -> str:
    """
    Resolve a path to a bundled resource (e.g. assets/card_image.png) so it
    works both running from source and as a frozen PyInstaller onefile exe.
    Onefile mode extracts bundled data files to a temp folder at runtime
    (sys._MEIPASS), not next to the exe.
    """
    base = Path(getattr(sys, "_MEIPASS", _app_dir()))
    return str(base / relative_path)

def get_google_drive_api_key() -> str:
    """
    Prefer an actual environment variable (your dev setup); fall back to
    config.env sitting next to the exe (everyone else's setup — a plain
    text file is much easier to hand someone than "set an env var").
    """
    return os.environ.get("GOOGLE_DRIVE_API_KEY") or _ENV_FILE_VALUES.get("GOOGLE_DRIVE_API_KEY", "")