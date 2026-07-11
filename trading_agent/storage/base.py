import json
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generic, Optional, TypeVar

T = TypeVar("T")


class LocalFileStore(ABC, Generic[T]):
    """Read/write a single domain model to a JSON file."""

    def __init__(self, userdata_dir: Path, filename: str, example_dir: Optional[Path] = None):
        self.userdata_dir = userdata_dir
        self.filepath = userdata_dir / filename
        self.example_path = (example_dir / filename) if example_dir else None

    @abstractmethod
    def _from_dict(self, data: dict) -> T:
        pass

    @abstractmethod
    def _to_dict(self, model: T) -> dict:
        pass

    @abstractmethod
    def _default(self) -> T:
        pass

    def ensure_exists(self) -> None:
        self.userdata_dir.mkdir(parents=True, exist_ok=True)
        if self.filepath.exists():
            return
        if self.example_path and self.example_path.exists():
            shutil.copy(self.example_path, self.filepath)
        else:
            self.save(self._default())

    def load(self) -> T:
        self.ensure_exists()
        with open(self.filepath, encoding="utf-8") as f:
            return self._from_dict(json.load(f))

    def save(self, model: T) -> None:
        self.userdata_dir.mkdir(parents=True, exist_ok=True)
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self._to_dict(model), f, indent=2)
            f.write("\n")
