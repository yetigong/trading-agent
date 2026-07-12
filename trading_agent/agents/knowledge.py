"""File-backed knowledge base for Learner feedback (Phase 6 will replace with DB)."""

from typing import Any, Dict, List, Optional
from pathlib import Path

from trading_agent.storage.base import JsonFileStore

DEFAULT_KNOWLEDGE: Dict[str, Any] = {
    "lessons": [],
    "signal_weights": {},
    "strategy_preferences": {},
}


class KnowledgeBase:
    def __init__(
        self,
        filename: str = "knowledge_base.json",
        data_dir: Optional[Path] = None,
        example_dir: Optional[Path] = None,
    ):
        self._store = JsonFileStore(filename, data_dir=data_dir, example_dir=example_dir)

    def load(self) -> Dict[str, Any]:
        data = self._store.load()
        return {
            "lessons": list(data.get("lessons") or []),
            "signal_weights": dict(data.get("signal_weights") or {}),
            "strategy_preferences": dict(data.get("strategy_preferences") or {}),
        }

    def save(self, data: Dict[str, Any]) -> None:
        payload = {
            "lessons": list(data.get("lessons") or []),
            "signal_weights": dict(data.get("signal_weights") or {}),
            "strategy_preferences": dict(data.get("strategy_preferences") or {}),
        }
        self._store.save(payload)

    def lessons(self, limit: int = 10) -> List[str]:
        lessons = self.load()["lessons"]
        return lessons[-limit:]

    def signal_weights(self) -> Dict[str, float]:
        return self.load()["signal_weights"]

    def strategy_preferences(self) -> Dict[str, Any]:
        return self.load()["strategy_preferences"]

    def append_lesson(self, lesson: str, max_lessons: int = 100) -> None:
        data = self.load()
        data["lessons"].append(lesson)
        data["lessons"] = data["lessons"][-max_lessons:]
        self.save(data)

    def update_weights_and_prefs(
        self,
        signal_weights: Optional[Dict[str, float]] = None,
        strategy_preferences: Optional[Dict[str, Any]] = None,
    ) -> None:
        data = self.load()
        if signal_weights is not None:
            data["signal_weights"].update(signal_weights)
        if strategy_preferences is not None:
            data["strategy_preferences"].update(strategy_preferences)
        self.save(data)
