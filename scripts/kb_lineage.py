#!/usr/bin/env python3
"""Print audit lineage for a KB recommendation or validation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trading_agent.agents.knowledge import KnowledgeBase


def _load_artifact_stats(path: Optional[str]) -> str:
    if not path:
        return ""
    p = Path(path)
    if not p.exists():
        return f" (missing artifact: {path})"
    try:
        with p.open(encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return f" (unreadable: {path})"
    if "cycle_summaries" in data:
        cycles = data.get("cycle_summaries") or []
        trades = data.get("trade_log") or []
        metrics = data.get("metrics") or {}
        return (
            f" → {path} "
            f"(cycles={len(cycles)}, trades={len(trades)}, "
            f"sharpe={metrics.get('sharpe')}, alpha={metrics.get('alpha_vs_spy')})"
        )
    decisions = data.get("decisions") or []
    executed = data.get("executed_trades") or []
    return f" → {path} (decisions={len(decisions)}, executed={len(executed)})"


def _format_event(event: Dict[str, Any], indent: str = "       ") -> List[str]:
    lines = [
        f"{indent}└─ {event.get('event_type')} {event.get('event_id')}"
        f"{_load_artifact_stats(event.get('artifact_path'))}"
    ]
    summary = event.get("summary")
    if summary:
        lines.append(f"{indent}     summary: {summary}")
    return lines


def format_lineage(kb: KnowledgeBase, recommendation_id: str) -> str:
    rec = kb.find_record(recommendation_id)
    if rec is None:
        raise SystemExit(f"Record not found: {recommendation_id}")

    lines = [
        f"ConfigRecommendation {rec.get('id')} ({rec.get('status')})",
        f"  summary: {rec.get('summary')}",
    ]
    provenance = rec.get("provenance") or {}
    lineage = provenance.get("kb_lineage") or {}
    vid = lineage.get("backtest_validation_id")
    if vid:
        validation = kb.find_record(vid)
        if validation:
            lines.append(f"  └─ BacktestValidation {vid}")
            lines.append(f"       summary: {validation.get('summary')}")
            metrics = validation.get("metrics") or {}
            lines.append(
                f"       metrics: Sharpe {metrics.get('sharpe')}, "
                f"alpha {metrics.get('alpha_vs_spy')}, "
                f"maxDD {metrics.get('max_drawdown')}"
            )
            trigger = (validation.get("provenance") or {}).get("trigger_event") or {}
            lines.extend(_format_event(trigger, indent="       "))
        else:
            lines.append(f"  └─ BacktestValidation {vid} (missing)")

    trigger = provenance.get("trigger_event")
    if trigger:
        lines.append("  └─ trigger_event")
        lines.extend(_format_event(trigger, indent="       "))

    for event in provenance.get("evidence_events") or []:
        lines.append("  └─ evidence")
        lines.extend(_format_event(event, indent="       "))

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="KB recommendation lineage")
    parser.add_argument("--recommendation-id", required=True)
    parser.add_argument("--data-dir", type=Path)
    args = parser.parse_args()

    kb_kwargs = {}
    if args.data_dir:
        kb_kwargs["data_dir"] = args.data_dir
    kb = KnowledgeBase(**kb_kwargs)
    print(format_lineage(kb, args.recommendation_id))


if __name__ == "__main__":
    main()
