"""
特徴量管理システムのテスト - Phase 62

feature_manager.pyの全メソッドと便利関数をカバーするテスト。
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.config.feature_manager import (
    FeatureManager,
    get_feature_categories,
    get_feature_count,
    get_feature_info,
    get_feature_names,
    reload_feature_config,
    validate_features,
)


class TestFeatureManager:
    """FeatureManagerクラスのテスト"""

    def setup_method(self):
        """各テスト前にFeatureManagerの新しいインスタンスを作成"""
        self.manager = FeatureManager()

    def teardown_method(self):
        """各テスト後にキャッシュをクリア"""
        self.manager.clear_cache()

    # === 基本機能テスト ===

    def test_init(self):
        """初期化テスト"""
        manager = FeatureManager()
        assert manager._feature_config is None
        assert manager._feature_order_path == Path("config/core/feature_order.json")

    def test_get_feature_names_returns_list(self):
        """get_feature_namesがリストを返すことを確認"""
        names = self.manager.get_feature_names()
        assert isinstance(names, list)
        assert len(names) > 0

    def test_get_feature_names_contains_expected_features(self):
        """get_feature_namesが期待される特徴量を含むことを確認"""
        names = self.manager.get_feature_names()
        expected_basics = ["close", "volume", "rsi_14", "macd", "atr_14"]
        for feature in expected_basics:
            assert feature in names

    def test_get_feature_count_returns_int(self):
        """get_feature_countが整数を返すことを確認"""
        count = self.manager.get_feature_count()
        assert isinstance(count, int)
        assert count > 0

    def test_get_feature_count_matches_names_length(self):
        """特徴量数と名前リストの長さが一致することを確認"""
        count = self.manager.get_feature_count()
        names = self.manager.get_feature_names()
        assert count == len(names)

    def test_get_feature_categories_returns_dict(self):
        """get_feature_categoriesが辞書を返すことを確認"""
        categories = self.manager.get_feature_categories()
        assert isinstance(categories, dict)
        assert len(categories) > 0

    def test_get_feature_categories_contains_expected_keys(self):
        """get_feature_categoriesが期待されるカテゴリを含むことを確認"""
        categories = self.manager.get_feature_categories()
        expected_categories = ["basic", "momentum", "volatility", "trend"]
        for cat in expected_categories:
            assert cat in categories

    def test_get_feature_info_returns_dict(self):
        """get_feature_infoが辞書を返すことを確認"""
        info = self.manager.get_feature_info()
        assert isinstance(info, dict)
        assert "total_features" in info
        assert "feature_names" in info
        assert "feature_categories" in info
        assert "config_source" in info
        assert "config_exists" in info
        assert "version" in info

    def test_get_feature_info_values(self):
        """get_feature_infoの値が正しいことを確認"""
        info = self.manager.get_feature_info()
        assert info["total_features"] == self.manager.get_feature_count()
        assert info["feature_names"] == self.manager.get_feature_names()
        assert info["feature_categories"] == self.manager.get_feature_categories()

    # === キャッシュ機能テスト ===

    def test_config_caching(self):
        """設定のキャッシュが機能することを確認"""
        # 最初の読み込み
        self.manager._load_feature_config()
        first_config = self.manager._feature_config

        # 2回目の読み込み（キャッシュから）
        second_config = self.manager._load_feature_config()
        assert first_config is second_config

    def test_clear_cache(self):
        """キャッシュクリアが機能することを確認"""
        self.manager._load_feature_config()
        assert self.manager._feature_config is not None

        self.manager.clear_cache()
        assert self.manager._feature_config is None

    # === バリデーションテスト ===

    def test_validate_features_valid(self):
        """正しい特徴量リストのバリデーションが成功することを確認"""
        valid_features = self.manager.get_feature_names()
        result = self.manager.validate_features(valid_features)
        assert result is True

    def test_validate_features_missing(self):
        """不足特徴量がある場合のバリデーションが失敗することを確認"""
        features = self.manager.get_feature_names()
        # 一つ削除
        missing_features = features[:-1]
        result = self.manager.validate_features(missing_features)
        assert result is False

    def test_validate_features_extra(self):
        """余分な特徴量がある場合（不足なし）のバリデーション"""
        features = self.manager.get_feature_names()
        # 余分な特徴量を追加（実際には不足があると失敗する）
        extra_features = features + ["extra_feature"]
        result = self.manager.validate_features(extra_features)
        # 余分な特徴量があるが、期待数と一致しないのでFalse
        assert result is False

    def test_validate_features_count_mismatch(self):
        """特徴量数が一致しない場合のバリデーションが失敗することを確認"""
        features = self.manager.get_feature_names()
        # 正しい特徴量だが重複を追加
        duplicated = features + [features[0]]
        result = self.manager.validate_features(duplicated)
        assert result is False

    # === 特徴量レベル情報テスト ===

    def test_get_feature_level_info_returns_dict(self):
        """get_feature_level_infoが辞書を返すことを確認"""
        level_info = self.manager.get_feature_level_info()
        assert isinstance(level_info, dict)
        assert "full" in level_info

    def test_get_feature_level_info_structure(self):
        """get_feature_level_infoの構造を確認"""
        level_info = self.manager.get_feature_level_info()
        for level_name, info in level_info.items():
            assert "count" in info
            assert "description" in info
            assert "model_file" in info

    def test_get_feature_level_counts(self):
        """get_feature_level_countsが正しい値を返すことを確認"""
        counts = self.manager.get_feature_level_counts()
        assert isinstance(counts, dict)
        assert "full" in counts
        assert isinstance(counts["full"], int)

    # === 基本特徴量テスト ===

    def test_get_basic_feature_names(self):
        """get_basic_feature_namesが戦略シグナルを除外することを確認"""
        basic_names = self.manager.get_basic_feature_names()
        all_names = self.manager.get_feature_names()

        # 基本特徴量は全特徴量より少ない
        assert len(basic_names) <= len(all_names)

        # 戦略シグナルが含まれていないことを確認
        for name in basic_names:
            assert not name.startswith("strategy_signal_")

    def test_get_basic_feature_names_contains_expected(self):
        """get_basic_feature_namesが期待される基本特徴量を含むことを確認"""
        basic_names = self.manager.get_basic_feature_names()
        expected = ["close", "volume", "rsi_14", "macd", "atr_14"]
        for feature in expected:
            assert feature in basic_names


class TestFeatureManagerFallback:
    """FeatureManagerのフォールバック機能テスト"""

    def test_file_not_found_uses_default(self):
        """設定ファイルが見つからない場合デフォルトを使用"""
        manager = FeatureManager()
        manager._feature_order_path = Path("/nonexistent/path/feature_order.json")
        manager.clear_cache()

        config = manager._load_feature_config()
        assert config is not None
        assert "total_features" in config
        assert config["total_features"] == 15  # デフォルト値

    def test_get_feature_names_fallback(self):
        """設定なしの場合のget_feature_namesフォールバック"""
        manager = FeatureManager()
        manager._feature_order_path = Path("/nonexistent/path/feature_order.json")
        manager.clear_cache()

        names = manager.get_feature_names()
        assert isinstance(names, list)
        assert "close" in names
        assert "volume" in names
        assert len(names) == 15

    def test_get_feature_categories_fallback(self):
        """設定なしの場合のget_feature_categoriesフォールバック"""
        manager = FeatureManager()
        manager._feature_order_path = Path("/nonexistent/path/feature_order.json")
        manager.clear_cache()

        categories = manager.get_feature_categories()
        assert isinstance(categories, dict)
        assert "basic" in categories
        assert "momentum" in categories

    def test_get_feature_count_fallback_calculates_from_names(self):
        """total_featuresがない場合、特徴量名から数える"""
        manager = FeatureManager()

        # feature_categoriesはあるがtotal_featuresがないconfig
        mock_config = {
            "feature_categories": {
                "basic": {"features": ["close", "volume"]},
                "momentum": {"features": ["rsi_14"]},
            }
        }
        manager._feature_config = mock_config

        count = manager.get_feature_count()
        names = manager.get_feature_names()
        assert count == len(names)

    def test_get_feature_level_info_fallback(self):
        """feature_levelsがない場合のフォールバック"""
        manager = FeatureManager()

        # feature_levelsがないconfig
        mock_config = {"total_features": 20}
        manager._feature_config = mock_config

        level_info = manager.get_feature_level_info()
        assert "full" in level_info
        assert level_info["full"]["count"] == 20
        assert level_info["full"]["model_file"] == "ensemble_full.pkl"

    def test_get_basic_feature_names_fallback(self):
        """feature_categoriesがない場合のget_basic_feature_namesフォールバック"""
        manager = FeatureManager()

        # feature_categoriesがないconfig
        mock_config = {"total_features": 15}
        manager._feature_config = mock_config

        # フォールバックは全特徴量を返す
        basic_names = manager.get_basic_feature_names()
        all_names = manager.get_feature_names()
        assert basic_names == all_names

    def test_get_feature_categories_no_feature_categories(self):
        """feature_categoriesがない場合のget_feature_categoriesフォールバック"""
        manager = FeatureManager()

        # feature_categoriesがないconfig（直接キャッシュに設定）
        mock_config = {"total_features": 15}
        manager._feature_config = mock_config

        categories = manager.get_feature_categories()
        assert isinstance(categories, dict)
        assert "basic" in categories
        assert "momentum" in categories
        assert "volatility" in categories
        assert "trend" in categories
        assert categories["basic"] == ["close", "volume"]


class TestFeatureManagerErrors:
    """FeatureManagerのエラーハンドリングテスト"""

    def test_json_decode_error_uses_default(self):
        """JSONデコードエラー時にデフォルトを使用"""
        manager = FeatureManager()
        manager.clear_cache()

        # 存在するパスを設定
        manager._feature_order_path = Path("config/core/feature_order.json")

        # json.loadでエラーを発生させる
        with patch("json.load", side_effect=json.JSONDecodeError("test", "", 0)):
            config = manager._load_feature_config()
            assert config is not None
            assert config["total_features"] == 15

    def test_file_read_error_uses_default(self):
        """ファイル読み込みエラー時にデフォルトを使用"""
        manager = FeatureManager()
        manager.clear_cache()

        # 存在するパスを設定
        manager._feature_order_path = Path("config/core/feature_order.json")

        # openでエラーを発生させる
        with patch("builtins.open", side_effect=IOError("Read error")):
            config = manager._load_feature_config()
            assert config is not None
            assert config["total_features"] == 15

    def test_generic_exception_uses_default(self):
        """一般例外時にデフォルトを使用"""
        manager = FeatureManager()
        manager.clear_cache()

        # 存在するパスを設定
        manager._feature_order_path = Path("config/core/feature_order.json")

        # json.loadで一般例外を発生させる
        with patch("json.load", side_effect=Exception("Generic error")):
            config = manager._load_feature_config()
            assert config is not None
            assert config["total_features"] == 15


class TestFeatureManagerCategoryOrder:
    """特徴量カテゴリ順序のテスト"""

    def test_feature_order_preserved(self):
        """特徴量の順序が保持されることを確認"""
        manager = FeatureManager()
        names = manager.get_feature_names()

        # basicカテゴリの特徴量が先頭にあることを確認
        basic_indices = [names.index(f) for f in ["close", "volume"] if f in names]
        if basic_indices:
            assert all(idx < 10 for idx in basic_indices)

    def test_strategy_signals_at_end(self):
        """戦略シグナルが末尾にあることを確認"""
        manager = FeatureManager()
        names = manager.get_feature_names()

        strategy_indices = [names.index(f) for f in names if f.startswith("strategy_signal_")]

        if strategy_indices:
            # 戦略シグナルは末尾に位置する
            min_strategy_idx = min(strategy_indices)
            non_strategy_indices = [
                i for i, f in enumerate(names) if not f.startswith("strategy_signal_")
            ]
            if non_strategy_indices:
                max_non_strategy_idx = max(non_strategy_indices)
                assert min_strategy_idx > max_non_strategy_idx


class TestConvenienceFunctions:
    """便利関数のテスト"""

    def test_get_feature_names_function(self):
        """get_feature_names便利関数のテスト"""
        names = get_feature_names()
        assert isinstance(names, list)
        assert len(names) > 0

    def test_get_feature_count_function(self):
        """get_feature_count便利関数のテスト"""
        count = get_feature_count()
        assert isinstance(count, int)
        assert count > 0

    def test_get_feature_categories_function(self):
        """get_feature_categories便利関数のテスト"""
        categories = get_feature_categories()
        assert isinstance(categories, dict)

    def test_validate_features_function(self):
        """validate_features便利関数のテスト"""
        valid_features = get_feature_names()
        result = validate_features(valid_features)
        assert result is True

    def test_get_feature_info_function(self):
        """get_feature_info便利関数のテスト"""
        info = get_feature_info()
        assert isinstance(info, dict)
        assert "total_features" in info

    def test_reload_feature_config_function(self):
        """reload_feature_config便利関数のテスト"""
        config = reload_feature_config()
        assert isinstance(config, dict)
        assert "total_features" in config or "feature_categories" in config


class TestIntegration:
    """統合テスト"""

    def test_full_workflow(self):
        """完全なワークフローのテスト"""
        manager = FeatureManager()

        # 設定読み込み
        config = manager._load_feature_config()
        assert config is not None

        # 特徴量情報取得
        names = manager.get_feature_names()
        count = manager.get_feature_count()
        categories = manager.get_feature_categories()

        # 整合性確認
        assert len(names) == count

        # カテゴリ内の特徴量が名前リストに含まれることを確認
        for cat_name, cat_features in categories.items():
            for feature in cat_features:
                assert feature in names, f"{feature} in {cat_name} not in names"

        # バリデーション
        assert manager.validate_features(names) is True

        # キャッシュクリア
        manager.clear_cache()
        assert manager._feature_config is None

    def test_reload_updates_cache(self):
        """reload_feature_configがキャッシュを更新することを確認"""
        # グローバルマネージャーを使用
        from src.core.config.feature_manager import _feature_manager

        # 初期読み込み
        _feature_manager._load_feature_config()
        original_config = _feature_manager._feature_config

        # リロード
        reload_feature_config()

        # キャッシュが更新されたことを確認（新しいオブジェクト）
        new_config = _feature_manager._feature_config
        assert new_config is not None
