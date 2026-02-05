#!/usr/bin/env python3
"""
標準分析スクリプト - Phase 61

目的:
  バックテスト結果の標準化された分析を実行し、毎回同一の分析項目で
  ブレのない比較を実現。

機能:
  - 85項目の固定指標計算（Phase 61.10: 平均ポジションサイズ追加）
  - JSON/Markdown/CSV出力
  - 履歴CSV追記（変更前後比較用）
  - 改善提案自動生成
  - CI連携: GitHub Actionsの最新バックテスト結果を自動取得

使い方:
  # ローカルJSONファイルを分析
  python3 scripts/backtest/standard_analysis.py <json_path>
  python3 scripts/backtest/standard_analysis.py <json_path> --phase 57.13

  # CIの最新バックテスト結果を取得して分析
  python3 scripts/backtest/standard_analysis.py --from-ci
  python3 scripts/backtest/standard_analysis.py --from-ci --phase 57.13
"""

import argparse
import csv
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@dataclass
class AnalysisResult:
    """分析結果データクラス"""

    # メタ情報
    timestamp: str = ""
    phase: str = ""
    backtest_start: str = ""
    backtest_end: str = ""

    # 基本指標（11項目）
    total_trades: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    expectancy: float = 0.0
    payoff_ratio: float = 0.0
    recovery_factor: float = 0.0
    avg_position_size: float = 0.0  # Phase 61.10: 平均ポジションサイズ（BTC）

    # 戦略別指標（6戦略）
    strategy_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # ML予測別指標
    ml_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # ML×戦略一致率
    agreement_rate: float = 0.0
    agreement_win_rate: float = 0.0
    disagreement_win_rate: float = 0.0
    ml_hold_win_rate: float = 0.0

    # レジーム別指標
    regime_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # 時系列指標
    profitable_days: int = 0
    losing_days: int = 0
    best_day_pnl: float = 0.0
    worst_day_pnl: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0

    # 改善示唆用指標
    worst_strategy: str = ""
    worst_strategy_pnl: float = 0.0
    best_strategy: str = ""
    best_strategy_pnl: float = 0.0
    low_confidence_win_rate: float = 0.0
    high_confidence_win_rate: float = 0.0
    tight_range_contribution: float = 0.0
    normal_range_contribution: float = 0.0

    # Phase 62.18: SLパターン分析指標
    sl_trades: int = 0
    tp_trades: int = 0
    sl_straight_loss_count: int = 0  # 一直線損切り（MFE <= 0）
    sl_small_profit_count: int = 0  # 微益後損切り（0 < MFE < 200）
    sl_profit_then_loss_count: int = 0  # プラス圏経由（200 <= MFE < 500）
    sl_tp_reachable_count: int = 0  # 500円以上経由（MFE >= 500）
    sl_mfe_avg: float = 0.0
    sl_mfe_median: float = 0.0
    sl_mfe_max: float = 0.0
    sl_mae_avg: float = 0.0
    sl_missed_profit_total: float = 0.0  # 逃した利益合計
    sl_missed_profit_avg: float = 0.0  # 平均逃した利益


class StandardAnalyzer:
    """標準分析クラス"""

    # 6戦略の固定リスト
    STRATEGIES = [
        "ATRBased",
        "BBReversal",
        "DonchianChannel",
        "StochasticReversal",
        "ADXTrendStrength",
        "MACDEMACrossover",
    ]

    # ML予測の固定リスト
    ML_PREDICTIONS = ["BUY", "HOLD", "SELL"]

    # レジームの固定リスト
    REGIMES = ["tight_range", "normal_range", "trending", "high_volatility"]

    def __init__(self, json_path: str):
        self.json_path = Path(json_path)
        self.data = self._load_json()
        self.trades = self._extract_all_trades()
        self.result = AnalysisResult()

    def _load_json(self) -> Dict[str, Any]:
        """JSONファイル読み込み"""
        with open(self.json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _extract_all_trades(self) -> List[Dict[str, Any]]:
        """全レジームから取引リスト抽出"""
        trades = []
        regime_perf = self.data.get("regime_performance", {})
        for regime_name, regime_data in regime_perf.items():
            regime_trades = regime_data.get("trades", [])
            for trade in regime_trades:
                trade["regime"] = regime_name
            trades.extend(regime_trades)
        return trades

    def analyze(self, phase: str = "") -> AnalysisResult:
        """分析実行"""
        self.result.timestamp = datetime.now().isoformat()
        self.result.phase = phase

        # メタ情報
        backtest_info = self.data.get("backtest_info", {})
        self.result.backtest_start = backtest_info.get("start_date", "")[:10]
        self.result.backtest_end = backtest_info.get("end_date", "")[:10]

        # 基本指標
        self._calc_basic_metrics()

        # 戦略別指標
        self._calc_strategy_stats()

        # ML予測別指標
        self._calc_ml_stats()

        # ML×戦略一致率
        self._calc_agreement_stats()

        # レジーム別指標
        self._calc_regime_stats()

        # 時系列指標
        self._calc_time_series_stats()

        # 改善示唆用指標
        self._calc_improvement_hints()

        # Phase 62.18: SLパターン分析
        self._calc_sl_pattern_stats()

        return self.result

    def _calc_basic_metrics(self):
        """基本指標計算"""
        perf = self.data.get("performance_metrics", {})

        self.result.total_trades = perf.get("total_trades", 0)
        self.result.win_rate = perf.get("win_rate", 0.0)
        self.result.total_pnl = perf.get("total_pnl", 0.0)
        self.result.profit_factor = perf.get("profit_factor", 0.0)
        self.result.sharpe_ratio = perf.get("sharpe_ratio", 0.0)
        self.result.max_drawdown = perf.get("max_drawdown", 0.0)
        self.result.max_drawdown_pct = perf.get("max_drawdown_pct", 0.0)
        self.result.expectancy = perf.get("expectancy", 0.0)
        self.result.payoff_ratio = perf.get("payoff_ratio", 0.0)
        self.result.recovery_factor = perf.get("recovery_factor", 0.0)

        # max_consecutive_wins/losses
        self.result.max_consecutive_wins = perf.get("max_consecutive_wins", 0)
        self.result.max_consecutive_losses = perf.get("max_consecutive_losses", 0)

        # Phase 61.10: 平均ポジションサイズ計算
        # position_size または amount フィールドを使用
        position_sizes = []
        for t in self.trades:
            size = t.get("position_size") or t.get("amount") or 0
            if size > 0:
                position_sizes.append(size)
        if position_sizes:
            self.result.avg_position_size = sum(position_sizes) / len(position_sizes)
        else:
            self.result.avg_position_size = 0.0

    def _calc_strategy_stats(self):
        """戦略別指標計算"""
        for strategy in self.STRATEGIES:
            strategy_trades = [t for t in self.trades if t.get("strategy") == strategy]
            count = len(strategy_trades)
            wins = sum(1 for t in strategy_trades if t.get("pnl", 0) > 0)
            total_pnl = sum(t.get("pnl", 0) for t in strategy_trades)

            # BUY/SELL比率
            buy_count = sum(1 for t in strategy_trades if t.get("side", "").lower() == "buy")
            sell_count = sum(1 for t in strategy_trades if t.get("side", "").lower() == "sell")

            self.result.strategy_stats[strategy] = {
                "trades": count,
                "win_rate": (wins / count * 100) if count > 0 else 0.0,
                "pnl": total_pnl,
                "avg_pnl": total_pnl / count if count > 0 else 0.0,
                "buy_ratio": (buy_count / count * 100) if count > 0 else 0.0,
                "sell_ratio": (sell_count / count * 100) if count > 0 else 0.0,
            }

    def _calc_ml_stats(self):
        """ML予測別指標計算"""
        ml_map = {0: "SELL", 1: "HOLD", 2: "BUY"}

        for pred_name in self.ML_PREDICTIONS:
            pred_value = {"SELL": 0, "HOLD": 1, "BUY": 2}.get(pred_name)
            ml_trades = [t for t in self.trades if t.get("ml_prediction") == pred_value]
            count = len(ml_trades)
            wins = sum(1 for t in ml_trades if t.get("pnl", 0) > 0)
            total_pnl = sum(t.get("pnl", 0) for t in ml_trades)

            self.result.ml_stats[pred_name] = {
                "trades": count,
                "win_rate": (wins / count * 100) if count > 0 else 0.0,
                "pnl": total_pnl,
                "avg_pnl": total_pnl / count if count > 0 else 0.0,
            }

    def _calc_agreement_stats(self):
        """ML×戦略一致率計算"""
        match_trades = []
        mismatch_trades = []
        ml_hold_trades = []

        for t in self.trades:
            side = t.get("side", "").lower()
            ml_pred = t.get("ml_prediction")

            if ml_pred is None:
                continue

            if ml_pred == 1:  # HOLD
                ml_hold_trades.append(t)
                mismatch_trades.append(t)
                continue

            is_match = (side == "buy" and ml_pred == 2) or (side == "sell" and ml_pred == 0)
            if is_match:
                match_trades.append(t)
            else:
                mismatch_trades.append(t)

        total_with_ml = len(match_trades) + len(mismatch_trades)

        self.result.agreement_rate = (
            (len(match_trades) / total_with_ml * 100) if total_with_ml > 0 else 0.0
        )

        match_wins = sum(1 for t in match_trades if t.get("pnl", 0) > 0)
        mismatch_wins = sum(1 for t in mismatch_trades if t.get("pnl", 0) > 0)
        hold_wins = sum(1 for t in ml_hold_trades if t.get("pnl", 0) > 0)

        self.result.agreement_win_rate = (
            (match_wins / len(match_trades) * 100) if len(match_trades) > 0 else 0.0
        )
        self.result.disagreement_win_rate = (
            (mismatch_wins / len(mismatch_trades) * 100) if len(mismatch_trades) > 0 else 0.0
        )
        self.result.ml_hold_win_rate = (
            (hold_wins / len(ml_hold_trades) * 100) if len(ml_hold_trades) > 0 else 0.0
        )

    def _calc_regime_stats(self):
        """レジーム別指標計算"""
        regime_map = {
            "tight_range": "tight_range",
            "normal_range": "normal_range",
            "trending": "trending",
            "high_volatility": "high_volatility",
        }

        for regime in self.REGIMES:
            regime_trades = [t for t in self.trades if t.get("regime") == regime]
            count = len(regime_trades)
            wins = sum(1 for t in regime_trades if t.get("pnl", 0) > 0)
            total_pnl = sum(t.get("pnl", 0) for t in regime_trades)

            self.result.regime_stats[regime] = {
                "trades": count,
                "win_rate": (wins / count * 100) if count > 0 else 0.0,
                "pnl": total_pnl,
                "avg_pnl": total_pnl / count if count > 0 else 0.0,
            }

    def _calc_time_series_stats(self):
        """時系列指標計算"""
        # 日別損益を計算
        daily_pnl = {}
        for t in self.trades:
            exit_ts = t.get("exit_timestamp", "")
            if exit_ts:
                date = exit_ts[:10]
                daily_pnl[date] = daily_pnl.get(date, 0) + t.get("pnl", 0)

        if daily_pnl:
            self.result.profitable_days = sum(1 for v in daily_pnl.values() if v > 0)
            self.result.losing_days = sum(1 for v in daily_pnl.values() if v < 0)
            self.result.best_day_pnl = max(daily_pnl.values())
            self.result.worst_day_pnl = min(daily_pnl.values())

    def _calc_improvement_hints(self):
        """改善示唆用指標計算"""
        # 最良/最悪戦略
        if self.result.strategy_stats:
            sorted_strategies = sorted(
                self.result.strategy_stats.items(), key=lambda x: x[1]["pnl"]
            )
            if sorted_strategies:
                worst = sorted_strategies[0]
                best = sorted_strategies[-1]
                self.result.worst_strategy = worst[0]
                self.result.worst_strategy_pnl = worst[1]["pnl"]
                self.result.best_strategy = best[0]
                self.result.best_strategy_pnl = best[1]["pnl"]

        # 信頼度帯別勝率
        # Phase 59.3: adjusted_confidenceを優先、フォールバックとしてml_confidence
        def get_confidence(t):
            return t.get("adjusted_confidence") or t.get("ml_confidence") or 0

        low_conf_trades = [t for t in self.trades if get_confidence(t) < 0.5]
        high_conf_trades = [t for t in self.trades if get_confidence(t) >= 0.65]

        low_wins = sum(1 for t in low_conf_trades if t.get("pnl", 0) > 0)
        high_wins = sum(1 for t in high_conf_trades if t.get("pnl", 0) > 0)

        self.result.low_confidence_win_rate = (
            (low_wins / len(low_conf_trades) * 100) if low_conf_trades else 0.0
        )
        self.result.high_confidence_win_rate = (
            (high_wins / len(high_conf_trades) * 100) if high_conf_trades else 0.0
        )

        # レジーム寄与度
        total_pnl = self.result.total_pnl
        if total_pnl != 0:
            tight_pnl = self.result.regime_stats.get("tight_range", {}).get("pnl", 0)
            normal_pnl = self.result.regime_stats.get("normal_range", {}).get("pnl", 0)
            self.result.tight_range_contribution = tight_pnl / abs(total_pnl) * 100
            self.result.normal_range_contribution = normal_pnl / abs(total_pnl) * 100

    def _calc_sl_pattern_stats(self):
        """Phase 62.18: SLパターン分析"""
        # SL/TP分類
        sl_trades = [t for t in self.trades if t.get("pnl", 0) < 0]
        tp_trades = [t for t in self.trades if t.get("pnl", 0) >= 0]

        self.result.sl_trades = len(sl_trades)
        self.result.tp_trades = len(tp_trades)

        if not sl_trades:
            return

        # TP目標額（thresholds.yamlから取得、フォールバック500円）
        tp_target = 500.0

        # パターン分類
        straight_loss = []  # MFE <= 0
        small_profit = []  # 0 < MFE < 200
        profit_then_loss = []  # 200 <= MFE < tp_target
        tp_reachable = []  # MFE >= tp_target

        for trade in sl_trades:
            mfe = trade.get("mfe", 0) or 0
            if mfe <= 0:
                straight_loss.append(trade)
            elif mfe < 200:
                small_profit.append(trade)
            elif mfe < tp_target:
                profit_then_loss.append(trade)
            else:
                tp_reachable.append(trade)

        self.result.sl_straight_loss_count = len(straight_loss)
        self.result.sl_small_profit_count = len(small_profit)
        self.result.sl_profit_then_loss_count = len(profit_then_loss)
        self.result.sl_tp_reachable_count = len(tp_reachable)

        # MFE統計（SL決済のみ）
        mfe_values = [t.get("mfe", 0) or 0 for t in sl_trades]
        if mfe_values:
            self.result.sl_mfe_avg = sum(mfe_values) / len(mfe_values)
            sorted_mfe = sorted(mfe_values)
            self.result.sl_mfe_median = sorted_mfe[len(sorted_mfe) // 2]
            self.result.sl_mfe_max = max(mfe_values)

        # MAE統計（SL決済のみ）
        mae_values = [t.get("mae", 0) or 0 for t in sl_trades]
        if mae_values:
            self.result.sl_mae_avg = sum(mae_values) / len(mae_values)

        # 逃した利益分析（TP到達可能だった取引）
        if tp_reachable:
            # 逃した利益 = MFE - 実際のPnL
            missed_profits = [(t.get("mfe", 0) or 0) - (t.get("pnl", 0) or 0) for t in tp_reachable]
            self.result.sl_missed_profit_total = sum(missed_profits)
            self.result.sl_missed_profit_avg = self.result.sl_missed_profit_total / len(
                tp_reachable
            )


class ReportGenerator:
    """レポート生成クラス"""

    def __init__(self, result: AnalysisResult):
        self.result = result
        self.output_dir = Path("docs/検証記録")
        self.output_dir.mkdir(exist_ok=True)

    def print_console(self):
        """コンソール出力"""
        r = self.result
        print("\n" + "=" * 60)
        print("📊 Phase 61 標準分析レポート")
        print("=" * 60)
        print(f"分析日時: {r.timestamp}")
        print(f"Phase: {r.phase}")
        print(f"バックテスト期間: {r.backtest_start} ~ {r.backtest_end}")
        print("-" * 60)

        print("\n【基本指標】")
        print(f"  総取引数: {r.total_trades}件")
        print(f"  勝率: {r.win_rate:.1f}%")
        print(f"  総損益: ¥{r.total_pnl:+,.0f}")
        print(f"  PF: {r.profit_factor:.2f}")
        print(f"  SR: {r.sharpe_ratio:.2f}")
        print(f"  最大DD: ¥{r.max_drawdown:,.0f} ({r.max_drawdown_pct:.2f}%)")
        print(f"  期待値: ¥{r.expectancy:+,.0f}")
        # Phase 61.10: 平均ポジションサイズ（異常検知付き）
        pos_size_warning = " ⚠️ 異常に小さい" if r.avg_position_size < 0.001 else ""
        print(f"  平均ポジションサイズ: {r.avg_position_size:.6f} BTC{pos_size_warning}")

        print("\n【戦略別パフォーマンス】")
        for strategy, stats in r.strategy_stats.items():
            if stats["trades"] > 0:
                print(
                    f"  {strategy}: {stats['trades']}件, "
                    f"勝率{stats['win_rate']:.1f}%, "
                    f"¥{stats['pnl']:+,.0f}"
                )

        print("\n【ML予測別パフォーマンス】")
        for pred, stats in r.ml_stats.items():
            if stats["trades"] > 0:
                print(
                    f"  {pred}: {stats['trades']}件, "
                    f"勝率{stats['win_rate']:.1f}%, "
                    f"¥{stats['pnl']:+,.0f}"
                )

        print("\n【ML×戦略一致率】")
        print(f"  一致率: {r.agreement_rate:.1f}%")
        print(f"  一致時勝率: {r.agreement_win_rate:.1f}%")
        print(f"  不一致時勝率: {r.disagreement_win_rate:.1f}%")
        print(f"  ML HOLD時勝率: {r.ml_hold_win_rate:.1f}%")

        print("\n【レジーム別パフォーマンス】")
        for regime, stats in r.regime_stats.items():
            if stats["trades"] > 0:
                print(
                    f"  {regime}: {stats['trades']}件, "
                    f"勝率{stats['win_rate']:.1f}%, "
                    f"¥{stats['pnl']:+,.0f}"
                )

        print("\n【時系列指標】")
        print(f"  利益日数: {r.profitable_days}日")
        print(f"  損失日数: {r.losing_days}日")
        print(f"  最良日: ¥{r.best_day_pnl:+,.0f}")
        print(f"  最悪日: ¥{r.worst_day_pnl:+,.0f}")
        print(f"  最大連勝: {r.max_consecutive_wins}回")
        print(f"  最大連敗: {r.max_consecutive_losses}回")

        # Phase 62.18: SLパターン分析
        self._print_sl_pattern_analysis()

        # 改善提案
        print("\n" + "=" * 60)
        print("💡 改善提案（自動生成）")
        print("=" * 60)
        self._print_improvement_suggestions()
        print("=" * 60 + "\n")

    def _print_improvement_suggestions(self):
        """改善提案出力"""
        r = self.result
        suggestions = []

        # 戦略の問題点
        if r.worst_strategy_pnl < 0:
            suggestions.append(
                f"1. 戦略の問題点: {r.worst_strategy}が¥{r.worst_strategy_pnl:,.0f}の損失"
                f" → 無効化または重み削減を検討"
            )

        # ML予測の活用
        if r.ml_hold_win_rate > r.win_rate:
            suggestions.append(
                f"2. ML HOLD時の勝率{r.ml_hold_win_rate:.1f}%は全体{r.win_rate:.1f}%より高い"
                f" → HOLDフィルターは不要"
            )

        # 信頼度帯
        if r.high_confidence_win_rate < r.low_confidence_win_rate:
            suggestions.append(
                f"3. 高信頼度帯の勝率{r.high_confidence_win_rate:.1f}%が低信頼度帯"
                f"{r.low_confidence_win_rate:.1f}%より低い → 信頼度フィルター見直し"
            )

        # レジーム寄与度
        if r.tight_range_contribution > 100:
            suggestions.append(
                f"4. tight_rangeの寄与度が{r.tight_range_contribution:.0f}%" f" → 損失をカバー"
            )

        # Phase 61.10: ポジションサイズ異常検知
        if r.avg_position_size > 0 and r.avg_position_size < 0.001:
            suggestions.append(
                f"5. ⚠️ 平均ポジションサイズが異常に小さい: {r.avg_position_size:.6f} BTC"
                f" → Dynamic Position Sizing設定を確認"
            )

        if not suggestions:
            suggestions.append("特に重大な問題は検出されませんでした。")

        for s in suggestions:
            print(f"  {s}")

    def _print_sl_pattern_analysis(self):
        """Phase 62.18: SLパターン分析出力"""
        r = self.result

        if r.sl_trades == 0:
            return

        print("\n" + "-" * 60)
        print("📉 SL決済パターン分析")
        print("-" * 60)

        # 全体サマリー
        total = r.sl_trades + r.tp_trades
        sl_rate = (r.sl_trades / total * 100) if total > 0 else 0
        tp_rate = (r.tp_trades / total * 100) if total > 0 else 0
        print(f"  SL決済: {r.sl_trades}件 ({sl_rate:.1f}%)")
        print(f"  TP決済: {r.tp_trades}件 ({tp_rate:.1f}%)")

        # パターン分類
        print("\n  【パターン分類】")
        patterns = [
            ("一直線損切り", r.sl_straight_loss_count, "MFE <= 0"),
            ("微益後損切り", r.sl_small_profit_count, "0 < MFE < 200"),
            ("プラス圏経由", r.sl_profit_then_loss_count, "200 <= MFE < 500"),
            ("500円以上経由", r.sl_tp_reachable_count, "MFE >= 500"),
        ]
        for name, count, desc in patterns:
            rate = (count / r.sl_trades * 100) if r.sl_trades > 0 else 0
            warning = " ⚠️" if name == "500円以上経由" and count > 0 else ""
            print(f"    {name}: {count:>3}件 ({rate:>5.1f}%) - {desc}{warning}")

        # MFE/MAE統計
        print("\n  【MFE/MAE統計（SL決済のみ）】")
        print(f"    平均MFE: ¥{r.sl_mfe_avg:,.0f}")
        print(f"    中央値MFE: ¥{r.sl_mfe_median:,.0f}")
        print(f"    最大MFE: ¥{r.sl_mfe_max:,.0f}")
        print(f"    平均MAE: ¥{r.sl_mae_avg:,.0f}")

        # 逃した利益
        if r.sl_tp_reachable_count > 0:
            print("\n  【逃した利益分析】")
            print(f"    500円以上MFEでSL決済: {r.sl_tp_reachable_count}件")
            print(f"    逃した利益合計: ¥{r.sl_missed_profit_total:,.0f}")
            print(f"    平均逃した利益: ¥{r.sl_missed_profit_avg:,.0f}/件")

        # SL分析からの改善示唆
        print("\n  【SL分析からの示唆】")
        sl_suggestions = []

        straight_rate = (r.sl_straight_loss_count / r.sl_trades * 100) if r.sl_trades > 0 else 0
        if straight_rate > 15:
            sl_suggestions.append(
                f"    - 一直線損切り率{straight_rate:.1f}%が高い → エントリー改善余地"
            )

        tp_reachable_rate = (r.sl_tp_reachable_count / r.sl_trades * 100) if r.sl_trades > 0 else 0
        if tp_reachable_rate > 10:
            sl_suggestions.append(
                f"    - 500円以上経由率{tp_reachable_rate:.1f}%が高い → トレーリングストップ検討"
            )

        if r.sl_missed_profit_total > 50000:
            sl_suggestions.append(
                f"    - 逃した利益¥{r.sl_missed_profit_total:,.0f} → 部分利確が効果的"
            )

        profit_via_rate = (
            (r.sl_profit_then_loss_count + r.sl_tp_reachable_count) / r.sl_trades * 100
            if r.sl_trades > 0
            else 0
        )
        if profit_via_rate > 50:
            sl_suggestions.append(
                f"    - プラス圏経由{profit_via_rate:.1f}% → 利確ロジック改善が効果的"
            )

        if not sl_suggestions:
            sl_suggestions.append("    - 特に重大な問題なし")

        for s in sl_suggestions:
            print(s)

    def save_json(self, filename: str = None) -> str:
        """JSON出力"""
        if filename is None:
            filename = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        filepath = self.output_dir / filename
        data = self._to_dict()

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"📁 JSON保存: {filepath}")
        return str(filepath)

    def save_markdown(self, filename: str = None) -> str:
        """Markdown出力"""
        if filename is None:
            filename = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        filepath = self.output_dir / filename
        r = self.result

        lines = [
            f"# Phase 61 標準分析レポート",
            f"",
            f"**分析日時**: {r.timestamp}",
            f"**Phase**: {r.phase}",
            f"**バックテスト期間**: {r.backtest_start} ~ {r.backtest_end}",
            f"",
            f"---",
            f"",
            f"## 基本指標",
            f"",
            f"| 指標 | 値 |",
            f"|------|-----|",
            f"| 総取引数 | {r.total_trades}件 |",
            f"| 勝率 | {r.win_rate:.1f}% |",
            f"| 総損益 | ¥{r.total_pnl:+,.0f} |",
            f"| PF | {r.profit_factor:.2f} |",
            f"| SR | {r.sharpe_ratio:.2f} |",
            f"| 最大DD | ¥{r.max_drawdown:,.0f} ({r.max_drawdown_pct:.2f}%) |",
            f"| 期待値 | ¥{r.expectancy:+,.0f} |",
            f"| ペイオフレシオ | {r.payoff_ratio:.2f} |",
            f"| リカバリーファクター | {r.recovery_factor:.2f} |",
            f"| 平均ポジションサイズ | {r.avg_position_size:.6f} BTC |",
            f"",
            f"---",
            f"",
            f"## 戦略別パフォーマンス",
            f"",
            f"| 戦略 | 取引数 | 勝率 | 総損益 | BUY率 | SELL率 |",
            f"|------|--------|------|--------|-------|--------|",
        ]

        for strategy, stats in r.strategy_stats.items():
            lines.append(
                f"| {strategy} | {stats['trades']}件 | {stats['win_rate']:.1f}% | "
                f"¥{stats['pnl']:+,.0f} | {stats['buy_ratio']:.0f}% | {stats['sell_ratio']:.0f}% |"
            )

        lines.extend(
            [
                f"",
                f"---",
                f"",
                f"## ML予測別パフォーマンス",
                f"",
                f"| ML予測 | 取引数 | 勝率 | 総損益 |",
                f"|--------|--------|------|--------|",
            ]
        )

        for pred, stats in r.ml_stats.items():
            lines.append(
                f"| {pred} | {stats['trades']}件 | {stats['win_rate']:.1f}% | "
                f"¥{stats['pnl']:+,.0f} |"
            )

        lines.extend(
            [
                f"",
                f"---",
                f"",
                f"## ML×戦略一致率",
                f"",
                f"| 指標 | 値 |",
                f"|------|-----|",
                f"| 一致率 | {r.agreement_rate:.1f}% |",
                f"| 一致時勝率 | {r.agreement_win_rate:.1f}% |",
                f"| 不一致時勝率 | {r.disagreement_win_rate:.1f}% |",
                f"| ML HOLD時勝率 | {r.ml_hold_win_rate:.1f}% |",
                f"",
                f"---",
                f"",
                f"## レジーム別パフォーマンス",
                f"",
                f"| レジーム | 取引数 | 勝率 | 総損益 |",
                f"|----------|--------|------|--------|",
            ]
        )

        for regime, stats in r.regime_stats.items():
            lines.append(
                f"| {regime} | {stats['trades']}件 | {stats['win_rate']:.1f}% | "
                f"¥{stats['pnl']:+,.0f} |"
            )

        lines.extend(
            [
                f"",
                f"---",
                f"",
                f"## 時系列指標",
                f"",
                f"| 指標 | 値 |",
                f"|------|-----|",
                f"| 利益日数 | {r.profitable_days}日 |",
                f"| 損失日数 | {r.losing_days}日 |",
                f"| 最良日 | ¥{r.best_day_pnl:+,.0f} |",
                f"| 最悪日 | ¥{r.worst_day_pnl:+,.0f} |",
                f"| 最大連勝 | {r.max_consecutive_wins}回 |",
                f"| 最大連敗 | {r.max_consecutive_losses}回 |",
                f"",
            ]
        )

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        print(f"📁 Markdown保存: {filepath}")
        return str(filepath)

    def append_csv(self, filename: str = "analysis_history.csv") -> str:
        """履歴CSV追記"""
        filepath = self.output_dir / filename
        r = self.result

        # CSVヘッダー
        headers = [
            "timestamp",
            "phase",
            "backtest_start",
            "backtest_end",
            "total_trades",
            "win_rate",
            "total_pnl",
            "profit_factor",
            "sharpe_ratio",
            "max_drawdown",
            "max_drawdown_pct",
            "expectancy",
            "payoff_ratio",
            "recovery_factor",
            "avg_position_size",
            "best_strategy",
            "best_strategy_pnl",
            "worst_strategy",
            "worst_strategy_pnl",
            "agreement_rate",
            "agreement_win_rate",
            "disagreement_win_rate",
            "ml_hold_win_rate",
            "profitable_days",
            "losing_days",
            "max_consecutive_wins",
            "max_consecutive_losses",
        ]

        # 戦略別カラム追加
        for strategy in StandardAnalyzer.STRATEGIES:
            headers.extend(
                [
                    f"{strategy}_trades",
                    f"{strategy}_win_rate",
                    f"{strategy}_pnl",
                ]
            )

        # ML予測別カラム追加
        for pred in StandardAnalyzer.ML_PREDICTIONS:
            headers.extend(
                [
                    f"ml_{pred}_trades",
                    f"ml_{pred}_win_rate",
                    f"ml_{pred}_pnl",
                ]
            )

        # データ行
        row = [
            r.timestamp,
            r.phase,
            r.backtest_start,
            r.backtest_end,
            r.total_trades,
            f"{r.win_rate:.1f}",
            f"{r.total_pnl:.0f}",
            f"{r.profit_factor:.2f}",
            f"{r.sharpe_ratio:.2f}",
            f"{r.max_drawdown:.0f}",
            f"{r.max_drawdown_pct:.2f}",
            f"{r.expectancy:.0f}",
            f"{r.payoff_ratio:.2f}",
            f"{r.recovery_factor:.2f}",
            f"{r.avg_position_size:.6f}",
            r.best_strategy,
            f"{r.best_strategy_pnl:.0f}",
            r.worst_strategy,
            f"{r.worst_strategy_pnl:.0f}",
            f"{r.agreement_rate:.1f}",
            f"{r.agreement_win_rate:.1f}",
            f"{r.disagreement_win_rate:.1f}",
            f"{r.ml_hold_win_rate:.1f}",
            r.profitable_days,
            r.losing_days,
            r.max_consecutive_wins,
            r.max_consecutive_losses,
        ]

        # 戦略別データ追加
        for strategy in StandardAnalyzer.STRATEGIES:
            stats = r.strategy_stats.get(strategy, {})
            row.extend(
                [
                    stats.get("trades", 0),
                    f"{stats.get('win_rate', 0):.1f}",
                    f"{stats.get('pnl', 0):.0f}",
                ]
            )

        # ML予測別データ追加
        for pred in StandardAnalyzer.ML_PREDICTIONS:
            stats = r.ml_stats.get(pred, {})
            row.extend(
                [
                    stats.get("trades", 0),
                    f"{stats.get('win_rate', 0):.1f}",
                    f"{stats.get('pnl', 0):.0f}",
                ]
            )

        # ファイル存在確認
        file_exists = filepath.exists()

        with open(filepath, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(headers)
            writer.writerow(row)

        print(f"📁 履歴CSV追記: {filepath}")
        return str(filepath)

    def _to_dict(self) -> Dict[str, Any]:
        """辞書変換"""
        r = self.result
        return {
            "timestamp": r.timestamp,
            "phase": r.phase,
            "backtest_period": {
                "start": r.backtest_start,
                "end": r.backtest_end,
            },
            "basic_metrics": {
                "total_trades": r.total_trades,
                "win_rate": r.win_rate,
                "total_pnl": r.total_pnl,
                "profit_factor": r.profit_factor,
                "sharpe_ratio": r.sharpe_ratio,
                "max_drawdown": r.max_drawdown,
                "max_drawdown_pct": r.max_drawdown_pct,
                "expectancy": r.expectancy,
                "payoff_ratio": r.payoff_ratio,
                "recovery_factor": r.recovery_factor,
                "avg_position_size": r.avg_position_size,
            },
            "strategy_stats": r.strategy_stats,
            "ml_stats": r.ml_stats,
            "agreement_stats": {
                "agreement_rate": r.agreement_rate,
                "agreement_win_rate": r.agreement_win_rate,
                "disagreement_win_rate": r.disagreement_win_rate,
                "ml_hold_win_rate": r.ml_hold_win_rate,
            },
            "regime_stats": r.regime_stats,
            "time_series_stats": {
                "profitable_days": r.profitable_days,
                "losing_days": r.losing_days,
                "best_day_pnl": r.best_day_pnl,
                "worst_day_pnl": r.worst_day_pnl,
                "max_consecutive_wins": r.max_consecutive_wins,
                "max_consecutive_losses": r.max_consecutive_losses,
            },
            "improvement_hints": {
                "worst_strategy": r.worst_strategy,
                "worst_strategy_pnl": r.worst_strategy_pnl,
                "best_strategy": r.best_strategy,
                "best_strategy_pnl": r.best_strategy_pnl,
                "low_confidence_win_rate": r.low_confidence_win_rate,
                "high_confidence_win_rate": r.high_confidence_win_rate,
                "tight_range_contribution": r.tight_range_contribution,
                "normal_range_contribution": r.normal_range_contribution,
            },
            # Phase 62.18: SLパターン分析
            "sl_pattern_analysis": {
                "sl_trades": r.sl_trades,
                "tp_trades": r.tp_trades,
                "patterns": {
                    "straight_loss": r.sl_straight_loss_count,
                    "small_profit": r.sl_small_profit_count,
                    "profit_then_loss": r.sl_profit_then_loss_count,
                    "tp_reachable": r.sl_tp_reachable_count,
                },
                "mfe_stats": {
                    "avg": r.sl_mfe_avg,
                    "median": r.sl_mfe_median,
                    "max": r.sl_mfe_max,
                },
                "mae_avg": r.sl_mae_avg,
                "missed_profit": {
                    "total": r.sl_missed_profit_total,
                    "avg": r.sl_missed_profit_avg,
                },
            },
        }


class CIIntegration:
    """GitHub Actions CI連携クラス"""

    WORKFLOW_NAME = "backtest.yml"
    ARTIFACT_NAME = "backtest-results"
    DOWNLOAD_DIR = Path("docs/検証記録/ci_downloads")

    @classmethod
    def fetch_latest_backtest(cls) -> Tuple[Optional[str], Optional[str]]:
        """
        最新のCIバックテスト結果を取得

        Returns:
            (json_path, run_info): JSONファイルパスと実行情報のタプル
            失敗時は (None, error_message)
        """
        print("🔍 CI最新バックテスト結果を検索中...")

        # gh CLI確認
        if not cls._check_gh_cli():
            return None, "gh CLI がインストールされていません"

        # 最新の成功したバックテスト実行を取得
        run_id, run_info = cls._get_latest_successful_run()
        if not run_id:
            return None, run_info  # run_infoにはエラーメッセージが入る

        print(f"✅ 最新実行を検出: Run ID {run_id}")
        print(f"   {run_info}")

        # artifactダウンロード
        json_path = cls._download_artifact(run_id)
        if not json_path:
            return None, "artifactのダウンロードに失敗しました"

        return json_path, run_info

    @classmethod
    def _check_gh_cli(cls) -> bool:
        """gh CLI インストール確認"""
        try:
            result = subprocess.run(
                ["gh", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    @classmethod
    def _get_latest_successful_run(cls) -> Tuple[Optional[str], str]:
        """最新の成功したバックテスト実行を取得"""
        try:
            result = subprocess.run(
                [
                    "gh",
                    "run",
                    "list",
                    "--workflow",
                    cls.WORKFLOW_NAME,
                    "--status",
                    "success",
                    "--limit",
                    "1",
                    "--json",
                    "databaseId,createdAt,displayTitle",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return None, f"gh run list 失敗: {result.stderr}"

            runs = json.loads(result.stdout)
            if not runs:
                return None, "成功したバックテスト実行が見つかりません"

            run = runs[0]
            run_id = str(run["databaseId"])
            created_at = run["createdAt"]
            title = run.get("displayTitle", "Backtest")

            return run_id, f"実行日時: {created_at}, タイトル: {title}"

        except subprocess.TimeoutExpired:
            return None, "gh run list タイムアウト"
        except json.JSONDecodeError:
            return None, "gh run list の出力パースに失敗"
        except Exception as e:
            return None, f"予期せぬエラー: {e}"

    @classmethod
    def _download_artifact(cls, run_id: str) -> Optional[str]:
        """artifactをダウンロードしてJSONパスを返す"""
        # ダウンロードディレクトリ準備
        cls.DOWNLOAD_DIR.mkdir(exist_ok=True)

        # 既存のファイルをクリア
        for f in cls.DOWNLOAD_DIR.glob("*"):
            if f.is_file():
                f.unlink()
            elif f.is_dir():
                shutil.rmtree(f)

        print(f"📥 artifact ダウンロード中 (Run ID: {run_id})...")

        try:
            result = subprocess.run(
                [
                    "gh",
                    "run",
                    "download",
                    run_id,
                    "--name",
                    cls.ARTIFACT_NAME,
                    "--dir",
                    str(cls.DOWNLOAD_DIR),
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                print(f"❌ ダウンロード失敗: {result.stderr}")
                return None

            # JSONファイルを探す
            json_files = list(cls.DOWNLOAD_DIR.glob("**/*.json"))
            if not json_files:
                print("❌ JSONファイルが見つかりません")
                return None

            # 最新のJSONファイルを選択
            json_path = max(json_files, key=lambda p: p.stat().st_mtime)
            print(f"✅ JSONファイル取得: {json_path}")

            return str(json_path)

        except subprocess.TimeoutExpired:
            print("❌ ダウンロードタイムアウト")
            return None
        except Exception as e:
            print(f"❌ ダウンロードエラー: {e}")
            return None


def main():
    parser = argparse.ArgumentParser(description="Phase 61 標準分析スクリプト")
    parser.add_argument(
        "json_path", nargs="?", help="バックテストJSONファイルパス（--from-ci/--local時は不要）"
    )
    parser.add_argument("--phase", default="", help="Phaseバージョン（例: 57.13）")
    parser.add_argument(
        "--from-ci",
        action="store_true",
        help="CIの最新バックテスト結果を自動取得して分析",
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="最新のローカルバックテスト結果を自動検出して分析",
    )
    parser.add_argument("--no-console", action="store_true", help="コンソール出力を抑制")
    parser.add_argument("--no-json", action="store_true", help="JSON出力を抑制")
    parser.add_argument("--no-markdown", action="store_true", help="Markdown出力を抑制")
    parser.add_argument("--no-csv", action="store_true", help="履歴CSV出力を抑制")

    args = parser.parse_args()

    # JSONパス決定
    json_path = args.json_path

    if args.from_ci:
        # CI連携モード
        json_path, run_info = CIIntegration.fetch_latest_backtest()
        if not json_path:
            print(f"❌ CIからの取得に失敗: {run_info}")
            sys.exit(1)
        print(f"📊 CI実行情報: {run_info}")
        print()
    elif args.local:
        # ローカルモード
        local_dir = Path("docs/検証記録")
        local_files = sorted(
            local_dir.glob("local_backtest_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not local_files:
            print("❌ ローカル結果が見つかりません")
            print(f"   検索パス: {local_dir}/local_backtest_*.json")
            sys.exit(1)
        json_path = str(local_files[0])
        print(f"📁 最新ローカル結果: {json_path}")
        print()
    elif not json_path:
        print("❌ json_path, --from-ci, または --local オプションが必要です")
        parser.print_help()
        sys.exit(1)

    # 分析実行
    analyzer = StandardAnalyzer(json_path)
    result = analyzer.analyze(phase=args.phase)

    # レポート生成
    reporter = ReportGenerator(result)

    if not args.no_console:
        reporter.print_console()

    if not args.no_json:
        reporter.save_json()

    if not args.no_markdown:
        reporter.save_markdown()

    if not args.no_csv:
        reporter.append_csv()

    print("\n✅ Phase 61 標準分析完了")


if __name__ == "__main__":
    main()
