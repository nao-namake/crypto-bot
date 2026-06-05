"""Phase 90θ/μ: ライブ分析の SLMonitor 誤発火監視テスト（reason別分類）。

従来は DRY_RUN緊急決済の発火を一律「誤発火」とカウントしていたが、
canceled_unfilled は 3/3連続検出を経た正当な昇格（同サイクルで Phase 64.12 が
実決済も担保）＝設計どおりで誤発火ではない。fetch_error_persistent 等のみが
真の誤発火（Phase 90μ 修正対象の Fire #2）。

_check_tp_sl_management が reason別にカウントし、真の誤発火がある場合のみ
warning_issues を加点し、canceled_unfilled のみなら正常扱いとすることを検証する。
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


class TestPhase90MuSLMonitorFire:
    """SLMonitor DRY_RUN 誤発火の reason別分類カウンタの検証。"""

    def _run(self, total_fire=0, canceled_unfilled=0, pending=0):
        """_count_logs を reason別に応答させて _check_tp_sl_management を実行。"""
        checker = BotFunctionChecker(MagicMock(), MagicMock())

        def fake_count(query, limit=50):
            # canceled_unfilled は DRY_RUN クエリも内包する（AND）ため先に判定
            if "reason=c5_canceled_unfilled" in query:
                return canceled_unfilled
            if "🧪 Phase 87 C1 [DRY_RUN]" in query:
                return total_fire
            if "canceled_unfilled_pending" in query:
                return pending
            return 0

        checker._count_logs = MagicMock(side_effect=fake_count)
        checker._check_tp_sl_management()
        return checker

    def _queries(self, checker):
        return [c.args[0] for c in checker._count_logs.call_args_list]

    def test_dry_run_query_issued(self):
        """DRY_RUN 緊急決済シミュレーション全件を拾うクエリが発行される。"""
        checker = self._run()
        assert any("🧪 Phase 87 C1 [DRY_RUN]" in q for q in self._queries(checker))

    def test_reason_split_query_issued(self):
        """reason=c5_canceled_unfilled を分離するクエリが発行される。"""
        checker = self._run()
        assert any("reason=c5_canceled_unfilled" in q for q in self._queries(checker))

    def test_pending_query_issued(self):
        """canceled_unfilled 抑止（pending）を拾うクエリが発行される。"""
        checker = self._run()
        assert any("canceled_unfilled_pending" in q for q in self._queries(checker))

    def test_true_fire_warns(self):
        """真の誤発火（canceled_unfilled以外）があれば warning_issues に加点。"""
        # 全2件のうち canceled_unfilled 1件 → 真の誤発火 1件
        checker = self._run(total_fire=2, canceled_unfilled=1)
        assert checker.result.sl_monitor_dry_run_fire_count == 2
        assert checker.result.sl_monitor_fire_canceled_unfilled == 1
        assert checker.result.sl_monitor_fire_true == 1
        assert checker.result.warning_issues >= 1

    def test_canceled_unfilled_only_no_warning(self):
        """canceled_unfilled のみ（設計どおり昇格）なら warning を立てず正常扱い。"""
        checker = self._run(total_fire=2, canceled_unfilled=2)
        assert checker.result.sl_monitor_fire_true == 0
        assert checker.result.sl_monitor_fire_canceled_unfilled == 2
        assert checker.result.warning_issues == 0

    def test_no_fire_no_warning(self):
        """発火ゼロなら normal_checks に加点（warning なし）。"""
        checker = self._run(total_fire=0, canceled_unfilled=0)
        assert checker.result.sl_monitor_dry_run_fire_count == 0
        assert checker.result.sl_monitor_fire_true == 0
        assert checker.result.warning_issues == 0
