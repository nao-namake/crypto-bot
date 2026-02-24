"""
ML予測統合機能テスト - Phase 29.5

trading_cycle_manager.pyのML予測統合ロジックをテスト。
一致時のボーナス、不一致時のペナルティ、加重平均計算を検証。
"""

import os
import sys
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))

from src.core.logger import CryptoBotLogger
from src.core.services.trading_cycle_manager import TradingCycleManager
from src.strategies.base.strategy_base import StrategySignal


class TestMLIntegration:
    """ML予測統合機能のテスト"""

    @pytest.fixture
    def mock_orchestrator(self):
        """モックOrchestratorを作成"""
        orchestrator = Mock()
        orchestrator.config = Mock()
        orchestrator.config.mode = "paper"
        return orchestrator

    @pytest.fixture
    def trading_cycle_manager(self, mock_orchestrator):
        """TradingCycleManager初期化"""
        logger = CryptoBotLogger(name="test_ml_integration")
        return TradingCycleManager(mock_orchestrator, logger)

    @patch("src.core.services.trading_cycle_manager.get_threshold")
    def test_ml_integration_disabled(self, mock_get_threshold, trading_cycle_manager):
        """ML統合無効時は戦略シグナルをそのまま返す"""

        # ML統合無効に設定
        def threshold_side_effect(key, default):
            if key == "ml.strategy_integration.enabled":
                return False
            return default

        mock_get_threshold.side_effect = threshold_side_effect

        ml_prediction = {"prediction": 1, "confidence": 0.9}
        strategy_signal = StrategySignal(
            strategy_name="test_strategy",
            timestamp=datetime.now(),
            action="sell",
            confidence=0.7,
            strength=0.7,
            current_price=17000000.0,
        )

        result = trading_cycle_manager._integrate_ml_with_strategy(ml_prediction, strategy_signal)

        # 統合されず、元のシグナルがそのまま返される
        assert result == strategy_signal

    @patch("src.core.services.trading_cycle_manager.get_threshold")
    def test_ml_low_confidence_ignored(self, mock_get_threshold, trading_cycle_manager):
        """ML信頼度が低い場合は統合しない"""

        def threshold_side_effect(key, default):
            if key == "ml.strategy_integration.enabled":
                return True
            if key == "ml.strategy_integration.min_ml_confidence":
                return 0.6
            return default

        mock_get_threshold.side_effect = threshold_side_effect

        ml_prediction = {"prediction": 1, "confidence": 0.5}  # 0.5 < 0.6
        strategy_signal = StrategySignal(
            strategy_name="test_strategy",
            timestamp=datetime.now(),
            action="buy",
            confidence=0.7,
            strength=0.7,
            current_price=17000000.0,
        )

        result = trading_cycle_manager._integrate_ml_with_strategy(ml_prediction, strategy_signal)

        # ML信頼度不足のため元のシグナルを返す
        assert result == strategy_signal

    @patch("src.core.services.trading_cycle_manager.get_threshold")
    def test_ml_strategy_agreement_bonus(self, mock_get_threshold, trading_cycle_manager):
        """ML予測と戦略が一致し、ML高信頼度の場合はボーナス適用"""

        def threshold_side_effect(key, default):
            thresholds = {
                "ml.strategy_integration.enabled": True,
                "ml.strategy_integration.min_ml_confidence": 0.6,
                "ml.strategy_integration.ml_weight": 0.3,
                "ml.strategy_integration.strategy_weight": 0.7,
                "ml.strategy_integration.high_confidence_threshold": 0.8,
                "ml.strategy_integration.agreement_bonus": 1.2,
            }
            return thresholds.get(key, default)

        mock_get_threshold.side_effect = threshold_side_effect

        ml_prediction = {
            "prediction": 2,
            "confidence": 0.9,
        }  # buy, 高信頼度（Phase 51.9: 真の3クラス分類）
        strategy_signal = StrategySignal(
            strategy_name="test_strategy",
            timestamp=datetime.now(),
            action="buy",
            confidence=0.7,
            strength=0.7,
            current_price=17000000.0,
        )

        result = trading_cycle_manager._integrate_ml_with_strategy(ml_prediction, strategy_signal)

        # 加重平均: 0.7 * 0.7 + 0.9 * 0.3 = 0.49 + 0.27 = 0.76
        # ボーナス適用: 0.76 * 1.2 = 0.912
        assert result.action == "buy"
        assert result.metadata["ml_adjusted"] is True
        assert result.metadata["is_agreement"] is True
        assert 0.90 < result.confidence <= 0.92  # ボーナス適用後

    @patch("src.core.services.trading_cycle_manager.get_threshold")
    def test_ml_strategy_disagreement_penalty(self, mock_get_threshold, trading_cycle_manager):
        """ML予測と戦略が不一致で、ML高信頼度の場合はペナルティ適用"""

        def threshold_side_effect(key, default):
            thresholds = {
                "ml.strategy_integration.enabled": True,
                "ml.strategy_integration.min_ml_confidence": 0.6,
                "ml.strategy_integration.ml_weight": 0.3,
                "ml.strategy_integration.strategy_weight": 0.7,
                "ml.strategy_integration.high_confidence_threshold": 0.8,
                "ml.strategy_integration.disagreement_penalty": 0.7,
            }
            return thresholds.get(key, default)

        mock_get_threshold.side_effect = threshold_side_effect

        ml_prediction = {
            "prediction": 0,
            "confidence": 0.9,
        }  # sell, 高信頼度（Phase 51.9: 真の3クラス分類）
        strategy_signal = StrategySignal(
            strategy_name="test_strategy",
            timestamp=datetime.now(),
            action="buy",
            confidence=0.7,
            strength=0.7,
            current_price=17000000.0,
        )

        result = trading_cycle_manager._integrate_ml_with_strategy(ml_prediction, strategy_signal)

        # 加重平均: 0.7 * 0.7 + 0.9 * 0.3 = 0.76
        # ペナルティ適用: 0.76 * 0.7 = 0.532
        assert result.action == "buy"
        assert result.metadata["ml_adjusted"] is True
        assert result.metadata["is_agreement"] is False
        assert 0.50 < result.confidence < 0.55  # ペナルティ適用後

    @patch("src.core.services.trading_cycle_manager.get_threshold")
    def test_ml_strategy_disagreement_extreme_penalty(
        self, mock_get_threshold, trading_cycle_manager
    ):
        """不一致かつ信頼度極低の場合はholdに変更"""

        def threshold_side_effect(key, default):
            thresholds = {
                "ml.strategy_integration.enabled": True,
                "ml.strategy_integration.min_ml_confidence": 0.6,
                "ml.strategy_integration.ml_weight": 0.3,
                "ml.strategy_integration.strategy_weight": 0.7,
                "ml.strategy_integration.high_confidence_threshold": 0.8,
                "ml.strategy_integration.disagreement_penalty": 0.5,  # 強いペナルティ
            }
            return thresholds.get(key, default)

        mock_get_threshold.side_effect = threshold_side_effect

        ml_prediction = {
            "prediction": 0,
            "confidence": 0.9,
        }  # sell, 高信頼度（Phase 51.9: 真の3クラス分類）
        strategy_signal = StrategySignal(
            strategy_name="test_strategy",
            timestamp=datetime.now(),
            action="buy",
            confidence=0.5,
            strength=0.5,
            current_price=17000000.0,
        )

        result = trading_cycle_manager._integrate_ml_with_strategy(ml_prediction, strategy_signal)

        # 加重平均: 0.5 * 0.7 + 0.9 * 0.3 = 0.35 + 0.27 = 0.62
        # ペナルティ適用: 0.62 * 0.5 = 0.31 < 0.4
        # → holdに変更
        assert result.action == "hold"
        assert result.metadata["ml_adjusted"] is True
        assert result.metadata["original_action"] == "buy"
        assert result.metadata["adjustment_reason"] == "ml_disagreement_low_confidence"

    @patch("src.core.services.trading_cycle_manager.get_threshold")
    def test_ml_normal_integration_weighted_average(
        self, mock_get_threshold, trading_cycle_manager
    ):
        """ML通常統合（信頼度が高くない場合）は加重平均のみ"""

        def threshold_side_effect(key, default):
            thresholds = {
                "ml.strategy_integration.enabled": True,
                "ml.strategy_integration.min_ml_confidence": 0.6,
                "ml.strategy_integration.ml_weight": 0.3,
                "ml.strategy_integration.strategy_weight": 0.7,
                "ml.strategy_integration.high_confidence_threshold": 0.8,
            }
            return thresholds.get(key, default)

        mock_get_threshold.side_effect = threshold_side_effect

        ml_prediction = {"prediction": 1, "confidence": 0.7}  # buy, 通常信頼度
        strategy_signal = StrategySignal(
            strategy_name="test_strategy",
            timestamp=datetime.now(),
            action="buy",
            confidence=0.6,
            strength=0.6,
            current_price=17000000.0,
        )

        result = trading_cycle_manager._integrate_ml_with_strategy(ml_prediction, strategy_signal)

        # 加重平均: 0.6 * 0.7 + 0.7 * 0.3 = 0.42 + 0.21 = 0.63
        # ボーナス・ペナルティなし
        assert result.action == "buy"
        assert result.metadata["ml_adjusted"] is True
        assert 0.62 < result.confidence < 0.64

    @patch("src.core.services.trading_cycle_manager.get_threshold")
    def test_ml_prediction_mapping(self, mock_get_threshold, trading_cycle_manager):
        """ML予測値(-1, 0, 1)のアクションマッピング確認"""

        def threshold_side_effect(key, default):
            thresholds = {
                "ml.strategy_integration.enabled": True,
                "ml.strategy_integration.min_ml_confidence": 0.6,
                "ml.strategy_integration.ml_weight": 0.3,
                "ml.strategy_integration.strategy_weight": 0.7,
            }
            return thresholds.get(key, default)

        mock_get_threshold.side_effect = threshold_side_effect

        strategy_signal = StrategySignal(
            strategy_name="test_strategy",
            timestamp=datetime.now(),
            action="hold",
            confidence=0.5,
            strength=0.5,
            current_price=17000000.0,
        )

        # Phase 51.9: 真の3クラス分類 (0: sell, 1: hold, 2: buy)
        # 0: sell
        ml_sell = {"prediction": 0, "confidence": 0.7}
        result_sell = trading_cycle_manager._integrate_ml_with_strategy(ml_sell, strategy_signal)
        assert result_sell.metadata["ml_action"] == "sell"

        # 1: hold
        ml_hold = {"prediction": 1, "confidence": 0.7}
        result_hold = trading_cycle_manager._integrate_ml_with_strategy(ml_hold, strategy_signal)
        assert result_hold.metadata["ml_action"] == "hold"

        # 2: buy
        ml_buy = {"prediction": 2, "confidence": 0.7}
        result_buy = trading_cycle_manager._integrate_ml_with_strategy(ml_buy, strategy_signal)
        assert result_buy.metadata["ml_action"] == "buy"

    @patch("src.core.services.trading_cycle_manager.get_threshold")
    def test_ml_integration_error_handling(self, mock_get_threshold, trading_cycle_manager):
        """ML統合処理でエラーが発生した場合、元のシグナルを返す"""

        # エラーを発生させる
        mock_get_threshold.side_effect = Exception("設定取得エラー")

        ml_prediction = {"prediction": 1, "confidence": 0.9}
        strategy_signal = StrategySignal(
            strategy_name="test_strategy",
            timestamp=datetime.now(),
            action="buy",
            confidence=0.7,
            strength=0.7,
            current_price=17000000.0,
        )

        result = trading_cycle_manager._integrate_ml_with_strategy(ml_prediction, strategy_signal)

        # エラー時は元のシグナルをそのまま返す
        assert result == strategy_signal


class TestFixedWeights:
    """固定重み取得テスト"""

    @pytest.fixture
    def mock_orchestrator(self):
        """モックOrchestratorを作成"""
        orchestrator = Mock()
        orchestrator.config = Mock()
        orchestrator.config.mode = "paper"
        return orchestrator

    @pytest.fixture
    def trading_cycle_manager(self, mock_orchestrator):
        """TradingCycleManager初期化"""
        logger = CryptoBotLogger(name="test_fixed_weights")
        return TradingCycleManager(mock_orchestrator, logger)

    @patch("src.core.services.trading_cycle_manager.get_threshold")
    def test_get_dynamic_weights_returns_fixed_weights(
        self, mock_get_threshold, trading_cycle_manager
    ):
        """固定重みが正しく返されることを確認"""

        def threshold_side_effect(key, default):
            if key == "ml.strategy_integration.ml_weight":
                return 0.35
            if key == "ml.strategy_integration.strategy_weight":
                return 0.7
            return default

        mock_get_threshold.side_effect = threshold_side_effect

        weights = trading_cycle_manager._get_dynamic_weights()

        assert weights["ml"] == 0.35
        assert weights["strategy"] == 0.7

    @patch("src.core.services.trading_cycle_manager.get_threshold")
    def test_integrate_ml_with_strategy_uses_weights(
        self, mock_get_threshold, trading_cycle_manager
    ):
        """_integrate_ml_with_strategy()内で重みが使用されることを確認"""

        dynamic_ml_weight = 0.6
        dynamic_strategy_weight = 0.4

        def threshold_side_effect(key, default):
            if key == "ml.strategy_integration.enabled":
                return True
            if key == "ml.strategy_integration.min_ml_confidence":
                return 0.45
            if key == "ml.strategy_integration.ml_weight":
                return dynamic_ml_weight
            if key == "ml.strategy_integration.strategy_weight":
                return dynamic_strategy_weight
            if key == "ml.strategy_integration.high_confidence_threshold":
                return 0.8
            return default

        mock_get_threshold.side_effect = threshold_side_effect

        ml_prediction = {"prediction": 1, "confidence": 0.7}
        strategy_signal = StrategySignal(
            strategy_name="test_strategy",
            timestamp=datetime.now(),
            action="buy",
            confidence=0.6,
            strength=0.6,
            current_price=17000000.0,
        )

        result = trading_cycle_manager._integrate_ml_with_strategy(ml_prediction, strategy_signal)

        # expected_confidence = 0.6 * 0.4 + 0.7 * 0.6 = 0.24 + 0.42 = 0.66
        assert result.action == "buy"
        assert 0.65 < result.confidence < 0.67


class TestMinStrategyConfidence:
    """Phase 61.5: 戦略信頼度最低閾値テスト"""

    @pytest.fixture
    def mock_orchestrator(self):
        """モックOrchestratorを作成"""
        orchestrator = Mock()
        orchestrator.config = Mock()
        orchestrator.config.mode = "paper"
        return orchestrator

    @pytest.fixture
    def trading_cycle_manager(self, mock_orchestrator):
        """TradingCycleManager初期化"""
        logger = CryptoBotLogger(name="test_min_strategy_confidence")
        return TradingCycleManager(mock_orchestrator, logger)

    @patch("src.core.services.trading_cycle_manager.get_threshold")
    def test_low_confidence_forced_hold(self, mock_get_threshold, trading_cycle_manager):
        """Phase 61.5: 信頼度0.25未満で強制HOLD"""

        def threshold_side_effect(key, default):
            thresholds = {
                "ml.strategy_integration.enabled": True,
                "ml.strategy_integration.min_strategy_confidence": 0.25,
            }
            return thresholds.get(key, default)

        mock_get_threshold.side_effect = threshold_side_effect

        ml_prediction = {"prediction": 2, "confidence": 0.9}  # buy, 高信頼度
        strategy_signal = StrategySignal(
            strategy_name="test_strategy",
            timestamp=datetime.now(),
            action="buy",
            confidence=0.20,  # 0.20 < 0.25 → HOLD変換
            strength=0.20,
            current_price=17000000.0,
        )

        result = trading_cycle_manager._integrate_ml_with_strategy(ml_prediction, strategy_signal)

        # 強制HOLD変換
        assert result.action == "hold"
        assert result.metadata["forced_hold_reason"] == "min_strategy_confidence"
        assert result.metadata["original_action"] == "buy"
        assert result.metadata["original_confidence"] == 0.20

    @patch("src.core.services.trading_cycle_manager.get_threshold")
    def test_normal_confidence_passes(self, mock_get_threshold, trading_cycle_manager):
        """Phase 61.5: 信頼度0.25以上は通常処理"""

        def threshold_side_effect(key, default):
            thresholds = {
                "ml.strategy_integration.enabled": True,
                "ml.strategy_integration.min_strategy_confidence": 0.25,
                "ml.strategy_integration.min_ml_confidence": 0.3,
                "ml.strategy_integration.ml_weight": 0.3,
                "ml.strategy_integration.strategy_weight": 0.7,
            }
            return thresholds.get(key, default)

        mock_get_threshold.side_effect = threshold_side_effect

        ml_prediction = {"prediction": 2, "confidence": 0.5}  # buy
        strategy_signal = StrategySignal(
            strategy_name="test_strategy",
            timestamp=datetime.now(),
            action="buy",
            confidence=0.40,  # 0.40 >= 0.25 → 通常処理
            strength=0.40,
            current_price=17000000.0,
        )

        result = trading_cycle_manager._integrate_ml_with_strategy(ml_prediction, strategy_signal)

        # 通常のML統合処理が行われる
        assert result.action == "buy"
        assert result.metadata["ml_adjusted"] is True
        assert "forced_hold_reason" not in result.metadata

    @patch("src.core.services.trading_cycle_manager.get_threshold")
    def test_boundary_confidence_passes(self, mock_get_threshold, trading_cycle_manager):
        """Phase 61.5: 境界値0.25は通常処理（>= なので）"""

        def threshold_side_effect(key, default):
            thresholds = {
                "ml.strategy_integration.enabled": True,
                "ml.strategy_integration.min_strategy_confidence": 0.25,
                "ml.strategy_integration.min_ml_confidence": 0.3,
                "ml.strategy_integration.ml_weight": 0.3,
                "ml.strategy_integration.strategy_weight": 0.7,
            }
            return thresholds.get(key, default)

        mock_get_threshold.side_effect = threshold_side_effect

        ml_prediction = {"prediction": 0, "confidence": 0.5}  # sell
        strategy_signal = StrategySignal(
            strategy_name="test_strategy",
            timestamp=datetime.now(),
            action="sell",
            confidence=0.25,  # 境界値0.25 → 通常処理（>= なので）
            strength=0.25,
            current_price=17000000.0,
        )

        result = trading_cycle_manager._integrate_ml_with_strategy(ml_prediction, strategy_signal)

        # 境界値は通常処理
        assert result.action == "sell"
        assert result.metadata["ml_adjusted"] is True
        assert "forced_hold_reason" not in result.metadata

    @patch("src.core.services.trading_cycle_manager.get_threshold")
    def test_sell_signal_low_confidence_forced_hold(
        self, mock_get_threshold, trading_cycle_manager
    ):
        """Phase 61.5: SELL信号も低信頼度で強制HOLD"""

        def threshold_side_effect(key, default):
            thresholds = {
                "ml.strategy_integration.enabled": True,
                "ml.strategy_integration.min_strategy_confidence": 0.25,
            }
            return thresholds.get(key, default)

        mock_get_threshold.side_effect = threshold_side_effect

        ml_prediction = {"prediction": 2, "confidence": 0.8}  # buy（戦略と不一致）
        strategy_signal = StrategySignal(
            strategy_name="test_strategy",
            timestamp=datetime.now(),
            action="sell",
            confidence=0.239,  # 1/27の実際の値（0.239 < 0.25）
            strength=0.239,
            current_price=17000000.0,
        )

        result = trading_cycle_manager._integrate_ml_with_strategy(ml_prediction, strategy_signal)

        # 強制HOLD変換
        assert result.action == "hold"
        assert result.metadata["forced_hold_reason"] == "min_strategy_confidence"
        assert result.metadata["original_action"] == "sell"


class TestMLSignalRecovery:
    """Phase 65.16: ML Signal Recovery テスト"""

    @pytest.fixture
    def mock_orchestrator(self):
        orchestrator = Mock()
        orchestrator.config = Mock()
        orchestrator.config.mode = "paper"
        return orchestrator

    @pytest.fixture
    def trading_cycle_manager(self, mock_orchestrator):
        logger = CryptoBotLogger(name="test_ml_recovery")
        return TradingCycleManager(mock_orchestrator, logger)

    def _make_threshold_side_effect(self, recovery_enabled=True, recovery_overrides=None):
        """ML Signal Recovery用のthreshold mock生成"""
        recovery_config = {
            "enabled": recovery_enabled,
            "min_ml_confidence": 0.55,
            "min_individual_confidence": 0.30,
            "recovery_confidence_cap": 0.35,
        }
        if recovery_overrides:
            recovery_config.update(recovery_overrides)

        def side_effect(key, default):
            thresholds = {
                "ml.strategy_integration.enabled": True,
                "ml.strategy_integration.min_strategy_confidence": 0.22,
                "ml.strategy_integration.min_ml_confidence": 0.32,
                "ml.strategy_integration.ml_weight": 0.35,
                "ml.strategy_integration.strategy_weight": 0.7,
                "ml.strategy_integration.high_confidence_threshold": 0.6,
                "ml.strategy_integration.agreement_bonus": 1.2,
                "ml.strategy_integration.disagreement_penalty": 0.95,
                "ml.strategy_integration.hold_conversion_threshold": 0.15,
                "ml.strategy_integration.ml_signal_recovery": recovery_config,
                "ml.regime_ml_integration.enabled": False,
            }
            return thresholds.get(key, default)

        return side_effect

    @patch("src.core.services.trading_cycle_manager.get_threshold")
    def test_recovery_basic_buy(self, mock_get_threshold, trading_cycle_manager):
        """ML Recovery基本動作: 戦略HOLD + ML BUY + 個別戦略BUY → BUY回復"""
        mock_get_threshold.side_effect = self._make_threshold_side_effect()

        ml_prediction = {"prediction": 2, "confidence": 0.65}  # BUY
        strategy_signal = StrategySignal(
            strategy_name="weighted_vote",
            timestamp=datetime.now(),
            action="hold",
            confidence=0.35,
            strength=0.35,
            current_price=14500000.0,
        )
        individual_signals = {
            "ATRBased": {"action": "buy", "confidence": 0.45},
            "BBReversal": {"action": "hold", "confidence": 0.30},
            "StochasticDivergence": {"action": "hold", "confidence": 0.25},
        }

        result = trading_cycle_manager._integrate_ml_with_strategy(
            ml_prediction,
            strategy_signal,
            individual_strategy_signals=individual_signals,
        )

        assert result.action == "buy"
        assert result.metadata["ml_recovery"] is True
        assert result.metadata["recovery_strategy"] == "ATRBased"
        assert result.confidence <= 0.35  # cap適用
        assert result.confidence == min(0.65 * 0.45, 0.35)

    @patch("src.core.services.trading_cycle_manager.get_threshold")
    def test_recovery_basic_sell(self, mock_get_threshold, trading_cycle_manager):
        """ML Recovery: 戦略HOLD + ML SELL + 個別戦略SELL → SELL回復"""
        mock_get_threshold.side_effect = self._make_threshold_side_effect()

        ml_prediction = {"prediction": 0, "confidence": 0.70}  # SELL
        strategy_signal = StrategySignal(
            strategy_name="weighted_vote",
            timestamp=datetime.now(),
            action="hold",
            confidence=0.30,
            strength=0.30,
            current_price=14500000.0,
        )
        individual_signals = {
            "MACDEMACrossover": {"action": "sell", "confidence": 0.40},
            "BBReversal": {"action": "hold", "confidence": 0.20},
        }

        result = trading_cycle_manager._integrate_ml_with_strategy(
            ml_prediction,
            strategy_signal,
            individual_strategy_signals=individual_signals,
        )

        assert result.action == "sell"
        assert result.metadata["ml_recovery"] is True
        assert result.metadata["recovery_strategy"] == "MACDEMACrossover"

    @patch("src.core.services.trading_cycle_manager.get_threshold")
    def test_recovery_not_triggered_ml_hold(self, mock_get_threshold, trading_cycle_manager):
        """ML自体がHOLD → Recovery不発動"""
        mock_get_threshold.side_effect = self._make_threshold_side_effect()

        ml_prediction = {"prediction": 1, "confidence": 0.80}  # HOLD
        strategy_signal = StrategySignal(
            strategy_name="weighted_vote",
            timestamp=datetime.now(),
            action="hold",
            confidence=0.30,
            strength=0.30,
            current_price=14500000.0,
        )
        individual_signals = {
            "ATRBased": {"action": "buy", "confidence": 0.50},
        }

        result = trading_cycle_manager._integrate_ml_with_strategy(
            ml_prediction,
            strategy_signal,
            individual_strategy_signals=individual_signals,
        )

        assert result.action == "hold"
        assert result.metadata.get("ml_recovery") is not True

    @patch("src.core.services.trading_cycle_manager.get_threshold")
    def test_recovery_not_triggered_ml_low_confidence(
        self, mock_get_threshold, trading_cycle_manager
    ):
        """ML信頼度不足（0.50 < 0.55） → Recovery不発動"""
        mock_get_threshold.side_effect = self._make_threshold_side_effect()

        ml_prediction = {"prediction": 2, "confidence": 0.50}  # BUY but low confidence
        strategy_signal = StrategySignal(
            strategy_name="weighted_vote",
            timestamp=datetime.now(),
            action="hold",
            confidence=0.30,
            strength=0.30,
            current_price=14500000.0,
        )
        individual_signals = {
            "ATRBased": {"action": "buy", "confidence": 0.50},
        }

        result = trading_cycle_manager._integrate_ml_with_strategy(
            ml_prediction,
            strategy_signal,
            individual_strategy_signals=individual_signals,
        )

        assert result.action == "hold"
        assert result.metadata.get("ml_recovery") is not True

    @patch("src.core.services.trading_cycle_manager.get_threshold")
    def test_recovery_not_triggered_no_agreeing_strategy(
        self, mock_get_threshold, trading_cycle_manager
    ):
        """個別戦略が同方向なし → Recovery不発動"""
        mock_get_threshold.side_effect = self._make_threshold_side_effect()

        ml_prediction = {"prediction": 2, "confidence": 0.70}  # BUY
        strategy_signal = StrategySignal(
            strategy_name="weighted_vote",
            timestamp=datetime.now(),
            action="hold",
            confidence=0.30,
            strength=0.30,
            current_price=14500000.0,
        )
        individual_signals = {
            "ATRBased": {"action": "hold", "confidence": 0.50},
            "BBReversal": {"action": "sell", "confidence": 0.40},
        }

        result = trading_cycle_manager._integrate_ml_with_strategy(
            ml_prediction,
            strategy_signal,
            individual_strategy_signals=individual_signals,
        )

        assert result.action == "hold"
        assert result.metadata.get("ml_recovery") is not True

    @patch("src.core.services.trading_cycle_manager.get_threshold")
    def test_recovery_not_triggered_strategy_low_confidence(
        self, mock_get_threshold, trading_cycle_manager
    ):
        """同方向戦略あるが信頼度不足（0.25 < 0.30） → Recovery不発動"""
        mock_get_threshold.side_effect = self._make_threshold_side_effect()

        ml_prediction = {"prediction": 2, "confidence": 0.70}  # BUY
        strategy_signal = StrategySignal(
            strategy_name="weighted_vote",
            timestamp=datetime.now(),
            action="hold",
            confidence=0.30,
            strength=0.30,
            current_price=14500000.0,
        )
        individual_signals = {
            "ATRBased": {"action": "buy", "confidence": 0.25},  # 0.25 < 0.30
        }

        result = trading_cycle_manager._integrate_ml_with_strategy(
            ml_prediction,
            strategy_signal,
            individual_strategy_signals=individual_signals,
        )

        assert result.action == "hold"
        assert result.metadata.get("ml_recovery") is not True

    @patch("src.core.services.trading_cycle_manager.get_threshold")
    def test_recovery_disabled(self, mock_get_threshold, trading_cycle_manager):
        """Recovery無効時 → Recovery不発動"""
        mock_get_threshold.side_effect = self._make_threshold_side_effect(recovery_enabled=False)

        ml_prediction = {"prediction": 2, "confidence": 0.70}  # BUY
        strategy_signal = StrategySignal(
            strategy_name="weighted_vote",
            timestamp=datetime.now(),
            action="hold",
            confidence=0.30,
            strength=0.30,
            current_price=14500000.0,
        )
        individual_signals = {
            "ATRBased": {"action": "buy", "confidence": 0.50},
        }

        result = trading_cycle_manager._integrate_ml_with_strategy(
            ml_prediction,
            strategy_signal,
            individual_strategy_signals=individual_signals,
        )

        assert result.action == "hold"
        assert result.metadata.get("ml_recovery") is not True

    @patch("src.core.services.trading_cycle_manager.get_threshold")
    def test_recovery_confidence_cap(self, mock_get_threshold, trading_cycle_manager):
        """回復信頼度がcapを超えない"""
        mock_get_threshold.side_effect = self._make_threshold_side_effect(
            recovery_overrides={"recovery_confidence_cap": 0.20}
        )

        ml_prediction = {"prediction": 2, "confidence": 0.90}  # BUY high
        strategy_signal = StrategySignal(
            strategy_name="weighted_vote",
            timestamp=datetime.now(),
            action="hold",
            confidence=0.30,
            strength=0.30,
            current_price=14500000.0,
        )
        individual_signals = {
            "ATRBased": {"action": "buy", "confidence": 0.80},
        }

        result = trading_cycle_manager._integrate_ml_with_strategy(
            ml_prediction,
            strategy_signal,
            individual_strategy_signals=individual_signals,
        )

        assert result.action == "buy"
        assert result.metadata["ml_recovery"] is True
        # 0.90 * 0.80 = 0.72 → cap 0.20
        assert result.confidence == 0.20

    @patch("src.core.services.trading_cycle_manager.get_threshold")
    def test_recovery_picks_highest_confidence_strategy(
        self, mock_get_threshold, trading_cycle_manager
    ):
        """複数の同方向戦略 → 最高信頼度を選択"""
        mock_get_threshold.side_effect = self._make_threshold_side_effect()

        ml_prediction = {"prediction": 2, "confidence": 0.65}  # BUY
        strategy_signal = StrategySignal(
            strategy_name="weighted_vote",
            timestamp=datetime.now(),
            action="hold",
            confidence=0.30,
            strength=0.30,
            current_price=14500000.0,
        )
        individual_signals = {
            "ATRBased": {"action": "buy", "confidence": 0.35},
            "StochasticDivergence": {"action": "buy", "confidence": 0.50},
            "BBReversal": {"action": "hold", "confidence": 0.40},
        }

        result = trading_cycle_manager._integrate_ml_with_strategy(
            ml_prediction,
            strategy_signal,
            individual_strategy_signals=individual_signals,
        )

        assert result.action == "buy"
        assert result.metadata["ml_recovery"] is True
        assert result.metadata["recovery_strategy"] == "StochasticDivergence"
        assert result.metadata["recovery_strategy_confidence"] == 0.50

    @patch("src.core.services.trading_cycle_manager.get_threshold")
    def test_recovery_not_triggered_when_strategy_not_hold(
        self, mock_get_threshold, trading_cycle_manager
    ):
        """戦略がHOLDでない場合 → Recovery不発動（通常フロー）"""
        mock_get_threshold.side_effect = self._make_threshold_side_effect()

        ml_prediction = {"prediction": 2, "confidence": 0.70}  # BUY
        strategy_signal = StrategySignal(
            strategy_name="weighted_vote",
            timestamp=datetime.now(),
            action="buy",  # 既にBUY
            confidence=0.50,
            strength=0.50,
            current_price=14500000.0,
        )
        individual_signals = {
            "ATRBased": {"action": "buy", "confidence": 0.50},
        }

        result = trading_cycle_manager._integrate_ml_with_strategy(
            ml_prediction,
            strategy_signal,
            individual_strategy_signals=individual_signals,
        )

        # 通常のML統合フロー（Recoveryではない）
        assert result.action == "buy"
        assert result.metadata.get("ml_recovery") is not True
        assert result.metadata["ml_adjusted"] is True

    @patch("src.core.services.trading_cycle_manager.get_threshold")
    def test_recovery_no_individual_signals(self, mock_get_threshold, trading_cycle_manager):
        """individual_strategy_signals=None → Recovery不発動"""
        mock_get_threshold.side_effect = self._make_threshold_side_effect()

        ml_prediction = {"prediction": 2, "confidence": 0.70}  # BUY
        strategy_signal = StrategySignal(
            strategy_name="weighted_vote",
            timestamp=datetime.now(),
            action="hold",
            confidence=0.30,
            strength=0.30,
            current_price=14500000.0,
        )

        result = trading_cycle_manager._integrate_ml_with_strategy(
            ml_prediction,
            strategy_signal,
            individual_strategy_signals=None,
        )

        assert result.action == "hold"
        assert result.metadata.get("ml_recovery") is not True
