"""Phase 90ο Stage 3: standard_analysis _check_phase90o_invariants のテスト

tp_sl_manager が出す invariant 違反 CRITICAL ログをライブ分析が集計し、
状態管理のズレ（VP↔実ポジ乖離・建玉サイズ膨張）を critical として可視化することを検証。
"""

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

_module_path = (
    Path(__file__).parent.parent.parent.parent / "scripts" / "live" / "standard_analysis.py"
)
_spec = importlib.util.spec_from_file_location("standard_analysis_inv_module", _module_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

BotFunctionChecker = _mod.BotFunctionChecker


def _make_checker():
    return BotFunctionChecker(MagicMock(), MagicMock())


class TestPhase90OmicronInvariantDetection:
    """_check_phase90o_invariants の集計・判定"""

    def test_violation_detected_is_critical(self):
        checker = _make_checker()
        checker._count_logs = MagicMock(return_value=2)
        before = checker.result.critical_issues
        checker._check_phase90o_invariants()
        assert checker.result.invariant_violation_count == 2
        assert checker.result.critical_issues == before + 1

    def test_no_violation_is_normal(self):
        checker = _make_checker()
        checker._count_logs = MagicMock(return_value=0)
        before = checker.result.normal_checks
        checker._check_phase90o_invariants()
        assert checker.result.invariant_violation_count == 0
        assert checker.result.critical_issues == 0
        assert checker.result.normal_checks == before + 1

    def test_query_targets_invariant_log(self):
        checker = _make_checker()
        checker._count_logs = MagicMock(return_value=0)
        checker._check_phase90o_invariants()
        q = checker._count_logs.call_args_list[0].args[0]
        assert "Phase 90ο invariant違反" in q
