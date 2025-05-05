import time
import threading
import unittest
import logging
from scheduler.scheduler import TradingScheduler
from agent.trading_cycle import TradingCycle

def setup_logging():
    """Configure logging for tests."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        force=True  # Override any existing logging configuration
    )

class TestScheduler(unittest.TestCase):
    def setUp(self):
        """Set up test case."""
        setup_logging()
        self.logger = logging.getLogger(__name__)
        self.logger.info("Setting up test case")

    def test_scheduler_two_cycles(self):
        results = []
        
        class TestTradingCycle(TradingCycle):
            def __init__(self):
                super().__init__()
                self.logger = logging.getLogger(__name__)
            
            def run_cycle(self):
                self.logger.info("Running test trading cycle")
                results.append('cycle_completed')
                return {'success': True}

        # Create test trading cycle instance
        test_cycle = TestTradingCycle()
        
        # Use a short interval for testing (10 seconds = 1/6 minute)
        scheduler = TradingScheduler(interval_minutes=1/6)
        
        # Run the scheduler in a separate thread so we can stop it after 2 cycles
        def run_scheduler():
            scheduler.start(test_cycle.run_cycle)

        self.logger.info("Starting scheduler thread")
        thread = threading.Thread(target=run_scheduler)
        thread.start()

        # Wait for 25 seconds to allow 2 cycles (10s interval)
        self.logger.info("Waiting for cycles to complete")
        time.sleep(25)
        
        # Stop the scheduler
        self.logger.info("Stopping scheduler")
        scheduler.stop()
        thread.join(timeout=5)  # Wait up to 5 seconds for the thread to finish

        self.assertGreaterEqual(len(results), 2, f"Expected at least 2 cycles, got {len(results)}")
        self.logger.info(f"Test passed: Scheduler completed {len(results)} cycles")

if __name__ == "__main__":
    unittest.main() 