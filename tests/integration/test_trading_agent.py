import unittest
from unittest.mock import Mock, patch
from datetime import datetime
from trader import TradingAgent
from trading_agent.market_data.alpaca_provider import AlpacaMarketDataProvider
from trading_agent.llm.client import get_llm_client
from alpaca_client import AlpacaTradingClient

class TestTradingAgentIntegration(unittest.TestCase):
    def setUp(self):
        # Create mock components
        self.mock_market_data = Mock(spec=AlpacaMarketDataProvider)
        self.mock_llm_client = Mock(spec=get_llm_client)
        self.mock_alpaca_client = Mock(spec=AlpacaTradingClient)

        # Create trading agent with mock components
        self.agent = TradingAgent(
            risk_tolerance="moderate",
            investment_goal="growth",
            max_position_size=0.1,
            llm_client=self.mock_llm_client,
            market_data_provider=self.mock_market_data,
            alpaca_client=self.mock_alpaca_client
        )

    @patch('trader.logger')
    def test_full_trading_cycle(self, mock_logger):
        """Test a complete trading cycle"""
        # Mock market data
        self.mock_market_data.get_market_data.return_value = {
            'symbols': ['AAPL', 'GOOGL'],
            'prices': {'AAPL': 150.0, 'GOOGL': 2800.0},
            'timestamp': datetime.now()
        }

        # Mock LLM analysis
        self.mock_llm_client.analyze_market.return_value = {
            'recommendations': [
                {'symbol': 'AAPL', 'action': 'buy', 'confidence': 0.8},
                {'symbol': 'GOOGL', 'action': 'hold', 'confidence': 0.6}
            ]
        }

        # Mock trade execution
        self.mock_alpaca_client.execute_trade.return_value = {
            'success': True,
            'order_id': '12345',
            'symbol': 'AAPL',
            'side': 'buy',
            'quantity': 10,
            'price': 150.0
        }

        # Run trading cycle
        result = self.agent.run_trading_cycle(
            analysis_params={
                "time_horizon": "medium-term",
                "focus_areas": "tech",
                "regions": "US"
            },
            strategy_params={
                "timeframe": "immediate",
                "risk_management": "standard",
                "position_sizing": "dynamic"
            },
            rebalance_params={
                "target_allocation": "balanced",
                "threshold": 5,
                "sector_weights": "market_cap"
            }
        )

        # Verify results
        self.assertTrue(result['success'])
        self.assertIn('trades', result)
        self.assertIn('analysis', result)
        mock_logger.info.assert_called()

    @patch('trader.logger')
    def test_error_handling(self, mock_logger):
        """Test error handling in trading cycle"""
        # Mock market data error
        self.mock_market_data.get_market_data.side_effect = Exception("Market data error")

        # Run trading cycle
        result = self.agent.run_trading_cycle(
            analysis_params={},
            strategy_params={},
            rebalance_params={}
        )

        # Verify error handling
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        mock_logger.error.assert_called()

    def test_portfolio_rebalancing(self):
        """Test portfolio rebalancing functionality"""
        # Mock current portfolio
        current_portfolio = {
            'AAPL': {'quantity': 100, 'value': 15000.0},
            'GOOGL': {'quantity': 5, 'value': 14000.0}
        }

        # Mock target allocation
        target_allocation = {
            'AAPL': 0.5,
            'GOOGL': 0.5
        }

        # Calculate rebalancing trades
        rebalance_trades = self.agent.calculate_rebalance_trades(
            current_portfolio,
            target_allocation,
            threshold=5
        )

        # Verify rebalancing trades
        self.assertIsNotNone(rebalance_trades)
        self.assertIn('trades', rebalance_trades)
        self.assertIn('analysis', rebalance_trades)

if __name__ == '__main__':
    unittest.main() 