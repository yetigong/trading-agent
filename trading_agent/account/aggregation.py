from typing import Dict, List, Optional, Tuple

from trading_agent.domain.account.account_history import AccountHistoryPoint


def aggregate_history(
    history: List[AccountHistoryPoint],
    group_by: str,
) -> List[AccountHistoryPoint]:
    if group_by == "month":
        return _aggregate_monthly(history)
    raise ValueError(f"Unsupported group_by value: {group_by}")


def _aggregate_monthly(history: List[AccountHistoryPoint]) -> List[AccountHistoryPoint]:
    """Collapse daily points to one end-of-month equity value per month."""
    if not history:
        return []

    last_by_month: Dict[Tuple[int, int], AccountHistoryPoint] = {}
    for point in sorted(history, key=lambda item: item.timestamp):
        key = (point.timestamp.year, point.timestamp.month)
        last_by_month[key] = point

    monthly: List[AccountHistoryPoint] = []
    prev_equity: Optional[float] = None
    for key in sorted(last_by_month.keys()):
        point = last_by_month[key]
        if prev_equity is not None:
            profit_loss = point.equity - prev_equity
            profit_loss_pct = profit_loss / prev_equity if prev_equity else 0.0
        else:
            profit_loss = point.profit_loss
            profit_loss_pct = point.profit_loss_pct

        monthly.append(
            AccountHistoryPoint(
                timestamp=point.timestamp,
                equity=point.equity,
                profit_loss=profit_loss,
                profit_loss_pct=profit_loss_pct,
            )
        )
        prev_equity = point.equity

    return monthly
