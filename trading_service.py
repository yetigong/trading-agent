import logging
from scheduler.scheduler import TradingScheduler
from agent.trading_cycle import TradingCycle

def setup_logging():
    """Configure logging for the trading service."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('trading_service.log')
        ]
    )

def main():
    """Main entry point for the trading service."""
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Create trading cycle instance
        trading_cycle = TradingCycle()
        
        # Create and start scheduler
        scheduler = TradingScheduler(interval_minutes=30)
        logger.info("Starting trading service with enhanced logging...")
        scheduler.start(trading_cycle.execute)
        
    except Exception as e:
        logger.error(f"Fatal error in trading service: {str(e)}")
        raise

if __name__ == "__main__":
    main() 