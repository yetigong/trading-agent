from typing import Dict, Any, List
from datetime import datetime

class MockAlpacaTradingClient:
    """Mock Alpaca trading client for testing."""
    
    def __init__(self):
        self.mock_account = {
            "portfolio_value": 100000.0,
            "cash": 50000.0,
            "positions": [
                {"symbol": "AAPL", "qty": 1, "market_value": 200.0},
                {"symbol": "MSFT", "qty": 0, "market_value": 0.0},
                {"symbol": "JNJ", "qty": 0, "market_value": 0.0}
            ]
        }
        self.orders = []
    
    def get_account(self) -> Dict[str, Any]:
        """Get mock account information."""
        return type('Account', (), {
            'portfolio_value': self.mock_account["portfolio_value"],
            'cash': self.mock_account["cash"]
        })()
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get mock positions."""
        return [type('Position', (), {
            'symbol': p["symbol"],
            'qty': p["qty"]
        })() for p in self.mock_account["positions"] if p["qty"] > 0]
    
    def place_market_order(self, symbol: str, qty: int, side: str) -> Dict[str, Any]:
        """Place a mock market order."""
        # Find the position
        position = next((p for p in self.mock_account["positions"] if p["symbol"] == symbol), None)
        
        # Validate order
        if side == "SELL":
            if not position or position["qty"] < qty:
                raise Exception({
                    "available": "0",
                    "code": 40310000,
                    "existing_qty": position["qty"] if position else "0",
                    "held_for_orders": "0",
                    "message": f"insufficient qty available for order (requested: {qty}, available: {position['qty'] if position else 0})",
                    "symbol": symbol
                })
        
        # Create and store the order
        order = {
            'id': f'order_{len(self.orders) + 1}',
            'symbol': symbol,
            'qty': qty,
            'side': side,
            'type': 'market',
            'status': 'filled',
            'filled_at': datetime.now()
        }
        self.orders.append(order)
        
        # Update position
        if position:
            if side == "BUY":
                position["qty"] += qty
            else:  # SELL
                position["qty"] -= qty
        
        return type('Order', (), {'id': order['id']})()
    
    def get_order(self, order_id: str) -> Dict[str, Any]:
        """Get mock order information."""
        for order in self.orders:
            if order['id'] == order_id:
                return order
        return None
    
    def get_orders(self) -> List[Dict[str, Any]]:
        """Get all mock orders."""
        return self.orders 