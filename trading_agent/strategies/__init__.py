"""
Trading Strategies Package

Provides interfaces and implementations for trading strategies.
"""

from .base import TradingStrategy
from .general import GeneralTradingStrategy

__all__ = ['TradingStrategy', 'GeneralTradingStrategy'] 