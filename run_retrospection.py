#!/usr/bin/env python3
"""Consume live retrospection triggers and run an out-of-band param sweep (Phase 4.5.5)."""

from __future__ import annotations

import argparse
import json
import logging
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List

from strategy_learning.knowledge import KnowledgeBase
from strategy_learning.retrospection import (
    claim_trigger,
    list_trigger_paths,
    load_trigger,
    mark_consumed,
)
from strategy_learning.sweep import (
    ParamSweepRunner,
    config_snapshot_from_sections,
)
from strategy_learning.sweep.operator_cli import (
    LOG_DIR,
    default_sweep_window,
    load_json_arg,
    parse_date,
    save_backtest_artifact,
    save_sweep_artifact,
    setup_logging,
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


def build_base_config(args) -> BacktestConfig:
    preferences = PreferencesStore().load_preferences().to_dict()
    analysis_params = AnalysisConfigStore().load()
    strategy_params = StrategyConfigStore().load()
    rebalance_params = RebalanceConfigStore().load()
    signal_config = SignalConfigStore().load_config().to_dict()
    watchlist = WatchlistStore().load_watchlist()

    strategy_params = {**strategy_params, **load_json_arg(args.override_strategy)}
    analysis_params = {**analysis_params, **load_json_arg(args.override_analysis)}
    preferences = {**preferences, **load_json_arg(args.override_preferences)}

    symbols = []
    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    elif watchlist.symbols:
        symbols = [s.upper() for s in watchlist.symbols]
    else:
        symbols = ["AAPL"]

    app_config = get_config()
    return BacktestConfig(
        start=parse_date(args.start),
        end=parse_date(args.end),
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


def print_summary(payload: Dict[str, Any], artifact: Path, trigger_path: Path) -> None:
    print("\n" + "=" * 72)
    print("RETROSPECTION → SWEEP SUMMARY")
    print("=" * 72)
    print(f"Trigger: {trigger_path}")
    print(f"Sweep ID: {payload.get('sweep_id')}")
    print(f"Period: {payload.get('period_start')} → {payload.get('period_end')}")
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
    print(f"Sweep artifact: {artifact}")
    print("=" * 72)


def build_parser() -> argparse.ArgumentParser:
    default_start, default_end = default_sweep_window()
    parser = argparse.ArgumentParser(
        description=(
            "Consume a pending live retrospection trigger and run param sweep "
            "(out-of-band; never inside TradingCycle)"
        )
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List pending retrospection triggers and exit",
    )
    parser.add_argument(
        "--trigger",
        help="Path to a retrospection_*.json trigger (default: oldest pending)",
    )
    parser.add_argument(
        "--start",
        default=default_start.isoformat(),
        help=f"Sweep backtest start YYYY-MM-DD (default: {default_start.isoformat()})",
    )
    parser.add_argument(
        "--end",
        default=default_end.isoformat(),
        help=f"Sweep backtest end YYYY-MM-DD (default: {default_end.isoformat()})",
    )
    parser.add_argument("--rebalance", choices=["weekly", "daily"], default="weekly")
    parser.add_argument("--initial-cash", type=float, default=100_000.0)
    parser.add_argument("--risk-free-rate", type=float, default=0.04)
    parser.add_argument("--symbols", help="Comma-separated symbols (default: watchlist or AAPL)")
    parser.add_argument("--run-label", default="retrospection_sweep")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--llm-pause-seconds", type=float, default=0.0)
    parser.add_argument("--override-strategy", help="JSON object merged into baseline strategy params")
    parser.add_argument("--override-analysis", help="JSON object merged into analysis params")
    parser.add_argument("--override-preferences", help="JSON object merged into baseline preferences")
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument(
        "--write-kb",
        action="store_true",
        help="Write a pending config recommendation when a candidate beats baseline",
    )
    parser.add_argument(
        "--validate-artifact",
        help="Optional held-out backtest artifact path attached as evidence EventRef",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show which trigger would be consumed without running a sweep",
    )
    return parser


def resolve_trigger_path(args) -> Path:
    if args.trigger:
        path = Path(args.trigger)
        if not path.exists():
            raise SystemExit(f"Trigger not found: {path}")
        return path
    pending = list_trigger_paths(LOG_DIR, status="pending")
    if not pending:
        raise SystemExit("No pending retrospection triggers in logs/")
    return pending[0]


def run_sweep_for_trigger(args, trigger_path: Path, logger: logging.Logger) -> None:
    try:
        claim_trigger(trigger_path)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    trigger = load_trigger(trigger_path)
    base = build_base_config(args)
    logger.info("Retrospection trigger: %s reasons=%s", trigger.trigger_id, trigger.reasons)
    logger.info("Sweep baseline config: %s", json.dumps(base.to_dict(), indent=2))
    logger.info("App config: %s", json.dumps(config_summary(get_config())))

    baseline_snapshot = config_snapshot_from_sections(
        strategy_params=base.strategy_params,
        preferences=base.preferences,
        rebalance_params=base.rebalance_params,
        signal_config=base.signal_config,
    )
    baseline_snapshot["start"] = base.start.isoformat()
    baseline_snapshot["end"] = base.end.isoformat()

    def run_backtest(config_snapshot: Dict[str, Any], run_label: str) -> Dict[str, Any]:
        cfg = deepcopy(base)
        cfg.run_label = run_label
        cfg.strategy_params = dict(config_snapshot.get("strategy_params") or {})
        cfg.preferences = dict(config_snapshot.get("preferences") or {})
        cfg.rebalance_params = dict(config_snapshot.get("rebalance_params") or {})
        result = BacktestEngine().run(cfg)
        payload = result.to_dict()
        artifact = save_backtest_artifact(payload, run_label, log_dir=LOG_DIR)
        payload["artifact_path"] = str(artifact)
        logger.info("Candidate artifact %s → %s", run_label, artifact)
        return payload

    runner = ParamSweepRunner(
        knowledge_base=KnowledgeBase() if args.write_kb else None,
        run_backtest=run_backtest,
        max_workers=args.max_workers,
        rebalance_frequency=args.rebalance,
    )
    result = runner.run(
        baseline_snapshot,
        period_start=base.start.isoformat(),
        period_end=base.end.isoformat(),
        run_label=args.run_label,
        write_kb=False,
    )
    payload = result.to_dict()
    artifact = save_sweep_artifact(payload, args.run_label, log_dir=LOG_DIR)

    recommendation_id = None
    if args.write_kb:
        from strategy_learning.sweep.recommend import maybe_write_recommendation

        extra_evidence: List[Dict[str, Any]] = []
        if trigger.event_ref:
            extra_evidence.append(dict(trigger.event_ref))
        kb = KnowledgeBase()
        rec = maybe_write_recommendation(
            kb,
            result,
            artifact_path=str(artifact),
            validate_artifact_path=args.validate_artifact,
            extra_evidence=extra_evidence,
        )
        if rec:
            recommendation_id = rec.get("id")
            result.recommendation_id = recommendation_id
            result.notes.append(f"Pending recommendation {recommendation_id}")
        else:
            result.notes.append("write_kb set but no recommendation produced")
        result.notes.append(f"retrospection_trigger={trigger.trigger_id}")
        payload = result.to_dict()
        with artifact.open("w", encoding="utf-8") as f:
            json.dump(serialize_for_json(payload), f, indent=2)
            f.write("\n")

    mark_consumed(
        trigger_path,
        sweep_artifact_path=str(artifact),
        recommendation_id=recommendation_id,
    )
    print_summary(payload, artifact, trigger_path)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    app_config = get_config()
    setup_logging(app_config.log_level)
    logger = logging.getLogger(__name__)

    if args.list:
        pending = list_trigger_paths(LOG_DIR, status="pending")
        if not pending:
            print("No pending retrospection triggers.")
            return
        print(f"Pending triggers ({len(pending)}):")
        for path in pending:
            trigger = load_trigger(path)
            print(f"  {path} id={trigger.trigger_id} reasons={trigger.reasons}")
        return

    try:
        validate_config(app_config)
    except ValueError as exc:
        logger.error("Configuration error: %s", exc)
        raise SystemExit(1) from exc

    trigger_path = resolve_trigger_path(args)
    if args.dry_run:
        trigger = load_trigger(trigger_path)
        print(f"Would consume: {trigger_path}")
        print(f"  id={trigger.trigger_id} reasons={trigger.reasons}")
        print(f"  sweep window: {args.start} → {args.end}")
        return

    run_sweep_for_trigger(args, trigger_path, logger)


if __name__ == "__main__":
    main()
