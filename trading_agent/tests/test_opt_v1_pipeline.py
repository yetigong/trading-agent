import unittest

from trading_agent.analysis.runner import AnalysisRunner
from trading_agent.domain.cycle import MarketAnalysis, StrategyContext
from trading_agent.domain.portfolio.portfolio_snapshot import (
    AccountSummary,
    PortfolioSnapshot,
)
from trading_agent.domain.signals.market_conditions import MarketConditions
from trading_agent.domain.signals.market_signals import (
    FundamentalSignals,
    MarketSignals,
)
from trading_agent.domain.user.user_preferences import UserPreferences
from trading_agent.formatters.strategy_context import format_strategy_context
from trading_agent.llm.mock_client import MockLLMClient
from trading_agent.signals.sources import MAX_SYMBOLS, SignalCollectionContext


class TestEmptyFundamentalsSkip(unittest.TestCase):
    def test_skips_fundamental_llm_when_metrics_empty(self):
        llm = MockLLMClient()
        prompts = []
        original = llm.generate_response

        def track(prompt, context=None):
            prompts.append(prompt)
            return original(prompt, context)

        llm.generate_response = track
        runner = AnalysisRunner(llm_client=llm)
        portfolio = PortfolioSnapshot(account=AccountSummary(buying_power=10000))
        signals = MarketSignals(fundamentals=FundamentalSignals(metrics={}))
        conditions = MarketConditions(
            volatility="moderate",
            trend="bullish",
            economic_cycle="expansion",
            market_phase="normal",
        )
        analysis = runner.run(
            portfolio=portfolio,
            signals=signals,
            market_conditions=conditions,
            user_preferences=UserPreferences(),
        )
        self.assertIsNotNone(analysis.fundamental)
        self.assertEqual(analysis.fundamental.status, "skipped")
        self.assertIn("no fundamental metrics", analysis.fundamental.summary.lower())
        prompt_blob = " ".join(prompts).lower()
        self.assertNotIn("provide fundamental analysis", prompt_blob)

    def test_runs_fundamental_when_metrics_present(self):
        llm = MockLLMClient()
        prompts = []
        original = llm.generate_response

        def track(prompt, context=None):
            prompts.append(prompt)
            return original(prompt, context)

        llm.generate_response = track
        runner = AnalysisRunner(llm_client=llm)
        portfolio = PortfolioSnapshot(account=AccountSummary(buying_power=10000))
        signals = MarketSignals(
            fundamentals=FundamentalSignals(metrics={"AAPL": {"pe": 20.0}})
        )
        conditions = MarketConditions(
            volatility="moderate",
            trend="bullish",
            economic_cycle="expansion",
            market_phase="normal",
        )
        analysis = runner.run(
            portfolio=portfolio,
            signals=signals,
            market_conditions=conditions,
            user_preferences=UserPreferences(),
        )
        self.assertEqual(analysis.fundamental.status, "success")
        prompt_blob = " ".join(prompts).lower()
        self.assertIn("provide fundamental analysis", prompt_blob)


class TestStrategyContextUniverse(unittest.TestCase):
    def test_format_includes_universe_symbols(self):
        context = StrategyContext(
            market_conditions=MarketConditions(
                volatility="moderate",
                trend="bullish",
                economic_cycle="expansion",
                market_phase="normal",
            ),
            market_analysis=MarketAnalysis(),
            portfolio=PortfolioSnapshot(account=AccountSummary(buying_power=10000)),
            user_preferences=UserPreferences(max_position_size=0.25),
            universe_symbols=["SPY", "QQQ", "TSLA", "NVDA"],
        )
        text = format_strategy_context(context)
        self.assertIn("Tradable Universe", text)
        self.assertIn("SPY", text)
        self.assertIn("NVDA", text)
        self.assertIn("25%", text)


class TestSignalUniverseCap(unittest.TestCase):
    def test_max_symbols_covers_expanded_universe(self):
        self.assertGreaterEqual(MAX_SYMBOLS, 13)
        symbols = [
            "SPY",
            "QQQ",
            "XLK",
            "XLV",
            "XLE",
            "XLI",
            "XLY",
            "IWM",
            "TSLA",
            "NVDA",
            "MSFT",
            "PLTR",
            "GLD",
        ]
        ctx = SignalCollectionContext.from_inputs(
            market_conditions=MarketConditions(
                volatility="moderate",
                trend="bullish",
                economic_cycle="expansion",
                market_phase="normal",
            ),
            universe_symbols=symbols,
        )
        self.assertEqual(ctx.symbols, symbols)


if __name__ == "__main__":
    unittest.main()
