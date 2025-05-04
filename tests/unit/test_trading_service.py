import unittest
from unittest.mock import Mock, patch
from datetime import datetime
from trading_agent.trading_service import TradingService
from trading_agent.market_data.alpaca_provider import AlpacaMarketDataProvider
from trading_agent.llm.client import get_llm_client

class TestTradingService(unittest.TestCase):
    def setUp(self):
        self.mock_market_data = Mock(spec=AlpacaMarketDataProvider)
        self.mock_llm_client = Mock(spec=get_llm_client)
        self.trading_service = TradingService(
            market_data_provider=self.mock_market_data,
            llm_client=self.mock_llm_client
        )

    def test_initialize_success(self):
        """Test successful initialization of trading service"""
        self.assertIsNotNone(self.trading_service)
        self.assertEqual(self.trading_service.market_data_provider, self.mock_market_data)
        self.assertEqual(self.trading_service.llm_client, self.mock_llm_client)

    @patch('trading_agent.trading_service.logger')
    def test_execute_trade_success(self, mock_logger):
        """Test successful trade execution"""
        # Mock trade data
        trade_data = {
            'symbol': 'AAPL',
            'side': 'buy',
            'quantity': 10,
            'price': 150.0
        }
        
        # Mock market data response
        self.mock_market_data.get_market_data.return_value = {
            'price': 150.0,
            'volume': 1000000,
            'timestamp': datetime.now()
        }

        # Execute trade
        result = self.trading_service.execute_trade(trade_data)

        # Verify results
        self.assertTrue(result['success'])
        self.assertEqual(result['symbol'], 'AAPL')
        mock_logger.info.assert_called()

    @patch('trading_agent.trading_service.logger')
    def test_execute_trade_failure(self, mock_logger):
        """Test trade execution failure"""
        # Mock trade data
        trade_data = {
            'symbol': 'INVALID',
            'side': 'buy',
            'quantity': 10,
            'price': 150.0
        }
        
        # Mock market data error
        self.mock_market_data.get_market_data.side_effect = Exception("Market data error")

        # Execute trade
        result = self.trading_service.execute_trade(trade_data)

        # Verify results
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        mock_logger.error.assert_called()

    def test_validate_trade_data(self):
        """Test trade data validation"""
        # Valid trade data
        valid_trade = {
            'symbol': 'AAPL',
            'side': 'buy',
            'quantity': 10,
            'price': 150.0
        }
        self.assertTrue(self.trading_service.validate_trade_data(valid_trade))

        # Invalid trade data
        invalid_trade = {
            'symbol': 'AAPL',
            'side': 'invalid',
            'quantity': -10,
            'price': -150.0
        }
        self.assertFalse(self.trading_service.validate_trade_data(invalid_trade))

    @patch('trading_agent.trading_service.logger')
    def test_handle_trade_error(self, mock_logger):
        """Test error handling for trades"""
        error = Exception("Test error")
        result = self.trading_service.handle_trade_error(error, 'AAPL')
        
        self.assertFalse(result['success'])
        self.assertEqual(result['symbol'], 'AAPL')
        self.assertIn('error', result)
        mock_logger.error.assert_called()

if __name__ == '__main__':
    unittest.main() 