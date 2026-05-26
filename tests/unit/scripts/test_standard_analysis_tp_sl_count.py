"""
Phase 90γ-③.5: standard_analysis.py の TP/SL 件数集計テスト

bitbank API ベースで win_count / loss_count を確定的に算出する挙動を検証。
GCP ログベース（"Phase 61.9: TP自動執行検知" など）は本番 LOG_LEVEL=WARNING で
INFO ログが出ないため不完全。Phase 90γ-③.5 で API の profit_loss > 0 / < 0 から
算出した値で tp/sl_triggered_count を上書きするように修正した。

`_fetch_trade_history` 全体は SQLite + GCP sync の重い副作用を持つため、本ファイルでは
`_fetch_pnl_from_bitbank_api` の win_count/loss_count 算出ロジックの単体検証に集中する。
統合挙動（tp_triggered_count 上書き）は 24h ライブ分析で実測検証する。
"""

import importlib.util
import itertools
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_module_path = (
    Path(__file__).parent.parent.parent.parent / "scripts" / "live" / "standard_analysis.py"
)
_spec = importlib.util.spec_from_file_location("standard_analysis_module", _module_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

LiveAnalyzer = _mod.LiveAnalyzer

_order_id_counter = itertools.count(1)


def _make_trade(profit_loss, side="buy", position_side="long", maker_taker="taker"):
    """bitbank API trades のモックエントリ生成（order_id はユニーク）"""
    return {
        "datetime": "2026-05-27T00:00:00Z",
        "order": f"order_{next(_order_id_counter)}",
        "info": {
            "profit_loss": str(profit_loss),
            "fee_occurred_amount_quote": "10",
            "side": side,
            "position_side": position_side,
            "maker_taker": maker_taker,
        },
    }


class TestPhase90Gamma35APIBasedPnLCalculation:
    """_fetch_pnl_from_bitbank_api の win_count / loss_count 算出ロジック検証"""

    @pytest.mark.asyncio
    async def test_profit_loss_positive_counts_as_win(self):
        """profit_loss > 0 の決済 = win_count（=TP扱い）"""
        analyzer = LiveAnalyzer(period_hours=24)
        analyzer.bitbank_client = MagicMock()

        trades = [
            _make_trade(286.0),
            _make_trade(150.0),
            _make_trade(50.0),
            _make_trade(215.0),
            _make_trade(-100.0),
        ]
        analyzer.bitbank_client.exchange.fetch_my_trades = MagicMock(return_value=trades)

        result = await analyzer._fetch_pnl_from_bitbank_api()

        assert result is not None
        assert result["win_count"] == 4
        assert result["loss_count"] == 1
        assert result["exit_count"] == 5

    @pytest.mark.asyncio
    async def test_zero_profit_loss_treated_as_entry(self):
        """profit_loss ≈ 0 はエントリー扱い（決済ではない）"""
        analyzer = LiveAnalyzer(period_hours=24)
        analyzer.bitbank_client = MagicMock()

        trades = [
            _make_trade(0.0),
            _make_trade(0.0),
            _make_trade(286.0),
            _make_trade(-100.0),
        ]
        analyzer.bitbank_client.exchange.fetch_my_trades = MagicMock(return_value=trades)

        result = await analyzer._fetch_pnl_from_bitbank_api()

        assert result is not None
        assert result["entry_count"] == 2
        assert result["win_count"] == 1
        assert result["loss_count"] == 1
        assert result["exit_count"] == 2

    @pytest.mark.asyncio
    async def test_all_losses_correct_count(self):
        """全てSL決済（profit_loss < 0）でも正しく集計"""
        analyzer = LiveAnalyzer(period_hours=24)
        analyzer.bitbank_client = MagicMock()

        trades = [
            _make_trade(-200.0),
            _make_trade(-150.0),
            _make_trade(-100.0),
        ]
        analyzer.bitbank_client.exchange.fetch_my_trades = MagicMock(return_value=trades)

        result = await analyzer._fetch_pnl_from_bitbank_api()

        assert result is not None
        assert result["win_count"] == 0
        assert result["loss_count"] == 3
        assert result["entry_count"] == 0

    @pytest.mark.asyncio
    async def test_total_pnl_sum_matches(self):
        """total_pnl が全決済の profit_loss 合計と一致"""
        analyzer = LiveAnalyzer(period_hours=24)
        analyzer.bitbank_client = MagicMock()

        trades = [
            _make_trade(286.0),
            _make_trade(150.0),
            _make_trade(50.0),
            _make_trade(215.0),
            _make_trade(-100.0),
        ]
        analyzer.bitbank_client.exchange.fetch_my_trades = MagicMock(return_value=trades)

        result = await analyzer._fetch_pnl_from_bitbank_api()

        assert result is not None
        assert result["total_pnl"] == 601.0  # 286+150+50+215-100

    @pytest.mark.asyncio
    async def test_empty_trades_returns_none(self):
        """trades が空なら None を返す（フォールバック発動条件）"""
        analyzer = LiveAnalyzer(period_hours=24)
        analyzer.bitbank_client = MagicMock()
        analyzer.bitbank_client.exchange.fetch_my_trades = MagicMock(return_value=[])

        result = await analyzer._fetch_pnl_from_bitbank_api()

        assert result is None
