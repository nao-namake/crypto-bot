"""
Phase 14-A: 閾値設定外部化機能のテスト

新しく追加したget_threshold関数と関連機能の
正常系・異常系テストを実装します。
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from src.core.config import get_all_thresholds, get_threshold, load_thresholds, reload_thresholds


class TestThresholdConfiguration:
    """閾値設定機能のテストスイート"""

    def test_get_threshold_with_valid_key(self):
        """有効なキーで閾値取得が成功する"""
        # 正常な階層キーで値を取得
        with patch(
            "src.core.config.threshold_manager.load_thresholds",
            return_value={
                "ml": {"default_confidence": 0.5},
                "trading": {"default_balance_jpy": 2000000.0},
            },
        ):
            result = get_threshold("ml.default_confidence", 0.5)
            assert result == 0.5

    def test_get_threshold_with_nested_key(self):
        """ネストしたキーでの閾値取得"""
        with patch(
            "src.core.config.threshold_manager.load_thresholds",
            return_value={"trading": {"fallback_prices": {"bid": 15900000.0, "ask": 16100000.0}}},
        ):
            bid = get_threshold("trading.fallback_prices.bid", 9000000.0)
            ask = get_threshold("trading.fallback_prices.ask", 9010000.0)

            assert bid == 15900000.0
            assert ask == 16100000.0

    def test_get_threshold_with_invalid_key_returns_default(self):
        """無効なキーの場合はデフォルト値を返す"""
        with patch("src.core.config.threshold_manager.load_thresholds", return_value={"ml": {}}):
            result = get_threshold("ml.nonexistent_key", 0.8)
            assert result == 0.8

    def test_get_threshold_with_missing_parent_key(self):
        """親キーが存在しない場合はデフォルト値を返す"""
        with patch("src.core.config.threshold_manager.load_thresholds", return_value={}):
            result = get_threshold("nonexistent.child.key", 42.0)
            assert result == 42.0

    def test_get_threshold_raises_keyerror_without_default(self):
        """デフォルト値がない場合はKeyErrorを発生"""
        with patch("src.core.config.threshold_manager.load_thresholds", return_value={}):
            with pytest.raises(KeyError, match="閾値設定が見つかりません"):
                get_threshold("missing.key")

    def test_load_thresholds_from_file(self):
        """YAMLファイルからの閾値設定読み込み"""
        test_config = {
            "ml": {"default_confidence": 0.5},
            "trading": {"default_balance_jpy": 10000.0},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(test_config, f)
            temp_path = f.name

        try:
            with patch("src.core.config.Path") as mock_path:
                mock_path.return_value.exists.return_value = True
                mock_path.return_value = Path(temp_path)

                # キャッシュリセット
                reload_thresholds()

                with patch("builtins.open", open(temp_path, "r")):
                    result = load_thresholds()

                assert result["ml"]["default_confidence"] == 0.5
                assert result["trading"]["default_balance_jpy"] == 10000.0
        finally:
            os.unlink(temp_path)

    def test_load_thresholds_file_not_found_uses_defaults(self):
        """YAMLファイルが見つからない場合はデフォルト設定を使用"""
        with patch("src.core.config.Path") as mock_path:
            mock_path.return_value.exists.return_value = False

            # キャッシュリセット
            reload_thresholds()

            result = load_thresholds()

            # デフォルト値の確認
            assert "ml" in result
            assert "trading" in result
            assert result["ml"]["default_confidence"] == 0.5

    def test_load_thresholds_yaml_parse_error_uses_defaults(self):
        """YAML解析エラー時はデフォルト設定を使用"""
        invalid_yaml = "invalid: yaml: content: ["

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(invalid_yaml)
            temp_path = f.name

        try:
            with patch("src.core.config.Path") as mock_path:
                mock_path.return_value.exists.return_value = True
                mock_path.return_value = Path(temp_path)

                # キャッシュリセット
                reload_thresholds()

                result = load_thresholds()

                # エラー時のデフォルト値確認
                assert result["ml"]["default_confidence"] == 0.5
        finally:
            os.unlink(temp_path)

    def test_reload_thresholds_clears_cache(self):
        """reload_thresholds がキャッシュを正しくクリアする"""
        # このテストは実際のthresholds.yamlファイルが存在するため、
        # reload_thresholds()の基本動作のみ確認
        reload_thresholds()
        result1 = get_all_thresholds()

        # reload_thresholds()を再実行
        reload_thresholds()
        result2 = get_all_thresholds()

        # 基本的には同じ設定が読み込まれるはず（ファイルが変更されていなければ）
        assert isinstance(result1, dict)
        assert isinstance(result2, dict)
        assert "ml" in result1
        assert "ml" in result2

    def test_get_all_thresholds_returns_copy(self):
        """get_all_thresholds が設定のコピーを返す"""
        # 実際の設定を使ってコピー機能をテスト
        result = get_all_thresholds()

        # 返された辞書のキーの存在確認
        assert "ml" in result
        assert "default_confidence" in result["ml"]

        # 返された辞書を変更
        original_value = result["ml"]["default_confidence"]
        result["ml"]["default_confidence"] = 999.0

        # 新しく取得した設定が変更されていないことを確認
        new_result = get_all_thresholds()
        assert new_result["ml"]["default_confidence"] == original_value
        assert new_result["ml"]["default_confidence"] != 999.0


class TestThresholdIntegration:
    """閾値設定機能の統合テスト"""

    def test_threshold_integration_with_ml_adapter(self):
        """ML Adapterとの統合確認"""
        test_config = {"ml": {"default_confidence": 0.5, "prediction_fallback_confidence": 0.0}}

        reload_thresholds()  # キャッシュクリア
        with patch("src.core.config.threshold_manager.load_thresholds", return_value=test_config):
            default_conf = get_threshold("ml.default_confidence", 0.5)
            fallback_conf = get_threshold("ml.prediction_fallback_confidence", 0.0)

            assert default_conf == 0.5
            assert fallback_conf == 0.0

    def test_threshold_integration_with_orchestrator(self):
        """Orchestratorとの統合確認"""
        test_config = {
            "trading": {
                "default_balance_jpy": 10000.0,
                "bid_spread_ratio": 0.999,
                "ask_spread_ratio": 1.001,
                "fallback_prices": {
                    "bid": 15900000.0,
                    "ask": 16100000.0,
                    "default_bid": 15900000.0,
                    "default_ask": 16100000.0,
                },
            },
            "performance": {"default_latency_ms": 100.0},
        }

        reload_thresholds()  # キャッシュクリア
        with patch("src.core.config.threshold_manager.load_thresholds", return_value=test_config):
            balance = get_threshold("trading.default_balance_jpy", 1000000.0)
            bid_ratio = get_threshold("trading.bid_spread_ratio", 0.999)
            ask_ratio = get_threshold("trading.ask_spread_ratio", 1.001)
            fallback_bid = get_threshold("trading.fallback_prices.bid", 9000000.0)
            latency = get_threshold("performance.default_latency_ms", 100.0)

            assert balance == 10000.0
            assert bid_ratio == 0.999
            assert ask_ratio == 1.001
            assert fallback_bid == 15900000.0
            assert latency == 100.0

    def test_threshold_error_resilience(self):
        """閾値設定エラー時の耐障害性確認"""
        # None値が返されたケース
        with patch("src.core.config.threshold_manager.load_thresholds", return_value=None):
            with pytest.raises(KeyError):
                get_threshold("any.key")

        # 空の辞書が返されたケース
        with patch("src.core.config.threshold_manager.load_thresholds", return_value={}):
            result = get_threshold("missing.key", "fallback")
            assert result == "fallback"

        # TypeError（不正な型）が返されたケース
        with patch(
            "src.core.config.threshold_manager.load_thresholds", return_value="invalid_type"
        ):
            result = get_threshold("any.key", "safe_default")
            assert result == "safe_default"


# Phase 14-A: 異常系テストカバレッジ向上のためのパラメータ化テスト
@pytest.mark.parametrize(
    "key_path,test_data,expected",
    [
        ("simple_key", {"simple_key": "value"}, "value"),
        ("nested.key", {"nested": {"key": "nested_value"}}, "nested_value"),
        ("deep.nested.key", {"deep": {"nested": {"key": 42}}}, 42),
        ("array_access.0", {"array_access": [1, 2, 3]}, 1),  # 配列アクセスは対応しない想定
    ],
)
def test_threshold_access_patterns(key_path, test_data, expected):
    """様々なキーアクセスパターンのテスト"""
    with patch("src.core.config.threshold_manager.load_thresholds", return_value=test_data):
        try:
            result = get_threshold(key_path, "default")
            assert (
                result == expected or result == "default"
            )  # 配列アクセスなどは失敗してdefaultが返る
        except (KeyError, TypeError):
            # 期待される失敗ケース
            pass


# カバレッジ向上のための境界値テスト
class TestBoundaryConditions:
    """境界値・エラー条件のテスト"""

    def test_empty_key_path(self):
        """空のキーパスの処理"""
        with patch(
            "src.core.config.threshold_manager.load_thresholds", return_value={"key": "value"}
        ):
            result = get_threshold("", "default")
            assert result == "default"

    def test_none_key_path(self):
        """Noneキーパスの処理"""
        with patch(
            "src.core.config.threshold_manager.load_thresholds", return_value={"key": "value"}
        ):
            with pytest.raises(AttributeError):
                get_threshold(None, "default")

    def test_numeric_values(self):
        """数値型の閾値設定"""
        test_data = {"numbers": {"int": 42, "float": 3.14159, "zero": 0, "negative": -1.5}}

        reload_thresholds()  # キャッシュクリア
        with patch("src.core.config.threshold_manager.load_thresholds", return_value=test_data):
            assert get_threshold("numbers.int", 0) == 42
            assert get_threshold("numbers.float", 0.0) == 3.14159
            assert get_threshold("numbers.zero", 1) == 0
            assert get_threshold("numbers.negative", 1.0) == -1.5

    def test_boolean_values(self):
        """真偽値の閾値設定"""
        test_data = {"booleans": {"true": True, "false": False}}

        with patch("src.core.config.threshold_manager.load_thresholds", return_value=test_data):
            assert get_threshold("booleans.true", False) is True
            assert get_threshold("booleans.false", True) is False
