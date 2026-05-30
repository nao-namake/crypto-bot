"""Phase 90δ/90ε/90ζ: ライブ分析スクリプトの追従テスト。

直近修正に対し standard_analysis.py の GCPログ grep が正しい文字列を使うことを検証:
- Phase 90δ: post_only指定だが実Taker約定 WARNING の監視
- Phase 90ε: 土日TP一律500円（土日一律縮小）の監視
- Phase 90ζ: 固定金額SL適用ログ（Phase 86・WARNING昇格）と (土日縮小→N円) の監視
- 特徴量システム grep が 37→55 へ追従していること（旧 "37特徴量" 空振り修正）
"""

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

_module_path = (
    Path(__file__).parent.parent.parent.parent / "scripts" / "live" / "standard_analysis.py"
)
_spec = importlib.util.spec_from_file_location("standard_analysis_p90wk_module", _module_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

BotFunctionChecker = _mod.BotFunctionChecker


def _capture_queries(method_name):
    """指定メソッドを呼び、_count_logs に渡された全クエリ文字列を返す。"""
    checker = BotFunctionChecker(MagicMock(), MagicMock())
    checker._count_logs = MagicMock(return_value=0)
    getattr(checker, method_name)()
    return [c.args[0] for c in checker._count_logs.call_args_list]


class TestPhase90DeltaTakerConflict:
    """Phase 90δ: post_only指定だが実Taker約定の監視クエリ。"""

    def test_maker_strategy_monitors_taker_conflict(self):
        queries = _capture_queries("_check_maker_strategy")
        assert any("Phase 90δ: post_only指定だがTaker約定" in q for q in queries)


class TestPhase90EpsilonZetaWeekend:
    """Phase 90ε/90ζ: 土日TP/SL縮小の監視クエリ。"""

    def test_weekend_tp_label_monitored(self):
        queries = _capture_queries("_check_phase90_weekend_tpsl")
        assert any("土日一律縮小" in q for q in queries)

    def test_weekend_sl_label_monitored(self):
        queries = _capture_queries("_check_phase90_weekend_tpsl")
        assert any("土日縮小" in q for q in queries)

    def test_fixed_sl_applied_uses_phase86_string(self):
        queries = _capture_queries("_check_phase90_weekend_tpsl")
        # 現行コードが出すのは "Phase 86: 固定金額SL適用"（旧 "Phase 70.2" は空振り）
        assert any("Phase 86: 固定金額SL適用" in q for q in queries)


class TestFeatureSystem37To55:
    """特徴量システム grep が 37→55 拡張に追従していること。"""

    def test_feature_grep_targets_55_not_37(self):
        queries = _capture_queries("_check_feature_system")
        assert any("55特徴量" in q for q in queries)
        # 旧 "37特徴量" 空振りクエリが残っていないこと
        assert not any("37特徴量" in q for q in queries)
