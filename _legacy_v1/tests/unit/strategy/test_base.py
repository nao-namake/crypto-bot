# tests/unit/strategy/test_base.py
# テスト対象: crypto_bot/strategy/base.py
# 説明:
#   - StrategyBaseは直接インスタンス化できない
#   - サブクラスでlogic_signal未実装ならエラー
#   - サブクラスでlogic_signal実装時は正常動作

import pandas as pd
import pytest

from crypto_bot.execution.engine import Position, Signal
from crypto_bot.strategy.base import StrategyBase


def test_strategy_base_instantiation_forbidden():
    # ABCは直接newできない
    with pytest.raises(TypeError):
        StrategyBase()


def test_logic_signal_not_implemented():
    # logic_signal未実装サブクラス→NotImplementedError
    class Dummy(StrategyBase):
        def logic_signal(self, df: pd.DataFrame, position: Position) -> pd.Series:
            # 親クラスの実装を呼び出す（NotImplementedError）
            return super().logic_signal(df, position)

    dummy = Dummy()
    df = pd.DataFrame({"close": [100, 110, 105]})
    position = Position()
    with pytest.raises(NotImplementedError):
        dummy.logic_signal(df, position)


def test_logic_signal_implemented():
    # サブクラスでlogic_signal実装すれば正常
    class MyStrategy(StrategyBase):
        def logic_signal(self, price_df, position):
            return Signal(side="BUY", price=100)

    strat = MyStrategy()
    signal = strat.logic_signal(pd.DataFrame(), Position())
    assert signal.side == "BUY"
    assert signal.price == 100
