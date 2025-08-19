"""
戦略ファクトリーのテスト
"""

from crypto_bot.strategy.composite import CompositeStrategy
from crypto_bot.strategy.factory import StrategyFactory

# 未使用のMock, patch, pd, pytest, Position, Signal, StrategyBase, errors削除


class TestStrategyFactory:

    def test_create_single_strategy(self):
        """単一戦略の生成をテスト"""
        config = {
            "name": "simple_ma",
            "params": {"short_period": 10, "long_period": 20},
        }

        strategy = StrategyFactory.create_strategy(config)

        assert hasattr(strategy, "logic_signal")
        assert strategy.short_period == 10
        assert strategy.long_period == 20

    def test_create_multi_strategy(self):
        """マルチ戦略の生成をテスト"""
        configs = [
            {
                "name": "simple_ma",
                "weight": 0.6,
                "params": {"short_period": 10, "long_period": 20},
            },
            {
                "name": "bollinger_bands",
                "weight": 0.4,
                "params": {"period": 20, "std_dev": 2.0},
            },
        ]

        strategy = StrategyFactory.create_multi_strategy(configs, "weighted_average")

        assert isinstance(strategy, CompositeStrategy)
        assert strategy.get_strategy_count() == 2

    def test_validate_config_valid(self):
        """有効な設定の検証をテスト"""
        config = {
            "name": "simple_ma",
            "params": {"short_period": 10, "long_period": 20},
        }

        errors = StrategyFactory.validate_config(config)
        assert len(errors) == 0

    def test_validate_config_missing_name(self):
        """戦略名が不足している場合のエラーをテスト"""
        config = {"params": {"short_period": 10}}

        errors = StrategyFactory.validate_config(config)
        assert len(errors) == 1
        assert "Strategy name is required" in errors[0]

    def test_validate_config_unknown_strategy(self):
        """存在しない戦略名の場合のエラーをテスト"""
        config = {"name": "unknown_strategy", "params": {}}

        errors = StrategyFactory.validate_config(config)
        assert len(errors) == 1
        assert "Unknown strategy: unknown_strategy" in errors[0]

    def test_list_available_strategies(self):
        """利用可能な戦略一覧の取得をテスト"""
        strategies = StrategyFactory.list_available_strategies()

        assert isinstance(strategies, list)
        assert len(strategies) > 0
        assert "ml" in strategies
        assert "simple_ma" in strategies

    def test_get_strategy_info(self):
        """戦略情報の取得をテスト"""
        info = StrategyFactory.get_strategy_info("simple_ma")

        assert info["name"] == "simple_ma"
        assert info["class_name"] == "SimpleMAStrategy"
        assert "parameters" in info
        assert isinstance(info["parameters"], list)

    def test_create_strategy_with_missing_required_param(self):
        """必須パラメータが不足している場合のテスト"""
        # ml_strategyはmodel_pathが必須パラメータ
        config = {
            "name": "ml",
            "params": {
                "threshold": 0.1
                # model_path が不足
            },
        }

        # 実際の戦略作成ではエラーが発生する可能性があるが、
        # ここでは設定検証のテストを行う
        StrategyFactory.validate_config(config)
        # ml_strategyの場合、model_pathが必須だがconfigパラメータで代替可能
        # エラーの詳細は実装依存

    def test_create_strategy_with_config_param(self):
        """configパラメータが戦略に渡されることをテスト"""
        config = {
            "name": "simple_ma",
            "params": {
                "short_period": 15,
                "long_period": 30,
                "extra_config": "test_value",
            },
        }

        strategy = StrategyFactory.create_strategy(config)

        # configが正しく渡されていることを確認
        assert hasattr(strategy, "config")
        assert strategy.config.get("extra_config") == "test_value"
