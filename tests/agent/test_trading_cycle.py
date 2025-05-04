import unittest
from unittest.mock import Mock, patch
from datetime import datetime
from agent.trading_cycle import TradingCycle
from trading_agent.market_data.alpaca_provider import AlpacaMarketDataProvider
from trading_agent.llm.client import get_llm_client

class TestTradingCycle(unittest.TestCase):
    def setUp(self):
        self.mock_market_data = Mock(spec=AlpacaMarketDataProvider)
        self.mock_llm_client = Mock()  # Remove spec to allow any method
        self.trading_cycle = TradingCycle(
            market_data_provider=self.mock_market_data,
            llm_client=self.mock_llm_client
        )

    def test_initialize_success(self):
        """Test successful initialization of trading cycle"""
        self.assertIsNotNone(self.trading_cycle)
        self.assertEqual(self.trading_cycle.market_data_provider, self.mock_market_data)
        self.assertEqual(self.trading_cycle.llm_client, self.mock_llm_client)

    def test_run_cycle_success(self):
        """Test successful trading cycle execution"""
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

        # Run cycle
        result = self.trading_cycle.run_cycle()

        # Verify results
        self.assertTrue(result['success'])
        self.assertIn('trades', result)
        self.assertIn('analysis', result)

    def test_run_cycle_failure(self):
        """Test trading cycle execution failure"""
        # Mock market data error
        self.mock_market_data.get_market_data.side_effect = Exception("Market data error")

        # Run cycle
        result = self.trading_cycle.run_cycle()

        # Verify results
        self.assertFalse(result['success'])
        self.assertIn('error', result)

    def test_validate_cycle_data(self):
        """Test cycle data validation"""
        # Valid cycle data
        valid_data = {
            'symbols': ['AAPL', 'GOOGL'],
            'prices': {'AAPL': 150.0, 'GOOGL': 2800.0},
            'timestamp': datetime.now()
        }
        self.assertTrue(self.trading_cycle.validate_cycle_data(valid_data))

        # Invalid cycle data
        invalid_data = {
            'symbols': [],
            'prices': {},
            'timestamp': None
        }
        self.assertFalse(self.trading_cycle.validate_cycle_data(invalid_data))

    def test_handle_cycle_error(self):
        """Test error handling for trading cycle"""
        error = Exception("Test error")
        result = self.trading_cycle.handle_cycle_error(error)
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)

    def test_process_recommendations(self):
        """Test processing of trading recommendations"""
        recommendations = [
            {'symbol': 'AAPL', 'action': 'buy', 'confidence': 0.8},
            {'symbol': 'GOOGL', 'action': 'sell', 'confidence': 0.7},
            {'symbol': 'MSFT', 'action': 'hold', 'confidence': 0.6}
        ]

        processed = self.trading_cycle.process_recommendations(recommendations)
        
        self.assertIn('buy', processed)
        self.assertIn('sell', processed)
        self.assertIn('hold', processed)
        self.assertEqual(len(processed['buy']), 1)
        self.assertEqual(len(processed['sell']), 1)
        self.assertEqual(len(processed['hold']), 1)

if __name__ == '__main__':
    unittest.main() 