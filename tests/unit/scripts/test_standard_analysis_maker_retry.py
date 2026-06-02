"""Phase 90κ: ライブ分析の Makerリトライ実動検知テスト。

per_attempt分割修正でリトライが実際に回るようになったかを観測するため、
_check_maker_strategy が「Maker注文試行」総数と試行2回目以降のクエリを発行することを検証。
"""

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

_module_path = (
    Path(__file__).parent.parent.parent.parent / "scripts" / "live" / "standard_analysis.py"
)
_spec = importlib.util.spec_from_file_location("standard_analysis_maker_retry", _module_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

BotFunctionChecker = _mod.BotFunctionChecker


class TestPhase90KappaMakerRetryDetection:
    def _queries(self):
        checker = BotFunctionChecker(MagicMock(), MagicMock())
        checker._count_logs = MagicMock(return_value=0)
        checker._check_maker_strategy()
        return [c.args[0] for c in checker._count_logs.call_args_list]

    def test_maker_trial_total_query_exists(self):
        """「Maker注文試行」総数を数えるクエリが発行される。"""
        qs = self._queries()
        assert any("Maker注文試行" in q and "試行 2/" not in q for q in qs)

    def test_maker_retry_query_counts_attempt_2_and_beyond(self):
        """リトライ(試行2回目以降)を数えるクエリが試行2/3/4/5を含む。"""
        qs = self._queries()
        retry_qs = [q for q in qs if "Maker注文試行 2/" in q]
        assert len(retry_qs) >= 1
        q = retry_qs[0]
        assert "Maker注文試行 3/" in q
        assert "Maker注文試行 4/" in q

    def test_fields_default_zero(self):
        """新フィールドが定義されデフォルト0。"""
        checker = BotFunctionChecker(MagicMock(), MagicMock())
        assert checker.result.maker_trial_total == 0
        assert checker.result.maker_retry_actual == 0
