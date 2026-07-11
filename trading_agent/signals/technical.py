import logging
from datetime import datetime
from typing import List, Optional

from trading_agent.domain.signals.signal_source_result import SignalSourceResult
from trading_agent.domain.signals.signal_status import SignalStatus
from trading_agent.domain.signals.technical import SymbolIndicators, TechnicalPayload
from trading_agent.market_data.base import MarketDataProvider
from trading_agent.signals.base import SignalProvider
from trading_agent.signals.indicators import (
    classify_trend,
    compute_macd,
    compute_rsi,
    compute_sma,
)

logger = logging.getLogger(__name__)


class TechnicalSignalProvider(SignalProvider):
    def __init__(self, market_data_provider: MarketDataProvider):
        self.market_data_provider = market_data_provider

    @property
    def source_id(self) -> str:
        return "technical"

    def fetch(self, symbols: List[str]) -> SignalSourceResult:
        now = datetime.now()
        fetch_bars = getattr(self.market_data_provider, "get_daily_bars", None)
        if not fetch_bars:
            return SignalSourceResult(
                source_id=self.source_id,
                status=SignalStatus.FAILED,
                timestamp=now,
                symbols=symbols,
                payload=TechnicalPayload(),
                error="Market data provider does not support daily bars",
            )

        indicators: List[SymbolIndicators] = []
        errors = 0
        for symbol in symbols:
            try:
                df = fetch_bars(symbol, days=120)
                if df is None or df.empty:
                    errors += 1
                    continue
                close = df["close"]
                current = float(close.iloc[-1])
                sma20 = compute_sma(close, 20)
                sma50 = compute_sma(close, 50)
                rsi = compute_rsi(close)
                macd, macd_signal = compute_macd(close)
                indicators.append(
                    SymbolIndicators(
                        symbol=symbol,
                        rsi=rsi,
                        macd=macd,
                        macd_signal=macd_signal,
                        sma20=sma20,
                        sma50=sma50,
                        trend=classify_trend(current, sma20, sma50),
                        current_price=current,
                    )
                )
            except Exception:
                errors += 1
                logger.exception("Failed technical indicators for %s", symbol)

        status = SignalStatus.SUCCESS
        if errors and indicators:
            status = SignalStatus.PARTIAL
        elif errors and not indicators:
            status = SignalStatus.FAILED

        return SignalSourceResult(
            source_id=self.source_id,
            status=status,
            timestamp=now,
            symbols=symbols,
            payload=TechnicalPayload(symbols=indicators),
            error=f"{errors} symbol(s) failed" if errors else None,
        )
