from pathlib import Path
from typing import Optional

from trading_agent.domain.user.user_preferences import UserPreferences

from .base import LocalFileStore
from .paths import get_example_dir, get_userdata_dir


class PreferencesStore(LocalFileStore[UserPreferences]):
    def __init__(self, userdata_dir: Optional[Path] = None):
        base = userdata_dir or get_userdata_dir()
        super().__init__(base, "preferences.json", get_example_dir())

    def _from_dict(self, data: dict) -> UserPreferences:
        return UserPreferences.from_dict(data)

    def _to_dict(self, model: UserPreferences) -> dict:
        return model.to_dict()

    def _default(self) -> UserPreferences:
        return UserPreferences.default()
