from trader import TradingAgent
from trading_agent.llm.client import get_llm_client
from trading_agent.market_data.alpaca_provider import AlpacaMarketDataProvider
from alpaca_client import AlpacaTradingClient
import json
from datetime import datetime
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

def run_trading_cycle():
    print("\nInitializing components...")
    
    # Initialize real providers
    print("Initializing LLM client...")
    llm_client = get_llm_client("claude", model="financial")  # Using Claude with financial model
    
    print("Initializing market data provider...")
    market_data_provider = AlpacaMarketDataProvider()
    
    print("Initializing Alpaca client...")
    alpaca_client = AlpacaTradingClient()
    
    # Create trading agent with user preferences
    print("Creating trading agent...")
    agent = TradingAgent(
        risk_tolerance="moderate",
        investment_goal="growth",
        max_position_size=0.1,
        llm_client=llm_client,
        market_data_provider=market_data_provider,
        alpaca_client=alpaca_client
    )
    
    # Define parameters for the trading cycle
    analysis_params = {
        "time_horizon": "medium-term",
        "focus_areas": "tech, healthcare",
        "regions": "US"
    }
    
    strategy_params = {
        "timeframe": "immediate",
        "risk_management": "standard",
        "position_sizing": "dynamic"
    }
    
    rebalance_params = {
        "target_allocation": "balanced",
        "threshold": 5,
        "sector_weights": "market_cap"
    }
    
    print("\nStarting Trading Cycle...")
    print(f"Timestamp: {datetime.now()}")
    print("\nParameters:")
    print(f"Analysis: {json.dumps(analysis_params, indent=2)}")
    print(f"Strategy: {json.dumps(strategy_params, indent=2)}")
    print(f"Rebalancing: {json.dumps(rebalance_params, indent=2)}")
    
    try:
        # Run a trading cycle
        print("\nRunning trading cycle...")
        results = agent.run_trading_cycle(
            analysis_params=analysis_params,
            strategy_params=strategy_params,
            rebalance_params=rebalance_params
        )
        
        # Print results
        print("\nTrading Cycle Results:")
        print(f"Status: {results['status']}")
        
        if results['status'] == 'success':
            print("\nSelected Analysis Strategy:")
            print(results['analysis_strategy'])
            
            print("\nMarket Analysis:")
            print(results['analysis']['analysis'])
            
            print("\nTrading Decisions:")
            for decision in results['decisions']:
                print(f"\nAction: {decision['action']}")
                print(f"Symbol: {decision['symbol']}")
                print(f"Quantity: {decision['quantity']}")
                if 'reasoning' in decision:
                    print(f"Reasoning: {decision['reasoning']}")
                if 'risk_level' in decision:
                    print(f"Risk Level: {decision['risk_level']}")
            
            if results['rebalancing']:
                print("\nPortfolio Rebalancing:")
                print(results['rebalancing']['rebalancing_plan'])
            
            print("\nExecuted Trades:")
            for trade in results['executed_trades']:
                print(f"\nSymbol: {trade['symbol']}")
                print(f"Status: {trade['status']}")
                if trade['status'] == 'failed':
                    print(f"Error: {trade['error']}")
        else:
            print(f"Error: {results.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"\nError running trading cycle: {str(e)}")
        import traceback
        print("\nTraceback:")
        print(traceback.format_exc())

if __name__ == "__main__":
    try:
        run_trading_cycle()
    except Exception as e:
        print(f"Error running trading cycle: {str(e)}") 