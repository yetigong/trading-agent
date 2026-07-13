"""Pure metrics for live underperformance detection (Phase 4.5.5)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

EquityPoint = Union[Tuple[datetime, float], Dict[str, Any]]
ClosePoint = Union[Tuple[datetime, float], Dict[str, Any], float]


def _as_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 1e12:
            ts /= 1000.0
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _equity_pair(point: EquityPoint) -> Optional[Tuple[datetime, float]]:
    if isinstance(point, (tuple, list)) and len(point) >= 2:
        ts = _as_datetime(point[0])
        try:
            equity = float(point[1])
        except (TypeError, ValueError):
            return None
        if ts is None:
            return None
        return ts, equity
    if isinstance(point, dict):
        ts = _as_datetime(point.get("timestamp") or point.get("ts") or point.get("date"))
        raw = point.get("equity")
        if raw is None:
            raw = point.get("value")
        try:
            equity = float(raw)
        except (TypeError, ValueError):
            return None
        if ts is None:
            return None
        return ts, equity
    return None


def _close_pair(point: ClosePoint) -> Optional[Tuple[Optional[datetime], float]]:
    if isinstance(point, (int, float)):
        return None, float(point)
    if isinstance(point, (tuple, list)) and len(point) >= 2:
        return _as_datetime(point[0]), float(point[1])
    if isinstance(point, dict):
        ts = _as_datetime(point.get("timestamp") or point.get("ts") or point.get("date"))
        raw = point.get("close")
        if raw is None:
            raw = point.get("value")
        if raw is None:
            return None
        return ts, float(raw)
    return None


def series_return(values: Sequence[float]) -> Optional[float]:
    """Simple first→last return; None if insufficient or non-positive start."""
    if len(values) < 2:
        return None
    start = float(values[0])
    end = float(values[-1])
    if start <= 0:
        return None
    return (end - start) / start


def _slice_pairs_by_window(
    pairs: List[Tuple[datetime, float]],
    *,
    window_days: int,
    as_of: datetime,
    allow_short_fallback: bool = True,
) -> List[Tuple[datetime, float]]:
    start_cutoff = as_of - timedelta(days=window_days)
    in_window = [p for p in pairs if start_cutoff <= p[0] <= as_of]
    if len(in_window) >= 2:
        return in_window
    if allow_short_fallback and len(pairs) >= 2:
        # Broker/bar history shorter than the requested window.
        return [p for p in pairs if p[0] <= as_of] or pairs
    return in_window


def window_equity_return(
    equity_points: Sequence[EquityPoint],
    *,
    window_days: int = 30,
    as_of: Optional[datetime] = None,
) -> Optional[float]:
    """Return of equity over [as_of - window, as_of] (fallback to full series if short)."""
    pairs = [p for p in (_equity_pair(pt) for pt in equity_points) if p is not None]
    if len(pairs) < 2:
        return None
    pairs.sort(key=lambda x: x[0])
    end_ts = as_of or pairs[-1][0]
    if end_ts.tzinfo is None:
        end_ts = end_ts.replace(tzinfo=timezone.utc)
    in_window = _slice_pairs_by_window(
        pairs, window_days=window_days, as_of=end_ts, allow_short_fallback=True
    )
    if len(in_window) < 2:
        return None
    return series_return([p[1] for p in in_window])


def window_closes_return(
    closes: Sequence[ClosePoint],
    *,
    window_days: int = 30,
    as_of: Optional[datetime] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> Optional[float]:
    """Return of closes over an explicit [start, end] or rolling window ending at as_of.

    Untimestamped closes are only used when neither start nor window bounds apply
    (legacy / test helpers); prefer timestamped bars in production.
    """
    parsed: List[Tuple[Optional[datetime], float]] = []
    for pt in closes:
        pair = _close_pair(pt)
        if pair is not None:
            parsed.append(pair)
    if len(parsed) < 2:
        return None

    timed = [(ts, val) for ts, val in parsed if ts is not None]
    if start is not None or end is not None:
        if len(timed) < 2:
            return None
        timed.sort(key=lambda x: x[0])
        lo = start or timed[0][0]
        hi = end or timed[-1][0]
        if lo.tzinfo is None:
            lo = lo.replace(tzinfo=timezone.utc)
        if hi.tzinfo is None:
            hi = hi.replace(tzinfo=timezone.utc)
        in_span = [p for p in timed if lo <= p[0] <= hi]
        if len(in_span) < 2:
            return None
        return series_return([p[1] for p in in_span])

    if len(timed) >= 2:
        timed.sort(key=lambda x: x[0])
        end_ts = as_of or timed[-1][0]
        if end_ts.tzinfo is None:
            end_ts = end_ts.replace(tzinfo=timezone.utc)
        in_window = _slice_pairs_by_window(
            timed, window_days=window_days, as_of=end_ts, allow_short_fallback=True
        )
        if len(in_window) < 2:
            return None
        return series_return([p[1] for p in in_window])

    # No timestamps: use series as-is (tests / injected bare floats).
    return series_return([p[1] for p in parsed])


def closes_return(closes: Sequence[ClosePoint]) -> Optional[float]:
    """Return from first to last close (ordered by timestamp when present)."""
    return window_closes_return(closes, window_days=10_000)


def spy_lag_pp(equity_return: Optional[float], spy_return: Optional[float]) -> Optional[float]:
    """Portfolio return minus SPY return (negative means lagging)."""
    if equity_return is None or spy_return is None:
        return None
    return equity_return - spy_return


def lags_spy(
    equity_return: Optional[float],
    spy_return: Optional[float],
    *,
    lag_threshold_pp: float = 0.05,
) -> bool:
    """True when equity lags SPY by more than lag_threshold_pp (percentage points)."""
    lag = spy_lag_pp(equity_return, spy_return)
    if lag is None:
        return False
    return lag < -abs(lag_threshold_pp)


def load_recent_cycle_summaries(
    log_dir: Union[str, Path],
    *,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Load newest cycle_*.json artifacts as lightweight summaries."""
    root = Path(log_dir)
    if not root.exists():
        return []
    paths = sorted(root.glob("cycle_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    summaries: List[Dict[str, Any]] = []
    for path in paths[:limit]:
        try:
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        summaries.append(
            {
                "cycle_id": data.get("cycle_id"),
                "status": data.get("status"),
                "hold": bool(data.get("hold")),
                "timestamp": data.get("timestamp"),
                "artifact_path": str(path),
            }
        )
    return summaries


def consecutive_hold_streak(summaries: Sequence[Dict[str, Any]]) -> int:
    """Count consecutive successful hold=true cycles from newest to oldest."""
    streak = 0
    for item in summaries:
        if str(item.get("status") or "") != "success":
            break
        if not item.get("hold"):
            break
        streak += 1
    return streak


def hold_streak_time_span(
    summaries: Sequence[Dict[str, Any]],
    *,
    streak_required: int,
) -> Optional[Tuple[datetime, datetime]]:
    """Return (oldest, newest) timestamps for the leading hold streak, if available."""
    if consecutive_hold_streak(summaries) < streak_required:
        return None
    streak_items = list(summaries[:streak_required])
    times: List[datetime] = []
    for item in streak_items:
        ts = _as_datetime(item.get("timestamp"))
        if ts is not None:
            times.append(ts)
    if len(times) < 2:
        # Single timestamp: treat as instantaneous span (no SPY move measurable).
        return None
    return min(times), max(times)


def hold_streak_with_spy_rise(
    summaries: Sequence[Dict[str, Any]],
    spy_closes: Sequence[ClosePoint],
    *,
    streak_required: int = 3,
    as_of: Optional[datetime] = None,
) -> Tuple[bool, Dict[str, Any]]:
    """True when ≥ streak_required consecutive holds and SPY rose over that cycle span."""
    streak = consecutive_hold_streak(summaries)
    span = hold_streak_time_span(summaries, streak_required=streak_required)
    metrics: Dict[str, Any] = {
        "hold_streak": streak,
        "hold_streak_required": streak_required,
        "hold_span_start": span[0].isoformat() if span else None,
        "hold_span_end": span[1].isoformat() if span else None,
        "spy_return_over_hold_span": None,
    }
    if streak < streak_required:
        return False, metrics

    if span is not None:
        spy_ret = window_closes_return(
            spy_closes,
            start=span[0],
            end=span[1],
        )
    else:
        # No cycle timestamps: cannot attribute SPY move to the hold span.
        metrics["spy_return_over_hold_span"] = None
        metrics["hold_span_unavailable"] = True
        return False, metrics

    metrics["spy_return_over_hold_span"] = spy_ret
    if spy_ret is None or spy_ret <= 0:
        return False, metrics
    return True, metrics


def portfolio_history_period_for_window(window_days: int) -> str:
    """Map retrospection window days to an Alpaca portfolio-history period string."""
    days = max(1, int(window_days))
    if days <= 7:
        return "1W"
    if days <= 31:
        return "1M"
    if days <= 93:
        return "3M"
    return "1A"
