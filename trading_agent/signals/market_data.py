import logging
from datetime import datetime, timedelta
from typing import List, Optional

import pandas as pd

from trading_agent.domain.signals.market_data import (
    IndexSnapshot,
    MarketDataPayload,
    SectorEtfSnapshot,
)
from trading_agent.domain.signals.signal_source_result import SignalSourceResult
from trading_agent.domain.signals.signal_status import SignalStatus
from trading_agent.market_data.base import MarketDataProvider
from trading_agent.signals.base import SignalProvider

logger = logging.getLogger(__name__)

SECTOR_ETFS = ["XLK", "XLV", "XLF", "XLE", "XLY", "XLP", "XLI", "XLB", "XLU", "XLRE"]


class MarketDataSignalProvider(SignalProvider):
    source_id = "market_data"

    def __init__(self, market_data_provider: MarketDataProvider):
        self.market_data_provider = market_data_provider

    @property
    def source_id(self) -> str:
        return "market_data"

    def fetch(self, symbols: List[str]) -> SignalSourceResult:
        now = datetime.now()
        try:
            conditions = self.market_data_provider.get_market_conditions()
            indices = []
            for sym, data in (conditions.get("indices") or {}).items():
                if isinstance(data, dict):
                    indices.append(
                        IndexSnapshot(
                            symbol=sym,
                            current_price=float(data.get("current_price", 0)),
                            daily_change=float(data.get("daily_change", 0)),
                            volume=float(data["volume"]) if data.get("volume") is not None else None,
                        )
                    )

            sector_etfs = self._fetch_sector_etfs()

            payload = MarketDataPayload(
                volatility=str(conditions.get("volatility", "unknown")),
                trend=str(conditions.get("trend", "unknown")),
                economic_cycle=str(conditions.get("economic_cycle", "unknown")),
                market_phase=str(conditions.get("market_phase", "unknown")),
                indices=indices,
                sector_etfs=sector_etfs,
                sentiment=conditions.get("sentiment"),
                timestamp=conditions.get("timestamp") or now,
            )
            return SignalSourceResult(
                source_id=self.source_id,
                status=SignalStatus.SUCCESS,
                timestamp=now,
                symbols=symbols,
                payload=payload,
            )
        except Exception as exc:
            logger.exception("Market data signal fetch failed")
            return SignalSourceResult(
                source_id=self.source_id,
                status=SignalStatus.FAILED,
                timestamp=now,
                symbols=symbols,
                payload=None,
                error=str(exc),
            )

    def _fetch_sector_etfs(self) -> List[SectorEtfSnapshot]:
        fetch_bars = getattr(self.market_data_provider, "get_daily_bars", None)
        if not fetch_bars:
            return []
        snapshots = []
        for etf in SECTOR_ETFS:
            try:
                df = fetch_bars(etf, days=5)
                if df is not None and len(df) >= 2:
                    change = (df["close"].iloc[-1] / df["close"].iloc[-2] - 1) * 100
                    snapshots.append(SectorEtfSnapshot(symbol=etf, daily_change=float(change)))
            except Exception:
                continue
        return snapshots
