import logging
from typing import Dict, List, Any, Optional

from trading_agent.domain.cycle import StrategyContext, TradingDecision
from trading_agent.formatters.portfolio import format_portfolio_snapshot
from trading_agent.llm.client import get_llm_client, LLMClient

logger = logging.getLogger(__name__)


class PortfolioRebalancer:
    """Portfolio rebalancing strategy using LLM."""

    def __init__(self, llm_client: Optional[LLMClient] = None, client_type: str = "openai", **kwargs):
        self.llm_client = llm_client or get_llm_client(client_type, **kwargs)

    def rebalance_portfolio(self, context: StrategyContext) -> Dict[str, Any]:
        rebalance_params = context.rebalance_params or {}
        portfolio_text = format_portfolio_snapshot(context.portfolio)
        prefs = context.user_preferences
        target_allocation = str(rebalance_params.get("target_allocation", "balanced")).lower()
        growth_guidance = ""
        if target_allocation == "growth":
            growth_guidance = (
                "Growth allocation mode: do not force equal-sector balance. "
                "Preserve growth/core overweights (e.g. SPY/QQQ/XLK and high-conviction "
                "growth names) when they remain within max position size."
            )

        prompt = f"""
        {portfolio_text}

        User Preferences:
        - Risk Tolerance: {prefs.risk_tolerance}
        - Investment Goal: {prefs.investment_goal}
        - Max Position Size: {prefs.max_position_size * 100:.0f}% of portfolio

        Rebalancing Parameters:
        - Target Allocation: {rebalance_params.get('target_allocation', 'balanced')}
        - Threshold: {rebalance_params.get('threshold', 5)}%
        - Sector Weights: {rebalance_params.get('sector_weights', 'market_cap')}

        {growth_guidance}

        Provide a rebalancing plan in this format:
        1. Target Allocation
        2. Required Changes
        3. Reasoning
        """

        try:
            response = self.llm_client.generate_response(prompt)
            return {"status": "success", "rebalancing_plan": self._parse_rebalancing_plan(response)}
        except Exception as exc:
            logger.error("Error in portfolio rebalancing: %s", exc)
            return {"status": "failed", "error": str(exc)}

    def generate_rebalancing_orders(
        self,
        context: StrategyContext,
        rebalancing_plan: Dict[str, Any],
    ) -> List[TradingDecision]:
        portfolio_text = format_portfolio_snapshot(context.portfolio)
        plan_body = rebalancing_plan.get("rebalancing_plan", rebalancing_plan)

        prompt = f"""
        Rebalancing Plan:
        {plan_body}

        {portfolio_text}

        Provide specific orders respecting available shares and buying power:
        1. Action (BUY/SELL)
        2. Symbol
        3. Quantity (integer only, no ALL)
        4. Reason
        """

        try:
            response = self.llm_client.generate_response(prompt)
            return self._parse_orders(response)
        except Exception as exc:
            logger.error("Error generating rebalancing orders: %s", exc)
            return []

    def _parse_rebalancing_plan(self, llm_response: str) -> Dict[str, Any]:
        plan: Dict[str, Any] = {}
        lines = llm_response.split("\n")
        current_section = None
        current_content: List[str] = []

        for line in lines:
            line = line.strip()
            if line.startswith("1. Target Allocation"):
                if current_section:
                    plan[current_section] = "\n".join(current_content)
                current_section = "target_allocation"
                current_content = []
            elif line.startswith("2. Required Changes"):
                if current_section:
                    plan[current_section] = "\n".join(current_content)
                current_section = "required_changes"
                current_content = []
            elif line.startswith("3. Reasoning"):
                if current_section:
                    plan[current_section] = "\n".join(current_content)
                current_section = "reasoning"
                current_content = []
            elif line and current_section:
                current_content.append(line)

        if current_section:
            plan[current_section] = "\n".join(current_content)
        return plan

    def _parse_orders(self, llm_response: str) -> List[TradingDecision]:
        orders: List[TradingDecision] = []
        current: Dict[str, Any] = {}

        for line in llm_response.split("\n"):
            line = line.strip()
            if line.startswith("1. Action"):
                if current:
                    orders.append(self._order_from_dict(current))
                current = {"action": line.split(":", 1)[1].strip()}
            elif line.startswith("2. Symbol"):
                current["symbol"] = line.split(":", 1)[1].strip()
            elif line.startswith("3. Quantity"):
                qty_raw = line.split(":", 1)[1].strip()
                try:
                    current["quantity"] = int(qty_raw)
                except ValueError:
                    continue
            elif line.startswith("4. Reason"):
                current["reason"] = line.split(":", 1)[1].strip()

        if current:
            orders.append(self._order_from_dict(current))
        return orders

    def _order_from_dict(self, data: Dict[str, Any]) -> TradingDecision:
        return TradingDecision(
            action=str(data.get("action", "")).upper(),
            symbol=str(data.get("symbol", "")).upper(),
            quantity=data.get("quantity", 0),
            reasoning=str(data.get("reason", "")),
            risk_level="medium",
            source="rebalancer",
        )
