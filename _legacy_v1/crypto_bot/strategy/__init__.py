# crypto_bot/strategy/__init__.py

from .base import StrategyBase
from .composite import CompositeStrategy
from .factory import StrategyFactory
from .ml_strategy import MLStrategy
from .registry import StrategyRegistry, strategy_registry
from .simple_ma import BollingerBandsStrategy, SimpleMAStrategy

__all__ = [
    "StrategyBase",
    "MLStrategy",
    "StrategyRegistry",
    "strategy_registry",
    "StrategyFactory",
    "CompositeStrategy",
    "SimpleMAStrategy",
    "BollingerBandsStrategy",
]
