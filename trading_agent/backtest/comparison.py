"""Compare saved BacktestRun artifacts side-by-side."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Sequence, Union


def load_run(path: Union[str, Path]) -> Dict[str, Any]:
    with Path(path).open(encoding="utf-8") as f:
        return json.load(f)


def _metric_rows(run: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    strategy = run.get("metrics") or {}
    if strategy:
        rows.append(dict(strategy))
    for bench in run.get("benchmarks") or []:
        rows.append(dict(bench))
    return rows


def compare_runs(paths: Sequence[Union[str, Path]]) -> Dict[str, Any]:
    """Load multiple backtest artifacts and produce a comparison table."""
    runs = []
    for path in paths:
        data = load_run(path)
        runs.append({
            "path": str(path),
            "run_id": data.get("run_id"),
            "run_label": (data.get("config") or {}).get("run_label"),
            "status": data.get("status"),
            "metrics": data.get("metrics") or {},
            "benchmarks": data.get("benchmarks") or [],
            "config": data.get("config") or {},
        })

    strategy_rows = []
    for run in runs:
        m = run["metrics"]
        strategy_rows.append({
            "run_label": run["run_label"],
            "path": run["path"],
            "total_return": m.get("total_return"),
            "cagr": m.get("cagr"),
            "max_drawdown": m.get("max_drawdown"),
            "sharpe": m.get("sharpe"),
            "alpha_vs_spy": m.get("alpha_vs_spy"),
            "trade_count": m.get("trade_count"),
        })

    best_sharpe = None
    lowest_dd = None
    if strategy_rows:
        with_sharpe = [r for r in strategy_rows if r.get("sharpe") is not None]
        with_dd = [r for r in strategy_rows if r.get("max_drawdown") is not None]
        if with_sharpe:
            best_sharpe = max(with_sharpe, key=lambda r: r["sharpe"])["run_label"]
        if with_dd:
            lowest_dd = min(with_dd, key=lambda r: r["max_drawdown"])["run_label"]

    return {
        "runs": runs,
        "strategy_comparison": strategy_rows,
        "highlights": {
            "best_sharpe": best_sharpe,
            "lowest_drawdown": lowest_dd,
        },
    }


def format_comparison(comparison: Dict[str, Any]) -> str:
    lines = ["=" * 72, "BACKTEST RUN COMPARISON", "=" * 72]
    header = f"{'Label':<20} {'Return':>10} {'CAGR':>10} {'MaxDD':>10} {'Sharpe':>10} {'Alpha':>10}"
    lines.append(header)
    lines.append("-" * 72)
    for row in comparison.get("strategy_comparison") or []:
        lines.append(
            f"{str(row.get('run_label') or ''):<20} "
            f"{_pct(row.get('total_return')):>10} "
            f"{_pct(row.get('cagr')):>10} "
            f"{_pct(row.get('max_drawdown')):>10} "
            f"{_num(row.get('sharpe')):>10} "
            f"{_pct(row.get('alpha_vs_spy')):>10}"
        )
    highlights = comparison.get("highlights") or {}
    lines.append("-" * 72)
    lines.append(f"Best Sharpe: {highlights.get('best_sharpe')}")
    lines.append(f"Lowest drawdown: {highlights.get('lowest_drawdown')}")
    lines.append("=" * 72)
    return "\n".join(lines)


def _pct(value) -> str:
    if value is None:
        return "n/a"
    return f"{float(value) * 100:.2f}%"


def _num(value) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2f}"
