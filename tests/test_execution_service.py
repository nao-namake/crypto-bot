"""
ExecutionServiceテスト

ExecutionResult型エラーの再発防止と動作保証のための包括テスト。
ペーパートレード・ライブトレード・エラー処理を網羅。
"""

import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# 必要な型を個別に定義（テスト用）
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

# 循環import回避のため、動的importを使用


class RiskDecision(Enum):
    """リスク判定結果（テスト用）"""

    APPROVED = "approved"
    DENIED = "denied"
    CONDITIONAL = "conditional"


class ExecutionMode(Enum):
    """実行モード（テスト用）"""

    PAPER = "paper"
    LIVE = "live"


class OrderStatus(Enum):
    """注文状態（テスト用）"""

    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class TradeEvaluation:
    """取引評価結果（テスト用簡易版）"""

    decision: RiskDecision
    side: str
    position_size: float
    confidence: float
    risk_score: float
    expected_return: float
    stop_loss: float
    take_profit: float
    max_drawdown: float
    kelly_fraction: float
    reasoning: str
    entry_price: float = 0.0


@dataclass
class ExecutionResult:
    """注文実行結果（テスト用簡易版）"""

    success: bool
    mode: ExecutionMode
    order_id: Optional[str] = None
    side: Optional[str] = None
    amount: Optional[float] = None
    price: Optional[float] = None
    filled_amount: Optional[float] = None
    filled_price: Optional[float] = None
    fee: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    timestamp: datetime = None
    error_message: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class TestExecutionService:
    """ExecutionServiceの包括テスト"""

    @pytest.fixture
    def paper_service(self):
        """ペーパートレード用ExecutionService"""
        from src.trading.execution_service import ExecutionService

        return ExecutionService(mode="paper")

    @pytest.fixture
    def live_service(self):
        """ライブトレード用ExecutionService（モック付き）"""
        from src.trading.execution_service import ExecutionService

        mock_client = Mock()
        return ExecutionService(mode="live", bitbank_client=mock_client)

    @pytest.fixture
    def sample_evaluation(self):
        """テスト用TradeEvaluation"""
        return TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="buy",
            position_size=0.0001,
            confidence=0.7,
            risk_score=0.3,
            expected_return=0.02,
            stop_loss=0.98,
            take_profit=1.05,
            max_drawdown=0.05,
            kelly_fraction=0.1,
            reasoning="テスト用取引",
            entry_price=5000000.0,
        )

    @pytest.mark.asyncio
    async def test_paper_trade_execution_success(self, paper_service, sample_evaluation):
        """ペーパートレード正常実行テスト"""
        from src.trading.risk_manager import ExecutionMode as RealExecutionMode
        from src.trading.risk_manager import ExecutionResult as RealExecutionResult
        from src.trading.risk_manager import OrderStatus as RealOrderStatus

        result = await paper_service.execute_trade(sample_evaluation)

        # ExecutionResult型検証
        assert isinstance(result, RealExecutionResult)
        assert result.success == True
        assert result.mode == RealExecutionMode.PAPER
        assert result.side == "buy"
        assert result.amount == 0.0001
        assert result.price == 5000000.0
        assert result.filled_amount == 0.0001
        assert result.filled_price == 5000000.0
        assert result.fee == 0.0
        assert result.status == RealOrderStatus.FILLED
        assert result.error_message is None
        assert result.order_id.startswith("paper_")

    @pytest.mark.asyncio
    async def test_live_trade_execution_success(self, live_service, sample_evaluation):
        """ライブトレード正常実行テスト"""
        from src.trading.risk_manager import ExecutionMode as RealExecutionMode
        from src.trading.risk_manager import ExecutionResult as RealExecutionResult
        from src.trading.risk_manager import OrderStatus as RealOrderStatus

        # Bitbankクライアントのモック設定
        mock_order_result = {
            "id": "test_order_123",
            "price": "5000000",
            "amount": "0.0001",
            "fee": "50",
        }
        live_service.bitbank_client.create_order.return_value = mock_order_result

        result = await live_service.execute_trade(sample_evaluation)

        # ExecutionResult型検証
        assert isinstance(result, RealExecutionResult)
        assert result.success == True
        assert result.mode == RealExecutionMode.LIVE
        assert result.side == "buy"
        assert result.amount == 0.0001
        assert result.price == 5000000.0
        assert result.filled_amount == 0.0001
        assert result.filled_price == 5000000.0
        assert result.fee == 50.0
        assert result.status == RealOrderStatus.FILLED
        assert result.error_message is None
        assert result.order_id == "test_order_123"

    @pytest.mark.asyncio
    async def test_backtest_execution_success(self, sample_evaluation):
        """バックテスト正常実行テスト"""
        from src.trading.execution_service import ExecutionService
        from src.trading.risk_manager import ExecutionMode as RealExecutionMode
        from src.trading.risk_manager import ExecutionResult as RealExecutionResult
        from src.trading.risk_manager import OrderStatus as RealOrderStatus

        service = ExecutionService(mode="backtest")
        result = await service.execute_trade(sample_evaluation)

        # ExecutionResult型検証
        assert isinstance(result, RealExecutionResult)
        assert result.success == True
        assert result.mode == RealExecutionMode.PAPER  # バックテストはPAPERモード
        assert result.side == "buy"
        assert result.amount == 0.0001
        assert result.price == 5000000.0
        assert result.filled_amount == 0.0001
        assert result.filled_price == 5000000.0
        assert result.fee == 0.0
        assert result.status == RealOrderStatus.FILLED
        assert result.order_id.startswith("backtest_")

    @pytest.mark.asyncio
    async def test_execution_error_handling(self, paper_service, sample_evaluation):
        """実行エラー処理テスト"""
        from src.trading.risk_manager import ExecutionMode as RealExecutionMode
        from src.trading.risk_manager import ExecutionResult as RealExecutionResult
        from src.trading.risk_manager import OrderStatus as RealOrderStatus

        # エラーを強制発生
        with patch.object(
            paper_service, "_execute_paper_trade", side_effect=Exception("テストエラー")
        ):
            result = await paper_service.execute_trade(sample_evaluation)

        # エラー時ExecutionResult型検証
        assert isinstance(result, RealExecutionResult)
        assert result.success == False
        assert result.mode == RealExecutionMode.PAPER
        assert result.price == 0.0
        assert result.amount == 0.0
        assert result.fee == 0.0
        assert result.status == RealOrderStatus.FAILED
        assert result.error_message == "テストエラー"
        assert result.side == "buy"

    @pytest.mark.asyncio
    async def test_live_trade_without_client_error(self, sample_evaluation):
        """ライブトレード・クライアントなしエラーテスト"""
        from src.trading.execution_service import ExecutionService
        from src.trading.risk_manager import ExecutionMode as RealExecutionMode
        from src.trading.risk_manager import ExecutionResult as RealExecutionResult
        from src.trading.risk_manager import OrderStatus as RealOrderStatus

        service = ExecutionService(mode="live", bitbank_client=None)

        result = await service.execute_trade(sample_evaluation)

        # エラー時ExecutionResult型検証
        assert isinstance(result, RealExecutionResult)
        assert result.success == False
        assert result.mode == RealExecutionMode.LIVE
        assert result.status == RealOrderStatus.FAILED
        assert "BitbankClientが必要" in result.error_message

    def test_paper_service_initialization(self):
        """ペーパーサービス初期化テスト"""
        from src.trading.execution_service import ExecutionService

        service = ExecutionService(mode="paper")
        assert service.mode == "paper"
        assert service.executed_trades == 0
        assert service.virtual_balance > 0
        assert len(service.virtual_positions) == 0

    def test_live_service_initialization(self):
        """ライブサービス初期化テスト"""
        from src.trading.execution_service import ExecutionService

        mock_client = Mock()
        service = ExecutionService(mode="live", bitbank_client=mock_client)
        assert service.mode == "live"
        assert service.bitbank_client == mock_client
        assert service.executed_trades == 0

    @pytest.mark.asyncio
    async def test_sell_order_execution(self, paper_service):
        """売り注文実行テスト"""
        sell_evaluation = TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="sell",
            position_size=0.0001,
            confidence=0.8,
            risk_score=0.2,
            expected_return=0.03,
            stop_loss=1.02,
            take_profit=0.95,
            max_drawdown=0.03,
            kelly_fraction=0.15,
            reasoning="テスト用売り注文",
            entry_price=5100000.0,
        )

        result = await paper_service.execute_trade(sell_evaluation)

        assert result.success == True
        assert result.side == "sell"
        assert result.price == 5100000.0

    def test_execution_result_dataclass_integrity(self):
        """ExecutionResult dataclass完整性テスト"""
        # 正しいフィールド名で作成できることを確認
        result = ExecutionResult(
            success=True,
            mode=ExecutionMode.PAPER,
            order_id="test_123",
            side="buy",
            amount=0.0001,
            price=5000000.0,
            filled_amount=0.0001,
            filled_price=5000000.0,
            fee=0.0,
            status=OrderStatus.FILLED,
        )

        assert result.success == True
        assert result.mode == ExecutionMode.PAPER
        assert result.side == "buy"
        assert result.amount == 0.0001
        assert result.price == 5000000.0

        # 間違ったフィールド名でエラーが発生することを確認
        with pytest.raises(TypeError):
            ExecutionResult(
                success=True,
                mode=ExecutionMode.PAPER,
                executed_price=5000000.0,  # 間違ったフィールド名
                executed_amount=0.0001,  # 間違ったフィールド名
            )

    @pytest.mark.asyncio
    async def test_statistics_update(self, paper_service, sample_evaluation):
        """統計情報更新テスト"""
        initial_trades = paper_service.executed_trades
        await paper_service.execute_trade(sample_evaluation)

        assert paper_service.executed_trades == initial_trades + 1
        assert len(paper_service.virtual_positions) == 1

        # 取引統計情報取得テスト
        stats = paper_service.get_trading_statistics()
        assert stats["executed_trades"] == initial_trades + 1
        assert stats["mode"] == "paper"

    @pytest.mark.asyncio
    async def test_multiple_paper_trades(self, paper_service, sample_evaluation):
        """複数ペーパートレード実行テスト"""
        from src.trading.risk_manager import ExecutionMode as RealExecutionMode

        results = []
        for i in range(3):
            result = await paper_service.execute_trade(sample_evaluation)
            results.append(result)

        # 全ての取引が成功していることを確認
        for result in results:
            assert result.success == True
            assert result.mode == RealExecutionMode.PAPER
            assert isinstance(result.order_id, str)

        # 統計が正しく更新されていることを確認
        assert paper_service.executed_trades == 3
        assert len(paper_service.virtual_positions) == 3
