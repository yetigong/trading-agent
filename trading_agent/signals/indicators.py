"""Technical indicator calculations from price bars."""

from typing import List, Optional, Tuple

import pandas as pd


def compute_rsi(series: pd.Series, period: int = 14) -> Optional[float]:
    if len(series) < period + 1:
        return None
    delta = series.diff().dropna()
    gain = delta.clip(lower=0).rolling(window=period).mean()
    loss = (-delta.clip(upper=0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    value = rsi.iloc[-1]
    if pd.isna(value) and gain.iloc[-1] > 0:
        return 100.0
    return float(value) if pd.notna(value) else None


def compute_macd(
    series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> Tuple[Optional[float], Optional[float]]:
    if len(series) < slow + signal:
        return None, None
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    macd_val = macd_line.iloc[-1]
    signal_val = signal_line.iloc[-1]
    return (
        float(macd_val) if pd.notna(macd_val) else None,
        float(signal_val) if pd.notna(signal_val) else None,
    )


def compute_sma(series: pd.Series, window: int) -> Optional[float]:
    if len(series) < window:
        return None
    value = series.rolling(window=window).mean().iloc[-1]
    return float(value) if pd.notna(value) else None


def classify_trend(current: float, sma20: Optional[float], sma50: Optional[float]) -> str:
    if sma20 is None or sma50 is None:
        return "neutral"
    if current > sma20 > sma50:
        return "bullish"
    if current < sma20 < sma50:
        return "bearish"
    return "neutral"
