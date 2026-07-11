"""Pure-pandas technical indicator computations."""

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd


def compute_sma(close: pd.Series, window: int) -> Optional[float]:
    if close is None or len(close) < window:
        return None
    value = close.rolling(window=window).mean().iloc[-1]
    return None if pd.isna(value) else float(value)


def compute_rsi(close: pd.Series, period: int = 14) -> Optional[float]:
    if close is None or len(close) < period + 1:
        return None

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    value = rsi.iloc[-1]
    if pd.isna(value):
        if avg_loss.iloc[-1] == 0 and avg_gain.iloc[-1] > 0:
            return 100.0
        return None
    return float(value)


def compute_macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> Dict[str, Optional[float]]:
    empty = {"macd": None, "signal": None, "histogram": None}
    if close is None or len(close) < slow + signal_period:
        return empty

    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    histogram = macd_line - signal_line

    macd_val = macd_line.iloc[-1]
    signal_val = signal_line.iloc[-1]
    hist_val = histogram.iloc[-1]

    if pd.isna(macd_val) or pd.isna(signal_val) or pd.isna(hist_val):
        return empty

    return {
        "macd": float(macd_val),
        "signal": float(signal_val),
        "histogram": float(hist_val),
    }


def compute_indicators_for_bars(bars: pd.DataFrame) -> Dict[str, Any]:
    """Compute RSI, MACD, and SMAs from a bars DataFrame with a 'close' column."""
    if bars is None or bars.empty or "close" not in bars.columns:
        return {}

    close = bars["close"]
    macd = compute_macd(close)

    result: Dict[str, Any] = {}
    rsi = compute_rsi(close)
    if rsi is not None:
        result["rsi_14"] = round(rsi, 2)

    sma_20 = compute_sma(close, 20)
    sma_50 = compute_sma(close, 50)
    if sma_20 is not None:
        result["sma_20"] = round(sma_20, 2)
    if sma_50 is not None:
        result["sma_50"] = round(sma_50, 2)

    if any(v is not None for v in macd.values()):
        result["macd"] = {k: round(v, 4) if v is not None else None for k, v in macd.items()}

    return result


def summarize_technical_indicators(indicators: Dict[str, Any]) -> str:
    """Build a human-readable summary from per-symbol indicator dicts."""
    if not indicators:
        return "Technical indicators unavailable."

    parts = []
    for symbol, data in indicators.items():
        if not isinstance(data, dict) or not data:
            continue
        pieces = []
        if "rsi_14" in data:
            rsi = data["rsi_14"]
            zone = "overbought" if rsi > 70 else "oversold" if rsi < 30 else "neutral"
            pieces.append(f"RSI={rsi} ({zone})")
        macd = data.get("macd")
        if isinstance(macd, dict) and macd.get("histogram") is not None:
            bias = "bullish" if macd["histogram"] > 0 else "bearish"
            pieces.append(f"MACD hist={macd['histogram']} ({bias})")
        if "sma_20" in data and "sma_50" in data:
            pieces.append(f"SMA20={data['sma_20']}, SMA50={data['sma_50']}")
        if pieces:
            parts.append(f"{symbol}: {', '.join(pieces)}")

    return "; ".join(parts) if parts else "Technical indicators unavailable."
