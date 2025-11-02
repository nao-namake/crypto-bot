"""
戦略個別パフォーマンス分析 - Phase 51.4

既存3戦略（ATRBased・DonchianChannel・ADXTrendStrength）の
個別パフォーマンスを定量的に評価し、削除候補を特定する。

主要機能:
- 単一戦略のパフォーマンス分析（勝率・損益率・シャープレシオ・最大DD）
- レジーム別パフォーマンス分析（tight_range/normal_range/trending別）
- 戦略間相関分析（相関係数マトリクス）
- アンサンブル貢献度測定（除外時の性能変化）
- レポート生成・可視化

Phase 51.4実装計画:
- Day 1（今回）: 基本骨格・メトリクス計算・簡易テスト
- Day 2（次回）: レジーム別分析・相関分析・貢献度測定
- Day 3（次回）: 可視化・レポート生成・完全テスト・実データ検証
"""

import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.backtest.reporter import TradeTracker  # Phase 51.4-Day2追加
from src.core.config.threshold_manager import get_threshold  # Phase 51.4-Day2追加
from src.core.logger import get_logger
from src.core.services.market_regime_classifier import MarketRegimeClassifier
from src.core.services.regime_types import RegimeType
from src.features.feature_generator import FeatureGenerator  # Phase 51.5-A追加
from src.strategies.implementations.adx_trend import ADXTrendStrengthStrategy  # Phase 51.4-Day2追加
from src.strategies.implementations.atr_based import ATRBasedStrategy  # Phase 51.4-Day2追加
from src.strategies.implementations.donchian_channel import (  # Phase 51.4-Day2追加
    DonchianChannelStrategy,
)
from src.strategies.utils import EntryAction  # Phase 51.4-Day2追加


@dataclass
class PerformanceMetrics:
    """パフォーマンスメトリクス"""

    strategy_name: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float  # 勝率
    total_pnl: float  # 総損益
    avg_win: float  # 平均勝ちトレード
    avg_loss: float  # 平均負けトレード
    profit_factor: float  # プロフィットファクター
    sharpe_ratio: float  # シャープレシオ
    max_drawdown: float  # 最大ドローダウン
    avg_holding_period: float  # 平均保有期間（分）


@dataclass
class RegimePerformance:
    """レジーム別パフォーマンス"""

    regime: RegimeType
    metrics: PerformanceMetrics


class StrategyPerformanceAnalyzer:
    """
    戦略個別パフォーマンス分析器

    Phase 51.4: 既存5戦略の個別評価・削除候補特定
    """

    def __init__(self, data_file: Optional[Path] = None):
        """
        初期化

        Args:
            data_file: 履歴データファイルパス（Noneの場合はデフォルトパス使用）
        """
        self.logger = get_logger(__name__)
        self.data_file = (
            data_file
            or Path(__file__).parent.parent.parent / "src/backtest/data/historical/BTC_JPY_4h.csv"
        )
        self.regime_classifier = MarketRegimeClassifier()

        # 3戦略リスト（Phase 51.5-A）
        self.strategies = [
            "ATRBased",
            "DonchianChannel",
            "ADXTrendStrength",
        ]

        self.logger.info("✅ StrategyPerformanceAnalyzer初期化完了")

    def calculate_basic_metrics(self, trades: List[Dict], strategy_name: str) -> PerformanceMetrics:
        """
        基本的なパフォーマンスメトリクスを計算

        Args:
            trades: 取引リスト（各取引は {'pnl': float, 'holding_period': float} を含む）
            strategy_name: 戦略名

        Returns:
            PerformanceMetrics: 計算されたメトリクス
        """
        if not trades:
            return PerformanceMetrics(
                strategy_name=strategy_name,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                total_pnl=0.0,
                avg_win=0.0,
                avg_loss=0.0,
                profit_factor=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                avg_holding_period=0.0,
            )

        # 取引リストから損益を抽出
        pnls = [t["pnl"] for t in trades]
        winning_trades = [p for p in pnls if p > 0]
        losing_trades = [p for p in pnls if p < 0]

        total_trades = len(trades)
        winning_count = len(winning_trades)
        losing_count = len(losing_trades)

        # 勝率
        win_rate = winning_count / total_trades if total_trades > 0 else 0.0

        # 総損益
        total_pnl = sum(pnls)

        # 平均勝ちトレード・平均負けトレード
        avg_win = sum(winning_trades) / winning_count if winning_count > 0 else 0.0
        avg_loss = sum(losing_trades) / losing_count if losing_count > 0 else 0.0

        # プロフィットファクター
        gross_profit = sum(winning_trades) if winning_trades else 0.0
        gross_loss = abs(sum(losing_trades)) if losing_trades else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

        # シャープレシオ（年率換算）
        sharpe_ratio = self._calculate_sharpe_ratio(pnls)

        # 最大ドローダウン
        max_drawdown = self._calculate_max_drawdown(pnls)

        # 平均保有期間
        holding_periods = [t.get("holding_period", 0) for t in trades]
        avg_holding_period = sum(holding_periods) / len(holding_periods) if holding_periods else 0.0

        return PerformanceMetrics(
            strategy_name=strategy_name,
            total_trades=total_trades,
            winning_trades=winning_count,
            losing_trades=losing_count,
            win_rate=win_rate,
            total_pnl=total_pnl,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            avg_holding_period=avg_holding_period,
        )

    def _calculate_sharpe_ratio(self, pnls: List[float], risk_free_rate: float = 0.0) -> float:
        """
        シャープレシオを計算

        Args:
            pnls: 損益リスト
            risk_free_rate: リスクフリーレート（デフォルト0%）

        Returns:
            シャープレシオ（年率換算）
        """
        if not pnls or len(pnls) < 2:
            return 0.0

        returns = np.array(pnls)
        mean_return = np.mean(returns)
        std_return = np.std(returns, ddof=1)  # サンプル標準偏差

        if std_return == 0:
            return 0.0

        # シャープレシオ = (平均リターン - リスクフリーレート) / リターンの標準偏差
        # 年率換算: √(取引頻度) を乗算（仮定: 1日1取引 → √365）
        sharpe = (mean_return - risk_free_rate) / std_return
        annualized_sharpe = sharpe * np.sqrt(365)  # 年率換算

        return float(annualized_sharpe)

    def _calculate_max_drawdown(self, pnls: List[float]) -> float:
        """
        最大ドローダウンを計算

        Args:
            pnls: 損益リスト

        Returns:
            最大ドローダウン（%）
        """
        if not pnls:
            return 0.0

        # エクイティカーブ（累積損益）
        cumulative_pnl = np.cumsum(pnls)

        # 各時点での最大値
        running_max = np.maximum.accumulate(cumulative_pnl)

        # ドローダウン
        drawdowns = cumulative_pnl - running_max

        # 最大ドローダウン
        max_dd = abs(np.min(drawdowns)) if len(drawdowns) > 0 else 0.0

        return float(max_dd)

    def load_historical_data(self) -> pd.DataFrame:
        """
        履歴データをロード

        Returns:
            pd.DataFrame: 履歴データ
        """
        self.logger.info(f"📊 履歴データロード: {self.data_file}")

        if not self.data_file.exists():
            raise FileNotFoundError(f"データファイルが見つかりません: {self.data_file}")

        # datetime列をindexとして設定（Phase 51.5-A修正）
        df = pd.read_csv(self.data_file, parse_dates=["datetime"], index_col="datetime")
        self.logger.info(f"✅ データロード完了: {len(df)}行")

        return df

    async def analyze_single_strategy(
        self, strategy_name: str, historical_data: pd.DataFrame
    ) -> PerformanceMetrics:
        """
        単一戦略のパフォーマンス分析（Phase 51.4-Day2: 実バックテスト統合）

        Args:
            strategy_name: 戦略名
            historical_data: 履歴データ

        Returns:
            PerformanceMetrics: パフォーマンスメトリクス
        """
        self.logger.info(f"🔍 {strategy_name} パフォーマンス分析開始...")

        # Phase 51.4-Day2: 実バックテスト実行
        trades = await self._run_single_strategy_backtest(strategy_name, historical_data)

        # メトリクス計算
        metrics = self.calculate_basic_metrics(trades, strategy_name)

        self.logger.info(
            f"✅ {strategy_name} 分析完了 - "
            f"取引数={metrics.total_trades}, "
            f"勝率={metrics.win_rate:.2%}, "
            f"シャープレシオ={metrics.sharpe_ratio:.2f}, "
            f"最大DD={metrics.max_drawdown:.2f}"
        )

        return metrics

    def _get_strategy_instance(self, strategy_name: str):
        """
        戦略インスタンスを生成（Phase 51.4-Day2実装）

        Args:
            strategy_name: 戦略名

        Returns:
            戦略インスタンス
        """
        strategy_map = {
            "ATRBased": ATRBasedStrategy,
            "DonchianChannel": DonchianChannelStrategy,
            "ADXTrendStrength": ADXTrendStrengthStrategy,
        }

        if strategy_name not in strategy_map:
            raise ValueError(f"未知の戦略名: {strategy_name}")

        return strategy_map[strategy_name]()

    async def _run_single_strategy_backtest(
        self, strategy_name: str, historical_data: pd.DataFrame
    ) -> List[Dict]:
        """
        単一戦略バックテスト実行（Phase 51.4-Day2実装）

        Args:
            strategy_name: 戦略名
            historical_data: 履歴データ

        Returns:
            取引リスト（TradeTracker形式）
        """
        self.logger.info(f"🔄 {strategy_name} バックテスト開始...")

        # 戦略インスタンス生成
        strategy = self._get_strategy_instance(strategy_name)

        # 特徴量事前計算（Phase 51.5-A修正）
        self.logger.info(f"[{strategy_name}] 特徴量事前計算開始...")
        feature_generator = FeatureGenerator()
        historical_data_with_features = await feature_generator.generate_features(
            historical_data.copy()
        )
        self.logger.info(f"[{strategy_name}] 特徴量計算完了: {historical_data_with_features.shape}")

        # TradeTracker初期化
        tracker = TradeTracker()

        # TP/SL設定値取得
        tp_ratio = get_threshold("position_management.take_profit.default_ratio", 0.01)  # 1%
        sl_ratio = get_threshold("risk.sl_min_distance_ratio", 0.015)  # 1.5%

        # オープンポジション管理
        open_position = None
        order_id_counter = 0

        # 履歴データをループ（最低100行必要）
        if len(historical_data) < 100:
            self.logger.warning(f"⚠️ データ不足: {len(historical_data)}行 < 100行")
            return []

        for i in range(50, len(historical_data)):  # 最初50行はウォームアップ
            # 現在までのデータで戦略分析（Phase 51.5-A修正: 特徴量付きDataFrame使用）
            df_slice = historical_data_with_features.iloc[: i + 1].copy()
            current_row = historical_data_with_features.iloc[i]
            current_price = float(current_row["close"])
            current_time = (
                pd.to_datetime(current_row["timestamp"])
                if "timestamp" in current_row
                else datetime.now()
            )

            try:
                # 戦略シグナル取得
                signal = strategy.analyze(df_slice, None)
            except Exception as e:
                self.logger.debug(f"戦略分析エラー（行{i}）: {e}")
                continue

            # オープンポジションがある場合、TP/SL判定
            if open_position is not None:
                entry_price = open_position["entry_price"]
                side = open_position["side"]

                # TP/SL価格計算
                if side == "buy":
                    tp_price = entry_price * (1 + tp_ratio)
                    sl_price = entry_price * (1 - sl_ratio)
                    # TP到達判定
                    if current_price >= tp_price:
                        tracker.record_exit(open_position["order_id"], tp_price, current_time, "TP")
                        open_position = None
                        continue
                    # SL到達判定
                    elif current_price <= sl_price:
                        tracker.record_exit(open_position["order_id"], sl_price, current_time, "SL")
                        open_position = None
                        continue
                else:  # sell
                    tp_price = entry_price * (1 - tp_ratio)
                    sl_price = entry_price * (1 + sl_ratio)
                    # TP到達判定
                    if current_price <= tp_price:
                        tracker.record_exit(open_position["order_id"], tp_price, current_time, "TP")
                        open_position = None
                        continue
                    # SL到達判定
                    elif current_price >= sl_price:
                        tracker.record_exit(open_position["order_id"], sl_price, current_time, "SL")
                        open_position = None
                        continue

                # 逆シグナルでエグジット
                if (side == "buy" and signal.action == EntryAction.SELL) or (
                    side == "sell" and signal.action == EntryAction.BUY
                ):
                    tracker.record_exit(
                        open_position["order_id"], current_price, current_time, "SIGNAL"
                    )
                    open_position = None

            # 新規エントリー判定（ポジションがない場合のみ）
            if open_position is None and signal.action in [EntryAction.BUY, EntryAction.SELL]:
                order_id = f"{strategy_name}_{order_id_counter}"
                order_id_counter += 1
                side = "buy" if signal.action == EntryAction.BUY else "sell"
                amount = 0.01  # 固定数量（簡易版）

                tracker.record_entry(
                    order_id, side, amount, current_price, current_time, strategy_name
                )
                open_position = {
                    "order_id": order_id,
                    "side": side,
                    "entry_price": current_price,
                }

        # 未決済ポジションがあれば最終価格でクローズ
        if open_position is not None:
            final_row = historical_data.iloc[-1]
            final_price = float(final_row["close"])
            final_time = (
                pd.to_datetime(final_row["timestamp"])
                if "timestamp" in final_row
                else datetime.now()
            )
            tracker.record_exit(open_position["order_id"], final_price, final_time, "END")

        self.logger.info(
            f"✅ {strategy_name} バックテスト完了 - {len(tracker.completed_trades)}取引"
        )
        return tracker.completed_trades

    async def analyze_regime_performance(
        self, strategy_name: str, historical_data: pd.DataFrame
    ) -> Dict[RegimeType, PerformanceMetrics]:
        """
        レジーム別パフォーマンス分析（Phase 51.4-Day2実装）

        Args:
            strategy_name: 戦略名
            historical_data: 履歴データ

        Returns:
            Dict[RegimeType, PerformanceMetrics]: レジーム別メトリクス
        """
        self.logger.info(f"🔍 {strategy_name} レジーム別分析開始...")

        # バックテスト実行（Phase 51.5-A: await追加）
        trades = await self._run_single_strategy_backtest(strategy_name, historical_data)

        # レジーム別に取引を分類
        regime_trades = {
            RegimeType.TIGHT_RANGE: [],
            RegimeType.NORMAL_RANGE: [],
            RegimeType.TRENDING: [],
            RegimeType.HIGH_VOLATILITY: [],
        }

        for trade in trades:
            # エントリー時点のタイムスタンプでデータスライス取得
            entry_timestamp = trade["entry_timestamp"]

            # タイムスタンプが文字列の場合はdatetimeに変換
            if isinstance(entry_timestamp, str):
                entry_timestamp = pd.to_datetime(entry_timestamp)

            # エントリー時点までのデータを取得
            if "timestamp" in historical_data.columns:
                historical_data["timestamp"] = pd.to_datetime(historical_data["timestamp"])
                mask = historical_data["timestamp"] <= entry_timestamp
                df_slice = historical_data[mask].copy()
            else:
                # タイムスタンプ列がない場合はスキップ
                self.logger.warning("タイムスタンプ列がないためレジーム分類をスキップ")
                continue

            if len(df_slice) < 50:
                # データ不足の場合はスキップ
                continue

            try:
                # レジーム分類
                regime = self.regime_classifier.classify(df_slice)
                regime_trades[regime].append(trade)
            except Exception as e:
                self.logger.debug(f"レジーム分類エラー: {e}")
                continue

        # レジーム別にメトリクス計算
        regime_metrics = {}
        for regime, trades_list in regime_trades.items():
            if len(trades_list) > 0:
                metrics = self.calculate_basic_metrics(
                    trades_list, f"{strategy_name}_{regime.value}"
                )
                regime_metrics[regime] = metrics
                self.logger.info(
                    f"  {regime.value}: {len(trades_list)}取引, "
                    f"勝率={metrics.win_rate:.2%}, "
                    f"シャープレシオ={metrics.sharpe_ratio:.2f}"
                )
            else:
                # 取引がない場合は空のメトリクス
                regime_metrics[regime] = PerformanceMetrics(
                    strategy_name=f"{strategy_name}_{regime.value}",
                    total_trades=0,
                    winning_trades=0,
                    losing_trades=0,
                    win_rate=0.0,
                    total_pnl=0.0,
                    avg_win=0.0,
                    avg_loss=0.0,
                    profit_factor=0.0,
                    sharpe_ratio=0.0,
                    max_drawdown=0.0,
                    avg_holding_period=0.0,
                )

        self.logger.info(f"✅ {strategy_name} レジーム別分析完了")
        return regime_metrics

    def calculate_strategy_correlation(
        self, all_strategy_trades: Dict[str, List[Dict]]
    ) -> pd.DataFrame:
        """
        戦略間相関分析（Phase 51.4-Day2実装）

        Args:
            all_strategy_trades: 戦略名 → 取引リストのマッピング

        Returns:
            pd.DataFrame: 5x5相関係数マトリクス
        """
        self.logger.info("🔍 戦略間相関分析開始...")

        # 各戦略の時系列リターンを生成
        strategy_returns = {}

        for strategy_name, trades in all_strategy_trades.items():
            if not trades:
                strategy_returns[strategy_name] = {}
                continue

            # タイムスタンプごとのリターンマップを作成
            returns_map = {}
            for trade in trades:
                # エグジットタイムスタンプを使用
                exit_timestamp = trade["exit_timestamp"]
                if isinstance(exit_timestamp, str):
                    exit_timestamp = pd.to_datetime(exit_timestamp)

                # タイムスタンプを文字列キーに変換
                timestamp_key = exit_timestamp.strftime("%Y-%m-%d %H:%M:%S")
                pnl = trade["pnl"]

                # 同じタイムスタンプに複数取引がある場合は合計
                if timestamp_key in returns_map:
                    returns_map[timestamp_key] += pnl
                else:
                    returns_map[timestamp_key] = pnl

            strategy_returns[strategy_name] = returns_map

        # 全タイムスタンプのユニオンを取得
        all_timestamps = set()
        for returns_map in strategy_returns.values():
            all_timestamps.update(returns_map.keys())

        all_timestamps = sorted(list(all_timestamps))

        # 各戦略のリターン配列を生成（欠損値は0埋め）
        return_arrays = {}
        for strategy_name in self.strategies:
            returns_map = strategy_returns.get(strategy_name, {})
            returns_array = [returns_map.get(ts, 0.0) for ts in all_timestamps]
            return_arrays[strategy_name] = returns_array

        # 相関係数マトリクス計算
        if len(all_timestamps) < 2:
            # データ不足の場合は単位行列を返す
            self.logger.warning("データ不足のため相関係数計算をスキップ")
            corr_matrix = np.eye(len(self.strategies))
        else:
            # numpy.corrcoef()で相関係数マトリクス計算
            returns_matrix = np.array([return_arrays[s] for s in self.strategies])
            corr_matrix = np.corrcoef(returns_matrix)

        # pandas DataFrameに変換
        corr_df = pd.DataFrame(corr_matrix, index=self.strategies, columns=self.strategies)

        self.logger.info("✅ 戦略間相関分析完了")
        self.logger.info(f"\n{corr_df.to_string()}")

        return corr_df

    async def measure_ensemble_contribution(
        self, historical_data: pd.DataFrame
    ) -> Dict[str, Dict[str, float]]:
        """
        アンサンブル貢献度測定（Phase 51.4-Day2実装・簡易版）

        Args:
            historical_data: 履歴データ

        Returns:
            Dict[strategy_name, metrics]: 各戦略の貢献度指標
        """
        self.logger.info("🔍 アンサンブル貢献度測定開始...")

        # 全戦略のバックテスト実行
        all_trades = {}
        for strategy_name in self.strategies:
            trades = await self._run_single_strategy_backtest(strategy_name, historical_data)
            all_trades[strategy_name] = trades

        # ベースライン（全5戦略アンサンブル）のシャープレシオ計算
        baseline_trades = []
        for trades in all_trades.values():
            baseline_trades.extend(trades)

        # 時系列順にソート
        baseline_trades.sort(key=lambda x: x["exit_timestamp"])

        baseline_pnls = [t["pnl"] for t in baseline_trades]
        baseline_sharpe = self._calculate_sharpe_ratio(baseline_pnls)

        self.logger.info(f"  ベースライン（全5戦略）: シャープレシオ={baseline_sharpe:.2f}")

        # 各戦略を除外した場合のシャープレシオ計算
        contribution_results = {}

        for excluded_strategy in self.strategies:
            # 除外した戦略以外の取引を結合
            without_trades = []
            for strategy_name, trades in all_trades.items():
                if strategy_name != excluded_strategy:
                    without_trades.extend(trades)

            # 時系列順にソート
            without_trades.sort(key=lambda x: x["exit_timestamp"])

            if without_trades:
                without_pnls = [t["pnl"] for t in without_trades]
                without_sharpe = self._calculate_sharpe_ratio(without_pnls)
            else:
                without_sharpe = 0.0

            # 貢献度計算（ベースライン - 除外時）
            contribution = baseline_sharpe - without_sharpe
            contribution_pct = (contribution / baseline_sharpe * 100) if baseline_sharpe != 0 else 0

            contribution_results[excluded_strategy] = {
                "baseline_sharpe": baseline_sharpe,
                "without_sharpe": without_sharpe,
                "contribution": contribution,
                "contribution_pct": contribution_pct,
                "num_trades": len(all_trades[excluded_strategy]),
            }

            self.logger.info(
                f"  {excluded_strategy}除外: シャープレシオ={without_sharpe:.2f}, "
                f"貢献度={contribution:+.2f} ({contribution_pct:+.1f}%)"
            )

        self.logger.info("✅ アンサンブル貢献度測定完了")
        return contribution_results

    async def analyze_all_strategies(self) -> Dict[str, PerformanceMetrics]:
        """
        全戦略のパフォーマンス分析

        Returns:
            Dict[str, PerformanceMetrics]: 戦略名 → メトリクスのマッピング
        """
        self.logger.info("=" * 80)
        self.logger.info("🚀 Phase 51.4: 戦略個別パフォーマンス分析開始")
        self.logger.info("=" * 80)

        # 履歴データロード
        historical_data = self.load_historical_data()

        # 全戦略を分析
        results = {}
        for strategy_name in self.strategies:
            metrics = await self.analyze_single_strategy(strategy_name, historical_data)
            results[strategy_name] = metrics

        self.logger.info("=" * 80)
        self.logger.info("✅ 全戦略分析完了")
        self.logger.info("=" * 80)

        return results

    def generate_summary_report(self, results: Dict[str, PerformanceMetrics]) -> str:
        """
        サマリーレポート生成

        Args:
            results: 分析結果

        Returns:
            レポート文字列
        """
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("Phase 51.4: 戦略個別パフォーマンス分析レポート")
        report_lines.append(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("=" * 80)
        report_lines.append("")

        for strategy_name, metrics in results.items():
            report_lines.append(f"【{strategy_name}】")
            report_lines.append(f"  総取引数: {metrics.total_trades}")
            report_lines.append(
                f"  勝率: {metrics.win_rate:.2%} ({metrics.winning_trades}勝 / {metrics.losing_trades}敗)"
            )
            report_lines.append(f"  総損益: {metrics.total_pnl:,.0f}円")
            report_lines.append(f"  平均勝ちトレード: {metrics.avg_win:,.0f}円")
            report_lines.append(f"  平均負けトレード: {metrics.avg_loss:,.0f}円")
            report_lines.append(f"  プロフィットファクター: {metrics.profit_factor:.2f}")
            report_lines.append(f"  シャープレシオ: {metrics.sharpe_ratio:.2f}")
            report_lines.append(f"  最大ドローダウン: {metrics.max_drawdown:,.0f}円")
            report_lines.append(f"  平均保有期間: {metrics.avg_holding_period:.0f}分")
            report_lines.append("")

        report_lines.append("=" * 80)
        report_lines.append("📊 Phase 51.4-Day1完了: 基本メトリクス計算実装済み")
        report_lines.append("⏭️  Phase 51.4-Day2予定: レジーム別分析・相関分析・貢献度測定")
        report_lines.append("=" * 80)

        return "\n".join(report_lines)

    def save_results(
        self, results: Dict[str, PerformanceMetrics], output_dir: Optional[Path] = None
    ):
        """
        分析結果を保存

        Args:
            results: 分析結果
            output_dir: 出力ディレクトリ（Noneの場合はデフォルト）
        """
        if output_dir is None:
            output_dir = Path(__file__).parent.parent.parent / "src/backtest/logs"

        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSON形式で保存
        json_file = output_dir / f"strategy_analysis_{timestamp}.json"
        json_data = {
            strategy_name: {
                "total_trades": m.total_trades,
                "winning_trades": m.winning_trades,
                "losing_trades": m.losing_trades,
                "win_rate": m.win_rate,
                "total_pnl": m.total_pnl,
                "avg_win": m.avg_win,
                "avg_loss": m.avg_loss,
                "profit_factor": m.profit_factor,
                "sharpe_ratio": m.sharpe_ratio,
                "max_drawdown": m.max_drawdown,
                "avg_holding_period": m.avg_holding_period,
            }
            for strategy_name, m in results.items()
        }

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)

        self.logger.info(f"💾 JSON保存完了: {json_file}")

        # テキストレポート保存
        txt_file = output_dir / f"strategy_analysis_{timestamp}.txt"
        report = self.generate_summary_report(results)

        with open(txt_file, "w", encoding="utf-8") as f:
            f.write(report)

        self.logger.info(f"💾 レポート保存完了: {txt_file}")


async def main():
    """メイン実行関数（Phase 51.4-Day3完全版）"""
    analyzer = StrategyPerformanceAnalyzer()

    print("=" * 80)
    print("📊 Phase 51.4-Day3: 戦略個別パフォーマンス分析（完全版）")
    print("=" * 80)
    print()

    # 1. 履歴データロード
    print("📂 履歴データロード中...")
    historical_data = analyzer.load_historical_data()
    print(f"✅ データロード完了: {len(historical_data)}行")
    print()

    # 2. 全戦略の基本分析
    print("📊 全戦略の基本分析実行中...")
    results = await analyzer.analyze_all_strategies()
    print(f"✅ 基本分析完了: {len(results)}戦略")
    print()

    # 3. レジーム別パフォーマンス分析
    print("🎯 レジーム別パフォーマンス分析実行中...")
    regime_results = {}
    for strategy_name in analyzer.strategies:
        print(f"  - {strategy_name}のレジーム別分析...")
        regime_metrics = await analyzer.analyze_regime_performance(strategy_name, historical_data)
        regime_results[strategy_name] = regime_metrics
    print(f"✅ レジーム別分析完了: {len(regime_results)}戦略")
    print()

    # 4. 戦略間相関分析
    print("📈 戦略間相関分析実行中...")
    all_strategy_trades = {}
    for strategy_name in analyzer.strategies:
        trades = await analyzer._run_single_strategy_backtest(strategy_name, historical_data)
        all_strategy_trades[strategy_name] = trades

    correlation_matrix = analyzer.calculate_strategy_correlation(all_strategy_trades)
    print("✅ 相関分析完了")
    print()
    print(correlation_matrix)
    print()

    # 5. アンサンブル貢献度測定
    print("🧮 アンサンブル貢献度測定中（Leave-One-Out法）...")
    contribution_results = await analyzer.measure_ensemble_contribution(historical_data)
    print("✅ 貢献度測定完了")
    print()

    # 貢献度表示
    for strategy_name, contrib in contribution_results.items():
        print(f"  {strategy_name}:")
        print(f"    ベースラインシャープレシオ: {contrib['baseline_sharpe']:.3f}")
        print(f"    除外時シャープレシオ: {contrib['without_sharpe']:.3f}")
        print(f"    貢献度: {contrib['contribution']:+.3f} ({contrib['contribution_pct']:+.2f}%)")
        print()

    # 6. 削除候補リスト作成
    print("=" * 80)
    print("🎯 削除候補戦略の特定")
    print("=" * 80)
    print()

    deletion_candidates = []
    deletion_reasons = {}

    # 削除基準1: 全レジームで勝率 < 50%
    print("📋 基準1: 全レジームで勝率 < 50%の戦略")
    for strategy_name, regime_metrics in regime_results.items():
        if len(regime_metrics) == 0:
            continue

        all_regimes_below_50 = all(m.win_rate < 0.5 for m in regime_metrics.values())

        if all_regimes_below_50:
            deletion_candidates.append(strategy_name)
            deletion_reasons[strategy_name] = deletion_reasons.get(strategy_name, [])
            deletion_reasons[strategy_name].append("全レジームで勝率<50%")
            print(f"  ⚠️  {strategy_name}: 全レジームで勝率<50%")

    if len(deletion_candidates) == 0:
        print("  ✅ 該当なし")
    print()

    # 削除基準2: 他戦略と相関係数 ≥ 0.7（冗長性）
    print("📋 基準2: 他戦略と相関係数 ≥ 0.7の戦略ペア（冗長性）")
    high_correlation_pairs = []
    for i, strategy1 in enumerate(analyzer.strategies):
        for j, strategy2 in enumerate(analyzer.strategies):
            if i < j:  # 上三角のみチェック
                corr = correlation_matrix.loc[strategy1, strategy2]
                if corr >= 0.7:
                    high_correlation_pairs.append((strategy1, strategy2, corr))
                    print(f"  ⚠️  {strategy1} vs {strategy2}: 相関係数 {corr:.3f}")

                    # 両方を候補に追加（後で貢献度で判断）
                    if strategy1 not in deletion_candidates:
                        deletion_candidates.append(strategy1)
                    if strategy2 not in deletion_candidates:
                        deletion_candidates.append(strategy2)

                    deletion_reasons[strategy1] = deletion_reasons.get(strategy1, [])
                    deletion_reasons[strategy1].append(f"{strategy2}と高相関({corr:.3f})")
                    deletion_reasons[strategy2] = deletion_reasons.get(strategy2, [])
                    deletion_reasons[strategy2].append(f"{strategy1}と高相関({corr:.3f})")

    if len(high_correlation_pairs) == 0:
        print("  ✅ 該当なし")
    print()

    # 削除基準3: アンサンブル貢献度 < 0%（ノイズ戦略）
    print("📋 基準3: アンサンブル貢献度 < 0%の戦略（ノイズ戦略）")
    for strategy_name, contrib in contribution_results.items():
        if contrib["contribution"] < 0:
            if strategy_name not in deletion_candidates:
                deletion_candidates.append(strategy_name)
            deletion_reasons[strategy_name] = deletion_reasons.get(strategy_name, [])
            deletion_reasons[strategy_name].append(
                f"貢献度{contrib['contribution_pct']:+.2f}%（ノイズ）"
            )
            print(f"  ⚠️  {strategy_name}: 貢献度 {contrib['contribution_pct']:+.2f}%")

    if not any(c["contribution"] < 0 for c in contribution_results.values()):
        print("  ✅ 該当なし")
    print()

    # 削除候補サマリー
    print("=" * 80)
    print(f"🎯 削除候補戦略: {len(deletion_candidates)}戦略")
    print("=" * 80)
    print()

    if len(deletion_candidates) > 0:
        for strategy_name in deletion_candidates:
            print(f"【{strategy_name}】")
            for reason in deletion_reasons.get(strategy_name, []):
                print(f"  - {reason}")
            print()
    else:
        print("✅ 削除候補なし（全戦略が基準をクリア）")
        print()

    # 7. 包括的レポート生成
    print("=" * 80)
    print("💾 レポート生成・保存中...")
    print("=" * 80)
    print()

    # 基本レポート生成
    report = analyzer.generate_summary_report(results)

    # レポートに追加情報を付与
    report += "\n\n" + "=" * 80 + "\n"
    report += "📊 Phase 51.4-Day3完全分析結果\n"
    report += "=" * 80 + "\n\n"

    report += "【削除候補戦略】\n"
    if len(deletion_candidates) > 0:
        for strategy_name in deletion_candidates:
            report += f"  ⚠️  {strategy_name}\n"
            for reason in deletion_reasons.get(strategy_name, []):
                report += f"      - {reason}\n"
    else:
        report += "  ✅ 削除候補なし\n"
    report += "\n"

    # 表示
    print(report)

    # 結果保存
    analyzer.save_results(results)

    print()
    print("=" * 80)
    print("✅ Phase 51.4-Day3完了")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
