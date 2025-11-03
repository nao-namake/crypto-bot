"""
Phase 51.5-B: StrategyRegistry単体テスト

Registry Pattern + Decoratorによる戦略自動登録システムのテスト。
戦略追加・削除の影響範囲を93%削減（27ファイル→4ファイル）。
"""

import pytest

from src.core.exceptions import StrategyError
from src.strategies.base.strategy_base import StrategyBase
from src.strategies.strategy_registry import StrategyRegistry


class TestStrategyRegistry:
    """StrategyRegistry基本機能テスト"""

    def setup_method(self):
        """各テストの前にレジストリをクリア"""
        StrategyRegistry.clear_registry()

    def test_register_decorator_basic(self):
        """@register decoratorの基本機能テスト"""

        @StrategyRegistry.register(name="TestStrategy", strategy_type="test")
        class TestStrategy(StrategyBase):
            def analyze(self, df):
                return None

            def get_required_features(self):
                return []

        assert StrategyRegistry.is_registered("TestStrategy")
        assert StrategyRegistry.get_strategy_count() == 1

    def test_register_decorator_retrieval(self):
        """登録した戦略クラスの取得テスト"""

        @StrategyRegistry.register(name="MyStrategy", strategy_type="custom")
        class MyStrategy(StrategyBase):
            def analyze(self, df):
                return None

            def get_required_features(self):
                return []

        retrieved_class = StrategyRegistry.get_strategy("MyStrategy")
        assert retrieved_class == MyStrategy

    def test_register_duplicate_name_raises_error(self):
        """同名の戦略を登録するとエラー"""

        @StrategyRegistry.register(name="DupStrategy", strategy_type="test1")
        class FirstStrategy(StrategyBase):
            def analyze(self, df):
                return None

            def get_required_features(self):
                return []

        with pytest.raises(StrategyError, match="既に登録されています"):

            @StrategyRegistry.register(name="DupStrategy", strategy_type="test2")
            class SecondStrategy(StrategyBase):
                def analyze(self, df):
                    return None

                def get_required_features(self):
                    return []

    def test_get_strategy_not_found_raises_error(self):
        """未登録の戦略を取得するとエラー"""
        with pytest.raises(StrategyError, match="が見つかりません"):
            StrategyRegistry.get_strategy("NonExistent")

    def test_get_strategy_metadata(self):
        """戦略メタデータ取得テスト"""

        @StrategyRegistry.register(name="MetaStrategy", strategy_type="meta_test")
        class MetaStrategy(StrategyBase):
            def analyze(self, df):
                return None

            def get_required_features(self):
                return []

        metadata = StrategyRegistry.get_strategy_metadata("MetaStrategy")

        assert metadata["name"] == "MetaStrategy"
        assert metadata["strategy_type"] == "meta_test"
        assert metadata["class"] == MetaStrategy
        assert metadata["class_name"] == "MetaStrategy"
        assert "module" in metadata

    def test_get_strategy_metadata_not_found_raises_error(self):
        """未登録の戦略のメタデータ取得でエラー"""
        with pytest.raises(StrategyError, match="が見つかりません"):
            StrategyRegistry.get_strategy_metadata("NonExistent")

    def test_list_strategies_empty(self):
        """空のレジストリリスト取得"""
        strategies = StrategyRegistry.list_strategies()
        assert strategies == []

    def test_list_strategies_multiple(self):
        """複数戦略のリスト取得"""

        @StrategyRegistry.register(name="Strategy1", strategy_type="type1")
        class Strategy1(StrategyBase):
            def analyze(self, df):
                return None

            def get_required_features(self):
                return []

        @StrategyRegistry.register(name="Strategy2", strategy_type="type2")
        class Strategy2(StrategyBase):
            def analyze(self, df):
                return None

            def get_required_features(self):
                return []

        @StrategyRegistry.register(name="Strategy3", strategy_type="type3")
        class Strategy3(StrategyBase):
            def analyze(self, df):
                return None

            def get_required_features(self):
                return []

        strategies = StrategyRegistry.list_strategies()
        assert len(strategies) == 3
        assert "Strategy1" in strategies
        assert "Strategy2" in strategies
        assert "Strategy3" in strategies

    def test_is_registered_true(self):
        """登録済み戦略の確認"""

        @StrategyRegistry.register(name="RegisteredStrategy", strategy_type="test")
        class RegisteredStrategy(StrategyBase):
            def analyze(self, df):
                return None

            def get_required_features(self):
                return []

        assert StrategyRegistry.is_registered("RegisteredStrategy") is True

    def test_is_registered_false(self):
        """未登録戦略の確認"""
        assert StrategyRegistry.is_registered("NonExistent") is False

    def test_get_strategy_count_zero(self):
        """戦略数0の確認"""
        assert StrategyRegistry.get_strategy_count() == 0

    def test_get_strategy_count_multiple(self):
        """複数戦略の数確認"""

        @StrategyRegistry.register(name="S1", strategy_type="t1")
        class S1(StrategyBase):
            def analyze(self, df):
                return None

            def get_required_features(self):
                return []

        @StrategyRegistry.register(name="S2", strategy_type="t2")
        class S2(StrategyBase):
            def analyze(self, df):
                return None

            def get_required_features(self):
                return []

        assert StrategyRegistry.get_strategy_count() == 2

    def test_clear_registry(self):
        """レジストリクリア機能テスト"""

        @StrategyRegistry.register(name="TempStrategy", strategy_type="temp")
        class TempStrategy(StrategyBase):
            def analyze(self, df):
                return None

            def get_required_features(self):
                return []

        assert StrategyRegistry.get_strategy_count() == 1

        StrategyRegistry.clear_registry()

        assert StrategyRegistry.get_strategy_count() == 0
        assert StrategyRegistry.is_registered("TempStrategy") is False

    def test_get_all_metadata(self):
        """全メタデータ取得テスト"""

        @StrategyRegistry.register(name="StrategyA", strategy_type="typeA")
        class StrategyA(StrategyBase):
            def analyze(self, df):
                return None

            def get_required_features(self):
                return []

        @StrategyRegistry.register(name="StrategyB", strategy_type="typeB")
        class StrategyB(StrategyBase):
            def analyze(self, df):
                return None

            def get_required_features(self):
                return []

        all_metadata = StrategyRegistry.get_all_metadata()

        assert len(all_metadata) == 2
        assert "StrategyA" in all_metadata
        assert "StrategyB" in all_metadata
        assert all_metadata["StrategyA"]["strategy_type"] == "typeA"
        assert all_metadata["StrategyB"]["strategy_type"] == "typeB"

    def test_get_all_metadata_returns_copy(self):
        """get_all_metadata()がコピーを返すことを確認"""

        @StrategyRegistry.register(name="OriginalStrategy", strategy_type="original")
        class OriginalStrategy(StrategyBase):
            def analyze(self, df):
                return None

            def get_required_features(self):
                return []

        metadata1 = StrategyRegistry.get_all_metadata()
        metadata2 = StrategyRegistry.get_all_metadata()

        # 異なるオブジェクトであることを確認
        assert metadata1 is not metadata2

        # 内容は同じ
        assert metadata1 == metadata2


class TestStrategyRegistryIntegration:
    """StrategyRegistry統合テスト"""

    def setup_method(self):
        """各テストの前にレジストリをクリア"""
        StrategyRegistry.clear_registry()

    def test_register_multiple_strategies_different_types(self):
        """異なるタイプの複数戦略登録"""

        @StrategyRegistry.register(name="ATRStrategy", strategy_type="atr_based")
        class ATRStrategy(StrategyBase):
            def analyze(self, df):
                return None

            def get_required_features(self):
                return []

        @StrategyRegistry.register(name="DonchianStrategy", strategy_type="donchian")
        class DonchianStrategy(StrategyBase):
            def analyze(self, df):
                return None

            def get_required_features(self):
                return []

        @StrategyRegistry.register(name="ADXStrategy", strategy_type="adx")
        class ADXStrategy(StrategyBase):
            def analyze(self, df):
                return None

            def get_required_features(self):
                return []

        assert StrategyRegistry.get_strategy_count() == 3

        # 各戦略が正しく取得できる
        assert StrategyRegistry.get_strategy("ATRStrategy") == ATRStrategy
        assert StrategyRegistry.get_strategy("DonchianStrategy") == DonchianStrategy
        assert StrategyRegistry.get_strategy("ADXStrategy") == ADXStrategy

    def test_metadata_contains_correct_module_info(self):
        """メタデータに正しいモジュール情報が含まれる"""

        @StrategyRegistry.register(name="ModuleTestStrategy", strategy_type="module_test")
        class ModuleTestStrategy(StrategyBase):
            def analyze(self, df):
                return None

            def get_required_features(self):
                return []

        metadata = StrategyRegistry.get_strategy_metadata("ModuleTestStrategy")

        # モジュール情報が含まれる
        assert "module" in metadata
        assert metadata["module"] is not None

    def test_register_preserves_class_functionality(self):
        """decoratorが元のクラス機能を保持する"""

        @StrategyRegistry.register(name="FunctionalStrategy", strategy_type="functional")
        class FunctionalStrategy(StrategyBase):
            def __init__(self, name="FunctionalStrategy", config=None):
                super().__init__(name, config)

            def analyze(self, df):
                return None

            def get_required_features(self):
                return []

            def custom_method(self):
                return "custom_result"

        # クラスの機能が保持されている
        instance = FunctionalStrategy()
        assert hasattr(instance, "custom_method")
        assert instance.custom_method() == "custom_result"


class TestStrategyRegistryErrorHandling:
    """StrategyRegistryエラー処理テスト"""

    def setup_method(self):
        """各テストの前にレジストリをクリア"""
        StrategyRegistry.clear_registry()

    def test_get_strategy_error_message_includes_available_strategies(self):
        """エラーメッセージに利用可能な戦略リストが含まれる"""

        @StrategyRegistry.register(name="AvailableStrategy1", strategy_type="type1")
        class AvailableStrategy1(StrategyBase):
            def analyze(self, df):
                return None

            def get_required_features(self):
                return []

        @StrategyRegistry.register(name="AvailableStrategy2", strategy_type="type2")
        class AvailableStrategy2(StrategyBase):
            def analyze(self, df):
                return None

            def get_required_features(self):
                return []

        with pytest.raises(StrategyError) as exc_info:
            StrategyRegistry.get_strategy("NonExistent")

        error_message = str(exc_info.value)
        assert "AvailableStrategy1" in error_message
        assert "AvailableStrategy2" in error_message

    def test_get_strategy_error_message_when_empty(self):
        """空のレジストリでのエラーメッセージ"""
        with pytest.raises(StrategyError) as exc_info:
            StrategyRegistry.get_strategy("NonExistent")

        error_message = str(exc_info.value)
        assert "（なし）" in error_message

    def test_get_metadata_error_message_includes_available_strategies(self):
        """get_metadataエラーメッセージに利用可能な戦略リスト"""

        @StrategyRegistry.register(name="MetaAvailable", strategy_type="meta")
        class MetaAvailable(StrategyBase):
            def analyze(self, df):
                return None

            def get_required_features(self):
                return []

        with pytest.raises(StrategyError) as exc_info:
            StrategyRegistry.get_strategy_metadata("NonExistent")

        error_message = str(exc_info.value)
        assert "MetaAvailable" in error_message


class TestStrategyRegistrySingleton:
    """StrategyRegistryシングルトン動作テスト"""

    def setup_method(self):
        """各テストの前にレジストリをクリア"""
        StrategyRegistry.clear_registry()

    def test_singleton_behavior(self):
        """シングルトンとして動作することを確認"""

        @StrategyRegistry.register(name="SingletonTest", strategy_type="singleton")
        class SingletonTest(StrategyBase):
            def analyze(self, df):
                return None

            def get_required_features(self):
                return []

        # 異なる場所から同じレジストリにアクセスできる
        count1 = StrategyRegistry.get_strategy_count()
        is_registered1 = StrategyRegistry.is_registered("SingletonTest")

        count2 = StrategyRegistry.get_strategy_count()
        is_registered2 = StrategyRegistry.is_registered("SingletonTest")

        assert count1 == count2 == 1
        assert is_registered1 == is_registered2 is True
