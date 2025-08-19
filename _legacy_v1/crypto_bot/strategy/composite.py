"""
コンポジット戦略

複数の戦略を組み合わせて実行するコンポジット戦略クラス。
異なる戦略の結果を統合し、より堅牢な取引判断を実現します。
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import List, Optional, Tuple

import pandas as pd

from crypto_bot.execution.engine import Position, Signal

from .base import StrategyBase

logger = logging.getLogger(__name__)


class CombinationMode(Enum):
    """戦略組み合わせモード"""

    WEIGHTED_AVERAGE = "weighted_average"
    MAJORITY_VOTE = "majority_vote"
    UNANIMOUS = "unanimous"
    FIRST_MATCH = "first_match"


class CompositeStrategy(StrategyBase):
    """
    複数の戦略を組み合わせるコンポジット戦略

    各戦略の結果を指定された方法で統合し、最終的な売買シグナルを生成します。
    """

    def __init__(
        self,
        strategies: List[Tuple[StrategyBase, float]],
        combination_mode: str = "weighted_average",
    ):
        """
        Args:
            strategies: (戦略インスタンス, 重み) のタプルのリスト
            combination_mode: 組み合わせ方法
        """
        self.strategies = strategies
        self.combination_mode = CombinationMode(combination_mode)

        # 重みの正規化
        total_weight = sum(weight for _, weight in strategies)
        if total_weight <= 0:
            raise ValueError("Total weight must be positive")

        self.normalized_strategies = [
            (strategy, weight / total_weight) for strategy, weight in strategies
        ]

        logger.info(
            f"Initialized CompositeStrategy with {len(strategies)} strategies, "
            f"mode: {combination_mode}"
        )
        for i, (strategy, weight) in enumerate(self.normalized_strategies):
            logger.info(
                f"  Strategy {i+1}: {strategy.__class__.__name__} "
                f"(weight: {weight:.3f})"
            )

    def logic_signal(
        self, price_df: pd.DataFrame, position: Position
    ) -> Optional[Signal]:
        """
        各戦略の結果を統合して最終シグナルを生成

        Args:
            price_df: OHLC DataFrame
            position: 現在のポジション

        Returns:
            統合されたシグナル
        """
        signals = []

        # 各戦略からシグナルを取得
        for strategy, weight in self.normalized_strategies:
            try:
                signal = strategy.logic_signal(price_df, position)
                signals.append((signal, weight))
                logger.debug(f"Strategy {strategy.__class__.__name__}: {signal}")
            except Exception as e:
                logger.error(f"Error in strategy {strategy.__class__.__name__}: {e}")
                signals.append((None, weight))

        # 組み合わせモードに応じて統合
        return self._combine_signals(signals, price_df.iloc[-1]["close"])

    def _combine_signals(
        self, signals: List[Tuple[Optional[Signal], float]], current_price: float
    ) -> Optional[Signal]:
        """
        シグナルリストを組み合わせて最終シグナルを生成

        Args:
            signals: (シグナル, 重み)のタプルのリスト
            current_price: 現在価格

        Returns:
            統合シグナル
        """
        valid_signals = [(sig, weight) for sig, weight in signals if sig is not None]

        if not valid_signals:
            return None

        if self.combination_mode == CombinationMode.WEIGHTED_AVERAGE:
            return self._weighted_average_combine(valid_signals, current_price)
        elif self.combination_mode == CombinationMode.MAJORITY_VOTE:
            return self._majority_vote_combine(valid_signals, current_price)
        elif self.combination_mode == CombinationMode.UNANIMOUS:
            return self._unanimous_combine(valid_signals, current_price)
        elif self.combination_mode == CombinationMode.FIRST_MATCH:
            return self._first_match_combine(valid_signals)
        else:
            raise ValueError(f"Unknown combination mode: {self.combination_mode}")

    def _weighted_average_combine(
        self, signals: List[Tuple[Signal, float]], current_price: float
    ) -> Optional[Signal]:
        """重み付き平均によるシグナル統合"""
        buy_weight = 0.0
        sell_weight = 0.0

        for signal, weight in signals:
            if signal.side == "BUY":
                buy_weight += weight
            elif signal.side == "SELL":
                sell_weight += weight

        # 閾値を設定（重みの合計が50%以上の場合にシグナル発生）
        threshold = 0.5

        if buy_weight > threshold and buy_weight > sell_weight:
            return Signal(side="BUY", price=current_price)
        elif sell_weight > threshold and sell_weight > buy_weight:
            return Signal(side="SELL", price=current_price)

        return None

    def _majority_vote_combine(
        self, signals: List[Tuple[Signal, float]], current_price: float
    ) -> Optional[Signal]:
        """多数決によるシグナル統合"""
        buy_count = sum(1 for signal, _ in signals if signal.side == "BUY")
        sell_count = sum(1 for signal, _ in signals if signal.side == "SELL")

        if buy_count > sell_count:
            return Signal(side="BUY", price=current_price)
        elif sell_count > buy_count:
            return Signal(side="SELL", price=current_price)

        return None

    def _unanimous_combine(
        self, signals: List[Tuple[Signal, float]], current_price: float
    ) -> Optional[Signal]:
        """全戦略一致によるシグナル統合"""
        if not signals:
            return None

        first_side = signals[0][0].side
        if all(signal.side == first_side for signal, _ in signals):
            return Signal(side=first_side, price=current_price)

        return None

    def _first_match_combine(
        self, signals: List[Tuple[Signal, float]]
    ) -> Optional[Signal]:
        """最初にマッチしたシグナルを返す"""
        if signals:
            return signals[0][0]
        return None

    def get_strategy_count(self) -> int:
        """組み合わせている戦略数を取得"""
        return len(self.strategies)

    def get_strategy_info(self) -> List[dict]:
        """組み合わせている戦略の情報を取得"""
        return [
            {"class_name": strategy.__class__.__name__, "weight": weight}
            for strategy, weight in self.normalized_strategies
        ]
