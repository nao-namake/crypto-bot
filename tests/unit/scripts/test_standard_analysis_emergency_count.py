"""Phase 90δ: 緊急成行決済カウントの誤カウント修正テスト。

旧クエリ 'textPayload:"緊急成行決済"' は DRY_RUN ログ
（🧪 Phase 87 C1 [DRY_RUN]: 緊急成行決済シミュレーション ... 実発注なし）に
部分一致し、実発注ゼロでも件数が立っていた。実発注を伴う成功ログのみを数える
クエリに変更したことを検証する。
"""

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

_module_path = (
    Path(__file__).parent.parent.parent.parent / "scripts" / "live" / "standard_analysis.py"
)
_spec = importlib.util.spec_from_file_location("standard_analysis_emc_module", _module_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

BotFunctionChecker = _mod.BotFunctionChecker


class TestPhase90DeltaEmergencyCloseCount:
    """緊急成行決済カウントが DRY_RUN を除外し実発注成功のみ数える。"""

    def _emergency_queries(self):
        # _check_tp_sl_management は BotFunctionChecker のメソッド。
        # logger / infra_checker は当該メソッドでは未使用のため MagicMock で可。
        checker = BotFunctionChecker(MagicMock(), MagicMock())
        checker._count_logs = MagicMock(return_value=0)
        checker._check_tp_sl_management()
        return [
            c.args[0] for c in checker._count_logs.call_args_list if "緊急成行決済" in c.args[0]
        ]

    def test_only_one_emergency_query(self):
        # 緊急成行決済を数えるクエリは1本に限定される
        assert len(self._emergency_queries()) == 1

    def test_query_counts_success_only(self):
        q = self._emergency_queries()[0]
        assert "Phase 87 C1: 緊急成行決済成功" in q
        assert "Phase 86: 緊急成行決済成功" in q

    def test_query_excludes_dry_run_terms(self):
        q = self._emergency_queries()[0]
        # DRY_RUN シミュレーションを拾う部分一致語を含まない
        assert "シミュレーション" not in q
        assert "実発注なし" not in q
        # 旧来の無条件マッチ（SL超過検出）も含まない
        assert "SL超過検出" not in q
