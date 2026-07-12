"""Backtest run status helpers."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

# Below this success rate the whole run is marked failed (not merely degraded).
MIN_CYCLE_SUCCESS_RATE = 0.8


def summarize_cycles(
    cycle_summaries: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    total = len(cycle_summaries)
    ok = sum(1 for c in cycle_summaries if c.get("status") == "success")
    failed = total - ok
    rate = (ok / total) if total else 1.0
    reasons: Dict[str, int] = {}
    for c in cycle_summaries:
        if c.get("status") == "success":
            continue
        reason = str(c.get("error") or "unknown")
        reasons[reason] = reasons.get(reason, 0) + 1
    return {
        "cycles_total": total,
        "cycles_ok": ok,
        "cycles_failed": failed,
        "cycle_success_rate": rate,
        "failure_reasons": reasons,
    }


def resolve_run_status(
    cycle_summaries: Sequence[Dict[str, Any]],
    *,
    min_success_rate: float = MIN_CYCLE_SUCCESS_RATE,
) -> Tuple[str, Optional[str]]:
    """
    Derive overall backtest status from per-cycle outcomes.

    - no cycles (e.g. skip_llm): success
    - all success: success
    - some failures but success rate >= threshold: degraded
    - success rate below threshold or zero successes: failed
    """
    summary = summarize_cycles(cycle_summaries)
    total = summary["cycles_total"]
    if total == 0:
        return "success", None

    ok = summary["cycles_ok"]
    failed = summary["cycles_failed"]
    rate = summary["cycle_success_rate"]

    if failed == 0:
        return "success", None

    detail = f"Cycle success {ok}/{total} ({rate:.0%})"
    top_reasons = sorted(
        summary["failure_reasons"].items(),
        key=lambda item: item[1],
        reverse=True,
    )
    if top_reasons:
        detail += f"; top failure: {top_reasons[0][0]}"

    if ok == 0 or rate < min_success_rate:
        return "failed", detail
    return "degraded", detail


def equity_deployment(equity_curve: Sequence[Dict[str, Any]]) -> Dict[str, Optional[float]]:
    """Cash and invested fractions from the last equity point."""
    if not equity_curve:
        return {"cash": None, "equity": None, "cash_pct": None, "invested_pct": None}
    last = equity_curve[-1]
    equity = float(last.get("equity") or 0.0)
    cash = float(last.get("cash") or 0.0)
    if equity <= 0:
        return {"cash": cash, "equity": equity, "cash_pct": None, "invested_pct": None}
    cash_pct = cash / equity
    return {
        "cash": cash,
        "equity": equity,
        "cash_pct": cash_pct,
        "invested_pct": 1.0 - cash_pct,
    }


def last_trade_date(trade_log: Sequence[Dict[str, Any]]) -> Optional[str]:
    if not trade_log:
        return None
    return str(trade_log[-1].get("date") or "") or None
