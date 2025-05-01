from abc import ABC, abstractmethod
import talib
import pandas as pd
from typing import Optional
from crypto_bot.execution.engine import Signal, Position

class StrategyBase(ABC):
    """
    すべての戦略はこのインターフェースを実装する。
    """
    @abstractmethod
    def logic_signal(
        self,
        price_df: pd.DataFrame,
        position: Position
    ) -> Signal:
        ...
        

class BollingerStrategy(StrategyBase):
    """
    ボリンジャーバンドを用いたシンプルな戦略。
    highが上帯を抜けたら買い、lowがミドルを下抜けたら売り。
    """
    def __init__(self, period: int = 20, nbdevup: float = 2.0, nbdevdn: float = 2.0):
        self.period = period
        self.nbdevup = nbdevup
        self.nbdevdn = nbdevdn

    def logic_signal(
        self,
        price_df: pd.DataFrame,
        position: Position
    ) -> Signal:
        if len(price_df) < self.period + 1:
            return Signal(None, None)

        closes = price_df["close"].values
        upper, middle, lower = talib.BBANDS(
            closes,
            timeperiod=self.period,
            nbdevup=self.nbdevup,
            nbdevdn=self.nbdevdn,
            matype=0
        )
        last = price_df.iloc[-1]
        prev = -2

        # エントリー
        if not position.exist and last["high"] > upper[prev]:
            return Signal("BUY", float(last["close"]))

        # エグジット
        if position.exist and last["low"] < middle[prev]:
            return Signal("SELL", float(last["close"]))

        return Signal(None, None)