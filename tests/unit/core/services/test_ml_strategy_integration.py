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

        ml_prediction = {"prediction": 1, "confidence": 0.9}  # buy, 高信頼度
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

        ml_prediction = {"prediction": -1, "confidence": 0.9}  # sell, 高信頼度
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

        ml_prediction = {"prediction": -1, "confidence": 0.9}  # sell, 高信頼度
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

        # -1: sell
        ml_sell = {"prediction": -1, "confidence": 0.7}
        result_sell = trading_cycle_manager._integrate_ml_with_strategy(ml_sell, strategy_signal)
        assert result_sell.metadata["ml_action"] == "sell"

        # 0: hold
        ml_hold = {"prediction": 0, "confidence": 0.7}
        result_hold = trading_cycle_manager._integrate_ml_with_strategy(ml_hold, strategy_signal)
        assert result_hold.metadata["ml_action"] == "hold"

        # 1: buy
        ml_buy = {"prediction": 1, "confidence": 0.7}
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
