"""
ExecutionService統合テスト（循環import回避版）

ExecutionResult型エラーの再発防止のための最小限テスト。
"""

import os
import sys
from unittest.mock import Mock

import pytest

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_execution_service_import():
    """ExecutionServiceが正常にimportできることを確認"""
    try:
        from src.trading import ExecutionService

        assert ExecutionService is not None
    except ImportError as e:
        pytest.fail(f"ExecutionServiceのimportに失敗: {e}")


def test_execution_service_initialization():
    """ExecutionService初期化テスト"""
    from src.trading import ExecutionService

    # ペーパーモード初期化
    paper_service = ExecutionService(mode="paper")
    assert paper_service.mode == "paper"
    assert paper_service.executed_trades == 0

    # ライブモード初期化
    mock_client = Mock()
    live_service = ExecutionService(mode="live", bitbank_client=mock_client)
    assert live_service.mode == "live"
    assert live_service.bitbank_client == mock_client


def test_execution_result_field_names():
    """ExecutionResultが正しいフィールド名を持つことを確認"""
    from src.trading import ExecutionMode, ExecutionResult, OrderStatus

    # 正しいフィールド名でExecutionResultを作成できることを確認
    try:
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

        # フィールドアクセス確認
        assert result.success == True
        assert result.mode == ExecutionMode.PAPER
        assert result.side == "buy"
        assert result.amount == 0.0001
        assert result.price == 5000000.0
        assert result.filled_amount == 0.0001
        assert result.filled_price == 5000000.0
        assert result.fee == 0.0
        assert result.status == OrderStatus.FILLED

    except Exception as e:
        pytest.fail(f"ExecutionResult作成エラー: {e}")


def test_wrong_field_names_raise_error():
    """間違ったフィールド名でTypeErrorが発生することを確認"""
    from src.trading import ExecutionMode, ExecutionResult

    # 間違ったフィールド名（修正前）を使用するとエラーになることを確認
    with pytest.raises(TypeError, match="unexpected keyword argument"):
        ExecutionResult(
            success=True,
            mode=ExecutionMode.PAPER,
            executed_price=5000000.0,  # 間違ったフィールド名
            executed_amount=0.0001,  # 間違ったフィールド名
        )

    with pytest.raises(TypeError, match="unexpected keyword argument"):
        ExecutionResult(
            success=True,
            mode=ExecutionMode.PAPER,
            trade_type="buy",  # 間違ったフィールド名
        )

    with pytest.raises(TypeError, match="unexpected keyword argument"):
        ExecutionResult(
            success=True,
            mode=ExecutionMode.PAPER,
            commission=50.0,  # 間違ったフィールド名
        )


def test_required_fields():
    """必須フィールドのテスト"""
    from src.trading import ExecutionMode, ExecutionResult

    # success と mode は必須フィールド
    with pytest.raises(TypeError):
        ExecutionResult()  # 必須フィールドなし

    # mode なしでエラー
    with pytest.raises(TypeError):
        ExecutionResult(success=True)

    # 最小限の必須フィールドで正常作成
    result = ExecutionResult(success=True, mode=ExecutionMode.PAPER)
    assert result.success == True
    assert result.mode == ExecutionMode.PAPER


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
