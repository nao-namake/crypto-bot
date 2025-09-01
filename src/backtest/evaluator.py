"""
バックテスト評価システム - Phase 12・CI/CD統合・手動実行監視・段階的デプロイ対応

レガシー評価機能の良い部分を継承し、包括的な性能分析を提供。
ウォークフォワード検証、統計的指標計算、リスク分析を統合。

レガシー継承機能:
- max_drawdown計算
- CAGR計算
- ウォークフォワード検証
- 基本統計指標

Phase 12新システム統合:
- Phase 1-11戦略との整合性・GitHub Actions対応
- リアルタイム評価・手動実行監視対応
- 詳細レポート生成・CI/CD品質ゲート対応
- 比較分析機能・段階的デプロイ対応.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..core.config import get_backtest_config
from ..core.logger import get_logger
from .engine import TradeRecord


@dataclass
class PerformanceMetrics:
    """
    パフォーマンス指標

    バックテストとペーパートレードで共通使用する
    包括的な性能評価指標。.
    """

    # 基本指標
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float

    # 損益指標
    total_profit: float
    average_profit: float
    profit_factor: float  # 総利益 / 総損失

    # リターン指標
    total_return: float
    annualized_return: float
    cagr: float  # 年間複利成長率

    # リスク指標
    max_drawdown: float
    max_drawdown_duration: int  # 日数
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float

    # 取引指標
    average_trade_duration: float  # 時間
    max_consecutive_wins: int
    max_consecutive_losses: int

    # 分析期間
    start_date: datetime
    end_date: datetime
    analysis_period_days: int

    # 詳細統計
    trade_distribution: Dict[str, Any] = field(default_factory=dict)
    monthly_returns: List[float] = field(default_factory=list)
    drawdown_periods: List[Dict[str, Any]] = field(default_factory=list)


class BacktestEvaluator:
    """
    バックテスト評価システム

    取引記録とエクイティカーブから包括的な性能分析を実行。
    レガシーシステムの評価ロジックを継承・改良。.
    """

    def __init__(self, risk_free_rate: Optional[float] = None):
        self.logger = get_logger(__name__)
        # リスクフリーレート設定（Phase 16-B：設定ファイル参照）
        if risk_free_rate is None:
            risk_free_rate = get_backtest_config("risk_free_rate", 0.001)
        self.risk_free_rate = risk_free_rate

    def evaluate_performance(
        self,
        trade_records: List[TradeRecord],
        equity_curve: List[Tuple[datetime, float]],
        initial_balance: float,
    ) -> PerformanceMetrics:
        """
        包括的パフォーマンス評価

        Args:
            trade_records: 取引記録リスト
            equity_curve: エクイティカーブ（時刻, 残高）
            initial_balance: 初期残高

        Returns:
            包括的パフォーマンス指標.
        """
        if not trade_records or not equity_curve:
            return self._create_empty_metrics()

        self.logger.info(f"パフォーマンス評価開始: {len(trade_records)}取引")

        # 基本統計
        basic_stats = self._calculate_basic_stats(trade_records)

        # リターン分析
        return_metrics = self._calculate_return_metrics(equity_curve, initial_balance)

        # リスク分析
        risk_metrics = self._calculate_risk_metrics(trade_records, equity_curve, initial_balance)

        # 取引分析
        trade_metrics = self._calculate_trade_metrics(trade_records)

        # 期間分析
        period_info = self._calculate_period_info(equity_curve)

        # 統合メトリクス作成
        metrics = PerformanceMetrics(
            # 基本指標
            total_trades=basic_stats["total_trades"],
            winning_trades=basic_stats["winning_trades"],
            losing_trades=basic_stats["losing_trades"],
            win_rate=basic_stats["win_rate"],
            # 損益指標
            total_profit=basic_stats["total_profit"],
            average_profit=basic_stats["average_profit"],
            profit_factor=basic_stats["profit_factor"],
            # リターン指標
            total_return=return_metrics["total_return"],
            annualized_return=return_metrics["annualized_return"],
            cagr=return_metrics["cagr"],
            # リスク指標
            max_drawdown=risk_metrics["max_drawdown"],
            max_drawdown_duration=risk_metrics["max_drawdown_duration"],
            volatility=risk_metrics["volatility"],
            sharpe_ratio=risk_metrics["sharpe_ratio"],
            sortino_ratio=risk_metrics["sortino_ratio"],
            # 取引指標
            average_trade_duration=trade_metrics["average_duration"],
            max_consecutive_wins=trade_metrics["max_consecutive_wins"],
            max_consecutive_losses=trade_metrics["max_consecutive_losses"],
            # 期間情報
            start_date=period_info["start_date"],
            end_date=period_info["end_date"],
            analysis_period_days=period_info["period_days"],
            # 詳細統計
            trade_distribution=trade_metrics["distribution"],
            monthly_returns=return_metrics["monthly_returns"],
            drawdown_periods=risk_metrics["drawdown_periods"],
        )

        self.logger.info(
            f"評価完了: 勝率{metrics.win_rate:.1%}, 総リターン{metrics.total_return:.1%}"
        )
        return metrics

    def _calculate_basic_stats(self, trade_records: List[TradeRecord]) -> Dict[str, Any]:
        """基本統計計算."""
        profits = [trade.profit_jpy for trade in trade_records]
        winning_profits = [p for p in profits if p > 0]
        losing_profits = [p for p in profits if p < 0]

        total_profit = sum(profits)
        total_wins = len(winning_profits)
        total_losses = len(losing_profits)
        total_trades = len(trade_records)

        win_rate = total_wins / total_trades if total_trades > 0 else 0.0
        average_profit = total_profit / total_trades if total_trades > 0 else 0.0

        # プロフィットファクター計算
        gross_profit = sum(winning_profits) if winning_profits else 0.0
        gross_loss = abs(sum(losing_profits)) if losing_profits else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        return {
            "total_trades": total_trades,
            "winning_trades": total_wins,
            "losing_trades": total_losses,
            "win_rate": win_rate,
            "total_profit": total_profit,
            "average_profit": average_profit,
            "profit_factor": profit_factor,
        }

    def _calculate_return_metrics(
        self,
        equity_curve: List[Tuple[datetime, float]],
        initial_balance: float,
    ) -> Dict[str, Any]:
        """リターン指標計算."""
        if len(equity_curve) < 2:
            return {
                "total_return": 0.0,
                "annualized_return": 0.0,
                "cagr": 0.0,
                "monthly_returns": [],
            }

        final_balance = equity_curve[-1][1]
        total_return = (final_balance - initial_balance) / initial_balance

        # 期間計算
        start_date = equity_curve[0][0]
        end_date = equity_curve[-1][0]
        period_days = (end_date - start_date).days
        period_years = period_days / 365.25

        # 年率リターン・CAGR計算（レガシーから継承）
        if period_years > 0:
            cagr = (final_balance / initial_balance) ** (1 / period_years) - 1
            annualized_return = total_return / period_years
        else:
            cagr = 0.0
            annualized_return = 0.0

        # 月次リターン計算
        monthly_returns = self._calculate_monthly_returns(equity_curve)

        return {
            "total_return": total_return,
            "annualized_return": annualized_return,
            "cagr": cagr,
            "monthly_returns": monthly_returns,
        }

    def _calculate_risk_metrics(
        self,
        trade_records: List[TradeRecord],
        equity_curve: List[Tuple[datetime, float]],
        initial_balance: float,
    ) -> Dict[str, Any]:
        """リスク指標計算."""
        # 最大ドローダウン計算（レガシーから継承・改良）
        max_dd_info = self._calculate_max_drawdown_detailed(equity_curve)

        # ボラティリティ計算
        returns = self._calculate_daily_returns(equity_curve)
        volatility = np.std(returns) * np.sqrt(252) if returns else 0.0  # 年率化

        # シャープレシオ計算
        avg_return = np.mean(returns) * 252 if returns else 0.0  # 年率化
        sharpe_ratio = (avg_return - self.risk_free_rate) / volatility if volatility > 0 else 0.0

        # ソルティーノ比率計算
        negative_returns = [r for r in returns if r < 0]
        downside_std = np.std(negative_returns) * np.sqrt(252) if negative_returns else 0.0
        sortino_ratio = (
            (avg_return - self.risk_free_rate) / downside_std if downside_std > 0 else 0.0
        )

        return {
            "max_drawdown": max_dd_info["max_drawdown"],
            "max_drawdown_duration": max_dd_info["max_duration"],
            "drawdown_periods": max_dd_info["periods"],
            "volatility": volatility,
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
        }

    def _calculate_trade_metrics(self, trade_records: List[TradeRecord]) -> Dict[str, Any]:
        """取引指標計算."""
        if not trade_records:
            return {
                "average_duration": 0.0,
                "max_consecutive_wins": 0,
                "max_consecutive_losses": 0,
                "distribution": {},
            }

        # 平均取引期間計算
        durations = []
        for trade in trade_records:
            if trade.exit_time and trade.entry_time:
                duration = (trade.exit_time - trade.entry_time).total_seconds() / 3600
                durations.append(duration)

        average_duration = np.mean(durations) if durations else 0.0

        # 連続勝敗計算
        consecutive_stats = self._calculate_consecutive_stats(trade_records)

        # 取引分布計算
        distribution = self._calculate_trade_distribution(trade_records)

        return {
            "average_duration": average_duration,
            "max_consecutive_wins": consecutive_stats["max_wins"],
            "max_consecutive_losses": consecutive_stats["max_losses"],
            "distribution": distribution,
        }

    def _calculate_max_drawdown_detailed(
        self, equity_curve: List[Tuple[datetime, float]]
    ) -> Dict[str, Any]:
        """詳細最大ドローダウン計算（レガシー改良版）."""
        if len(equity_curve) < 2:
            return {"max_drawdown": 0.0, "max_duration": 0, "periods": []}

        equity_values = [eq[1] for eq in equity_curve]
        timestamps = [eq[0] for eq in equity_curve]

        peak = equity_values[0]
        peak_time = timestamps[0]
        max_dd = 0.0
        max_dd_duration = 0
        current_dd_start = None
        drawdown_periods = []

        for i, (timestamp, equity) in enumerate(equity_curve):
            if equity > peak:
                # 新高値更新
                if current_dd_start:
                    # ドローダウン期間終了（バグ修正）
                    dd_duration = (timestamp - current_dd_start).days

                    # ドローダウン期間中の最小値を正しく取得
                    start_idx = next(
                        idx for idx, ts in enumerate(timestamps) if ts >= current_dd_start
                    )
                    min_equity_in_period = min(equity_values[start_idx:i])

                    drawdown_periods.append(
                        {
                            "start": current_dd_start,
                            "end": timestamp,
                            "duration_days": dd_duration,
                            "drawdown": (peak - min_equity_in_period) / peak,
                        }
                    )
                    current_dd_start = None

                peak = equity
                peak_time = timestamp
            else:
                # ドローダウン中
                if current_dd_start is None:
                    current_dd_start = peak_time

                drawdown = (peak - equity) / peak
                if drawdown > max_dd:
                    max_dd = drawdown
                    max_dd_duration = (timestamp - peak_time).days

        # 最終ドローダウンが継続中の場合（バグ修正）
        if current_dd_start:
            final_timestamp = timestamps[-1]
            dd_duration = (final_timestamp - current_dd_start).days

            # current_dd_start以降の最小値を正しく取得
            start_idx = next(i for i, ts in enumerate(timestamps) if ts >= current_dd_start)
            min_equity_in_period = min(equity_values[start_idx:])

            drawdown_periods.append(
                {
                    "start": current_dd_start,
                    "end": final_timestamp,
                    "duration_days": dd_duration,
                    "drawdown": (peak - min_equity_in_period) / peak,
                }
            )

        return {
            "max_drawdown": max_dd,
            "max_duration": max_dd_duration,
            "periods": drawdown_periods,
        }

    def _calculate_daily_returns(self, equity_curve: List[Tuple[datetime, float]]) -> List[float]:
        """日次リターン計算."""
        if len(equity_curve) < 2:
            return []

        returns = []
        for i in range(1, len(equity_curve)):
            prev_equity = equity_curve[i - 1][1]
            curr_equity = equity_curve[i][1]

            if prev_equity > 0:
                daily_return = (curr_equity - prev_equity) / prev_equity
                returns.append(daily_return)

        return returns

    def _calculate_monthly_returns(self, equity_curve: List[Tuple[datetime, float]]) -> List[float]:
        """月次リターン計算."""
        if len(equity_curve) < 2:
            return []

        # 月末残高を抽出
        monthly_data = {}
        for timestamp, equity in equity_curve:
            month_key = timestamp.strftime("%Y-%m")
            monthly_data[month_key] = equity

        # 月次リターン計算
        monthly_returns = []
        prev_equity = None

        for month_key in sorted(monthly_data.keys()):
            curr_equity = monthly_data[month_key]

            if prev_equity is not None and prev_equity > 0:
                monthly_return = (curr_equity - prev_equity) / prev_equity
                monthly_returns.append(monthly_return)

            prev_equity = curr_equity

        return monthly_returns

    def _calculate_consecutive_stats(self, trade_records: List[TradeRecord]) -> Dict[str, int]:
        """連続勝敗統計計算."""
        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0

        for trade in trade_records:
            if trade.profit_jpy > 0:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)

        return {"max_wins": max_wins, "max_losses": max_losses}

    def _calculate_trade_distribution(self, trade_records: List[TradeRecord]) -> Dict[str, Any]:
        """取引分布統計計算."""
        profits = [trade.profit_jpy for trade in trade_records]

        if not profits:
            return {}

        return {
            "mean_profit": np.mean(profits),
            "median_profit": np.median(profits),
            "std_profit": np.std(profits),
            "min_profit": np.min(profits),
            "max_profit": np.max(profits),
            "percentile_25": np.percentile(profits, 25),
            "percentile_75": np.percentile(profits, 75),
        }

    def _calculate_period_info(self, equity_curve: List[Tuple[datetime, float]]) -> Dict[str, Any]:
        """期間情報計算."""
        if not equity_curve:
            return {
                "start_date": datetime.now(),
                "end_date": datetime.now(),
                "period_days": 0,
            }

        start_date = equity_curve[0][0]
        end_date = equity_curve[-1][0]
        period_days = (end_date - start_date).days

        return {
            "start_date": start_date,
            "end_date": end_date,
            "period_days": period_days,
        }

    def _create_empty_metrics(self) -> PerformanceMetrics:
        """空のメトリクス作成."""
        return PerformanceMetrics(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            total_profit=0.0,
            average_profit=0.0,
            profit_factor=0.0,
            total_return=0.0,
            annualized_return=0.0,
            cagr=0.0,
            max_drawdown=0.0,
            max_drawdown_duration=0,
            volatility=0.0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            average_trade_duration=0.0,
            max_consecutive_wins=0,
            max_consecutive_losses=0,
            start_date=datetime.now(),
            end_date=datetime.now(),
            analysis_period_days=0,
        )


# レガシーから継承したウォークフォワード検証機能
def split_walk_forward(
    df: pd.DataFrame, train_window: int, test_window: int, step: int
) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
    """
    ウォークフォワード検証のためのデータ分割（レガシーから継承）

    Args:
        df: 分割対象データ
        train_window: 学習期間
        test_window: テスト期間
        step: スライドステップ

    Returns:
        (学習データ, テストデータ) のタプルリスト.
    """
    splits = []
    start = 0
    length = len(df)

    while start + train_window + test_window <= length:
        train_df = df.iloc[start : start + train_window]
        test_df = df.iloc[start + train_window : start + train_window + test_window]
        splits.append((train_df, test_df))
        start += step

    return splits
