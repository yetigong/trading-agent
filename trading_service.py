import logging
from scheduler.scheduler import TradingScheduler
from agent.trading_cycle import TradingCycle
from trading_agent.config import get_config

def setup_logging(log_level: str = "INFO"):
    """Configure logging for the trading service."""
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('trading_service.log')
        ]
    )

def main():
    """Main entry point for the trading service."""
    config = get_config()
    setup_logging(config.log_level)
    logger = logging.getLogger(__name__)
    
    try:
        trading_cycle = TradingCycle()
        scheduler = TradingScheduler(interval_minutes=config.trading_cycle_interval)
        logger.info(
            "Starting trading service (interval=%d min, llm=%s)...",
            config.trading_cycle_interval,
            config.llm_provider,
        )
        scheduler.start(trading_cycle.execute)
        
    except Exception as e:
        logger.error(f"Fatal error in trading service: {str(e)}")
        raise

if __name__ == "__main__":
    main() 