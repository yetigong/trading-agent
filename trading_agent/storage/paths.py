import os
from pathlib import Path


def get_userdata_dir() -> Path:
    return Path(os.getenv("USERDATA_DIR", "userdata"))


def get_example_dir() -> Path:
    return Path(os.getenv("USERDATA_EXAMPLE_DIR", "userdata.example"))
