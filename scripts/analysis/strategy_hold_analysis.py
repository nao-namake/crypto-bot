#!/usr/bin/env python3
"""
戦略HOLD原因詳細分析スクリプト - Phase 59.4

各戦略のHOLD発生条件を詳細に分析し、ADX/RSI/Stochasticの値分布を可視化する。

使用方法:
    python scripts/analysis/strategy_hold_analysis.py --days 30
    python scripts/analysis/strategy_hold_analysis.py --days 30 --output ./output
    python scripts/analysis/strategy_hold_analysis.py --export

機能:
    1. ADX値の分布ヒストグラム生成
    2. 各戦略のHOLD条件達成率分析
    3. レジーム別・戦略別のシグナル発火率計算
    4. 閾値調整シミュレーション
"""

import argparse
import asyncio
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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

from src.core.config.threshold_manager import get_threshold
from src.data.data_pipeline import DataPipeline
from src.features.feature_generator import FeatureGenerator
from src.strategies.strategy_loader import StrategyLoader


class StrategyHoldAnalyzer:
    """戦略HOLD原因詳細分析ツール"""

    def __init__(self, verbose: bool = False):
        """
        初期化

        Args:
            verbose: 詳細出力モード
        """
        self.verbose = verbose
        self.strategies = []
        self.df = None
        self.results: Dict[str, Dict[str, Any]] = {}
        self.adx_distribution: Dict[str, int] = defaultdict(int)
        self.regime_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    async def load_data(self, days: int = 30, csv_path: Optional[str] = None) -> pd.DataFrame:
        """
        履歴データを読み込み

        Args:
            days: 分析日数
            csv_path: CSVファイルパス（指定時はファイルから読み込み）

        Returns:
            pd.DataFrame: 特徴量付きデータ
        """
        print(f"📊 {days}日分のデータを取得中...")

        # CSVファイルから読み込み（デフォルト: バックテスト用履歴データ）
        default_csv = str(project_root / "src/backtest/data/historical/BTC_JPY_15m.csv")
        csv_file = csv_path or default_csv

        if os.path.exists(csv_file):
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

            # 特徴量生成
            feature_gen = FeatureGenerator()
            self.df = await feature_gen.generate_features(df_raw)

            print(f"✅ {len(self.df)}データポイントを取得")
            return self.df

        # CSVがない場合はエラー
        raise FileNotFoundError(f"CSVファイルが見つかりません: {csv_file}")

    def load_strategies(self) -> List:
        """
        全戦略をロード

        Returns:
            List: 戦略インスタンスリスト
        """
        print("🔧 6戦略をロード中...")

        loader = StrategyLoader("config/core/strategies.yaml")
        strategy_configs = loader.load_strategies()

        self.strategies = [config["instance"] for config in strategy_configs]

        print(f"✅ {len(self.strategies)}戦略をロード完了")
        for s in self.strategies:
            print(f"   - {s.name}")

        return self.strategies

    def analyze_adx_distribution(self) -> Dict[str, Any]:
        """
        ADX値の分布を分析

        Returns:
            Dict: ADX分布分析結果
        """
        if self.df is None or self.df.empty:
            raise ValueError("データが読み込まれていません")

        print("\n📊 ADX分布を分析中...")

        adx_values = self.df["adx_14"].dropna()
        total = len(adx_values)

        # ADX区間別のカウント
        ranges = [
            ("< 15 (弱いレンジ)", lambda x: x < 15),
            ("15-20 (レンジ)", lambda x: 15 <= x < 20),
            ("20-25 (弱いトレンド)", lambda x: 20 <= x < 25),
            ("25-30 (トレンド)", lambda x: 25 <= x < 30),
            ("30-35 (強いトレンド)", lambda x: 30 <= x < 35),
            ("35-40 (非常に強い)", lambda x: 35 <= x < 40),
            (">= 40 (極端)", lambda x: x >= 40),
        ]

        distribution = {}
        for label, condition in ranges:
            count = sum(1 for x in adx_values if condition(x))
            rate = count / total if total > 0 else 0
            distribution[label] = {"count": count, "rate": rate}
            print(f"   {label}: {count:>5} ({rate:.1%})")

        # 統計情報
        stats = {
            "mean": float(adx_values.mean()),
            "median": float(adx_values.median()),
            "std": float(adx_values.std()),
            "min": float(adx_values.min()),
            "max": float(adx_values.max()),
            "p25": float(adx_values.quantile(0.25)),
            "p75": float(adx_values.quantile(0.75)),
        }

        print(
            f"\n   統計: 平均={stats['mean']:.1f}, 中央値={stats['median']:.1f}, 標準偏差={stats['std']:.1f}"
        )
        print(f"         25%tile={stats['p25']:.1f}, 75%tile={stats['p75']:.1f}")

        return {"distribution": distribution, "stats": stats}

    def analyze_threshold_impact(self) -> Dict[str, Dict[str, float]]:
        """
        閾値変更による影響をシミュレーション

        Returns:
            Dict: 閾値別の発火率予測
        """
        if self.df is None or self.df.empty:
            raise ValueError("データが読み込まれていません")

        print("\n📊 閾値変更シミュレーション...")

        adx_values = self.df["adx_14"].dropna()
        total = len(adx_values)

        # レンジ戦略（ADX < 閾値で発火）
        range_thresholds = [20, 25, 30, 35, 40, 45, 50]
        range_impact = {}
        print("\n   【レンジ戦略】ADX < 閾値で発火")
        for threshold in range_thresholds:
            count = sum(1 for x in adx_values if x < threshold)
            rate = count / total if total > 0 else 0
            range_impact[threshold] = rate
            marker = (
                " ← 現在(Phase 59)"
                if threshold == 40
                else (" ← 旧(Phase 56)" if threshold == 35 else "")
            )
            print(f"   ADX < {threshold}: {rate:.1%}{marker}")

        # トレンド戦略（ADX >= 閾値で発火）
        trend_thresholds = [15, 20, 25, 30, 35]
        trend_impact = {}
        print("\n   【トレンド戦略】ADX >= 閾値で発火")
        for threshold in trend_thresholds:
            count = sum(1 for x in adx_values if x >= threshold)
            rate = count / total if total > 0 else 0
            trend_impact[threshold] = rate
            marker = (
                " ← 現在(Phase 59)"
                if threshold == 20
                else (" ← 旧(Phase 56)" if threshold == 25 else "")
            )
            print(f"   ADX >= {threshold}: {rate:.1%}{marker}")

        return {"range": range_impact, "trend": trend_impact}

    def analyze_stochastic_conditions(self) -> Dict[str, Any]:
        """
        Stochastic条件の達成率を分析

        Returns:
            Dict: Stochastic条件分析結果
        """
        if self.df is None or self.df.empty:
            raise ValueError("データが読み込まれていません")

        print("\n📊 Stochastic条件を分析中...")

        df = self.df.dropna(subset=["stoch_k", "stoch_d", "rsi_14", "adx_14"])
        total = len(df)

        # 現在のPhase 59設定
        adx_range_threshold = 40  # Phase 59
        stoch_overbought = 75
        stoch_oversold = 25
        rsi_overbought = 60
        rsi_oversold = 40

        conditions = {
            "レンジ相場 (ADX < 40)": sum(
                1 for _, r in df.iterrows() if r["adx_14"] < adx_range_threshold
            ),
            "Stoch過買い (K>75, D>75)": sum(
                1
                for _, r in df.iterrows()
                if r["stoch_k"] > stoch_overbought and r["stoch_d"] > stoch_overbought
            ),
            "Stoch過売り (K<25, D<25)": sum(
                1
                for _, r in df.iterrows()
                if r["stoch_k"] < stoch_oversold and r["stoch_d"] < stoch_oversold
            ),
            "レンジ + 過買い": sum(
                1
                for _, r in df.iterrows()
                if r["adx_14"] < adx_range_threshold
                and r["stoch_k"] > stoch_overbought
                and r["stoch_d"] > stoch_overbought
            ),
            "レンジ + 過売り": sum(
                1
                for _, r in df.iterrows()
                if r["adx_14"] < adx_range_threshold
                and r["stoch_k"] < stoch_oversold
                and r["stoch_d"] < stoch_oversold
            ),
            "完全条件SELL (レンジ+過買い+RSI>60)": sum(
                1
                for _, r in df.iterrows()
                if r["adx_14"] < adx_range_threshold
                and r["stoch_k"] > stoch_overbought
                and r["stoch_d"] > stoch_overbought
                and r["rsi_14"] > rsi_overbought
            ),
            "完全条件BUY (レンジ+過売り+RSI<40)": sum(
                1
                for _, r in df.iterrows()
                if r["adx_14"] < adx_range_threshold
                and r["stoch_k"] < stoch_oversold
                and r["stoch_d"] < stoch_oversold
                and r["rsi_14"] < rsi_oversold
            ),
        }

        print(f"\n   データポイント数: {total}")
        for label, count in conditions.items():
            rate = count / total if total > 0 else 0
            print(f"   {label}: {count:>5} ({rate:.1%})")

        return {"conditions": conditions, "total": total}

    def analyze_bb_reversal_conditions(self) -> Dict[str, Any]:
        """
        BB Reversal条件の達成率を分析

        Returns:
            Dict: BB Reversal条件分析結果
        """
        if self.df is None or self.df.empty:
            raise ValueError("データが読み込まれていません")

        print("\n📊 BB Reversal条件を分析中...")

        df = self.df.dropna(subset=["bb_position", "rsi_14", "adx_14"])
        total = len(df)

        # Phase 59設定
        adx_range_threshold = 40
        bb_upper = 0.85
        bb_lower = 0.15
        rsi_overbought = 70
        rsi_oversold = 30

        conditions = {
            "レンジ相場 (ADX < 40)": sum(
                1 for _, r in df.iterrows() if r["adx_14"] < adx_range_threshold
            ),
            "BB上端 (> 0.85)": sum(1 for _, r in df.iterrows() if r["bb_position"] > bb_upper),
            "BB下端 (< 0.15)": sum(1 for _, r in df.iterrows() if r["bb_position"] < bb_lower),
            "RSI過買い (> 70)": sum(1 for _, r in df.iterrows() if r["rsi_14"] > rsi_overbought),
            "RSI過売り (< 30)": sum(1 for _, r in df.iterrows() if r["rsi_14"] < rsi_oversold),
            "完全条件SELL (レンジ+BB上端+RSI>70)": sum(
                1
                for _, r in df.iterrows()
                if r["adx_14"] < adx_range_threshold
                and r["bb_position"] > bb_upper
                and r["rsi_14"] > rsi_overbought
            ),
            "完全条件BUY (レンジ+BB下端+RSI<30)": sum(
                1
                for _, r in df.iterrows()
                if r["adx_14"] < adx_range_threshold
                and r["bb_position"] < bb_lower
                and r["rsi_14"] < rsi_oversold
            ),
        }

        print(f"\n   データポイント数: {total}")
        for label, count in conditions.items():
            rate = count / total if total > 0 else 0
            print(f"   {label}: {count:>5} ({rate:.1%})")

        return {"conditions": conditions, "total": total}

    def analyze_macd_conditions(self) -> Dict[str, Any]:
        """
        MACD EMA Crossover条件の達成率を分析

        Returns:
            Dict: MACD条件分析結果
        """
        if self.df is None or self.df.empty:
            raise ValueError("データが読み込まれていません")

        print("\n📊 MACD EMA Crossover条件を分析中...")

        # 実際の特徴量名: ema_20（短期）, ema_50（長期）
        required_cols = ["macd_histogram", "adx_14", "ema_20", "ema_50", "close"]
        df = self.df.dropna(subset=required_cols)
        total = len(df)

        # Phase 59設定
        adx_trend_threshold = 20  # Phase 59 (旧: 25)

        conditions = {
            "トレンド相場 (ADX >= 20)": sum(
                1 for _, r in df.iterrows() if r["adx_14"] >= adx_trend_threshold
            ),
            "トレンド相場 (ADX >= 25 旧)": sum(1 for _, r in df.iterrows() if r["adx_14"] >= 25),
            "MACD正": sum(1 for _, r in df.iterrows() if r["macd_histogram"] > 0),
            "MACD負": sum(1 for _, r in df.iterrows() if r["macd_histogram"] < 0),
            "EMA上向き (short > long)": sum(
                1 for _, r in df.iterrows() if r["ema_20"] > r["ema_50"]
            ),
            "EMA下向き (short < long)": sum(
                1 for _, r in df.iterrows() if r["ema_20"] < r["ema_50"]
            ),
            "トレンド(20) + MACD正 + EMA上向き": sum(
                1
                for _, r in df.iterrows()
                if r["adx_14"] >= adx_trend_threshold
                and r["macd_histogram"] > 0
                and r["ema_20"] > r["ema_50"]
            ),
            "トレンド(20) + MACD負 + EMA下向き": sum(
                1
                for _, r in df.iterrows()
                if r["adx_14"] >= adx_trend_threshold
                and r["macd_histogram"] < 0
                and r["ema_20"] < r["ema_50"]
            ),
        }

        print(f"\n   データポイント数: {total}")
        for label, count in conditions.items():
            rate = count / total if total > 0 else 0
            print(f"   {label}: {count:>5} ({rate:.1%})")

        return {"conditions": conditions, "total": total}

    def run_strategy_analysis(self) -> Dict[str, Dict[str, Any]]:
        """
        全戦略のシグナル分析を実行

        Returns:
            Dict: 戦略別の分析結果
        """
        if self.df is None or self.df.empty:
            raise ValueError("データが読み込まれていません")

        if not self.strategies:
            raise ValueError("戦略が読み込まれていません")

        print("\n🔍 戦略シグナル分析を実行中...")
        total_rows = len(self.df)

        for strategy in self.strategies:
            print(f"   分析中: {strategy.name}...", end=" ", flush=True)

            signals, reasons = self._run_strategy_simple(strategy)

            # 結果を保存
            counts = self._count_signals(signals)
            hold_reasons = self._categorize_hold_reasons(reasons, signals)

            self.results[strategy.name] = {
                "counts": counts,
                "hold_reasons": hold_reasons,
                "hold_rate": counts.get("hold", 0) / total_rows if total_rows > 0 else 0,
            }

            print(f"完了 (HOLD率: {self.results[strategy.name]['hold_rate']:.1%})")

        return self.results

    def _run_strategy_simple(self, strategy) -> Tuple[List[str], List[str]]:
        """戦略を実行し、シグナル・理由を収集（高速版）"""
        signals, reasons = [], []
        min_rows = 50

        # サンプリング（高速化のため10データごと）
        sample_rate = 10
        indices = list(range(min_rows, len(self.df), sample_rate))

        for i in indices:
            try:
                df_slice = self.df.iloc[: i + 1].copy()
                signal = strategy.analyze(df_slice)

                action = signal.action.lower() if hasattr(signal, "action") else "hold"
                reason = signal.reason if hasattr(signal, "reason") else "理由なし"

                signals.append(action)
                reasons.append(reason or "理由なし")

            except Exception as e:
                signals.append("hold")
                reasons.append(f"エラー: {str(e)[:50]}")

        return signals, reasons

    def _count_signals(self, signals: List[str]) -> Dict[str, int]:
        """シグナルをカウント"""
        counts = defaultdict(int)
        for signal in signals:
            counts[signal.lower()] += 1
        return dict(counts)

    def _categorize_hold_reasons(self, reasons: List[str], signals: List[str]) -> Dict[str, int]:
        """HOLD理由をカテゴリ別に集計"""
        hold_reasons = defaultdict(int)
        for reason, signal in zip(reasons, signals):
            if signal.lower() == "hold":
                hold_reasons[reason] += 1
        return dict(sorted(hold_reasons.items(), key=lambda x: -x[1]))

    def generate_report(self) -> str:
        """詳細レポートを生成"""
        lines = []

        # ヘッダー
        lines.append("=" * 80)
        lines.append("Phase 59.4 戦略HOLD原因詳細分析レポート")
        lines.append(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 80)

        # 戦略別HOLD率サマリー
        if self.results:
            lines.append("\n📊 戦略別HOLD率サマリー")
            lines.append("-" * 80)
            lines.append(
                f"{'戦略名':<25} | {'BUY':>5} | {'SELL':>5} | {'HOLD':>5} | {'HOLD率':>8} | 状態"
            )
            lines.append("-" * 80)

            for name, result in self.results.items():
                counts = result["counts"]
                hold_rate = result["hold_rate"]

                if hold_rate > 0.80:
                    status = "🔴 要改善"
                elif hold_rate > 0.60:
                    status = "🟡 注意"
                else:
                    status = "🟢 正常"

                lines.append(
                    f"{name:<25} | {counts.get('buy', 0):>5} | {counts.get('sell', 0):>5} | "
                    f"{counts.get('hold', 0):>5} | {hold_rate:>7.1%} | {status}"
                )

        # HOLD理由詳細
        if self.results:
            lines.append("\n📋 HOLD理由詳細（上位3件）")
            lines.append("-" * 80)

            for name, result in self.results.items():
                hold_reasons = result.get("hold_reasons", {})
                if hold_reasons:
                    lines.append(f"\n【{name}】")
                    for reason, count in list(hold_reasons.items())[:3]:
                        total = sum(result["counts"].values())
                        rate = count / total if total > 0 else 0
                        lines.append(f"  {count:>4}回 ({rate:>5.1%}): {reason[:65]}")

        lines.append("\n" + "=" * 80)
        lines.append("Phase 59改善ポイント:")
        lines.append("  - StochasticReversal: ADX閾値 35→40 (レンジ判定範囲拡大)")
        lines.append("  - BBReversal: RSI閾値 65/35→70/30, ADX閾値 35→40")
        lines.append("  - MACDEMACrossover: ADX閾値 25→20 (トレンド判定範囲拡大)")
        lines.append("=" * 80)

        return "\n".join(lines)

    def export_results(self, output_path: str):
        """結果をファイル出力"""
        os.makedirs(output_path, exist_ok=True)
        print(f"\n💾 結果を {output_path} に出力中...")

        # レポート出力
        report_path = os.path.join(output_path, "hold_analysis_report.txt")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(self.generate_report())
        print(f"  ✅ {report_path}")


async def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(description="戦略HOLD原因詳細分析スクリプト - Phase 59.4")
    parser.add_argument("--days", type=int, default=30, help="分析日数（デフォルト: 30日）")
    parser.add_argument("--verbose", "-v", action="store_true", help="詳細出力モード")
    parser.add_argument("--output", type=str, help="出力ディレクトリ")
    parser.add_argument("--export", action="store_true", help="結果をファイル出力")

    args = parser.parse_args()

    print("=" * 80)
    print("🔍 Phase 59.4 戦略HOLD原因詳細分析")
    print("=" * 80)

    try:
        analyzer = StrategyHoldAnalyzer(verbose=args.verbose)

        # データ読み込み
        await analyzer.load_data(days=args.days)

        # 戦略ロード
        analyzer.load_strategies()

        # 1. ADX分布分析
        analyzer.analyze_adx_distribution()

        # 2. 閾値変更シミュレーション
        analyzer.analyze_threshold_impact()

        # 3. 個別戦略条件分析
        analyzer.analyze_stochastic_conditions()
        analyzer.analyze_bb_reversal_conditions()
        analyzer.analyze_macd_conditions()

        # 4. 戦略シグナル分析
        analyzer.run_strategy_analysis()

        # レポート出力
        print("\n" + analyzer.generate_report())

        # ファイル出力
        if args.export or args.output:
            output_dir = args.output or "./output/hold_analysis"
            analyzer.export_results(output_dir)

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
