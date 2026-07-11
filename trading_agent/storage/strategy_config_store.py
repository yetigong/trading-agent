from .base import JsonFileStore


class StrategyConfigStore(JsonFileStore):
    def __init__(self, **kwargs):
        super().__init__("strategy_params.json", **kwargs)
