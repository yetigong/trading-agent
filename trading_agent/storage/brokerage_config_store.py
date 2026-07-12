from trading_agent.domain.user.brokerage_config import BrokerageConfig

from .base import JsonFileStore


class BrokerageConfigStore(JsonFileStore):
    def __init__(self, **kwargs):
        super().__init__("brokerage_config.json", **kwargs)

    def load_config(self) -> BrokerageConfig:
        return BrokerageConfig.from_dict(self.load())
