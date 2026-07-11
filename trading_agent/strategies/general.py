import logging
from typing import Dict, List, Any, Optional

from ..llm.client import get_llm_client, LLMClient
from ..models import TRADING_DECISIONS_JSON_PROMPT, format_market_conditions, parse_trading_decisions
from .base import TradingStrategy

logger = logging.getLogger(__name__)


class GeneralTradingStrategy(TradingStrategy):
    """General trading strategy using LLM."""

    def __init__(self, llm_client: Optional[LLMClient] = None, client_type: str = "openai", **kwargs):
        self.llm_client = llm_client or get_llm_client(client_type, **kwargs)

    def make_decisions(
        self,
        market_analysis: Dict[str, Any],
        portfolio_data: Dict[str, Any],
        user_preferences: Dict[str, Any],
        strategy_params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        strategy_params = strategy_params or {}
        market_conditions = strategy_params.get("market_conditions")
        market_context = format_market_conditions(market_conditions)

        context = f"""
        {market_context}

        Market Analysis:
        {market_analysis.get('analysis', '')}

        Current Portfolio Status:
        - Account Value: ${portfolio_data.get('portfolio_value', 0)}
        - Cash Balance: ${portfolio_data.get('cash', 0)}
        - Current Positions: {portfolio_data.get('positions', [])}

        User Preferences:
        - Risk Tolerance: {user_preferences.get('risk_tolerance', 'moderate')}
        - Investment Goal: {user_preferences.get('investment_goal', 'growth')}
        - Max Position Size: {user_preferences.get('max_position_size', 0.1) * 100}% of portfolio

        Strategy Parameters:
        - Decision Timeframe: {strategy_params.get('timeframe', 'immediate')}
        - Risk Management: {strategy_params.get('risk_management', 'standard')}
        - Position Sizing: {strategy_params.get('position_sizing', 'dynamic')}

        {TRADING_DECISIONS_JSON_PROMPT}
        """

        try:
            response = self.llm_client.generate_response(context)
            decisions = parse_trading_decisions(response)
            return self.validate_decisions(decisions)
        except Exception as e:
            logger.error("Error in making trading decisions: %s", e)
            return []

    def get_strategy_name(self) -> str:
        return "General Trading Strategy"

    def get_supported_parameters(self) -> Dict[str, str]:
        return {
            "timeframe": "Decision timeframe (immediate, short-term, long-term)",
            "risk_management": "Risk management approach (conservative, standard, aggressive)",
            "position_sizing": "Position sizing method (fixed, dynamic, percentage-based)",
            "max_positions": "Maximum number of concurrent positions",
            "stop_loss": "Stop loss percentage",
            "take_profit": "Take profit percentage",
        }

    def validate_decisions(self, decisions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        validated_decisions = []

        for decision in decisions:
            if not all(k in decision for k in ["action", "symbol", "quantity", "reasoning", "risk_level"]):
                continue

            if decision["action"] not in ["BUY", "SELL"]:
                continue

            if decision["quantity"] != "ALL":
                try:
                    decision["quantity"] = int(decision["quantity"])
                    if decision["quantity"] <= 0:
                        continue
                except (ValueError, TypeError):
                    continue

            if decision["risk_level"] not in ["low", "medium", "high"]:
                continue

            validated_decisions.append(decision)

        return validated_decisions
