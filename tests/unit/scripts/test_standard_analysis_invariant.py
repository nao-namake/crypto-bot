"""Phase 90ο Stage 3 + Phase 90π R1: standard_analysis _check_phase90o_invariants のテスト

invariant 違反を種別分類し、Phase 90π R1 reconcile の稼働状況と突合して判定することを検証:
- 「建玉合計 > 上限」= 真のサイズ膨張 → CRITICAL 維持
- 「VP↔実ポジ乖離」= VP キャッシュ揮発。reconcile[LIVE] 稼働中なら WARNING 降格、未稼働なら CRITICAL
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


def _fake_counts(size=0, vp=0, live=0, sl_place=0, market_close=0):
    """クエリ内容で値を返す _count_logs スタブを作る。"""

    def _count(query, limit=50):
        if "建玉合計" in query:
            return size
        if "VP↔実ポジ乖離" in query:
            return vp
        if "reconcile[LIVE]" in query:
            return live
        if "SL配置" in query:
            return sl_place
        if "成行決済" in query:
            return market_close
        return 0

    return _count


class TestPhase90OmicronInvariantDetection:
    """_check_phase90o_invariants の種別分類・reconcile 突合判定"""

    def test_vp_drift_with_reconcile_is_warning_not_critical(self):
        """VP↔実ポジ乖離 + reconcile[LIVE] 稼働 → WARNING（致命的にしない）"""
        checker = _make_checker()
        checker._count_logs = MagicMock(side_effect=_fake_counts(vp=3, live=288, sl_place=2))
        before_crit = checker.result.critical_issues
        before_warn = checker.result.warning_issues
        checker._check_phase90o_invariants()
        assert checker.result.invariant_vp_drift_count == 3
        assert checker.result.invariant_violation_count == 3
        assert checker.result.critical_issues == before_crit  # 致命的に上げない
        assert checker.result.warning_issues == before_warn + 1
        assert checker.result.reconcile_live_count == 288

    def test_vp_drift_without_reconcile_is_critical(self):
        """VP↔実ポジ乖離 + reconcile 未稼働 → CRITICAL（R1 が効いていない真の異常）"""
        checker = _make_checker()
        checker._count_logs = MagicMock(side_effect=_fake_counts(vp=3, live=0))
        before = checker.result.critical_issues
        checker._check_phase90o_invariants()
        assert checker.result.critical_issues == before + 1

    def test_size_inflation_is_critical_even_with_reconcile(self):
        """建玉サイズ膨張 → reconcile 稼働でも CRITICAL（6/15 ドカン型）"""
        checker = _make_checker()
        checker._count_logs = MagicMock(side_effect=_fake_counts(size=1, live=288))
        before = checker.result.critical_issues
        checker._check_phase90o_invariants()
        assert checker.result.invariant_size_violation_count == 1
        assert checker.result.critical_issues == before + 1

    def test_size_inflation_and_vp_drift_combined(self):
        """膨張(CRITICAL) と VP乖離(WARNING) が同時に出ても両方計上される"""
        checker = _make_checker()
        checker._count_logs = MagicMock(side_effect=_fake_counts(size=1, vp=2, live=288))
        before_crit = checker.result.critical_issues
        before_warn = checker.result.warning_issues
        checker._check_phase90o_invariants()
        assert checker.result.invariant_violation_count == 3
        assert checker.result.critical_issues == before_crit + 1  # 膨張のみ
        assert checker.result.warning_issues == before_warn + 1  # VP乖離のみ

    def test_no_violation_is_normal(self):
        checker = _make_checker()
        checker._count_logs = MagicMock(side_effect=_fake_counts(live=288))
        before = checker.result.normal_checks
        checker._check_phase90o_invariants()
        assert checker.result.invariant_violation_count == 0
        assert checker.result.critical_issues == 0
        assert checker.result.normal_checks == before + 1

    def test_reconcile_action_count_aggregated(self):
        """reconcile の SL配置 + 成行決済 が action_count に集計される"""
        checker = _make_checker()
        checker._count_logs = MagicMock(
            side_effect=_fake_counts(live=288, sl_place=2, market_close=2)
        )
        checker._check_phase90o_invariants()
        assert checker.result.reconcile_action_count == 4

    def test_query_classifies_by_type(self):
        """種別分類クエリ（建玉合計 / VP↔実ポジ乖離）が発行される"""
        checker = _make_checker()
        checker._count_logs = MagicMock(side_effect=_fake_counts())
        checker._check_phase90o_invariants()
        queries = [c.args[0] for c in checker._count_logs.call_args_list]
        assert any("建玉合計" in q for q in queries)
        assert any("VP↔実ポジ乖離" in q for q in queries)
        assert any("reconcile[LIVE]" in q for q in queries)
