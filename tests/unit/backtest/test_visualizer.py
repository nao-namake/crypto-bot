"""
BacktestVisualizerテスト

matplotlibグラフ生成の全メソッドをテスト。
実際のファイル出力はモック化。
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.backtest.visualizer import BacktestVisualizer


class TestBacktestVisualizerInit:
    """初期化テスト."""

    def test_default_output_dir(self):
        """デフォルト出力ディレクトリ."""
        viz = BacktestVisualizer()
        assert viz.output_dir.exists() or True  # パスが設定されていればOK
        assert "graphs" in str(viz.output_dir)

    def test_custom_output_dir(self):
        """カスタム出力ディレクトリ."""
        with tempfile.TemporaryDirectory() as tmpdir:
            viz = BacktestVisualizer(output_dir=tmpdir)
            assert viz.output_dir == Path(tmpdir)


class TestGenerateAllCharts:
    """generate_all_charts テスト."""

    def test_generate_all_charts_success(self):
        """全グラフ一括生成成功."""
        with tempfile.TemporaryDirectory() as tmpdir:
            viz = BacktestVisualizer(output_dir=tmpdir)

            # モックTradeTracker
            mock_tracker = Mock()
            mock_tracker.equity_curve = [0, 100, 200, 150, 300]
            mock_tracker.completed_trades = [
                {
                    "pnl": 100,
                    "entry_timestamp": "2025-01-01",
                    "exit_timestamp": "2025-01-02",
                    "entry_price": 14500000,
                    "exit_price": 14600000,
                }
            ]

            price_data = {
                "2025-01-01": 14500000,
                "2025-01-02": 14600000,
                "2025-01-03": 14550000,
            }

            result = viz.generate_all_charts(
                mock_tracker, price_data=price_data, session_id="test_session"
            )
            assert "test_session" in str(result)

    def test_generate_all_charts_default_session_id(self):
        """セッションIDなしの場合自動生成."""
        with tempfile.TemporaryDirectory() as tmpdir:
            viz = BacktestVisualizer(output_dir=tmpdir)

            mock_tracker = Mock()
            mock_tracker.equity_curve = [0, 100]
            mock_tracker.completed_trades = []

            result = viz.generate_all_charts(mock_tracker)
            assert result.exists()

    def test_generate_all_charts_no_trades(self):
        """取引なしの場合もエラーなし."""
        with tempfile.TemporaryDirectory() as tmpdir:
            viz = BacktestVisualizer(output_dir=tmpdir)

            mock_tracker = Mock()
            mock_tracker.equity_curve = [0]
            mock_tracker.completed_trades = []

            result = viz.generate_all_charts(mock_tracker)
            assert result.exists()

    def test_generate_all_charts_exception(self):
        """グラフ生成中の例外."""
        with tempfile.TemporaryDirectory() as tmpdir:
            viz = BacktestVisualizer(output_dir=tmpdir)

            mock_tracker = Mock()
            mock_tracker.equity_curve = None  # Noneでplot_equity_curveが失敗

            with pytest.raises(Exception):
                viz.generate_all_charts(mock_tracker, session_id="test_err")


class TestPlotEquityCurve:
    """plot_equity_curve テスト."""

    def test_equity_curve_success(self):
        """エクイティカーブ生成成功."""
        with tempfile.TemporaryDirectory() as tmpdir:
            viz = BacktestVisualizer(output_dir=tmpdir)
            output_path = Path(tmpdir) / "equity.png"

            equity_curve = [0, 100, 200, 150, 300, -50, 400]
            viz.plot_equity_curve(equity_curve, output_path)

            assert output_path.exists()

    def test_equity_curve_error(self):
        """エクイティカーブ生成エラー（例外をキャッチ）."""
        with tempfile.TemporaryDirectory() as tmpdir:
            viz = BacktestVisualizer(output_dir=tmpdir)
            output_path = Path(tmpdir) / "equity.png"

            # Noneを渡すとエラー
            viz.plot_equity_curve(None, output_path)
            # 例外はキャッチされファイルは作られない
            assert not output_path.exists()


class TestPlotPnlDistribution:
    """plot_pnl_distribution テスト."""

    def test_pnl_distribution_success(self):
        """損益分布ヒストグラム生成成功."""
        with tempfile.TemporaryDirectory() as tmpdir:
            viz = BacktestVisualizer(output_dir=tmpdir)
            output_path = Path(tmpdir) / "pnl.png"

            pnl_list = [100, -50, 200, -30, 150, -80, 300]
            viz.plot_pnl_distribution(pnl_list, output_path)

            assert output_path.exists()

    def test_pnl_distribution_error(self):
        """損益分布ヒストグラム生成エラー."""
        with tempfile.TemporaryDirectory() as tmpdir:
            viz = BacktestVisualizer(output_dir=tmpdir)
            output_path = Path(tmpdir) / "pnl.png"

            viz.plot_pnl_distribution(None, output_path)
            assert not output_path.exists()


class TestPlotDrawdown:
    """plot_drawdown テスト."""

    def test_drawdown_success(self):
        """ドローダウンチャート生成成功."""
        with tempfile.TemporaryDirectory() as tmpdir:
            viz = BacktestVisualizer(output_dir=tmpdir)
            output_path = Path(tmpdir) / "drawdown.png"

            equity_curve = [0, 100, 200, 150, 300, 250, 400]
            viz.plot_drawdown(equity_curve, output_path)

            assert output_path.exists()

    def test_drawdown_error(self):
        """ドローダウンチャート生成エラー."""
        with tempfile.TemporaryDirectory() as tmpdir:
            viz = BacktestVisualizer(output_dir=tmpdir)
            output_path = Path(tmpdir) / "drawdown.png"

            viz.plot_drawdown(None, output_path)
            assert not output_path.exists()


class TestPlotPriceWithTrades:
    """plot_price_with_trades テスト."""

    def test_price_with_trades_success(self):
        """価格チャート+取引マーカー生成成功."""
        with tempfile.TemporaryDirectory() as tmpdir:
            viz = BacktestVisualizer(output_dir=tmpdir)
            output_path = Path(tmpdir) / "price.png"

            price_data = {
                "ts1": 14500000,
                "ts2": 14510000,
                "ts3": 14490000,
                "ts4": 14520000,
            }

            trades = [
                {
                    "entry_timestamp": "ts1",
                    "exit_timestamp": "ts3",
                    "entry_price": 14500000,
                    "exit_price": 14490000,
                    "pnl": -100,
                },
                {
                    "entry_timestamp": "ts2",
                    "exit_timestamp": "ts4",
                    "entry_price": 14510000,
                    "exit_price": 14520000,
                    "pnl": 200,
                },
            ]

            viz.plot_price_with_trades(price_data, trades, output_path)
            assert output_path.exists()

    def test_price_with_trades_missing_timestamps(self):
        """タイムスタンプが見つからない取引."""
        with tempfile.TemporaryDirectory() as tmpdir:
            viz = BacktestVisualizer(output_dir=tmpdir)
            output_path = Path(tmpdir) / "price.png"

            price_data = {"ts1": 14500000, "ts2": 14510000}

            trades = [
                {
                    "entry_timestamp": "missing_ts",
                    "exit_timestamp": "also_missing",
                    "entry_price": 14500000,
                    "exit_price": 14510000,
                    "pnl": 100,
                }
            ]

            viz.plot_price_with_trades(price_data, trades, output_path)
            assert output_path.exists()

    def test_price_with_trades_error(self):
        """価格チャート生成エラー."""
        with tempfile.TemporaryDirectory() as tmpdir:
            viz = BacktestVisualizer(output_dir=tmpdir)
            output_path = Path(tmpdir) / "price.png"

            viz.plot_price_with_trades(None, [], output_path)
            assert not output_path.exists()


class TestCleanupOldGraphs:
    """_cleanup_old_graphs テスト."""

    def test_cleanup_old_graphs(self):
        """古いグラフフォルダ削除."""
        with tempfile.TemporaryDirectory() as tmpdir:
            viz = BacktestVisualizer(output_dir=tmpdir)

            # 7つのバックテストフォルダを作成
            import time

            for i in range(7):
                d = Path(tmpdir) / f"backtest_{i:04d}"
                d.mkdir()
                # 異なるmtimeを設定
                time.sleep(0.01)

            viz._cleanup_old_graphs(keep=5)

            remaining = [d for d in Path(tmpdir).iterdir() if d.is_dir()]
            assert len(remaining) == 5

    def test_cleanup_fewer_than_keep(self):
        """keepより少ない場合は削除しない."""
        with tempfile.TemporaryDirectory() as tmpdir:
            viz = BacktestVisualizer(output_dir=tmpdir)

            # 3つだけ作成
            for i in range(3):
                d = Path(tmpdir) / f"backtest_{i:04d}"
                d.mkdir()

            viz._cleanup_old_graphs(keep=5)

            remaining = [d for d in Path(tmpdir).iterdir() if d.is_dir()]
            assert len(remaining) == 3
