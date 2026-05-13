"""
ドローダウン管理テスト - Phase 38対応完了

Phase 6リスク管理層のドローダウン監視・制御機能テスト。

テスト範囲:
- ドローダウン計算の正確性
- 連続損失カウント
- 取引停止判定
- 状態永続化

Phase 38 API変更:
- Constructor: DrawdownManager(config={"persistence": {"local_path": path}})
- Default initial_balance: 10000.0
- update_balance: 戻り値なし（void）
- Session management: 未実装（将来追加予定）
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.trading import (
    DrawdownManager,
    TradingStatus,
)


class TestDrawdownManager:
    """ドローダウン管理テスト."""

    def setup_method(self):
        """各テスト前の初期化."""
        # Phase 38: テンポラリファイルを使用して永続化テスト
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_file.close()

        # Phase 38: persistence引数がconfig引数に統合
        self.manager = DrawdownManager(
            max_drawdown_ratio=0.20,
            consecutive_loss_limit=5,
            cooldown_hours=6,  # Phase 55.12: 6時間に変更
            config={
                "persistence": {
                    "local_path": self.temp_file.name,
                }
            },
            mode="backtest",  # テストモードでは永続化しない
        )

    def teardown_method(self):
        """各テスト後のクリーンアップ."""
        try:
            Path(self.temp_file.name).unlink()
        except OSError:
            pass

    def test_drawdown_manager_initialization(self):
        """ドローダウン管理器初期化テスト."""
        assert self.manager.max_drawdown_ratio == 0.20
        assert self.manager.consecutive_loss_limit == 5
        assert self.manager.cooldown_hours == 6  # Phase 55.12: 6時間に変更
        # Phase 38: 初期残高はデフォルト10000.0に変更
        assert self.manager.current_balance == 10000.0
        assert self.manager.peak_balance == 10000.0
        assert self.manager.consecutive_losses == 0
        assert self.manager.trading_status == TradingStatus.ACTIVE

    def test_initialize_balance(self):
        """初期残高設定テスト."""
        initial_balance = 1000000  # 100万円

        self.manager.initialize_balance(initial_balance)

        assert self.manager.current_balance == initial_balance
        assert self.manager.peak_balance == initial_balance

    def test_invalid_initial_balance(self):
        """無効初期残高のエラーハンドリングテスト."""
        # Phase 38: 負の残高はそのまま設定される（バリデーションなし）
        self.manager.initialize_balance(-100000)

        # 負の残高も設定可能
        assert self.manager.current_balance == -100000

    def test_update_balance_normal(self):
        """通常の残高更新テスト."""
        self.manager.initialize_balance(1000000)

        # 残高増加（新しいピーク）
        self.manager.update_balance(1100000)
        assert self.manager.current_balance == 1100000
        assert self.manager.peak_balance == 1100000

        # 残高減少（ドローダウン発生）
        self.manager.update_balance(1050000)
        assert self.manager.current_balance == 1050000
        drawdown = self.manager.calculate_current_drawdown()
        expected_drawdown = (1100000 - 1050000) / 1100000  # 約4.5%
        assert abs(drawdown - expected_drawdown) < 0.001

    def test_drawdown_calculation(self):
        """ドローダウン計算テスト."""
        self.manager.initialize_balance(1000000)
        self.manager.update_balance(1200000)  # ピーク更新

        # 10%ドローダウン
        self.manager.update_balance(1080000)
        drawdown = self.manager.calculate_current_drawdown()
        expected = (1200000 - 1080000) / 1200000
        assert abs(drawdown - expected) < 0.001

        # 20%ドローダウン（制限値）
        self.manager.update_balance(960000)
        drawdown = self.manager.calculate_current_drawdown()
        expected = (1200000 - 960000) / 1200000
        assert abs(drawdown - expected) < 0.001
        assert drawdown >= 0.20

    def test_trading_allowed_normal(self):
        """通常時の取引許可テスト."""
        self.manager.initialize_balance(1000000)

        # 通常状態
        assert self.manager.check_trading_allowed() == True

        # 軽微なドローダウン（15%）
        self.manager.update_balance(850000)
        assert self.manager.check_trading_allowed() == True

    def test_drawdown_limit_exceeded(self):
        """ドローダウン制限超過テスト."""
        self.manager.initialize_balance(1000000)

        # 20%超のドローダウン - record_trade_resultで検知される
        self.manager.update_balance(750000)  # 25%ドローダウン
        self.manager.record_trade_result(-250000, "test")  # 損失記録でチェック

        drawdown = self.manager.calculate_current_drawdown()
        assert drawdown >= 0.20
        assert self.manager.trading_status == TradingStatus.PAUSED_DRAWDOWN
        assert self.manager.check_trading_allowed() == False

    def test_record_trade_result_wins(self):
        """勝ち取引記録テスト."""
        self.manager.initialize_balance(1000000)

        # 連続損失がある状態で勝ち取引
        self.manager.consecutive_losses = 3

        self.manager.record_trade_result(profit_loss=50000, strategy="test_strategy")  # 5万円利益

        # 勝ち取引で連続損失リセット
        assert self.manager.consecutive_losses == 0

    def test_record_trade_result_losses(self):
        """負け取引記録テスト."""
        self.manager.initialize_balance(1000000)

        # 損失取引記録
        self.manager.record_trade_result(profit_loss=-30000, strategy="test_strategy")  # 3万円損失

        assert self.manager.consecutive_losses == 1
        assert self.manager.trading_status == TradingStatus.ACTIVE  # まだ制限内

    def test_consecutive_loss_limit(self):
        """連続損失制限テスト."""
        self.manager.initialize_balance(1000000)

        # 5回連続損失
        for _i in range(5):
            self.manager.record_trade_result(-20000, "test")

        assert self.manager.consecutive_losses == 5
        assert self.manager.trading_status == TradingStatus.PAUSED_CONSECUTIVE_LOSS
        assert self.manager.cooldown_until is not None

        # 取引停止確認
        assert self.manager.check_trading_allowed() == False

    def test_cooldown_period(self):
        """クールダウン期間テスト. (Phase 87 H8: 即 ACTIVE → RECOVERY_TESTING 経由に変更)"""
        self.manager.initialize_balance(1000000)

        # 連続損失で停止
        for _i in range(5):
            self.manager.record_trade_result(-20000, "test")

        # 停止期間中は取引不可
        assert self.manager.check_trading_allowed() == False

        # 時間経過をシミュレート（25時間後）
        future_time = datetime.now() + timedelta(hours=25)
        with patch("src.trading.risk.drawdown.datetime") as mock_datetime:
            mock_datetime.now.return_value = future_time

            # Phase 87 H8: クールダウン期間終了で RECOVERY_TESTING へ（即ACTIVEではない）
            # check_trading_allowed は RECOVERY_TESTING でも False（trading_status != ACTIVE）
            # ※既存仕様維持: RECOVERY_TESTING 中の取引可否判定は上位層で別途扱う
            allowed = self.manager.check_trading_allowed()
            # Phase 87 H8: RECOVERY_TESTING へ遷移、consecutive_losses は維持
            assert self.manager.trading_status == TradingStatus.RECOVERY_TESTING
            assert self.manager.consecutive_losses == 5  # 維持されることを確認
            # ACTIVE ではないので allowed=False（既存 check_trading_allowed は ACTIVE のみ True）
            assert allowed is False

    def test_drawdown_statistics(self):
        """ドローダウン統計情報テスト."""
        self.manager.initialize_balance(1000000)
        self.manager.update_balance(1200000)  # ピーク
        self.manager.update_balance(1100000)  # ドローダウン

        # 取引記録追加
        self.manager.record_trade_result(50000, "strategy_a")
        self.manager.record_trade_result(-30000, "strategy_b")

        stats = self.manager.get_drawdown_statistics()

        assert "current_balance" in stats
        assert "peak_balance" in stats
        assert "current_drawdown" in stats
        assert "consecutive_losses" in stats
        assert "trading_status" in stats
        assert "trading_allowed" in stats

        assert stats["current_balance"] == 1100000
        assert stats["peak_balance"] == 1200000
        assert stats["consecutive_losses"] == 1  # 最後が損失

    def test_state_persistence(self):
        """状態永続化テスト."""
        # Phase 38: modeをliveに変更して永続化テスト
        manager = DrawdownManager(
            config={
                "persistence": {
                    "local_path": self.temp_file.name,
                }
            },
            mode="live",  # 永続化有効化
        )

        # 初期状態設定
        manager.initialize_balance(1000000)
        manager.update_balance(1100000)
        manager.record_trade_result(-50000, "test")

        # 状態保存確認
        assert Path(self.temp_file.name).exists()

        # 新しいマネージャーで状態復元
        manager2 = DrawdownManager(
            config={
                "persistence": {
                    "local_path": self.temp_file.name,
                }
            },
            mode="live",
        )

        # 状態復元確認
        assert manager2.current_balance == 1100000
        assert manager2.peak_balance == 1100000
        assert manager2.consecutive_losses == 1

    def test_edge_cases(self):
        """エッジケーステスト."""
        # ゼロ残高
        self.manager.initialize_balance(100000)
        self.manager.update_balance(0)
        drawdown = self.manager.calculate_current_drawdown()
        assert drawdown == 1.0  # 100%ドローダウン

        # 負の残高
        self.manager.update_balance(-50000)
        drawdown = self.manager.calculate_current_drawdown()
        assert drawdown > 1.0  # 100%超のドローダウン

    def test_error_handling(self):
        """エラーハンドリングテスト."""
        # 初期化前の操作（一時ファイルで独立状態）
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_file:
            new_manager = DrawdownManager(
                config={
                    "persistence": {
                        "local_path": temp_file.name,
                    }
                },
                mode="backtest",
            )

        # エラーが発生してもシステムが停止しない
        drawdown = new_manager.calculate_current_drawdown()
        assert drawdown == 0.0

        stats = new_manager.get_drawdown_statistics()
        assert "current_balance" in stats


# パフォーマンステスト
def test_large_trade_history():
    """大量取引履歴のパフォーマンステスト."""
    manager = DrawdownManager(mode="backtest")
    manager.initialize_balance(1000000)

    # 1000回の取引をシミュレート
    import time

    start_time = time.time()

    for i in range(1000):
        profit_loss = 1000 if i % 3 == 0 else -500  # 勝率33%
        manager.record_trade_result(profit_loss, f"strategy_{i % 5}")

    end_time = time.time()

    # 3秒以内で処理完了を確認（CI環境の負荷を考慮）
    assert end_time - start_time < 3.0

    # 履歴サイズ確認
    assert len(manager.trade_history) == 1000


# 統合テスト
def test_realistic_trading_scenario():
    """現実的な取引シナリオテスト."""
    manager = DrawdownManager(
        max_drawdown_ratio=0.15,  # 15%制限
        consecutive_loss_limit=3,  # 3回制限
        mode="backtest",
    )

    # 初期資金100万円
    manager.initialize_balance(1000000)

    # 好調期（残高増加）
    manager.update_balance(1100000)
    manager.record_trade_result(50000, "strategy_a")
    manager.update_balance(1150000)
    manager.record_trade_result(30000, "strategy_b")

    assert manager.check_trading_allowed() == True

    # 調整期（ドローダウン）
    manager.update_balance(1100000)
    manager.record_trade_result(-40000, "strategy_a")
    manager.update_balance(1050000)
    manager.record_trade_result(-30000, "strategy_b")
    manager.update_balance(1000000)
    manager.record_trade_result(-20000, "strategy_a")

    # 3連敗で停止
    assert manager.consecutive_losses == 3
    assert manager.check_trading_allowed() == False

    # 統計確認
    stats = manager.get_drawdown_statistics()
    assert stats["trading_allowed"] == False
    assert stats["consecutive_losses"] == 3


class TestPhase87Stage2R1EmergencyStop:
    """Phase 87 Stage 2-R1: set_emergency_stop() のテスト"""

    def setup_method(self):
        from src.trading.risk.drawdown import DrawdownManager, TradingStatus

        self.TradingStatus = TradingStatus
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_file.close()
        self.manager = DrawdownManager(
            max_drawdown_ratio=0.20,
            consecutive_loss_limit=5,
            cooldown_hours=6,
            config={"persistence": {"local_path": self.temp_file.name}},
            mode="backtest",
        )

    def teardown_method(self):
        try:
            Path(self.temp_file.name).unlink()
        except OSError:
            pass

    def test_set_emergency_stop_transitions(self):
        """ACTIVE → EMERGENCY_STOP へ遷移"""
        assert self.manager.trading_status == self.TradingStatus.ACTIVE
        self.manager.set_emergency_stop("ml_consecutive_failures=3")
        assert self.manager.trading_status == self.TradingStatus.EMERGENCY_STOP

    def test_set_emergency_stop_blocks_trading(self):
        """EMERGENCY_STOP では check_trading_allowed=False"""
        self.manager.set_emergency_stop("test")
        assert self.manager.check_trading_allowed() is False

    def test_set_emergency_stop_idempotent(self):
        """既に EMERGENCY_STOP の状態で再度呼んでも例外なし"""
        self.manager.set_emergency_stop("first")
        self.manager.set_emergency_stop("second")
        assert self.manager.trading_status == self.TradingStatus.EMERGENCY_STOP


class TestPhase87Stage3H8RecoveryTesting:
    """Phase 87 Stage 3 H8: RECOVERY_TESTING + 無限ループ防止"""

    def setup_method(self):
        from src.trading.risk.drawdown import DrawdownManager, TradingStatus

        self.TradingStatus = TradingStatus
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_file.close()
        self.manager = DrawdownManager(
            max_drawdown_ratio=0.20,
            consecutive_loss_limit=5,
            cooldown_hours=6,
            config={"persistence": {"local_path": self.temp_file.name}},
            mode="backtest",
        )
        self.manager.initialize_balance(1000000)

    def teardown_method(self):
        try:
            Path(self.temp_file.name).unlink()
        except OSError:
            pass

    def _enter_recovery_testing(self):
        """RECOVERY_TESTING 状態に遷移させるヘルパー"""
        self.manager.trading_status = self.TradingStatus.RECOVERY_TESTING
        self.manager.consecutive_losses = 5
        self.manager.recovery_win_streak = 0
        self.manager.recovery_failure_count = 0

    def test_recovery_two_wins_returns_active(self):
        """2連勝で ACTIVE 復帰 + consecutive_losses リセット"""
        self._enter_recovery_testing()
        self.manager.record_recovery_trade(100)
        assert self.manager.trading_status == self.TradingStatus.RECOVERY_TESTING
        self.manager.record_recovery_trade(200)
        assert self.manager.trading_status == self.TradingStatus.ACTIVE
        assert self.manager.consecutive_losses == 0
        assert self.manager.recovery_win_streak == 0
        assert self.manager.recovery_failure_count == 0

    def test_recovery_loss_re_cooldown(self):
        """1勝後の損失で win_streak リセット + 再 cooldown"""
        self._enter_recovery_testing()
        self.manager.record_recovery_trade(100)
        assert self.manager.recovery_win_streak == 1
        # 損失 → 再 cooldown
        self.manager.record_recovery_trade(-50)
        assert self.manager.recovery_win_streak == 0
        assert self.manager.recovery_failure_count == 1
        # PAUSED_CONSECUTIVE_LOSS に遷移
        assert self.manager.trading_status == self.TradingStatus.PAUSED_CONSECUTIVE_LOSS

    def test_recovery_position_size_half(self):
        """RECOVERY_TESTING 中はポジションサイズ倍率が 0.5 固定"""
        self._enter_recovery_testing()
        assert self.manager.get_position_size_multiplier() == 0.5

    def test_record_trade_result_delegates_to_recovery(self):
        """RECOVERY_TESTING 中に record_trade_result を呼ぶと record_recovery_trade に委譲"""
        self._enter_recovery_testing()
        self.manager.record_trade_result(100, "test")
        # win_streak が増えることで record_recovery_trade が呼ばれたことを確認
        assert self.manager.recovery_win_streak == 1

    def test_recovery_state_persistence(self):
        """recovery_win_streak / recovery_failure_count が save/load される (mode=live モック)"""
        from src.trading.risk.drawdown import DrawdownManager

        # mode='paper' に変更（_save_state/_load_state が動作する）
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        tmp.close()
        mgr1 = DrawdownManager(
            max_drawdown_ratio=0.2,
            consecutive_loss_limit=5,
            cooldown_hours=6,
            config={"persistence": {"local_path": tmp.name}},
            mode="paper",
        )
        mgr1.recovery_win_streak = 3
        mgr1.recovery_failure_count = 1
        mgr1._save_state()

        # 別インスタンスで復元
        mgr2 = DrawdownManager(
            max_drawdown_ratio=0.2,
            consecutive_loss_limit=5,
            cooldown_hours=6,
            config={"persistence": {"local_path": tmp.name}},
            mode="paper",
        )
        assert mgr2.recovery_win_streak == 3
        assert mgr2.recovery_failure_count == 1

        try:
            Path(tmp.name).unlink()
        except OSError:
            pass

    def test_recovery_infinite_loop_emergency_stop(self):
        """3回連続 recovery 失敗で EMERGENCY_STOP に遷移"""
        self._enter_recovery_testing()
        # 3回連続損失（各回で recovery_failure_count += 1）
        # 1回目: failure_count=1 → PAUSED_CONSECUTIVE_LOSS
        self.manager.record_recovery_trade(-50)
        assert self.manager.recovery_failure_count == 1
        # 再度 RECOVERY_TESTING に戻す（実運用では cooldown 解除で自動）
        self._enter_recovery_testing()
        self.manager.recovery_failure_count = 1  # 引き継ぎ
        # 2回目: failure_count=2 → PAUSED_CONSECUTIVE_LOSS
        self.manager.record_recovery_trade(-50)
        assert self.manager.recovery_failure_count == 2
        # 3回目: failure_count=3 → EMERGENCY_STOP
        self._enter_recovery_testing()
        self.manager.recovery_failure_count = 2
        self.manager.record_recovery_trade(-50)
        assert self.manager.recovery_failure_count == 3
        assert self.manager.trading_status == self.TradingStatus.EMERGENCY_STOP
