"""
Phase 51.5-B: StrategyLoader単体テスト

Facade Patternによる戦略動的ロードシステムのテスト。
strategies.yamlから戦略を読み込み、動的にインスタンス化。
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from src.core.exceptions import StrategyError
from src.strategies.base.strategy_base import StrategyBase
from src.strategies.strategy_loader import StrategyLoader
from src.strategies.strategy_registry import StrategyRegistry


class TestStrategyLoaderBasic:
    """StrategyLoader基本機能テスト"""

    def setup_method(self):
        """各テストの前にレジストリをクリア"""
        StrategyRegistry.clear_registry()

    def test_init_with_default_path(self):
        """デフォルトパスでの初期化"""
        loader = StrategyLoader()
        assert loader.config_path == Path("config/strategies.yaml")

    def test_init_with_custom_path(self):
        """カスタムパスでの初期化"""
        custom_path = "custom/path/strategies.yaml"
        loader = StrategyLoader(custom_path)
        assert loader.config_path == Path(custom_path)

    def test_load_config_file_not_found(self):
        """存在しないファイルのロードでエラー"""
        loader = StrategyLoader("nonexistent/strategies.yaml")

        with pytest.raises(StrategyError, match="が見つかりません"):
            loader._load_config()

    def test_load_config_missing_strategies_section(self):
        """strategiesセクションがない設定ファイル"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"version": "1.0.0"}, f)
            temp_path = f.name

        try:
            loader = StrategyLoader(temp_path)
            with pytest.raises(StrategyError, match="'strategies' セクションがありません"):
                loader._load_config()
        finally:
            Path(temp_path).unlink()

    def test_load_config_success(self):
        """正常な設定ファイルのロード"""
        config_data = {
            "strategy_system_version": "2.0.0",
            "strategies": {
                "test_strategy": {
                    "enabled": True,
                    "class_name": "TestStrategy",
                    "strategy_type": "test",
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            loader = StrategyLoader(temp_path)
            config = loader._load_config()

            assert "strategies" in config
            assert "test_strategy" in config["strategies"]
            assert config["strategy_system_version"] == "2.0.0"
        finally:
            Path(temp_path).unlink()

    def test_load_config_yaml_parse_error(self):
        """YAMLパースエラー"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [[[")
            temp_path = f.name

        try:
            loader = StrategyLoader(temp_path)
            with pytest.raises(StrategyError, match="YAML解析エラー"):
                loader._load_config()
        finally:
            Path(temp_path).unlink()


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
        config_data = {
            "strategy_system_version": "2.0.0",
            "strategies": {
                "strategy1": {
                    "enabled": True,
                    "class_name": "TestStrategy1",
                    "strategy_type": "test1",
                    "weight": 1.0,
                    "priority": 1,
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            with patch("src.strategies.strategy_loader.get_all_thresholds", return_value={}):
                loader = StrategyLoader(temp_path)
                strategies = loader.load_strategies()

                assert len(strategies) == 1
                assert strategies[0]["weight"] == 1.0
                assert strategies[0]["priority"] == 1
                assert strategies[0]["metadata"]["strategy_id"] == "strategy1"
                assert strategies[0]["metadata"]["name"] == "TestStrategy1"
        finally:
            Path(temp_path).unlink()

    def test_load_strategies_skip_disabled(self):
        """無効な戦略をスキップ"""
        config_data = {
            "strategy_system_version": "2.0.0",
            "strategies": {
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
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            with patch("src.strategies.strategy_loader.get_all_thresholds", return_value={}):
                loader = StrategyLoader(temp_path)
                strategies = loader.load_strategies()

                assert len(strategies) == 1
                assert strategies[0]["metadata"]["strategy_id"] == "enabled_strategy"
        finally:
            Path(temp_path).unlink()

    def test_load_strategies_priority_sorting(self):
        """優先度順にソート"""
        config_data = {
            "strategy_system_version": "2.0.0",
            "strategies": {
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
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            with patch("src.strategies.strategy_loader.get_all_thresholds", return_value={}):
                loader = StrategyLoader(temp_path)
                strategies = loader.load_strategies()

                assert len(strategies) == 2
                assert strategies[0]["metadata"]["strategy_id"] == "high_priority"
                assert strategies[1]["metadata"]["strategy_id"] == "low_priority"
        finally:
            Path(temp_path).unlink()

    def test_load_strategy_missing_required_field(self):
        """必須フィールドが欠けている場合のエラー"""
        config_data = {
            "strategy_system_version": "2.0.0",
            "strategies": {
                "invalid_strategy": {
                    "enabled": True,
                    # class_name が欠けている
                    "strategy_type": "test1",
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            with patch("src.strategies.strategy_loader.get_all_thresholds", return_value={}):
                loader = StrategyLoader(temp_path)
                with pytest.raises(StrategyError, match="class_name"):
                    loader.load_strategies()
        finally:
            Path(temp_path).unlink()

    def test_load_strategy_class_not_registered(self):
        """未登録のクラス名でエラー"""
        config_data = {
            "strategy_system_version": "2.0.0",
            "strategies": {
                "unknown_strategy": {
                    "enabled": True,
                    "class_name": "UnknownStrategy",
                    "strategy_type": "unknown",
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            with patch("src.strategies.strategy_loader.get_all_thresholds", return_value={}):
                loader = StrategyLoader(temp_path)
                with pytest.raises(
                    StrategyError,
                    match=r"Registryに未登録で、'module_path'が設定されていません",
                ):
                    loader.load_strategies()
        finally:
            Path(temp_path).unlink()


class TestStrategyLoaderThresholdsIntegration:
    """StrategyLoader thresholds.yaml統合テスト"""

    def setup_method(self):
        """各テストの前にレジストリをクリア"""
        StrategyRegistry.clear_registry()

        @StrategyRegistry.register(name="ThresholdStrategy", strategy_type="threshold_test")
        class ThresholdStrategy(StrategyBase):
            def __init__(self, config=None):
                self.config = config or {}

            def analyze(self, df):
                return None

            def get_required_features(self):
                return []

        self.ThresholdStrategy = ThresholdStrategy

    def test_get_strategy_thresholds_success(self):
        """thresholds.yamlから戦略設定を取得"""
        config_data = {
            "strategy_system_version": "2.0.0",
            "strategies": {
                "threshold_strategy": {
                    "enabled": True,
                    "class_name": "ThresholdStrategy",
                    "strategy_type": "threshold_test",
                }
            },
        }

        thresholds_data = {"strategies": {"threshold_strategy": {"param1": 100, "param2": "value"}}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            with patch(
                "src.strategies.strategy_loader.get_all_thresholds",
                return_value=thresholds_data,
            ):
                loader = StrategyLoader(temp_path)
                strategies = loader.load_strategies()

                assert len(strategies) == 1
                instance = strategies[0]["instance"]
                assert instance.config["param1"] == 100
                assert instance.config["param2"] == "value"
        finally:
            Path(temp_path).unlink()

    def test_get_strategy_thresholds_missing_config(self):
        """thresholds.yamlに設定がない場合は空辞書"""
        config_data = {
            "strategy_system_version": "2.0.0",
            "strategies": {
                "no_threshold_strategy": {
                    "enabled": True,
                    "class_name": "ThresholdStrategy",
                    "strategy_type": "threshold_test",
                }
            },
        }

        thresholds_data = {"strategies": {}}  # no_threshold_strategyの設定なし

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            with patch(
                "src.strategies.strategy_loader.get_all_thresholds",
                return_value=thresholds_data,
            ):
                loader = StrategyLoader(temp_path)
                strategies = loader.load_strategies()

                assert len(strategies) == 1
                instance = strategies[0]["instance"]
                assert instance.config == {}
        finally:
            Path(temp_path).unlink()

    def test_get_strategy_thresholds_error_fallback(self):
        """thresholds.yaml読み込みエラー時は空辞書"""
        config_data = {
            "strategy_system_version": "2.0.0",
            "strategies": {
                "error_strategy": {
                    "enabled": True,
                    "class_name": "ThresholdStrategy",
                    "strategy_type": "threshold_test",
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            with patch(
                "src.strategies.strategy_loader.get_all_thresholds",
                side_effect=Exception("Threshold load error"),
            ):
                loader = StrategyLoader(temp_path)
                strategies = loader.load_strategies()

                assert len(strategies) == 1
                instance = strategies[0]["instance"]
                assert instance.config == {}
        finally:
            Path(temp_path).unlink()


class TestStrategyLoaderUtilityMethods:
    """StrategyLoaderユーティリティメソッドテスト"""

    def setup_method(self):
        """各テストの前にレジストリをクリア"""
        StrategyRegistry.clear_registry()

    def test_get_enabled_strategy_ids(self):
        """有効な戦略IDのリスト取得"""
        config_data = {
            "strategy_system_version": "2.0.0",
            "strategies": {
                "enabled1": {"enabled": True, "class_name": "S1", "strategy_type": "t1"},
                "disabled1": {
                    "enabled": False,
                    "class_name": "S2",
                    "strategy_type": "t2",
                },
                "enabled2": {"enabled": True, "class_name": "S3", "strategy_type": "t3"},
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            loader = StrategyLoader(temp_path)
            enabled_ids = loader.get_enabled_strategy_ids()

            assert len(enabled_ids) == 2
            assert "enabled1" in enabled_ids
            assert "enabled2" in enabled_ids
            assert "disabled1" not in enabled_ids
        finally:
            Path(temp_path).unlink()

    def test_get_strategy_config(self):
        """特定戦略の設定取得"""
        config_data = {
            "strategy_system_version": "2.0.0",
            "strategies": {
                "target_strategy": {
                    "enabled": True,
                    "class_name": "TargetClass",
                    "strategy_type": "target_type",
                    "weight": 0.5,
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            loader = StrategyLoader(temp_path)
            strategy_config = loader.get_strategy_config("target_strategy")

            assert strategy_config["enabled"] is True
            assert strategy_config["class_name"] == "TargetClass"
            assert strategy_config["weight"] == 0.5
        finally:
            Path(temp_path).unlink()

    def test_get_strategy_config_not_found(self):
        """存在しない戦略の設定取得でエラー"""
        config_data = {
            "strategy_system_version": "2.0.0",
            "strategies": {"existing_strategy": {"enabled": True}},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            loader = StrategyLoader(temp_path)
            with pytest.raises(StrategyError, match="が見つかりません"):
                loader.get_strategy_config("nonexistent_strategy")
        finally:
            Path(temp_path).unlink()

    def test_get_strategy_config_returns_copy(self):
        """get_strategy_config()がコピーを返すことを確認"""
        config_data = {
            "strategy_system_version": "2.0.0",
            "strategies": {
                "copy_test": {
                    "enabled": True,
                    "class_name": "CopyTest",
                    "strategy_type": "copy",
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            loader = StrategyLoader(temp_path)
            config1 = loader.get_strategy_config("copy_test")
            config2 = loader.get_strategy_config("copy_test")

            # 異なるオブジェクトであることを確認
            assert config1 is not config2

            # 内容は同じ
            assert config1 == config2
        finally:
            Path(temp_path).unlink()


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
        config_data = {
            "strategy_system_version": "2.0.0",
            "strategies": {
                "no_weight": {
                    "enabled": True,
                    "class_name": "DefaultTest",
                    "strategy_type": "default",
                    # weightなし
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            with patch("src.strategies.strategy_loader.get_all_thresholds", return_value={}):
                loader = StrategyLoader(temp_path)
                strategies = loader.load_strategies()

                assert strategies[0]["weight"] == 1.0
        finally:
            Path(temp_path).unlink()

    def test_default_priority(self):
        """デフォルトpriority=99"""
        config_data = {
            "strategy_system_version": "2.0.0",
            "strategies": {
                "no_priority": {
                    "enabled": True,
                    "class_name": "DefaultTest",
                    "strategy_type": "default",
                    # priorityなし
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name

        try:
            with patch("src.strategies.strategy_loader.get_all_thresholds", return_value={}):
                loader = StrategyLoader(temp_path)
                strategies = loader.load_strategies()

                assert strategies[0]["priority"] == 99
        finally:
            Path(temp_path).unlink()
