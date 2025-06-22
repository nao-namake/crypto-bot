# crypto_bot/strategy/__init__.py

from .base import StrategyBase
from .ml_strategy import MLStrategy
from .registry import StrategyRegistry, strategy_registry
from .factory import StrategyFactory
from .composite import CompositeStrategy
from .simple_ma import SimpleMAStrategy, BollingerBandsStrategy

__all__ = [
    "StrategyBase",
    "MLStrategy",
    "StrategyRegistry",
    "strategy_registry",
    "StrategyFactory",
    "CompositeStrategy",
    "SimpleMAStrategy",
    "BollingerBandsStrategy"
]