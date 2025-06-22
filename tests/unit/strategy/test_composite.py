"""
コンポジット戦略のテスト
"""

import pytest
import pandas as pd
from unittest.mock import Mock

from crypto_bot.strategy.composite import CompositeStrategy, CombinationMode
from crypto_bot.strategy.base import StrategyBase
from crypto_bot.execution.engine import Position, Signal


class MockStrategy(StrategyBase):
    """テスト用のモック戦略"""
    
    def __init__(self, return_signal=None):
        self.return_signal = return_signal
    
    def logic_signal(self, price_df, position):
        return self.return_signal


class TestCompositeStrategy:
    
    def test_initialization(self):
        """コンポジット戦略の初期化をテスト"""
        strategy1 = MockStrategy()
        strategy2 = MockStrategy()
        strategies = [(strategy1, 0.6), (strategy2, 0.4)]
        
        composite = CompositeStrategy(strategies, "weighted_average")
        
        assert composite.get_strategy_count() == 2
        assert len(composite.normalized_strategies) == 2
        # 重みが正規化されていることを確認
        assert composite.normalized_strategies[0][1] == 0.6
        assert composite.normalized_strategies[1][1] == 0.4
    
    def test_weight_normalization(self):
        """重みの正規化をテスト"""
        strategy1 = MockStrategy()
        strategy2 = MockStrategy()
        strategies = [(strategy1, 30), (strategy2, 20)]  # 合計50
        
        composite = CompositeStrategy(strategies, "weighted_average")
        
        # 正規化された重みを確認
        assert composite.normalized_strategies[0][1] == 0.6  # 30/50
        assert composite.normalized_strategies[1][1] == 0.4  # 20/50
    
    def test_zero_total_weight_error(self):
        """重みの合計が0の場合のエラーをテスト"""
        strategy1 = MockStrategy()
        strategies = [(strategy1, 0)]
        
        with pytest.raises(ValueError, match="Total weight must be positive"):
            CompositeStrategy(strategies, "weighted_average")
    
    def test_weighted_average_combine_buy(self):
        """重み付き平均でBUYシグナルが生成されることをテスト"""
        buy_signal = Signal(side="BUY", price=100.0)
        sell_signal = Signal(side="SELL", price=100.0)
        
        strategy1 = MockStrategy(buy_signal)
        strategy2 = MockStrategy(buy_signal)
        strategy3 = MockStrategy(sell_signal)
        
        # BUY重み: 0.8, SELL重み: 0.2
        strategies = [(strategy1, 0.4), (strategy2, 0.4), (strategy3, 0.2)]
        composite = CompositeStrategy(strategies, "weighted_average")
        
        price_df = pd.DataFrame({'close': [100.0]})
        result = composite.logic_signal(price_df, None)
        
        assert result is not None
        assert result.side == "BUY"
    
    def test_weighted_average_combine_sell(self):
        """重み付き平均でSELLシグナルが生成されることをテスト"""
        buy_signal = Signal(side="BUY", price=100.0)
        sell_signal = Signal(side="SELL", price=100.0)
        
        strategy1 = MockStrategy(sell_signal)
        strategy2 = MockStrategy(sell_signal)
        strategy3 = MockStrategy(buy_signal)
        
        # SELL重み: 0.8, BUY重み: 0.2
        strategies = [(strategy1, 0.4), (strategy2, 0.4), (strategy3, 0.2)]
        composite = CompositeStrategy(strategies, "weighted_average")
        
        price_df = pd.DataFrame({'close': [100.0]})
        result = composite.logic_signal(price_df, None)
        
        assert result is not None
        assert result.side == "SELL"
    
    def test_weighted_average_no_signal(self):
        """重み付き平均で閾値を超えない場合のテスト"""
        buy_signal = Signal(side="BUY", price=100.0)
        sell_signal = Signal(side="SELL", price=100.0)
        
        strategy1 = MockStrategy(buy_signal)
        strategy2 = MockStrategy(sell_signal)
        
        # BUY重み: 0.5, SELL重み: 0.5 (どちらも閾値0.5を超えない)
        strategies = [(strategy1, 0.5), (strategy2, 0.5)]
        composite = CompositeStrategy(strategies, "weighted_average")
        
        price_df = pd.DataFrame({'close': [100.0]})
        result = composite.logic_signal(price_df, None)
        
        assert result is None
    
    def test_majority_vote_combine(self):
        """多数決によるシグナル統合をテスト"""
        buy_signal = Signal(side="BUY", price=100.0)
        sell_signal = Signal(side="SELL", price=100.0)
        
        strategy1 = MockStrategy(buy_signal)
        strategy2 = MockStrategy(buy_signal)
        strategy3 = MockStrategy(sell_signal)
        
        strategies = [(strategy1, 1), (strategy2, 1), (strategy3, 1)]
        composite = CompositeStrategy(strategies, "majority_vote")
        
        price_df = pd.DataFrame({'close': [100.0]})
        result = composite.logic_signal(price_df, None)
        
        assert result is not None
        assert result.side == "BUY"  # 2 vs 1でBUYが勝利
    
    def test_unanimous_combine_success(self):
        """全戦略一致によるシグナル統合（成功）をテスト"""
        buy_signal = Signal(side="BUY", price=100.0)
        
        strategy1 = MockStrategy(buy_signal)
        strategy2 = MockStrategy(buy_signal)
        
        strategies = [(strategy1, 1), (strategy2, 1)]
        composite = CompositeStrategy(strategies, "unanimous")
        
        price_df = pd.DataFrame({'close': [100.0]})
        result = composite.logic_signal(price_df, None)
        
        assert result is not None
        assert result.side == "BUY"
    
    def test_unanimous_combine_failure(self):
        """全戦略一致によるシグナル統合（不一致）をテスト"""
        buy_signal = Signal(side="BUY", price=100.0)
        sell_signal = Signal(side="SELL", price=100.0)
        
        strategy1 = MockStrategy(buy_signal)
        strategy2 = MockStrategy(sell_signal)
        
        strategies = [(strategy1, 1), (strategy2, 1)]
        composite = CompositeStrategy(strategies, "unanimous")
        
        price_df = pd.DataFrame({'close': [100.0]})
        result = composite.logic_signal(price_df, None)
        
        assert result is None  # 一致しないためシグナルなし
    
    def test_first_match_combine(self):
        """最初マッチによるシグナル統合をテスト"""
        buy_signal = Signal(side="BUY", price=100.0)
        sell_signal = Signal(side="SELL", price=100.0)
        
        strategy1 = MockStrategy(buy_signal)
        strategy2 = MockStrategy(sell_signal)
        
        strategies = [(strategy1, 1), (strategy2, 1)]
        composite = CompositeStrategy(strategies, "first_match")
        
        price_df = pd.DataFrame({'close': [100.0]})
        result = composite.logic_signal(price_df, None)
        
        assert result is not None
        assert result.side == "BUY"  # 最初の戦略のシグナル
    
    def test_no_signals(self):
        """すべての戦略がNoneを返す場合をテスト"""
        strategy1 = MockStrategy(None)
        strategy2 = MockStrategy(None)
        
        strategies = [(strategy1, 1), (strategy2, 1)]
        composite = CompositeStrategy(strategies, "weighted_average")
        
        price_df = pd.DataFrame({'close': [100.0]})
        result = composite.logic_signal(price_df, None)
        
        assert result is None
    
    def test_get_strategy_info(self):
        """戦略情報の取得をテスト"""
        strategy1 = MockStrategy()
        strategy2 = MockStrategy()
        
        strategies = [(strategy1, 0.6), (strategy2, 0.4)]
        composite = CompositeStrategy(strategies, "weighted_average")
        
        info = composite.get_strategy_info()
        
        assert len(info) == 2
        assert info[0]["class_name"] == "MockStrategy"
        assert info[0]["weight"] == 0.6
        assert info[1]["weight"] == 0.4