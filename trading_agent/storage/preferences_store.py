from trading_agent.domain.user.user_preferences import UserPreferences

from .base import JsonFileStore


class PreferencesStore(JsonFileStore):
    def __init__(self, **kwargs):
        super().__init__("preferences.json", **kwargs)

    def load_preferences(self) -> UserPreferences:
        return UserPreferences.from_dict(self.load())
