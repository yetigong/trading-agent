import logging
from datetime import datetime
from typing import Any, Dict, Optional

from trading_agent.domain.portfolio.portfolio_snapshot import PortfolioSnapshot
from trading_agent.domain.signals.market_conditions import MarketConditions
from trading_agent.domain.signals.market_signals import MarketSignals
from trading_agent.domain.user.user_preferences import UserPreferences
from trading_agent.formatters.market_analysis import format_market_signals
from trading_agent.formatters.market_conditions import format_market_conditions
from trading_agent.formatters.portfolio import format_portfolio_snapshot
from trading_agent.llm.client import get_llm_client, LLMClient
from .base import AnalysisStrategy

logger = logging.getLogger(__name__)


class GeneralAnalysisStrategy(AnalysisStrategy):
    """General market analysis strategy using LLM."""

    def __init__(self, llm_client: Optional[LLMClient] = None, client_type: str = "openai", **kwargs):
        self.llm_client = llm_client or get_llm_client(client_type, **kwargs)

    def analyze(
        self,
        portfolio: PortfolioSnapshot,
        user_preferences: UserPreferences,
        analysis_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        analysis_params = analysis_params or {}
        market_conditions = analysis_params.get("market_conditions")
        signals = analysis_params.get("signals")

        if isinstance(market_conditions, dict):
            market_conditions = MarketConditions.from_dict(market_conditions)
        if isinstance(signals, dict):
            signals = MarketSignals.from_dict(signals)

        context = f"""
        {format_market_conditions(market_conditions)}
        {format_market_signals(signals)}

        {format_portfolio_snapshot(portfolio)}

        User Preferences:
        - Risk Tolerance: {user_preferences.risk_tolerance}
        - Investment Goal: {user_preferences.investment_goal}
        - Investment Horizon: {user_preferences.investment_horizon}

        Analysis Parameters:
        - Time Horizon: {analysis_params.get('time_horizon', 'medium-term')}
        - Focus Areas: {analysis_params.get('focus_areas', 'all')}
        - Regions: {analysis_params.get('regions', 'US')}

        Provide a comprehensive market analysis (no trade orders) in this format:
        1. Market Overview
        2. Sector Analysis
        3. Risk Assessment
        4. Opportunities
        """

        try:
            if hasattr(self.llm_client, "system"):
                self.llm_client.system = (
                    "You are a trading analyst. Provide market analysis only — "
                    "do not recommend specific trade orders."
                )

            response = self.llm_client.generate_response(context)
            return {"status": "success", "analysis": response, "timestamp": datetime.now()}
        except Exception as exc:
            logger.error("Error in general market analysis: %s", exc)
            return {"status": "failed", "error": str(exc)}

    def get_strategy_name(self) -> str:
        return "General Analysis Strategy"

    def get_supported_parameters(self) -> Dict[str, str]:
        return {
            "time_horizon": "Analysis time horizon (short-term, medium-term, long-term)",
            "focus_areas": "Specific sectors or areas to focus on",
            "regions": "Geographic regions to analyze",
        }
