"""Phase 90ο Stage 3: TPSLManager._check_position_invariants の単体テスト

VP↔実ポジの不変条件（建玉サイズ膨張・両建て・状態乖離）の検知ログを検証する。
2026-06-15 のサイズ膨張型ドカン（重複エントリーで 0.0325 BTC）の再発を、
毎サイクル損失前に可視化するための監視。検知のみで決済・復元はしない。
"""

from unittest.mock import MagicMock, patch

from src.trading.execution.tp_sl_manager import TPSLManager


def _make_mgr():
    mgr = TPSLManager()
    mgr.logger = MagicMock()
    return mgr


class TestPhase90OmicronInvariants:
    """_check_position_invariants の検知ロジック"""

    def test_size_inflation_critical(self):
        """建玉合計 > 上限 → CRITICAL（6/15 のサイズ膨張型ドカンの再発検知）"""
        mgr = _make_mgr()
        with patch("src.trading.execution.tp_sl_manager.get_threshold", return_value=0.02):
            mgr._check_position_invariants(
                virtual_positions=[{"side": "sell", "amount": 0.0325}],
                margin_positions=[{"side": "short", "amount": 0.0325}],
            )
        criticals = [str(c.args[0]) for c in mgr.logger.critical.call_args_list]
        assert any("invariant違反" in m and "建玉合計" in m for m in criticals)

    def test_within_limit_no_critical(self):
        """1ポジ分（≤上限）・VP一致 → CRITICAL なし"""
        mgr = _make_mgr()
        with patch("src.trading.execution.tp_sl_manager.get_threshold", return_value=0.02):
            mgr._check_position_invariants(
                virtual_positions=[{"side": "sell", "amount": 0.015}],
                margin_positions=[{"side": "short", "amount": 0.015}],
            )
        assert not mgr.logger.critical.called

    def test_both_direction_warning(self):
        """long+short 両建て → WARNING"""
        mgr = _make_mgr()
        with patch("src.trading.execution.tp_sl_manager.get_threshold", return_value=0.02):
            mgr._check_position_invariants(
                virtual_positions=[
                    {"side": "buy", "amount": 0.01},
                    {"side": "sell", "amount": 0.01},
                ],
                margin_positions=[
                    {"side": "long", "amount": 0.01},
                    {"side": "short", "amount": 0.01},
                ],
            )
        warnings = [str(c.args[0]) for c in mgr.logger.warning.call_args_list]
        assert any("両建て" in m for m in warnings)

    def test_divergence_3_consecutive_escalates_to_critical(self):
        """VP↔実ポジ乖離: 2回までは warning、3回連続で CRITICAL 昇格"""
        mgr = _make_mgr()
        vp = []  # VP空（再起動で揮発した状態）
        mp = [{"side": "short", "amount": 0.015}]  # 実ポジは存在
        with patch("src.trading.execution.tp_sl_manager.get_threshold", return_value=0.02):
            mgr._check_position_invariants(vp, mp)  # 1回目
            mgr._check_position_invariants(vp, mp)  # 2回目
            # 2回目までは乖離 CRITICAL は出ない
            assert not any("乖離" in str(c.args[0]) for c in mgr.logger.critical.call_args_list)
            mgr._check_position_invariants(vp, mp)  # 3回目 → CRITICAL
        assert any(
            "乖離" in str(c.args[0]) and "3連続" in str(c.args[0])
            for c in mgr.logger.critical.call_args_list
        )

    def test_divergence_resets_on_match(self):
        """乖離が解消したらカウンタがリセットされる"""
        mgr = _make_mgr()
        with patch("src.trading.execution.tp_sl_manager.get_threshold", return_value=0.02):
            mgr._check_position_invariants([], [{"side": "short", "amount": 0.015}])  # 乖離1
            mgr._check_position_invariants([], [{"side": "short", "amount": 0.015}])  # 乖離2
            # VP=実ポジで一致 → リセット
            mgr._check_position_invariants(
                [{"side": "sell", "amount": 0.015}], [{"side": "short", "amount": 0.015}]
            )
        assert mgr._invariant_divergence_count == 0

    def test_empty_both_no_violation(self):
        """VP・実ポジともに空（フラット）→ 違反なし"""
        mgr = _make_mgr()
        with patch("src.trading.execution.tp_sl_manager.get_threshold", return_value=0.02):
            mgr._check_position_invariants([], [])
        assert not mgr.logger.critical.called
