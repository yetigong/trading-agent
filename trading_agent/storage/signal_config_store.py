from pathlib import Path
from typing import Optional

from trading_agent.domain.user.signal_config import SignalConfig

from .base import LocalFileStore
from .paths import get_example_dir, get_userdata_dir


class SignalConfigStore(LocalFileStore[SignalConfig]):
    def __init__(self, userdata_dir: Optional[Path] = None):
        base = userdata_dir or get_userdata_dir()
        super().__init__(base, "signal_config.json", get_example_dir())

    def _from_dict(self, data: dict) -> SignalConfig:
        return SignalConfig.from_dict(data)

    def _to_dict(self, model: SignalConfig) -> dict:
        return model.to_dict()

    def _default(self) -> SignalConfig:
        return SignalConfig.default()
