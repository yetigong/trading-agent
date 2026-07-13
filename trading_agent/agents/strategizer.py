"""Trading Strategizer — propose/select strategy and produce trade decisions."""

from typing import Any, Dict, Optional

from trading_agent.agents.base import ConfigurableAgent
from strategy_learning.knowledge import KnowledgeBase
from trading_agent.agents.messages import StrategyOption, StrategyPlan
from trading_agent.domain.cycle import StrategyContext
from trading_agent.domain.user.user_preferences import UserPreferences
from trading_agent.portfolio.rebalancer import PortfolioRebalancer
from trading_agent.strategies.general import GeneralTradingStrategy


class TradingStrategizerAgent(ConfigurableAgent):
    name = "trading_strategizer"

    def __init__(
        self,
        trading_strategy: GeneralTradingStrategy,
        portfolio_rebalancer: PortfolioRebalancer,
        user_preferences: UserPreferences,
        knowledge_base: Optional[KnowledgeBase] = None,
        enabled: bool = True,
    ):
        super().__init__(enabled=enabled)
        self.trading_strategy = trading_strategy
        self.portfolio_rebalancer = portfolio_rebalancer
        self.user_preferences = user_preferences
        self.knowledge_base = knowledge_base or KnowledgeBase()

    def run(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        market_conditions = ctx["market_conditions"]
        market_analysis = ctx["market_analysis"]
        portfolio = ctx["portfolio"]
        strategy_params = dict(ctx.get("strategy_params") or {})
        rebalance_params = dict(ctx.get("rebalance_params") or {})
        analysis_params = dict(ctx.get("analysis_params") or {})

        # Soft KB prefs first; active config (strategy_params) wins on key conflicts.
        prefs = self.knowledge_base.strategy_preferences()
        if prefs:
            strategy_params = {**prefs, **strategy_params}

        lessons = self.knowledge_base.lessons_for_prompt()
        if lessons:
            strategy_params["knowledge_lessons"] = lessons

        validation = self.knowledge_base.active_backtest_validation()
        if validation:
            strategy_params["backtest_validation_summary"] = validation.get(
                "summary"
            ) or validation.get("id")

        universe_symbols = [
            str(s).upper()
            for s in (ctx.get("universe_symbols") or [])
            if s
        ]
        context = StrategyContext(
            market_conditions=market_conditions,
            market_analysis=market_analysis,
            portfolio=portfolio,
            user_preferences=self.user_preferences,
            strategy_params=strategy_params,
            rebalance_params=rebalance_params,
            analysis_params=analysis_params,
            universe_symbols=universe_symbols,
        )

        decisions = self.trading_strategy.make_decisions(context)
        strategy_hold = len(decisions) == 0

        rebalancing = self.portfolio_rebalancer.rebalance_portfolio(context)
        if rebalancing.get("status") == "success":
            rebalance_orders = self.portfolio_rebalancer.generate_rebalancing_orders(
                context, rebalancing
            )
            decisions.extend(rebalance_orders)

        option = StrategyOption(
            name=self.trading_strategy.get_strategy_name(),
            rationale="Primary LLM strategy with optional rebalancer overlay",
            trade_offs="Single-option v1; multi-option bake-off deferred",
            decisions=list(decisions),
        )
        plan = StrategyPlan(
            options=[option],
            selected=option,
            decisions=decisions,
            rebalancing=rebalancing,
            strategy_hold=strategy_hold,
            preferences_applied=prefs,
        )

        ctx["strategy_context"] = context
        ctx["strategy_plan"] = plan
        ctx["decisions"] = decisions
        ctx["rebalancing"] = rebalancing
        ctx["strategy_hold"] = strategy_hold
        return {"strategy_plan": plan}
