import json
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from .paths import get_data_dir, get_example_data_dir

logger = logging.getLogger(__name__)


class JsonFileStore:
    """Read/write a single JSON file; seeds from data.example/ when missing."""

    def __init__(
        self,
        filename: str,
        data_dir: Optional[Path] = None,
        example_dir: Optional[Path] = None,
    ):
        self.filename = filename
        self.data_dir = data_dir or get_data_dir()
        self.example_dir = example_dir or get_example_data_dir()
        self.path = self.data_dir / filename
        self.example_path = self.example_dir / filename

    def load(self) -> Dict[str, Any]:
        self.ensure_exists()
        with self.path.open(encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError(f"Expected object in {self.path}")
        return data

    def save(self, data: Dict[str, Any]) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

    def ensure_exists(self) -> None:
        if self.path.exists():
            return

        self.data_dir.mkdir(parents=True, exist_ok=True)
        if self.example_path.exists():
            shutil.copy2(self.example_path, self.path)
            logger.info("Seeded %s from %s", self.path, self.example_path)
        else:
            self.save({})
            logger.warning("Created empty %s (no example at %s)", self.path, self.example_path)
