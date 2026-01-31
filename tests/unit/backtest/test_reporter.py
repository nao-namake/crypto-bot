"""
BacktestReporter and MLAnalyzer unit tests - Phase 62
Coverage target: 70%+

Tests for:
- BacktestReporter: レポート生成システム
- MLAnalyzer: ML予測分析システム
- TradeTracker: 追加のパフォーマンス指標計算
"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.backtest.reporter import BacktestReporter, MLAnalyzer, TradeTracker


class TestMLAnalyzerPredictionDistribution:
    """MLAnalyzer予測分布分析テスト"""

    def test_analyze_empty_predictions(self):
        """空の予測配列テスト"""
        analyzer = MLAnalyzer()
        predictions = np.array([])

        result = analyzer._analyze_prediction_distribution(predictions)

        assert result["total_predictions"] == 0
        assert result["sell_count"] == 0
        assert result["hold_count"] == 0
        assert result["buy_count"] == 0
        assert result["hold_target_met"] is True

    def test_analyze_prediction_distribution_basic(self):
        """基本的な予測分布テスト"""
        analyzer = MLAnalyzer()
        # 0=SELL, 1=HOLD, 2=BUY
        predictions = np.array([0, 0, 1, 1, 1, 2, 2, 2, 2, 2])

        result = analyzer._analyze_prediction_distribution(predictions)

        assert result["total_predictions"] == 10
        assert result["sell_count"] == 2
        assert result["hold_count"] == 3
        assert result["buy_count"] == 5
        assert result["sell_pct"] == 20.0
        assert result["hold_pct"] == 30.0
        assert result["buy_pct"] == 50.0
        assert result["hold_target_met"] is True  # 30% <= 60%

    def test_analyze_prediction_distribution_hold_target_fail(self):
        """HOLD比率が目標超過のテスト"""
        analyzer = MLAnalyzer()
        # HOLD比率 70% > 60%
        predictions = np.array([1, 1, 1, 1, 1, 1, 1, 0, 0, 2])

        result = analyzer._analyze_prediction_distribution(predictions)

        assert result["hold_pct"] == 70.0
        assert result["hold_target_met"] is False


class TestMLAnalyzerConfidenceStatistics:
    """MLAnalyzer信頼度統計テスト"""

    def test_analyze_empty_probabilities(self):
        """空の確率配列テスト"""
        analyzer = MLAnalyzer()
        probabilities = np.array([])

        result = analyzer._analyze_confidence_statistics(probabilities)

        assert result["avg_confidence"] == 0.0
        assert result["min_confidence"] == 0.0
        assert result["max_confidence"] == 0.0
        assert result["high_confidence_ratio"] == 0.0

    def test_analyze_confidence_statistics_basic(self):
        """基本的な信頼度統計テスト"""
        analyzer = MLAnalyzer()
        # 3クラスの確率分布
        probabilities = np.array([
            [0.1, 0.2, 0.7],  # confidence=0.7
            [0.2, 0.6, 0.2],  # confidence=0.6
            [0.8, 0.1, 0.1],  # confidence=0.8
            [0.3, 0.5, 0.2],  # confidence=0.5
        ])

        result = analyzer._analyze_confidence_statistics(probabilities)

        assert result["avg_confidence"] == 0.65  # (0.7+0.6+0.8+0.5)/4
        assert result["min_confidence"] == 0.5
        assert result["max_confidence"] == 0.8
        # high_confidence (>0.6): 0.7, 0.8 = 2/4 = 50%
        assert result["high_confidence_ratio"] == 50.0

    def test_analyze_confidence_all_high(self):
        """全て高信頼度のテスト"""
        analyzer = MLAnalyzer()
        probabilities = np.array([
            [0.1, 0.1, 0.8],
            [0.1, 0.8, 0.1],
            [0.9, 0.05, 0.05],
        ])

        result = analyzer._analyze_confidence_statistics(probabilities)

        assert result["high_confidence_ratio"] == 100.0


class TestMLAnalyzerStrategyAgreement:
    """MLAnalyzer戦略一致率テスト"""

    def test_analyze_empty_trades(self):
        """空の取引リストテスト"""
        analyzer = MLAnalyzer()

        result = analyzer._analyze_ml_strategy_agreement([])

        assert result["total_trades_with_ml"] == 0
        assert result["agreement_rate"] == 0.0

    def test_analyze_trades_without_ml(self):
        """ML情報なし取引テスト"""
        analyzer = MLAnalyzer()
        trades = [
            {"side": "buy", "pnl": 100},
            {"side": "sell", "pnl": -50},
        ]

        result = analyzer._analyze_ml_strategy_agreement(trades)

        assert result["total_trades_with_ml"] == 0

    def test_analyze_ml_strategy_agreement_basic(self):
        """基本的な一致率テスト"""
        analyzer = MLAnalyzer()
        trades = [
            {"side": "buy", "ml_prediction": 2, "pnl": 100},   # BUY一致・勝ち
            {"side": "sell", "ml_prediction": 0, "pnl": 50},   # SELL一致・勝ち
            {"side": "buy", "ml_prediction": 0, "pnl": -30},   # 不一致・負け
            {"side": "sell", "ml_prediction": 2, "pnl": -20},  # 不一致・負け
        ]

        result = analyzer._analyze_ml_strategy_agreement(trades)

        assert result["total_trades_with_ml"] == 4
        assert result["agreement_count"] == 2
        assert result["disagreement_count"] == 2
        assert result["agreement_rate"] == 50.0
        assert result["agreement_win_rate"] == 100.0   # 2勝/2取引
        assert result["disagreement_win_rate"] == 0.0  # 0勝/2取引
        assert result["agreement_avg_pnl"] == 75.0     # (100+50)/2
        assert result["disagreement_avg_pnl"] == -25.0 # (-30-20)/2


class TestMLAnalyzerFullAnalysis:
    """MLAnalyzer全体分析テスト"""

    def test_analyze_predictions_full(self):
        """完全分析テスト"""
        analyzer = MLAnalyzer()

        predictions = np.array([0, 1, 2, 2, 2])
        probabilities = np.array([
            [0.7, 0.2, 0.1],
            [0.2, 0.6, 0.2],
            [0.1, 0.2, 0.7],
            [0.1, 0.1, 0.8],
            [0.2, 0.3, 0.5],
        ])
        trades = [
            {"side": "buy", "ml_prediction": 2, "pnl": 100},
        ]

        result = analyzer.analyze_predictions(predictions, probabilities, trades)

        assert "prediction_distribution" in result
        assert "confidence_statistics" in result
        assert "ml_strategy_agreement" in result

        assert result["prediction_distribution"]["total_predictions"] == 5
        assert result["confidence_statistics"]["avg_confidence"] > 0


class TestMLAnalyzerLogSummary:
    """MLAnalyzerログ出力テスト"""

    def test_log_analysis_summary(self):
        """ログ出力テスト（例外なし確認）"""
        analyzer = MLAnalyzer()
        analysis = {
            "prediction_distribution": {
                "sell_count": 10,
                "hold_count": 30,
                "buy_count": 60,
                "sell_pct": 10.0,
                "hold_pct": 30.0,
                "buy_pct": 60.0,
                "hold_target_met": True,
            },
            "confidence_statistics": {
                "avg_confidence": 0.65,
                "high_confidence_ratio": 40.0,
            },
            "ml_strategy_agreement": {
                "total_trades_with_ml": 50,
                "agreement_rate": 75.0,
                "agreement_count": 38,
                "agreement_win_rate": 60.0,
                "disagreement_win_rate": 40.0,
            },
        }

        # 例外が発生しないことを確認
        analyzer.log_analysis_summary(analysis)

    def test_log_analysis_summary_no_ml_trades(self):
        """ML取引なしのログ出力テスト"""
        analyzer = MLAnalyzer()
        analysis = {
            "prediction_distribution": {
                "sell_count": 0,
                "hold_count": 0,
                "buy_count": 0,
                "sell_pct": 0.0,
                "hold_pct": 0.0,
                "buy_pct": 0.0,
                "hold_target_met": True,
            },
            "confidence_statistics": {
                "avg_confidence": 0.0,
                "high_confidence_ratio": 0.0,
            },
            "ml_strategy_agreement": {
                "total_trades_with_ml": 0,
            },
        }

        # 例外が発生しないことを確認
        analyzer.log_analysis_summary(analysis)


class TestTradeTrackerAdditionalMetrics:
    """TradeTracker追加指標テスト"""

    def test_calculate_sharpe_ratio_empty(self):
        """取引なし時のシャープレシオ"""
        tracker = TradeTracker()

        result = tracker._calculate_sharpe_ratio()

        assert result == 0.0

    def test_calculate_sharpe_ratio_single_trade(self):
        """1取引時のシャープレシオ"""
        tracker = TradeTracker()
        tracker.record_entry("t1", "buy", 0.001, 15000000, datetime.now(), "Test")
        tracker.record_exit("t1", 15100000, datetime.now(), "TP")

        result = tracker._calculate_sharpe_ratio()

        assert result == 0.0  # 2取引未満は0

    def test_calculate_sharpe_ratio_multiple_trades(self):
        """複数取引時のシャープレシオ"""
        tracker = TradeTracker()

        # 複数の取引を記録
        for i in range(5):
            tracker.record_entry(f"t{i}", "buy", 0.001, 15000000, datetime.now(), "Test")
            exit_price = 15100000 if i % 2 == 0 else 14900000
            tracker.record_exit(f"t{i}", exit_price, datetime.now(), "TP")

        result = tracker._calculate_sharpe_ratio()

        # 計算結果が返される（具体的な値はロジック依存）
        assert isinstance(result, float)

    def test_calculate_sharpe_ratio_zero_std(self):
        """標準偏差0の場合"""
        tracker = TradeTracker()

        # 全て同じPnLの取引
        for i in range(3):
            tracker.record_entry(f"t{i}", "buy", 0.001, 15000000, datetime.now(), "Test")
            tracker.record_exit(f"t{i}", 15100000, datetime.now(), "TP")

        result = tracker._calculate_sharpe_ratio()

        assert result == 0.0

    def test_calculate_sortino_ratio_empty(self):
        """取引なし時のソルティノレシオ"""
        tracker = TradeTracker()

        result = tracker._calculate_sortino_ratio()

        assert result == 0.0

    def test_calculate_sortino_ratio_no_losses(self):
        """損失なし時のソルティノレシオ"""
        tracker = TradeTracker()

        # 全て勝ち取引
        for i in range(3):
            tracker.record_entry(f"t{i}", "buy", 0.001, 15000000, datetime.now(), "Test")
            tracker.record_exit(f"t{i}", 15100000, datetime.now(), "TP")

        result = tracker._calculate_sortino_ratio()

        assert result == float("inf")  # 負のリターンなし、利益あり

    def test_calculate_sortino_ratio_with_losses(self):
        """損失あり時のソルティノレシオ"""
        tracker = TradeTracker()

        # 勝ち負け混在
        tracker.record_entry("t1", "buy", 0.001, 15000000, datetime.now(), "Test")
        tracker.record_exit("t1", 15100000, datetime.now(), "TP")

        tracker.record_entry("t2", "buy", 0.001, 15000000, datetime.now(), "Test")
        tracker.record_exit("t2", 14900000, datetime.now(), "SL")

        result = tracker._calculate_sortino_ratio()

        assert isinstance(result, float)

    def test_calculate_calmar_ratio_empty(self):
        """取引なし時のカルマーレシオ"""
        tracker = TradeTracker()

        result = tracker._calculate_calmar_ratio(0.0)

        assert result == 0.0

    def test_calculate_calmar_ratio_zero_dd(self):
        """DD=0時のカルマーレシオ"""
        tracker = TradeTracker()

        # 利益のみの取引
        tracker.record_entry("t1", "buy", 0.001, 15000000, datetime.now(), "Test")
        tracker.record_exit("t1", 15100000, datetime.now(), "TP")

        result = tracker._calculate_calmar_ratio(0.0)

        assert result == float("inf")

    def test_calculate_calmar_ratio_with_dd(self):
        """DD>0時のカルマーレシオ"""
        tracker = TradeTracker()

        tracker.record_entry("t1", "buy", 0.001, 15000000, datetime.now(), "Test")
        tracker.record_exit("t1", 15100000, datetime.now(), "TP")

        result = tracker._calculate_calmar_ratio(5.0)

        assert isinstance(result, float)
        assert result > 0

    def test_calculate_consecutive_streaks_empty(self):
        """取引なし時の連勝連敗"""
        tracker = TradeTracker()

        wins, losses = tracker._calculate_consecutive_streaks()

        assert wins == 0
        assert losses == 0

    def test_calculate_consecutive_streaks_basic(self):
        """基本的な連勝連敗計算"""
        tracker = TradeTracker()

        # 3連勝、2連敗、1勝
        for i in range(3):  # 3連勝
            tracker.record_entry(f"w{i}", "buy", 0.001, 15000000, datetime.now(), "Test")
            tracker.record_exit(f"w{i}", 15100000, datetime.now(), "TP")

        for i in range(2):  # 2連敗
            tracker.record_entry(f"l{i}", "buy", 0.001, 15000000, datetime.now(), "Test")
            tracker.record_exit(f"l{i}", 14900000, datetime.now(), "SL")

        tracker.record_entry("w3", "buy", 0.001, 15000000, datetime.now(), "Test")
        tracker.record_exit("w3", 15100000, datetime.now(), "TP")  # 1勝

        wins, losses = tracker._calculate_consecutive_streaks()

        assert wins == 3
        assert losses == 2

    def test_calculate_consecutive_streaks_zero_pnl(self):
        """損益0の取引がある場合"""
        tracker = TradeTracker()

        tracker.record_entry("t1", "buy", 0.001, 15000000, datetime.now(), "Test")
        tracker.record_exit("t1", 15100000, datetime.now(), "TP")

        tracker.record_entry("t2", "buy", 0.001, 15000000, datetime.now(), "Test")
        tracker.record_exit("t2", 15000000, datetime.now(), "close")  # 損益0

        tracker.record_entry("t3", "buy", 0.001, 15000000, datetime.now(), "Test")
        tracker.record_exit("t3", 15100000, datetime.now(), "TP")

        wins, losses = tracker._calculate_consecutive_streaks()

        # 損益0はカウントしないため、連勝が継続
        assert wins == 2
        assert losses == 0

    def test_calculate_trades_per_month_empty(self):
        """取引なし時の月間取引数"""
        tracker = TradeTracker()

        result = tracker._calculate_trades_per_month()

        assert result == 0.0

    def test_calculate_trades_per_month_with_dates(self):
        """期間指定ありの月間取引数"""
        tracker = TradeTracker()

        for i in range(10):
            tracker.record_entry(f"t{i}", "buy", 0.001, 15000000, datetime.now(), "Test")
            tracker.record_exit(f"t{i}", 15100000, datetime.now(), "TP")

        start = datetime(2025, 1, 1)
        end = datetime(2025, 3, 1)  # 2ヶ月

        result = tracker._calculate_trades_per_month(start, end)

        # 10取引 / 2ヶ月 = 5取引/月
        assert result == pytest.approx(5.0, rel=0.1)

    def test_calculate_trades_per_month_iso_string(self):
        """ISO文字列での期間指定"""
        tracker = TradeTracker()

        for i in range(6):
            tracker.record_entry(f"t{i}", "buy", 0.001, 15000000, datetime.now(), "Test")
            tracker.record_exit(f"t{i}", 15100000, datetime.now(), "TP")

        result = tracker._calculate_trades_per_month(
            "2025-01-01T00:00:00", "2025-02-01T00:00:00"
        )

        # 6取引 / 1ヶ月 = 6取引/月
        assert result == pytest.approx(6.0, rel=0.2)


class TestTradeTrackerMaxDrawdown:
    """最大ドローダウン計算テスト"""

    def test_max_drawdown_empty(self):
        """取引なし時のDD"""
        tracker = TradeTracker()

        dd, dd_pct = tracker._calculate_max_drawdown()

        assert dd == 0.0
        assert dd_pct == 0.0

    def test_max_drawdown_no_loss(self):
        """損失なし時のDD"""
        tracker = TradeTracker()

        for i in range(3):
            tracker.record_entry(f"t{i}", "buy", 0.001, 15000000, datetime.now(), "Test")
            tracker.record_exit(f"t{i}", 15100000, datetime.now(), "TP")

        dd, dd_pct = tracker._calculate_max_drawdown()

        assert dd == 0.0
        assert dd_pct == 0.0

    def test_max_drawdown_with_loss(self):
        """損失ありのDD計算"""
        tracker = TradeTracker()

        # 勝ち→負け→勝ち
        tracker.record_entry("t1", "buy", 0.01, 15000000, datetime.now(), "Test")
        tracker.record_exit("t1", 15100000, datetime.now(), "TP")  # +1000

        tracker.record_entry("t2", "buy", 0.01, 15000000, datetime.now(), "Test")
        tracker.record_exit("t2", 14800000, datetime.now(), "SL")  # -2000

        tracker.record_entry("t3", "buy", 0.01, 15000000, datetime.now(), "Test")
        tracker.record_exit("t3", 15100000, datetime.now(), "TP")  # +1000

        dd, dd_pct = tracker._calculate_max_drawdown()

        # ピーク1000から-1000まで下落 = DD 2000
        assert dd == 2000
        assert dd_pct > 0


class TestTradeTrackerMFEMAEStatistics:
    """MFE/MAE統計計算テスト"""

    def test_mfe_mae_statistics_empty(self):
        """取引なし時のMFE/MAE統計"""
        tracker = TradeTracker()

        result = tracker._calculate_mfe_mae_statistics()

        assert result["avg_mfe"] == 0.0
        assert result["avg_mae"] == 0.0
        assert result["mfe_capture_ratio"] == 0.0

    def test_mfe_mae_statistics_no_excursion_data(self):
        """MFE/MAEデータなし取引"""
        tracker = TradeTracker()
        tracker.completed_trades = [
            {"pnl": 100, "mfe": None, "mae": None},
        ]

        result = tracker._calculate_mfe_mae_statistics()

        assert result["avg_mfe"] == 0.0

    def test_mfe_mae_capture_ratio(self):
        """MFE捕捉率計算"""
        tracker = TradeTracker()

        # MFE 200, 実際のPnL 100 → 捕捉率 50%
        tracker.record_entry("t1", "buy", 0.001, 15000000, datetime.now(), "Test")
        tracker.update_price_excursions(15200000, 14900000)
        tracker.record_exit("t1", 15100000, datetime.now(), "TP")

        result = tracker._calculate_mfe_mae_statistics()

        # 実際PnL 100、MFE 200 → 捕捉率 50%
        assert result["mfe_capture_ratio"] == pytest.approx(50.0, rel=0.1)


class TestBacktestReporterInit:
    """BacktestReporter初期化テスト"""

    def test_init_default_output_dir(self):
        """デフォルト出力ディレクトリテスト"""
        reporter = BacktestReporter()

        assert reporter.output_dir.exists()
        assert "logs" in str(reporter.output_dir)

    def test_init_custom_output_dir(self):
        """カスタム出力ディレクトリテスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            reporter = BacktestReporter(output_dir=tmpdir)

            assert reporter.output_dir == Path(tmpdir)
            assert reporter.output_dir.exists()


class TestBacktestReporterProgressReport:
    """進捗レポートテスト"""

    @pytest.mark.asyncio
    async def test_save_progress_report(self):
        """進捗レポート保存テスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            reporter = BacktestReporter(output_dir=tmpdir)

            progress_stats = {
                "current_cycle": 100,
                "total_cycles": 500,
                "progress_pct": 20.0,
            }

            filepath = await reporter.save_progress_report(progress_stats)

            assert Path(filepath).exists()
            with open(filepath, "r") as f:
                data = json.load(f)
            assert data["current_cycle"] == 100


class TestBacktestReporterErrorReport:
    """エラーレポートテスト"""

    @pytest.mark.asyncio
    async def test_save_error_report(self):
        """エラーレポート保存テスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            reporter = BacktestReporter(output_dir=tmpdir)

            filepath = await reporter.save_error_report(
                error_message="Test error occurred",
                context={"phase": "test", "step": 1}
            )

            assert Path(filepath).exists()
            with open(filepath, "r") as f:
                data = json.load(f)
            assert data["error_message"] == "Test error occurred"
            assert data["context"]["phase"] == "test"


class TestBacktestReporterTextReport:
    """テキストレポート生成テスト"""

    @pytest.mark.asyncio
    async def test_generate_text_report(self):
        """テキストレポート生成テスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            reporter = BacktestReporter(output_dir=tmpdir)

            report_data = {
                "backtest_info": {
                    "duration_days": 60,
                    "generated_at": datetime.now().isoformat(),
                },
                "performance_metrics": {
                    "total_trades": 100,
                    "winning_trades": 60,
                    "losing_trades": 40,
                    "win_rate": 60.0,
                    "total_pnl": 50000,
                    "total_profit": 100000,
                    "total_loss": -50000,
                    "profit_factor": 2.0,
                    "max_drawdown": 10000,
                    "max_drawdown_pct": 2.0,
                    "average_win": 1666,
                    "average_loss": -1250,
                },
                "execution_stats": {
                    "data_processing": {
                        "processed_cycles": 1000,
                        "total_data_points": 5000,
                    },
                },
            }

            filepath = Path(tmpdir) / "test_report.txt"
            await reporter._generate_text_report(
                filepath, report_data, "2025-01-01", "2025-03-01"
            )

            assert filepath.exists()
            content = filepath.read_text()
            assert "バックテストレポート" in content
            assert "総取引数: 100回" in content
            assert "勝率: 60.00%" in content


class TestBacktestReporterFullReport:
    """バックテストレポート生成テスト"""

    @pytest.mark.asyncio
    async def test_generate_backtest_report_basic(self):
        """基本的なレポート生成テスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            reporter = BacktestReporter(output_dir=tmpdir)

            # いくつかの取引を記録
            reporter.trade_tracker.record_entry(
                "t1", "buy", 0.001, 15000000, datetime.now(), "Test", regime="tight_range"
            )
            reporter.trade_tracker.record_exit("t1", 15100000, datetime.now(), "TP")

            final_stats = {
                "data_processing": {
                    "processed_cycles": 100,
                    "total_data_points": 500,
                }
            }

            with patch.object(reporter, "_generate_text_report", return_value=None):
                filepath = await reporter.generate_backtest_report(
                    final_stats=final_stats,
                    start_date=datetime(2025, 1, 1),
                    end_date=datetime(2025, 3, 1),
                )

            assert Path(filepath).exists()
            with open(filepath, "r") as f:
                data = json.load(f)

            assert "backtest_info" in data
            assert "performance_metrics" in data
            assert "regime_performance" in data
            assert data["completed_trades"] == 1

    @pytest.mark.asyncio
    async def test_generate_backtest_report_with_ml_data(self):
        """ML分析付きレポート生成テスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            reporter = BacktestReporter(output_dir=tmpdir)

            # 取引を記録
            reporter.trade_tracker.record_entry(
                "t1", "buy", 0.001, 15000000, datetime.now(), "Test",
                ml_prediction=2, ml_confidence=0.75
            )
            reporter.trade_tracker.record_exit("t1", 15100000, datetime.now(), "TP")

            final_stats = {"data_processing": {}}

            ml_predictions_data = {
                "predictions": np.array([0, 1, 2, 2, 2]),
                "probabilities": np.array([
                    [0.7, 0.2, 0.1],
                    [0.2, 0.6, 0.2],
                    [0.1, 0.2, 0.7],
                    [0.1, 0.1, 0.8],
                    [0.2, 0.2, 0.6],
                ]),
            }

            with patch.object(reporter, "_generate_text_report", return_value=None):
                filepath = await reporter.generate_backtest_report(
                    final_stats=final_stats,
                    start_date=datetime(2025, 1, 1),
                    end_date=datetime(2025, 3, 1),
                    ml_predictions_data=ml_predictions_data,
                )

            with open(filepath, "r") as f:
                data = json.load(f)

            assert "ml_analysis" in data
            assert "prediction_distribution" in data["ml_analysis"]

    @pytest.mark.asyncio
    async def test_generate_backtest_report_string_dates(self):
        """ISO文字列日付でのレポート生成テスト"""
        with tempfile.TemporaryDirectory() as tmpdir:
            reporter = BacktestReporter(output_dir=tmpdir)

            final_stats = {"data_processing": {}}

            with patch.object(reporter, "_generate_text_report", return_value=None):
                filepath = await reporter.generate_backtest_report(
                    final_stats=final_stats,
                    start_date="2025-01-01T00:00:00Z",
                    end_date="2025-03-01T00:00:00Z",
                )

            with open(filepath, "r") as f:
                data = json.load(f)

            assert data["backtest_info"]["start_date"] == "2025-01-01T00:00:00Z"
            assert data["backtest_info"]["duration_days"] == 59


class TestTradeTrackerHoldingPeriod:
    """保有期間計算テスト"""

    def test_holding_period_datetime(self):
        """datetime型でのホールディング期間"""
        tracker = TradeTracker()
        entry_time = datetime(2025, 1, 1, 10, 0, 0)
        exit_time = datetime(2025, 1, 1, 10, 30, 0)

        tracker.record_entry("t1", "buy", 0.001, 15000000, entry_time, "Test")
        trade = tracker.record_exit("t1", 15100000, exit_time, "TP")

        assert trade["holding_period"] == pytest.approx(30.0, rel=0.01)

    def test_holding_period_timestamp(self):
        """Unix timestamp型でのホールディング期間"""
        tracker = TradeTracker()
        entry_time = 1704096000  # Unix timestamp
        exit_time = entry_time + 1800  # +30分

        tracker.record_entry("t1", "buy", 0.001, 15000000, entry_time, "Test")
        trade = tracker.record_exit("t1", 15100000, exit_time, "TP")

        assert trade["holding_period"] == pytest.approx(30.0, rel=0.01)


class TestTradeTrackerMLInfo:
    """ML情報記録テスト"""

    def test_record_entry_with_ml_info(self):
        """ML情報付きエントリー記録"""
        tracker = TradeTracker()

        tracker.record_entry(
            order_id="t1",
            side="buy",
            amount=0.001,
            price=15000000,
            timestamp=datetime.now(),
            strategy="Test",
            regime="tight_range",
            ml_prediction=2,
            ml_confidence=0.85,
            adjusted_confidence=0.80,
        )

        entry = tracker.open_entries["t1"]
        assert entry["ml_prediction"] == 2
        assert entry["ml_confidence"] == 0.85
        assert entry["adjusted_confidence"] == 0.80

    def test_record_exit_preserves_ml_info(self):
        """決済時にML情報が保持されるテスト"""
        tracker = TradeTracker()

        tracker.record_entry(
            "t1", "buy", 0.001, 15000000, datetime.now(), "Test",
            ml_prediction=2, ml_confidence=0.85, adjusted_confidence=0.80
        )
        trade = tracker.record_exit("t1", 15100000, datetime.now(), "TP")

        assert trade["ml_prediction"] == 2
        assert trade["ml_confidence"] == 0.85
        assert trade["adjusted_confidence"] == 0.80


class TestTradeTrackerInfiniteValues:
    """無限大値のテスト（Phase 57.7）"""

    def test_profit_factor_infinite_no_loss(self):
        """損失なし時のPFは無限大"""
        tracker = TradeTracker()

        tracker.record_entry("t1", "buy", 0.001, 15000000, datetime.now(), "Test")
        tracker.record_exit("t1", 15100000, datetime.now(), "TP")

        metrics = tracker.get_performance_metrics()

        assert metrics["profit_factor"] == float("inf")

    def test_payoff_ratio_infinite_no_loss(self):
        """損失なし時のペイオフレシオは無限大"""
        tracker = TradeTracker()

        tracker.record_entry("t1", "buy", 0.001, 15000000, datetime.now(), "Test")
        tracker.record_exit("t1", 15100000, datetime.now(), "TP")

        metrics = tracker.get_performance_metrics()

        assert metrics["payoff_ratio"] == float("inf")

    def test_recovery_factor_infinite_no_dd(self):
        """DD=0時のリカバリーファクターは無限大"""
        tracker = TradeTracker()

        tracker.record_entry("t1", "buy", 0.001, 15000000, datetime.now(), "Test")
        tracker.record_exit("t1", 15100000, datetime.now(), "TP")

        metrics = tracker.get_performance_metrics()

        assert metrics["recovery_factor"] == float("inf")
