from trading_agent.domain.cycle import StrategyContext
from trading_agent.formatters.market_analysis import format_market_analysis
from trading_agent.formatters.market_conditions import format_market_conditions
from trading_agent.formatters.portfolio import format_portfolio_snapshot


def format_strategy_context(context: StrategyContext) -> str:
    prefs = context.user_preferences
    return "\n\n".join([
        format_market_conditions(context.market_conditions),
        format_market_analysis(context.market_analysis),
        format_portfolio_snapshot(context.portfolio),
        "User Preferences:",
        f"- Risk Tolerance: {prefs.risk_tolerance}",
        f"- Investment Goal: {prefs.investment_goal}",
        f"- Max Position Size: {prefs.max_position_size * 100:.0f}% of portfolio",
        f"- Investment Horizon: {prefs.investment_horizon}",
    ])
