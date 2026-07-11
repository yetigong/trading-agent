from pathlib import Path
from typing import Optional

from trading_agent.domain.user.watchlist import Watchlist

from .base import LocalFileStore
from .paths import get_example_dir, get_userdata_dir


class WatchlistStore(LocalFileStore[Watchlist]):
    def __init__(self, userdata_dir: Optional[Path] = None):
        base = userdata_dir or get_userdata_dir()
        super().__init__(base, "watchlist.json", get_example_dir())

    def _from_dict(self, data: dict) -> Watchlist:
        return Watchlist.from_dict(data)

    def _to_dict(self, model: Watchlist) -> dict:
        return model.to_dict()

    def _default(self) -> Watchlist:
        return Watchlist.default()
