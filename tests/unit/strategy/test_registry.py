"""
戦略レジストリのテスト
"""

import pytest
from unittest.mock import Mock

from crypto_bot.strategy.base import StrategyBase
from crypto_bot.strategy.registry import StrategyRegistry
from crypto_bot.execution.engine import Position, Signal


class MockStrategy(StrategyBase):
    """テスト用のモック戦略"""
    
    def logic_signal(self, price_df, position):
        return None


class TestStrategyRegistry:
    
    def test_singleton_pattern(self):
        """レジストリがシングルトンパターンで動作することを確認"""
        registry1 = StrategyRegistry()
        registry2 = StrategyRegistry()
        assert registry1 is registry2
    
    def test_register_strategy(self):
        """戦略の手動登録をテスト"""
        registry = StrategyRegistry()
        
        # テスト用戦略を登録
        registry.register("test_strategy", MockStrategy)
        
        # 登録された戦略を取得
        strategy_class = registry.get_strategy("test_strategy")
        assert strategy_class == MockStrategy
        
        # 戦略リストに含まれることを確認
        strategies = registry.list_strategies()
        assert "test_strategy" in strategies
    
    def test_register_invalid_strategy(self):
        """無効な戦略クラスの登録でエラーが発生することを確認"""
        registry = StrategyRegistry()
        
        class NotAStrategy:
            pass
        
        with pytest.raises(ValueError, match="must inherit from StrategyBase"):
            registry.register("invalid_strategy", NotAStrategy)
    
    def test_get_nonexistent_strategy(self):
        """存在しない戦略の取得でエラーが発生することを確認"""
        registry = StrategyRegistry()
        
        with pytest.raises(KeyError, match="Strategy 'nonexistent' not found"):
            registry.get_strategy("nonexistent")
    
    def test_class_name_to_strategy_name_conversion(self):
        """クラス名から戦略名への変換をテスト"""
        registry = StrategyRegistry()
        
        # CamelCaseからsnake_caseへの変換
        assert registry._class_name_to_strategy_name("MLStrategy") == "ml"
        assert registry._class_name_to_strategy_name("SimpleMAStrategy") == "simple_ma"
        assert registry._class_name_to_strategy_name("BollingerBandsStrategy") == "bollinger_bands"
        assert registry._class_name_to_strategy_name("TestStrategy") == "test"
    
    def test_auto_discovery(self):
        """自動発見機能のテスト"""
        registry = StrategyRegistry()
        
        # 実際に登録されている戦略を確認
        strategies = registry.list_strategies()
        
        # 少なくともMLStrategyが発見されることを確認
        assert "ml" in strategies
        assert "simple_ma" in strategies
        assert "bollinger_bands" in strategies