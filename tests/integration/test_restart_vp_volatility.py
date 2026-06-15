"""Phase 90ο 統合: 2026-06-15 ドカンの回帰テスト

scale-to-zero 再起動で内部VP(virtual_positions)が揮発した状態（VP空）でも、
bitbank実建玉を基準に同方向の重複エントリーを拒否することを execute_trade レベルで確認する。

6/15 事故の連鎖:
  既存ショート保有 → コンテナ再起動でVP揮発 → 新コンテナでVP空 →
  同方向上限チェックがすり抜け → 重複エントリー → 0.0325 BTC に膨張 → 一括SLでドカン
本テストは Stage 0/1（実ポジ基準の上限チェック）がこの連鎖を断つことを担保する。
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.trading.core import OrderStatus, RiskDecision, TradeEvaluation
from src.trading.execution.executor import ExecutionService
from src.trading.position.limits import PositionLimits


def _buy_evaluation():
    return TradeEvaluation(
        decision=RiskDecision.APPROVED,
        side="buy",
        risk_score=0.1,
        position_size=0.015,
        stop_loss=10300000.0,
        take_profit=10600000.0,
        confidence_level=0.75,
        warnings=[],
        denial_reasons=[],
        evaluation_timestamp=datetime.now(),
        kelly_recommendation=0.05,
        drawdown_status="normal",
        anomaly_alerts=[],
        market_conditions={"market_data": {}},
    )


class TestPhase90OmicronRestartRegression:
    """VP揮発 × 実ポジ存在 → 重複拒否（6/15 事故の回帰）"""

    @pytest.mark.asyncio
    async def test_vp_empty_but_real_position_blocks_same_direction(self):
        """VP空（再起動直後）でも実ポジに long があれば同方向 buy を拒否する"""
        bitbank = MagicMock()
        bitbank.fetch_margin_positions = AsyncMock(
            return_value=[{"side": "long", "amount": 0.0175}]
        )
        svc = ExecutionService(mode="live", bitbank_client=bitbank)
        svc.position_limits = PositionLimits()
        svc.balance_monitor = None  # 残高チェックはスキップ
        svc.current_balance = 500000.0
        # position_tracker 未注入 → virtual_positions は空（VP揮発状態の再現）
        assert svc.virtual_positions == []

        result = await svc.execute_trade(_buy_evaluation())

        # VP は空だが、実ポジ基準で同方向制限に掛かり拒否される（6/15 はここがすり抜けた）
        assert result.success is False
        assert result.status == OrderStatus.REJECTED
        assert "同方向" in (result.error_message or "")

    @pytest.mark.asyncio
    async def test_fetch_failure_rejects_entry_safety_first(self):
        """実ポジ取得失敗（10009等）→ ポジ0誤認せずエントリー拒否（安全優先）"""
        bitbank = MagicMock()
        bitbank.fetch_margin_positions = AsyncMock(side_effect=Exception("bitbank 10009"))
        svc = ExecutionService(mode="live", bitbank_client=bitbank)
        svc.position_limits = PositionLimits()
        svc.balance_monitor = None
        svc.current_balance = 500000.0

        result = await svc.execute_trade(_buy_evaluation())

        assert result.success is False
        assert result.status == OrderStatus.REJECTED
        assert "実ポジ取得失敗" in (result.error_message or "")
