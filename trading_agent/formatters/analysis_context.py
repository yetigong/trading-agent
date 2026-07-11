from trading_agent.domain.cycle.analysis_context import AnalysisContext
from trading_agent.formatters.market_signals import format_market_signals


def format_analysis_context(context: AnalysisContext) -> str:
    signal_block = format_market_signals(context.market_signals)
    prefs = context.user_preferences
    portfolio = context.portfolio

    return f"""
{signal_block}

Current Portfolio:
- Total Value: ${portfolio.portfolio_value:,.2f}
- Cash Balance: ${portfolio.cash:,.2f}
- Current Positions: {portfolio.positions}

User Preferences:
- Risk Tolerance: {prefs.risk_tolerance}
- Investment Goal: {prefs.investment_goal}
- Investment Horizon: {prefs.investment_horizon}

Analysis Parameters:
- Time Horizon: {context.time_horizon}
- Focus Areas: {context.focus_areas}
- Regions: {context.regions}
""".strip()
