"""Industry-standard passive and simple active benchmarks."""

from __future__ import annotations

from datetime import date
from typing import Any, Callable, Dict, List, Optional, Sequence

import pandas as pd

from trading_agent.backtest.broker import BacktestBroker
from trading_agent.backtest.metrics import compute_metrics
from trading_agent.backtest.models import PerformanceMetrics
from trading_agent.market_data.alpaca_historical import read_cached_bars, slice_bars_as_of


PriceLookup = Callable[[str, date], Optional[float]]


def _price_from_cache(
    symbol: str,
    as_of: date,
    cache_dir=None,
) -> Optional[float]:
    bars = slice_bars_as_of(read_cached_bars(symbol, cache_dir), as_of)
    if bars is None or bars.empty:
        return None
    return float(bars["close"].iloc[-1])


def _equity_curve_buy_and_hold(
    allocations: Dict[str, float],
    trading_days: Sequence[date],
    initial_cash: float,
    price_fn: PriceLookup,
) -> List[Dict[str, Any]]:
    """Buy allocation weights on first day with available prices; hold thereafter."""
    if not trading_days:
        return []

    first_day = trading_days[0]
    shares: Dict[str, float] = {}
    cash = float(initial_cash)

    available = {}
    for symbol, weight in allocations.items():
        px = price_fn(symbol, first_day)
        if px is not None and px > 0:
            available[symbol] = (weight, px)

    weight_sum = sum(w for w, _ in available.values()) or 1.0
    for symbol, (weight, px) in available.items():
        spend = initial_cash * (weight / weight_sum)
        qty = int(spend // px)
        if qty > 0:
            shares[symbol] = qty
            cash -= qty * px

    curve: List[Dict[str, Any]] = []
    for day in trading_days:
        equity = cash
        for symbol, qty in shares.items():
            px = price_fn(symbol, day)
            if px is None:
                px = price_fn(symbol, first_day) or 0.0
            equity += qty * px
        curve.append({"date": day.isoformat(), "equity": equity, "cash": cash})
    return curve


def _sma_crossover_curve(
    symbol: str,
    trading_days: Sequence[date],
    initial_cash: float,
    price_fn: PriceLookup,
    fast: int = 20,
    slow: int = 50,
    bars_loader=None,
) -> List[Dict[str, Any]]:
    """Long when SMA(fast) > SMA(slow); otherwise cash."""
    if bars_loader is None:
        from trading_agent.market_data.alpaca_historical import read_cached_bars as bars_loader

    full = bars_loader(symbol)
    if full is None or full.empty or not trading_days:
        return [{"date": d.isoformat(), "equity": initial_cash, "cash": initial_cash} for d in trading_days]

    cash = float(initial_cash)
    shares = 0
    curve: List[Dict[str, Any]] = []

    for day in trading_days:
        hist = slice_bars_as_of(full, day)
        price = price_fn(symbol, day)
        if hist is None or len(hist) < slow or price is None:
            curve.append({"date": day.isoformat(), "equity": cash + shares * (price or 0), "cash": cash})
            continue

        sma_fast = float(hist["close"].rolling(window=fast).mean().iloc[-1])
        sma_slow = float(hist["close"].rolling(window=slow).mean().iloc[-1])
        bullish = sma_fast > sma_slow

        if bullish and shares == 0 and price > 0:
            shares = int(cash // price)
            cash -= shares * price
        elif not bullish and shares > 0:
            cash += shares * price
            shares = 0

        curve.append({
            "date": day.isoformat(),
            "equity": cash + shares * price,
            "cash": cash,
        })
    return curve


def run_benchmarks(
    trading_days: Sequence[date],
    initial_cash: float,
    price_fn: PriceLookup,
    universe: Optional[List[str]] = None,
    risk_free_rate: float = 0.04,
    cache_dir=None,
) -> List[PerformanceMetrics]:
    """Run SPY, QQQ, 60/40, SMA crossover, and equal-weight B&H benchmarks."""
    universe = [s.upper() for s in (universe or [])]

    def cached_price(symbol: str, day: date) -> Optional[float]:
        px = price_fn(symbol, day)
        if px is not None:
            return px
        return _price_from_cache(symbol, day, cache_dir)

    spy_curve = _equity_curve_buy_and_hold({"SPY": 1.0}, trading_days, initial_cash, cached_price)
    qqq_curve = _equity_curve_buy_and_hold({"QQQ": 1.0}, trading_days, initial_cash, cached_price)
    balanced = _equity_curve_buy_and_hold(
        {"SPY": 0.6, "AGG": 0.4},
        trading_days,
        initial_cash,
        cached_price,
    )
    sma_curve = _sma_crossover_curve("SPY", trading_days, initial_cash, cached_price)

    equal_alloc = {s: 1.0 for s in universe} if universe else {"SPY": 1.0}
    equal_curve = _equity_curve_buy_and_hold(equal_alloc, trading_days, initial_cash, cached_price)

    results = [
        compute_metrics("SPY buy-and-hold", spy_curve, initial_cash, risk_free_rate, spy_curve),
        compute_metrics("QQQ buy-and-hold", qqq_curve, initial_cash, risk_free_rate, spy_curve),
        compute_metrics("60/40 SPY/AGG", balanced, initial_cash, risk_free_rate, spy_curve),
        compute_metrics("SMA(20/50) SPY", sma_curve, initial_cash, risk_free_rate, spy_curve),
        compute_metrics("Equal-weight B&H", equal_curve, initial_cash, risk_free_rate, spy_curve),
    ]
    return results
