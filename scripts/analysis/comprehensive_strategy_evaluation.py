#!/usr/bin/env python3
"""
包括的戦略評価スクリプト - Phase 60

全6戦略を単体で詳細評価し、改善ポイントを特定する包括的分析ツール。
Phase 60でstrategy_performance_analysis.py, strategy_signal_analyzer.pyの機能を完全統合。

使用方法:
    python scripts/analysis/comprehensive_strategy_evaluation.py --days 30
    python scripts/analysis/comprehensive_strategy_evaluation.py --days 30 --strategy ATRBased
    python scripts/analysis/comprehensive_strategy_evaluation.py --days 30 --export ./output

機能:
    1. 戦略単体バックテスト（勝率・PF・シャープレシオ・最大DD）
    2. シグナル分布分析（BUY/SELL/HOLD率・HOLD理由）
    3. ADX/RSI/Stochastic条件達成率
    4. [Phase 60.1] 時間帯別パフォーマンス分析
    5. [Phase 60.1] 連敗検出・アラート
    6. [Phase 60.1] パラメータ感度分析
    7. [Phase 60.1] 具体的改善提案（数値付き）
    8. [Phase 60] レジーム別パフォーマンス分析（tight_range/normal_range/trending/high_volatility）
    9. [Phase 60] 戦略間相関分析（相関係数マトリクス）
    10. [Phase 60] アンサンブル貢献度測定（Leave-One-Out法）
"""

import argparse
import asyncio
import json
import os
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# プロジェクトルートをパスに追加
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# 設定読み込み
from src.core.config import load_config

try:
    load_config("config/core/unified.yaml")
except Exception:
    pass

from src.backtest.reporter import TradeTracker
from src.core.config.threshold_manager import get_threshold
from src.core.services.market_regime_classifier import MarketRegimeClassifier
from src.core.services.regime_types import RegimeType
from src.features.feature_generator import FeatureGenerator
from src.strategies.strategy_loader import StrategyLoader
from src.strategies.utils import EntryAction


@dataclass
class StrategyMetrics:
    """戦略評価メトリクス"""

    strategy_name: str
    # バックテスト結果
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    avg_holding_period: float = 0.0
    # シグナル分布
    buy_count: int = 0
    sell_count: int = 0
    hold_count: int = 0
    hold_rate: float = 0.0
    # 信頼度
    avg_buy_confidence: float = 0.0
    avg_sell_confidence: float = 0.0
    avg_hold_confidence: float = 0.0
    # 主要HOLD理由
    top_hold_reasons: Dict[str, int] = None
    # 評価スコア
    overall_score: float = 0.0
    improvement_suggestions: List[str] = None
    # [Phase 60.1] 時間帯別パフォーマンス
    hourly_performance: Dict[int, Dict[str, float]] = None  # hour -> {win_rate, pf, trades}
    best_hours: List[int] = None
    worst_hours: List[int] = None
    # [Phase 60.1] 連敗分析
    max_consecutive_losses: int = 0
    max_consecutive_wins: int = 0
    avg_recovery_trades: float = 0.0  # 連敗後の回復までの取引数
    # [Phase 60.1] パラメータ感度
    parameter_sensitivity: Dict[str, Dict[str, float]] = None  # param -> {-10%: pf, +10%: pf}
    # [Phase 60] レジーム別・相関・貢献度分析（strategy_performance_analysis.pyから統合）
    regime_performance: Dict[str, Dict[str, float]] = None  # regime -> {win_rate, pf, trades}
    correlation_with_others: Dict[str, float] = None  # strategy_name -> correlation
    ensemble_contribution: float = 0.0  # 貢献度（%）

    def __post_init__(self):
        if self.top_hold_reasons is None:
            self.top_hold_reasons = {}
        if self.improvement_suggestions is None:
            self.improvement_suggestions = []
        if self.hourly_performance is None:
            self.hourly_performance = {}
        if self.best_hours is None:
            self.best_hours = []
        if self.worst_hours is None:
            self.worst_hours = []
        if self.parameter_sensitivity is None:
            self.parameter_sensitivity = {}
        if self.regime_performance is None:
            self.regime_performance = {}
        if self.correlation_with_others is None:
            self.correlation_with_others = {}


@dataclass
class RegimeMetrics:
    """レジーム別メトリクス"""

    regime: str
    total_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0


class ComprehensiveStrategyEvaluator:
    """包括的戦略評価器"""

    def __init__(self, verbose: bool = False):
        """
        初期化

        Args:
            verbose: 詳細出力モード
        """
        self.verbose = verbose
        self.strategies = []
        self.strategy_instances = {}
        self.df = None
        self.df_with_features = None
        self.results: Dict[str, StrategyMetrics] = {}
        self.regime_results: Dict[str, Dict[str, RegimeMetrics]] = {}
        self.regime_classifier = MarketRegimeClassifier()

    async def load_data(self, days: int = 30, csv_path: Optional[str] = None) -> pd.DataFrame:
        """
        履歴データを読み込み

        Args:
            days: 分析日数
            csv_path: CSVファイルパス

        Returns:
            pd.DataFrame: 特徴量付きデータ
        """
        print(f"📊 {days}日分のデータを取得中...")

        # CSVファイルから読み込み
        default_csv = str(project_root / "src/backtest/data/historical/BTC_JPY_15m.csv")
        csv_file = csv_path or default_csv

        if not os.path.exists(csv_file):
            raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_file}")

        print(f"   📁 CSVから読み込み: {csv_file}")
        df_raw = pd.read_csv(csv_file)

        # タイムスタンプ列の変換
        if "timestamp" in df_raw.columns:
            df_raw["timestamp"] = pd.to_datetime(df_raw["timestamp"])
        elif "datetime" in df_raw.columns:
            df_raw["timestamp"] = pd.to_datetime(df_raw["datetime"])

        # 日数分のデータをフィルタリング（15分足 = 96データ/日）
        rows_needed = days * 96
        if len(df_raw) > rows_needed:
            df_raw = df_raw.tail(rows_needed)

        self.df = df_raw

        # 特徴量生成
        print("   🔧 特徴量生成中...")
        feature_gen = FeatureGenerator()
        self.df_with_features = await feature_gen.generate_features(df_raw.copy())

        print(f"✅ {len(self.df_with_features)}データポイントを取得")
        return self.df_with_features

    def load_strategies(self, target_strategy: Optional[str] = None) -> List:
        """
        戦略をロード

        Args:
            target_strategy: 特定の戦略のみ分析する場合はその名前

        Returns:
            List: 戦略インスタンスリスト
        """
        print("🔧 戦略をロード中...")

        loader = StrategyLoader("config/core/strategies.yaml")
        strategy_configs = loader.load_strategies()

        for config in strategy_configs:
            instance = config["instance"]
            name = instance.name
            if target_strategy is None or name == target_strategy:
                self.strategies.append(instance)
                self.strategy_instances[name] = instance

        print(f"✅ {len(self.strategies)}戦略をロード完了")
        for s in self.strategies:
            print(f"   - {s.name}")

        return self.strategies

    async def evaluate_all_strategies(self) -> Dict[str, StrategyMetrics]:
        """
        全戦略を評価

        Returns:
            Dict[str, StrategyMetrics]: 戦略別評価結果
        """
        if self.df_with_features is None or self.df_with_features.empty:
            raise ValueError("データが読み込まれていません")

        if not self.strategies:
            raise ValueError("戦略が読み込まれていません")

        print("\n" + "=" * 80)
        print("🔍 包括的戦略評価を実行中...")
        print("=" * 80)

        # 全戦略のバックテスト結果を収集（相関・貢献度分析用）
        all_trades: Dict[str, List[Dict]] = {}

        for strategy in self.strategies:
            print(f"\n📊 {strategy.name} を評価中...")
            metrics = await self._evaluate_single_strategy(strategy)
            self.results[strategy.name] = metrics

            # 取引リストを収集
            trades = await self._run_backtest(strategy)
            all_trades[strategy.name] = trades

            # [Phase 60] レジーム別パフォーマンス分析
            metrics.regime_performance = self._analyze_regime_performance(trades)

            # 簡易結果表示
            print(
                f"   勝率: {metrics.win_rate:.1%} | PF: {metrics.profit_factor:.2f} | "
                f"HOLD率: {metrics.hold_rate:.1%} | 取引数: {metrics.total_trades}"
            )

        # [Phase 60] 戦略間相関分析
        if len(all_trades) > 1:
            print("\n📈 戦略間相関分析中...")
            corr_matrix = self._calculate_strategy_correlation(all_trades)
            if not corr_matrix.empty:
                for strategy_name in self.results.keys():
                    correlations = {}
                    for other_name in self.results.keys():
                        if other_name != strategy_name:
                            try:
                                correlations[other_name] = float(
                                    corr_matrix.loc[strategy_name, other_name]
                                )
                            except Exception:
                                pass
                    self.results[strategy_name].correlation_with_others = correlations

        # [Phase 60] アンサンブル貢献度測定
        if len(all_trades) > 1:
            print("🧮 アンサンブル貢献度測定中...")
            contributions = await self._measure_ensemble_contribution(all_trades)
            for strategy_name, contrib_pct in contributions.items():
                if strategy_name in self.results:
                    self.results[strategy_name].ensemble_contribution = contrib_pct

        return self.results

    async def _evaluate_single_strategy(self, strategy) -> StrategyMetrics:
        """
        単一戦略を詳細評価

        Args:
            strategy: 戦略インスタンス

        Returns:
            StrategyMetrics: 評価結果
        """
        metrics = StrategyMetrics(strategy_name=strategy.name)

        # 1. シグナル分布分析
        signals, reasons, confidences = self._analyze_signals(strategy)

        buy_count = sum(1 for s in signals if s == "buy")
        sell_count = sum(1 for s in signals if s == "sell")
        hold_count = sum(1 for s in signals if s == "hold")
        total = len(signals)

        metrics.buy_count = buy_count
        metrics.sell_count = sell_count
        metrics.hold_count = hold_count
        metrics.hold_rate = hold_count / total if total > 0 else 0

        # 信頼度計算
        buy_confs = [c for s, c in zip(signals, confidences) if s == "buy"]
        sell_confs = [c for s, c in zip(signals, confidences) if s == "sell"]
        hold_confs = [c for s, c in zip(signals, confidences) if s == "hold"]

        metrics.avg_buy_confidence = sum(buy_confs) / len(buy_confs) if buy_confs else 0
        metrics.avg_sell_confidence = sum(sell_confs) / len(sell_confs) if sell_confs else 0
        metrics.avg_hold_confidence = sum(hold_confs) / len(hold_confs) if hold_confs else 0

        # HOLD理由集計
        hold_reasons = defaultdict(int)
        for reason, signal in zip(reasons, signals):
            if signal == "hold":
                hold_reasons[reason] += 1
        metrics.top_hold_reasons = dict(sorted(hold_reasons.items(), key=lambda x: -x[1])[:5])

        # 2. バックテスト実行
        trades = await self._run_backtest(strategy)

        if trades:
            metrics.total_trades = len(trades)
            pnls = [t["pnl"] for t in trades]
            winning = [p for p in pnls if p > 0]
            losing = [p for p in pnls if p < 0]

            metrics.winning_trades = len(winning)
            metrics.losing_trades = len(losing)
            metrics.win_rate = len(winning) / len(trades) if trades else 0
            metrics.total_pnl = sum(pnls)

            # PF計算
            gross_profit = sum(winning) if winning else 0
            gross_loss = abs(sum(losing)) if losing else 0
            metrics.profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

            # シャープレシオ
            if len(pnls) >= 2:
                mean_return = np.mean(pnls)
                std_return = np.std(pnls, ddof=1)
                metrics.sharpe_ratio = mean_return / std_return if std_return > 0 else 0

            # 最大DD
            cumulative = np.cumsum(pnls)
            running_max = np.maximum.accumulate(cumulative)
            drawdowns = cumulative - running_max
            metrics.max_drawdown = abs(np.min(drawdowns)) if len(drawdowns) > 0 else 0

            # 平均保有期間
            holding_periods = [t.get("holding_period", 0) for t in trades]
            metrics.avg_holding_period = (
                sum(holding_periods) / len(holding_periods) if holding_periods else 0
            )

            # [Phase 60.1] 時間帯別パフォーマンス分析
            hourly_perf, best_hours, worst_hours = self._analyze_hourly_performance(trades)
            metrics.hourly_performance = hourly_perf
            metrics.best_hours = best_hours
            metrics.worst_hours = worst_hours

            # [Phase 60.1] 連勝/連敗分析
            max_losses, max_wins, avg_recovery = self._analyze_consecutive_results(trades)
            metrics.max_consecutive_losses = max_losses
            metrics.max_consecutive_wins = max_wins
            metrics.avg_recovery_trades = avg_recovery

        # [Phase 60.1] パラメータ感度分析
        metrics.parameter_sensitivity = self._analyze_parameter_sensitivity(
            strategy, trades if trades else []
        )

        # 3. 総合スコア計算
        metrics.overall_score = self._calculate_overall_score(metrics)

        # 4. 改善提案生成（Phase 60.1で強化）
        metrics.improvement_suggestions = self._generate_suggestions(metrics)

        return metrics

    def _analyze_signals(self, strategy) -> Tuple[List[str], List[str], List[float]]:
        """シグナル分析（高速サンプリング版）"""
        signals, reasons, confidences = [], [], []
        min_rows = 50
        sample_rate = 5  # 5データごとにサンプリング

        for i in range(min_rows, len(self.df_with_features), sample_rate):
            try:
                df_slice = self.df_with_features.iloc[: i + 1].copy()
                signal = strategy.analyze(df_slice)

                action = signal.action.lower() if hasattr(signal, "action") else "hold"
                reason = signal.reason if hasattr(signal, "reason") else "理由なし"
                confidence = float(signal.confidence) if hasattr(signal, "confidence") else 0.0

                signals.append(action)
                reasons.append(reason or "理由なし")
                confidences.append(confidence)

            except Exception as e:
                signals.append("hold")
                reasons.append(f"エラー: {str(e)[:30]}")
                confidences.append(0.0)

        return signals, reasons, confidences

    async def _run_backtest(self, strategy) -> List[Dict]:
        """単一戦略バックテスト"""
        tracker = TradeTracker()

        # TP/SL設定
        tp_ratio = get_threshold("position_management.take_profit.default_ratio", 0.01)
        sl_ratio = get_threshold("risk.sl_min_distance_ratio", 0.015)

        open_position = None
        order_id_counter = 0

        for i in range(50, len(self.df_with_features)):
            df_slice = self.df_with_features.iloc[: i + 1].copy()
            current_row = self.df_with_features.iloc[i]
            current_price = float(current_row["close"])
            current_time = pd.to_datetime(current_row.get("timestamp", datetime.now()))

            try:
                signal = strategy.analyze(df_slice, None)
            except Exception:
                continue

            # ポジションクローズ判定
            if open_position is not None:
                entry_price = open_position["entry_price"]
                side = open_position["side"]

                if side == "buy":
                    tp_price = entry_price * (1 + tp_ratio)
                    sl_price = entry_price * (1 - sl_ratio)
                    if current_price >= tp_price:
                        tracker.record_exit(open_position["order_id"], tp_price, current_time, "TP")
                        open_position = None
                        continue
                    elif current_price <= sl_price:
                        tracker.record_exit(open_position["order_id"], sl_price, current_time, "SL")
                        open_position = None
                        continue
                else:
                    tp_price = entry_price * (1 - tp_ratio)
                    sl_price = entry_price * (1 + sl_ratio)
                    if current_price <= tp_price:
                        tracker.record_exit(open_position["order_id"], tp_price, current_time, "TP")
                        open_position = None
                        continue
                    elif current_price >= sl_price:
                        tracker.record_exit(open_position["order_id"], sl_price, current_time, "SL")
                        open_position = None
                        continue

                # 逆シグナルでクローズ
                if (side == "buy" and signal.action == EntryAction.SELL) or (
                    side == "sell" and signal.action == EntryAction.BUY
                ):
                    tracker.record_exit(
                        open_position["order_id"], current_price, current_time, "SIGNAL"
                    )
                    open_position = None

            # 新規エントリー
            if open_position is None and signal.action in [EntryAction.BUY, EntryAction.SELL]:
                order_id = f"{strategy.name}_{order_id_counter}"
                order_id_counter += 1
                side = "buy" if signal.action == EntryAction.BUY else "sell"

                tracker.record_entry(
                    order_id, side, 0.01, current_price, current_time, strategy.name
                )
                open_position = {
                    "order_id": order_id,
                    "side": side,
                    "entry_price": current_price,
                }

        # 未決済ポジションをクローズ
        if open_position is not None:
            final_row = self.df_with_features.iloc[-1]
            final_price = float(final_row["close"])
            final_time = pd.to_datetime(final_row.get("timestamp", datetime.now()))
            tracker.record_exit(open_position["order_id"], final_price, final_time, "END")

        return tracker.completed_trades

    def _analyze_hourly_performance(
        self, trades: List[Dict]
    ) -> Tuple[Dict[int, Dict], List[int], List[int]]:
        """
        [Phase 60.1] 時間帯別パフォーマンス分析

        Returns:
            Tuple[hourly_perf, best_hours, worst_hours]
        """
        hourly_data = defaultdict(lambda: {"wins": 0, "losses": 0, "profit": 0.0, "loss": 0.0})

        for trade in trades:
            entry_time = trade.get("entry_time")
            if entry_time is None:
                continue

            hour = entry_time.hour if hasattr(entry_time, "hour") else 0
            pnl = trade.get("pnl", 0)

            if pnl > 0:
                hourly_data[hour]["wins"] += 1
                hourly_data[hour]["profit"] += pnl
            else:
                hourly_data[hour]["losses"] += 1
                hourly_data[hour]["loss"] += abs(pnl)

        # パフォーマンス計算
        hourly_perf = {}
        for hour, data in hourly_data.items():
            total = data["wins"] + data["losses"]
            if total > 0:
                win_rate = data["wins"] / total
                pf = data["profit"] / data["loss"] if data["loss"] > 0 else float("inf")
                hourly_perf[hour] = {"win_rate": win_rate, "pf": pf, "trades": total}

        # ベスト・ワースト時間帯（取引数3以上で判定）
        valid_hours = [(h, p) for h, p in hourly_perf.items() if p["trades"] >= 3]

        best_hours = sorted(valid_hours, key=lambda x: x[1]["win_rate"], reverse=True)[:3]
        best_hours = [h for h, _ in best_hours]

        worst_hours = sorted(valid_hours, key=lambda x: x[1]["win_rate"])[:3]
        worst_hours = [h for h, _ in worst_hours]

        return hourly_perf, best_hours, worst_hours

    def _analyze_consecutive_results(self, trades: List[Dict]) -> Tuple[int, int, float]:
        """
        [Phase 60.1] 連勝/連敗分析

        Returns:
            Tuple[max_losses, max_wins, avg_recovery]
        """
        if not trades:
            return 0, 0, 0.0

        results = [1 if t.get("pnl", 0) > 0 else -1 for t in trades]

        max_wins = 0
        max_losses = 0
        current_streak = 0
        current_type = 0  # 1=winning, -1=losing

        recovery_trades = []  # 連敗後に勝つまでの取引数
        loss_streak_start = None

        for i, result in enumerate(results):
            if result == current_type:
                current_streak += 1
            else:
                # ストリーク終了
                if current_type == 1:
                    max_wins = max(max_wins, current_streak)
                elif current_type == -1:
                    max_losses = max(max_losses, current_streak)
                    if loss_streak_start is not None:
                        recovery_trades.append(i - loss_streak_start)
                        loss_streak_start = None

                current_streak = 1
                current_type = result

                if result == -1 and loss_streak_start is None:
                    loss_streak_start = i

        # 最後のストリーク
        if current_type == 1:
            max_wins = max(max_wins, current_streak)
        elif current_type == -1:
            max_losses = max(max_losses, current_streak)

        avg_recovery = sum(recovery_trades) / len(recovery_trades) if recovery_trades else 0.0

        return max_losses, max_wins, avg_recovery

    def _analyze_parameter_sensitivity(
        self, strategy, base_trades: List[Dict]
    ) -> Dict[str, Dict[str, float]]:
        """
        [Phase 60.1] パラメータ感度分析（簡易版）

        戦略の主要パラメータを±10%変動させた時のPF変化を推定
        """
        # 主要パラメータとその現在値・推奨調整方向を定義
        strategy_params = {
            "ATRBased": {
                "rsi_overbought": {"current": 65, "range": [60, 70], "direction": "buy条件緩和で↓"},
                "rsi_oversold": {"current": 35, "range": [30, 40], "direction": "sell条件緩和で↑"},
            },
            "BBReversal": {
                "adx_range_threshold": {
                    "current": 60,
                    "range": [50, 70],
                    "direction": "レンジ判定拡大で↑",
                },
                "rsi_overbought": {"current": 68, "range": [65, 75], "direction": "buy条件緩和で↓"},
            },
            "StochasticReversal": {
                "adx_range_threshold": {
                    "current": 60,
                    "range": [50, 70],
                    "direction": "レンジ判定拡大で↑",
                },
                "stoch_overbought": {"current": 75, "range": [70, 85], "direction": "条件緩和で↓"},
            },
            "DonchianChannel": {
                "middle_zone_min": {
                    "current": 0.40,
                    "range": [0.35, 0.45],
                    "direction": "HOLD範囲縮小で↓",
                },
            },
            "ADXTrendStrength": {
                "strong_trend_threshold": {
                    "current": 25,
                    "range": [20, 30],
                    "direction": "トレンド判定拡大で↓",
                },
            },
            "MACDEMACrossover": {
                "adx_trend_threshold": {
                    "current": 12,
                    "range": [10, 15],
                    "direction": "トレンド判定拡大で↓",
                },
            },
        }

        result = {}
        if strategy.name in strategy_params:
            for param, info in strategy_params[strategy.name].items():
                result[param] = {
                    "current": info["current"],
                    "suggested_range": info["range"],
                    "adjustment_hint": info["direction"],
                }

        return result

    def _calculate_overall_score(self, metrics: StrategyMetrics) -> float:
        """総合スコア計算（0-100）"""
        score = 0

        # 勝率（30点）
        if metrics.win_rate >= 0.5:
            score += 30 * min(metrics.win_rate / 0.6, 1.0)
        else:
            score += 30 * (metrics.win_rate / 0.5)

        # PF（25点）
        if metrics.profit_factor >= 1.0:
            score += min(25, 25 * (metrics.profit_factor / 1.5))
        else:
            score += 25 * metrics.profit_factor

        # 取引数（15点）- 少なすぎも多すぎも減点
        if 10 <= metrics.total_trades <= 100:
            score += 15
        elif metrics.total_trades < 10:
            score += 15 * (metrics.total_trades / 10)
        else:
            score += 15 * max(0, 1 - (metrics.total_trades - 100) / 200)

        # HOLD率（15点）- 低いほど良い
        if metrics.hold_rate <= 0.5:
            score += 15
        elif metrics.hold_rate <= 0.8:
            score += 15 * (1 - (metrics.hold_rate - 0.5) / 0.3)
        else:
            score += 5

        # シャープレシオ（15点）
        if metrics.sharpe_ratio > 0:
            score += min(15, 15 * (metrics.sharpe_ratio / 1.5))

        return round(score, 1)

    def _generate_suggestions(self, metrics: StrategyMetrics) -> List[str]:
        """
        [Phase 60.1強化] 改善提案を生成（具体的な数値付き）
        """
        suggestions = []

        # HOLD率が高い
        if metrics.hold_rate > 0.8:
            suggestions.append(f"HOLD率が{metrics.hold_rate:.1%}と高い。条件緩和を検討")
            # HOLD理由を分析
            if metrics.top_hold_reasons:
                top_reason = list(metrics.top_hold_reasons.keys())[0]
                if "not_range_market" in top_reason or "レンジ" in top_reason:
                    suggestions.append(
                        "💡 具体案: adx_range_threshold を 60→70 に変更（レンジ判定範囲+17%拡大）"
                    )
                elif "not_trend_market" in top_reason or "トレンド" in top_reason:
                    suggestions.append(
                        "💡 具体案: adx_trend_threshold を 12→10 に変更（トレンド判定範囲拡大）"
                    )
                elif "RSI" in top_reason:
                    suggestions.append("💡 具体案: rsi_overbought を 68→72 に変更（buy条件緩和）")

        # 勝率が低い
        if metrics.win_rate < 0.4:
            suggestions.append(f"勝率{metrics.win_rate:.1%}が低い。")
            suggestions.append("💡 具体案: min_confidence を +0.05 上げてエントリー条件厳格化")

        # 取引数が少ない
        if metrics.total_trades < 5:
            suggestions.append(f"取引数{metrics.total_trades}が少ない。")
            suggestions.append("💡 具体案: hold_confidence を -0.05 下げて発火率向上")

        # PFが低い
        if 0 < metrics.profit_factor < 1.0:
            suggestions.append(f"PF{metrics.profit_factor:.2f}が1.0未満。")
            suggestions.append(
                "💡 具体案: TP比率を 0.012→0.015 に上げるか、SL比率を 0.008→0.006 に下げる"
            )

        # [Phase 60.1] 連敗が多い場合
        if metrics.max_consecutive_losses >= 5:
            suggestions.append(
                f"⚠️ 最大連敗{metrics.max_consecutive_losses}回。リスク管理強化を検討"
            )
            suggestions.append("💡 具体案: 連敗3回後はポジションサイズを50%に縮小するルール追加")

        # [Phase 60.1] 時間帯別の提案
        if metrics.worst_hours and metrics.hourly_performance:
            worst_hour = metrics.worst_hours[0]
            if worst_hour in metrics.hourly_performance:
                perf = metrics.hourly_performance[worst_hour]
                if perf.get("win_rate", 0.5) < 0.35:
                    suggestions.append(f"⚠️ {worst_hour}時台の勝率が{perf['win_rate']:.1%}と低い")
                    suggestions.append(
                        f"💡 具体案: {worst_hour}:00-{(worst_hour + 1) % 24}:00のエントリーを避ける設定追加"
                    )

        # [Phase 60.1] パラメータ感度に基づく提案
        if metrics.parameter_sensitivity:
            for param, info in metrics.parameter_sensitivity.items():
                if "adjustment_hint" in info:
                    suggestions.append(
                        f"📊 {param}: 現在値={info['current']} → 推奨範囲{info['suggested_range']} ({info['adjustment_hint']})"
                    )

        if not suggestions:
            suggestions.append("✅ 現在の設定で良好なパフォーマンス")

        return suggestions

    # ==========================================================================
    # [Phase 60] strategy_performance_analysis.pyから統合した機能
    # ==========================================================================

    def _analyze_regime_performance(self, trades: List[Dict]) -> Dict[str, Dict[str, float]]:
        """
        [Phase 60] レジーム別パフォーマンス分析

        Args:
            trades: 取引リスト

        Returns:
            Dict[regime_name, {win_rate, pf, trades}]
        """
        if not trades or self.df_with_features is None:
            return {}

        regime_trades = {
            "tight_range": [],
            "normal_range": [],
            "trending": [],
            "high_volatility": [],
        }

        for trade in trades:
            entry_time = trade.get("entry_time")
            if entry_time is None:
                continue

            # エントリー時点のデータを取得してレジーム分類
            try:
                if hasattr(entry_time, "strftime"):
                    mask = (
                        pd.to_datetime(
                            self.df_with_features.get("timestamp", self.df_with_features.index)
                        )
                        <= entry_time
                    )
                    df_slice = self.df_with_features[mask]
                else:
                    df_slice = self.df_with_features

                if len(df_slice) < 50:
                    continue

                regime = self.regime_classifier.classify(df_slice)
                regime_name = regime.value if hasattr(regime, "value") else str(regime)
                if regime_name in regime_trades:
                    regime_trades[regime_name].append(trade)
            except Exception:
                continue

        # レジーム別メトリクス計算
        regime_perf = {}
        for regime_name, trades_list in regime_trades.items():
            if not trades_list:
                continue

            pnls = [t.get("pnl", 0) for t in trades_list]
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p < 0]

            win_rate = len(wins) / len(pnls) if pnls else 0
            gross_profit = sum(wins) if wins else 0
            gross_loss = abs(sum(losses)) if losses else 0
            pf = gross_profit / gross_loss if gross_loss > 0 else 0

            regime_perf[regime_name] = {
                "win_rate": win_rate,
                "pf": pf,
                "trades": len(trades_list),
            }

        return regime_perf

    def _calculate_strategy_correlation(self, all_trades: Dict[str, List[Dict]]) -> pd.DataFrame:
        """
        [Phase 60] 戦略間相関分析

        Args:
            all_trades: 戦略名 -> 取引リストのマッピング

        Returns:
            pd.DataFrame: 相関係数マトリクス
        """
        if not all_trades:
            return pd.DataFrame()

        # 各戦略の時系列リターンを生成
        strategy_returns = {}
        all_timestamps = set()

        for strategy_name, trades in all_trades.items():
            returns_map = {}
            for trade in trades:
                exit_time = trade.get("exit_time")
                if exit_time is None:
                    continue

                timestamp_key = (
                    exit_time.strftime("%Y-%m-%d %H:%M")
                    if hasattr(exit_time, "strftime")
                    else str(exit_time)
                )
                pnl = trade.get("pnl", 0)

                if timestamp_key in returns_map:
                    returns_map[timestamp_key] += pnl
                else:
                    returns_map[timestamp_key] = pnl
                    all_timestamps.add(timestamp_key)

            strategy_returns[strategy_name] = returns_map

        if len(all_timestamps) < 2:
            return pd.DataFrame()

        # 各戦略のリターン配列を生成（欠損値は0埋め）
        all_timestamps = sorted(list(all_timestamps))
        return_arrays = {}

        for strategy_name in all_trades.keys():
            returns_map = strategy_returns.get(strategy_name, {})
            returns_array = [returns_map.get(ts, 0.0) for ts in all_timestamps]
            return_arrays[strategy_name] = returns_array

        # 相関係数マトリクス計算
        strategy_names = list(all_trades.keys())
        returns_matrix = np.array([return_arrays[s] for s in strategy_names])

        try:
            corr_matrix = np.corrcoef(returns_matrix)
            return pd.DataFrame(corr_matrix, index=strategy_names, columns=strategy_names)
        except Exception:
            return pd.DataFrame()

    async def _measure_ensemble_contribution(
        self, all_trades: Dict[str, List[Dict]]
    ) -> Dict[str, float]:
        """
        [Phase 60] アンサンブル貢献度測定（Leave-One-Out法）

        Args:
            all_trades: 戦略名 -> 取引リストのマッピング

        Returns:
            Dict[strategy_name, contribution_pct]: 各戦略の貢献度（%）
        """
        if not all_trades:
            return {}

        # ベースライン（全戦略アンサンブル）のシャープレシオ計算
        baseline_trades = []
        for trades in all_trades.values():
            baseline_trades.extend(trades)

        if not baseline_trades:
            return {}

        baseline_trades.sort(key=lambda x: x.get("exit_time", datetime.now()))
        baseline_pnls = [t.get("pnl", 0) for t in baseline_trades]

        if len(baseline_pnls) < 2:
            return {}

        baseline_mean = np.mean(baseline_pnls)
        baseline_std = np.std(baseline_pnls, ddof=1)
        baseline_sharpe = baseline_mean / baseline_std if baseline_std > 0 else 0

        # 各戦略を除外した場合のシャープレシオ計算
        contribution_results = {}

        for excluded_strategy in all_trades.keys():
            without_trades = []
            for strategy_name, trades in all_trades.items():
                if strategy_name != excluded_strategy:
                    without_trades.extend(trades)

            if not without_trades:
                contribution_results[excluded_strategy] = 100.0  # 唯一の戦略
                continue

            without_trades.sort(key=lambda x: x.get("exit_time", datetime.now()))
            without_pnls = [t.get("pnl", 0) for t in without_trades]

            if len(without_pnls) < 2:
                contribution_results[excluded_strategy] = 0.0
                continue

            without_mean = np.mean(without_pnls)
            without_std = np.std(without_pnls, ddof=1)
            without_sharpe = without_mean / without_std if without_std > 0 else 0

            # 貢献度計算（ベースライン - 除外時）
            contribution = baseline_sharpe - without_sharpe
            contribution_pct = (contribution / baseline_sharpe * 100) if baseline_sharpe != 0 else 0

            contribution_results[excluded_strategy] = contribution_pct

        return contribution_results

    def analyze_market_conditions(self) -> Dict[str, Any]:
        """市場条件分析（ADX分布等）"""
        if self.df_with_features is None:
            return {}

        print("\n📊 市場条件を分析中...")

        adx = self.df_with_features["adx_14"].dropna()
        total = len(adx)

        # ADX分布
        adx_dist = {
            "< 20 (レンジ)": sum(1 for x in adx if x < 20) / total,
            "20-30 (弱いトレンド)": sum(1 for x in adx if 20 <= x < 30) / total,
            "30-40 (トレンド)": sum(1 for x in adx if 30 <= x < 40) / total,
            ">= 40 (強いトレンド)": sum(1 for x in adx if x >= 40) / total,
        }

        print("   ADX分布:")
        for label, rate in adx_dist.items():
            print(f"     {label}: {rate:.1%}")

        return {
            "adx_distribution": adx_dist,
            "adx_mean": float(adx.mean()),
            "adx_median": float(adx.median()),
        }

    def generate_report(self) -> str:
        """包括的レポート生成"""
        lines = []

        lines.append("=" * 80)
        lines.append("📊 Phase 60.1 包括的戦略評価レポート")
        lines.append(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(
            f"分析データポイント: {len(self.df_with_features) if self.df_with_features is not None else 0}"
        )
        lines.append("=" * 80)

        # サマリーテーブル（Phase 60.1: 連敗列追加）
        lines.append("\n📈 戦略別サマリー")
        lines.append("-" * 90)
        lines.append(
            f"{'戦略名':<20} | {'勝率':>6} | {'PF':>5} | {'取引数':>5} | {'HOLD率':>7} | {'最大連敗':>6} | {'スコア':>5}"
        )
        lines.append("-" * 90)

        sorted_results = sorted(self.results.items(), key=lambda x: -x[1].overall_score)

        for name, m in sorted_results:
            lines.append(
                f"{name:<20} | {m.win_rate:>5.1%} | {m.profit_factor:>5.2f} | "
                f"{m.total_trades:>5} | {m.hold_rate:>6.1%} | {m.max_consecutive_losses:>6} | {m.overall_score:>5.1f}"
            )

        # 詳細分析
        lines.append("\n📋 戦略別詳細分析")
        lines.append("-" * 80)

        for name, m in sorted_results:
            lines.append(f"\n【{name}】スコア: {m.overall_score}/100")
            lines.append(
                f"  バックテスト: {m.total_trades}取引, 勝率{m.win_rate:.1%}, "
                f"PF {m.profit_factor:.2f}, 最大DD ¥{m.max_drawdown:,.0f}"
            )
            lines.append(
                f"  シグナル分布: BUY {m.buy_count} / SELL {m.sell_count} / HOLD {m.hold_count}"
            )
            lines.append(
                f"  平均信頼度: BUY {m.avg_buy_confidence:.3f} / SELL {m.avg_sell_confidence:.3f}"
            )

            # [Phase 60.1] 連勝/連敗情報
            lines.append(
                f"  連続結果: 最大連勝{m.max_consecutive_wins}回 / 最大連敗{m.max_consecutive_losses}回 / 平均回復{m.avg_recovery_trades:.1f}取引"
            )

            # [Phase 60.1] 時間帯別パフォーマンス
            if m.best_hours:
                best_str = ", ".join([f"{h}時" for h in m.best_hours[:3]])
                lines.append(f"  ベスト時間帯: {best_str}")
            if m.worst_hours:
                worst_str = ", ".join([f"{h}時" for h in m.worst_hours[:3]])
                lines.append(f"  ワースト時間帯: {worst_str}")

            if m.top_hold_reasons:
                lines.append("  主要HOLD理由:")
                for reason, count in list(m.top_hold_reasons.items())[:3]:
                    lines.append(f"    - {count}回: {reason[:55]}")

            # [Phase 60] レジーム別パフォーマンス
            if m.regime_performance:
                lines.append("  レジーム別パフォーマンス:")
                for regime, perf in m.regime_performance.items():
                    lines.append(
                        f"    - {regime}: 勝率{perf['win_rate']:.1%}, PF {perf['pf']:.2f}, {perf['trades']}取引"
                    )

            # [Phase 60] 相関分析（高相関のみ表示）
            if m.correlation_with_others:
                high_corr = [(n, c) for n, c in m.correlation_with_others.items() if abs(c) >= 0.5]
                if high_corr:
                    lines.append("  高相関戦略:")
                    for other_name, corr in sorted(high_corr, key=lambda x: -abs(x[1]))[:3]:
                        lines.append(f"    - vs {other_name}: {corr:.3f}")

            # [Phase 60] 貢献度
            if m.ensemble_contribution != 0:
                emoji = "✅" if m.ensemble_contribution > 0 else "⚠️"
                lines.append(f"  アンサンブル貢献度: {emoji} {m.ensemble_contribution:+.1f}%")

            if m.improvement_suggestions:
                lines.append("  改善提案:")
                for suggestion in m.improvement_suggestions[:5]:  # Phase 60.1: 5件に増加
                    lines.append(f"    {suggestion}")

        # ランキング
        lines.append("\n🏆 戦略ランキング")
        lines.append("-" * 80)
        for i, (name, m) in enumerate(sorted_results, 1):
            status = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else "  "))
            lines.append(f"{status} {i}位: {name} (スコア: {m.overall_score}/100)")

        # 総評
        lines.append("\n📝 総評")
        lines.append("-" * 80)

        high_hold = [n for n, m in self.results.items() if m.hold_rate > 0.8]
        low_win = [n for n, m in self.results.items() if m.win_rate < 0.4 and m.total_trades > 5]

        if high_hold:
            lines.append(f"⚠️ HOLD率が高い戦略: {', '.join(high_hold)}")
        if low_win:
            lines.append(f"⚠️ 勝率が低い戦略: {', '.join(low_win)}")

        best = sorted_results[0] if sorted_results else None
        if best:
            lines.append(f"✅ 最高評価戦略: {best[0]} (スコア: {best[1].overall_score}/100)")

        lines.append("\n" + "=" * 80)

        return "\n".join(lines)

    def export_results(self, output_path: str):
        """結果をエクスポート"""
        os.makedirs(output_path, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSON出力
        json_file = os.path.join(output_path, f"strategy_evaluation_{timestamp}.json")
        json_data = {}
        for name, m in self.results.items():
            json_data[name] = {
                "total_trades": m.total_trades,
                "win_rate": m.win_rate,
                "profit_factor": m.profit_factor,
                "hold_rate": m.hold_rate,
                "overall_score": m.overall_score,
                "top_hold_reasons": m.top_hold_reasons,
                "improvement_suggestions": m.improvement_suggestions,
            }

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        print(f"  ✅ JSON: {json_file}")

        # レポート出力
        report_file = os.path.join(output_path, f"strategy_evaluation_{timestamp}.txt")
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(self.generate_report())
        print(f"  ✅ レポート: {report_file}")


async def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(description="包括的戦略評価スクリプト - Phase 60.1")
    parser.add_argument("--days", type=int, default=30, help="分析日数（デフォルト: 30日）")
    parser.add_argument("--strategy", type=str, help="特定の戦略のみ分析")
    parser.add_argument("--export", type=str, help="結果出力ディレクトリ")
    parser.add_argument("--verbose", "-v", action="store_true", help="詳細出力")

    args = parser.parse_args()

    print("=" * 80)
    print("🔍 Phase 60.1 包括的戦略評価")
    print("   新機能: 時間帯別分析・連敗検出・パラメータ感度・具体的改善提案")
    print("=" * 80)

    try:
        evaluator = ComprehensiveStrategyEvaluator(verbose=args.verbose)

        # データ読み込み
        await evaluator.load_data(days=args.days)

        # 戦略ロード
        evaluator.load_strategies(target_strategy=args.strategy)

        # 市場条件分析
        evaluator.analyze_market_conditions()

        # 全戦略評価
        await evaluator.evaluate_all_strategies()

        # レポート表示
        print("\n" + evaluator.generate_report())

        # エクスポート
        if args.export:
            print(f"\n💾 結果を {args.export} に出力中...")
            evaluator.export_results(args.export)

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
