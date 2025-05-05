import schedule
import time
import logging
from typing import Callable

class TradingScheduler:
    """Scheduler for running trading cycles at regular intervals."""
    
    def __init__(self, interval_minutes: int = 30):
        """
        Initialize the trading scheduler.
        
        Args:
            interval_minutes: Interval between trading cycles in minutes
        """
        self.interval_minutes = interval_minutes
        self.logger = logging.getLogger(__name__)
        self._running = False
    
    def start(self, trading_cycle_func: Callable):
        """
        Start the scheduler with the given trading cycle function.
        
        Args:
            trading_cycle_func: Function to execute for each trading cycle
        """
        self.logger.info(f"Starting trading scheduler with {self.interval_minutes} minute interval")
        
        # Schedule the trading cycle
        schedule.every(self.interval_minutes).minutes.do(trading_cycle_func)
        
        # Run immediately on startup
        trading_cycle_func()
        
        # Keep the scheduler running
        self._running = True
        while self._running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except KeyboardInterrupt:
                self.logger.info("Trading scheduler stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Error in scheduler: {str(e)}")
                time.sleep(60)  # Wait a minute before retrying
    
    def stop(self):
        """Stop the scheduler."""
        self.logger.info("Stopping trading scheduler")
        self._running = False
        schedule.clear()  # Clear all scheduled jobs 