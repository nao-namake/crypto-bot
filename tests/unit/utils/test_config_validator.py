# tests/unit/utils/test_config_validator.py
"""
設定検証機能のテスト
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from crypto_bot.utils.config_validator import (
    ConfigValidationError,
    ConfigValidator,
    validate_config_file,
)


class TestConfigValidator:
    """ConfigValidatorクラスのテスト"""

    def test_valid_config(self):
        """有効な設定の検証"""
        valid_config = {
            "data": {
                "exchange": "bybit",
                "symbol": "BTC/USDT",
                "timeframe": "1h",
                "limit": 1000,
            },
            "strategy": {
                "params": {"threshold": 0.1, "thresholds_to_test": [0.05, 0.1, 0.15]}
            },
            "risk": {
                "risk_per_trade": 0.01,
                "stop_atr_mult": 2.0,
                "dynamic_position_sizing": {"enabled": True},
            },
            "backtest": {"starting_balance": 10000.0, "slippage_rate": 0.001},
            "walk_forward": {"train_window": 1500, "test_window": 250, "step": 250},
            "ml": {
                "model_type": "lgbm",
                "target_type": "classification",
                "feat_period": 14,
                "horizon": 5,
                "rolling_window": 20,
                "lags": [1, 2, 3],
                "extra_features": ["rsi_14", "macd"],
                "optuna": {"n_trials": 30, "timeout": 900},
            },
        }

        validator = ConfigValidator()
        # エラーが発生しないことを確認
        validator.validate(valid_config)

    def test_missing_required_fields(self):
        """必須フィールドが欠けている場合"""
        invalid_config = {
            "data": {
                # exchange, symbol, timeframe が欠けている
                "limit": 1000
            }
        }

        validator = ConfigValidator()
        with pytest.raises(ConfigValidationError) as exc_info:
            validator.validate(invalid_config)

        error_msg = str(exc_info.value)
        assert "data.exchange は必須です" in error_msg
        assert "data.symbol は必須です" in error_msg
        assert "data.timeframe は必須です" in error_msg

    def test_invalid_exchange(self):
        """無効な取引所名"""
        invalid_config = {
            "data": {
                "exchange": "invalid_exchange",
                "symbol": "BTC/USDT",
                "timeframe": "1h",
            }
        }

        validator = ConfigValidator()
        with pytest.raises(ConfigValidationError) as exc_info:
            validator.validate(invalid_config)

        assert "data.exchange は" in str(exc_info.value)

    def test_invalid_timeframe(self):
        """無効な時間枠"""
        invalid_config = {
            "data": {
                "exchange": "bybit",
                "symbol": "BTC/USDT",
                "timeframe": "2h",  # 無効な時間枠
            }
        }

        validator = ConfigValidator()
        with pytest.raises(ConfigValidationError) as exc_info:
            validator.validate(invalid_config)

        assert "data.timeframe は" in str(exc_info.value)

    def test_invalid_limit(self):
        """無効な制限値"""
        invalid_config = {
            "data": {
                "exchange": "bybit",
                "symbol": "BTC/USDT",
                "timeframe": "1h",
                "limit": -100,  # 負の値
            }
        }

        validator = ConfigValidator()
        with pytest.raises(ConfigValidationError) as exc_info:
            validator.validate(invalid_config)

        assert "data.limit は正の整数である必要があります" in str(exc_info.value)

    def test_invalid_threshold(self):
        """無効な閾値"""
        invalid_config = {"strategy": {"params": {"threshold": 1.5}}}  # 範囲外

        validator = ConfigValidator()
        with pytest.raises(ConfigValidationError) as exc_info:
            validator.validate(invalid_config)

        assert (
            "strategy.params.threshold は -1.0 から 1.0 の間である必要があります"
            in str(exc_info.value)
        )

    def test_invalid_thresholds_to_test(self):
        """無効な閾値リスト"""
        invalid_config = {
            "strategy": {"params": {"thresholds_to_test": []}}  # 空のリスト
        }

        validator = ConfigValidator()
        with pytest.raises(ConfigValidationError) as exc_info:
            validator.validate(invalid_config)

        assert (
            "strategy.params.thresholds_to_test は空でないリストである必要があります"
            in str(exc_info.value)
        )

    def test_invalid_risk_per_trade(self):
        """無効なリスク率"""
        invalid_config = {"risk": {"risk_per_trade": 1.5}}  # 1.0より大きい

        validator = ConfigValidator()
        with pytest.raises(ConfigValidationError) as exc_info:
            validator.validate(invalid_config)

        assert (
            "risk.risk_per_trade は 0 より大きく 1.0 以下である必要があります"
            in str(exc_info.value)
        )

    def test_invalid_stop_atr_mult(self):
        """無効なATR倍率"""
        invalid_config = {"risk": {"stop_atr_mult": -1.0}}  # 負の値

        validator = ConfigValidator()
        with pytest.raises(ConfigValidationError) as exc_info:
            validator.validate(invalid_config)

        assert "risk.stop_atr_mult は正の数である必要があります" in str(exc_info.value)

    def test_invalid_starting_balance(self):
        """無効な初期残高"""
        invalid_config = {"backtest": {"starting_balance": -1000}}  # 負の値

        validator = ConfigValidator()
        with pytest.raises(ConfigValidationError) as exc_info:
            validator.validate(invalid_config)

        assert "backtest.starting_balance は正の数である必要があります" in str(
            exc_info.value
        )

    def test_invalid_slippage_rate(self):
        """無効なスリッページ率"""
        invalid_config = {"backtest": {"slippage_rate": 1.5}}  # 1.0より大きい

        validator = ConfigValidator()
        with pytest.raises(ConfigValidationError) as exc_info:
            validator.validate(invalid_config)

        assert "backtest.slippage_rate は 0 から 1.0 の間である必要があります" in str(
            exc_info.value
        )

    def test_invalid_walk_forward_params(self):
        """無効なウォークフォワードパラメータ"""
        invalid_config = {
            "walk_forward": {
                "train_window": -100,  # 負の値
                "test_window": 0,  # ゼロ
                "step": "invalid",  # 文字列
            }
        }

        validator = ConfigValidator()
        with pytest.raises(ConfigValidationError) as exc_info:
            validator.validate(invalid_config)

        error_msg = str(exc_info.value)
        assert "walk_forward.train_window は正の整数である必要があります" in error_msg
        assert "walk_forward.test_window は正の整数である必要があります" in error_msg
        assert "walk_forward.step は正の整数である必要があります" in error_msg

    def test_invalid_ml_model_type(self):
        """無効なMLモデルタイプ"""
        invalid_config = {"ml": {"model_type": "invalid_model"}}

        validator = ConfigValidator()
        with pytest.raises(ConfigValidationError) as exc_info:
            validator.validate(invalid_config)

        assert "ml.model_type は" in str(exc_info.value)

    def test_invalid_ml_params(self):
        """無効なMLパラメータ"""
        invalid_config = {
            "ml": {
                "feat_period": -1,
                "horizon": 0,
                "rolling_window": "invalid",
                "lags": [1, -2, 3],  # 負の値を含む
                "extra_features": "not_a_list",  # リストではない
            }
        }

        validator = ConfigValidator()
        with pytest.raises(ConfigValidationError) as exc_info:
            validator.validate(invalid_config)

        error_msg = str(exc_info.value)
        assert "ml.feat_period は正の整数である必要があります" in error_msg
        assert "ml.horizon は正の整数である必要があります" in error_msg
        assert "ml.rolling_window は正の整数である必要があります" in error_msg
        assert "ml.lags[1] は正の整数である必要があります" in error_msg
        assert "ml.extra_features はリストである必要があります" in error_msg

    def test_invalid_optuna_params(self):
        """無効なOptunaパラメータ"""
        invalid_config = {"ml": {"optuna": {"n_trials": -10, "timeout": 0}}}

        validator = ConfigValidator()
        with pytest.raises(ConfigValidationError) as exc_info:
            validator.validate(invalid_config)

        error_msg = str(exc_info.value)
        assert "ml.optuna.n_trials は正の整数である必要があります" in error_msg
        assert "ml.optuna.timeout は正の数である必要があります" in error_msg


def test_validate_config_file():
    """設定ファイル検証の統合テスト"""
    valid_config = {
        "data": {"exchange": "bybit", "symbol": "BTC/USDT", "timeframe": "1h"}
    }

    # 一時ファイルに設定を書き出し
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yaml.dump(valid_config, f)
        temp_path = f.name

    try:
        # ファイルから設定を検証
        validate_config_file(temp_path)
    finally:
        # 一時ファイルを削除
        Path(temp_path).unlink()


def test_validate_config_file_not_found():
    """存在しないファイルのテスト"""
    with pytest.raises(FileNotFoundError):
        validate_config_file("non_existent_file.yml")


def test_validate_config_file_invalid():
    """無効な設定ファイルのテスト"""
    invalid_config = {
        "data": {
            "exchange": "invalid_exchange",
            "symbol": "BTC/USDT",
            "timeframe": "1h",
        }
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yaml.dump(invalid_config, f)
        temp_path = f.name

    try:
        with pytest.raises(ConfigValidationError):
            validate_config_file(temp_path)
    finally:
        Path(temp_path).unlink()
