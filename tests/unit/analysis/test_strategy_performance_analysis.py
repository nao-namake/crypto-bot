"""
戦略個別パフォーマンス分析のテスト - Phase 51.4

Phase 51.4-Day1: 基本メトリクス計算のテスト
Phase 51.4-Day2以降: レジーム別分析・相関分析・貢献度測定のテスト追加予定
"""

import sys
from pathlib import Path

import pytest

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from scripts.analysis.strategy_performance_analysis import (
    PerformanceMetrics,
    StrategyPerformanceAnalyzer,
)


class TestStrategyPerformanceAnalyzer:
    """StrategyPerformanceAnalyzer のテスト"""

    @pytest.fixture
    def analyzer(self):
        """StrategyPerformanceAnalyzer インスタンスを返すfixture"""
        return StrategyPerformanceAnalyzer()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 基本メトリクス計算テスト
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_calculate_basic_metrics_winning_trades(self, analyzer):
        """勝ちトレードのみのメトリクス計算が正しいことを確認"""
        trades = [
            {"pnl": 1000, "holding_period": 60},
            {"pnl": 1500, "holding_period": 120},
            {"pnl": 2000, "holding_period": 90},
        ]

        metrics = analyzer.calculate_basic_metrics(trades, "TestStrategy")

        assert metrics.strategy_name == "TestStrategy"
        assert metrics.total_trades == 3
        assert metrics.winning_trades == 3
        assert metrics.losing_trades == 0
        assert metrics.win_rate == 1.0  # 100%勝率
        assert metrics.total_pnl == 4500
        assert metrics.avg_win == 1500.0
        assert metrics.avg_loss == 0.0
        assert metrics.profit_factor == 0.0  # 負けトレードなしの場合は0
        assert metrics.avg_holding_period == 90.0

    def test_calculate_basic_metrics_losing_trades(self, analyzer):
        """負けトレードのみのメトリクス計算が正しいことを確認"""
        trades = [
            {"pnl": -1000, "holding_period": 60},
            {"pnl": -1500, "holding_period": 120},
        ]

        metrics = analyzer.calculate_basic_metrics(trades, "TestStrategy")

        assert metrics.total_trades == 2
        assert metrics.winning_trades == 0
        assert metrics.losing_trades == 2
        assert metrics.win_rate == 0.0  # 0%勝率
        assert metrics.total_pnl == -2500
        assert metrics.avg_win == 0.0
        assert metrics.avg_loss == -1250.0
        assert metrics.profit_factor == 0.0  # 勝ちトレードなしの場合は0

    def test_calculate_basic_metrics_mixed_trades(self, analyzer):
        """勝ち負け混合トレードのメトリクス計算が正しいことを確認"""
        trades = [
            {"pnl": 1000, "holding_period": 60},
            {"pnl": -500, "holding_period": 120},
            {"pnl": 1500, "holding_period": 90},
            {"pnl": -800, "holding_period": 150},
            {"pnl": 2000, "holding_period": 180},
        ]

        metrics = analyzer.calculate_basic_metrics(trades, "TestStrategy")

        assert metrics.total_trades == 5
        assert metrics.winning_trades == 3
        assert metrics.losing_trades == 2
        assert metrics.win_rate == 0.6  # 60%勝率
        assert metrics.total_pnl == 3200
        assert metrics.avg_win == 1500.0  # (1000 + 1500 + 2000) / 3
        assert metrics.avg_loss == -650.0  # (-500 + -800) / 2
        assert metrics.profit_factor > 0  # 勝ち総額 / 負け総額

    def test_calculate_basic_metrics_empty_trades(self, analyzer):
        """空の取引リストで正しくハンドリングされることを確認"""
        trades = []

        metrics = analyzer.calculate_basic_metrics(trades, "TestStrategy")

        assert metrics.total_trades == 0
        assert metrics.winning_trades == 0
        assert metrics.losing_trades == 0
        assert metrics.win_rate == 0.0
        assert metrics.total_pnl == 0.0
        assert metrics.profit_factor == 0.0

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # シャープレシオ計算テスト
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_calculate_sharpe_ratio_positive_returns(self, analyzer):
        """正のリターンでシャープレシオが計算されることを確認"""
        pnls = [100, 150, 120, 180, 110]

        sharpe = analyzer._calculate_sharpe_ratio(pnls)

        assert sharpe > 0  # 正のリターンなのでシャープレシオも正
        assert isinstance(sharpe, float)

    def test_calculate_sharpe_ratio_negative_returns(self, analyzer):
        """負のリターンでシャープレシオが負になることを確認"""
        pnls = [-100, -150, -120, -180, -110]

        sharpe = analyzer._calculate_sharpe_ratio(pnls)

        assert sharpe < 0  # 負のリターンなのでシャープレシオも負

    def test_calculate_sharpe_ratio_no_variance(self, analyzer):
        """リターンの分散が0の場合にシャープレシオが0になることを確認"""
        pnls = [100, 100, 100, 100, 100]

        sharpe = analyzer._calculate_sharpe_ratio(pnls)

        assert sharpe == 0.0  # 分散0の場合はシャープレシオ0

    def test_calculate_sharpe_ratio_empty_list(self, analyzer):
        """空のリストでシャープレシオが0になることを確認"""
        pnls = []

        sharpe = analyzer._calculate_sharpe_ratio(pnls)

        assert sharpe == 0.0

    def test_calculate_sharpe_ratio_single_value(self, analyzer):
        """単一値でシャープレシオが0になることを確認"""
        pnls = [100]

        sharpe = analyzer._calculate_sharpe_ratio(pnls)

        assert sharpe == 0.0  # 標準偏差計算不可の場合は0

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 最大ドローダウン計算テスト
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_calculate_max_drawdown_with_drawdown(self, analyzer):
        """ドローダウンが発生する場合に最大DDが計算されることを確認"""
        # エクイティカーブ: 0 → 100 → 50 → 150 → 30 → 200
        # 累積PnL: 100, -50, 100, -120, 170
        pnls = [100, -50, 100, -120, 170]

        max_dd = analyzer._calculate_max_drawdown(pnls)

        # 最大エクイティ150から30への下落 = 120
        assert max_dd > 0
        assert isinstance(max_dd, float)

    def test_calculate_max_drawdown_no_drawdown(self, analyzer):
        """ドローダウンが発生しない場合にDDが0になることを確認"""
        # 常に右肩上がり
        pnls = [100, 150, 200, 250, 300]

        max_dd = analyzer._calculate_max_drawdown(pnls)

        assert max_dd == 0.0

    def test_calculate_max_drawdown_empty_list(self, analyzer):
        """空のリストでDDが0になることを確認"""
        pnls = []

        max_dd = analyzer._calculate_max_drawdown(pnls)

        assert max_dd == 0.0

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 統合テスト
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_performance_metrics_dataclass(self):
        """PerformanceMetrics データクラスが正しく動作することを確認"""
        metrics = PerformanceMetrics(
            strategy_name="TestStrategy",
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
            win_rate=0.6,
            total_pnl=5000.0,
            avg_win=1500.0,
            avg_loss=-800.0,
            profit_factor=1.8,
            sharpe_ratio=2.5,
            max_drawdown=1200.0,
            avg_holding_period=120.0,
        )

        assert metrics.strategy_name == "TestStrategy"
        assert metrics.total_trades == 10
        assert metrics.win_rate == 0.6
        assert metrics.sharpe_ratio == 2.5

    def test_analyzer_strategies_list(self, analyzer):
        """アナライザーが6戦略を認識していることを確認 - Phase 51.7 Day 7"""
        assert len(analyzer.strategies) == 6
        assert "ATRBased" in analyzer.strategies
        assert "DonchianChannel" in analyzer.strategies
        assert "ADXTrendStrength" in analyzer.strategies
        assert "BBReversal" in analyzer.strategies
        assert "StochasticReversal" in analyzer.strategies
        assert "MACDEMACrossover" in analyzer.strategies


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Phase 51.4-Day2テスト（実装済み）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestStrategyPerformanceAnalyzerDay2:
    """StrategyPerformanceAnalyzer Day2機能のテスト"""

    @pytest.fixture
    def analyzer(self):
        """StrategyPerformanceAnalyzer インスタンスを返すfixture"""
        return StrategyPerformanceAnalyzer()

    @pytest.fixture
    def sample_historical_data(self):
        """サンプル履歴データを返すfixture - Phase 51.5-A修正（datetime indexとtimestampカラム）"""
        from datetime import datetime, timedelta

        import pandas as pd

        # 100行のサンプルデータ生成
        base_time = datetime(2025, 1, 1)
        timestamps = [base_time + timedelta(hours=4 * i) for i in range(100)]

        data = {
            "timestamp": timestamps,  # バックテスト関数で期待されるカラム
            "open": [10000000 + i * 1000 for i in range(100)],
            "high": [10050000 + i * 1000 for i in range(100)],
            "low": [9950000 + i * 1000 for i in range(100)],
            "close": [10000000 + i * 1000 for i in range(100)],
            "volume": [100 for i in range(100)],
        }
        df = pd.DataFrame(data)
        # datetimeをindexとして設定（feature_generator.pyが期待）
        df.index = pd.DatetimeIndex(timestamps, name="datetime")
        return df

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 実バックテスト統合テスト
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_get_strategy_instance_valid(self, analyzer):
        """戦略インスタンス生成が正しく動作することを確認"""
        strategy = analyzer._get_strategy_instance("ATRBased")
        assert strategy is not None
        assert hasattr(strategy, "analyze")

    def test_get_strategy_instance_invalid(self, analyzer):
        """未知の戦略名でエラーが発生することを確認 - Phase 51.7 Day 7"""
        from src.core.exceptions import StrategyError

        with pytest.raises(StrategyError, match="が見つかりません"):
            analyzer._get_strategy_instance("UnknownStrategy")

    @pytest.mark.asyncio
    async def test_run_single_strategy_backtest_basic(self, analyzer, sample_historical_data):
        """単一戦略バックテストが正常動作することを確認"""
        trades = await analyzer._run_single_strategy_backtest("ATRBased", sample_historical_data)

        # 取引リストが返されることを確認
        assert isinstance(trades, list)

        # 各取引に必要なフィールドがあることを確認
        if len(trades) > 0:
            trade = trades[0]
            assert "pnl" in trade
            assert "holding_period" in trade
            assert "order_id" in trade
            assert "side" in trade

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # レジーム別分析テスト
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    @pytest.mark.asyncio
    async def test_analyze_regime_performance_structure(self, analyzer, sample_historical_data):
        """レジーム別分析が正しい構造を返すことを確認"""
        from src.core.services.regime_types import RegimeType

        regime_metrics = await analyzer.analyze_regime_performance("ATRBased", sample_historical_data)

        # 4レジーム分のメトリクスが返されることを確認
        assert isinstance(regime_metrics, dict)
        assert len(regime_metrics) == 4

        # 各レジームのメトリクスが存在することを確認
        for regime in RegimeType:
            assert regime in regime_metrics
            metrics = regime_metrics[regime]
            assert hasattr(metrics, "total_trades")
            assert hasattr(metrics, "win_rate")
            assert hasattr(metrics, "sharpe_ratio")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 戦略間相関分析テスト
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_calculate_strategy_correlation_structure(self, analyzer):
        """相関分析が正しい構造を返すことを確認 - Phase 51.7 Day 7: 6戦略構成"""
        import pandas as pd

        # サンプル取引データ - Phase 51.7 Day 7: 6戦略
        all_strategy_trades = {
            "ATRBased": [{"exit_timestamp": "2025-01-01 00:00:00", "pnl": 1000}],
            "DonchianChannel": [{"exit_timestamp": "2025-01-01 00:00:00", "pnl": 800}],
            "ADXTrendStrength": [{"exit_timestamp": "2025-01-01 00:00:00", "pnl": -300}],
            "BBReversal": [{"exit_timestamp": "2025-01-01 00:00:00", "pnl": 500}],
            "StochasticReversal": [{"exit_timestamp": "2025-01-01 00:00:00", "pnl": 600}],
            "MACDEMACrossover": [{"exit_timestamp": "2025-01-01 00:00:00", "pnl": -200}],
        }

        corr_df = analyzer.calculate_strategy_correlation(all_strategy_trades)

        # DataFrameが6x6であることを確認 - Phase 51.7 Day 7
        assert isinstance(corr_df, pd.DataFrame)
        assert corr_df.shape == (6, 6)

        # 対角要素が1.0であることを確認（自己相関）
        for strategy in analyzer.strategies:
            assert abs(corr_df.loc[strategy, strategy] - 1.0) < 0.01

    def test_calculate_strategy_correlation_empty_data(self, analyzer):
        """空データで相関分析が正常動作することを確認"""
        import pandas as pd

        # 空の取引データ
        all_strategy_trades = {s: [] for s in analyzer.strategies}

        corr_df = analyzer.calculate_strategy_correlation(all_strategy_trades)

        # 単位行列が返されることを確認 - Phase 51.7 Day 7: 6戦略構成
        assert isinstance(corr_df, pd.DataFrame)
        assert corr_df.shape == (6, 6)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # アンサンブル貢献度測定テスト
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    @pytest.mark.asyncio
    async def test_measure_ensemble_contribution_structure(self, analyzer, sample_historical_data):
        """貢献度測定が正しい構造を返すことを確認 - Phase 51.7 Day 7: 6戦略構成"""
        contribution_results = await analyzer.measure_ensemble_contribution(sample_historical_data)

        # 6戦略分の貢献度が返されることを確認 - Phase 51.7 Day 7
        assert isinstance(contribution_results, dict)
        assert len(contribution_results) == 6

        # 各戦略の貢献度指標が存在することを確認
        for strategy in analyzer.strategies:
            assert strategy in contribution_results
            result = contribution_results[strategy]
            assert "baseline_sharpe" in result
            assert "without_sharpe" in result
            assert "contribution" in result
            assert "contribution_pct" in result
            assert "num_trades" in result

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 統合テスト
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    @pytest.mark.asyncio
    async def test_integration_all_analyses(self, analyzer, sample_historical_data):
        """全分析機能が連携して動作することを確認 - Phase 51.7 Day 7: 6戦略構成"""
        # 基本分析
        metrics = await analyzer.analyze_single_strategy("ATRBased", sample_historical_data)
        assert metrics.strategy_name == "ATRBased"

        # レジーム別分析
        regime_metrics = await analyzer.analyze_regime_performance("ATRBased", sample_historical_data)
        assert len(regime_metrics) == 4

        # 相関分析（簡易版）- Phase 51.7 Day 7: 6戦略構成
        all_strategy_trades = {s: [{"exit_timestamp": "2025-01-01 00:00:00", "pnl": 1000}] for s in analyzer.strategies}
        corr_df = analyzer.calculate_strategy_correlation(all_strategy_trades)
        assert corr_df.shape == (6, 6)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Phase 51.4-Day3以降のテスト（未実装）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# TODO: Phase 51.4-Day3実装時に追加
# - test_generate_visualizations()
# - test_generate_full_report()
# - test_identify_deletion_candidates()
