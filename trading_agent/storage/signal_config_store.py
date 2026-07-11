from trading_agent.domain.user.signal_config import SignalConfig

from .base import JsonFileStore


class SignalConfigStore(JsonFileStore):
    def __init__(self, **kwargs):
        super().__init__("signal_config.json", **kwargs)

    def load_config(self) -> SignalConfig:
        return SignalConfig.from_dict(self.load())
