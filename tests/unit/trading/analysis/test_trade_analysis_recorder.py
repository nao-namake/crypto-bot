"""Phase 69.7: TradeAnalysisRecorder テスト"""

import os
import tempfile

import pytest

from src.trading.analysis.trade_analysis_recorder import TradeAnalysisRecorder


@pytest.fixture
def tmp_db_path(tmp_path):
    return str(tmp_path / "test_trade.db")


@pytest.fixture
def recorder(tmp_db_path):
    return TradeAnalysisRecorder(db_path=tmp_db_path)


class TestRecordEntry:
    """エントリー記録テスト"""

    def test_basic_entry(self, recorder):
        recorder.record_entry(
            order_id="order_123",
            price=11000000.0,
            side="buy",
            amount=0.01,
            strategy_name="ATRBased",
            ml_prediction=2,
            ml_confidence=0.45,
            adjusted_confidence=0.38,
            regime="tight_range",
            take_profit=11050000.0,
            stop_loss=10950000.0,
        )
        analyses = recorder.get_recent_analyses()
        assert len(analyses) == 0  # exit未記録なので表示されない

    def test_entry_with_none_values(self, recorder):
        recorder.record_entry(
            order_id="order_456",
            price=11000000.0,
            side="sell",
            amount=0.02,
        )
        # エラーなく記録される
        pending = recorder.get_pending_price_checks()
        assert len(pending) == 0  # exit未記録

    def test_entry_overwrite(self, recorder):
        recorder.record_entry(
            order_id="order_789",
            price=11000000.0,
            side="buy",
            amount=0.01,
            strategy_name="ATRBased",
        )
        recorder.record_entry(
            order_id="order_789",
            price=11100000.0,
            side="buy",
            amount=0.02,
            strategy_name="BBReversal",
        )
        # REPLACE動作の確認


class TestRecordExit:
    """決済記録テスト"""

    def test_tp_exit(self, recorder):
        recorder.record_entry(
            order_id="order_tp",
            price=11000000.0,
            side="buy",
            amount=0.01,
            strategy_name="ATRBased",
            ml_confidence=0.50,
            regime="normal_range",
            take_profit=11050000.0,
            stop_loss=10950000.0,
        )
        recorder.record_exit(
            entry_order_id="order_tp",
            exit_price=11050000.0,
            exit_type="take_profit",
            pnl=500.0,
        )
        analyses = recorder.get_recent_analyses()
        assert len(analyses) == 1
        assert analyses[0]["exit_type"] == "take_profit"
        assert analyses[0]["pnl"] == 500.0
        assert analyses[0]["strategy_name"] == "ATRBased"
        assert analyses[0]["ml_confidence"] == 0.50
        assert analyses[0]["regime"] == "normal_range"

    def test_sl_exit(self, recorder):
        recorder.record_entry(
            order_id="order_sl",
            price=11000000.0,
            side="buy",
            amount=0.01,
        )
        recorder.record_exit(
            entry_order_id="order_sl",
            exit_price=10950000.0,
            exit_type="stop_loss_timeout",
            pnl=-500.0,
        )
        analyses = recorder.get_recent_analyses()
        assert len(analyses) == 1
        assert analyses[0]["pnl"] == -500.0

    def test_exit_without_entry(self, recorder):
        """エントリー未記録の決済はスキップ"""
        recorder.record_exit(
            entry_order_id="nonexistent",
            exit_price=11000000.0,
            exit_type="take_profit",
            pnl=500.0,
        )
        analyses = recorder.get_recent_analyses()
        assert len(analyses) == 0


class TestPostExitPrices:
    """事後価格追跡テスト"""

    def test_update_partial_prices(self, recorder):
        recorder.record_entry(
            order_id="order_post",
            price=11000000.0,
            side="buy",
            amount=0.01,
        )
        recorder.record_exit(
            entry_order_id="order_post",
            exit_price=11050000.0,
            exit_type="take_profit",
            pnl=500.0,
        )
        # 15分後のみ更新
        recorder.update_post_exit_prices("order_post", price_15min=11040000.0)

        pending = recorder.get_pending_price_checks()
        assert len(pending) == 1  # 4hがまだない
        assert pending[0]["price_15min_after"] == 11040000.0
        assert pending[0]["price_1h_after"] is None

    def test_update_all_prices(self, recorder):
        recorder.record_entry(
            order_id="order_full",
            price=11000000.0,
            side="buy",
            amount=0.01,
        )
        recorder.record_exit(
            entry_order_id="order_full",
            exit_price=11050000.0,
            exit_type="take_profit",
            pnl=500.0,
        )
        recorder.update_post_exit_prices(
            "order_full",
            price_15min=11040000.0,
            price_1h=11030000.0,
            price_4h=11020000.0,
        )
        pending = recorder.get_pending_price_checks()
        assert len(pending) == 0  # 全て埋まった

        analyses = recorder.get_recent_analyses()
        assert analyses[0]["price_4h_after"] == 11020000.0

    def test_get_pending_empty(self, recorder):
        pending = recorder.get_pending_price_checks()
        assert pending == []


class TestEvaluateDecision:
    """判断評価テスト"""

    def test_tp_good_buy(self):
        """TP後に価格下落 → TP正解"""
        record = {
            "exit_type": "take_profit",
            "entry_side": "buy",
            "exit_price": 11050000.0,
            "price_1h_after": 11030000.0,
        }
        assert TradeAnalysisRecorder.evaluate_decision(record) == "good"

    def test_tp_bad_buy(self):
        """TP後に価格上昇 → TP早すぎ"""
        record = {
            "exit_type": "take_profit",
            "entry_side": "buy",
            "exit_price": 11050000.0,
            "price_1h_after": 11100000.0,
        }
        assert TradeAnalysisRecorder.evaluate_decision(record) == "bad"

    def test_sl_good_buy(self):
        """SL後にさらに下落 → SL正解"""
        record = {
            "exit_type": "stop_loss",
            "entry_side": "buy",
            "exit_price": 10950000.0,
            "price_1h_after": 10900000.0,
        }
        assert TradeAnalysisRecorder.evaluate_decision(record) == "good"

    def test_sl_bad_buy(self):
        """SL後に価格回復 → SL不要だった"""
        record = {
            "exit_type": "stop_loss",
            "entry_side": "buy",
            "exit_price": 10950000.0,
            "price_1h_after": 11050000.0,
        }
        assert TradeAnalysisRecorder.evaluate_decision(record) == "bad"

    def test_sl_timeout_good_sell(self):
        """ショートSLタイムアウト後にさらに上昇 → SL正解"""
        record = {
            "exit_type": "stop_loss_timeout",
            "entry_side": "sell",
            "exit_price": 11100000.0,
            "price_1h_after": 11200000.0,
        }
        assert TradeAnalysisRecorder.evaluate_decision(record) == "good"

    def test_no_post_price(self):
        """事後価格なし → None"""
        record = {
            "exit_type": "take_profit",
            "entry_side": "buy",
            "exit_price": 11050000.0,
            "price_1h_after": None,
        }
        assert TradeAnalysisRecorder.evaluate_decision(record) is None

    def test_no_exit_price(self):
        record = {
            "exit_type": "take_profit",
            "entry_side": "buy",
            "exit_price": 0,
            "price_1h_after": 11000000.0,
        }
        assert TradeAnalysisRecorder.evaluate_decision(record) is None


class TestGetRecentAnalyses:
    """直近分析取得テスト"""

    def test_limit(self, recorder):
        for i in range(5):
            recorder.record_entry(
                order_id=f"order_{i}",
                price=11000000.0 + i * 1000,
                side="buy",
                amount=0.01,
            )
            recorder.record_exit(
                entry_order_id=f"order_{i}",
                exit_price=11050000.0,
                exit_type="take_profit",
                pnl=500.0,
            )
        analyses = recorder.get_recent_analyses(limit=3)
        assert len(analyses) == 3

    def test_only_exited(self, recorder):
        """決済済みのみ返す"""
        recorder.record_entry(
            order_id="open_order",
            price=11000000.0,
            side="buy",
            amount=0.01,
        )
        analyses = recorder.get_recent_analyses()
        assert len(analyses) == 0
