from agent.trading_cycle import TradingCycle
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/trading_agent.log')
    ]
)

def main():
    try:
        # Create and run trading cycle
        cycle = TradingCycle()
        cycle.execute()
    except Exception as e:
        logging.error(f"Trading agent failed: {str(e)}")
        raise

if __name__ == "__main__":
    main() 