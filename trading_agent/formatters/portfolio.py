from typing import Optional

from trading_agent.domain.portfolio.portfolio_snapshot import PortfolioSnapshot


def format_portfolio_snapshot(portfolio: Optional[PortfolioSnapshot]) -> str:
    if not portfolio:
        return "Portfolio: unavailable"

    acct = portfolio.account
    lines = [
        "Current Portfolio:",
        f"- Account Value: ${acct.portfolio_value:,.2f}",
        f"- Cash Balance: ${acct.cash:,.2f}",
        f"- Buying Power: ${acct.buying_power:,.2f}",
        f"- Equity: ${acct.equity:,.2f}",
    ]

    if portfolio.positions:
        lines.append("- Positions:")
        for pos in portfolio.positions:
            lines.append(
                f"  - {pos.symbol}: {pos.qty:g} shares "
                f"(available {pos.available_qty:g}), "
                f"market_value=${pos.market_value:,.2f}, "
                f"price=${pos.current_price:,.2f}"
            )
    else:
        lines.append("- Positions: none")

    if portfolio.open_orders:
        lines.append("- Open Orders:")
        for order in portfolio.open_orders:
            lines.append(
                f"  - {order.symbol}: {order.side.upper()} {order.qty:g} ({order.status})"
            )

    lines.extend([
        "",
        "Trading constraints:",
        "- SELL quantity must not exceed available shares for that symbol.",
        '- Use "ALL" for SELL only when shares are held; never use "ALL" for BUY.',
        "- BUY notional must fit within buying power and max position size.",
        "- Do not trade symbols with conflicting open orders.",
        "- If buying power is low, prioritize SELL orders before BUY orders.",
    ])

    return "\n".join(lines)
