import logging
from datetime import datetime
from typing import Any, Dict, Optional

from trading_agent.domain.portfolio.portfolio_snapshot import PortfolioSnapshot
from trading_agent.domain.signals.market_signals import MarketSignals
from trading_agent.domain.user.user_preferences import UserPreferences
from trading_agent.formatters.market_analysis import format_market_signals
from trading_agent.formatters.portfolio import format_portfolio_snapshot
from trading_agent.llm.client import get_llm_client, LLMClient
from .base import AnalysisStrategy

logger = logging.getLogger(__name__)


class TechnicalAnalysisStrategy(AnalysisStrategy):
    """Technical analysis strategy using LLM."""

    def __init__(self, llm_client: Optional[LLMClient] = None, client_type: str = "openai", **kwargs):
        self.llm_client = llm_client or get_llm_client(client_type, **kwargs)

    def analyze(
        self,
        portfolio: PortfolioSnapshot,
        user_preferences: UserPreferences,
        analysis_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        analysis_params = analysis_params or {}
        signals = analysis_params.get("signals")
        if isinstance(signals, dict):
            signals = MarketSignals.from_dict(signals)

        context = f"""
        {format_market_signals(signals)}
        {format_portfolio_snapshot(portfolio)}

        User Preferences:
        - Risk Tolerance: {user_preferences.risk_tolerance}
        - Investment Goal: {user_preferences.investment_goal}

        Analysis Parameters:
        - Time Horizon: {analysis_params.get('time_horizon', 'medium-term')}
        - Technical Indicators: {analysis_params.get('indicators', ['MA', 'RSI', 'MACD'])}
        - Chart Patterns: {analysis_params.get('patterns', ['trend', 'support', 'resistance'])}

        Provide technical analysis (no trade orders) in this format:
        1. Price Action Analysis
        2. Technical Indicators
        3. Chart Patterns
        4. Support/Resistance Levels
        5. Trading Signals (bullish/bearish bias only, no order sizes)
        """

        try:
            response = self.llm_client.generate_response(context)
            return {"status": "success", "analysis": response, "timestamp": datetime.now()}
        except Exception as exc:
            logger.error("Error in technical analysis: %s", exc)
            return {"status": "failed", "error": str(exc)}

    def get_strategy_name(self) -> str:
        return "Technical Analysis Strategy"

    def get_supported_parameters(self) -> Dict[str, str]:
        return {
            "time_horizon": "Analysis time horizon",
            "indicators": "Technical indicators to use",
            "patterns": "Chart patterns to look for",
        }
