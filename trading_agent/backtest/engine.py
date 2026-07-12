"""Backtest engine — replay TradingAgent over a historical period."""

from __future__ import annotations

import logging
import time
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from trading_agent.backtest.benchmarks import _equity_curve_buy_and_hold, run_benchmarks
from trading_agent.backtest.broker import BacktestBroker
from trading_agent.backtest.metrics import compute_metrics
from trading_agent.backtest.models import BacktestConfig, BacktestRun
from trading_agent.backtest.status import (
    equity_deployment,
    last_trade_date,
    resolve_run_status,
    summarize_cycles,
)
from trading_agent.llm.client import build_llm_client
from trading_agent.llm.failover_client import FailoverLLMClient
from trading_agent.market_data.alpaca_historical import (
    DEFAULT_INDICES,
    HistoricalAlpacaProvider,
    fetch_and_cache_bars,
    get_alpaca_cache_dir,
)
from trading_agent.market_data.finnhub_historical import (
    HistoricalFinnhubProvider,
    fetch_and_cache_news,
    get_finnhub_cache_dir,
)
from trading_agent.market_data.mock_fundamentals_provider import MockFundamentalsProvider
from trading_agent.orchestrator.agent import TradingAgent

logger = logging.getLogger(__name__)


def select_rebalance_dates(
    trading_days: Sequence[date],
    frequency: str = "weekly",
) -> List[date]:
    if not trading_days:
        return []
    if frequency == "daily":
        return list(trading_days)

    # Weekly: last trading day of each ISO week
    by_week: Dict[tuple, date] = {}
    for day in trading_days:
        key = day.isocalendar()[:2]
        by_week[key] = day
    return sorted(by_week.values())


def ensure_historical_data(
    symbols: List[str],
    start: date,
    end: date,
    refresh: bool = False,
    alpaca_cache_dir: Optional[Path] = None,
    finnhub_cache_dir: Optional[Path] = None,
    fetch_bars: bool = True,
    fetch_news: bool = True,
) -> Dict[str, Any]:
    """Prefetch bars and news into per-provider caches."""
    bar_symbols = sorted(set(symbols) | set(DEFAULT_INDICES) | {"AGG"})
    result: Dict[str, Any] = {"bars": None, "news": None}

    if fetch_bars:
        result["bars"] = fetch_and_cache_bars(
            bar_symbols,
            start,
            end,
            cache_dir=alpaca_cache_dir,
            refresh=refresh,
        )
    if fetch_news:
        result["news"] = fetch_and_cache_news(
            symbols,
            start,
            end,
            cache_dir=finnhub_cache_dir,
            refresh=refresh,
        )
    return result


class BacktestEngine:
    """Run the live TradingAgent pipeline over historical rebalance dates."""

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        skip_data_fetch: bool = False,
    ):
        self.llm_client = llm_client
        self.skip_data_fetch = skip_data_fetch

    def run(self, config: BacktestConfig) -> BacktestRun:
        run_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        notes = [
            "FMP fundamentals are TTM snapshots (not true point-in-time) — using mock/empty slice in backtest.",
        ]

        alpaca_cache = Path(config.alpaca_cache_dir) if config.alpaca_cache_dir else get_alpaca_cache_dir()
        finnhub_cache = Path(config.finnhub_cache_dir) if config.finnhub_cache_dir else get_finnhub_cache_dir()

        prefs = config.preferences or {}
        sector_etfs = list((config.signal_config or {}).get("sector_etfs") or [])

        symbols = [s.upper() for s in config.symbols]
        if not symbols:
            symbols = list(config.seed_positions.keys()) or ["AAPL"]

        try:
            if not self.skip_data_fetch:
                ensure_historical_data(
                    symbols=symbols + sector_etfs,
                    start=config.start,
                    end=config.end,
                    refresh=config.refresh_cache,
                    alpaca_cache_dir=alpaca_cache,
                    finnhub_cache_dir=finnhub_cache,
                )

            market = HistoricalAlpacaProvider(
                as_of_date=config.start,
                cache_dir=alpaca_cache,
                sector_etfs=sector_etfs or None,
            )
            news = HistoricalFinnhubProvider(
                as_of_date=config.start,
                cache_dir=finnhub_cache,
            )

            trading_days = market.trading_days(config.start, config.end)
            if not trading_days:
                return BacktestRun(
                    run_id=run_id,
                    timestamp=timestamp,
                    config=config.to_dict(),
                    status="failed",
                    error="No trading days found in cached bars for the requested period",
                    notes=notes,
                )

            rebalance_dates = set(
                select_rebalance_dates(trading_days, config.rebalance_frequency)
            )

            def price_fn(symbol: str) -> Optional[float]:
                return market.get_close_price(symbol)

            broker = BacktestBroker(
                initial_cash=config.initial_cash,
                seed_positions=config.seed_positions,
                price_fn=price_fn,
            )
            broker.set_as_of_date(trading_days[0])

            llm: Optional[Any] = self.llm_client
            if llm is None and not config.skip_llm:
                llm = build_llm_client(
                    provider=config.llm_provider,
                    model=config.llm_model,
                    fallback_provider=config.llm_fallback_provider,
                    fallback_model=config.llm_fallback_model,
                    max_retries=config.llm_max_retries,
                )

            agent = None
            if not config.skip_llm:
                max_position_size = float(prefs.get("max_position_size", 0.25))
                agent = TradingAgent(
                    risk_tolerance=prefs.get("risk_tolerance", "moderate"),
                    investment_goal=prefs.get("investment_goal", "growth"),
                    max_position_size=max_position_size,
                    llm_client=llm,
                    market_data_provider=market,
                    news_provider=news,
                    fundamentals_provider=MockFundamentalsProvider(metrics={}),
                    broker_client=broker,
                    universe_symbols=symbols,
                    # Prevent per-cycle learner writes from polluting live KB.
                    disabled=["learner"],
                )

            equity_curve: List[Dict[str, Any]] = []
            trade_log: List[Dict[str, Any]] = []
            cycle_summaries: List[Dict[str, Any]] = []

            for day in trading_days:
                market.set_as_of_date(day)
                news.set_as_of_date(day)
                broker.set_as_of_date(day)

                if agent is not None and day in rebalance_dates:
                    cycle_result = agent.run_trading_cycle(
                        analysis_params=config.analysis_params,
                        strategy_params=config.strategy_params,
                        rebalance_params=config.rebalance_params,
                    )
                    llm_meta: Dict[str, Any] = {}
                    if isinstance(llm, FailoverLLMClient):
                        llm_meta = llm.stats()
                    cycle_summaries.append({
                        "date": day.isoformat(),
                        "cycle_id": cycle_result.get("cycle_id"),
                        "status": cycle_result.get("status"),
                        "hold": cycle_result.get("hold"),
                        "decisions": cycle_result.get("decisions") or [],
                        "executed_trades": cycle_result.get("executed_trades") or [],
                        "error": cycle_result.get("error"),
                        "llm": llm_meta,
                    })
                    for trade in cycle_result.get("executed_trades") or []:
                        if trade.get("status") != "executed":
                            continue
                        trade_log.append({
                            "date": day.isoformat(),
                            "symbol": trade.get("symbol"),
                            "side": trade.get("action"),
                            "qty": trade.get("quantity"),
                            "price": market.get_close_price(str(trade.get("symbol") or "")) or 0.0,
                            "reasoning": trade.get("reasoning") or "",
                        })
                    if config.llm_pause_seconds > 0:
                        time.sleep(config.llm_pause_seconds)

                equity_curve.append({
                    "date": day.isoformat(),
                    "equity": broker.equity,
                    "cash": broker.cash,
                })

            def bench_price(symbol: str, day: date) -> Optional[float]:
                market.set_as_of_date(day)
                return market.get_close_price(symbol)

            benchmarks = run_benchmarks(
                trading_days,
                config.initial_cash,
                price_fn=bench_price,
                universe=symbols,
                risk_free_rate=config.risk_free_rate,
                cache_dir=alpaca_cache,
            )
            spy_curve = _equity_curve_buy_and_hold(
                {"SPY": 1.0},
                trading_days,
                config.initial_cash,
                bench_price,
            )
            strategy_metrics = compute_metrics(
                name=f"LLM strategy ({config.run_label})",
                curve=equity_curve,
                initial_cash=config.initial_cash,
                risk_free_rate=config.risk_free_rate,
                spy_curve=spy_curve,
                trade_count=len(trade_log),
            )

            cycle_stats = summarize_cycles(cycle_summaries)
            status, status_detail = resolve_run_status(cycle_summaries)
            deployment = equity_deployment(equity_curve)
            if status_detail:
                notes.append(status_detail)
            if isinstance(llm, FailoverLLMClient):
                notes.append(f"LLM failover stats: {llm.stats()}")

            run_config = config.to_dict()
            run_config["cycle_stats"] = cycle_stats
            run_config["deployment"] = deployment
            run_config["last_trade_date"] = last_trade_date(trade_log)

            return BacktestRun(
                run_id=run_id,
                timestamp=timestamp,
                config=run_config,
                status=status,
                equity_curve=equity_curve,
                trade_log=trade_log,
                cycle_summaries=cycle_summaries,
                metrics=strategy_metrics.to_dict(),
                benchmarks=[b.to_dict() for b in benchmarks],
                notes=notes,
                error=status_detail if status == "failed" else None,
            )

        except Exception as exc:
            logger.exception("Backtest failed")
            return BacktestRun(
                run_id=run_id,
                timestamp=timestamp,
                config=config.to_dict(),
                status="failed",
                error=str(exc),
                notes=notes,
            )
