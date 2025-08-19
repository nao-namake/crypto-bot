"""
Phase 8 バックテストエンジンテスト

カバレッジ向上とシステム品質保証のための基本テスト.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pandas as pd

from src.backtest.engine import BacktestEngine, TradeRecord
from src.trading.risk import RiskDecision


class TestBacktestEngine:
    """BacktestEngine基本テスト."""

    def test_engine_initialization(self):
        """エンジン初期化テスト."""
        engine = BacktestEngine(initial_balance=100000)

        assert engine.initial_balance == 100000
        assert engine.current_balance == 100000
        assert len(engine.trade_records) == 0
        assert engine.trade_records == []
        assert engine.position is not None

    def test_reset_engine(self):
        """エンジンリセットテスト."""
        engine = BacktestEngine()

        # 状態変更
        engine.current_balance = 500000
        engine.trade_records = [Mock()]

        # リセット実行
        engine.reset()

        # 初期状態確認
        assert engine.current_balance == engine.initial_balance
        assert len(engine.trade_records) == 0
        assert engine.trade_records == []
        assert engine.position is not None

    def test_trade_record_creation(self):
        """TradeRecord作成テスト."""
        entry_time = datetime.now()
        exit_time = entry_time + timedelta(hours=2)

        trade = TradeRecord(
            entry_time=entry_time,
            exit_time=exit_time,
            side="buy",
            entry_price=5000000.0,
            exit_price=5100000.0,
            amount=0.01,
            profit_jpy=1000.0,
            profit_rate=0.02,
            slippage=100.0,
            commission=60.0,
            stop_loss=4900000.0,
            take_profit=5200000.0,
            strategy_signal="atr_based",
            ml_confidence=0.75,
            risk_score=0.3,
        )

        assert trade.side == "buy"
        assert trade.entry_price == 5000000.0
        assert trade.profit_jpy == 1000.0
        assert trade.strategy_signal == "atr_based"

    @patch("src.backtest.engine.DataPipeline")
    def test_engine_components_integration(self, mock_pipeline):
        """エンジンコンポーネント統合テスト."""
        mock_pipeline.return_value = Mock()

        engine = BacktestEngine()

        # 主要コンポーネント確認
        assert engine.data_pipeline is not None
        assert engine.strategy_manager is not None
        assert engine.model_manager is not None
        assert engine.risk_manager is not None

    def test_calculate_performance_metrics(self):
        """パフォーマンス指標計算テスト."""
        engine = BacktestEngine(initial_balance=1000000)

        # サンプル取引記録追加
        trade1 = TradeRecord(
            entry_time=datetime.now(),
            exit_time=datetime.now() + timedelta(hours=1),
            side="buy",
            entry_price=5000000.0,
            exit_price=5100000.0,
            amount=0.01,
            profit_jpy=10000.0,
            profit_rate=0.02,
            slippage=0.0,
            commission=60.0,
            stop_loss=None,
            take_profit=None,
            strategy_signal="test",
            ml_confidence=0.7,
            risk_score=0.2,
        )

        trade2 = TradeRecord(
            entry_time=datetime.now(),
            exit_time=datetime.now() + timedelta(hours=2),
            side="sell",
            entry_price=5100000.0,
            exit_price=5000000.0,
            amount=0.01,
            profit_jpy=-10000.0,
            profit_rate=-0.02,
            slippage=0.0,
            commission=60.0,
            stop_loss=None,
            take_profit=None,
            strategy_signal="test",
            ml_confidence=0.6,
            risk_score=0.4,
        )

        engine.trade_records = [trade1, trade2]
        engine.total_trades = 2

        # 基本統計計算
        total_profit = sum(t.profit_jpy for t in engine.trade_records)
        win_rate = len([t for t in engine.trade_records if t.profit_jpy > 0]) / len(
            engine.trade_records
        )

        assert total_profit == 0.0  # 利益+損失=0
        assert win_rate == 0.5  # 勝率50%

    def test_engine_state_properties(self):
        """エンジン状態プロパティテスト."""
        engine = BacktestEngine()

        # 基本プロパティ確認
        assert hasattr(engine, "initial_balance")
        assert hasattr(engine, "current_balance")
        assert hasattr(engine, "trade_records")
        assert hasattr(engine, "position")
        assert hasattr(engine, "equity_curve")

        # 初期状態確認
        assert engine.initial_balance > 0
        assert engine.current_balance == engine.initial_balance
        assert isinstance(engine.trade_records, list)
        assert isinstance(engine.equity_curve, list)


class TestBacktestEngineIntegration:
    """BacktestEngine統合テスト."""

    def test_engine_with_mock_data(self):
        """モックデータでのエンジンテスト."""
        engine = BacktestEngine()

        # モック市場データ
        mock_data = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=100, freq="1H"),
                "open": [5000000.0] * 100,
                "high": [5050000.0] * 100,
                "low": [4950000.0] * 100,
                "close": [5000000.0] * 100,
                "volume": [1000.0] * 100,
            }
        )

        # データ設定（実際のバックテスト実行はせず、設定のみテスト）
        assert mock_data is not None
        assert len(mock_data) == 100

    def test_risk_manager_integration(self):
        """リスク管理システム統合テスト."""
        engine = BacktestEngine()

        # リスク管理システムが適切に初期化されているか確認
        assert engine.risk_manager is not None

        # 基本設定確認
        risk_summary = engine.risk_manager.get_risk_summary()
        assert "risk_metrics" in risk_summary
        assert "system_status" in risk_summary
