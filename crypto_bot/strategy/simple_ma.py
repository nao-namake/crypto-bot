"""
移動平均戦略

シンプルな移動平均クロス戦略のサンプル実装。
プラグインシステムのデモンストレーション用として提供します。
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from crypto_bot.execution.engine import Position, Signal

from .base import StrategyBase

logger = logging.getLogger(__name__)


class SimpleMAStrategy(StrategyBase):
    """
    シンプルな移動平均クロス戦略

    短期移動平均が長期移動平均を上抜けしたらBUY、
    下抜けしたらSELLシグナルを生成します。
    """

    def __init__(
        self, short_period: int = 20, long_period: int = 50, config: dict = None
    ):
        """
        Args:
            short_period: 短期移動平均の期間
            long_period: 長期移動平均の期間
            config: 戦略設定（オプション）
        """
        self.short_period = short_period
        self.long_period = long_period
        self.config = config or {}

        if short_period >= long_period:
            raise ValueError("Short period must be less than long period")

        logger.info(
            f"SimpleMAStrategy initialized: short={short_period}, long={long_period}"
        )

    def logic_signal(
        self, price_df: pd.DataFrame, position: Position
    ) -> Optional[Signal]:
        """
        移動平均クロスに基づくシグナル生成

        Args:
            price_df: OHLC DataFrame
            position: 現在のポジション

        Returns:
            売買シグナル
        """
        if len(price_df) < self.long_period:
            logger.debug("Insufficient data for MA calculation")
            return None

        # 移動平均を計算
        short_ma = price_df["close"].rolling(window=self.short_period).mean()
        long_ma = price_df["close"].rolling(window=self.long_period).mean()

        # 最新の値を取得
        current_short = short_ma.iloc[-1]
        current_long = long_ma.iloc[-1]
        prev_short = short_ma.iloc[-2] if len(short_ma) > 1 else current_short
        prev_long = long_ma.iloc[-2] if len(long_ma) > 1 else current_long

        current_price = float(price_df["close"].iloc[-1])

        # クロスの判定
        golden_cross = prev_short <= prev_long and current_short > current_long
        dead_cross = prev_short >= prev_long and current_short < current_long

        position_exists = position is not None and position.exist

        logger.debug(
            f"MA values - Short: {current_short:.2f}, Long: {current_long:.2f}"
        )
        logger.debug(f"Cross signals - Golden: {golden_cross}, Dead: {dead_cross}")

        if position_exists:
            # ポジション保有中はクローズシグナルのみ
            if dead_cross:
                logger.info("Dead cross detected - Exit signal")
                return Signal(side="SELL", price=current_price)
        else:
            # ポジション未保有時はエントリーシグナル
            if golden_cross:
                logger.info("Golden cross detected - Entry signal")
                return Signal(side="BUY", price=current_price)

        return None


class BollingerBandsStrategy(StrategyBase):
    """
    ボリンジャーバンド戦略

    ボリンジャーバンドの上下バンドをブレイクした場合の
    逆張り戦略のサンプル実装。
    """

    def __init__(self, period: int = 20, std_dev: float = 2.0, config: dict = None):
        """
        Args:
            period: 移動平均とバンドの計算期間
            std_dev: 標準偏差の倍数
            config: 戦略設定（オプション）
        """
        self.period = period
        self.std_dev = std_dev
        self.config = config or {}

        logger.info(
            f"BollingerBandsStrategy initialized: period={period}, std_dev={std_dev}"
        )

    def logic_signal(
        self, price_df: pd.DataFrame, position: Position
    ) -> Optional[Signal]:
        """
        ボリンジャーバンドに基づくシグナル生成

        Args:
            price_df: OHLC DataFrame
            position: 現在のポジション

        Returns:
            売買シグナル
        """
        if len(price_df) < self.period:
            logger.debug("Insufficient data for Bollinger Bands calculation")
            return None

        # ボリンジャーバンドを計算
        close_prices = price_df["close"]
        sma = close_prices.rolling(window=self.period).mean()
        std = close_prices.rolling(window=self.period).std()

        upper_band = sma + (std * self.std_dev)
        lower_band = sma - (std * self.std_dev)

        current_price = float(close_prices.iloc[-1])
        current_upper = upper_band.iloc[-1]
        current_lower = lower_band.iloc[-1]
        current_sma = sma.iloc[-1]

        position_exists = position is not None and position.exist

        logger.debug(
            f"Bollinger Bands - Upper: {current_upper:.2f}, "
            f"SMA: {current_sma:.2f}, Lower: {current_lower:.2f}"
        )
        logger.debug(f"Current price: {current_price:.2f}")

        if position_exists:
            # ポジション保有中は中央線への回帰でクローズ
            if abs(current_price - current_sma) < abs(
                current_sma * 0.005
            ):  # 0.5%以内で中央線
                logger.info("Price near SMA - Exit signal")
                return Signal(side="SELL", price=current_price)
        else:
            # ポジション未保有時はバンドブレイクで逆張りエントリー
            if current_price <= current_lower:
                logger.info("Price below lower band - Buy signal (contrarian)")
                return Signal(side="BUY", price=current_price)
            elif current_price >= current_upper:
                logger.info("Price above upper band - Sell signal (contrarian)")
                return Signal(side="SELL", price=current_price)

        return None
