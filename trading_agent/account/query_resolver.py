from dataclasses import dataclass
from typing import Optional

from trading_agent.domain.account.account_history import AccountHistoryQuery

VALID_TIMEFRAMES = frozenset({"1Min", "5Min", "15Min", "1H", "1D"})
PERIOD_ALIASES = {"1Y": "1A", "1y": "1A"}
MONTHLY_TIMEFRAME_ALIASES = frozenset({"1M", "1m", "MONTH", "month"})


@dataclass(frozen=True)
class ResolvedHistoryRequest:
    period: str
    timeframe: Optional[str]
    group_by: Optional[str]
    date_end: Optional[str]
    extended_hours: bool


def resolve_history_request(query: AccountHistoryQuery) -> ResolvedHistoryRequest:
    """Normalize user-facing query params into valid Alpaca API request values."""
    period = PERIOD_ALIASES.get(query.period, query.period)
    timeframe = query.timeframe
    group_by = query.group_by

    if timeframe in MONTHLY_TIMEFRAME_ALIASES:
        group_by = group_by or "month"
        timeframe = None

    if group_by == "month" and not timeframe:
        timeframe = "1D"

    if timeframe and timeframe not in VALID_TIMEFRAMES:
        raise ValueError(
            f"Invalid timeframe '{timeframe}'. "
            f"Alpaca supports: {', '.join(sorted(VALID_TIMEFRAMES))}. "
            "For monthly breakdown use --group-by month (not --timeframe 1M)."
        )

    return ResolvedHistoryRequest(
        period=period,
        timeframe=timeframe,
        group_by=group_by,
        date_end=query.date_end,
        extended_hours=query.extended_hours,
    )
