#!/usr/bin/env python3
"""Manual entry point for Phase 4.5.4 param sweep (sole hard-recommendation producer)."""

from __future__ import annotations

import argparse
import json
import logging
from copy import deepcopy
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Optional

from strategy_learning.knowledge import KnowledgeBase
from strategy_learning.sweep import (
    ParamSweepRunner,
    config_snapshot_from_sections,
)
from trading_agent.backtest.engine import BacktestEngine
from trading_agent.backtest.models import BacktestConfig
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


def build_base_config(args) -> BacktestConfig:
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


def save_sweep_artifact(payload: Dict[str, Any], run_label: str) -> Path:
    LOG_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_label = "".join(c if c.isalnum() or c in "-_" else "_" for c in run_label) or "sweep"
    path = LOG_DIR / f"sweep_{timestamp}_{safe_label}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(serialize_for_json(payload), f, indent=2)
        f.write("\n")
    return path


def save_backtest_artifact(run_dict: Dict[str, Any], run_label: str) -> Path:
    LOG_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_label = "".join(c if c.isalnum() or c in "-_" else "_" for c in run_label) or "run"
    path = LOG_DIR / f"backtest_{timestamp}_{safe_label}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(serialize_for_json(run_dict), f, indent=2)
        f.write("\n")
    return path


def print_sweep_summary(payload: Dict[str, Any], artifact: Path) -> None:
    print("\n" + "=" * 72)
    print("PARAM SWEEP SUMMARY")
    print("=" * 72)
    print(f"Sweep ID: {payload.get('sweep_id')}")
    print(f"Label: {payload.get('run_label')}")
    print(f"Period: {payload.get('period_start')} → {payload.get('period_end')}")
    baseline = payload.get("baseline") or {}
    print(
        f"Baseline: status={baseline.get('status')} "
        f"sharpe={(baseline.get('metrics') or {}).get('sharpe')}"
    )
    print(f"Candidates: {len(payload.get('candidates') or [])}")
    winner = payload.get("winner") or {}
    print(
        f"Winner: {winner.get('label')} status={winner.get('status')} "
        f"sharpe={(winner.get('metrics') or {}).get('sharpe')}"
    )
    if payload.get("recommendation_id"):
        print(f"Pending recommendation: {payload['recommendation_id']}")
        print("  Review: .venv/bin/python scripts/review_config_recommendation.py")
    for note in payload.get("notes") or []:
        print(f"Note: {note}")
    print(f"Artifact: {artifact}")
    print("=" * 72)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run OAT param sweep; optionally write a pending KB recommendation"
    )
    parser.add_argument("--start", required=True, help="Backtest start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="Backtest end date YYYY-MM-DD")
    parser.add_argument("--rebalance", choices=["weekly", "daily"], default="weekly")
    parser.add_argument("--initial-cash", type=float, default=100_000.0)
    parser.add_argument("--risk-free-rate", type=float, default=0.04)
    parser.add_argument("--symbols", help="Comma-separated symbols (default: watchlist or AAPL)")
    parser.add_argument("--run-label", default="sweep", help="Label stored in the artifact")
    parser.add_argument("--refresh", action="store_true", help="Refresh historical caches")
    parser.add_argument(
        "--llm-pause-seconds",
        type=float,
        default=0.0,
        help="Sleep between LLM rebalance cycles to reduce rate-limit pressure",
    )
    parser.add_argument("--override-strategy", help="JSON object merged into baseline strategy params")
    parser.add_argument("--override-analysis", help="JSON object merged into analysis params")
    parser.add_argument("--override-preferences", help="JSON object merged into baseline preferences")
    parser.add_argument(
        "--max-workers",
        type=int,
        default=1,
        help=(
            "Parallel candidate backtests (default 1 = sequential). "
            "Use >1 to overlap candidates; LLM calls within each backtest stay sequential. "
            "Watch provider rate limits."
        ),
    )
    parser.add_argument(
        "--write-kb",
        action="store_true",
        help="Write a pending config recommendation when a candidate beats baseline",
    )
    parser.add_argument(
        "--validate-artifact",
        help="Optional held-out backtest artifact path attached as evidence EventRef",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    app_config = get_config()
    setup_logging(app_config.log_level)
    logger = logging.getLogger(__name__)

    try:
        validate_config(app_config)
    except ValueError as exc:
        logger.error("Configuration error: %s", exc)
        raise SystemExit(1) from exc

    base = build_base_config(args)
    logger.info("Sweep baseline config: %s", json.dumps(base.to_dict(), indent=2))
    logger.info("App config: %s", json.dumps(config_summary(app_config)))

    baseline_snapshot = config_snapshot_from_sections(
        strategy_params=base.strategy_params,
        preferences=base.preferences,
        rebalance_params=base.rebalance_params,
        signal_config=base.signal_config,
    )
    # Carry period into snapshot for SweepResult defaults / hashing context
    baseline_snapshot["start"] = base.start.isoformat()
    baseline_snapshot["end"] = base.end.isoformat()

    # One engine per backtest call so --max-workers >1 does not share mutable state.
    def run_backtest(config_snapshot: Dict[str, Any], run_label: str) -> Dict[str, Any]:
        cfg = deepcopy(base)
        cfg.run_label = run_label
        cfg.strategy_params = dict(config_snapshot.get("strategy_params") or {})
        cfg.preferences = dict(config_snapshot.get("preferences") or {})
        cfg.rebalance_params = dict(config_snapshot.get("rebalance_params") or {})
        # Keep analysis/signal/LLM from baseline; do not mutate data/*.json stores.
        result = BacktestEngine().run(cfg)
        payload = result.to_dict()
        artifact = save_backtest_artifact(payload, run_label)
        payload["artifact_path"] = str(artifact)
        logger.info("Candidate artifact %s → %s", run_label, artifact)
        return payload

    runner = ParamSweepRunner(
        knowledge_base=KnowledgeBase() if args.write_kb else None,
        run_backtest=run_backtest,
        max_workers=args.max_workers,
        rebalance_frequency=args.rebalance,
    )

    # First pass without KB path (artifact not yet known); write KB after save if needed.
    result = runner.run(
        baseline_snapshot,
        period_start=base.start.isoformat(),
        period_end=base.end.isoformat(),
        run_label=args.run_label,
        write_kb=False,
    )
    payload = result.to_dict()
    artifact = save_sweep_artifact(payload, args.run_label)

    if args.write_kb:
        from strategy_learning.sweep.recommend import maybe_write_recommendation

        kb = KnowledgeBase()
        rec = maybe_write_recommendation(
            kb,
            result,
            artifact_path=str(artifact),
            validate_artifact_path=args.validate_artifact,
        )
        if rec:
            result.recommendation_id = rec.get("id")
            result.notes.append(f"Pending recommendation {rec.get('id')}")
            payload = result.to_dict()
            with artifact.open("w", encoding="utf-8") as f:
                json.dump(serialize_for_json(payload), f, indent=2)
                f.write("\n")
        else:
            result.notes.append("write_kb set but no recommendation produced")
            payload = result.to_dict()
            with artifact.open("w", encoding="utf-8") as f:
                json.dump(serialize_for_json(payload), f, indent=2)
                f.write("\n")

    print_sweep_summary(payload, artifact)


if __name__ == "__main__":
    main()
