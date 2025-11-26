#!/usr/bin/env python3
"""
戦略シグナル分析スクリプト - Phase 55.7

各戦略のBUY/SELL/HOLD出現状況を分析し、問題のある戦略を特定する。

使用方法:
    python scripts/analysis/strategy_signal_analyzer.py --days 7
    python scripts/analysis/strategy_signal_analyzer.py --days 30 --verbose
    python scripts/analysis/strategy_signal_analyzer.py --export ./output

機能:
    1. 6戦略のシグナル分布集計
    2. HOLD理由の詳細分析
    3. 時系列での多数決推移
    4. CSV/TXT形式での出力
"""

import argparse
import asyncio
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta
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

from src.data.data_pipeline import DataPipeline
from src.features.feature_generator import FeatureGenerator
from src.strategies.strategy_loader import StrategyLoader


class StrategySignalAnalyzer:
    """戦略シグナル分析ツール（詳細版）"""

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

    async def load_data(self, days: int = 7, csv_path: Optional[str] = None) -> pd.DataFrame:
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

        # CSVがない場合はAPI経由で取得
        print("   ⚠️ CSVが見つかりません。APIから取得を試行...")
        pipeline = DataPipeline()
        market_data = await pipeline.fetch_multi_timeframe(symbol="BTC/JPY", limit=days * 6)

        # 15分足データを使用
        df_15m = market_data.get("15m")
        if df_15m is None or df_15m.empty:
            raise ValueError("15分足データの取得に失敗しました")

        # 特徴量生成
        feature_gen = FeatureGenerator()
        self.df = await feature_gen.generate_features(df_15m)

        print(f"✅ {len(self.df)}データポイントを取得")
        return self.df

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

    def run_analysis(self) -> Dict[str, Dict[str, Any]]:
        """
        全戦略のシグナル分析を実行

        Returns:
            Dict: 戦略別の分析結果
        """
        if self.df is None or self.df.empty:
            raise ValueError("データが読み込まれていません")

        if not self.strategies:
            raise ValueError("戦略が読み込まれていません")

        print("\n🔍 シグナル分析を実行中...")
        total_rows = len(self.df)

        for strategy in self.strategies:
            print(f"   分析中: {strategy.name}...", end=" ", flush=True)

            signals, reasons, confidences = self._run_strategy_with_details(strategy)

            # 結果を保存
            self.results[strategy.name] = {
                "signals": signals,
                "reasons": reasons,
                "confidences": confidences,
                "counts": self._count_signals(signals),
                "hold_reasons": self._categorize_hold_reasons(reasons, signals),
                "avg_confidence": {
                    "buy": self._avg_confidence_by_action(confidences, signals, "buy"),
                    "sell": self._avg_confidence_by_action(confidences, signals, "sell"),
                    "hold": self._avg_confidence_by_action(confidences, signals, "hold"),
                },
            }

            counts = self.results[strategy.name]["counts"]
            hold_rate = counts.get("hold", 0) / total_rows if total_rows > 0 else 0
            print(f"完了 (hold率: {hold_rate:.1%})")

        return self.results

    def _run_strategy_with_details(self, strategy) -> Tuple[List[str], List[str], List[float]]:
        """
        戦略を実行し、シグナル・理由・信頼度を収集

        Args:
            strategy: 戦略インスタンス

        Returns:
            Tuple: (シグナルリスト, 理由リスト, 信頼度リスト)
        """
        signals, reasons, confidences = [], [], []
        min_rows = 50  # 最低必要な行数

        for i in range(len(self.df)):
            if i < min_rows:
                # 初期データが不足している場合はHOLD
                signals.append("hold")
                reasons.append("データ不足")
                confidences.append(0.0)
                continue

            try:
                df_slice = self.df.iloc[: i + 1].copy()
                signal = strategy.analyze(df_slice)

                action = signal.action.lower() if hasattr(signal, "action") else "hold"
                reason = signal.reason if hasattr(signal, "reason") else "理由なし"
                confidence = signal.confidence if hasattr(signal, "confidence") else 0.0

                signals.append(action)
                reasons.append(reason or "理由なし")
                confidences.append(float(confidence))

            except Exception as e:
                signals.append("hold")
                reasons.append(f"エラー: {str(e)[:50]}")
                confidences.append(0.0)

        return signals, reasons, confidences

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

    def _avg_confidence_by_action(
        self, confidences: List[float], signals: List[str], action: str
    ) -> float:
        """アクション別の平均信頼度を計算"""
        values = [c for c, s in zip(confidences, signals) if s.lower() == action]
        return sum(values) / len(values) if values else 0.0

    def get_vote_timeline(self) -> pd.DataFrame:
        """
        時系列での多数決推移を取得

        Returns:
            pd.DataFrame: 多数決タイムライン
        """
        if not self.results:
            raise ValueError("分析が実行されていません")

        timeline = []
        for i in range(len(self.df)):
            votes = {"buy": 0, "sell": 0, "hold": 0}

            for name, result in self.results.items():
                if i < len(result["signals"]):
                    action = result["signals"][i].lower()
                    if action in votes:
                        votes[action] += 1

            # 多数決（同点の場合はhold優先）
            max_votes = max(votes.values())
            if votes["hold"] == max_votes:
                winner = "hold"
            elif votes["buy"] == max_votes:
                winner = "buy"
            elif votes["sell"] == max_votes:
                winner = "sell"
            else:
                winner = "hold"

            timeline.append(
                {
                    "index": i,
                    "timestamp": self.df.iloc[i].get("timestamp", i),
                    "close": self.df.iloc[i].get("close", 0),
                    "buy_votes": votes["buy"],
                    "sell_votes": votes["sell"],
                    "hold_votes": votes["hold"],
                    "majority": winner,
                }
            )

        return pd.DataFrame(timeline)

    def generate_report(self) -> str:
        """
        詳細レポートを生成

        Returns:
            str: レポート文字列
        """
        if not self.results:
            return "分析結果がありません"

        total_rows = len(self.df) if self.df is not None else 0
        lines = []

        # ヘッダー
        lines.append("=" * 70)
        lines.append(f"戦略シグナル分析レポート - Phase 55.7")
        lines.append(f"分析データポイント: {total_rows}")
        lines.append(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 70)

        # 戦略別サマリー
        lines.append("\n📊 戦略別シグナル分布")
        lines.append("-" * 70)
        lines.append(
            f"{'戦略名':<22} | {'BUY':>5} | {'SELL':>5} | {'HOLD':>5} | {'hold率':>8} | 状態"
        )
        lines.append("-" * 70)

        problem_strategies = []
        for name, result in self.results.items():
            counts = result["counts"]
            total = sum(counts.values())
            hold_rate = counts.get("hold", 0) / total if total > 0 else 0

            if hold_rate > 0.95:
                status = "🔴 深刻"
                problem_strategies.append((name, hold_rate, "深刻"))
            elif hold_rate > 0.90:
                status = "🟡 問題"
                problem_strategies.append((name, hold_rate, "問題"))
            elif hold_rate > 0.80:
                status = "🟠 注意"
            else:
                status = "🟢 正常"

            lines.append(
                f"{name:<22} | {counts.get('buy', 0):>5} | {counts.get('sell', 0):>5} | "
                f"{counts.get('hold', 0):>5} | {hold_rate:>7.1%} | {status}"
            )

        # 多数決サマリー
        lines.append("\n📈 多数決結果")
        lines.append("-" * 70)
        timeline = self.get_vote_timeline()
        majority_counts = timeline["majority"].value_counts()
        total_majority = len(timeline)

        for action in ["buy", "sell", "hold"]:
            count = majority_counts.get(action, 0)
            rate = count / total_majority if total_majority > 0 else 0
            status = " ← 問題" if action == "hold" and rate > 0.80 else ""
            lines.append(f"  {action.upper():<6}: {count:>5} ({rate:>6.1%}){status}")

        # HOLD理由詳細
        lines.append("\n📋 HOLD理由詳細（上位5件）")
        lines.append("-" * 70)

        for name, result in self.results.items():
            hold_reasons = result.get("hold_reasons", {})
            if hold_reasons:
                lines.append(f"\n【{name}】")
                for reason, count in list(hold_reasons.items())[:5]:
                    rate = count / total_rows if total_rows > 0 else 0
                    lines.append(f"  {count:>4}回 ({rate:>5.1%}): {reason[:60]}")

        # 信頼度サマリー
        lines.append("\n📊 平均信頼度")
        lines.append("-" * 70)
        lines.append(f"{'戦略名':<22} | {'BUY':>8} | {'SELL':>8} | {'HOLD':>8}")
        lines.append("-" * 70)

        for name, result in self.results.items():
            avg_conf = result.get("avg_confidence", {})
            lines.append(
                f"{name:<22} | {avg_conf.get('buy', 0):>7.3f} | "
                f"{avg_conf.get('sell', 0):>7.3f} | {avg_conf.get('hold', 0):>7.3f}"
            )

        # 問題サマリー
        if problem_strategies:
            lines.append("\n⚠️ 問題のある戦略")
            lines.append("-" * 70)
            for name, hold_rate, severity in problem_strategies:
                lines.append(
                    f"  {severity}: {name} (hold率 {hold_rate:.1%}) - 条件が厳しすぎる可能性"
                )

        lines.append("\n" + "=" * 70)

        return "\n".join(lines)

    def export_csv(self, output_path: str):
        """
        詳細結果をCSV出力

        Args:
            output_path: 出力ディレクトリパス
        """
        if not self.results:
            print("分析結果がありません")
            return

        os.makedirs(output_path, exist_ok=True)
        print(f"\n💾 結果を {output_path} に出力中...")

        # 1. 戦略別シグナル一覧
        signal_data = {
            "index": range(len(self.df)),
            "close": self.df["close"].tolist(),
        }
        for name, result in self.results.items():
            signal_data[name] = result["signals"]

        df_signals = pd.DataFrame(signal_data)
        signals_path = os.path.join(output_path, "strategy_signals.csv")
        df_signals.to_csv(signals_path, index=False)
        print(f"  ✅ {signals_path}")

        # 2. 多数決推移
        timeline_path = os.path.join(output_path, "vote_timeline.csv")
        self.get_vote_timeline().to_csv(timeline_path, index=False)
        print(f"  ✅ {timeline_path}")

        # 3. HOLD理由サマリー
        reasons_path = os.path.join(output_path, "hold_reasons.txt")
        with open(reasons_path, "w", encoding="utf-8") as f:
            f.write("HOLD理由サマリー\n")
            f.write("=" * 60 + "\n\n")
            for name, result in self.results.items():
                f.write(f"=== {name} ===\n")
                for reason, count in result.get("hold_reasons", {}).items():
                    f.write(f"  {count:>4}回: {reason}\n")
                f.write("\n")
        print(f"  ✅ {reasons_path}")

        # 4. サマリーレポート
        report_path = os.path.join(output_path, "analysis_report.txt")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(self.generate_report())
        print(f"  ✅ {report_path}")

        print("💾 出力完了")


async def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(description="戦略シグナル分析スクリプト - Phase 55.7")
    parser.add_argument("--days", type=int, default=7, help="分析日数（デフォルト: 7日）")
    parser.add_argument("--verbose", "-v", action="store_true", help="詳細出力モード")
    parser.add_argument("--export", type=str, help="CSV出力ディレクトリ")
    parser.add_argument(
        "--strategy",
        type=str,
        help="特定戦略のみ分析（カンマ区切り: ATRBased,BBReversal）",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("🔍 戦略シグナル分析スクリプト - Phase 55.7")
    print("=" * 60)

    try:
        analyzer = StrategySignalAnalyzer(verbose=args.verbose)

        # データ読み込み
        await analyzer.load_data(days=args.days)

        # 戦略ロード
        analyzer.load_strategies()

        # 特定戦略のフィルタリング
        if args.strategy:
            target_names = [s.strip() for s in args.strategy.split(",")]
            analyzer.strategies = [s for s in analyzer.strategies if s.name in target_names]
            print(f"📌 {len(analyzer.strategies)}戦略に絞り込み: {target_names}")

        # 分析実行
        analyzer.run_analysis()

        # レポート出力
        print("\n" + analyzer.generate_report())

        # CSV出力（オプション）
        if args.export:
            analyzer.export_csv(args.export)

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
