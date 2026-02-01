"""
TradeTracker unit tests - Phase 61.4 MFE/MAE機能含む
"""

from datetime import datetime, timedelta

import pytest

from src.backtest.reporter import TradeTracker


class TestTradeTrackerBasic:
    """TradeTracker基本機能テスト"""

    def test_init(self):
        """初期化テスト"""
        tracker = TradeTracker()
        assert tracker.open_entries == {}
        assert tracker.completed_trades == []
        assert tracker.total_pnl == 0.0
        assert tracker.equity_curve == [0.0]

    def test_record_entry(self):
        """エントリー記録テスト"""
        tracker = TradeTracker()
        timestamp = datetime.now()

        tracker.record_entry(
            order_id="test_001",
            side="buy",
            amount=0.001,
            price=15000000,
            timestamp=timestamp,
            strategy="BBReversal",
            regime="tight_range",
        )

        assert "test_001" in tracker.open_entries
        entry = tracker.open_entries["test_001"]
        assert entry["side"] == "buy"
        assert entry["amount"] == 0.001
        assert entry["entry_price"] == 15000000
        assert entry["strategy"] == "BBReversal"
        assert entry["regime"] == "tight_range"
        # Phase 61.4: MFE/MAE初期値
        assert entry["mfe"] == 0.0
        assert entry["mae"] == 0.0

    def test_record_exit_long_profit(self):
        """ロング利益決済テスト（Phase 62.7: 手数料込み）"""
        tracker = TradeTracker()
        entry_time = datetime.now()
        exit_time = entry_time + timedelta(minutes=30)

        tracker.record_entry("test_001", "buy", 0.001, 15000000, entry_time, "Test")
        trade = tracker.record_exit("test_001", 15100000, exit_time, "TP")

        assert trade is not None
        # Phase 62.7: 粗利100 - 手数料(15000000 + 15100000) × 0.001 × 0.0012 × 2 ≈ 64円
        assert trade["pnl"] == pytest.approx(64, abs=2)
        assert trade["exit_reason"] == "TP"
        assert len(tracker.completed_trades) == 1
        assert tracker.total_pnl == pytest.approx(64, abs=2)

    def test_record_exit_long_loss(self):
        """ロング損失決済テスト（Phase 62.7: 手数料込み）"""
        tracker = TradeTracker()
        entry_time = datetime.now()
        exit_time = entry_time + timedelta(minutes=30)

        tracker.record_entry("test_001", "buy", 0.001, 15000000, entry_time, "Test")
        trade = tracker.record_exit("test_001", 14900000, exit_time, "SL")

        assert trade is not None
        # Phase 62.7: 粗損-100 - 手数料(15000000 + 14900000) × 0.001 × 0.0012 × 2 ≈ -136円
        assert trade["pnl"] == pytest.approx(-136, abs=2)
        assert tracker.total_pnl == pytest.approx(-136, abs=2)

    def test_record_exit_short_profit(self):
        """ショート利益決済テスト（Phase 62.7: 手数料込み）"""
        tracker = TradeTracker()
        entry_time = datetime.now()
        exit_time = entry_time + timedelta(minutes=30)

        tracker.record_entry("test_001", "sell", 0.001, 15000000, entry_time, "Test")
        trade = tracker.record_exit("test_001", 14900000, exit_time, "TP")

        assert trade is not None
        # Phase 62.7: 粗利100 - 手数料(15000000 + 14900000) × 0.001 × 0.0012 × 2 ≈ 64円
        assert trade["pnl"] == pytest.approx(64, abs=2)

    def test_record_exit_short_loss(self):
        """ショート損失決済テスト（Phase 62.7: 手数料込み）"""
        tracker = TradeTracker()
        entry_time = datetime.now()
        exit_time = entry_time + timedelta(minutes=30)

        tracker.record_entry("test_001", "sell", 0.001, 15000000, entry_time, "Test")
        trade = tracker.record_exit("test_001", 15100000, exit_time, "SL")

        assert trade is not None
        # Phase 62.7: 粗損-100 - 手数料(15000000 + 15100000) × 0.001 × 0.0012 × 2 ≈ -136円
        assert trade["pnl"] == pytest.approx(-136, abs=2)

    def test_record_exit_not_found(self):
        """存在しないエントリーの決済テスト"""
        tracker = TradeTracker()
        result = tracker.record_exit("nonexistent", 15000000, datetime.now(), "TP")
        assert result is None

    def test_duplicate_entry_skipped(self):
        """重複エントリーがスキップされるテスト"""
        tracker = TradeTracker()
        timestamp = datetime.now()

        tracker.record_entry("test_001", "buy", 0.001, 15000000, timestamp, "Test1")
        tracker.record_entry("test_001", "sell", 0.002, 16000000, timestamp, "Test2")

        # 最初のエントリーが保持される
        entry = tracker.open_entries["test_001"]
        assert entry["side"] == "buy"
        assert entry["amount"] == 0.001


class TestTradeTrackerMFEMAE:
    """Phase 61.4: MFE/MAE追跡テスト"""

    def test_update_price_excursions_long(self):
        """ロングポジションのMFE/MAE更新テスト"""
        tracker = TradeTracker()
        tracker.record_entry("test_001", "buy", 0.001, 15000000, datetime.now(), "Test")

        # 価格変動: 高値15200000, 安値14800000
        tracker.update_price_excursions(15200000, 14800000)

        entry = tracker.open_entries["test_001"]
        # MFE: (15200000 - 15000000) * 0.001 = 200
        assert entry["mfe"] == 200
        assert entry["mfe_price"] == 15200000
        # MAE: (14800000 - 15000000) * 0.001 = -200
        assert entry["mae"] == -200
        assert entry["mae_price"] == 14800000

    def test_update_price_excursions_short(self):
        """ショートポジションのMFE/MAE更新テスト"""
        tracker = TradeTracker()
        tracker.record_entry("test_001", "sell", 0.001, 15000000, datetime.now(), "Test")

        # 価格変動: 高値15200000, 安値14800000
        tracker.update_price_excursions(15200000, 14800000)

        entry = tracker.open_entries["test_001"]
        # ショートのMFE: (15000000 - 14800000) * 0.001 = 200 (安値でMFE)
        assert entry["mfe"] == 200
        assert entry["mfe_price"] == 14800000
        # ショートのMAE: (15000000 - 15200000) * 0.001 = -200 (高値でMAE)
        assert entry["mae"] == -200
        assert entry["mae_price"] == 15200000

    def test_mfe_mae_incremental_update(self):
        """MFE/MAEが段階的に更新されるテスト"""
        tracker = TradeTracker()
        tracker.record_entry("test_001", "buy", 0.001, 15000000, datetime.now(), "Test")

        # 1回目: 小さな変動
        tracker.update_price_excursions(15050000, 14950000)
        entry = tracker.open_entries["test_001"]
        assert entry["mfe"] == 50
        assert entry["mae"] == -50

        # 2回目: 大きなMFE更新
        tracker.update_price_excursions(15200000, 14980000)
        entry = tracker.open_entries["test_001"]
        assert entry["mfe"] == 200  # 更新
        assert entry["mae"] == -50  # 維持（より小さい損失なので）

        # 3回目: 大きなMAE更新
        tracker.update_price_excursions(15100000, 14700000)
        entry = tracker.open_entries["test_001"]
        assert entry["mfe"] == 200  # 維持
        assert entry["mae"] == -300  # 更新

    def test_mfe_mae_recorded_on_exit(self):
        """決済時にMFE/MAEが記録されるテスト（Phase 62.7: 手数料込み）"""
        tracker = TradeTracker()
        entry_time = datetime.now()
        exit_time = entry_time + timedelta(minutes=30)

        tracker.record_entry("test_001", "buy", 0.001, 15000000, entry_time, "Test")
        tracker.update_price_excursions(15200000, 14800000)
        trade = tracker.record_exit("test_001", 15050000, exit_time, "TP")

        assert trade["mfe"] == 200
        assert trade["mae"] == -200
        assert trade["mfe_price"] == 15200000
        assert trade["mae_price"] == 14800000
        # Phase 62.7: 粗利50 - 手数料約36 ≈ 14円
        assert trade["pnl"] == pytest.approx(14, abs=2)

    def test_mfe_mae_statistics(self):
        """MFE/MAE統計計算テスト（Phase 62.7: 手数料込み）"""
        tracker = TradeTracker()

        # 取引1: MFE到達後に逆行
        tracker.record_entry("test_001", "buy", 0.001, 15000000, datetime.now(), "Test")
        tracker.update_price_excursions(15200000, 14900000)
        tracker.record_exit("test_001", 15050000, datetime.now(), "TP")

        # 取引2: MFEをフル捕捉
        tracker.record_entry("test_002", "buy", 0.001, 15000000, datetime.now(), "Test")
        tracker.update_price_excursions(15100000, 14950000)
        tracker.record_exit("test_002", 15100000, datetime.now(), "TP")

        metrics = tracker.get_performance_metrics()

        assert metrics["avg_mfe"] == 150  # (200 + 100) / 2
        assert metrics["avg_mae"] == -75  # (-100 + -50) / 2
        # Phase 62.7: 手数料考慮後は両方が「逃した利益あり」となる
        # 取引1: MFE 200 vs PnL 14 → 逃した利益あり
        # 取引2: MFE 100 vs PnL 64 → 逃した利益あり
        assert metrics["trades_with_missed_profit"] == 2
        # 取引1: (200 - 14) + 取引2: (100 - 64) ≈ 186 + 36 = 222
        assert metrics["missed_profit_total"] == pytest.approx(222, abs=10)


class TestTradeTrackerPerformanceMetrics:
    """パフォーマンス指標テスト"""

    def test_empty_metrics(self):
        """取引なし時の指標テスト"""
        tracker = TradeTracker()
        metrics = tracker.get_performance_metrics()

        assert metrics["total_trades"] == 0
        assert metrics["win_rate"] == 0.0
        assert metrics["profit_factor"] == 0.0
        assert metrics["avg_mfe"] == 0.0
        assert metrics["avg_mae"] == 0.0

    def test_win_rate_calculation(self):
        """勝率計算テスト"""
        tracker = TradeTracker()

        # 3勝2敗
        for i in range(3):
            tracker.record_entry(f"win_{i}", "buy", 0.001, 15000000, datetime.now(), "Test")
            tracker.record_exit(f"win_{i}", 15100000, datetime.now(), "TP")

        for i in range(2):
            tracker.record_entry(f"loss_{i}", "buy", 0.001, 15000000, datetime.now(), "Test")
            tracker.record_exit(f"loss_{i}", 14900000, datetime.now(), "SL")

        metrics = tracker.get_performance_metrics()
        assert metrics["total_trades"] == 5
        assert metrics["winning_trades"] == 3
        assert metrics["losing_trades"] == 2
        assert metrics["win_rate"] == 60.0

    def test_profit_factor_calculation(self):
        """プロフィットファクター計算テスト（Phase 62.7: 手数料込み）"""
        tracker = TradeTracker()

        # Phase 62.7: 手数料込みで計算
        # 粗利益300円、粗損失100円だが手数料で減少
        tracker.record_entry("win_1", "buy", 0.001, 15000000, datetime.now(), "Test")
        tracker.record_exit("win_1", 15300000, datetime.now(), "TP")  # 粗利300 - 手数料36 = 264

        tracker.record_entry("loss_1", "buy", 0.001, 15000000, datetime.now(), "Test")
        tracker.record_exit("loss_1", 14900000, datetime.now(), "SL")  # 粗損-100 - 手数料36 = -136

        metrics = tracker.get_performance_metrics()
        # Phase 62.7: 手数料控除後の値
        assert metrics["total_profit"] == pytest.approx(264, abs=2)
        assert metrics["total_loss"] == pytest.approx(-136, abs=2)
        # PF = 264 / 136 ≈ 1.94
        assert metrics["profit_factor"] == pytest.approx(1.94, rel=0.1)


class TestTradeTrackerRegimePerformance:
    """レジーム別パフォーマンステスト"""

    def test_regime_performance(self):
        """レジーム別集計テスト"""
        tracker = TradeTracker()

        # tight_range: 2取引
        tracker.record_entry(
            "t1", "buy", 0.001, 15000000, datetime.now(), "Test", regime="tight_range"
        )
        tracker.record_exit("t1", 15100000, datetime.now(), "TP")

        tracker.record_entry(
            "t2", "buy", 0.001, 15000000, datetime.now(), "Test", regime="tight_range"
        )
        tracker.record_exit("t2", 14900000, datetime.now(), "SL")

        # trending: 1取引
        tracker.record_entry(
            "tr1", "buy", 0.001, 15000000, datetime.now(), "Test", regime="trending"
        )
        tracker.record_exit("tr1", 15200000, datetime.now(), "TP")

        regime_perf = tracker.get_regime_performance()

        assert "tight_range" in regime_perf
        assert regime_perf["tight_range"]["total_trades"] == 2
        assert regime_perf["tight_range"]["win_rate"] == 50.0

        assert "trending" in regime_perf
        assert regime_perf["trending"]["total_trades"] == 1
        assert regime_perf["trending"]["win_rate"] == 100.0
