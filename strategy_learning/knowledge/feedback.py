"""Backtest feedback — turn BacktestRun artifacts into KB v2 records."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from strategy_learning.knowledge.records import (
    SIGNAL_WEIGHT_DELTA,
    TUNABLE_ENUMS,
    clamp_signal_weight,
    config_hash,
    make_event_ref,
    new_id,
    step_enum,
    step_numeric,
    MAX_POSITION_SIZE_STEPS,
    REBALANCE_THRESHOLD_STEPS,
)
from strategy_learning.knowledge.store import KnowledgeBase

DEFAULT_MAX_DRAWDOWN = -0.25
DEFAULT_MIN_TRADES = 1


class BacktestFeedbackAgent:
    """Score a completed backtest and write validation / recommendation records."""

    name = "backtest_feedback"

    def __init__(
        self,
        knowledge_base: Optional[KnowledgeBase] = None,
        *,
        max_drawdown: float = DEFAULT_MAX_DRAWDOWN,
        min_trades: int = DEFAULT_MIN_TRADES,
    ):
        self.knowledge_base = knowledge_base or KnowledgeBase()
        self.max_drawdown = max_drawdown
        self.min_trades = min_trades

    def reflect_on_artifact(
        self,
        artifact_path: str | Path,
        *,
        is_validated_baseline: bool = True,
    ) -> Dict[str, Any]:
        # Lazy import: trading_agent.backtest.__init__ pulls BacktestEngine → agents.
        from trading_agent.backtest.comparison import load_run
        from trading_agent.backtest.models import BacktestRun

        path = Path(artifact_path)
        data = load_run(path)
        run = BacktestRun.from_dict(data)
        return self.reflect_on_backtest(
            run,
            artifact_path=str(path),
            is_validated_baseline=is_validated_baseline,
        )

    def reflect_on_backtest(
        self,
        run: Any,
        *,
        artifact_path: Optional[str] = None,
        is_validated_baseline: bool = True,
    ) -> Dict[str, Any]:
        metrics = run.metrics or {}
        config = run.config or {}
        spy = self._spy_benchmark(run.benchmarks or [])
        underperf, reasons = self._underperformance(metrics, spy, run)

        config_snapshot = {
            "strategy_params": dict(config.get("strategy_params") or {}),
            "preferences": dict(config.get("preferences") or {}),
            "rebalance_params": dict(config.get("rebalance_params") or {}),
            "signal_config": {
                k: (config.get("signal_config") or {}).get(k)
                for k in ("enabled_sources",)
                if (config.get("signal_config") or {}).get(k) is not None
            },
        }
        c_hash = config_hash(config_snapshot)
        period_start = config.get("start")
        period_end = config.get("end")
        run_label = config.get("run_label") or "default"

        event = make_event_ref(
            event_type="backtest_run",
            event_id=run.run_id,
            artifact_path=artifact_path,
            artifact_kind="backtest",
            summary=f"{run_label} {period_start}→{period_end} status={run.status}",
            user_id=self.knowledge_base.user_id,
            timestamp=run.timestamp,
            metadata={
                "run_label": run_label,
                "period_start": period_start,
                "period_end": period_end,
                "status": run.status,
                "rebalance_count": len(run.cycle_summaries or []),
            },
        )

        sharpe = metrics.get("sharpe")
        alpha = metrics.get("alpha_vs_spy")
        max_dd = metrics.get("max_drawdown")
        summary = (
            f"{run_label} {period_start}→{period_end}: "
            f"Sharpe {_fmt(sharpe)}, alpha {_fmt(alpha)}, "
            f"maxDD {_fmt(max_dd)}, status={run.status}"
        )
        if underperf:
            rationale = "Underperformed vs benchmarks/guardrails: " + "; ".join(reasons)
        else:
            rationale = "Validated window for current config; no promotion proposed"

        validation = self.knowledge_base.append_backtest_validation({
            "id": new_id("bv"),
            "summary": summary,
            "rationale": rationale,
            "provenance": {"trigger_event": event},
            "status": run.status,
            "config_hash": c_hash,
            "config_snapshot": config_snapshot,
            "metrics": {
                "sharpe": sharpe,
                "alpha_vs_spy": alpha,
                "max_drawdown": max_dd,
                "total_return": metrics.get("total_return"),
                "trade_count": metrics.get("trade_count"),
            },
            "benchmark_comparison": {
                "spy_sharpe": spy.get("sharpe") if spy else None,
                "beat_spy": self._beat_spy(metrics, spy),
            },
            "is_validated_baseline": is_validated_baseline,
        })

        lesson = self.knowledge_base.append_lesson_record({
            "id": new_id("les-bt"),
            "source": "backtest",
            "summary": summary,
            "rationale": rationale,
            "provenance": {
                "trigger_event": event,
                "kb_lineage": {"backtest_validation_id": validation["id"]},
            },
            "tags": ["backtest", "underperformance"] if underperf else ["backtest", "validation"],
            "metrics_snapshot": {
                "sharpe": sharpe,
                "alpha_vs_spy": alpha,
                "max_drawdown": max_dd,
            },
        })

        recommendation = None
        weight_updates: Dict[str, float] = {}
        if underperf and run.status == "success":
            proposed, diff_summary, weight_updates = self._propose_changes(
                config_snapshot, metrics, spy, reasons
            )
            if proposed:
                recommendation = self.knowledge_base.append_config_recommendation({
                    "id": new_id("cr"),
                    "summary": f"Proposed config change after {run_label} underperformance",
                    "rationale": rationale + ". Diff: " + "; ".join(diff_summary),
                    "provenance": {
                        "generated_by": "backtest_feedback",
                        "trigger_event": event,
                        "evidence_events": [event],
                        "kb_lineage": {
                            "backtest_validation_id": validation["id"],
                            "baseline_validation_id": validation["id"],
                            "lesson_id": lesson["id"],
                        },
                    },
                    "status": "pending_review",
                    "baseline_config_hash": c_hash,
                    "proposed_changes": proposed,
                    "diff_summary": diff_summary,
                    "expected_impact": {
                        "reasons": reasons,
                        "metrics_delta_vs_baseline": "re-backtest after promote",
                    },
                    "review": {
                        "reviewed_at": None,
                        "reviewed_by": None,
                        "decision": None,
                        "reject_reason": None,
                    },
                    "supersedes": None,
                    "superseded_by": None,
                })

        if weight_updates:
            # Capped deltas only when underperformance is attributed to signal families.
            current = self.knowledge_base.signal_weights()
            merged = dict(current)
            for key, delta in weight_updates.items():
                base = float(merged.get(key, 1.0))
                merged[key] = clamp_signal_weight(base + delta)
            self.knowledge_base.update_weights_and_prefs(signal_weights=merged)

        return {
            "validation": validation,
            "lesson": lesson,
            "recommendation": recommendation,
            "underperformance": underperf,
            "reasons": reasons,
            "review_required": recommendation is not None,
        }

    def _spy_benchmark(self, benchmarks: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        for row in benchmarks:
            name = str(row.get("name") or "").lower()
            if "spy" in name:
                return row
        return benchmarks[0] if benchmarks else None

    def _beat_spy(
        self, metrics: Dict[str, Any], spy: Optional[Dict[str, Any]]
    ) -> Optional[bool]:
        if not spy:
            return None
        alpha = metrics.get("alpha_vs_spy")
        if alpha is not None:
            return float(alpha) > 0
        sharpe = metrics.get("sharpe")
        spy_sharpe = spy.get("sharpe")
        if sharpe is not None and spy_sharpe is not None:
            return float(sharpe) >= float(spy_sharpe)
        return None

    def _underperformance(
        self,
        metrics: Dict[str, Any],
        spy: Optional[Dict[str, Any]],
        run: Any,
    ) -> Tuple[bool, List[str]]:
        reasons: List[str] = []
        if run.status != "success":
            reasons.append(f"run status={run.status}")
            return True, reasons

        trade_count = int(metrics.get("trade_count") or 0)
        if trade_count < self.min_trades:
            reasons.append(f"trade_count {trade_count} < min {self.min_trades}")

        max_dd = metrics.get("max_drawdown")
        if max_dd is not None and float(max_dd) < self.max_drawdown:
            reasons.append(
                f"max_drawdown {float(max_dd):.3f} below ceiling {self.max_drawdown}"
            )

        alpha = metrics.get("alpha_vs_spy")
        sharpe = metrics.get("sharpe")
        spy_sharpe = spy.get("sharpe") if spy else None
        beat = self._beat_spy(metrics, spy)
        if beat is False:
            if alpha is not None:
                reasons.append(f"alpha_vs_spy {float(alpha):.3f} <= 0")
            elif sharpe is not None and spy_sharpe is not None:
                reasons.append(
                    f"sharpe {float(sharpe):.3f} < SPY sharpe {float(spy_sharpe):.3f}"
                )

        # High cash drag heuristic from notes / equity if present
        equity = run.equity_curve or []
        if equity:
            last = equity[-1]
            last_eq = float(last.get("equity") or 0)
            last_cash = float(last.get("cash") or 0)
            if last_eq > 0 and (last_cash / last_eq) > 0.4 and beat is False:
                reasons.append("high cash deployment with underperformance vs SPY")

        return bool(reasons), reasons

    def _propose_changes(
        self,
        config_snapshot: Dict[str, Any],
        metrics: Dict[str, Any],
        spy: Optional[Dict[str, Any]],
        reasons: List[str],
    ) -> Tuple[Dict[str, Any], List[str], Dict[str, float]]:
        """One discrete step per field; whitelist only."""
        proposed: Dict[str, Any] = {}
        diffs: List[str] = []
        weight_deltas: Dict[str, float] = {}

        strategy = dict(config_snapshot.get("strategy_params") or {})
        prefs = dict(config_snapshot.get("preferences") or {})
        rebalance = dict(config_snapshot.get("rebalance_params") or {})

        reason_text = " ".join(reasons).lower()
        high_dd = "max_drawdown" in reason_text
        high_cash = "cash" in reason_text
        low_trades = "trade_count" in reason_text
        lag_spy = "alpha" in reason_text or "sharpe" in reason_text

        # Direction: -1 more conservative, +1 more aggressive
        if high_dd:
            direction = -1
        elif low_trades and not high_dd:
            direction = 1
        elif high_cash and lag_spy:
            direction = 1  # less defensive
        elif lag_spy:
            direction = -1
        else:
            direction = -1

        rm_choices = TUNABLE_ENUMS["strategy_params"]["risk_management"]
        new_rm = step_enum(strategy.get("risk_management"), rm_choices, direction)
        if new_rm and new_rm != strategy.get("risk_management"):
            proposed.setdefault("strategy_params", {})["risk_management"] = new_rm
            diffs.append(
                f"strategy_params.risk_management: "
                f"{strategy.get('risk_management')} → {new_rm}"
            )

        if high_dd or lag_spy:
            cur_size = float(prefs.get("max_position_size", 0.25))
            new_size = step_numeric(cur_size, MAX_POSITION_SIZE_STEPS, -1 if high_dd else direction)
            if new_size != cur_size:
                proposed.setdefault("preferences", {})["max_position_size"] = new_size
                diffs.append(f"preferences.max_position_size: {cur_size} → {new_size}")

        if high_dd:
            cur_thr = float(rebalance.get("threshold", 0.05) or 0.05)
            new_thr = step_numeric(cur_thr, REBALANCE_THRESHOLD_STEPS, 1)
            if new_thr != cur_thr:
                proposed.setdefault("rebalance_params", {})["threshold"] = new_thr
                diffs.append(f"rebalance_params.threshold: {cur_thr} → {new_thr}")

        if low_trades:
            # Soft bias only via KB prefs — not hard strategy_params.json
            self.knowledge_base.update_weights_and_prefs(
                strategy_preferences={
                    "recent_trade_bias": min(
                        1.0,
                        float(
                            self.knowledge_base.strategy_preferences().get(
                                "recent_trade_bias", 0.0
                            )
                        )
                        + 0.1,
                    )
                }
            )
            diffs.append("strategy_preferences.recent_trade_bias += 0.1 (soft KB only)")

        # Attribute lagging technical/news lightly when present in reasons
        if lag_spy:
            weight_deltas["technicals"] = -SIGNAL_WEIGHT_DELTA
            weight_deltas["news"] = SIGNAL_WEIGHT_DELTA

        return proposed, diffs, weight_deltas


def format_feedback_banner(result: Dict[str, Any]) -> str:
    lines = ["=" * 72, "BACKTEST FEEDBACK", "=" * 72]
    validation = result.get("validation") or {}
    lines.append(validation.get("summary") or "")
    if result.get("underperformance"):
        lines.append("Underperformance reasons:")
        for reason in result.get("reasons") or []:
            lines.append(f"  - {reason}")
    else:
        lines.append("No underperformance vs guardrails.")
    rec = result.get("recommendation")
    if rec:
        lines.append("")
        lines.append("CONFIG REVIEW REQUIRED")
        lines.append(f"  recommendation_id: {rec.get('id')}")
        lines.append(f"  summary: {rec.get('summary')}")
        for diff in rec.get("diff_summary") or []:
            lines.append(f"  - {diff}")
        lines.append(
            "  Review: .venv/bin/python scripts/review_config_recommendation.py"
        )
        lines.append(
            f"  Lineage: .venv/bin/python scripts/kb_lineage.py "
            f"--recommendation-id {rec.get('id')}"
        )
    else:
        lines.append("No pending config recommendation.")
    lines.append("=" * 72)
    return "\n".join(lines)


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return str(value)
