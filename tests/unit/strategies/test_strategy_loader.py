"""
Phase 65.11: StrategyLoader単体テスト

thresholds.yaml（get_all_thresholds経由）から戦略定義+パラメータを読み込み、
動的にインスタンス化するFacade Patternのテスト。
"""

from unittest.mock import patch

import pytest

from src.core.exceptions import StrategyError
from src.strategies.base.strategy_base import StrategyBase
from src.strategies.strategy_loader import StrategyLoader
from src.strategies.strategy_registry import StrategyRegistry


def _make_thresholds(strategies: dict, version: str = "2.0.0") -> dict:
    """テスト用thresholds辞書を生成するヘルパー"""
    return {
        "strategy_system_version": version,
        "strategies": strategies,
    }


class TestStrategyLoaderBasic:
    """StrategyLoader基本機能テスト"""

    def setup_method(self):
        """各テストの前にレジストリをクリア"""
        StrategyRegistry.clear_registry()

    def test_init(self):
        """初期化テスト"""
        loader = StrategyLoader()
        assert loader.config is None

    def test_load_config_empty_thresholds(self):
        """get_all_thresholds が空を返す場合エラー"""
        with patch("src.strategies.strategy_loader.get_all_thresholds", return_value={}):
            loader = StrategyLoader()
            with pytest.raises(StrategyError, match="読み込み結果が空です"):
                loader._load_config()

    def test_load_config_missing_strategies_section(self):
        """strategiesセクションがない場合エラー"""
        with patch(
            "src.strategies.strategy_loader.get_all_thresholds",
            return_value={"ml": {}},
        ):
            loader = StrategyLoader()
            with pytest.raises(StrategyError, match="'strategies' セクションがありません"):
                loader._load_config()

    def test_load_config_success(self):
        """正常な設定の読み込み"""
        thresholds = _make_thresholds(
            {"test_strategy": {"enabled": True, "class_name": "T", "strategy_type": "t"}}
        )
        with patch(
            "src.strategies.strategy_loader.get_all_thresholds",
            return_value=thresholds,
        ):
            loader = StrategyLoader()
            config = loader._load_config()

            assert "strategies" in config
            assert "test_strategy" in config["strategies"]
            assert config["strategy_system_version"] == "2.0.0"

    def test_load_config_get_all_thresholds_error(self):
        """get_all_thresholds がエラーを投げる場合"""
        with patch(
            "src.strategies.strategy_loader.get_all_thresholds",
            side_effect=Exception("Config load error"),
        ):
            loader = StrategyLoader()
            with pytest.raises(StrategyError, match="読み込みエラー"):
                loader._load_config()


class TestStrategyLoaderStrategyLoading:
    """StrategyLoader戦略ロード機能テスト"""

    def setup_method(self):
        """各テストの前にレジストリをクリア"""
        StrategyRegistry.clear_registry()

        # テスト用戦略クラスを登録
        @StrategyRegistry.register(name="TestStrategy1", strategy_type="test1")
        class TestStrategy1(StrategyBase):
            def __init__(self, config=None):
                self.config = config or {}

            def analyze(self, df):
                return None

            def get_required_features(self):
                return []

        @StrategyRegistry.register(name="TestStrategy2", strategy_type="test2")
        class TestStrategy2(StrategyBase):
            def __init__(self, config=None):
                self.config = config or {}

            def analyze(self, df):
                return None

            def get_required_features(self):
                return []

        self.TestStrategy1 = TestStrategy1
        self.TestStrategy2 = TestStrategy2

    def test_load_strategies_basic(self):
        """基本的な戦略ロード"""
        thresholds = _make_thresholds(
            {
                "strategy1": {
                    "enabled": True,
                    "class_name": "TestStrategy1",
                    "strategy_type": "test1",
                    "weight": 1.0,
                    "priority": 1,
                }
            }
        )

        with patch(
            "src.strategies.strategy_loader.get_all_thresholds",
            return_value=thresholds,
        ):
            loader = StrategyLoader()
            strategies = loader.load_strategies()

            assert len(strategies) == 1
            assert strategies[0]["weight"] == 1.0
            assert strategies[0]["priority"] == 1
            assert strategies[0]["metadata"]["strategy_id"] == "strategy1"
            assert strategies[0]["metadata"]["name"] == "TestStrategy1"

    def test_load_strategies_skip_disabled(self):
        """無効な戦略をスキップ"""
        thresholds = _make_thresholds(
            {
                "enabled_strategy": {
                    "enabled": True,
                    "class_name": "TestStrategy1",
                    "strategy_type": "test1",
                },
                "disabled_strategy": {
                    "enabled": False,
                    "class_name": "TestStrategy2",
                    "strategy_type": "test2",
                },
            }
        )

        with patch(
            "src.strategies.strategy_loader.get_all_thresholds",
            return_value=thresholds,
        ):
            loader = StrategyLoader()
            strategies = loader.load_strategies()

            assert len(strategies) == 1
            assert strategies[0]["metadata"]["strategy_id"] == "enabled_strategy"

    def test_load_strategies_priority_sorting(self):
        """優先度順にソート"""
        thresholds = _make_thresholds(
            {
                "low_priority": {
                    "enabled": True,
                    "class_name": "TestStrategy1",
                    "strategy_type": "test1",
                    "priority": 10,
                },
                "high_priority": {
                    "enabled": True,
                    "class_name": "TestStrategy2",
                    "strategy_type": "test2",
                    "priority": 1,
                },
            }
        )

        with patch(
            "src.strategies.strategy_loader.get_all_thresholds",
            return_value=thresholds,
        ):
            loader = StrategyLoader()
            strategies = loader.load_strategies()

            assert len(strategies) == 2
            assert strategies[0]["metadata"]["strategy_id"] == "high_priority"
            assert strategies[1]["metadata"]["strategy_id"] == "low_priority"

    def test_load_strategy_missing_required_field(self):
        """必須フィールドが欠けている場合のエラー"""
        thresholds = _make_thresholds(
            {
                "invalid_strategy": {
                    "enabled": True,
                    # class_name が欠けている
                    "strategy_type": "test1",
                }
            }
        )

        with patch(
            "src.strategies.strategy_loader.get_all_thresholds",
            return_value=thresholds,
        ):
            loader = StrategyLoader()
            with pytest.raises(StrategyError, match="class_name"):
                loader.load_strategies()

    def test_load_strategy_class_not_registered(self):
        """未登録のクラス名でエラー"""
        thresholds = _make_thresholds(
            {
                "unknown_strategy": {
                    "enabled": True,
                    "class_name": "UnknownStrategy",
                    "strategy_type": "unknown",
                }
            }
        )

        with patch(
            "src.strategies.strategy_loader.get_all_thresholds",
            return_value=thresholds,
        ):
            loader = StrategyLoader()
            with pytest.raises(
                StrategyError,
                match=r"Registryに未登録で、'module_path'が設定されていません",
            ):
                loader.load_strategies()

    def test_load_strategy_config_passed_to_instance(self):
        """戦略configがインスタンスにそのまま渡されることを確認"""
        thresholds = _make_thresholds(
            {
                "test_strategy": {
                    "enabled": True,
                    "class_name": "TestStrategy1",
                    "strategy_type": "test1",
                    "weight": 0.5,
                    "priority": 1,
                    "regime_affinity": "range",
                    "param1": 100,
                    "param2": "value",
                }
            }
        )

        with patch(
            "src.strategies.strategy_loader.get_all_thresholds",
            return_value=thresholds,
        ):
            loader = StrategyLoader()
            strategies = loader.load_strategies()

            assert len(strategies) == 1
            instance = strategies[0]["instance"]
            # 定義フィールドもパラメータも全て含まれる
            assert instance.config["param1"] == 100
            assert instance.config["param2"] == "value"
            assert instance.config["enabled"] is True
            assert instance.config["class_name"] == "TestStrategy1"


class TestStrategyLoaderUtilityMethods:
    """StrategyLoaderユーティリティメソッドテスト"""

    def setup_method(self):
        """各テストの前にレジストリをクリア"""
        StrategyRegistry.clear_registry()

    def test_get_enabled_strategy_ids(self):
        """有効な戦略IDのリスト取得"""
        thresholds = _make_thresholds(
            {
                "enabled1": {"enabled": True, "class_name": "S1", "strategy_type": "t1"},
                "disabled1": {"enabled": False, "class_name": "S2", "strategy_type": "t2"},
                "enabled2": {"enabled": True, "class_name": "S3", "strategy_type": "t3"},
            }
        )

        with patch(
            "src.strategies.strategy_loader.get_all_thresholds",
            return_value=thresholds,
        ):
            loader = StrategyLoader()
            enabled_ids = loader.get_enabled_strategy_ids()

            assert len(enabled_ids) == 2
            assert "enabled1" in enabled_ids
            assert "enabled2" in enabled_ids
            assert "disabled1" not in enabled_ids

    def test_get_strategy_config(self):
        """特定戦略の設定取得"""
        thresholds = _make_thresholds(
            {
                "target_strategy": {
                    "enabled": True,
                    "class_name": "TargetClass",
                    "strategy_type": "target_type",
                    "weight": 0.5,
                }
            }
        )

        with patch(
            "src.strategies.strategy_loader.get_all_thresholds",
            return_value=thresholds,
        ):
            loader = StrategyLoader()
            strategy_config = loader.get_strategy_config("target_strategy")

            assert strategy_config["enabled"] is True
            assert strategy_config["class_name"] == "TargetClass"
            assert strategy_config["weight"] == 0.5

    def test_get_strategy_config_not_found(self):
        """存在しない戦略の設定取得でエラー"""
        thresholds = _make_thresholds({"existing_strategy": {"enabled": True}})

        with patch(
            "src.strategies.strategy_loader.get_all_thresholds",
            return_value=thresholds,
        ):
            loader = StrategyLoader()
            with pytest.raises(StrategyError, match="が見つかりません"):
                loader.get_strategy_config("nonexistent_strategy")

    def test_get_strategy_config_returns_copy(self):
        """get_strategy_config()がコピーを返すことを確認"""
        thresholds = _make_thresholds(
            {
                "copy_test": {
                    "enabled": True,
                    "class_name": "CopyTest",
                    "strategy_type": "copy",
                }
            }
        )

        with patch(
            "src.strategies.strategy_loader.get_all_thresholds",
            return_value=thresholds,
        ):
            loader = StrategyLoader()
            config1 = loader.get_strategy_config("copy_test")
            config2 = loader.get_strategy_config("copy_test")

            # 異なるオブジェクトであることを確認
            assert config1 is not config2
            # 内容は同じ
            assert config1 == config2


class TestStrategyLoaderDefaultValues:
    """StrategyLoaderデフォルト値テスト"""

    def setup_method(self):
        """各テストの前にレジストリをクリア"""
        StrategyRegistry.clear_registry()

        @StrategyRegistry.register(name="DefaultTest", strategy_type="default")
        class DefaultTest(StrategyBase):
            def __init__(self, config=None):
                self.config = config or {}

            def analyze(self, df):
                return None

            def get_required_features(self):
                return []

    def test_default_weight(self):
        """デフォルトweight=1.0"""
        thresholds = _make_thresholds(
            {
                "no_weight": {
                    "enabled": True,
                    "class_name": "DefaultTest",
                    "strategy_type": "default",
                    # weightなし
                }
            }
        )

        with patch(
            "src.strategies.strategy_loader.get_all_thresholds",
            return_value=thresholds,
        ):
            loader = StrategyLoader()
            strategies = loader.load_strategies()

            assert strategies[0]["weight"] == 1.0

    def test_default_priority(self):
        """デフォルトpriority=99"""
        thresholds = _make_thresholds(
            {
                "no_priority": {
                    "enabled": True,
                    "class_name": "DefaultTest",
                    "strategy_type": "default",
                    # priorityなし
                }
            }
        )

        with patch(
            "src.strategies.strategy_loader.get_all_thresholds",
            return_value=thresholds,
        ):
            loader = StrategyLoader()
            strategies = loader.load_strategies()

            assert strategies[0]["priority"] == 99
