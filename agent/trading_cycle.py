from trader import TradingAgent
from trading_agent.llm.client import get_llm_client
from trading_agent.market_data.alpaca_provider import AlpacaMarketDataProvider
from alpaca_client import AlpacaTradingClient
import json
from datetime import datetime
from dotenv import load_dotenv
import os
import logging

class TradingCycle:
    """Handles the execution of a single trading cycle."""
    
    def __init__(self):
        """Initialize the trading cycle with default parameters."""
        self.logger = logging.getLogger(__name__)
        load_dotenv()
        
        # Default parameters
        self.analysis_params = {
            "time_horizon": "medium-term",
            "focus_areas": "tech, healthcare",
            "regions": "US"
        }
        
        self.strategy_params = {
            "timeframe": "immediate",
            "risk_management": "standard",
            "position_sizing": "dynamic"
        }
        
        self.rebalance_params = {
            "target_allocation": "balanced",
            "threshold": 5,
            "sector_weights": "market_cap"
        }
    
    def initialize_components(self):
        """Initialize all required components for trading."""
        self.logger.info("Initializing components...")
        
        # Initialize real providers
        self.logger.info("Initializing LLM client...")
        self.llm_client = get_llm_client("gemini", model="financial")
        
        self.logger.info("Initializing market data provider...")
        self.market_data_provider = AlpacaMarketDataProvider()
        
        self.logger.info("Initializing Alpaca client...")
        self.alpaca_client = AlpacaTradingClient()
        
        self.logger.info("Creating trading agent...")
        self.agent = TradingAgent(
            risk_tolerance="moderate",
            investment_goal="growth",
            max_position_size=0.1,
            llm_client=self.llm_client,
            market_data_provider=self.market_data_provider,
            alpaca_client=self.alpaca_client
        )
    
    def execute(self):
        """Execute a complete trading cycle."""
        cycle_start_time = datetime.now()
        self.logger.info("=" * 80)
        self.logger.info(f"Starting new trading cycle at {cycle_start_time}")
        self.logger.info("=" * 80)
        
        try:
            # Initialize components
            self.initialize_components()
            
            # Log cycle start
            self.logger.info(f"Analysis parameters: {json.dumps(self.analysis_params, indent=2)}")
            self.logger.info(f"Strategy parameters: {json.dumps(self.strategy_params, indent=2)}")
            self.logger.info(f"Rebalancing parameters: {json.dumps(self.rebalance_params, indent=2)}")
            
            # Run trading cycle
            results = self.agent.run_trading_cycle(
                analysis_params=self.analysis_params,
                strategy_params=self.strategy_params,
                rebalance_params=self.rebalance_params
            )
            
            # Log results
            self.logger.info(f"Trading cycle completed with status: {results['status']}")
            
            if results['status'] == 'success':
                self.logger.info(f"Selected analysis strategy: {results['analysis_strategy']}")
                self.logger.info(f"Market analysis: {results['analysis']['analysis']}")
                
                for decision in results['decisions']:
                    self.logger.info(f"Trading decision: {json.dumps(decision, indent=2)}")
                
                if results['rebalancing']:
                    self.logger.info(f"Portfolio rebalancing: {json.dumps(results['rebalancing'], indent=2)}")
                
                for trade in results['executed_trades']:
                    self.logger.info(f"Executed trade: {json.dumps(trade, indent=2)}")
            else:
                self.logger.error(f"Trading cycle failed: {results.get('error', 'Unknown error')}")
            
            # Generate cycle summary
            cycle_end_time = datetime.now()
            cycle_duration = cycle_end_time - cycle_start_time
            
            self.logger.info("=" * 80)
            self.logger.info("TRADING CYCLE SUMMARY")
            self.logger.info("=" * 80)
            self.logger.info(f"Start Time: {cycle_start_time}")
            self.logger.info(f"End Time: {cycle_end_time}")
            self.logger.info(f"Duration: {cycle_duration}")
            self.logger.info(f"Status: {results['status']}")
            
            if results['status'] == 'success':
                self.logger.info("\nOperations Summary:")
                self.logger.info(f"- Analysis Strategy: {results['analysis_strategy']}")
                self.logger.info(f"- Number of Trading Decisions: {len(results['decisions'])}")
                self.logger.info(f"- Portfolio Rebalancing: {'Yes' if results['rebalancing'] else 'No'}")
                self.logger.info(f"- Number of Executed Trades: {len(results['executed_trades'])}")
                
                # Count successful and failed trades
                successful_trades = sum(1 for trade in results['executed_trades'] if trade['status'] == 'executed')
                failed_trades = sum(1 for trade in results['executed_trades'] if trade['status'] == 'failed')
                self.logger.info(f"- Successful Trades: {successful_trades}")
                self.logger.info(f"- Failed Trades: {failed_trades}")
            
            self.logger.info("=" * 80)
            self.logger.info("Trading cycle completed")
            self.logger.info("=" * 80)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error in trading cycle: {str(e)}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Log cycle failure summary
            cycle_end_time = datetime.now()
            cycle_duration = cycle_end_time - cycle_start_time
            
            self.logger.info("=" * 80)
            self.logger.info("TRADING CYCLE FAILED")
            self.logger.info("=" * 80)
            self.logger.info(f"Start Time: {cycle_start_time}")
            self.logger.info(f"End Time: {cycle_end_time}")
            self.logger.info(f"Duration: {cycle_duration}")
            self.logger.info(f"Error: {str(e)}")
            self.logger.info("=" * 80)
            
            raise 