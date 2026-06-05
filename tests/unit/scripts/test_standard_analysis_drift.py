"""Phase 90μ: ライブ分析の Phase 89-β drift 解釈テスト。

従来は drift_detected >= 20 で即 warning（「Bonferroni 補正薄い可能性」）を上げていたが、
実ログ上 drift 検出は strategy_signal_*（相場局面で当然変動する戦略シグナル）主体で、
Auto Retraining が発火していなければ実害はない。判定を retrain_triggered で分岐し、
検出が多くても再学習0回なら正常扱い、再学習が実発火して初めて過剰検知を疑うことを検証する。
"""

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

_module_path = (
    Path(__file__).parent.parent.parent.parent / "scripts" / "live" / "standard_analysis.py"
)
_spec = importlib.util.spec_from_file_location("standard_analysis_drift_module", _module_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

BotFunctionChecker = _mod.BotFunctionChecker

GCP = "src.analysis.common.gcp_metrics"


class TestPhase89DriftInterpretation:
    """drift 検出数と retrain_triggered による判定分岐の検証。"""

    def _run(self, drift_detected, retrain_triggered):
        """drift 以外のメトリクスは warning を出さない無害値でモックして実行。"""
        checker = BotFunctionChecker(MagicMock(), MagicMock())
        checker.infra_checker.result.phase89_metrics = {}
        drift_metric = {
            "drift_detected": drift_detected,
            "drift_suppressed_by_bonferroni": 0,
            "drift_resolved": 0,
            "retrain_triggered": retrain_triggered,
            "retrain_cooldown_skipped": 0,
            "state_restored_on_restart": 0,
            "verdict": "OK",
        }
        with (
            patch(f"{GCP}.count_phase89_drift_events", return_value=drift_metric),
            patch(
                f"{GCP}.count_phase89_gating_stats",
                return_value={"total_triggers": 0, "skip_percentage": 0.0},
            ),
            patch(
                f"{GCP}.count_phase89_nbeats_health",
                return_value={
                    "sl_placeholder_detected": 0,
                    "warning_external_api_client_missing": 0,
                },
            ),
            patch(
                f"{GCP}.count_phase89_websocket_status",
                return_value={
                    "trigger_mode_skipped": True,
                    "verdict": "SKIPPED",
                    "websocket_start_success": 0,
                    "websocket_start_failure": 0,
                },
            ),
            patch(
                f"{GCP}.count_phase89_kelly_safety",
                return_value={"fractional_kelly_active": 0},
            ),
        ):
            checker._check_phase89_features()
        return checker

    def test_high_drift_no_retrain_is_normal(self):
        """検出多数でも再学習0回なら warning を立てず正常扱い（実害なし）。"""
        checker = self._run(drift_detected=39, retrain_triggered=0)
        assert checker.result.warning_issues == 0

    def test_high_drift_with_retrain_warns(self):
        """検出多数 かつ 再学習が実発火していれば過剰検知として warning。"""
        checker = self._run(drift_detected=39, retrain_triggered=2)
        assert checker.result.warning_issues == 1

    def test_low_drift_is_normal(self):
        """検出が閾値未満なら従来どおり正常扱い。"""
        checker = self._run(drift_detected=5, retrain_triggered=0)
        assert checker.result.warning_issues == 0
