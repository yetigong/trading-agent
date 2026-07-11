from .base import JsonFileStore


class RebalanceConfigStore(JsonFileStore):
    def __init__(self, **kwargs):
        super().__init__("rebalance_params.json", **kwargs)
