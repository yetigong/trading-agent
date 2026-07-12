"""Performance metrics for backtest equity curves."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from trading_agent.backtest.models import PerformanceMetrics


def _equity_series(curve: Sequence[Dict[str, Any]]) -> np.ndarray:
    return np.array([float(p["equity"]) for p in curve], dtype=float)


def daily_returns(curve: Sequence[Dict[str, Any]]) -> np.ndarray:
    equities = _equity_series(curve)
    if len(equities) < 2:
        return np.array([], dtype=float)
    return np.diff(equities) / equities[:-1]


def total_return(curve: Sequence[Dict[str, Any]], initial_cash: Optional[float] = None) -> float:
    if not curve:
        return 0.0
    start = float(initial_cash) if initial_cash is not None else float(curve[0]["equity"])
    end = float(curve[-1]["equity"])
    if start == 0:
        return 0.0
    return (end - start) / start


def cagr(curve: Sequence[Dict[str, Any]], initial_cash: Optional[float] = None) -> float:
    if len(curve) < 2:
        return 0.0
    start = float(initial_cash) if initial_cash is not None else float(curve[0]["equity"])
    end = float(curve[-1]["equity"])
    if start <= 0 or end <= 0:
        return 0.0
    days = max(len(curve) - 1, 1)
    years = days / 252.0
    if years <= 0:
        return 0.0
    return float((end / start) ** (1 / years) - 1)


def max_drawdown(curve: Sequence[Dict[str, Any]]) -> float:
    equities = _equity_series(curve)
    if len(equities) == 0:
        return 0.0
    peak = equities[0]
    max_dd = 0.0
    for value in equities:
        if value > peak:
            peak = value
        if peak > 0:
            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd
    return float(max_dd)


def volatility(curve: Sequence[Dict[str, Any]]) -> float:
    rets = daily_returns(curve)
    if len(rets) < 2:
        return 0.0
    return float(np.std(rets, ddof=1) * np.sqrt(252))


def sharpe_ratio(
    curve: Sequence[Dict[str, Any]],
    risk_free_rate: float = 0.04,
) -> float:
    rets = daily_returns(curve)
    if len(rets) < 2:
        return 0.0
    daily_rf = risk_free_rate / 252.0
    excess = rets - daily_rf
    std = float(np.std(excess, ddof=1))
    if std == 0:
        return 0.0
    return float(np.mean(excess) / std * np.sqrt(252))


def alpha_beta_vs_benchmark(
    strategy_curve: Sequence[Dict[str, Any]],
    benchmark_curve: Sequence[Dict[str, Any]],
) -> tuple:
    """Return (alpha, beta) using daily returns aligned by index order."""
    s = daily_returns(strategy_curve)
    b = daily_returns(benchmark_curve)
    n = min(len(s), len(b))
    if n < 2:
        return None, None
    s = s[-n:]
    b = b[-n:]
    var_b = float(np.var(b, ddof=1))
    if var_b == 0:
        return None, None
    cov = float(np.cov(s, b, ddof=1)[0, 1])
    beta = cov / var_b
    alpha = float((np.mean(s) - beta * np.mean(b)) * 252)
    return alpha, beta


def compute_metrics(
    name: str,
    curve: Sequence[Dict[str, Any]],
    initial_cash: float,
    risk_free_rate: float = 0.04,
    spy_curve: Optional[Sequence[Dict[str, Any]]] = None,
    trade_count: int = 0,
) -> PerformanceMetrics:
    alpha = None
    beta = None
    if spy_curve:
        alpha, beta = alpha_beta_vs_benchmark(curve, spy_curve)
    return PerformanceMetrics(
        name=name,
        total_return=total_return(curve, initial_cash),
        cagr=cagr(curve, initial_cash),
        max_drawdown=max_drawdown(curve),
        volatility=volatility(curve),
        sharpe=sharpe_ratio(curve, risk_free_rate),
        alpha_vs_spy=alpha,
        beta_vs_spy=beta,
        trade_count=trade_count,
    )
