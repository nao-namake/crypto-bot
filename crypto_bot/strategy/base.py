# crypto_bot/strategy/base.py
# 説明:
# すべての売買戦略クラス（例: MLStrategy, BollingerStrategy）は、この抽象クラス（基底クラス）を継承します。
# 共通のインターフェース（logic_signalメソッド）を強制し、統一的な使い方ができるようにします。
# 
# ポイント:
# ・Pythonの「抽象基底クラス（ABC）」で設計
# ・logic_signalは必ず実装しないとエラーになる（= 強制力がある）

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
