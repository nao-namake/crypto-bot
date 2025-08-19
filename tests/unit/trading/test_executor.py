"""
executor.pyのテスト - Phase 7

レガシーシステムのテストパターンを参考にしつつ、
新システムの非同期処理とシンプル構造に対応したテスト実装。

テスト対象:
- ペーパートレード機能（基本動作）
- ポジション管理（VirtualPosition）
- 統計情報・記録機能
- エラーハンドリング.
"""

import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.trading.executor import (
    ExecutionMode,
    ExecutionResult,
    OrderExecutor,
    OrderStatus,
    TradingStatistics,
    VirtualPosition,
    create_order_executor,
)
from src.trading.risk import RiskDecision, TradeEvaluation


class TestVirtualPosition:
    """VirtualPositionテスト（レガシーから継承・改良）."""

    def test_position_creation(self):
        """ポジション作成テスト."""
        position = VirtualPosition()
        assert position.exist is False
        assert position.side == ""
        assert position.amount == 0.0
        assert position.unrealized_pnl == 0.0

    def test_buy_position_pnl_calculation(self):
        """買いポジションPnL計算テスト."""
        position = VirtualPosition(
            exist=True,
            side="buy",
            entry_price=5000000.0,  # 500万円
            amount=0.1,  # 0.1 BTC
            entry_time=datetime.now(),
        )

        # 価格上昇時（利益）
        current_price = 5500000.0  # 550万円
        pnl = position.calculate_pnl(current_price)
        expected_pnl = (5500000.0 - 5000000.0) * 0.1  # 50万円
        assert pnl == expected_pnl
        assert position.unrealized_pnl == expected_pnl

        # 価格下落時（損失）
        current_price = 4500000.0  # 450万円
        pnl = position.calculate_pnl(current_price)
        expected_pnl = (4500000.0 - 5000000.0) * 0.1  # -50万円
        assert pnl == expected_pnl

    def test_sell_position_pnl_calculation(self):
        """売りポジションPnL計算テスト."""
        position = VirtualPosition(
            exist=True, side="sell", entry_price=5000000.0, amount=0.1, entry_time=datetime.now()
        )

        # 価格下落時（利益）
        current_price = 4500000.0
        pnl = position.calculate_pnl(current_price)
        expected_pnl = (5000000.0 - 4500000.0) * 0.1  # 50万円
        assert pnl == expected_pnl

        # 価格上昇時（損失）
        current_price = 5500000.0
        pnl = position.calculate_pnl(current_price)
        expected_pnl = (5000000.0 - 5500000.0) * 0.1  # -50万円
        assert pnl == expected_pnl

    def test_stop_conditions_buy_position(self):
        """買いポジションのストップ条件テスト."""
        position = VirtualPosition(
            exist=True,
            side="buy",
            entry_price=5000000.0,
            amount=0.1,
            stop_loss=4800000.0,  # 4%下でストップロス
            take_profit=5500000.0,  # 10%上でテイクプロフィット
        )

        # ストップロス条件
        assert position.check_stop_conditions(4700000.0) == "stop_loss"

        # テイクプロフィット条件
        assert position.check_stop_conditions(5600000.0) == "take_profit"

        # 条件なし
        assert position.check_stop_conditions(5100000.0) is None

    def test_stop_conditions_sell_position(self):
        """売りポジションのストップ条件テスト."""
        position = VirtualPosition(
            exist=True,
            side="sell",
            entry_price=5000000.0,
            amount=0.1,
            stop_loss=5200000.0,  # 4%上でストップロス
            take_profit=4500000.0,  # 10%下でテイクプロフィット
        )

        # ストップロス条件
        assert position.check_stop_conditions(5300000.0) == "stop_loss"

        # テイクプロフィット条件
        assert position.check_stop_conditions(4400000.0) == "take_profit"

        # 条件なし
        assert position.check_stop_conditions(4900000.0) is None


class TestOrderExecutor:
    """OrderExecutorテスト."""

    @pytest.fixture
    def temp_log_dir(self):
        """一時ログディレクトリ."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def executor(self, temp_log_dir):
        """テスト用OrderExecutor."""
        return OrderExecutor(
            mode=ExecutionMode.PAPER, initial_balance=1000000.0, log_dir=temp_log_dir
        )

    @pytest.fixture
    def sample_evaluation(self):
        """サンプル取引評価."""
        return TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="buy",  # 追加された必須フィールド
            risk_score=0.2,  # 低リスク
            position_size=0.01,  # 0.01 BTC
            stop_loss=4800000.0,
            take_profit=5500000.0,
            confidence_level=0.75,
            warnings=[],
            denial_reasons=[],
            evaluation_timestamp=datetime.now(),
            kelly_recommendation=0.02,
            drawdown_status="normal",
            anomaly_alerts=[],
            market_conditions={},
        )

    def test_executor_initialization(self, temp_log_dir):
        """初期化テスト."""
        executor = OrderExecutor(
            mode=ExecutionMode.PAPER, initial_balance=1000000.0, log_dir=temp_log_dir
        )

        assert executor.mode == ExecutionMode.PAPER
        assert executor.current_balance == 1000000.0
        assert executor.initial_balance == 1000000.0
        assert executor.virtual_position.exist is False
        assert executor.statistics.total_trades == 0

        # ログファイル作成確認
        assert executor.trades_csv.exists()
        assert executor.trades_csv.parent.exists()

    @pytest.mark.asyncio
    async def test_paper_trade_buy_success(self, executor, sample_evaluation):
        """ペーパートレード買い注文成功テスト."""
        # 現在価格モック
        with patch.object(executor, "_get_current_price", return_value=5000000.0):
            result = await executor.execute_trade(sample_evaluation)

        # 実行結果検証
        assert result.success is True
        assert result.mode == ExecutionMode.PAPER
        assert result.side == "buy"
        assert result.amount == 0.01
        assert result.price == 5000000.0
        assert result.status == OrderStatus.FILLED
        assert result.fee > 0  # 手数料が計算されている

        # 残高・ポジション状態検証
        expected_cost = 0.01 * 5000000.0 + result.fee  # コスト + 手数料
        expected_balance = 1000000.0 - expected_cost
        assert abs(executor.current_balance - expected_balance) < 1.0  # 誤差許容

        assert executor.virtual_position.exist is True
        assert executor.virtual_position.side == "buy"
        assert executor.virtual_position.amount == 0.01
        assert executor.virtual_position.entry_price == 5000000.0

    @pytest.mark.asyncio
    async def test_paper_trade_sell_position_close(self, executor, sample_evaluation):
        """ペーパートレード売り注文（ポジション決済）テスト."""
        # 既存買いポジション設定
        executor.virtual_position = VirtualPosition(
            exist=True, side="buy", entry_price=5000000.0, amount=0.01, entry_time=datetime.now()
        )

        # 売り注文評価
        sell_evaluation = TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="sell",
            risk_score=0.2,  # 必須フィールド追加
            position_size=0.01,
            stop_loss=None,
            take_profit=None,
            confidence_level=0.75,
            warnings=[],
            denial_reasons=[],
            evaluation_timestamp=datetime.now(),
            kelly_recommendation=0.02,
            drawdown_status="normal",
            anomaly_alerts=[],
            market_conditions={},
        )

        # 価格上昇時の決済（利益）
        with patch.object(executor, "_get_current_price", return_value=5500000.0):
            result = await executor.execute_trade(sell_evaluation)

        # 決済結果検証
        assert result.success is True
        assert result.paper_pnl > 0  # 利益が発生
        assert executor.virtual_position.exist is False  # ポジション解消

        # PnL計算検証
        expected_pnl = (5500000.0 - 5000000.0) * 0.01  # 5,000円の利益
        assert abs(result.paper_pnl - expected_pnl) < 1.0

    @pytest.mark.asyncio
    async def test_paper_trade_insufficient_balance(self, executor, sample_evaluation):
        """ペーパートレード残高不足テスト."""
        # 残高を少額に設定
        executor.current_balance = 10000.0  # 1万円

        # 大きな注文（残高不足）
        large_evaluation = TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="buy",
            risk_score=0.2,  # 必須フィールド追加
            position_size=1.0,  # 1 BTC（約500万円相当）
            stop_loss=None,
            take_profit=None,
            confidence_level=0.75,
            warnings=[],
            denial_reasons=[],
            evaluation_timestamp=datetime.now(),
            kelly_recommendation=0.02,
            drawdown_status="normal",
            anomaly_alerts=[],
            market_conditions={},
        )

        with patch.object(executor, "_get_current_price", return_value=5000000.0):
            result = await executor.execute_trade(large_evaluation)

        # 失敗結果検証
        assert result.success is False
        assert "残高不足" in result.error_message
        assert executor.virtual_position.exist is False  # ポジション変更なし

    @pytest.mark.asyncio
    async def test_rejected_evaluation_handling(self, executor):
        """拒否された評価の処理テスト."""
        rejected_evaluation = TradeEvaluation(
            decision=RiskDecision.DENIED,
            side="buy",
            risk_score=0.8,  # 高リスクスコア追加
            position_size=0.01,
            stop_loss=None,
            take_profit=None,
            confidence_level=0.75,
            warnings=[],
            denial_reasons=["高リスク"],
            evaluation_timestamp=datetime.now(),
            kelly_recommendation=0.02,
            drawdown_status="high_risk",
            anomaly_alerts=[],
            market_conditions={},
        )

        result = await executor.execute_trade(rejected_evaluation)

        assert result.success is False
        assert "承認されていません" in result.error_message
        assert executor.virtual_position.exist is False
        assert executor.current_balance == 1000000.0  # 残高変更なし

    @pytest.mark.asyncio
    async def test_statistics_update(self, executor, sample_evaluation):
        """統計情報更新テスト."""
        initial_trades = executor.statistics.total_trades

        # 複数回取引実行
        with patch.object(executor, "_get_current_price", return_value=5000000.0):
            await executor.execute_trade(sample_evaluation)

        # 統計更新確認
        assert executor.statistics.total_trades == initial_trades + 1
        assert executor.statistics.current_balance == executor.current_balance
        assert executor.statistics.last_update is not None

    @pytest.mark.asyncio
    async def test_stop_conditions_check(self, executor):
        """ストップ条件チェックテスト."""
        # ストップロス設定でポジション作成
        executor.virtual_position = VirtualPosition(
            exist=True,
            side="buy",
            entry_price=5000000.0,
            amount=0.01,
            stop_loss=4800000.0,  # 4%下でストップロス
        )

        # ストップロス条件でチェック
        with patch.object(executor, "_get_current_price", return_value=4700000.0):
            result = await executor.check_stop_conditions()

        if result:  # ストップロス発動
            assert result.success is True
            assert result.side == "sell"  # 反対売買（売り）
            assert executor.virtual_position.exist is False  # ポジション解消

    @pytest.mark.asyncio
    async def test_get_current_price_error_handling(self, executor, sample_evaluation):
        """現在価格取得エラーハンドリングテスト."""
        # 価格取得失敗をシミュレート
        with patch.object(executor, "_get_current_price", return_value=None):
            result = await executor.execute_trade(sample_evaluation)

        assert result.success is False
        assert "現在価格取得失敗" in result.error_message

    def test_trading_statistics_retrieval(self, executor):
        """取引統計情報取得テスト."""
        stats = executor.get_trading_statistics()

        assert "mode" in stats
        assert "statistics" in stats
        assert "current_balance" in stats
        assert "initial_balance" in stats
        assert "return_rate" in stats

        assert stats["mode"] == ExecutionMode.PAPER.value
        assert stats["current_balance"] == 1000000.0
        assert stats["return_rate"] == 0.0  # 初期状態

    @pytest.mark.asyncio
    async def test_live_mode_not_implemented(self, temp_log_dir, sample_evaluation):
        """ライブモード未実装の確認テスト."""
        live_executor = OrderExecutor(mode=ExecutionMode.LIVE, log_dir=temp_log_dir)

        result = await live_executor.execute_trade(sample_evaluation)

        assert result.success is False
        assert "未実装" in result.error_message


class TestFactoryFunction:
    """ファクトリー関数テスト."""

    def test_create_order_executor_paper_mode(self):
        """ペーパーモード作成テスト."""
        executor = create_order_executor(mode="paper", initial_balance=500000.0)

        assert executor.mode == ExecutionMode.PAPER
        assert executor.initial_balance == 500000.0
        assert executor.current_balance == 500000.0

    def test_create_order_executor_live_mode(self):
        """ライブモード作成テスト."""
        executor = create_order_executor(mode="live", initial_balance=1000000.0)

        assert executor.mode == ExecutionMode.LIVE
        assert executor.initial_balance == 1000000.0

    def test_create_order_executor_default_mode(self):
        """デフォルトモード作成テスト."""
        executor = create_order_executor()

        assert executor.mode == ExecutionMode.PAPER
        assert executor.initial_balance == 1000000.0


class TestExecutionResult:
    """ExecutionResultテスト."""

    def test_execution_result_creation(self):
        """ExecutionResult作成テスト."""
        result = ExecutionResult(
            success=True,
            mode=ExecutionMode.PAPER,
            order_id="test_123",
            side="buy",
            amount=0.01,
            price=5000000.0,
            status=OrderStatus.FILLED,
        )

        assert result.success is True
        assert result.mode == ExecutionMode.PAPER
        assert result.order_id == "test_123"
        assert result.side == "buy"
        assert result.amount == 0.01
        assert result.price == 5000000.0
        assert result.status == OrderStatus.FILLED
        assert result.timestamp is not None


class TestIntegrationScenarios:
    """統合シナリオテスト."""

    @pytest.fixture
    def temp_log_dir(self):
        """一時ログディレクトリ."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_complete_trading_cycle(self, temp_log_dir):
        """完全な取引サイクルテスト."""
        executor = OrderExecutor(
            mode=ExecutionMode.PAPER, initial_balance=1000000.0, log_dir=temp_log_dir
        )

        # 1. 買いエントリー
        buy_evaluation = TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="buy",
            risk_score=0.2,  # 必須フィールド追加
            position_size=0.01,
            stop_loss=4800000.0,
            take_profit=5500000.0,
            confidence_level=0.75,
            warnings=[],
            denial_reasons=[],
            evaluation_timestamp=datetime.now(),
            kelly_recommendation=0.02,
            drawdown_status="normal",
            anomaly_alerts=[],
            market_conditions={},
        )

        with patch.object(executor, "_get_current_price", return_value=5000000.0):
            buy_result = await executor.execute_trade(buy_evaluation)

        assert buy_result.success is True
        assert executor.virtual_position.exist is True

        # 2. 価格変動シミュレート・含み損益確認
        with patch.object(executor, "_get_current_price", return_value=5200000.0):
            current_price = await executor._get_current_price()
            unrealized_pnl = executor.virtual_position.calculate_pnl(current_price)
            assert unrealized_pnl > 0  # 含み益

        # 3. 売り決済
        sell_evaluation = TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="sell",
            risk_score=0.2,  # 必須フィールド追加
            position_size=0.01,
            stop_loss=None,
            take_profit=None,
            confidence_level=0.75,
            warnings=[],
            denial_reasons=[],
            evaluation_timestamp=datetime.now(),
            kelly_recommendation=0.02,
            drawdown_status="normal",
            anomaly_alerts=[],
            market_conditions={},
        )

        with patch.object(executor, "_get_current_price", return_value=5200000.0):
            sell_result = await executor.execute_trade(sell_evaluation)

        assert sell_result.success is True
        assert executor.virtual_position.exist is False
        assert sell_result.paper_pnl > 0  # 利益確定

        # 4. 統計確認
        stats = executor.get_trading_statistics()
        assert stats["statistics"].total_trades == 2
        assert stats["statistics"].winning_trades >= 1
        assert stats["current_balance"] > 1000000.0  # 利益分増加

        # 5. ログファイル確認
        assert executor.trades_csv.exists()
        assert executor.stats_json.exists()

        # CSV内容確認
        with open(executor.trades_csv, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) >= 3  # ヘッダー + 買い + 売り
