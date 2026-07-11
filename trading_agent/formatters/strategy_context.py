from trading_agent.domain.cycle.strategy_context import StrategyContext
from trading_agent.formatters.market_signals import format_market_signals


def format_strategy_context(context: StrategyContext) -> str:
    signal_block = format_market_signals(context.market_signals)
    prefs = context.user_preferences
    portfolio = context.portfolio
    analysis = context.market_analysis

    return f"""
{signal_block}

Market Analysis:
{analysis.analysis}

Current Portfolio Status:
- Account Value: ${portfolio.portfolio_value:,.2f}
- Cash Balance: ${portfolio.cash:,.2f}
- Current Positions: {portfolio.positions}

User Preferences:
- Risk Tolerance: {prefs.risk_tolerance}
- Investment Goal: {prefs.investment_goal}
- Max Position Size: {prefs.max_position_size * 100:.0f}% of portfolio

Strategy Parameters:
- Decision Timeframe: {context.timeframe}
- Risk Management: {context.risk_management}
- Position Sizing: {context.position_sizing}
""".strip()
