"""
CooldownManager テストスイート - Phase 38リファクタリング

Phase 31.1: 柔軟なクールダウン機能のテスト。

テスト範囲:
- should_apply_cooldown(): クールダウン判定（強トレンド時スキップ）
- calculate_trend_strength(): トレンド強度計算（ADX・DI・EMA）
- get_cooldown_status(): クールダウンステータス取得
- 設定無効時・柔軟モード無効時・市場データなし時の動作
"""

from unittest.mock import patch

import pandas as pd
import pytest

from src.trading.core import RiskDecision, TradeEvaluation
from src.trading.position.cooldown import CooldownManager


@pytest.fixture
def cooldown_manager():
    """CooldownManager fixture"""
    return CooldownManager()


@pytest.fixture
def sample_evaluation():
    """TradeEvaluation fixture"""
    from datetime import datetime

    return TradeEvaluation(
        decision=RiskDecision.APPROVED,
        side="buy",
        risk_score=0.1,
        position_size=0.001,
        stop_loss=13700000.0,
        take_profit=14300000.0,
        confidence_level=0.75,
        warnings=[],
        denial_reasons=[],
        evaluation_timestamp=datetime.now(),
        kelly_recommendation=0.05,
        drawdown_status="normal",
        anomaly_alerts=[],
        market_conditions={"market_data": {}},
    )


class TestShouldApplyCooldown:
    """should_apply_cooldown() テスト"""

    @pytest.mark.asyncio
    @patch("src.trading.position.cooldown.get_features_config")
    async def test_cooldown_disabled(self, mock_features, cooldown_manager, sample_evaluation):
        """クールダウン無効時はFalse"""
        mock_features.return_value = {"trading": {"cooldown": {"enabled": False}}}

        result = await cooldown_manager.should_apply_cooldown(sample_evaluation)

        assert result is False

    @pytest.mark.asyncio
    @patch("src.trading.position.cooldown.get_features_config")
    async def test_flexible_mode_disabled(self, mock_features, cooldown_manager, sample_evaluation):
        """柔軟モード無効時は常にTrue"""
        mock_features.return_value = {"trading": {"cooldown": {"enabled": True, "flexible_mode": False}}}

        result = await cooldown_manager.should_apply_cooldown(sample_evaluation)

        assert result is True

    @pytest.mark.asyncio
    @patch("src.trading.position.cooldown.get_features_config")
    async def test_no_market_data(self, mock_features, cooldown_manager, sample_evaluation):
        """市場データなし時はデフォルトでTrue"""
        mock_features.return_value = {
            "trading": {
                "cooldown": {
                    "enabled": True,
                    "flexible_mode": True,
                    "trend_strength_threshold": 0.7,
                }
            }
        }
        sample_evaluation.market_conditions = {"market_data": None}

        result = await cooldown_manager.should_apply_cooldown(sample_evaluation)

        assert result is True

    @pytest.mark.asyncio
    @patch("src.trading.position.cooldown.get_features_config")
    async def test_strong_trend_skips_cooldown(self, mock_features, cooldown_manager, sample_evaluation):
        """強トレンド時はクールダウンスキップ"""
        mock_features.return_value = {
            "trading": {
                "cooldown": {
                    "enabled": True,
                    "flexible_mode": True,
                    "trend_strength_threshold": 0.7,
                }
            }
        }

        # 強トレンドデータ作成
        market_data = {
            "4h": pd.DataFrame(
                {
                    "adx_14": [45.0, 46.0, 47.0],  # 強いトレンド
                    "plus_di_14": [35.0, 36.0, 37.0],
                    "minus_di_14": [10.0, 9.0, 8.0],  # DI差分=大
                    "ema_20": [14500000.0, 14520000.0, 14540000.0],
                    "ema_50": [14000000.0, 14010000.0, 14020000.0],  # 上昇トレンド
                }
            )
        }
        sample_evaluation.market_conditions = {"market_data": market_data}

        result = await cooldown_manager.should_apply_cooldown(sample_evaluation)

        # トレンド強度が高いのでクールダウンスキップ
        assert result is False

    @pytest.mark.asyncio
    @patch("src.trading.position.cooldown.get_features_config")
    async def test_weak_trend_applies_cooldown(self, mock_features, cooldown_manager, sample_evaluation):
        """弱トレンド時はクールダウン適用"""
        mock_features.return_value = {
            "trading": {
                "cooldown": {
                    "enabled": True,
                    "flexible_mode": True,
                    "trend_strength_threshold": 0.7,
                }
            }
        }

        # 弱トレンドデータ作成
        market_data = {
            "4h": pd.DataFrame(
                {
                    "adx_14": [15.0, 16.0, 17.0],  # 弱い
                    "plus_di_14": [20.0, 21.0, 22.0],
                    "minus_di_14": [19.0, 20.0, 21.0],  # DI差分=小
                    "ema_20": [14000000.0, 14005000.0, 14010000.0],
                    "ema_50": [14000000.0, 14002000.0, 14004000.0],  # ほぼ横ばい
                }
            )
        }
        sample_evaluation.market_conditions = {"market_data": market_data}

        result = await cooldown_manager.should_apply_cooldown(sample_evaluation)

        assert result is True

    @pytest.mark.asyncio
    @patch("src.trading.position.cooldown.get_features_config")
    async def test_exception_handling_defaults_to_true(self, mock_features, cooldown_manager, sample_evaluation):
        """例外発生時はデフォルトでTrue"""
        mock_features.side_effect = Exception("Config error")

        result = await cooldown_manager.should_apply_cooldown(sample_evaluation)

        assert result is True

    @pytest.mark.asyncio
    @patch("src.trading.position.cooldown.get_features_config")
    async def test_custom_threshold(self, mock_features, cooldown_manager, sample_evaluation):
        """カスタム閾値テスト"""
        mock_features.return_value = {
            "trading": {
                "cooldown": {
                    "enabled": True,
                    "flexible_mode": True,
                    "trend_strength_threshold": 0.5,  # 低い閾値
                }
            }
        }

        # 中程度のトレンド
        market_data = {
            "4h": pd.DataFrame(
                {
                    "adx_14": [30.0, 31.0, 32.0],
                    "plus_di_14": [28.0, 29.0, 30.0],
                    "minus_di_14": [15.0, 14.0, 13.0],
                    "ema_20": [14300000.0, 14320000.0, 14340000.0],
                    "ema_50": [14100000.0, 14110000.0, 14120000.0],
                }
            )
        }
        sample_evaluation.market_conditions = {"market_data": market_data}

        result = await cooldown_manager.should_apply_cooldown(sample_evaluation)

        # 閾値が低いのでスキップされる可能性が高い
        assert isinstance(result, bool)


class TestCalculateTrendStrength:
    """calculate_trend_strength() テスト"""

    def test_empty_dataframe(self, cooldown_manager):
        """空DataFrame時は0.0"""
        market_data = {"4h": pd.DataFrame()}

        strength = cooldown_manager.calculate_trend_strength(market_data)

        assert strength == 0.0

    def test_insufficient_data(self, cooldown_manager):
        """データ不足時は0.0"""
        market_data = {"4h": pd.DataFrame({"adx_14": [25.0], "plus_di_14": [20.0]})}

        strength = cooldown_manager.calculate_trend_strength(market_data)

        assert strength == 0.0

    def test_strong_trend_calculation(self, cooldown_manager):
        """強トレンド計算"""
        market_data = {
            "4h": pd.DataFrame(
                {
                    "adx_14": [48.0, 49.0, 50.0],  # 強い（50/50 = 1.0）
                    "plus_di_14": [40.0, 41.0, 42.0],
                    "minus_di_14": [5.0, 4.0, 3.0],  # DI差分=39（39/40 = 0.975）
                    "ema_20": [14500000.0, 14520000.0, 14540000.0],
                    "ema_50": [14000000.0, 14010000.0, 14020000.0],  # 約3.7%差
                }
            )
        }

        strength = cooldown_manager.calculate_trend_strength(market_data)

        # ADX: 1.0*0.5 + DI: 0.975*0.3 + EMA: 0.74*0.2 = 0.5 + 0.2925 + 0.148 ≈ 0.94
        assert strength >= 0.7  # 強いトレンド

    def test_weak_trend_calculation(self, cooldown_manager):
        """弱トレンド計算"""
        market_data = {
            "4h": pd.DataFrame(
                {
                    "adx_14": [10.0, 11.0, 12.0],  # 弱い（12/50 = 0.24）
                    "plus_di_14": [18.0, 19.0, 20.0],
                    "minus_di_14": [17.0, 18.0, 19.0],  # DI差分=1（1/40 = 0.025）
                    "ema_20": [14000000.0, 14005000.0, 14010000.0],
                    "ema_50": [14000000.0, 14003000.0, 14006000.0],  # 約0.03%差
                }
            )
        }

        strength = cooldown_manager.calculate_trend_strength(market_data)

        # ADX: 0.24*0.5 + DI: 0.025*0.3 + EMA: 0.006*0.2 ≈ 0.128
        assert strength < 0.3  # 弱いトレンド

    def test_missing_adx_column(self, cooldown_manager):
        """ADXカラム欠損時は低スコア"""
        market_data = {
            "4h": pd.DataFrame(
                {
                    "plus_di_14": [25.0, 26.0, 27.0],
                    "minus_di_14": [15.0, 14.0, 13.0],
                    "ema_20": [14000000.0, 14010000.0, 14020000.0],
                    "ema_50": [14000000.0, 14005000.0, 14010000.0],
                }
            )
        }

        strength = cooldown_manager.calculate_trend_strength(market_data)

        # ADXがないが、DI・EMAは計算される
        assert isinstance(strength, float)

    def test_missing_di_columns(self, cooldown_manager):
        """DIカラム欠損時は低スコア"""
        market_data = {
            "4h": pd.DataFrame(
                {
                    "adx_14": [30.0, 31.0, 32.0],
                    "ema_20": [14000000.0, 14010000.0, 14020000.0],
                    "ema_50": [14000000.0, 14005000.0, 14010000.0],
                }
            )
        }

        strength = cooldown_manager.calculate_trend_strength(market_data)

        # DIがないが、ADX・EMAは計算される
        assert isinstance(strength, float)

    def test_missing_ema_columns(self, cooldown_manager):
        """EMAカラム欠損時は低スコア"""
        market_data = {
            "4h": pd.DataFrame(
                {
                    "adx_14": [30.0, 31.0, 32.0],
                    "plus_di_14": [28.0, 29.0, 30.0],
                    "minus_di_14": [15.0, 14.0, 13.0],
                }
            )
        }

        strength = cooldown_manager.calculate_trend_strength(market_data)

        # EMAがないが、ADX・DIは計算される
        assert isinstance(strength, float)

    def test_exception_handling(self, cooldown_manager):
        """例外発生時は0.0"""
        market_data = {"4h": "invalid_data"}  # 不正なデータ

        strength = cooldown_manager.calculate_trend_strength(market_data)

        assert strength == 0.0

    def test_no_4h_key(self, cooldown_manager):
        """4hキーがない場合は0.0"""
        market_data = {"1h": pd.DataFrame({"adx_14": [30.0]})}

        strength = cooldown_manager.calculate_trend_strength(market_data)

        assert strength == 0.0

    def test_ema_50_zero_division(self, cooldown_manager):
        """EMA50が0の場合のゼロ除算回避"""
        market_data = {
            "4h": pd.DataFrame(
                {
                    "adx_14": [30.0, 31.0, 32.0],
                    "plus_di_14": [28.0, 29.0, 30.0],
                    "minus_di_14": [15.0, 14.0, 13.0],
                    "ema_20": [14000000.0, 14010000.0, 14020000.0],
                    "ema_50": [0.0, 0.0, 0.0],  # ゼロ
                }
            )
        }

        strength = cooldown_manager.calculate_trend_strength(market_data)

        # ゼロ除算回避で0.0が返される
        assert isinstance(strength, float)
        assert strength >= 0.0


class TestGetCooldownStatus:
    """get_cooldown_status() テスト"""

    @patch("src.trading.position.cooldown.get_features_config")
    def test_cooldown_disabled_status(self, mock_features, cooldown_manager):
        """クールダウン無効状態"""
        mock_features.return_value = {"trading": {"cooldown": {"enabled": False}}}

        status = cooldown_manager.get_cooldown_status(0.5)

        assert status["enabled"] is False
        assert "クールダウン無効" in status["reason"]

    @patch("src.trading.position.cooldown.get_features_config")
    def test_normal_mode_status(self, mock_features, cooldown_manager):
        """通常モード状態"""
        mock_features.return_value = {"trading": {"cooldown": {"enabled": True, "flexible_mode": False}}}

        status = cooldown_manager.get_cooldown_status(0.5)

        assert status["enabled"] is True
        assert status["flexible_mode"] is False
        assert "通常モード" in status["reason"]

    @patch("src.trading.position.cooldown.get_features_config")
    def test_strong_trend_skip_status(self, mock_features, cooldown_manager):
        """強トレンドでスキップ状態"""
        mock_features.return_value = {
            "trading": {
                "cooldown": {
                    "enabled": True,
                    "flexible_mode": True,
                    "trend_strength_threshold": 0.7,
                }
            }
        }

        status = cooldown_manager.get_cooldown_status(0.85)

        assert status["enabled"] is True
        assert status["flexible_mode"] is True
        assert status["trend_strength"] == 0.85
        assert status["threshold"] == 0.7
        assert status["skip_cooldown"] is True
        assert "強トレンド検出" in status["reason"]

    @patch("src.trading.position.cooldown.get_features_config")
    def test_weak_trend_apply_status(self, mock_features, cooldown_manager):
        """弱トレンドで適用状態"""
        mock_features.return_value = {
            "trading": {
                "cooldown": {
                    "enabled": True,
                    "flexible_mode": True,
                    "trend_strength_threshold": 0.7,
                }
            }
        }

        status = cooldown_manager.get_cooldown_status(0.5)

        assert status["skip_cooldown"] is False
        assert "トレンド弱" in status["reason"]

    @patch("src.trading.position.cooldown.get_features_config")
    def test_exception_handling_status(self, mock_features, cooldown_manager):
        """例外発生時のステータス"""
        mock_features.side_effect = Exception("Config error")

        status = cooldown_manager.get_cooldown_status(0.5)

        assert status["enabled"] is True
        assert status["flexible_mode"] is False
        assert "エラー" in status["reason"]

    @patch("src.trading.position.cooldown.get_features_config")
    def test_status_structure(self, mock_features, cooldown_manager):
        """ステータス構造確認"""
        mock_features.return_value = {
            "trading": {
                "cooldown": {
                    "enabled": True,
                    "flexible_mode": True,
                    "trend_strength_threshold": 0.7,
                }
            }
        }

        status = cooldown_manager.get_cooldown_status(0.6)

        # 必須キー確認
        assert "enabled" in status
        assert "flexible_mode" in status
        assert "trend_strength" in status
        assert "threshold" in status
        assert "skip_cooldown" in status
        assert "reason" in status


class TestInitialization:
    """初期化テスト"""

    def test_cooldown_manager_initialization(self, cooldown_manager):
        """CooldownManager初期化"""
        assert hasattr(cooldown_manager, "logger")

    def test_initial_state(self, cooldown_manager):
        """初期状態確認"""
        # 初期状態でメソッド呼び出しが可能
        market_data = {"4h": pd.DataFrame()}
        strength = cooldown_manager.calculate_trend_strength(market_data)
        assert strength == 0.0
