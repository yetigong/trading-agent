import unittest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from trading_agent.scheduler import TradingScheduler
from trading_agent.trading_cycle import TradingCycle

class TestTradingScheduler(unittest.TestCase):
    def setUp(self):
        self.mock_trading_cycle = Mock(spec=TradingCycle)
        self.scheduler = TradingScheduler(trading_cycle=self.mock_trading_cycle)

    def test_initialize_success(self):
        """Test successful initialization of scheduler"""
        self.assertIsNotNone(self.scheduler)
        self.assertEqual(self.scheduler.trading_cycle, self.mock_trading_cycle)
        self.assertFalse(self.scheduler.is_running)

    @patch('trading_agent.scheduler.logger')
    def test_start_scheduler_success(self, mock_logger):
        """Test successful scheduler start"""
        # Mock trading cycle result
        self.mock_trading_cycle.run_cycle.return_value = {
            'success': True,
            'trades': [],
            'analysis': {}
        }

        # Start scheduler
        self.scheduler.start(interval=1)  # 1 second interval for testing
        self.assertTrue(self.scheduler.is_running)
        mock_logger.info.assert_called()

    @patch('trading_agent.scheduler.logger')
    def test_stop_scheduler_success(self, mock_logger):
        """Test successful scheduler stop"""
        # Start scheduler
        self.scheduler.start(interval=1)
        self.assertTrue(self.scheduler.is_running)

        # Stop scheduler
        self.scheduler.stop()
        self.assertFalse(self.scheduler.is_running)
        mock_logger.info.assert_called()

    @patch('trading_agent.scheduler.logger')
    def test_scheduler_error_handling(self, mock_logger):
        """Test scheduler error handling"""
        # Mock trading cycle error
        self.mock_trading_cycle.run_cycle.side_effect = Exception("Test error")

        # Start scheduler
        self.scheduler.start(interval=1)
        
        # Wait for one cycle
        import time
        time.sleep(1.1)
        
        # Stop scheduler
        self.scheduler.stop()
        
        # Verify error was logged
        mock_logger.error.assert_called()

    def test_validate_schedule(self):
        """Test schedule validation"""
        # Valid schedule
        valid_schedule = {
            'interval': 60,
            'start_time': datetime.now(),
            'end_time': datetime.now() + timedelta(hours=1)
        }
        self.assertTrue(self.scheduler.validate_schedule(valid_schedule))

        # Invalid schedule
        invalid_schedule = {
            'interval': -60,
            'start_time': None,
            'end_time': None
        }
        self.assertFalse(self.scheduler.validate_schedule(invalid_schedule))

    @patch('trading_agent.scheduler.logger')
    def test_handle_scheduler_error(self, mock_logger):
        """Test error handling for scheduler"""
        error = Exception("Test error")
        self.scheduler.handle_scheduler_error(error)
        mock_logger.error.assert_called()

    def test_schedule_validation(self):
        """Test schedule time validation"""
        now = datetime.now()
        
        # Valid times
        valid_times = {
            'start': now,
            'end': now + timedelta(hours=1)
        }
        self.assertTrue(self.scheduler.validate_schedule_times(valid_times))

        # Invalid times (end before start)
        invalid_times = {
            'start': now,
            'end': now - timedelta(hours=1)
        }
        self.assertFalse(self.scheduler.validate_schedule_times(invalid_times))

if __name__ == '__main__':
    unittest.main() 