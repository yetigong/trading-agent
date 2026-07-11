from trading_agent.domain.user.watchlist import Watchlist

from .base import JsonFileStore


class WatchlistStore(JsonFileStore):
    def __init__(self, **kwargs):
        super().__init__("watchlist.json", **kwargs)

    def load_watchlist(self) -> Watchlist:
        return Watchlist.from_dict(self.load())
