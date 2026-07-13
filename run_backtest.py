#!/usr/bin/env python3
"""Manual entry point for Phase 3 backtesting."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Optional

from trading_agent.backtest.comparison import compare_runs, format_comparison
from trading_agent.backtest.engine import BacktestEngine, ensure_historical_data
from trading_agent.backtest.models import BacktestConfig
from trading_agent.backtest.status import equity_deployment, last_trade_date, summarize_cycles
from trading_agent.config import config_summary, get_config, validate_config
from trading_agent.models import serialize_for_json
from trading_agent.storage import (
    AnalysisConfigStore,
    PreferencesStore,
    RebalanceConfigStore,
    SignalConfigStore,
    StrategyConfigStore,
    WatchlistStore,
)

LOG_DIR = Path("logs")


def setup_logging(log_level: str) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_DIR / "trading_agent.log"),
        ],
        force=True,
    )


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _load_json_arg(raw: Optional[str]) -> Dict[str, Any]:
    if not raw:
        return {}
    return json.loads(raw)


def build_config_from_stores(args) -> BacktestConfig:
    preferences = PreferencesStore().load_preferences().to_dict()
    analysis_params = AnalysisConfigStore().load()
    strategy_params = StrategyConfigStore().load()
    rebalance_params = RebalanceConfigStore().load()
    signal_config = SignalConfigStore().load_config().to_dict()
    watchlist = WatchlistStore().load_watchlist()

    strategy_params = {**strategy_params, **_load_json_arg(args.override_strategy)}
    analysis_params = {**analysis_params, **_load_json_arg(args.override_analysis)}
    preferences = {**preferences, **_load_json_arg(args.override_preferences)}

    symbols = []
    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    elif watchlist.symbols:
        symbols = [s.upper() for s in watchlist.symbols]
    else:
        symbols = ["AAPL"]

    app_config = get_config()
    return BacktestConfig(
        start=_parse_date(args.start),
        end=_parse_date(args.end),
        initial_cash=args.initial_cash,
        rebalance_frequency=args.rebalance,
        run_label=args.run_label,
        symbols=symbols,
        risk_free_rate=args.risk_free_rate,
        refresh_cache=args.refresh,
        analysis_params=analysis_params,
        strategy_params=strategy_params,
        rebalance_params=rebalance_params,
        preferences=preferences,
        signal_config=signal_config,
        llm_provider=app_config.llm_provider,
        llm_model=app_config.llm_model,
        llm_fallback_provider=app_config.llm_fallback_provider,
        llm_fallback_model=app_config.llm_fallback_model,
        llm_max_retries=app_config.llm_max_retries,
        llm_pause_seconds=args.llm_pause_seconds,
    )


def save_artifact(run_dict: Dict[str, Any], run_label: str) -> Path:
    LOG_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_label = "".join(c if c.isalnum() or c in "-_" else "_" for c in run_label) or "run"
    path = LOG_DIR / f"backtest_{timestamp}_{safe_label}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(serialize_for_json(run_dict), f, indent=2)
        f.write("\n")
    return path


def print_summary(run_dict: Dict[str, Any]) -> None:
    print("\n" + "=" * 72)
    print("BACKTEST SUMMARY")
    print("=" * 72)
    status = run_dict.get("status")
    print(f"Status: {status}")
    print(f"Run ID: {run_dict.get('run_id')}")
    if status == "failed" and run_dict.get("error"):
        print(f"Error: {run_dict.get('error')}")

    config = run_dict.get("config") or {}
    cycle_stats = config.get("cycle_stats") or summarize_cycles(
        run_dict.get("cycle_summaries") or []
    )
    deployment = config.get("deployment") or equity_deployment(
        run_dict.get("equity_curve") or []
    )
    trade_date = config.get("last_trade_date") or last_trade_date(
        run_dict.get("trade_log") or []
    )

    if cycle_stats.get("cycles_total"):
        print(
            f"Cycles: {cycle_stats.get('cycles_ok', 0)}/"
            f"{cycle_stats.get('cycles_total', 0)} succeeded "
            f"({float(cycle_stats.get('cycle_success_rate') or 0) * 100:.0f}%)"
        )
    else:
        print(f"Cycles: {len(run_dict.get('cycle_summaries') or [])}")

    if trade_date:
        print(f"Last trade date: {trade_date}")
    if deployment.get("cash_pct") is not None:
        print(
            f"End cash: {_pct(deployment.get('cash_pct'))} "
            f"(invested {_pct(deployment.get('invested_pct'))})"
        )

    if status == "failed" and not (run_dict.get("metrics") or {}):
        for note in run_dict.get("notes") or []:
            print(f"Note: {note}")
        print("=" * 72)
        return

    metrics = run_dict.get("metrics") or {}
    if metrics:
        print(f"Strategy: {metrics.get('name')}")
        print(f"Total return: {_pct(metrics.get('total_return'))}")
        print(f"CAGR: {_pct(metrics.get('cagr'))}")
        print(f"Max drawdown: {_pct(metrics.get('max_drawdown'))}")
        print(f"Sharpe: {_num(metrics.get('sharpe'))}")
        print(f"Alpha vs SPY: {_pct(metrics.get('alpha_vs_spy'))}")
        print(f"Trades: {metrics.get('trade_count', 0)}")

    if status in ("success", "degraded") and (run_dict.get("benchmarks") or []):
        if status == "degraded":
            print("\nWARNING: Run is degraded — do not treat benchmark comparison as authoritative.")
        print("\nBenchmarks:")
        print(f"  {'Name':<22} {'Return':>10} {'MaxDD':>10} {'Sharpe':>10}")
        for bench in run_dict.get("benchmarks") or []:
            print(
                f"  {str(bench.get('name')):<22} "
                f"{_pct(bench.get('total_return')):>10} "
                f"{_pct(bench.get('max_drawdown')):>10} "
                f"{_num(bench.get('sharpe')):>10}"
            )
    for note in run_dict.get("notes") or []:
        print(f"Note: {note}")
    print("=" * 72)


def _pct(value) -> str:
    if value is None:
        return "n/a"
    return f"{float(value) * 100:.2f}%"


def _num(value) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2f}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run or compare trading-agent backtests")
    parser.add_argument("--start", help="Backtest start date YYYY-MM-DD")
    parser.add_argument("--end", help="Backtest end date YYYY-MM-DD")
    parser.add_argument("--rebalance", choices=["weekly", "daily"], default="weekly")
    parser.add_argument("--initial-cash", type=float, default=100_000.0)
    parser.add_argument("--risk-free-rate", type=float, default=0.04)
    parser.add_argument("--symbols", help="Comma-separated symbols (default: watchlist or AAPL)")
    parser.add_argument("--run-label", default="default", help="Label stored in the artifact")
    parser.add_argument("--refresh", action="store_true", help="Refresh historical caches")
    parser.add_argument("--prefetch-only", action="store_true", help="Only prefetch historical data")
    parser.add_argument(
        "--llm-pause-seconds",
        type=float,
        default=0.0,
        help="Sleep between LLM rebalance cycles to reduce rate-limit pressure",
    )
    parser.add_argument("--override-strategy", help="JSON object merged into strategy params")
    parser.add_argument("--override-analysis", help="JSON object merged into analysis params")
    parser.add_argument("--override-preferences", help="JSON object merged into preferences")
    parser.add_argument(
        "--compare",
        nargs="+",
        metavar="ARTIFACT",
        help="Compare two or more saved backtest JSON artifacts",
    )
    parser.add_argument(
        "--feedback",
        nargs="?",
        const="__latest__",
        metavar="ARTIFACT",
        help=(
            "Run BacktestFeedback on ARTIFACT (or the run just completed). "
            "Writes KB validations/lessons and may create a pending recommendation."
        ),
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    app_config = get_config()
    setup_logging(app_config.log_level)
    logger = logging.getLogger(__name__)

    if args.compare:
        comparison = compare_runs(args.compare)
        print(format_comparison(comparison))
        if comparison.get("warnings"):
            raise SystemExit(1)
        return

    # Feedback-only mode against an existing artifact
    if args.feedback and args.feedback != "__latest__" and not (args.start and args.end):
        from strategy_learning.knowledge import (
            BacktestFeedbackAgent,
            format_feedback_banner,
        )

        result = BacktestFeedbackAgent().reflect_on_artifact(args.feedback)
        print(format_feedback_banner(result))
        return

    if not args.start or not args.end:
        parser.error("--start and --end are required unless using --compare or --feedback ARTIFACT")

    try:
        if not args.prefetch_only:
            validate_config(app_config)
    except ValueError as exc:
        # Prefetch can run with only Alpaca/Finnhub keys; full run needs LLM config.
        if not args.prefetch_only:
            logger.error("Configuration error: %s", exc)
            raise SystemExit(1) from exc

    bt_config = build_config_from_stores(args)
    logger.info("Backtest config: %s", json.dumps(bt_config.to_dict(), indent=2))
    logger.info("App config: %s", json.dumps(config_summary(app_config)))

    if args.prefetch_only:
        summary = ensure_historical_data(
            symbols=bt_config.symbols + list((bt_config.signal_config or {}).get("sector_etfs") or []),
            start=bt_config.start,
            end=bt_config.end,
            refresh=bt_config.refresh_cache,
        )
        print(json.dumps(summary, indent=2))
        return

    engine = BacktestEngine()
    result = engine.run(bt_config)
    payload = result.to_dict()
    artifact = save_artifact(payload, bt_config.run_label)
    logger.info("Backtest artifact saved to %s", artifact)
    print_summary(payload)
    print(f"Artifact: {artifact}")

    if args.feedback is not None:
        from strategy_learning.knowledge import (
            BacktestFeedbackAgent,
            format_feedback_banner,
        )

        feedback_path = artifact if args.feedback == "__latest__" else Path(args.feedback)
        fb = BacktestFeedbackAgent().reflect_on_artifact(feedback_path)
        print(format_feedback_banner(fb))

    if result.status == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
