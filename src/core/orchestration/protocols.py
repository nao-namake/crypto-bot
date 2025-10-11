"""
サービスプロトコル定義 - Phase 38.4完了版

各サービス層のインターフェース定義・Protocol型ヒント基盤システム

Phase 28-29最適化: Protocol型ヒントシステム確立・依存性注入基盤
Phase 38: trading層レイヤードアーキテクチャ実装完了
Phase 38.4: 全モジュールPhase統一・コード品質保証完了
"""

# 循環インポート回避のため、型ヒントでのみ使用
from typing import TYPE_CHECKING, Any, Dict, Optional, Protocol, Union

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from src.strategies.base.strategy_base import StrategySignal
    from src.trading import ExecutionResult, TradeEvaluation


class DataServiceProtocol(Protocol):
    """データ層サービスインターフェース."""

    async def fetch_multi_timeframe(self, symbol: str, limit: int) -> Optional[Dict[str, Any]]: ...


class FeatureServiceProtocol(Protocol):
    """特徴量生成サービスインターフェース."""

    async def generate_features(self, market_data: Dict[str, Any]) -> Dict[str, Any]: ...


class StrategyServiceProtocol(Protocol):
    """戦略評価サービスインターフェース."""

    def analyze_market(self, df: pd.DataFrame) -> "StrategySignal": ...

    def _create_hold_signal(self, df: pd.DataFrame, reason: str) -> "StrategySignal": ...


class MLServiceProtocol(Protocol):
    """ML予測サービスインターフェース."""

    def predict(self, X: pd.DataFrame, use_confidence: bool = True) -> np.ndarray: ...


class RiskServiceProtocol(Protocol):
    """リスク管理サービスインターフェース."""

    def evaluate_trade_opportunity(
        self,
        ml_prediction: Dict[str, Any],
        strategy_signal: Dict[str, Any],
        market_data: pd.DataFrame,
        current_balance: float,
        bid: float,
        ask: float,
    ) -> "TradeEvaluation": ...


class ExecutionServiceProtocol(Protocol):
    """注文実行サービスインターフェース（Phase 38.4完了版）."""

    async def execute_trade(self, evaluation: "TradeEvaluation") -> "ExecutionResult": ...

    async def check_stop_conditions(self) -> Optional["ExecutionResult"]: ...

    def get_trading_statistics(self) -> Dict[str, Union[int, float, str]]: ...
