import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def get_repo_root() -> Path:
    return _REPO_ROOT


def get_data_dir() -> Path:
    override = os.getenv("DATA_DIR")
    if override:
        return Path(override)
    return _REPO_ROOT / "data"


def get_example_data_dir() -> Path:
    override = os.getenv("EXAMPLE_DATA_DIR")
    if override:
        return Path(override)
    return _REPO_ROOT / "data.example"


def get_cache_dir(name: str) -> Path:
    override = os.getenv(f"{name.upper()}_CACHE_DIR")
    if override:
        return Path(override)
    return get_data_dir() / "cache" / name
