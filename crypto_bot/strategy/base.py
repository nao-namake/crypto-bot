from abc import ABC, abstractmethod

import pandas as pd

from crypto_bot.execution.engine import Position, Signal


class StrategyBase(ABC):
    """
    すべての戦略はこのインターフェースを実装する。
    """

    @abstractmethod
    def logic_signal(self, price_df: pd.DataFrame, position: Position) -> Signal:
        """
        シグナル生成の抽象メソッド。
        price_df: OHLC DataFrame
        position: 現在のポジション
        """
        raise NotImplementedError
