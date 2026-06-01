"""Phase 90θ: ライブ分析の SLMonitor 誤発火監視テスト。

従来 emergency_market_close は実発注成功ログのみカウントするため、DRY_RUN での
緊急決済誤発火（canceled_unfilled 中間状態の誤判定）を検出できない盲点があった。
_check_tp_sl_management が DRY_RUN 発火と pending 抑止を計測し、誤発火時に
warning_issues を加点することを検証する。
"""

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

_module_path = (
    Path(__file__).parent.parent.parent.parent / "scripts" / "live" / "standard_analysis.py"
)
_spec = importlib.util.spec_from_file_location("standard_analysis_slfire_module", _module_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

BotFunctionChecker = _mod.BotFunctionChecker


class TestPhase90ThetaSLMonitorFire:
    """SLMonitor DRY_RUN 誤発火監視カウンタの検証。"""

    def _run(self, count_return=0):
        checker = BotFunctionChecker(MagicMock(), MagicMock())
        checker._count_logs = MagicMock(return_value=count_return)
        checker._check_tp_sl_management()
        return checker

    def _queries(self, checker):
        return [c.args[0] for c in checker._count_logs.call_args_list]

    def test_dry_run_query_issued(self):
        """DRY_RUN 緊急決済シミュレーションを拾うクエリが発行される。"""
        checker = self._run()
        assert any("🧪 Phase 87 C1 [DRY_RUN]" in q for q in self._queries(checker))

    def test_pending_query_issued(self):
        """canceled_unfilled 抑止（pending）を拾うクエリが発行される。"""
        checker = self._run()
        assert any("canceled_unfilled_pending" in q for q in self._queries(checker))

    def test_warning_added_when_dry_run_fire_detected(self):
        """誤発火が検出されたら warning_issues に加点される。"""
        checker = self._run(count_return=2)
        assert checker.result.sl_monitor_dry_run_fire_count == 2
        assert checker.result.warning_issues >= 1

    def test_no_warning_when_no_dry_run_fire(self):
        """誤発火ゼロなら normal_checks に加点（warning なし）。"""
        checker = self._run(count_return=0)
        assert checker.result.sl_monitor_dry_run_fire_count == 0
        assert checker.result.warning_issues == 0
