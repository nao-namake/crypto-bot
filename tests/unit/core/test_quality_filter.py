"""
Phase 84: ML品質フィルタの「失敗高確信閾値」yaml化テスト

trading_cycle_manager.py の _apply_quality_filter で、
旧ハードコード0.55を yaml参照に変更したことの動作確認。
"""

from unittest.mock import MagicMock, patch

from src.core.services.trading_cycle_manager import TradingCycleManager
from src.strategies.base.strategy_base import StrategySignal


def _make_signal(action="buy", confidence=0.7):
    """テスト用 StrategySignal 生成"""
    return StrategySignal(
        strategy_name="TestStrategy",
        timestamp=None,
        action=action,
        confidence=confidence,
        strength=0.5,
        current_price=12500000.0,
        entry_price=12500000.0,
    )


def _make_manager():
    """TradingCycleManager のテスト用インスタンス（依存最小限）"""
    orchestrator = MagicMock()
    logger = MagicMock()
    return TradingCycleManager(orchestrator, logger)


class TestPhase84QualityFilter:
    """Phase 84: 失敗高確信閾値 yaml化"""

    @patch("src.core.orchestration.quality_filter.get_threshold")
    def test_default_threshold_is_065(self, mock_get):
        """デフォルト値は 0.65（旧0.55から緩和）"""
        thresholds = {
            "ml.quality_filter.accept_threshold": 0.58,
            "ml.quality_filter.reject_threshold": 0.42,
            "ml.quality_filter.uncertain_penalty": 0.5,
            "ml.quality_filter.high_confidence_failure_threshold": 0.65,
        }
        mock_get.side_effect = lambda key, default=None: thresholds.get(key, default)

        manager = _make_manager()
        signal = _make_signal(action="sell", confidence=0.7)

        # 失敗確率 0.60 (= 65% 未満) → 通過するはず
        ml_prediction = {"prediction": 0, "confidence": 0.60}
        result = manager._apply_quality_filter(ml_prediction, signal)
        # 失敗確率0.60 < 0.65 → 拒否されない（accept条件も成立しないので中間帯処理される）
        # → action は "sell" のまま（hold変換されない）
        assert (
            result.action != "hold"
        ), f"失敗確率0.60 (旧閾値0.55では拒否、新閾値0.65では通過) で hold 変換された: {result.action}"

    @patch("src.core.orchestration.quality_filter.get_threshold")
    def test_high_failure_confidence_still_rejected(self, mock_get):
        """失敗確率 0.65以上は引き続き拒否（過剰防衛は維持）"""
        thresholds = {
            "ml.quality_filter.accept_threshold": 0.58,
            "ml.quality_filter.reject_threshold": 0.42,
            "ml.quality_filter.uncertain_penalty": 0.5,
            "ml.quality_filter.high_confidence_failure_threshold": 0.65,
        }
        mock_get.side_effect = lambda key, default=None: thresholds.get(key, default)

        manager = _make_manager()
        signal = _make_signal(action="sell", confidence=0.7)

        # 失敗確率 0.808 (>= 0.65) → 確信失敗として拒否
        ml_prediction = {"prediction": 0, "confidence": 0.808}
        result = manager._apply_quality_filter(ml_prediction, signal)
        assert (
            result.action == "hold"
        ), f"失敗確率0.808 (新閾値0.65以上) は拒否されるはず: {result.action}"

    @patch("src.core.orchestration.quality_filter.get_threshold")
    def test_yaml_override_threshold(self, mock_get):
        """yaml で 0.50 等にオーバーライド可能（より厳しく）"""
        thresholds = {
            "ml.quality_filter.accept_threshold": 0.58,
            "ml.quality_filter.reject_threshold": 0.42,
            "ml.quality_filter.uncertain_penalty": 0.5,
            "ml.quality_filter.high_confidence_failure_threshold": 0.50,
        }
        mock_get.side_effect = lambda key, default=None: thresholds.get(key, default)

        manager = _make_manager()
        signal = _make_signal(action="sell", confidence=0.7)

        # 失敗確率 0.55 (>= yaml の 0.50) → 拒否
        ml_prediction = {"prediction": 0, "confidence": 0.55}
        result = manager._apply_quality_filter(ml_prediction, signal)
        assert (
            result.action == "hold"
        ), f"yaml 0.50 設定で失敗確率0.55 は拒否されるはず: {result.action}"

    @patch("src.core.orchestration.quality_filter.get_threshold")
    def test_legacy_055_threshold_passes_058(self, mock_get):
        """旧ハードコード0.55の挙動: 失敗確率0.58 は拒否されていた（新閾値0.65なら通過）"""
        # まず旧挙動を再現（high_conf_failure=0.55）
        thresholds = {
            "ml.quality_filter.accept_threshold": 0.58,
            "ml.quality_filter.reject_threshold": 0.42,
            "ml.quality_filter.uncertain_penalty": 0.5,
            "ml.quality_filter.high_confidence_failure_threshold": 0.55,
        }
        mock_get.side_effect = lambda key, default=None: thresholds.get(key, default)

        manager = _make_manager()
        signal = _make_signal(action="sell", confidence=0.7)

        # 失敗確率 0.58 (>= 0.55 旧閾値) → 拒否
        ml_prediction = {"prediction": 0, "confidence": 0.58}
        result = manager._apply_quality_filter(ml_prediction, signal)
        assert result.action == "hold", "旧閾値0.55では失敗確率0.58で拒否される"

        # 新閾値0.65に変更すると、同じ0.58は通過
        thresholds["ml.quality_filter.high_confidence_failure_threshold"] = 0.65
        result_new = manager._apply_quality_filter(ml_prediction, signal)
        assert result_new.action != "hold", "新閾値0.65では失敗確率0.58は通過するはず（中間帯処理）"
