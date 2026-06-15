"""Phase 90ξ: ML予測 / Silent Failure 検出の本番WARNING環境対応テスト。

本番は LOG_LEVEL=WARNING のため、ML予測 (🤖 ML予測実行開始: ProductionEnsemble・INFO) /
統合シグナル生成 (strategy_manager.py:104・INFO) / Atomic Entry完了 (executor.py:705・INFO)
が抑制され、対応する grep が構造的に 0 件になる（7日間 0 件を実機確認）。
旧実装は ml_prediction_count==0 を無条件 CRITICAL、signal_count==0 を warning、
signal>0 & order==0 を CRITICAL+=3 と誤判定していた。

WARNING で出力される代替ログ（gating 通過 → フル取引サイクル開始 / 固定金額TP適用 /
TP Maker配置成功 / 取引拒否系）を併用して誤検知を解消したことを検証する。
"""

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

_module_path = (
    Path(__file__).parent.parent.parent.parent / "scripts" / "live" / "standard_analysis.py"
)
_spec = importlib.util.spec_from_file_location("standard_analysis_xi_module", _module_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

BotFunctionChecker = _mod.BotFunctionChecker


def _make_checker():
    # logger / infra_checker は対象メソッドでは未使用のため MagicMock で可。
    return BotFunctionChecker(MagicMock(), MagicMock())


class TestPhase90XiMLPredictionSurvival:
    """ML予測チェックが WARNING 代替ログを併用し偽 CRITICAL を出さない。"""

    def test_query_includes_warning_survival_signals(self):
        checker = _make_checker()
        checker._count_logs = MagicMock(return_value=0)
        checker._check_ml_prediction()
        q = checker._count_logs.call_args_list[0].args[0]
        # 旧 INFO パターンは残しつつ WARNING 生存シグナルを併用する
        assert "ProductionEnsemble" in q
        assert "フル取引サイクル開始" in q
        assert "固定金額TP適用" in q

    def test_no_false_critical_when_only_warning_logs(self):
        # 本番ケース: ML予測(INFO)=0 でも フルサイクル/TP適用(WARNING)>0 → 正常
        checker = _make_checker()
        checker._count_logs = MagicMock(return_value=5)
        before = checker.result.critical_issues
        checker._check_ml_prediction()
        assert checker.result.critical_issues == before
        assert checker.result.normal_checks >= 1

    def test_critical_when_truly_no_ml_activity(self):
        # ML予測も フルサイクルも TP適用も 0 = 真に稼働していない → CRITICAL 維持
        checker = _make_checker()
        checker._count_logs = MagicMock(return_value=0)
        before = checker.result.critical_issues
        checker._check_ml_prediction()
        assert checker.result.critical_issues == before + 1


class TestPhase90XiSilentFailure:
    """Silent Failure 検出が本番 WARNING 環境で正しく動作する。"""

    @staticmethod
    def _fake_count(signal, order, resolved):
        """クエリ内容で signal/order/resolved を一意に振り分ける side_effect。"""

        def _inner(query, limit=10):
            if "フル取引サイクル開始" in query:
                return signal
            if "TP Maker配置成功" in query:
                return order
            if "取引拒否" in query:
                return resolved
            return 0

        return _inner

    def test_queries_include_warning_alternatives(self):
        checker = _make_checker()
        checker._count_logs = MagicMock(return_value=0)
        checker._detect_silent_failure()
        queries = [c.args[0] for c in checker._count_logs.call_args_list]
        # signal: フルサイクル / order: TP Maker配置 / resolved: 拒否系
        assert any("フル取引サイクル開始" in q for q in queries)
        assert any("TP Maker配置成功" in q for q in queries)
        assert any("取引拒否" in q for q in queries)
        assert any("品質フィルタ拒否" in q for q in queries)

    def test_signals_rejected_is_normal_not_critical(self):
        # 本番の典型: フルサイクル多数・実行0・全件拒否 → 正常（偽 CRITICAL 回避）
        checker = _make_checker()
        checker._count_logs = MagicMock(side_effect=self._fake_count(96, 0, 97))
        before_c = checker.result.critical_issues
        before_n = checker.result.normal_checks
        checker._detect_silent_failure()
        assert checker.result.critical_issues == before_c
        assert checker.result.normal_checks == before_n + 1
        assert checker.result.cycle_resolved_count == 97

    def test_true_silent_failure_is_critical(self):
        # シグナル評価に入ったのに実行も拒否も無い = 真の Silent Failure
        checker = _make_checker()
        checker._count_logs = MagicMock(side_effect=self._fake_count(50, 0, 0))
        before = checker.result.critical_issues
        checker._detect_silent_failure()
        assert checker.result.critical_issues == before + 3

    def test_no_signal_is_warning(self):
        # フルサイクルに一度も入っていない → warning に留める
        checker = _make_checker()
        checker._count_logs = MagicMock(side_effect=self._fake_count(0, 0, 0))
        before = checker.result.warning_issues
        checker._detect_silent_failure()
        assert checker.result.warning_issues == before + 1

    def test_orders_executed_computes_success_rate(self):
        # 実行あり → success_rate を参考値として計算（判定は normal）
        checker = _make_checker()
        checker._count_logs = MagicMock(side_effect=self._fake_count(10, 5, 3))
        checker._detect_silent_failure()
        assert checker.result.success_rate == 50
        assert checker.result.normal_checks >= 1

    def test_low_execution_rate_with_rejections_is_normal(self):
        # 実機回帰: signal/resolved は --limit=30 でクランプ・order は少数。
        # 実行率 3/30=10% でも拒否で処理完了しているため正常（旧実装は <20% を CRITICAL 誤判定）。
        checker = _make_checker()
        checker._count_logs = MagicMock(side_effect=self._fake_count(30, 3, 30))
        before_c = checker.result.critical_issues
        before_w = checker.result.warning_issues
        checker._detect_silent_failure()
        assert checker.result.critical_issues == before_c
        assert checker.result.warning_issues == before_w
        assert checker.result.normal_checks >= 1
        assert checker.result.success_rate == 10  # 参考値として保持
