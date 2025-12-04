#!/usr/bin/env python3
"""
高度トレード分析スクリプト - Phase 60.2

バックテスト結果の詳細分析と可視化を行うスクリプト。
comprehensive_strategy_evaluation.pyとは別の視点で分析を提供。

使用方法:
    python scripts/analysis/advanced_trade_analysis.py --days 30
    python scripts/analysis/advanced_trade_analysis.py --days 30 --export ./output
    python scripts/analysis/advanced_trade_analysis.py --days 30 --visualize

機能:
    1. 時間帯・曜日別パフォーマンス分析
    2. 連勝/連敗パターン分析
    3. 損益分布可視化（ヒストグラム・箱ひげ図）
    4. 最適エントリー条件特定
    5. 累積損益曲線
"""

import argparse
import asyncio
import json
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
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
from src.features.feature_generator import FeatureGenerator
from src.strategies.strategy_loader import StrategyLoader
from src.strategies.utils import EntryAction


@dataclass
class TradeAnalysisResult:
    """トレード分析結果"""

    # 基本統計
    total_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_pnl: float = 0.0

    # 時間帯別
    hourly_stats: Dict[int, Dict[str, float]] = None  # hour -> {win_rate, pf, trades, avg_pnl}
    best_hours: List[int] = None
    worst_hours: List[int] = None

    # 曜日別
    weekday_stats: Dict[int, Dict[str, float]] = None  # 0=Mon -> {win_rate, pf, trades}
    best_weekdays: List[str] = None
    worst_weekdays: List[str] = None

    # 連続結果
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    avg_win_streak: float = 0.0
    avg_loss_streak: float = 0.0
    recovery_analysis: Dict[str, float] = None  # 連敗後の回復パターン

    # 損益分布
    pnl_distribution: Dict[str, float] = None  # mean, median, std, skew, percentiles

    # 最適条件
    optimal_conditions: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.hourly_stats is None:
            self.hourly_stats = {}
        if self.weekday_stats is None:
            self.weekday_stats = {}
        if self.best_hours is None:
            self.best_hours = []
        if self.worst_hours is None:
            self.worst_hours = []
        if self.best_weekdays is None:
            self.best_weekdays = []
        if self.worst_weekdays is None:
            self.worst_weekdays = []
        if self.recovery_analysis is None:
            self.recovery_analysis = {}
        if self.pnl_distribution is None:
            self.pnl_distribution = {}
        if self.optimal_conditions is None:
            self.optimal_conditions = []


class AdvancedTradeAnalyzer:
    """高度トレード分析器"""

    WEEKDAY_NAMES = ["月", "火", "水", "木", "金", "土", "日"]

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.df = None
        self.df_with_features = None
        self.trades: List[Dict] = []
        self.result = TradeAnalysisResult()

    async def load_data(self, days: int = 30, csv_path: Optional[str] = None) -> pd.DataFrame:
        """履歴データを読み込み"""
        print(f"📊 {days}日分のデータを取得中...")

        default_csv = str(project_root / "src/backtest/data/historical/BTC_JPY_15m.csv")
        csv_file = csv_path or default_csv

        if not os.path.exists(csv_file):
            raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_file}")

        print(f"   📁 CSVから読み込み: {csv_file}")
        df_raw = pd.read_csv(csv_file)

        if "timestamp" in df_raw.columns:
            df_raw["timestamp"] = pd.to_datetime(df_raw["timestamp"])
        elif "datetime" in df_raw.columns:
            df_raw["timestamp"] = pd.to_datetime(df_raw["datetime"])

        rows_needed = days * 96
        if len(df_raw) > rows_needed:
            df_raw = df_raw.tail(rows_needed)

        self.df = df_raw

        print("   🔧 特徴量生成中...")
        feature_gen = FeatureGenerator()
        self.df_with_features = await feature_gen.generate_features(df_raw.copy())

        print(f"✅ {len(self.df_with_features)}データポイントを取得")
        return self.df_with_features

    async def run_backtest(self) -> List[Dict]:
        """統合バックテスト実行"""
        print("🔄 バックテスト実行中...")

        tracker = TradeTracker()
        loader = StrategyLoader("config/core/strategies.yaml")
        strategy_configs = loader.load_strategies()
        strategies = [config["instance"] for config in strategy_configs]

        tp_ratio = get_threshold("position_management.take_profit.default_ratio", 0.012)
        sl_ratio = get_threshold("risk.sl_min_distance_ratio", 0.008)

        open_position = None
        order_id_counter = 0

        for i in range(50, len(self.df_with_features)):
            df_slice = self.df_with_features.iloc[: i + 1].copy()
            current_row = self.df_with_features.iloc[i]
            current_price = float(current_row["close"])
            current_time = pd.to_datetime(current_row.get("timestamp", datetime.now()))

            # 多数決シグナル
            votes = {"buy": 0, "sell": 0, "hold": 0}
            for strategy in strategies:
                try:
                    signal = strategy.analyze(df_slice, None)
                    action = (
                        signal.action.value.lower()
                        if hasattr(signal.action, "value")
                        else str(signal.action).lower()
                    )
                    if action in votes:
                        votes[action] += 1
                except Exception:
                    votes["hold"] += 1

            final_action = max(votes, key=votes.get)

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
                if (side == "buy" and final_action == "sell") or (
                    side == "sell" and final_action == "buy"
                ):
                    tracker.record_exit(
                        open_position["order_id"], current_price, current_time, "SIGNAL"
                    )
                    open_position = None

            # 新規エントリー
            if open_position is None and final_action in ["buy", "sell"]:
                order_id = f"trade_{order_id_counter}"
                order_id_counter += 1

                tracker.record_entry(
                    order_id, final_action, 0.01, current_price, current_time, "multi_strategy"
                )
                open_position = {
                    "order_id": order_id,
                    "side": final_action,
                    "entry_price": current_price,
                }

        # 未決済ポジションをクローズ
        if open_position is not None:
            final_row = self.df_with_features.iloc[-1]
            final_price = float(final_row["close"])
            final_time = pd.to_datetime(final_row.get("timestamp", datetime.now()))
            tracker.record_exit(open_position["order_id"], final_price, final_time, "END")

        self.trades = tracker.completed_trades
        print(f"✅ {len(self.trades)}件の取引を完了")
        return self.trades

    def analyze_hourly_performance(self) -> Dict[int, Dict[str, float]]:
        """時間帯別パフォーマンス分析"""
        hourly_data = defaultdict(
            lambda: {"wins": 0, "losses": 0, "profit": 0.0, "loss": 0.0, "pnls": []}
        )

        for trade in self.trades:
            entry_time = trade.get("entry_time")
            if entry_time is None:
                continue

            hour = entry_time.hour if hasattr(entry_time, "hour") else 0
            pnl = trade.get("pnl", 0)

            hourly_data[hour]["pnls"].append(pnl)
            if pnl > 0:
                hourly_data[hour]["wins"] += 1
                hourly_data[hour]["profit"] += pnl
            else:
                hourly_data[hour]["losses"] += 1
                hourly_data[hour]["loss"] += abs(pnl)

        hourly_stats = {}
        for hour in range(24):
            data = hourly_data[hour]
            total = data["wins"] + data["losses"]
            if total > 0:
                win_rate = data["wins"] / total
                pf = data["profit"] / data["loss"] if data["loss"] > 0 else float("inf")
                avg_pnl = sum(data["pnls"]) / len(data["pnls"]) if data["pnls"] else 0
                hourly_stats[hour] = {
                    "win_rate": win_rate,
                    "pf": min(pf, 10.0),  # 上限
                    "trades": total,
                    "avg_pnl": avg_pnl,
                }

        self.result.hourly_stats = hourly_stats

        # ベスト・ワースト（取引数3以上）
        valid = [(h, s) for h, s in hourly_stats.items() if s["trades"] >= 3]
        if valid:
            self.result.best_hours = [
                h for h, _ in sorted(valid, key=lambda x: x[1]["win_rate"], reverse=True)[:3]
            ]
            self.result.worst_hours = [
                h for h, _ in sorted(valid, key=lambda x: x[1]["win_rate"])[:3]
            ]

        return hourly_stats

    def analyze_weekday_performance(self) -> Dict[int, Dict[str, float]]:
        """曜日別パフォーマンス分析"""
        weekday_data = defaultdict(lambda: {"wins": 0, "losses": 0, "profit": 0.0, "loss": 0.0})

        for trade in self.trades:
            entry_time = trade.get("entry_time")
            if entry_time is None:
                continue

            weekday = entry_time.weekday() if hasattr(entry_time, "weekday") else 0
            pnl = trade.get("pnl", 0)

            if pnl > 0:
                weekday_data[weekday]["wins"] += 1
                weekday_data[weekday]["profit"] += pnl
            else:
                weekday_data[weekday]["losses"] += 1
                weekday_data[weekday]["loss"] += abs(pnl)

        weekday_stats = {}
        for day in range(7):
            data = weekday_data[day]
            total = data["wins"] + data["losses"]
            if total > 0:
                win_rate = data["wins"] / total
                pf = data["profit"] / data["loss"] if data["loss"] > 0 else float("inf")
                weekday_stats[day] = {
                    "win_rate": win_rate,
                    "pf": min(pf, 10.0),
                    "trades": total,
                }

        self.result.weekday_stats = weekday_stats

        # ベスト・ワースト
        if weekday_stats:
            sorted_days = sorted(
                weekday_stats.items(), key=lambda x: x[1]["win_rate"], reverse=True
            )
            self.result.best_weekdays = [self.WEEKDAY_NAMES[d] for d, _ in sorted_days[:2]]
            self.result.worst_weekdays = [self.WEEKDAY_NAMES[d] for d, _ in sorted_days[-2:]]

        return weekday_stats

    def analyze_consecutive_patterns(self) -> Dict[str, Any]:
        """連勝/連敗パターン分析"""
        if not self.trades:
            return {}

        results = [1 if t.get("pnl", 0) > 0 else -1 for t in self.trades]

        # ストリーク分析
        win_streaks = []
        loss_streaks = []
        current_streak = 1
        current_type = results[0]

        for i in range(1, len(results)):
            if results[i] == current_type:
                current_streak += 1
            else:
                if current_type == 1:
                    win_streaks.append(current_streak)
                else:
                    loss_streaks.append(current_streak)
                current_streak = 1
                current_type = results[i]

        # 最後のストリーク
        if current_type == 1:
            win_streaks.append(current_streak)
        else:
            loss_streaks.append(current_streak)

        self.result.max_consecutive_wins = max(win_streaks) if win_streaks else 0
        self.result.max_consecutive_losses = max(loss_streaks) if loss_streaks else 0
        self.result.avg_win_streak = sum(win_streaks) / len(win_streaks) if win_streaks else 0
        self.result.avg_loss_streak = sum(loss_streaks) / len(loss_streaks) if loss_streaks else 0

        # 連敗後の回復分析
        recovery_after_loss = defaultdict(list)
        current_loss_streak = 0

        for i, result in enumerate(results):
            if result == -1:
                current_loss_streak += 1
            else:
                if current_loss_streak > 0:
                    # 連敗後に勝った
                    recovery_after_loss[current_loss_streak].append(i)
                current_loss_streak = 0

        self.result.recovery_analysis = {
            "loss_streak_2_recovery_rate": len(recovery_after_loss.get(2, []))
            / max(len([s for s in loss_streaks if s >= 2]), 1),
            "loss_streak_3_recovery_rate": len(recovery_after_loss.get(3, []))
            / max(len([s for s in loss_streaks if s >= 3]), 1),
            "avg_recovery_trades": sum(len(v) for v in recovery_after_loss.values())
            / max(len(recovery_after_loss), 1),
        }

        return {
            "max_wins": self.result.max_consecutive_wins,
            "max_losses": self.result.max_consecutive_losses,
            "avg_win_streak": self.result.avg_win_streak,
            "avg_loss_streak": self.result.avg_loss_streak,
            "recovery": self.result.recovery_analysis,
        }

    def analyze_pnl_distribution(self) -> Dict[str, float]:
        """損益分布分析"""
        if not self.trades:
            return {}

        pnls = [t.get("pnl", 0) for t in self.trades]
        pnls_array = np.array(pnls)

        distribution = {
            "mean": float(np.mean(pnls_array)),
            "median": float(np.median(pnls_array)),
            "std": float(np.std(pnls_array)),
            "min": float(np.min(pnls_array)),
            "max": float(np.max(pnls_array)),
            "percentile_10": float(np.percentile(pnls_array, 10)),
            "percentile_25": float(np.percentile(pnls_array, 25)),
            "percentile_75": float(np.percentile(pnls_array, 75)),
            "percentile_90": float(np.percentile(pnls_array, 90)),
            "positive_count": int(np.sum(pnls_array > 0)),
            "negative_count": int(np.sum(pnls_array < 0)),
        }

        # 歪度（スキュー）
        if distribution["std"] > 0:
            distribution["skewness"] = float(
                ((pnls_array - distribution["mean"]) ** 3).mean() / (distribution["std"] ** 3)
            )
        else:
            distribution["skewness"] = 0.0

        self.result.pnl_distribution = distribution
        return distribution

    def find_optimal_conditions(self) -> List[Dict[str, Any]]:
        """最適エントリー条件の特定"""
        conditions = []

        # 時間帯条件
        if self.result.hourly_stats:
            best_hours = [
                h
                for h, s in self.result.hourly_stats.items()
                if s["trades"] >= 3 and s["win_rate"] >= 0.5
            ]
            if best_hours:
                conditions.append(
                    {
                        "type": "time_filter",
                        "description": f"勝率50%以上の時間帯: {sorted(best_hours)}時",
                        "expected_improvement": "+5-10% 勝率向上",
                    }
                )

        # 曜日条件
        if self.result.weekday_stats:
            best_days = [
                d
                for d, s in self.result.weekday_stats.items()
                if s["trades"] >= 3 and s["win_rate"] >= 0.5
            ]
            if best_days:
                day_names = [self.WEEKDAY_NAMES[d] for d in best_days]
                conditions.append(
                    {
                        "type": "weekday_filter",
                        "description": f"勝率50%以上の曜日: {', '.join(day_names)}曜日",
                        "expected_improvement": "+3-5% 勝率向上",
                    }
                )

        # 連敗後ルール
        if self.result.max_consecutive_losses >= 5:
            conditions.append(
                {
                    "type": "risk_management",
                    "description": "連敗5回以上検出。連敗3回後はポジションサイズ50%縮小推奨",
                    "expected_improvement": "最大DD 20-30%削減",
                }
            )

        self.result.optimal_conditions = conditions
        return conditions

    def run_full_analysis(self) -> TradeAnalysisResult:
        """全分析実行"""
        print("\n📊 詳細分析を実行中...")

        # 基本統計
        if self.trades:
            pnls = [t.get("pnl", 0) for t in self.trades]
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p < 0]

            self.result.total_trades = len(self.trades)
            self.result.win_rate = len(wins) / len(self.trades) if self.trades else 0
            self.result.total_pnl = sum(pnls)
            gross_profit = sum(wins) if wins else 0
            gross_loss = abs(sum(losses)) if losses else 0
            self.result.profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        # 各分析
        self.analyze_hourly_performance()
        self.analyze_weekday_performance()
        self.analyze_consecutive_patterns()
        self.analyze_pnl_distribution()
        self.find_optimal_conditions()

        return self.result

    def generate_report(self) -> str:
        """分析レポート生成"""
        lines = []

        lines.append("=" * 80)
        lines.append("📊 Phase 60.2 高度トレード分析レポート")
        lines.append(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"分析取引数: {self.result.total_trades}")
        lines.append("=" * 80)

        # 基本統計
        lines.append("\n📈 基本統計")
        lines.append("-" * 40)
        lines.append(f"  総取引数: {self.result.total_trades}")
        lines.append(f"  勝率: {self.result.win_rate:.1%}")
        lines.append(f"  PF: {self.result.profit_factor:.2f}")
        lines.append(f"  総損益: ¥{self.result.total_pnl:,.0f}")

        # 時間帯別
        lines.append("\n⏰ 時間帯別パフォーマンス")
        lines.append("-" * 40)
        if self.result.hourly_stats:
            lines.append(f"  ベスト時間帯: {self.result.best_hours}時")
            lines.append(f"  ワースト時間帯: {self.result.worst_hours}時")
            lines.append("  詳細:")
            for hour in sorted(self.result.hourly_stats.keys()):
                s = self.result.hourly_stats[hour]
                lines.append(
                    f"    {hour:02d}時: 勝率{s['win_rate']:.1%}, PF{s['pf']:.2f}, {s['trades']}取引"
                )

        # 曜日別
        lines.append("\n📅 曜日別パフォーマンス")
        lines.append("-" * 40)
        if self.result.weekday_stats:
            lines.append(f"  ベスト曜日: {', '.join(self.result.best_weekdays)}")
            lines.append(f"  ワースト曜日: {', '.join(self.result.worst_weekdays)}")
            for day in sorted(self.result.weekday_stats.keys()):
                s = self.result.weekday_stats[day]
                lines.append(
                    f"    {self.WEEKDAY_NAMES[day]}曜: 勝率{s['win_rate']:.1%}, PF{s['pf']:.2f}, {s['trades']}取引"
                )

        # 連続結果
        lines.append("\n🔄 連勝/連敗パターン")
        lines.append("-" * 40)
        lines.append(f"  最大連勝: {self.result.max_consecutive_wins}回")
        lines.append(f"  最大連敗: {self.result.max_consecutive_losses}回")
        lines.append(f"  平均連勝: {self.result.avg_win_streak:.1f}回")
        lines.append(f"  平均連敗: {self.result.avg_loss_streak:.1f}回")

        # 損益分布
        lines.append("\n📊 損益分布")
        lines.append("-" * 40)
        if self.result.pnl_distribution:
            d = self.result.pnl_distribution
            lines.append(f"  平均損益: ¥{d['mean']:,.0f}")
            lines.append(f"  中央値: ¥{d['median']:,.0f}")
            lines.append(f"  標準偏差: ¥{d['std']:,.0f}")
            lines.append(f"  最大利益: ¥{d['max']:,.0f}")
            lines.append(f"  最大損失: ¥{d['min']:,.0f}")
            lines.append(f"  勝ち取引: {d['positive_count']}件 / 負け取引: {d['negative_count']}件")

        # 最適条件
        lines.append("\n💡 最適エントリー条件")
        lines.append("-" * 40)
        if self.result.optimal_conditions:
            for cond in self.result.optimal_conditions:
                lines.append(f"  【{cond['type']}】")
                lines.append(f"    {cond['description']}")
                lines.append(f"    期待効果: {cond['expected_improvement']}")
        else:
            lines.append("  特に問題なし")

        lines.append("\n" + "=" * 80)

        return "\n".join(lines)

    def export_results(self, output_path: str):
        """結果をエクスポート"""
        os.makedirs(output_path, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSON出力
        json_file = os.path.join(output_path, f"advanced_analysis_{timestamp}.json")
        json_data = {
            "total_trades": self.result.total_trades,
            "win_rate": self.result.win_rate,
            "profit_factor": self.result.profit_factor,
            "total_pnl": self.result.total_pnl,
            "hourly_stats": self.result.hourly_stats,
            "weekday_stats": self.result.weekday_stats,
            "best_hours": self.result.best_hours,
            "worst_hours": self.result.worst_hours,
            "max_consecutive_wins": self.result.max_consecutive_wins,
            "max_consecutive_losses": self.result.max_consecutive_losses,
            "pnl_distribution": self.result.pnl_distribution,
            "optimal_conditions": self.result.optimal_conditions,
        }

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        print(f"  ✅ JSON: {json_file}")

        # レポート出力
        report_file = os.path.join(output_path, f"advanced_analysis_{timestamp}.txt")
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(self.generate_report())
        print(f"  ✅ レポート: {report_file}")

    def visualize(self, output_path: Optional[str] = None):
        """可視化（matplotlib）"""
        try:
            import matplotlib
            import matplotlib.pyplot as plt

            matplotlib.use("Agg")
        except ImportError:
            print("⚠️ matplotlib未インストール。可視化をスキップ")
            return

        if not self.trades:
            print("⚠️ 取引データなし。可視化をスキップ")
            return

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        # 1. 累積損益曲線
        pnls = [t.get("pnl", 0) for t in self.trades]
        cumulative = np.cumsum(pnls)
        axes[0, 0].plot(cumulative, label="累積損益")
        axes[0, 0].fill_between(range(len(cumulative)), cumulative, alpha=0.3)
        axes[0, 0].axhline(y=0, color="red", linestyle="--", alpha=0.5)
        axes[0, 0].set_title("累積損益曲線")
        axes[0, 0].set_xlabel("取引番号")
        axes[0, 0].set_ylabel("損益 (円)")
        axes[0, 0].legend()

        # 2. 損益ヒストグラム
        axes[0, 1].hist(pnls, bins=30, edgecolor="black", alpha=0.7)
        axes[0, 1].axvline(x=0, color="red", linestyle="--", alpha=0.7)
        axes[0, 1].axvline(
            x=np.mean(pnls), color="green", linestyle="-", label=f"平均: ¥{np.mean(pnls):.0f}"
        )
        axes[0, 1].set_title("損益分布ヒストグラム")
        axes[0, 1].set_xlabel("損益 (円)")
        axes[0, 1].set_ylabel("頻度")
        axes[0, 1].legend()

        # 3. 時間帯別勝率
        if self.result.hourly_stats:
            hours = sorted(self.result.hourly_stats.keys())
            win_rates = [self.result.hourly_stats[h]["win_rate"] * 100 for h in hours]
            colors = ["green" if wr >= 50 else "red" for wr in win_rates]
            axes[1, 0].bar(hours, win_rates, color=colors, alpha=0.7)
            axes[1, 0].axhline(y=50, color="black", linestyle="--", alpha=0.5)
            axes[1, 0].set_title("時間帯別勝率")
            axes[1, 0].set_xlabel("時間 (JST)")
            axes[1, 0].set_ylabel("勝率 (%)")
            axes[1, 0].set_xticks(range(0, 24, 2))

        # 4. 曜日別勝率
        if self.result.weekday_stats:
            days = sorted(self.result.weekday_stats.keys())
            win_rates = [self.result.weekday_stats[d]["win_rate"] * 100 for d in days]
            day_labels = [self.WEEKDAY_NAMES[d] for d in days]
            colors = ["green" if wr >= 50 else "red" for wr in win_rates]
            axes[1, 1].bar(day_labels, win_rates, color=colors, alpha=0.7)
            axes[1, 1].axhline(y=50, color="black", linestyle="--", alpha=0.5)
            axes[1, 1].set_title("曜日別勝率")
            axes[1, 1].set_xlabel("曜日")
            axes[1, 1].set_ylabel("勝率 (%)")

        plt.tight_layout()

        if output_path:
            os.makedirs(output_path, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            fig_path = os.path.join(output_path, f"advanced_analysis_{timestamp}.png")
            plt.savefig(fig_path, dpi=150)
            print(f"  ✅ グラフ: {fig_path}")
        else:
            plt.show()

        plt.close()


async def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(description="高度トレード分析スクリプト - Phase 60.2")
    parser.add_argument("--days", type=int, default=30, help="分析日数（デフォルト: 30日）")
    parser.add_argument("--export", type=str, help="結果出力ディレクトリ")
    parser.add_argument("--visualize", action="store_true", help="可視化を実行")
    parser.add_argument("--verbose", "-v", action="store_true", help="詳細出力")

    args = parser.parse_args()

    print("=" * 80)
    print("🔍 Phase 60.2 高度トレード分析")
    print("   機能: 時間帯別・曜日別分析、連敗パターン、損益分布、最適条件特定")
    print("=" * 80)

    try:
        analyzer = AdvancedTradeAnalyzer(verbose=args.verbose)

        # データ読み込み
        await analyzer.load_data(days=args.days)

        # バックテスト実行
        await analyzer.run_backtest()

        # 全分析実行
        analyzer.run_full_analysis()

        # レポート表示
        print("\n" + analyzer.generate_report())

        # エクスポート
        if args.export:
            print(f"\n💾 結果を {args.export} に出力中...")
            analyzer.export_results(args.export)

            if args.visualize:
                print("📈 グラフを生成中...")
                analyzer.visualize(args.export)
        elif args.visualize:
            analyzer.visualize()

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
