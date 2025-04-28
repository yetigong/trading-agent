import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from alpaca_client import AlpacaTradingClient
from alpaca.trading.enums import OrderSide
from trading_agent.analysis.selector import AnalysisStrategySelector
from trading_agent.strategies.general import GeneralTradingStrategy
from trading_agent.portfolio.rebalancer import PortfolioRebalancer
from trading_agent.market_data.alpaca_provider import AlpacaMarketDataProvider
from trading_agent.market_data.base import MarketDataProvider
from trading_agent.llm.client import get_llm_client, LLMClient

class TradingAgent:
    def __init__(self, 
                 risk_tolerance: str = "moderate",  # low, moderate, high
                 investment_goal: str = "growth",   # income, growth, balanced
                 max_position_size: float = 0.1,    # maximum 10% of portfolio per position
                 llm_client: Optional[LLMClient] = None,
                 client_type: str = "openai",
                 market_data_provider: Optional[MarketDataProvider] = None,
                 **kwargs):
        """
        Initialize the trading agent with user preferences and configuration.
        
        Args:
            risk_tolerance: User's risk tolerance level
            investment_goal: User's investment goal
            max_position_size: Maximum position size as a fraction of portfolio
            llm_client: Optional LLM client instance
            client_type: Type of LLM client to use if llm_client is not provided
            market_data_provider: Optional market data provider instance
            **kwargs: Additional arguments to pass to the LLM client
        """
        load_dotenv()
        
        # Initialize LLM client
        self.llm_client = llm_client or get_llm_client(client_type, **kwargs)
        
        # Initialize components
        self.strategy_selector = AnalysisStrategySelector(llm_client=self.llm_client)
        self.trading_strategy = GeneralTradingStrategy(llm_client=self.llm_client)
        self.portfolio_rebalancer = PortfolioRebalancer(llm_client=self.llm_client)
        self.market_data_provider = market_data_provider or AlpacaMarketDataProvider()
        
        # Initialize Alpaca client
        self.alpaca_client = AlpacaTradingClient()
        
        # User preferences
        self.user_preferences = {
            "risk_tolerance": risk_tolerance,
            "investment_goal": investment_goal,
            "max_position_size": max_position_size,
            "investment_horizon": "medium-term"  # short-term, medium-term, long-term
        }
        
        # Portfolio tracking
        self.portfolio = {}
        self.last_analysis = None
        self.last_rebalancing = None
        self.current_analysis_strategy = None
    
    def get_portfolio_data(self) -> Dict[str, Any]:
        """Get current portfolio data from Alpaca."""
        account = self.alpaca_client.get_account()
        positions = self.alpaca_client.get_positions()
        
        return {
            "portfolio_value": float(account.portfolio_value),
            "cash": float(account.cash),
            "positions": [p.symbol for p in positions],
            "timestamp": datetime.now()
        }
    
    def get_market_conditions(self) -> Dict[str, Any]:
        """Get current market conditions from the market data provider."""
        return self.market_data_provider.get_market_conditions()
    
    def analyze_market_conditions(self, analysis_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze current market conditions using the selected strategy."""
        portfolio_data = self.get_portfolio_data()
        market_conditions = self.get_market_conditions()
        
        # Select the appropriate analysis strategy
        strategy_class = self.strategy_selector.select_strategy(
            market_conditions=market_conditions,
            user_preferences=self.user_preferences,
            selection_params=analysis_params
        )
        
        # Create an instance of the selected strategy
        strategy = strategy_class(llm_client=self.llm_client)
        self.current_analysis_strategy = strategy.get_strategy_name()
        
        # Perform analysis
        analysis = strategy.analyze(
            portfolio_data=portfolio_data,
            user_preferences=self.user_preferences,
            analysis_params=analysis_params
        )
        
        self.last_analysis = analysis
        return analysis
    
    def make_trading_decisions(self, 
                             market_analysis: Dict[str, Any],
                             strategy_params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Make trading decisions using the trading strategy."""
        portfolio_data = self.get_portfolio_data()
        decisions = self.trading_strategy.make_decisions(
            market_analysis=market_analysis,
            portfolio_data=portfolio_data,
            user_preferences=self.user_preferences,
            strategy_params=strategy_params
        )
        return decisions
    
    def rebalance_portfolio(self, rebalance_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Rebalance portfolio using the portfolio rebalancer."""
        portfolio_data = self.get_portfolio_data()
        rebalancing_plan = self.portfolio_rebalancer.rebalance_portfolio(
            portfolio_data=portfolio_data,
            user_preferences=self.user_preferences,
            rebalance_params=rebalance_params
        )
        self.last_rebalancing = rebalancing_plan
        return rebalancing_plan
    
    def execute_trades(self, decisions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute trading decisions using Alpaca client."""
        executed_trades = []
        
        for decision in decisions:
            try:
                # Handle 'ALL' quantity
                quantity = decision['quantity']
                if quantity == 'ALL':
                    # Get current position
                    positions = self.alpaca_client.get_positions()
                    position = next((p for p in positions if p.symbol == decision['symbol']), None)
                    if position:
                        quantity = int(float(position.qty))
                    else:
                        print(f"Warning: No position found for {decision['symbol']} to sell ALL")
                        continue
                
                # Place the order
                order = self.alpaca_client.place_market_order(
                    symbol=decision['symbol'],
                    qty=quantity,
                    side=OrderSide.BUY if decision['action'] == 'BUY' else OrderSide.SELL
                )
                
                executed_trades.append({
                    'symbol': decision['symbol'],
                    'action': decision['action'],
                    'quantity': quantity,
                    'status': 'executed',
                    'order_id': order.id
                })
                
            except Exception as e:
                executed_trades.append({
                    'symbol': decision['symbol'],
                    'action': decision['action'],
                    'quantity': decision['quantity'],
                    'status': 'failed',
                    'error': str(e)
                })
        
        return executed_trades
    
    def run_trading_cycle(self, 
                         analysis_params: Optional[Dict[str, Any]] = None,
                         strategy_params: Optional[Dict[str, Any]] = None,
                         rebalance_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run a complete trading cycle:
        1. Analyze market conditions
        2. Make trading decisions
        3. Rebalance portfolio if needed
        4. Execute trades
        5. Return results
        """
        # Step 1: Analyze market conditions
        analysis = self.analyze_market_conditions(analysis_params)
        if not analysis:
            return {"status": "failed", "error": "Market analysis failed"}
        
        # Step 2: Make trading decisions
        decisions = self.make_trading_decisions(analysis, strategy_params)
        if not decisions:
            return {"status": "failed", "error": "No trading decisions generated"}
        
        # Step 3: Rebalance portfolio
        rebalancing = self.rebalance_portfolio(rebalance_params)
        if rebalancing:
            rebalancing_orders = self.portfolio_rebalancer.generate_rebalancing_orders(
                rebalancing_plan=rebalancing,
                portfolio_data=self.get_portfolio_data()
            )
            decisions.extend(rebalancing_orders)
        
        # Step 4: Execute trades
        executed_trades = self.execute_trades(decisions)
        
        return {
            "status": "success",
            "analysis": analysis,
            "analysis_strategy": self.current_analysis_strategy,
            "decisions": decisions,
            "rebalancing": rebalancing,
            "executed_trades": executed_trades
        }

if __name__ == "__main__":
    # Example usage
    try:
        # Create trading agent with user preferences
        agent = TradingAgent(
            risk_tolerance="moderate",
            investment_goal="growth",
            max_position_size=0.1
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
        
        # Run a trading cycle
        results = agent.run_trading_cycle(
            analysis_params=analysis_params,
            strategy_params=strategy_params,
            rebalance_params=rebalance_params
        )
        
        # Print results
        print("\nTrading Cycle Results:")
        print(f"Status: {results['status']}")
        
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
            
    except Exception as e:
        print(f"Error: {str(e)}") 