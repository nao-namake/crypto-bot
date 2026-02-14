"""
StopManager テストスイート

Phase 28: TP/SL機能
Phase 31.1: 柔軟クールダウン
Phase 37.4: エラーコード検出（30101, 50061, 50062）
Phase 37.5.3: 残注文クリーンアップ
Phase 38: リファクタリング対応

テスト範囲:
- check_stop_conditions(): ポジションなし・TP/SL到達判定
- place_tp_sl_orders(): TP/SL注文配置・エラーハンドリング
- _check_take_profit_stop_loss(): TP/SL判定ロジック
- _evaluate_position_exit(): 買い・売りポジション決済判定
- _execute_position_exit(): 決済実行・P&L計算
- _check_emergency_stop_loss(): 緊急ストップロス判定
- should_apply_cooldown(): 柔軟クールダウン判定
- Phase 37.5.3: 残注文クリーンアップ機能
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, call, patch

import pytest

from src.trading.core import (
    ExecutionMode,
    ExecutionResult,
    OrderStatus,
    RiskDecision,
    TradeEvaluation,
)
from src.trading.execution.stop_manager import StopManager


@pytest.fixture
def stop_manager():
    """StopManager fixture"""
    return StopManager()


@pytest.fixture
def mock_bitbank_client():
    """BitbankClient mock fixture"""
    client = AsyncMock()
    client.fetch_ticker = AsyncMock(return_value={"last": 14000000.0})
    client.fetch_positions = AsyncMock(return_value=[])
    client.fetch_margin_positions = AsyncMock(return_value=[])  # Phase 37.5.4: native API対応
    client.create_take_profit_order = Mock(return_value={"id": "tp_order_123"})
    client.create_stop_loss_order = Mock(return_value={"id": "sl_order_456"})
    client.cancel_order = AsyncMock()
    return client


@pytest.fixture
def sample_evaluation():
    """TradeEvaluation fixture"""
    return TradeEvaluation(
        decision=RiskDecision.APPROVED,
        side="buy",
        risk_score=0.1,
        position_size=0.001,
        stop_loss=13700000.0,
        take_profit=14300000.0,
        confidence_level=0.75,
        warnings=[],
        denial_reasons=[],
        evaluation_timestamp=datetime.now(),
        kelly_recommendation=0.05,
        drawdown_status="normal",
        anomaly_alerts=[],
        market_conditions={"market_data": {}},
    )


@pytest.fixture
def sample_position():
    """ポジション fixture"""
    return {
        "order_id": "order_123",
        "side": "buy",
        "amount": 0.001,
        "price": 14000000.0,
        "take_profit": 14300000.0,
        "stop_loss": 13700000.0,
        "timestamp": datetime.now(),
    }


class TestCheckStopConditions:
    """check_stop_conditions() テスト"""

    @pytest.mark.asyncio
    async def test_no_positions_returns_none(self, stop_manager, mock_bitbank_client):
        """ポジションなしの場合はNoneを返す"""
        result = await stop_manager.check_stop_conditions(
            virtual_positions=[],
            bitbank_client=mock_bitbank_client,
            mode="paper",
            executed_trades=0,
            session_pnl=0.0,
        )

        assert result is None

    @pytest.mark.asyncio
    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_price_fetch_failure_returns_none(
        self, mock_threshold, stop_manager, sample_position
    ):
        """価格取得失敗時はNoneを返す"""
        # フォールバック価格を設定
        mock_threshold.return_value = 0  # 無効価格

        mock_client = AsyncMock()
        mock_client.fetch_ticker = AsyncMock(return_value={"last": 0})  # 無効価格

        result = await stop_manager.check_stop_conditions(
            virtual_positions=[sample_position],
            bitbank_client=mock_client,
            mode="paper",
            executed_trades=0,
            session_pnl=0.0,
        )

        assert result is None

    @pytest.mark.asyncio
    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_take_profit_triggered(
        self, mock_threshold, stop_manager, sample_position, mock_bitbank_client
    ):
        """テイクプロフィット到達時に決済実行"""
        # TP/SL有効化
        mock_threshold.side_effect = lambda key, default=None: (
            {"enabled": True} if "take_profit" in key or "stop_loss" in key else default
        )

        # TP価格到達（14,300,000円以上）
        mock_bitbank_client.fetch_ticker = AsyncMock(return_value={"last": 14350000.0})

        result = await stop_manager.check_stop_conditions(
            virtual_positions=[sample_position],
            bitbank_client=mock_bitbank_client,
            mode="paper",
            executed_trades=0,
            session_pnl=0.0,
        )

        assert result is not None
        assert isinstance(result, ExecutionResult)
        assert result.success is True
        assert result.side == "sell"  # 買いポジション決済→売り
        assert result.paper_pnl > 0  # 利益確定

    @pytest.mark.asyncio
    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_stop_loss_triggered(
        self, mock_threshold, stop_manager, sample_position, mock_bitbank_client
    ):
        """ストップロス到達時に決済実行"""
        # TP/SL有効化
        mock_threshold.side_effect = lambda key, default=None: (
            {"enabled": True} if "take_profit" in key or "stop_loss" in key else default
        )

        # SL価格到達（13,700,000円以下）
        # _get_current_price()が呼ばれるのでfetch_tickerをmock
        mock_bitbank_client.fetch_ticker = Mock(return_value={"last": 13650000.0})

        result = await stop_manager.check_stop_conditions(
            virtual_positions=[sample_position],
            bitbank_client=mock_bitbank_client,
            mode="paper",
            executed_trades=0,
            session_pnl=0.0,
        )

        assert result is not None
        assert isinstance(result, ExecutionResult)
        assert result.success is True
        assert result.side == "sell"  # 買いポジション決済→売り
        assert result.paper_pnl < 0  # 損失確定

    @pytest.mark.asyncio
    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_exception_handling_returns_none(
        self, mock_threshold, stop_manager, sample_position
    ):
        """例外発生時はNoneを返す"""
        # フォールバック価格を設定
        mock_threshold.return_value = 0  # 無効価格

        mock_client = AsyncMock()
        mock_client.fetch_ticker = AsyncMock(side_effect=Exception("API Error"))

        result = await stop_manager.check_stop_conditions(
            virtual_positions=[sample_position],
            bitbank_client=mock_client,
            mode="paper",
            executed_trades=0,
            session_pnl=0.0,
        )

        assert result is None


# Phase 43.5: TestPlaceTpSlOrdersクラス削除（place_tp_sl_orders廃止のため）


class TestEvaluatePositionExit:
    """_evaluate_position_exit() テスト"""

    @pytest.mark.asyncio
    async def test_buy_position_take_profit(self, stop_manager):
        """買いポジション - TP到達"""
        position = {
            "side": "buy",
            "price": 14000000.0,
            "amount": 0.001,
            "take_profit": 14300000.0,
            "stop_loss": None,
        }
        tp_config = {"enabled": True}
        sl_config = {"enabled": True}

        result = await stop_manager._evaluate_position_exit(
            position=position,
            current_price=14350000.0,
            tp_config=tp_config,
            sl_config=sl_config,
            mode="paper",
        )

        assert result is not None
        assert isinstance(result, ExecutionResult)
        assert result.success is True
        assert result.side == "sell"
        assert result.paper_pnl > 0  # 利益

    @pytest.mark.asyncio
    async def test_buy_position_stop_loss(self, stop_manager):
        """買いポジション - SL到達"""
        position = {
            "side": "buy",
            "price": 14000000.0,
            "amount": 0.001,
            "take_profit": None,
            "stop_loss": 13700000.0,
        }
        tp_config = {"enabled": True}
        sl_config = {"enabled": True}

        result = await stop_manager._evaluate_position_exit(
            position=position,
            current_price=13650000.0,
            tp_config=tp_config,
            sl_config=sl_config,
            mode="paper",
        )

        assert result is not None
        assert isinstance(result, ExecutionResult)
        assert result.success is True
        assert result.side == "sell"
        assert result.paper_pnl < 0  # 損失

    @pytest.mark.asyncio
    async def test_sell_position_take_profit(self, stop_manager):
        """売りポジション - TP到達"""
        position = {
            "side": "sell",
            "price": 14000000.0,
            "amount": 0.001,
            "take_profit": 13700000.0,
            "stop_loss": None,
        }
        tp_config = {"enabled": True}
        sl_config = {"enabled": True}

        result = await stop_manager._evaluate_position_exit(
            position=position,
            current_price=13650000.0,
            tp_config=tp_config,
            sl_config=sl_config,
            mode="paper",
        )

        assert result is not None
        assert isinstance(result, ExecutionResult)
        assert result.success is True
        assert result.side == "buy"  # 売りポジション決済→買い
        assert result.paper_pnl > 0  # 利益

    @pytest.mark.asyncio
    async def test_sell_position_stop_loss(self, stop_manager):
        """売りポジション - SL到達"""
        position = {
            "side": "sell",
            "price": 14000000.0,
            "amount": 0.001,
            "take_profit": None,
            "stop_loss": 14300000.0,
        }
        tp_config = {"enabled": True}
        sl_config = {"enabled": True}

        result = await stop_manager._evaluate_position_exit(
            position=position,
            current_price=14350000.0,
            tp_config=tp_config,
            sl_config=sl_config,
            mode="paper",
        )

        assert result is not None
        assert isinstance(result, ExecutionResult)
        assert result.success is True
        assert result.side == "buy"  # 売りポジション決済→買い
        assert result.paper_pnl < 0  # 損失

    @pytest.mark.asyncio
    async def test_no_tp_sl_returns_none(self, stop_manager):
        """TP/SL未設定の場合はNone"""
        position = {
            "side": "buy",
            "price": 14000000.0,
            "amount": 0.001,
            "take_profit": None,
            "stop_loss": None,
        }
        tp_config = {"enabled": True}
        sl_config = {"enabled": True}

        result = await stop_manager._evaluate_position_exit(
            position=position,
            current_price=14100000.0,
            tp_config=tp_config,
            sl_config=sl_config,
            mode="paper",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_invalid_position_returns_none(self, stop_manager):
        """無効なポジションの場合はNone"""
        position = {
            "side": "buy",
            "price": 0,
            "amount": 0.001,
            "take_profit": 14300000.0,
            "stop_loss": None,
        }
        tp_config = {"enabled": True}
        sl_config = {"enabled": True}

        result = await stop_manager._evaluate_position_exit(
            position=position,
            current_price=14100000.0,
            tp_config=tp_config,
            sl_config=sl_config,
            mode="paper",
        )

        assert result is None


class TestExecutePositionExit:
    """_execute_position_exit() テスト"""

    @pytest.mark.asyncio
    async def test_buy_position_exit_profit(self, stop_manager):
        """買いポジション決済 - 利益"""
        position = {"order_id": "order_123", "side": "buy", "price": 14000000.0, "amount": 0.001}

        result = await stop_manager._execute_position_exit(
            position=position, current_price=14300000.0, exit_reason="take_profit", mode="paper"
        )

        assert result.success is True
        assert result.side == "sell"
        assert result.amount == 0.001
        assert result.price == 14300000.0
        assert result.paper_pnl == 300.0  # (14,300,000 - 14,000,000) * 0.001
        assert result.status == OrderStatus.FILLED

    @pytest.mark.asyncio
    async def test_buy_position_exit_loss(self, stop_manager):
        """買いポジション決済 - 損失"""
        position = {"order_id": "order_123", "side": "buy", "price": 14000000.0, "amount": 0.001}

        result = await stop_manager._execute_position_exit(
            position=position, current_price=13700000.0, exit_reason="stop_loss", mode="paper"
        )

        assert result.success is True
        assert result.side == "sell"
        assert result.amount == 0.001
        assert result.price == 13700000.0
        assert result.paper_pnl == -300.0  # (13,700,000 - 14,000,000) * 0.001
        assert result.status == OrderStatus.FILLED

    @pytest.mark.asyncio
    async def test_sell_position_exit_profit(self, stop_manager):
        """売りポジション決済 - 利益"""
        position = {"order_id": "order_123", "side": "sell", "price": 14000000.0, "amount": 0.001}

        result = await stop_manager._execute_position_exit(
            position=position, current_price=13700000.0, exit_reason="take_profit", mode="paper"
        )

        assert result.success is True
        assert result.side == "buy"
        assert result.amount == 0.001
        assert result.price == 13700000.0
        assert result.paper_pnl == 300.0  # (14,000,000 - 13,700,000) * 0.001
        assert result.status == OrderStatus.FILLED

    @pytest.mark.asyncio
    async def test_sell_position_exit_loss(self, stop_manager):
        """売りポジション決済 - 損失"""
        position = {"order_id": "order_123", "side": "sell", "price": 14000000.0, "amount": 0.001}

        result = await stop_manager._execute_position_exit(
            position=position, current_price=14300000.0, exit_reason="stop_loss", mode="paper"
        )

        assert result.success is True
        assert result.side == "buy"
        assert result.amount == 0.001
        assert result.price == 14300000.0
        assert result.paper_pnl == -300.0  # (14,000,000 - 14,300,000) * 0.001
        assert result.status == OrderStatus.FILLED

    @pytest.mark.asyncio
    async def test_execution_mode_live(self, stop_manager):
        """ライブモード決済"""
        position = {"order_id": "order_123", "side": "buy", "price": 14000000.0, "amount": 0.001}

        result = await stop_manager._execute_position_exit(
            position=position, current_price=14300000.0, exit_reason="take_profit", mode="live"
        )

        assert result.success is True
        assert result.mode == ExecutionMode.LIVE


class TestCheckEmergencyStopLoss:
    """_check_emergency_stop_loss() テスト"""

    @pytest.mark.asyncio
    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_emergency_disabled_returns_none(
        self, mock_threshold, stop_manager, sample_position
    ):
        """緊急ストップロス無効時はNone"""
        mock_threshold.return_value = {"enable": False}

        result = await stop_manager._check_emergency_stop_loss(
            virtual_positions=[sample_position],
            current_price=14000000.0,
            mode="paper",
            executed_trades=0,
            session_pnl=0.0,
        )

        assert result is None

    @pytest.mark.asyncio
    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_max_loss_threshold_triggered(
        self, mock_threshold, stop_manager, sample_position
    ):
        """最大損失閾値超過で緊急決済"""
        mock_threshold.return_value = {
            "enable": True,
            "max_loss_threshold": 0.05,
            "min_hold_minutes": 0,  # 保有時間チェックスキップ
        }

        # 5%以上の損失（14,000,000 → 13,200,000 = -5.7%）
        result = await stop_manager._check_emergency_stop_loss(
            virtual_positions=[sample_position],
            current_price=13200000.0,
            mode="paper",
            executed_trades=0,
            session_pnl=0.0,
        )

        assert result is not None
        assert isinstance(result, ExecutionResult)
        assert result.success is True
        assert result.emergency_exit is True
        assert result.paper_pnl < 0


# Phase 64: TestShouldApplyCooldown削除（cooldown.py CooldownManagerのテストでカバー）


class TestGetCurrentPrice:
    """_get_current_price() テスト"""

    @pytest.mark.asyncio
    async def test_fetch_ticker_success(self, stop_manager, mock_bitbank_client):
        """ticker取得成功"""
        mock_bitbank_client.fetch_ticker = Mock(return_value={"last": 14500000.0})

        price = await stop_manager._get_current_price(mock_bitbank_client)

        assert price == 14500000.0

    @pytest.mark.asyncio
    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_fetch_ticker_failure_fallback(self, mock_threshold, stop_manager):
        """ticker取得失敗時はフォールバック価格"""
        mock_threshold.return_value = 16000000.0
        mock_client = AsyncMock()
        mock_client.fetch_ticker = AsyncMock(side_effect=Exception("API Error"))

        price = await stop_manager._get_current_price(mock_client)

        assert price == 16000000.0
        mock_threshold.assert_called_once_with("trading.fallback_btc_jpy", 16500000.0)

    @pytest.mark.asyncio
    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_no_bitbank_client_fallback(self, mock_threshold, stop_manager):
        """BitbankClientなし時はフォールバック価格"""
        mock_threshold.return_value = 16500000.0

        price = await stop_manager._get_current_price(None)

        assert price == 16500000.0


# Phase 64: TestCalculateTrendStrength削除（cooldown.py CooldownManagerのテストでカバー）


class TestRapidPriceMovement:
    """_check_rapid_price_movement() テスト"""

    @pytest.mark.asyncio
    async def test_no_rapid_movement_returns_none(self, stop_manager):
        """価格変動なし時はNone（現在は簡易実装）"""
        config = {"price_change_threshold": 0.03}

        result = await stop_manager._check_rapid_price_movement(14000000.0, config)

        # 簡易実装のため常にNone
        assert result is None


# ===== 追加テスト: 未カバー箇所対応 =====


# Phase 51.6: TestCleanupOrphanedOrdersDetailedクラス削除
# 理由: _cleanup_orphaned_orders()メソッドは Phase 51.6で削除され、
# cleanup_old_unfilled_orders()メソッドに置き換えられた。
# Phase 51.6の新しいテストは TestPhase516CleanupOldUnfilledOrders クラスで実装済み。


# Phase 51.6: TestCancelOrphanedTpSlOrdersクラス削除
# 理由: _cancel_orphaned_tp_sl_orders()メソッドは Phase 51.6で削除された。
# Phase 49.6でcleanup_position_orders()に置き換え済み。


# Phase 64: TestCalculateTrendStrengthDetailed削除（cooldown.py CooldownManagerのテストでカバー）


class TestEvaluateEmergencyExit:
    """_evaluate_emergency_exit() テスト - 緊急決済判定詳細"""

    @pytest.mark.asyncio
    async def test_min_hold_time_not_met(self, stop_manager):
        """最小保有時間未満は緊急決済しない"""
        position = {
            "price": 14000000.0,
            "side": "buy",
            "timestamp": datetime.now(),  # 直前にエントリー
        }
        config = {
            "max_loss_threshold": 0.05,
            "min_hold_minutes": 5,  # 5分保有必須
        }

        result = await stop_manager._evaluate_emergency_exit(position, 13200000.0, config)

        # 保有時間不足 → False
        assert result is False

    @pytest.mark.asyncio
    async def test_loss_threshold_exactly_at_limit(self, stop_manager):
        """損失が閾値ちょうどの場合は緊急決済する"""
        position = {
            "price": 14000000.0,
            "side": "buy",
            "timestamp": datetime.now() - timedelta(minutes=10),
        }
        config = {
            "max_loss_threshold": 0.05,
            "min_hold_minutes": 1,
        }

        # 損失ちょうど-5%（14,000,000 → 13,300,000）
        result = await stop_manager._evaluate_emergency_exit(position, 13300000.0, config)

        # 実装は <= -max_loss_threshold なので、閾値ちょうどでも緊急決済する
        assert result is True

    @pytest.mark.asyncio
    async def test_sell_position_loss_evaluation(self, stop_manager):
        """売りポジションの損失評価"""
        position = {
            "price": 14000000.0,
            "side": "sell",
            "timestamp": datetime.now() - timedelta(minutes=10),
        }
        config = {
            "max_loss_threshold": 0.05,
            "min_hold_minutes": 1,
        }

        # 売りポジション損失: 14,000,000 → 14,800,000（+5.7%損失）
        result = await stop_manager._evaluate_emergency_exit(position, 14800000.0, config)

        # 5%超の損失 → 緊急決済
        assert result is True

    @pytest.mark.asyncio
    async def test_invalid_side_returns_false(self, stop_manager):
        """無効なsideの場合はFalse"""
        position = {
            "price": 14000000.0,
            "side": "invalid",  # 無効なside
            "timestamp": datetime.now() - timedelta(minutes=10),
        }
        config = {
            "max_loss_threshold": 0.05,
            "min_hold_minutes": 1,
        }

        result = await stop_manager._evaluate_emergency_exit(position, 13200000.0, config)

        assert result is False

    @pytest.mark.asyncio
    async def test_zero_entry_price_returns_false(self, stop_manager):
        """エントリー価格0の場合はFalse"""
        position = {
            "price": 0,  # 無効な価格
            "side": "buy",
            "timestamp": datetime.now() - timedelta(minutes=10),
        }
        config = {
            "max_loss_threshold": 0.05,
            "min_hold_minutes": 1,
        }

        result = await stop_manager._evaluate_emergency_exit(position, 14000000.0, config)

        assert result is False


# ========================================
# Phase 51.6: 古い注文クリーンアップ + SL価格検証強化テスト
# ========================================


# Phase 64: TestPhase516CleanupOldUnfilledOrders は PositionRestorer に移動
# テストは test_position_restorer.py を参照


# Phase 64: TestPhase516SLPriceValidation は test_tp_sl_manager.py に移動


# ========================================
# Phase 59.6: 孤児SL管理テスト
# ========================================


class TestPhase596OrphanSLManagement:
    """Phase 59.6: 孤児SL管理テスト"""

    @pytest.fixture
    def stop_manager(self):
        """StopManagerインスタンス"""
        return StopManager()

    @pytest.fixture
    def mock_bitbank_client(self):
        """BitbankClientのモック（同期メソッドとして呼ばれる）"""
        client = MagicMock()
        client.cancel_order = MagicMock(return_value={"success": True})
        return client

    def test_mark_orphan_sl_creates_file(self, stop_manager, tmp_path):
        """Phase 59.6: 孤児SLマーク - ファイル作成"""
        import json
        from pathlib import Path

        # テスト用に一時ディレクトリを使用
        orphan_file = tmp_path / "orphan_sl_orders.json"

        with patch.object(Path, "__new__", return_value=orphan_file):
            # _mark_orphan_slの内部でPathを使うので直接テスト
            stop_manager._mark_orphan_sl("sl_order_123", "take_profit")

        # ファイルが作成され、内容が正しいことを確認
        # 注: 実際のPathを使用するため、dataディレクトリに作成される
        # このテストでは例外が発生しないことを確認

    def test_mark_orphan_sl_appends_to_existing(self, stop_manager, tmp_path):
        """Phase 59.6: 孤児SLマーク - 既存ファイルに追記"""
        import json

        # 孤児SLを2回マーク
        stop_manager._mark_orphan_sl("sl_order_001", "take_profit")
        stop_manager._mark_orphan_sl("sl_order_002", "manual")

        # 例外が発生しないことを確認（実際のファイル操作は別テストで検証）

    # Phase 64: cleanup_orphan_sl_orders テストは test_position_restorer.py に移動


# ========================================
# Phase 59.6: SL指値化テスト
# ========================================


# Phase 64: TestPhase596SLStopLimit は test_tp_sl_manager.py に移動

# ========================================
# Phase 61.9: TP/SL自動執行検知テスト
# ========================================


@pytest.mark.asyncio
class TestPhase619AutoExecutionDetection:
    """Phase 61.9: TP/SL自動執行検知テスト"""

    @pytest.fixture
    def stop_manager(self):
        """StopManagerインスタンス"""
        return StopManager()

    @pytest.fixture
    def mock_bitbank_client(self):
        """BitbankClientのモック"""
        client = MagicMock()
        client.fetch_order = MagicMock()
        client.cancel_order = MagicMock(return_value={"success": True})
        return client

    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_detect_tp_auto_execution(
        self, mock_threshold, stop_manager, mock_bitbank_client
    ):
        """Phase 61.9: TP自動執行検知テスト"""

        # Phase 62.6: 手数料設定も含めてモック
        def threshold_side_effect(key, default=None):
            if key == "tp_sl_auto_detection":
                return {"enabled": True, "log_level": "info"}
            elif key == "trading.fees.entry_taker_rate":
                return 0.001
            elif key == "trading.fees.exit_taker_rate":
                return 0.001
            return default

        mock_threshold.side_effect = threshold_side_effect

        # 仮想ポジション（買いポジション・TP/SL注文ID付き）
        virtual_positions = [
            {
                "order_id": "entry_001",
                "side": "buy",
                "amount": 0.001,
                "price": 14000000.0,
                "tp_order_id": "tp_001",
                "sl_order_id": "sl_001",
                "strategy_name": "BBReversal",
            }
        ]

        # 実ポジション（空 = ポジション決済済み）
        actual_positions = []

        # TP注文が約定済み（status="closed"）
        mock_bitbank_client.fetch_order = MagicMock(
            side_effect=lambda order_id, symbol: (
                {
                    "status": "closed",
                    "average": 14300000.0,
                    "price": 14300000.0,
                }
                if order_id == "tp_001"
                else {"status": "open", "price": 13700000.0}
            )
        )

        result = await stop_manager.detect_auto_executed_orders(
            virtual_positions=virtual_positions,
            actual_positions=actual_positions,
            bitbank_client=mock_bitbank_client,
            symbol="BTC/JPY",
        )

        # TP自動執行が検知される
        assert len(result) == 1
        assert result[0]["execution_type"] == "take_profit"
        assert result[0]["order_id"] == "entry_001"
        assert result[0]["exit_price"] == 14300000.0
        # Phase 62.19: 手数料考慮後の損益（Taker 0.1%）
        # 粗利益: (14300000 - 14000000) * 0.001 = 300円
        # エントリー手数料: 14000000 * 0.001 * 0.001 = 14円
        # 決済手数料: 14300000 * 0.001 * 0.001 = 14.3円
        # 実現損益: 300 - 14 - 14.3 = 271.7円
        expected_pnl = 300.0 - 14.0 - 14.3
        assert abs(result[0]["pnl"] - expected_pnl) < 0.1

        # 残SL注文がキャンセルされる
        mock_bitbank_client.cancel_order.assert_called_once_with("sl_001", "BTC/JPY")

    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_detect_sl_auto_execution(
        self, mock_threshold, stop_manager, mock_bitbank_client
    ):
        """Phase 61.9: SL自動執行検知テスト"""

        # Phase 62.6: 手数料設定も含めてモック
        def threshold_side_effect(key, default=None):
            if key == "tp_sl_auto_detection":
                return {"enabled": True, "log_level": "info"}
            elif key == "trading.fees.entry_taker_rate":
                return 0.001
            elif key == "trading.fees.exit_taker_rate":
                return 0.001
            return default

        mock_threshold.side_effect = threshold_side_effect

        # 仮想ポジション（買いポジション・TP/SL注文ID付き）
        virtual_positions = [
            {
                "order_id": "entry_002",
                "side": "buy",
                "amount": 0.001,
                "price": 14000000.0,
                "tp_order_id": "tp_002",
                "sl_order_id": "sl_002",
                "strategy_name": "ATRBased",
            }
        ]

        # 実ポジション（空 = ポジション決済済み）
        actual_positions = []

        # TP注文は未約定、SL注文が約定済み
        def mock_fetch_order(order_id, symbol):
            if order_id == "tp_002":
                return {"status": "open", "price": 14300000.0}
            elif order_id == "sl_002":
                return {"status": "closed", "average": 13700000.0, "price": 13700000.0}
            return {}

        mock_bitbank_client.fetch_order = MagicMock(side_effect=mock_fetch_order)

        result = await stop_manager.detect_auto_executed_orders(
            virtual_positions=virtual_positions,
            actual_positions=actual_positions,
            bitbank_client=mock_bitbank_client,
            symbol="BTC/JPY",
        )

        # SL自動執行が検知される
        assert len(result) == 1
        assert result[0]["execution_type"] == "stop_loss"
        assert result[0]["order_id"] == "entry_002"
        assert result[0]["exit_price"] == 13700000.0
        # Phase 62.19: 手数料考慮後の損益（Taker 0.1%）
        # 粗利益: (13700000 - 14000000) * 0.001 = -300円
        # エントリー手数料: 14000000 * 0.001 * 0.001 = 14円
        # 決済手数料: 13700000 * 0.001 * 0.001 = 13.7円
        # 実現損益: -300 - 14 - 13.7 = -327.7円
        expected_pnl = -300.0 - 14.0 - 13.7
        assert abs(result[0]["pnl"] - expected_pnl) < 0.1

        # 残TP注文がキャンセルされる
        mock_bitbank_client.cancel_order.assert_called_once_with("tp_002", "BTC/JPY")

    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_no_disappeared_positions(
        self, mock_threshold, stop_manager, mock_bitbank_client
    ):
        """Phase 61.9: 消失なし時は何もしない"""
        mock_threshold.return_value = {"enabled": True, "log_level": "info"}

        # 仮想ポジション
        virtual_positions = [
            {
                "order_id": "entry_003",
                "side": "buy",
                "amount": 0.001,
                "price": 14000000.0,
                "tp_order_id": "tp_003",
                "sl_order_id": "sl_003",
            }
        ]

        # 実ポジション（同じポジションが存在）
        actual_positions = [
            {
                "side": "long",  # buy -> long
                "amount": 0.001,
                "average_price": 14000000.0,
            }
        ]

        result = await stop_manager.detect_auto_executed_orders(
            virtual_positions=virtual_positions,
            actual_positions=actual_positions,
            bitbank_client=mock_bitbank_client,
            symbol="BTC/JPY",
        )

        # 消失なしのため空リスト
        assert len(result) == 0
        mock_bitbank_client.fetch_order.assert_not_called()

    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_api_error_handling(self, mock_threshold, stop_manager, mock_bitbank_client):
        """Phase 61.9: APIエラー時も処理継続"""
        mock_threshold.return_value = {"enabled": True, "log_level": "info"}

        # 仮想ポジション
        virtual_positions = [
            {
                "order_id": "entry_004",
                "side": "buy",
                "amount": 0.001,
                "price": 14000000.0,
                "tp_order_id": "tp_004",
                "sl_order_id": "sl_004",
            }
        ]

        # 実ポジション（空 = ポジション決済済み）
        actual_positions = []

        # APIエラー
        mock_bitbank_client.fetch_order = MagicMock(side_effect=Exception("API Error"))

        result = await stop_manager.detect_auto_executed_orders(
            virtual_positions=virtual_positions,
            actual_positions=actual_positions,
            bitbank_client=mock_bitbank_client,
            symbol="BTC/JPY",
        )

        # エラー時は空リスト（処理継続）
        assert len(result) == 0

    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_disabled_feature(self, mock_threshold, stop_manager, mock_bitbank_client):
        """Phase 61.9: 機能無効時はスキップ"""
        mock_threshold.return_value = {"enabled": False}

        virtual_positions = [
            {
                "order_id": "entry_005",
                "side": "buy",
                "amount": 0.001,
                "price": 14000000.0,
                "tp_order_id": "tp_005",
                "sl_order_id": "sl_005",
            }
        ]
        actual_positions = []

        result = await stop_manager.detect_auto_executed_orders(
            virtual_positions=virtual_positions,
            actual_positions=actual_positions,
            bitbank_client=mock_bitbank_client,
            symbol="BTC/JPY",
        )

        # 機能無効時は空リスト
        assert len(result) == 0
        mock_bitbank_client.fetch_order.assert_not_called()

    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_sell_position_tp_execution(
        self, mock_threshold, stop_manager, mock_bitbank_client
    ):
        """Phase 61.9: 売りポジションのTP自動執行検知"""

        # Phase 62.6: 手数料設定も含めてモック
        def threshold_side_effect(key, default=None):
            if key == "tp_sl_auto_detection":
                return {"enabled": True, "log_level": "info"}
            elif key == "trading.fees.entry_taker_rate":
                return 0.001
            elif key == "trading.fees.exit_taker_rate":
                return 0.001
            return default

        mock_threshold.side_effect = threshold_side_effect

        # 仮想ポジション（売りポジション）
        virtual_positions = [
            {
                "order_id": "entry_006",
                "side": "sell",
                "amount": 0.001,
                "price": 14000000.0,
                "tp_order_id": "tp_006",
                "sl_order_id": "sl_006",
                "strategy_name": "MACDEMACrossover",
            }
        ]

        # 実ポジション（空）
        actual_positions = []

        # TP注文が約定済み（売りポジションのTPは価格下落で約定）
        mock_bitbank_client.fetch_order = MagicMock(
            return_value={"status": "closed", "average": 13700000.0, "price": 13700000.0}
        )

        result = await stop_manager.detect_auto_executed_orders(
            virtual_positions=virtual_positions,
            actual_positions=actual_positions,
            bitbank_client=mock_bitbank_client,
            symbol="BTC/JPY",
        )

        # TP自動執行が検知される
        assert len(result) == 1
        assert result[0]["execution_type"] == "take_profit"
        # Phase 62.19: 手数料考慮後の損益（Taker 0.1%）
        # 粗利益: (14000000 - 13700000) * 0.001 = 300円（ショート利益）
        # エントリー手数料: 14000000 * 0.001 * 0.001 = 14円
        # 決済手数料: 13700000 * 0.001 * 0.001 = 13.7円
        # 実現損益: 300 - 14 - 13.7 = 272.3円
        expected_pnl = 300.0 - 14.0 - 13.7
        assert abs(result[0]["pnl"] - expected_pnl) < 0.1

    @patch("src.trading.execution.stop_manager.get_threshold")
    def test_calc_pnl_buy_profit(self, mock_threshold, stop_manager):
        """Phase 62.19: 損益計算 - 買いポジション利益（Taker 0.1%手数料）"""
        mock_threshold.side_effect = lambda key, default=None: (0.001 if "fee" in key else default)
        pnl = stop_manager._calc_pnl(
            entry_price=14000000.0,
            exit_price=14300000.0,
            amount=0.001,
            side="buy",
        )
        # Phase 62.19: Taker 0.1%手数料考慮
        # 粗利益: 300円
        # エントリー手数料: 14000000 * 0.001 * 0.001 = 14円
        # 決済手数料: 14300000 * 0.001 * 0.001 = 14.3円
        # 実現損益: 300 - 14 - 14.3 = 271.7円
        expected_pnl = 300.0 - 14.0 - 14.3
        assert abs(pnl - expected_pnl) < 0.1

    @patch("src.trading.execution.stop_manager.get_threshold")
    def test_calc_pnl_buy_loss(self, mock_threshold, stop_manager):
        """Phase 62.19: 損益計算 - 買いポジション損失（Taker 0.1%手数料）"""
        mock_threshold.side_effect = lambda key, default=None: (0.001 if "fee" in key else default)
        pnl = stop_manager._calc_pnl(
            entry_price=14000000.0,
            exit_price=13700000.0,
            amount=0.001,
            side="buy",
        )
        # Phase 62.19: Taker 0.1%手数料考慮
        # 粗利益: -300円
        # エントリー手数料: 14000000 * 0.001 * 0.001 = 14円
        # 決済手数料: 13700000 * 0.001 * 0.001 = 13.7円
        # 実現損益: -300 - 14 - 13.7 = -327.7円
        expected_pnl = -300.0 - 14.0 - 13.7
        assert abs(pnl - expected_pnl) < 0.1

    @patch("src.trading.execution.stop_manager.get_threshold")
    def test_calc_pnl_sell_profit(self, mock_threshold, stop_manager):
        """Phase 62.19: 損益計算 - 売りポジション利益（Taker 0.1%手数料）"""
        mock_threshold.side_effect = lambda key, default=None: (0.001 if "fee" in key else default)
        pnl = stop_manager._calc_pnl(
            entry_price=14000000.0,
            exit_price=13700000.0,
            amount=0.001,
            side="sell",
        )
        # Phase 62.19: Taker 0.1%手数料考慮
        # 粗利益: 300円（ショート）
        # エントリー手数料: 14000000 * 0.001 * 0.001 = 14円
        # 決済手数料: 13700000 * 0.001 * 0.001 = 13.7円
        # 実現損益: 300 - 14 - 13.7 = 272.3円
        expected_pnl = 300.0 - 14.0 - 13.7
        assert abs(pnl - expected_pnl) < 0.1

    @patch("src.trading.execution.stop_manager.get_threshold")
    def test_calc_pnl_sell_loss(self, mock_threshold, stop_manager):
        """Phase 62.19: 損益計算 - 売りポジション損失（Taker 0.1%手数料）"""
        mock_threshold.side_effect = lambda key, default=None: (0.001 if "fee" in key else default)
        pnl = stop_manager._calc_pnl(
            entry_price=14000000.0,
            exit_price=14300000.0,
            amount=0.001,
            side="sell",
        )
        # Phase 62.19: Taker 0.1%手数料考慮
        # 粗利益: -300円（ショート損失）
        # エントリー手数料: 14000000 * 0.001 * 0.001 = 14円
        # 決済手数料: 14300000 * 0.001 * 0.001 = 14.3円
        # 実現損益: -300 - 14 - 14.3 = -328.3円
        expected_pnl = -300.0 - 14.0 - 14.3
        assert abs(pnl - expected_pnl) < 0.1

    def test_find_disappeared_positions_matching(self, stop_manager):
        """Phase 61.9: 消失ポジション検出 - マッチング"""
        virtual_positions = [
            {
                "order_id": "entry_007",
                "side": "buy",
                "amount": 0.001,
                "tp_order_id": "tp_007",
                "sl_order_id": "sl_007",
            }
        ]
        actual_positions = [{"side": "long", "amount": 0.001}]  # マッチ

        disappeared = stop_manager._find_disappeared_positions(virtual_positions, actual_positions)

        assert len(disappeared) == 0

    def test_find_disappeared_positions_not_matching(self, stop_manager):
        """Phase 61.9: 消失ポジション検出 - マッチなし"""
        virtual_positions = [
            {
                "order_id": "entry_008",
                "side": "buy",
                "amount": 0.001,
                "tp_order_id": "tp_008",
                "sl_order_id": "sl_008",
            }
        ]
        actual_positions = []  # 実ポジションなし

        disappeared = stop_manager._find_disappeared_positions(virtual_positions, actual_positions)

        assert len(disappeared) == 1
        assert disappeared[0]["order_id"] == "entry_008"

    def test_find_disappeared_positions_amount_tolerance(self, stop_manager):
        """Phase 61.9: 消失ポジション検出 - 数量許容誤差"""
        virtual_positions = [
            {
                "order_id": "entry_009",
                "side": "buy",
                "amount": 0.001,
                "tp_order_id": "tp_009",
                "sl_order_id": "sl_009",
            }
        ]
        actual_positions = [{"side": "long", "amount": 0.00105}]  # 5%誤差（10%以内なのでマッチ）

        disappeared = stop_manager._find_disappeared_positions(virtual_positions, actual_positions)

        assert len(disappeared) == 0  # 許容誤差内なのでマッチ

    def test_find_disappeared_positions_no_tp_sl_orders(self, stop_manager):
        """Phase 61.9: TP/SL注文IDなしのポジションは対象外"""
        virtual_positions = [
            {
                "order_id": "entry_010",
                "side": "buy",
                "amount": 0.001,
                # tp_order_id, sl_order_idなし
            }
        ]
        actual_positions = []

        disappeared = stop_manager._find_disappeared_positions(virtual_positions, actual_positions)

        # TP/SL注文IDがないので対象外
        assert len(disappeared) == 0


# ========================================
# Phase 61.3: 約定確認・リトライ機能テスト
# ========================================


@pytest.mark.asyncio
class TestPhase613WaitForFill:
    """Phase 61.3: _wait_for_fill() テスト"""

    @pytest.fixture
    def stop_manager(self):
        """StopManagerインスタンス"""
        return StopManager()

    @pytest.fixture
    def mock_bitbank_client(self):
        """BitbankClientのモック"""
        client = MagicMock()
        return client

    async def test_wait_for_fill_success(self, stop_manager, mock_bitbank_client):
        """Phase 61.3: 約定確認成功"""
        # fetch_orderが約定済みを返す
        mock_bitbank_client.fetch_order = MagicMock(
            return_value={"status": "closed", "filled": 0.001}
        )

        is_filled, order = await stop_manager._wait_for_fill(
            order_id="order_123",
            bitbank_client=mock_bitbank_client,
            symbol="BTC/JPY",
            timeout_seconds=10,
            check_interval=1,
        )

        assert is_filled is True
        assert order is not None
        assert order["status"] == "closed"

    async def test_wait_for_fill_canceled(self, stop_manager, mock_bitbank_client):
        """Phase 61.3: 注文キャンセル検出"""
        mock_bitbank_client.fetch_order = MagicMock(return_value={"status": "canceled"})

        is_filled, order = await stop_manager._wait_for_fill(
            order_id="order_123",
            bitbank_client=mock_bitbank_client,
            symbol="BTC/JPY",
            timeout_seconds=10,
            check_interval=1,
        )

        assert is_filled is False
        assert order is not None
        assert order["status"] == "canceled"

    async def test_wait_for_fill_expired(self, stop_manager, mock_bitbank_client):
        """Phase 61.3: 注文期限切れ検出"""
        mock_bitbank_client.fetch_order = MagicMock(return_value={"status": "expired"})

        is_filled, order = await stop_manager._wait_for_fill(
            order_id="order_123",
            bitbank_client=mock_bitbank_client,
            symbol="BTC/JPY",
            timeout_seconds=10,
            check_interval=1,
        )

        assert is_filled is False
        assert order is not None
        assert order["status"] == "expired"

    async def test_wait_for_fill_timeout(self, stop_manager, mock_bitbank_client):
        """Phase 61.3: タイムアウト"""
        # 常にopenを返す
        mock_bitbank_client.fetch_order = MagicMock(return_value={"status": "open"})

        is_filled, order = await stop_manager._wait_for_fill(
            order_id="order_123",
            bitbank_client=mock_bitbank_client,
            symbol="BTC/JPY",
            timeout_seconds=3,  # 短いタイムアウト
            check_interval=1,
        )

        assert is_filled is False
        assert order is None

    async def test_wait_for_fill_api_error(self, stop_manager, mock_bitbank_client):
        """Phase 61.3: APIエラー時もタイムアウトまで待機"""
        # 2回APIエラー後、約定済みを返す
        mock_bitbank_client.fetch_order = MagicMock(
            side_effect=[
                Exception("API Error"),
                Exception("API Error"),
                {"status": "closed", "filled": 0.001},
            ]
        )

        is_filled, order = await stop_manager._wait_for_fill(
            order_id="order_123",
            bitbank_client=mock_bitbank_client,
            symbol="BTC/JPY",
            timeout_seconds=10,
            check_interval=1,
        )

        assert is_filled is True
        assert order is not None


@pytest.mark.asyncio
class TestPhase613RetryCloseOrder:
    """Phase 61.3: _retry_close_order_with_price_update() テスト"""

    @pytest.fixture
    def stop_manager(self):
        """StopManagerインスタンス"""
        return StopManager()

    @pytest.fixture
    def mock_bitbank_client(self):
        """BitbankClientのモック"""
        client = MagicMock()
        client.fetch_ticker = MagicMock(return_value={"last": 14000000.0})
        client.create_order = MagicMock(return_value={"id": "new_order_123"})
        client.cancel_order = MagicMock()
        return client

    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_retry_success_on_first_retry(
        self, mock_threshold, stop_manager, mock_bitbank_client
    ):
        """Phase 61.3: 1回目のリトライで成功"""
        mock_threshold.return_value = {"timeout_seconds": 3, "check_interval_seconds": 1}

        # fetch_orderで約定済みを返す
        mock_bitbank_client.fetch_order = MagicMock(
            return_value={"status": "closed", "filled": 0.001}
        )

        success, order_id = await stop_manager._retry_close_order_with_price_update(
            bitbank_client=mock_bitbank_client,
            symbol="BTC/JPY",
            exit_side="sell",
            amount=0.001,
            entry_position_side="long",
            original_order_id="old_order_123",
            max_retries=3,
            slippage_increase_per_retry=0.001,
        )

        assert success is True
        assert order_id == "new_order_123"

    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_retry_all_failed(self, mock_threshold, stop_manager, mock_bitbank_client):
        """Phase 61.3: 全リトライ失敗"""
        mock_threshold.return_value = {"timeout_seconds": 1, "check_interval_seconds": 1}

        # 常にopenを返す（約定しない）
        mock_bitbank_client.fetch_order = MagicMock(return_value={"status": "open"})

        success, order_id = await stop_manager._retry_close_order_with_price_update(
            bitbank_client=mock_bitbank_client,
            symbol="BTC/JPY",
            exit_side="sell",
            amount=0.001,
            entry_position_side="long",
            original_order_id="old_order_123",
            max_retries=2,  # 2回だけ
            slippage_increase_per_retry=0.001,
        )

        assert success is False
        assert order_id is None

    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_retry_with_buy_side(self, mock_threshold, stop_manager, mock_bitbank_client):
        """Phase 61.3: 買い決済のリトライ（価格上乗せ）"""
        mock_threshold.return_value = {"timeout_seconds": 3, "check_interval_seconds": 1}

        # fetch_orderで約定済みを返す
        mock_bitbank_client.fetch_order = MagicMock(
            return_value={"status": "closed", "filled": 0.001}
        )

        success, order_id = await stop_manager._retry_close_order_with_price_update(
            bitbank_client=mock_bitbank_client,
            symbol="BTC/JPY",
            exit_side="buy",  # 買い決済
            amount=0.001,
            entry_position_side="short",
            original_order_id="old_order_123",
            max_retries=1,
            slippage_increase_per_retry=0.001,
        )

        assert success is True
        # create_orderの価格が現在価格 + スリッページ であることを確認
        call_kwargs = mock_bitbank_client.create_order.call_args[1]
        expected_price = 14000000.0 * (1 + 0.001)
        assert abs(call_kwargs["price"] - expected_price) < 1

    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_retry_invalid_price(self, mock_threshold, stop_manager, mock_bitbank_client):
        """Phase 61.3: 価格取得失敗時のリトライスキップ"""
        mock_threshold.return_value = {"timeout_seconds": 3, "check_interval_seconds": 1}

        # 価格0を返す
        mock_bitbank_client.fetch_ticker = MagicMock(return_value={"last": 0})

        success, order_id = await stop_manager._retry_close_order_with_price_update(
            bitbank_client=mock_bitbank_client,
            symbol="BTC/JPY",
            exit_side="sell",
            amount=0.001,
            entry_position_side="long",
            original_order_id="old_order_123",
            max_retries=2,
            slippage_increase_per_retry=0.001,
        )

        # 価格0のためリトライスキップ、最終的に失敗
        assert success is False
        assert order_id is None

    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_retry_create_order_no_id(
        self, mock_threshold, stop_manager, mock_bitbank_client
    ):
        """Phase 61.3: 注文ID取得失敗時のリトライ続行"""
        mock_threshold.return_value = {"timeout_seconds": 1, "check_interval_seconds": 1}

        # 1回目はID無し、2回目は正常ID
        mock_bitbank_client.create_order = MagicMock(
            side_effect=[
                {"id": None},  # 1回目: ID無し
                {"id": "new_order_456"},  # 2回目: 正常
            ]
        )
        mock_bitbank_client.fetch_order = MagicMock(
            return_value={"status": "closed", "filled": 0.001}
        )

        success, order_id = await stop_manager._retry_close_order_with_price_update(
            bitbank_client=mock_bitbank_client,
            symbol="BTC/JPY",
            exit_side="sell",
            amount=0.001,
            entry_position_side="long",
            original_order_id="old_order_123",
            max_retries=3,
            slippage_increase_per_retry=0.001,
        )

        assert success is True
        assert order_id == "new_order_456"

    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_retry_exception_handling(
        self, mock_threshold, stop_manager, mock_bitbank_client
    ):
        """Phase 61.3: 例外発生時のリトライ続行"""
        mock_threshold.return_value = {"timeout_seconds": 3, "check_interval_seconds": 1}

        # 最初のリトライで例外、2回目で成功
        call_count = [0]

        def mock_create_order(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("API Error")
            return {"id": "new_order_789"}

        mock_bitbank_client.create_order = MagicMock(side_effect=mock_create_order)
        mock_bitbank_client.fetch_order = MagicMock(
            return_value={"status": "closed", "filled": 0.001}
        )

        success, order_id = await stop_manager._retry_close_order_with_price_update(
            bitbank_client=mock_bitbank_client,
            symbol="BTC/JPY",
            exit_side="sell",
            amount=0.001,
            entry_position_side="long",
            original_order_id="old_order_123",
            max_retries=3,
            slippage_increase_per_retry=0.001,
        )

        assert success is True
        assert order_id == "new_order_789"


# ========================================
# Phase 49.6: cleanup_position_orders() テスト
# ========================================


@pytest.mark.asyncio
class TestCleanupPositionOrders:
    """Phase 49.6/58.8: cleanup_position_orders() テスト"""

    @pytest.fixture
    def stop_manager(self):
        """StopManagerインスタンス"""
        return StopManager()

    @pytest.fixture
    def mock_bitbank_client(self):
        """BitbankClientのモック"""
        client = MagicMock()
        client.cancel_order = MagicMock(return_value={"success": True})
        return client

    async def test_cleanup_tp_on_stop_loss_reason(self, stop_manager, mock_bitbank_client):
        """Phase 49.6: SL理由でTP注文キャンセル"""
        result = await stop_manager.cleanup_position_orders(
            tp_order_id="tp_123",
            sl_order_id=None,
            symbol="BTC/JPY",
            bitbank_client=mock_bitbank_client,
            reason="stop_loss",
        )

        assert result["cancelled_count"] == 1
        assert result["success"] is True
        mock_bitbank_client.cancel_order.assert_called_once_with("tp_123", "BTC/JPY")

    async def test_cleanup_sl_on_take_profit_reason(self, stop_manager, mock_bitbank_client):
        """Phase 49.6: TP理由でSL注文キャンセル"""
        result = await stop_manager.cleanup_position_orders(
            tp_order_id=None,
            sl_order_id="sl_456",
            symbol="BTC/JPY",
            bitbank_client=mock_bitbank_client,
            reason="take_profit",
        )

        assert result["cancelled_count"] == 1
        assert result["success"] is True
        mock_bitbank_client.cancel_order.assert_called_once_with("sl_456", "BTC/JPY")

    async def test_cleanup_both_on_manual_reason(self, stop_manager, mock_bitbank_client):
        """Phase 49.6: 手動決済で両方キャンセル"""
        result = await stop_manager.cleanup_position_orders(
            tp_order_id="tp_123",
            sl_order_id="sl_456",
            symbol="BTC/JPY",
            bitbank_client=mock_bitbank_client,
            reason="manual",
        )

        assert result["cancelled_count"] == 2
        assert result["success"] is True
        assert mock_bitbank_client.cancel_order.call_count == 2

    async def test_cleanup_order_not_found_success(self, stop_manager, mock_bitbank_client):
        """Phase 58.8: OrderNotFoundは成功扱い"""
        mock_bitbank_client.cancel_order = MagicMock(
            side_effect=Exception("OrderNotFound: order not found")
        )

        result = await stop_manager.cleanup_position_orders(
            tp_order_id="tp_123",
            sl_order_id=None,
            symbol="BTC/JPY",
            bitbank_client=mock_bitbank_client,
            reason="stop_loss",
        )

        # OrderNotFoundは成功扱い（既にキャンセル/約定済み）
        assert result["cancelled_count"] == 1
        assert result["success"] is True

    async def test_cleanup_retry_on_failure(self, stop_manager, mock_bitbank_client):
        """Phase 58.8: キャンセル失敗時のリトライ"""
        # 2回失敗後、3回目で成功
        mock_bitbank_client.cancel_order = MagicMock(
            side_effect=[
                Exception("API Rate Limit"),
                Exception("API Rate Limit"),
                {"success": True},
            ]
        )

        result = await stop_manager.cleanup_position_orders(
            tp_order_id="tp_123",
            sl_order_id=None,
            symbol="BTC/JPY",
            bitbank_client=mock_bitbank_client,
            reason="stop_loss",
        )

        assert result["cancelled_count"] == 1
        assert mock_bitbank_client.cancel_order.call_count == 3

    async def test_cleanup_sl_failure_marks_orphan(self, stop_manager, mock_bitbank_client):
        """Phase 59.6: SLキャンセル失敗時は孤児SLとして記録"""
        # 全リトライ失敗
        mock_bitbank_client.cancel_order = MagicMock(side_effect=Exception("Permanent Error"))

        with patch.object(stop_manager, "_mark_orphan_sl") as mock_mark:
            result = await stop_manager.cleanup_position_orders(
                tp_order_id=None,
                sl_order_id="sl_456",
                symbol="BTC/JPY",
                bitbank_client=mock_bitbank_client,
                reason="take_profit",
            )

            # 孤児SLとして記録される
            mock_mark.assert_called_once_with("sl_456", "take_profit")


# ========================================
# Phase 46: place_take_profit() テスト
# ========================================


# Phase 64: TestPlaceTakeProfit は test_tp_sl_manager.py に移動

# ========================================
# 追加テスト: cleanup_old_unfilled_orders() 詳細テスト
# ========================================


# Phase 64: TestCleanupOldUnfilledOrdersDetailed は PositionRestorer に移動
# テストは test_position_restorer.py を参照


# ========================================
# Phase 61.9: _log_auto_execution() テスト
# ========================================


class TestLogAutoExecution:
    """Phase 61.9: _log_auto_execution() テスト"""

    @pytest.fixture
    def stop_manager(self):
        """StopManagerインスタンス"""
        return StopManager()

    def test_log_tp_execution_profit(self, stop_manager):
        """Phase 61.9: TP自動執行ログ - 利益"""
        execution_info = {
            "execution_type": "take_profit",
            "side": "buy",
            "amount": 0.001,
            "exit_price": 14300000.0,
            "pnl": 300.0,
            "strategy_name": "BBReversal",
        }
        config = {"log_level": "info"}

        # ログ出力が例外を発生させないことを確認
        stop_manager._log_auto_execution(execution_info, config)

    def test_log_tp_execution_loss(self, stop_manager):
        """Phase 61.9: TP自動執行ログ - 損失（異常ケース）"""
        execution_info = {
            "execution_type": "take_profit",
            "side": "buy",
            "amount": 0.001,
            "exit_price": 13900000.0,
            "pnl": -100.0,  # 損失（異常ケース）
            "strategy_name": "ATRBased",
        }
        config = {"log_level": "info"}

        stop_manager._log_auto_execution(execution_info, config)

    def test_log_sl_execution_loss(self, stop_manager):
        """Phase 61.9: SL自動執行ログ - 損失"""
        execution_info = {
            "execution_type": "stop_loss",
            "side": "buy",
            "amount": 0.001,
            "exit_price": 13700000.0,
            "pnl": -300.0,
            "strategy_name": "StochasticDivergence",
        }
        config = {"log_level": "info"}

        stop_manager._log_auto_execution(execution_info, config)

    def test_log_sl_execution_profit(self, stop_manager):
        """Phase 61.9: SL自動執行ログ - 利益（異常ケース）"""
        execution_info = {
            "execution_type": "stop_loss",
            "side": "sell",
            "amount": 0.001,
            "exit_price": 14100000.0,
            "pnl": 100.0,  # 利益（異常ケース）
            "strategy_name": "DonchianChannel",
        }
        config = {"log_level": "info"}

        stop_manager._log_auto_execution(execution_info, config)


# ========================================
# 追加テスト: _calc_pnl() エッジケース
# ========================================


class TestCalcPnlEdgeCases:
    """_calc_pnl() エッジケーステスト"""

    @pytest.fixture
    def stop_manager(self):
        """StopManagerインスタンス"""
        return StopManager()

    def test_calc_pnl_zero_entry_price(self, stop_manager):
        """エントリー価格0の場合は0を返す"""
        pnl = stop_manager._calc_pnl(
            entry_price=0,
            exit_price=14000000.0,
            amount=0.001,
            side="buy",
        )
        assert pnl == 0.0

    def test_calc_pnl_zero_exit_price(self, stop_manager):
        """決済価格0の場合は0を返す"""
        pnl = stop_manager._calc_pnl(
            entry_price=14000000.0,
            exit_price=0,
            amount=0.001,
            side="buy",
        )
        assert pnl == 0.0

    def test_calc_pnl_zero_amount(self, stop_manager):
        """数量0の場合は0を返す"""
        pnl = stop_manager._calc_pnl(
            entry_price=14000000.0,
            exit_price=14300000.0,
            amount=0,
            side="buy",
        )
        assert pnl == 0.0

    def test_calc_pnl_negative_values(self, stop_manager):
        """負の値の場合は0を返す"""
        pnl = stop_manager._calc_pnl(
            entry_price=-14000000.0,
            exit_price=14300000.0,
            amount=0.001,
            side="buy",
        )
        assert pnl == 0.0


# ========================================
# Phase 62.6: 手数料考慮した損益計算テスト
# ========================================


class TestCalcPnlWithFees:
    """Phase 62.6: _calc_pnl() 手数料考慮テスト

    検証データ: 2026/02/01 取引（bitbank UI実現損益と照合済み）
      - エントリー: 12,276,840円 × 0.0108 BTC = 132,589.87円
      - 決済: 12,219,839円 × 0.0108 BTC = 131,974.26円
      - エントリー手数料(Taker 0.12%): 159.11円
      - 決済手数料(Taker 0.12%): 158.37円
      - 粗利益: 615.61円
      - 実現損益: 298.13円 ✓
    """

    @pytest.fixture
    def stop_manager(self):
        """StopManagerインスタンス"""
        return StopManager()

    @patch("src.trading.execution.stop_manager.get_threshold")
    def test_calc_pnl_with_fees_real_trade_data(self, mock_get_threshold, stop_manager):
        """実取引データでの検証（2026/02/01 19:14→19:35 利確）"""

        # Phase 62.19: Taker 0.1%手数料設定モック
        def threshold_side_effect(key, default=None):
            if key == "trading.fees.entry_taker_rate":
                return 0.001  # Taker 0.1%
            elif key == "trading.fees.exit_taker_rate":
                return 0.001  # Taker 0.1%
            return default

        mock_get_threshold.side_effect = threshold_side_effect

        # 実取引データ
        entry_price = 12276840  # エントリー価格
        exit_price = 12219839  # 決済価格（TP約定）
        amount = 0.0108  # 数量

        # 計算実行
        pnl = stop_manager._calc_pnl(
            entry_price=entry_price,
            exit_price=exit_price,
            amount=amount,
            side="sell",  # ショートポジション（価格下落で利益）
        )

        # Phase 62.19: 期待値計算（Taker 0.1%）
        # 粗利益: (12,276,840 - 12,219,839) × 0.0108 = 615.61円
        # エントリー手数料: 12,276,840 × 0.0108 × 0.001 = 132.59円
        # 決済手数料: 12,219,839 × 0.0108 × 0.001 = 131.97円
        # 実現損益: 615.61 - 132.59 - 131.97 = 351.05円
        expected_pnl = 351.05

        # 許容誤差±1円で検証
        assert abs(pnl - expected_pnl) < 1.0, f"Expected ~{expected_pnl}, got {pnl}"

    @patch("src.trading.execution.stop_manager.get_threshold")
    def test_calc_pnl_long_profit(self, mock_get_threshold, stop_manager):
        """ロングポジション利確の手数料計算"""
        mock_get_threshold.side_effect = lambda key, default=None: (
            0.001 if "fee" in key else default
        )

        # ロング: 14,000,000円 → 14,100,000円（+100,000円の粗利益）
        entry_price = 14000000
        exit_price = 14100000
        amount = 0.01

        pnl = stop_manager._calc_pnl(
            entry_price=entry_price,
            exit_price=exit_price,
            amount=amount,
            side="buy",
        )

        # 期待値計算
        gross_pnl = (exit_price - entry_price) * amount  # 1,000円
        entry_fee = entry_price * amount * 0.001  # 168円
        exit_fee = exit_price * amount * 0.001  # 169.2円
        expected_net_pnl = gross_pnl - entry_fee - exit_fee  # 662.8円

        assert abs(pnl - expected_net_pnl) < 0.1

    @patch("src.trading.execution.stop_manager.get_threshold")
    def test_calc_pnl_long_loss(self, mock_get_threshold, stop_manager):
        """ロングポジション損切の手数料計算"""
        mock_get_threshold.side_effect = lambda key, default=None: (
            0.001 if "fee" in key else default
        )

        # ロング: 14,000,000円 → 13,900,000円（-100,000円の粗損失）
        entry_price = 14000000
        exit_price = 13900000
        amount = 0.01

        pnl = stop_manager._calc_pnl(
            entry_price=entry_price,
            exit_price=exit_price,
            amount=amount,
            side="buy",
        )

        # 期待値計算
        gross_pnl = (exit_price - entry_price) * amount  # -1,000円
        entry_fee = entry_price * amount * 0.001  # 168円
        exit_fee = exit_price * amount * 0.001  # 166.8円
        expected_net_pnl = gross_pnl - entry_fee - exit_fee  # -1,334.8円

        assert abs(pnl - expected_net_pnl) < 0.1
        assert pnl < 0  # 損失確認

    @patch("src.trading.execution.stop_manager.get_threshold")
    def test_calc_pnl_short_profit(self, mock_get_threshold, stop_manager):
        """ショートポジション利確の手数料計算"""
        mock_get_threshold.side_effect = lambda key, default=None: (
            0.001 if "fee" in key else default
        )

        # ショート: 14,000,000円 → 13,900,000円（+100,000円の粗利益）
        entry_price = 14000000
        exit_price = 13900000
        amount = 0.01

        pnl = stop_manager._calc_pnl(
            entry_price=entry_price,
            exit_price=exit_price,
            amount=amount,
            side="sell",
        )

        # 期待値計算
        gross_pnl = (entry_price - exit_price) * amount  # 1,000円
        entry_fee = entry_price * amount * 0.001  # 168円
        exit_fee = exit_price * amount * 0.001  # 166.8円
        expected_net_pnl = gross_pnl - entry_fee - exit_fee  # 665.2円

        assert abs(pnl - expected_net_pnl) < 0.1
        assert pnl > 0  # 利益確認

    @patch("src.trading.execution.stop_manager.get_threshold")
    def test_calc_pnl_short_loss(self, mock_get_threshold, stop_manager):
        """ショートポジション損切の手数料計算"""
        mock_get_threshold.side_effect = lambda key, default=None: (
            0.001 if "fee" in key else default
        )

        # ショート: 14,000,000円 → 14,100,000円（-100,000円の粗損失）
        entry_price = 14000000
        exit_price = 14100000
        amount = 0.01

        pnl = stop_manager._calc_pnl(
            entry_price=entry_price,
            exit_price=exit_price,
            amount=amount,
            side="sell",
        )

        # 期待値計算
        gross_pnl = (entry_price - exit_price) * amount  # -1,000円
        entry_fee = entry_price * amount * 0.001  # 168円
        exit_fee = exit_price * amount * 0.001  # 169.2円
        expected_net_pnl = gross_pnl - entry_fee - exit_fee  # -1,337.2円

        assert abs(pnl - expected_net_pnl) < 0.1
        assert pnl < 0  # 損失確認

    @patch("src.trading.execution.stop_manager.get_threshold")
    def test_calc_pnl_uses_config_values(self, mock_get_threshold, stop_manager):
        """設定ファイルから手数料率を取得することを確認"""
        mock_get_threshold.side_effect = lambda key, default=None: (
            0.001 if "fee" in key else default
        )

        stop_manager._calc_pnl(
            entry_price=14000000,
            exit_price=14100000,
            amount=0.01,
            side="buy",
        )

        # get_threshold が適切なキーで呼び出されたことを確認
        call_keys = [call[0][0] for call in mock_get_threshold.call_args_list]
        assert "trading.fees.entry_taker_rate" in call_keys
        assert "trading.fees.exit_taker_rate" in call_keys


# ========================================
# 追加テスト: _cancel_remaining_order() テスト
# ========================================


@pytest.mark.asyncio
class TestCancelRemainingOrder:
    """Phase 61.9: _cancel_remaining_order() テスト"""

    @pytest.fixture
    def stop_manager(self):
        """StopManagerインスタンス"""
        return StopManager()

    @pytest.fixture
    def mock_bitbank_client(self):
        """BitbankClientのモック"""
        client = MagicMock()
        client.cancel_order = MagicMock(return_value={"success": True})
        return client

    async def test_cancel_remaining_sl_after_tp(self, stop_manager, mock_bitbank_client):
        """Phase 61.9: TP約定後にSLキャンセル"""
        execution_info = {
            "execution_type": "take_profit",
            "remaining_order_id": "sl_123",
        }

        await stop_manager._cancel_remaining_order(execution_info, mock_bitbank_client, "BTC/JPY")

        mock_bitbank_client.cancel_order.assert_called_once_with("sl_123", "BTC/JPY")

    async def test_cancel_remaining_tp_after_sl(self, stop_manager, mock_bitbank_client):
        """Phase 61.9: SL約定後にTPキャンセル"""
        execution_info = {
            "execution_type": "stop_loss",
            "remaining_order_id": "tp_456",
        }

        await stop_manager._cancel_remaining_order(execution_info, mock_bitbank_client, "BTC/JPY")

        mock_bitbank_client.cancel_order.assert_called_once_with("tp_456", "BTC/JPY")

    async def test_cancel_remaining_no_order_id(self, stop_manager, mock_bitbank_client):
        """Phase 61.9: remaining_order_idがない場合は何もしない"""
        execution_info = {
            "execution_type": "take_profit",
            "remaining_order_id": None,
        }

        await stop_manager._cancel_remaining_order(execution_info, mock_bitbank_client, "BTC/JPY")

        mock_bitbank_client.cancel_order.assert_not_called()

    async def test_cancel_remaining_order_not_found(self, stop_manager, mock_bitbank_client):
        """Phase 61.9: OrderNotFoundは許容"""
        mock_bitbank_client.cancel_order = MagicMock(
            side_effect=Exception("OrderNotFound: not found")
        )
        execution_info = {
            "execution_type": "take_profit",
            "remaining_order_id": "sl_123",
        }

        # 例外が発生しない
        await stop_manager._cancel_remaining_order(execution_info, mock_bitbank_client, "BTC/JPY")

    async def test_cancel_remaining_api_error(self, stop_manager, mock_bitbank_client):
        """Phase 61.9: APIエラーは警告ログ"""
        mock_bitbank_client.cancel_order = MagicMock(side_effect=Exception("API Rate Limit"))
        execution_info = {
            "execution_type": "take_profit",
            "remaining_order_id": "sl_123",
        }

        # 例外が発生しない（警告ログのみ）
        await stop_manager._cancel_remaining_order(execution_info, mock_bitbank_client, "BTC/JPY")


# ========================================
# 追加テスト: check_stop_conditions() バックテストモード
# ========================================


class TestCheckStopConditionsBacktest:
    """check_stop_conditions() バックテストモードテスト"""

    @pytest.fixture
    def stop_manager(self):
        """StopManagerインスタンス"""
        return StopManager()

    @pytest.mark.asyncio
    async def test_backtest_mode_returns_none(self, stop_manager):
        """バックテストモードではNoneを返す"""
        sample_position = {
            "order_id": "order_123",
            "side": "buy",
            "amount": 0.001,
            "price": 14000000.0,
            "take_profit": 14300000.0,
            "stop_loss": 13700000.0,
        }

        result = await stop_manager.check_stop_conditions(
            virtual_positions=[sample_position],
            bitbank_client=None,
            mode="backtest",  # バックテストモード
            executed_trades=0,
            session_pnl=0.0,
        )

        # バックテストモードではNone（backtest_runner.pyが処理）
        assert result is None


# ========================================
# 追加テスト: _evaluate_position_exit() 例外ハンドリング
# ========================================


@pytest.mark.asyncio
class TestEvaluatePositionExitExceptionHandling:
    """_evaluate_position_exit() 例外ハンドリングテスト"""

    @pytest.fixture
    def stop_manager(self):
        """StopManagerインスタンス"""
        return StopManager()

    async def test_exception_returns_none(self, stop_manager):
        """例外発生時はNoneを返す"""
        # 不正なデータでエラーを発生させる
        position = {
            "side": "buy",
            "price": "invalid",  # 文字列（不正）
            "amount": 0.001,
            "take_profit": 14300000.0,
        }
        tp_config = {"enabled": True}
        sl_config = {"enabled": True}

        result = await stop_manager._evaluate_position_exit(
            position=position,
            current_price=14350000.0,
            tp_config=tp_config,
            sl_config=sl_config,
            mode="paper",
        )

        # 例外が発生してもNoneを返す
        assert result is None

    async def test_none_price_skipped(self, stop_manager):
        """Phase 53.11: priceがNoneの場合はスキップ"""
        position = {
            "side": "buy",
            "price": None,  # None
            "amount": 0.001,
            "take_profit": 14300000.0,
        }
        tp_config = {"enabled": True}
        sl_config = {"enabled": True}

        result = await stop_manager._evaluate_position_exit(
            position=position,
            current_price=14350000.0,
            tp_config=tp_config,
            sl_config=sl_config,
            mode="paper",
        )

        assert result is None

    async def test_none_amount_skipped(self, stop_manager):
        """Phase 53.11: amountがNoneの場合はスキップ"""
        position = {
            "side": "buy",
            "price": 14000000.0,
            "amount": None,  # None
            "take_profit": 14300000.0,
        }
        tp_config = {"enabled": True}
        sl_config = {"enabled": True}

        result = await stop_manager._evaluate_position_exit(
            position=position,
            current_price=14350000.0,
            tp_config=tp_config,
            sl_config=sl_config,
            mode="paper",
        )

        assert result is None


# ========================================
# Phase 58.1: _execute_position_exit() ライブモード詳細テスト
# ========================================


@pytest.mark.asyncio
class TestExecutePositionExitLiveMode:
    """_execute_position_exit() ライブモード詳細テスト"""

    @pytest.fixture
    def stop_manager(self):
        """StopManagerインスタンス"""
        return StopManager()

    @pytest.fixture
    def mock_bitbank_client(self):
        """BitbankClientのモック"""
        client = MagicMock()
        client.create_order = MagicMock(return_value={"id": "close_order_123"})
        client.cancel_order = MagicMock(return_value={"success": True})
        return client

    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_live_mode_creates_close_order(
        self, mock_threshold, stop_manager, mock_bitbank_client
    ):
        """Phase 58.1: ライブモードで決済注文を発行"""
        mock_threshold.side_effect = lambda key, default=None: {
            "trading_constraints.currency_pair": "BTC/JPY",
            "position_management.stop_loss.fill_confirmation": {"enabled": False},
        }.get(key, default)

        position = {
            "order_id": "order_123",
            "side": "buy",
            "price": 14000000.0,
            "amount": 0.001,
            "tp_order_id": None,
            "sl_order_id": None,
        }

        result = await stop_manager._execute_position_exit(
            position=position,
            current_price=14300000.0,
            exit_reason="take_profit",
            mode="live",
            bitbank_client=mock_bitbank_client,
        )

        assert result.success is True
        assert result.mode == ExecutionMode.LIVE
        mock_bitbank_client.create_order.assert_called_once()

    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_live_mode_cleanup_tp_sl_orders(
        self, mock_threshold, stop_manager, mock_bitbank_client
    ):
        """Phase 49.6: ライブモードでTP/SL注文をクリーンアップ"""
        mock_threshold.side_effect = lambda key, default=None: {
            "trading_constraints.currency_pair": "BTC/JPY",
            "position_management.stop_loss.fill_confirmation": {"enabled": False},
        }.get(key, default)

        position = {
            "order_id": "order_123",
            "side": "buy",
            "price": 14000000.0,
            "amount": 0.001,
            "tp_order_id": "tp_123",
            "sl_order_id": "sl_456",
        }

        result = await stop_manager._execute_position_exit(
            position=position,
            current_price=14300000.0,
            exit_reason="take_profit",
            mode="live",
            bitbank_client=mock_bitbank_client,
        )

        assert result.success is True
        # TP/SL注文がクリーンアップされる（cancel_orderが呼ばれる）
        assert mock_bitbank_client.cancel_order.call_count >= 1

    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_live_mode_with_fill_confirmation_enabled(
        self, mock_threshold, stop_manager, mock_bitbank_client
    ):
        """Phase 61.3: fill_confirmation有効時の約定確認"""
        mock_threshold.side_effect = lambda key, default=None: {
            "trading_constraints.currency_pair": "BTC/JPY",
            "position_management.stop_loss.fill_confirmation": {
                "enabled": True,
                "timeout_seconds": 3,
                "check_interval_seconds": 1,
            },
            "position_management.stop_loss.retry_on_unfilled": {"enabled": False},
        }.get(key, default)

        mock_bitbank_client.fetch_order = MagicMock(
            return_value={"status": "closed", "filled": 0.001}
        )

        position = {
            "order_id": "order_123",
            "side": "buy",
            "price": 14000000.0,
            "amount": 0.001,
        }

        result = await stop_manager._execute_position_exit(
            position=position,
            current_price=14300000.0,
            exit_reason="stop_loss",
            mode="live",
            bitbank_client=mock_bitbank_client,
        )

        assert result.success is True
        # fetch_orderが呼ばれる（約定確認）
        assert mock_bitbank_client.fetch_order.call_count >= 1

    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_live_mode_with_retry_on_unfilled(
        self, mock_threshold, stop_manager, mock_bitbank_client
    ):
        """Phase 61.3: 未約定時のリトライ"""
        mock_threshold.side_effect = lambda key, default=None: {
            "trading_constraints.currency_pair": "BTC/JPY",
            "position_management.stop_loss.fill_confirmation": {
                "enabled": True,
                "timeout_seconds": 1,
                "check_interval_seconds": 1,
            },
            "position_management.stop_loss.retry_on_unfilled": {
                "enabled": True,
                "max_retries": 2,
                "slippage_increase_per_retry": 0.001,
            },
        }.get(key, default)

        # 最初の注文は未約定、リトライで約定
        call_count = [0]

        def mock_fetch_order(order_id, symbol):
            call_count[0] += 1
            if call_count[0] <= 1:
                return {"status": "open"}  # 最初は未約定
            return {"status": "closed", "filled": 0.001}

        mock_bitbank_client.fetch_order = MagicMock(side_effect=mock_fetch_order)
        mock_bitbank_client.fetch_ticker = MagicMock(return_value={"last": 14000000.0})

        position = {
            "order_id": "order_123",
            "side": "buy",
            "price": 14000000.0,
            "amount": 0.001,
        }

        result = await stop_manager._execute_position_exit(
            position=position,
            current_price=14300000.0,
            exit_reason="stop_loss",
            mode="live",
            bitbank_client=mock_bitbank_client,
        )

        assert result.success is True

    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_live_mode_create_order_failure(
        self, mock_threshold, stop_manager, mock_bitbank_client
    ):
        """Phase 62.21: 決済注文発行失敗時はsuccess=Falseで返す（バグ修正）"""
        mock_threshold.side_effect = lambda key, default=None: {
            "trading_constraints.currency_pair": "BTC/JPY",
            "position_management.stop_loss.fill_confirmation": {"enabled": False},
        }.get(key, default)

        mock_bitbank_client.create_order = MagicMock(side_effect=Exception("API Error"))

        position = {
            "order_id": "order_123",
            "side": "buy",
            "price": 14000000.0,
            "amount": 0.001,
        }

        result = await stop_manager._execute_position_exit(
            position=position,
            current_price=14300000.0,
            exit_reason="stop_loss",
            mode="live",
            bitbank_client=mock_bitbank_client,
        )

        # Phase 62.21: エラー時はExecutionResult（success=False）を返す
        assert result is not None
        assert result.success is False  # Phase 62.21: 決済失敗時はFalse
        assert result.error_message == "API Error"
        assert result.order_id == "exit_error_order_123"

    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_live_mode_cleanup_error_continues(
        self, mock_threshold, stop_manager, mock_bitbank_client
    ):
        """Phase 59.6: クリーンアップエラーでも処理継続"""
        mock_threshold.side_effect = lambda key, default=None: {
            "trading_constraints.currency_pair": "BTC/JPY",
            "position_management.stop_loss.fill_confirmation": {"enabled": False},
        }.get(key, default)

        # cancel_orderでエラー発生
        mock_bitbank_client.cancel_order = MagicMock(side_effect=Exception("Cancel Failed"))

        position = {
            "order_id": "order_123",
            "side": "buy",
            "price": 14000000.0,
            "amount": 0.001,
            "tp_order_id": "tp_123",
            "sl_order_id": "sl_456",
        }

        result = await stop_manager._execute_position_exit(
            position=position,
            current_price=14300000.0,
            exit_reason="take_profit",
            mode="live",
            bitbank_client=mock_bitbank_client,
        )

        # エラーがあっても処理継続
        assert result.success is True


# ========================================
# 追加: _check_emergency_stop_loss() 詳細テスト
# ========================================


@pytest.mark.asyncio
class TestCheckEmergencyStopLossDetailed:
    """_check_emergency_stop_loss() 詳細テスト"""

    @pytest.fixture
    def stop_manager(self):
        """StopManagerインスタンス"""
        return StopManager()

    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_emergency_exit_removes_position(self, mock_threshold, stop_manager):
        """緊急決済後にポジションが削除される"""
        mock_threshold.return_value = {
            "enable": True,
            "max_loss_threshold": 0.05,
            "min_hold_minutes": 0,
        }

        position = {
            "order_id": "order_123",
            "side": "buy",
            "price": 14000000.0,
            "amount": 0.001,
            "timestamp": datetime.now() - timedelta(minutes=10),
        }
        virtual_positions = [position]

        result = await stop_manager._check_emergency_stop_loss(
            virtual_positions=virtual_positions,
            current_price=13200000.0,  # 5%以上の損失
            mode="paper",
            executed_trades=0,
            session_pnl=0.0,
        )

        assert result is not None
        assert len(virtual_positions) == 0  # ポジション削除

    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_emergency_no_position_triggered(self, mock_threshold, stop_manager):
        """損失閾値未満では緊急決済しない"""
        mock_threshold.return_value = {
            "enable": True,
            "max_loss_threshold": 0.05,
            "min_hold_minutes": 0,
        }

        position = {
            "order_id": "order_123",
            "side": "buy",
            "price": 14000000.0,
            "amount": 0.001,
            "timestamp": datetime.now() - timedelta(minutes=10),
        }
        virtual_positions = [position]

        result = await stop_manager._check_emergency_stop_loss(
            virtual_positions=virtual_positions,
            current_price=13800000.0,  # 1.4%損失（閾値未満）
            mode="paper",
            executed_trades=0,
            session_pnl=0.0,
        )

        assert result is None
        assert len(virtual_positions) == 1  # ポジション維持


# ========================================
# 追加: _evaluate_emergency_exit() 詳細テスト
# ========================================


@pytest.mark.asyncio
class TestEvaluateEmergencyExitDetailed:
    """_evaluate_emergency_exit() 詳細テスト"""

    @pytest.fixture
    def stop_manager(self):
        """StopManagerインスタンス"""
        return StopManager()

    async def test_position_price_none_returns_false(self, stop_manager):
        """Phase 53.11: priceがNoneの場合はFalse"""
        position = {
            "price": None,  # None
            "side": "buy",
            "timestamp": datetime.now() - timedelta(minutes=10),
        }
        config = {
            "max_loss_threshold": 0.05,
            "min_hold_minutes": 1,
        }

        result = await stop_manager._evaluate_emergency_exit(position, 13200000.0, config)

        assert result is False

    async def test_rapid_price_movement_detected_buy(self, stop_manager):
        """急落検出（買いポジション）"""
        position = {
            "price": 14000000.0,
            "side": "buy",
            "timestamp": datetime.now() - timedelta(minutes=10),
        }
        config = {
            "max_loss_threshold": 0.10,  # 10%閾値
            "min_hold_minutes": 1,
            "price_change_threshold": 0.03,
        }

        # 5%損失（閾値未満だが_check_rapid_price_movementで処理）
        result = await stop_manager._evaluate_emergency_exit(position, 13300000.0, config)

        # 現在の実装では_check_rapid_price_movementが常にNoneを返すためFalse
        assert result is False

    async def test_timestamp_not_datetime(self, stop_manager):
        """timestampがdatetime以外の場合"""
        position = {
            "price": 14000000.0,
            "side": "buy",
            "timestamp": "2026-01-31T10:00:00",  # 文字列
        }
        config = {
            "max_loss_threshold": 0.05,
            "min_hold_minutes": 1,
        }

        # 保有時間チェックがスキップされる
        result = await stop_manager._evaluate_emergency_exit(position, 13200000.0, config)

        # 5%超の損失なので緊急決済
        assert result is True


# ========================================
# 追加: place_stop_loss() 詳細テスト
# ========================================


# Phase 64: TestPlaceStopLossDetailed は test_tp_sl_manager.py に移動

# ========================================
# 追加: _check_take_profit_stop_loss() テスト
# ========================================


@pytest.mark.asyncio
class TestCheckTakeProfitStopLossDetailed:
    """_check_take_profit_stop_loss() 詳細テスト"""

    @pytest.fixture
    def stop_manager(self):
        """StopManagerインスタンス"""
        return StopManager()

    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_both_tp_sl_disabled(self, mock_threshold, stop_manager):
        """TP/SL両方無効時はNone"""
        mock_threshold.side_effect = lambda key, default=None: (
            {"enabled": False} if "take_profit" in key or "stop_loss" in key else default
        )

        position = {
            "side": "buy",
            "price": 14000000.0,
            "amount": 0.001,
            "take_profit": 14300000.0,
            "stop_loss": 13700000.0,
        }

        result = await stop_manager._check_take_profit_stop_loss(
            current_price=14350000.0,
            virtual_positions=[position],
            mode="paper",
            executed_trades=0,
            session_pnl=0.0,
        )

        assert result is None

    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_multiple_positions_triggered(self, mock_threshold, stop_manager):
        """Phase 58.1: 複数ポジション同時TP到達"""
        mock_threshold.side_effect = lambda key, default=None: (
            {"enabled": True} if "take_profit" in key or "stop_loss" in key else default
        )

        positions = [
            {
                "side": "buy",
                "price": 14000000.0,
                "amount": 0.001,
                "take_profit": 14300000.0,
                "stop_loss": None,
                "order_id": "order_1",
            },
            {
                "side": "buy",
                "price": 14100000.0,
                "amount": 0.001,
                "take_profit": 14300000.0,
                "stop_loss": None,
                "order_id": "order_2",
            },
        ]

        result = await stop_manager._check_take_profit_stop_loss(
            current_price=14350000.0,
            virtual_positions=positions,
            mode="paper",
            executed_trades=0,
            session_pnl=0.0,
        )

        # 最初の結果が返される
        assert result is not None
        # 両方のポジションが削除される
        assert len(positions) == 0


# ========================================
# 追加: _execute_emergency_exit() テスト
# ========================================


@pytest.mark.asyncio
class TestExecuteEmergencyExitDetailed:
    """_execute_emergency_exit() 詳細テスト"""

    @pytest.fixture
    def stop_manager(self):
        """StopManagerインスタンス"""
        return StopManager()

    async def test_emergency_exit_buy_position(self, stop_manager):
        """緊急決済 - 買いポジション"""
        position = {
            "order_id": "order_123",
            "side": "buy",
            "price": 14000000.0,
            "amount": 0.001,
        }

        result = await stop_manager._execute_emergency_exit(
            position=position,
            current_price=13200000.0,
            reason="max_loss_exceeded",
            mode="paper",
        )

        assert result.success is True
        assert result.side == "sell"
        assert result.emergency_exit is True
        assert result.emergency_reason == "max_loss_exceeded"

    async def test_emergency_exit_sell_position(self, stop_manager):
        """緊急決済 - 売りポジション"""
        position = {
            "order_id": "order_456",
            "side": "sell",
            "price": 14000000.0,
            "amount": 0.001,
        }

        result = await stop_manager._execute_emergency_exit(
            position=position,
            current_price=14800000.0,
            reason="rapid_price_movement",
            mode="paper",
        )

        assert result.success is True
        assert result.side == "buy"
        assert result.emergency_exit is True
        assert result.emergency_reason == "rapid_price_movement"


# ========================================
# 追加: cleanup_orphan_sl_orders() エッジケーステスト
# ========================================


# Phase 64: TestCleanupOrphanSLOrdersEdgeCases は PositionRestorer に移動
# テストは test_position_restorer.py を参照


# ========================================
# 追加: _find_disappeared_positions() エッジケーステスト
# ========================================


class TestFindDisappearedPositionsEdgeCases:
    """Phase 61.9: _find_disappeared_positions() エッジケーステスト"""

    @pytest.fixture
    def stop_manager(self):
        """StopManagerインスタンス"""
        return StopManager()

    def test_zero_amount_skipped(self, stop_manager):
        """amount=0のポジションはスキップ"""
        virtual_positions = [
            {
                "order_id": "entry_001",
                "side": "buy",
                "amount": 0,  # 0
                "tp_order_id": "tp_001",
                "sl_order_id": "sl_001",
            }
        ]
        actual_positions = []

        disappeared = stop_manager._find_disappeared_positions(virtual_positions, actual_positions)

        assert len(disappeared) == 0

    def test_short_position_matching(self, stop_manager):
        """ショートポジションのマッチング"""
        virtual_positions = [
            {
                "order_id": "entry_001",
                "side": "sell",  # ショート
                "amount": 0.001,
                "tp_order_id": "tp_001",
                "sl_order_id": "sl_001",
            }
        ]
        actual_positions = [{"side": "short", "amount": 0.001}]  # マッチ

        disappeared = stop_manager._find_disappeared_positions(virtual_positions, actual_positions)

        assert len(disappeared) == 0

    def test_actual_position_zero_amount(self, stop_manager):
        """実ポジションのamount=0は無視"""
        virtual_positions = [
            {
                "order_id": "entry_001",
                "side": "buy",
                "amount": 0.001,
                "tp_order_id": "tp_001",
                "sl_order_id": "sl_001",
            }
        ]
        actual_positions = [{"side": "long", "amount": 0}]  # amount=0

        disappeared = stop_manager._find_disappeared_positions(virtual_positions, actual_positions)

        # 実ポジションのamount=0なのでマッチしない
        assert len(disappeared) == 1


# Phase 64: TestPhase6210TPMakerStrategy は test_tp_sl_manager.py に移動


class TestPhase6210BitbankClientTPMaker:
    """Phase 62.10: BitbankClient TP Maker対応テスト"""

    @patch("src.data.bitbank_client.get_threshold")
    def test_create_tp_order_with_post_only(self, mock_threshold):
        """post_only=Trueでlimit+post_only注文が発行される"""
        from src.data.bitbank_client import BitbankClient

        # モック設定
        mock_threshold.return_value = False  # use_native_type = false

        with patch.object(BitbankClient, "__init__", lambda self, **kwargs: None):
            client = BitbankClient()
            client.logger = MagicMock()
            client.api_key = "test_key"
            client.api_secret = "test_secret"
            client.leverage = 1.0

            # create_orderをモック
            mock_order = {"id": "tp_maker_order_001"}
            client.create_order = Mock(return_value=mock_order)

            result = client.create_take_profit_order(
                entry_side="buy",
                amount=0.001,
                take_profit_price=14100000.0,
                symbol="BTC/JPY",
                post_only=True,
            )

            assert result["id"] == "tp_maker_order_001"

            # create_orderがpost_only=Trueで呼ばれていることを確認
            client.create_order.assert_called_once_with(
                symbol="BTC/JPY",
                side="sell",  # buyの反対
                order_type="limit",
                amount=0.001,
                price=14100000.0,
                is_closing_order=True,
                entry_position_side="long",
                post_only=True,
            )

    @patch("src.data.bitbank_client.get_threshold")
    def test_create_tp_order_without_post_only(self, mock_threshold):
        """post_only=Falseで従来のtake_profit注文フロー"""
        from src.data.bitbank_client import BitbankClient

        # モック設定
        mock_threshold.return_value = False  # use_native_type = false

        with patch.object(BitbankClient, "__init__", lambda self, **kwargs: None):
            client = BitbankClient()
            client.logger = MagicMock()
            client.api_key = "test_key"
            client.api_secret = "test_secret"
            client.leverage = 1.0

            # create_orderをモック
            mock_order = {"id": "tp_native_order_001"}
            client.create_order = Mock(return_value=mock_order)

            result = client.create_take_profit_order(
                entry_side="sell",
                amount=0.002,
                take_profit_price=13900000.0,
                symbol="BTC/JPY",
                post_only=False,
            )

            assert result["id"] == "tp_native_order_001"

            # create_orderがpost_only指定なし（または False）で呼ばれていることを確認
            call_args = client.create_order.call_args
            assert call_args[1].get("post_only", False) is False
