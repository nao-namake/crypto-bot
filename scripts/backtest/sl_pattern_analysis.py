#!/usr/bin/env python3
"""
SL決済パターン分析スクリプト - Phase 62.18

目的:
  SL決済されたポジションの価格推移パターンを分析し、Bot改修に活かす。
  MFE（Maximum Favorable Excursion）データを使用してパターン分類。

分析パターン:
  - 一直線損切り: エントリー直後から損切り方向へ一直線
  - 微益後損切り: 少しプラスになった後に損切り
  - プラス圏経由損切り: 200-500円のMFE経由後に損切り
  - 500円以上経由損切り: TP到達可能だったのに損切り（改善余地大）

使い方:
  # ローカルJSONファイルを分析
  python3 scripts/analysis/sl_pattern_analysis.py <json_path>

  # CIの最新バックテスト結果を取得して分析
  python3 scripts/analysis/sl_pattern_analysis.py --from-ci

  # 詳細出力
  python3 scripts/analysis/sl_pattern_analysis.py --from-ci --verbose
"""

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@dataclass
class SLPatternResult:
    """SLパターン分析結果データクラス"""

    # メタ情報
    timestamp: str = ""
    backtest_start: str = ""
    backtest_end: str = ""
    tp_target: float = 500.0  # 現在のTP目標額（円）

    # 全体サマリー
    total_trades: int = 0
    sl_trades: int = 0
    tp_trades: int = 0

    # パターン分類結果
    straight_loss_count: int = 0  # 一直線損切り（MFE <= 0）
    small_profit_loss_count: int = 0  # 微益後損切り（0 < MFE < 200）
    profit_then_loss_count: int = 0  # プラス圏経由損切り（200 <= MFE < TP）
    tp_reachable_loss_count: int = 0  # TP到達可能だった損切り（MFE >= TP）

    # MFE統計（SL決済のみ）
    sl_mfe_avg: float = 0.0
    sl_mfe_median: float = 0.0
    sl_mfe_max: float = 0.0
    sl_mfe_min: float = 0.0

    # MAE統計（SL決済のみ）
    sl_mae_avg: float = 0.0
    sl_mae_median: float = 0.0

    # 逃した利益分析
    missed_profit_count: int = 0  # TP到達可能だった件数
    missed_profit_total: float = 0.0  # 逃した利益合計
    missed_profit_avg: float = 0.0  # 平均逃した利益

    # 詳細データ（verbose用）
    sl_trades_detail: List[Dict[str, Any]] = field(default_factory=list)


class SLPatternAnalyzer:
    """SLパターン分析クラス"""

    # パターン名定義
    PATTERN_STRAIGHT_LOSS = "一直線損切り"
    PATTERN_SMALL_PROFIT = "微益後損切り"
    PATTERN_PROFIT_THEN_LOSS = "プラス圏経由損切り"
    PATTERN_TP_REACHABLE = "500円以上経由損切り"

    def __init__(self, json_path: str, tp_target: float = 500.0):
        self.json_path = Path(json_path)
        self.tp_target = tp_target
        self.data = self._load_json()
        self.trades = self._extract_all_trades()
        self.result = SLPatternResult(tp_target=tp_target)

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

    def classify_sl_pattern(self, trade: Dict[str, Any]) -> str:
        """
        SL決済のパターンを分類

        Args:
            trade: 取引データ（mfe, mae, pnl等を含む）

        Returns:
            パターン名
        """
        mfe = trade.get("mfe", 0) or 0  # Noneの場合は0

        if mfe <= 0:
            return self.PATTERN_STRAIGHT_LOSS
        elif mfe < 200:
            return self.PATTERN_SMALL_PROFIT
        elif mfe < self.tp_target:
            return self.PATTERN_PROFIT_THEN_LOSS
        else:
            return self.PATTERN_TP_REACHABLE

    def analyze(self) -> SLPatternResult:
        """分析実行"""
        self.result.timestamp = datetime.now().isoformat()

        # メタ情報
        backtest_info = self.data.get("backtest_info", {})
        self.result.backtest_start = backtest_info.get("start_date", "")[:10]
        self.result.backtest_end = backtest_info.get("end_date", "")[:10]

        # 全体統計
        self.result.total_trades = len(self.trades)

        # SL/TP分類
        sl_trades = [t for t in self.trades if t.get("pnl", 0) < 0]
        tp_trades = [t for t in self.trades if t.get("pnl", 0) >= 0]

        self.result.sl_trades = len(sl_trades)
        self.result.tp_trades = len(tp_trades)

        if not sl_trades:
            print("⚠️ SL決済データがありません")
            return self.result

        # パターン分類
        patterns = {
            self.PATTERN_STRAIGHT_LOSS: [],
            self.PATTERN_SMALL_PROFIT: [],
            self.PATTERN_PROFIT_THEN_LOSS: [],
            self.PATTERN_TP_REACHABLE: [],
        }

        for trade in sl_trades:
            pattern = self.classify_sl_pattern(trade)
            patterns[pattern].append(trade)

        self.result.straight_loss_count = len(patterns[self.PATTERN_STRAIGHT_LOSS])
        self.result.small_profit_loss_count = len(patterns[self.PATTERN_SMALL_PROFIT])
        self.result.profit_then_loss_count = len(patterns[self.PATTERN_PROFIT_THEN_LOSS])
        self.result.tp_reachable_loss_count = len(patterns[self.PATTERN_TP_REACHABLE])

        # MFE統計（SL決済のみ）
        mfe_values = [t.get("mfe", 0) or 0 for t in sl_trades]
        if mfe_values:
            self.result.sl_mfe_avg = sum(mfe_values) / len(mfe_values)
            sorted_mfe = sorted(mfe_values)
            self.result.sl_mfe_median = sorted_mfe[len(sorted_mfe) // 2]
            self.result.sl_mfe_max = max(mfe_values)
            self.result.sl_mfe_min = min(mfe_values)

        # MAE統計（SL決済のみ）
        mae_values = [t.get("mae", 0) or 0 for t in sl_trades]
        if mae_values:
            self.result.sl_mae_avg = sum(mae_values) / len(mae_values)
            sorted_mae = sorted(mae_values)
            self.result.sl_mae_median = sorted_mae[len(sorted_mae) // 2]

        # 逃した利益分析（TP到達可能だった取引）
        tp_reachable_trades = patterns[self.PATTERN_TP_REACHABLE]
        if tp_reachable_trades:
            self.result.missed_profit_count = len(tp_reachable_trades)
            # 逃した利益 = MFE - 実際のPnL（損失なのでマイナス）= MFE + |PnL|
            missed_profits = [
                (t.get("mfe", 0) or 0) - (t.get("pnl", 0) or 0) for t in tp_reachable_trades
            ]
            self.result.missed_profit_total = sum(missed_profits)
            self.result.missed_profit_avg = (
                self.result.missed_profit_total / self.result.missed_profit_count
            )

        # 詳細データ保存
        self.result.sl_trades_detail = sl_trades

        return self.result


class SLPatternReporter:
    """SLパターン分析レポート生成クラス"""

    def __init__(self, result: SLPatternResult):
        self.result = result

    def print_console(self, verbose: bool = False):
        """コンソール出力"""
        r = self.result

        print("\n" + "=" * 60)
        print("SL決済パターン分析")
        print("=" * 60)
        print(f"分析日時: {r.timestamp}")
        print(f"バックテスト期間: {r.backtest_start} ~ {r.backtest_end}")
        print(f"TP目標額: ¥{r.tp_target:,.0f}")
        print("-" * 60)

        # 全体サマリー
        print("\n【全体サマリー】")
        print(f"  総取引数: {r.total_trades}件")
        sl_rate = (r.sl_trades / r.total_trades * 100) if r.total_trades > 0 else 0
        tp_rate = (r.tp_trades / r.total_trades * 100) if r.total_trades > 0 else 0
        print(f"  SL決済数: {r.sl_trades}件 ({sl_rate:.1f}%)")
        print(f"  TP決済数: {r.tp_trades}件 ({tp_rate:.1f}%)")

        if r.sl_trades == 0:
            print("\n⚠️ SL決済データがないため、パターン分析をスキップします")
            return

        # パターン分類
        print("\n【SL決済パターン分類】")
        patterns = [
            ("一直線損切り", r.straight_loss_count, "エントリー精度に問題"),
            ("微益後損切り", r.small_profit_loss_count, "小さなMFE経由"),
            ("プラス圏経由", r.profit_then_loss_count, "200-500円のMFE経由"),
            ("500円以上経由", r.tp_reachable_loss_count, "TP到達可能だった"),
        ]

        for name, count, desc in patterns:
            rate = (count / r.sl_trades * 100) if r.sl_trades > 0 else 0
            warning = " ⚠️" if name == "500円以上経由" and count > 0 else ""
            print(f"  {name}: {count:>3}件 ({rate:>5.1f}%) - {desc}{warning}")

        # MFE統計
        print("\n【MFE統計（SL決済のみ）】")
        print(f"  平均MFE: ¥{r.sl_mfe_avg:,.0f}")
        print(f"  中央値MFE: ¥{r.sl_mfe_median:,.0f}")
        print(f"  最大MFE: ¥{r.sl_mfe_max:,.0f}")
        print(f"  最小MFE: ¥{r.sl_mfe_min:,.0f}")

        # MAE統計
        print("\n【MAE統計（SL決済のみ）】")
        print(f"  平均MAE: ¥{r.sl_mae_avg:,.0f}")
        print(f"  中央値MAE: ¥{r.sl_mae_median:,.0f}")

        # 逃した利益分析
        if r.missed_profit_count > 0:
            print("\n【逃した利益分析】")
            print(f"  500円以上MFEでSL決済: {r.missed_profit_count}件")
            print(f"  逃した利益合計: ¥{r.missed_profit_total:,.0f}")
            print(f"  平均逃した利益: ¥{r.missed_profit_avg:,.0f}/件")

        # 改善示唆
        print("\n" + "-" * 60)
        print("【改善示唆】")
        self._print_improvement_suggestions()
        print("=" * 60 + "\n")

        # Verbose: 詳細データ
        if verbose and r.sl_trades_detail:
            self._print_verbose_detail()

    def _print_improvement_suggestions(self):
        """改善示唆出力"""
        r = self.result
        suggestions = []

        # 一直線損切り率
        straight_rate = (r.straight_loss_count / r.sl_trades * 100) if r.sl_trades > 0 else 0
        if straight_rate > 15:
            suggestions.append(
                f"  1. 一直線損切り率 {straight_rate:.1f}% が高い "
                f"→ エントリーロジック/タイミング改善余地あり"
            )
        elif straight_rate > 0:
            suggestions.append(f"  1. 一直線損切り率 {straight_rate:.1f}% は許容範囲内")

        # 500円以上経由率
        tp_reachable_rate = (
            (r.tp_reachable_loss_count / r.sl_trades * 100) if r.sl_trades > 0 else 0
        )
        if tp_reachable_rate > 10:
            suggestions.append(
                f"  2. 500円以上経由率 {tp_reachable_rate:.1f}% が高い "
                f"→ TP設定見直し/トレーリングストップ検討"
            )
        elif r.tp_reachable_loss_count > 0:
            suggestions.append(
                f"  2. 500円以上経由率 {tp_reachable_rate:.1f}% "
                f"({r.tp_reachable_loss_count}件) → 一部TP設定改善余地"
            )

        # 逃した利益
        if r.missed_profit_total > 10000:
            suggestions.append(
                f"  3. 逃した利益 ¥{r.missed_profit_total:,.0f} が大きい "
                f"→ 部分利確/トレーリングストップが有効"
            )

        # 全体傾向
        profit_via_rate = (
            ((r.profit_then_loss_count + r.tp_reachable_loss_count) / r.sl_trades * 100)
            if r.sl_trades > 0
            else 0
        )
        if profit_via_rate > 50:
            suggestions.append(
                f"  4. プラス圏経由損切りが {profit_via_rate:.1f}% "
                f"→ 大半が一度プラスになってから損切り。利確ロジック改善が効果的"
            )

        if not suggestions:
            suggestions.append("  特に重大な問題は検出されませんでした。")

        for s in suggestions:
            print(s)

    def _print_verbose_detail(self):
        """詳細データ出力"""
        r = self.result
        print("\n" + "=" * 60)
        print("【詳細: SL決済取引一覧（上位10件: MFE降順）】")
        print("=" * 60)

        # MFE降順でソート
        sorted_trades = sorted(r.sl_trades_detail, key=lambda t: t.get("mfe", 0) or 0, reverse=True)

        print(f"{'#':<3} {'戦略':<20} {'MFE':>8} {'MAE':>8} {'PnL':>10} {'レジーム':<12}")
        print("-" * 70)

        for i, trade in enumerate(sorted_trades[:10], 1):
            strategy = trade.get("strategy", "N/A")[:18]
            mfe = trade.get("mfe", 0) or 0
            mae = trade.get("mae", 0) or 0
            pnl = trade.get("pnl", 0) or 0
            regime = trade.get("regime", "N/A")

            print(f"{i:<3} {strategy:<20} {mfe:>8,.0f} {mae:>8,.0f} {pnl:>10,.0f} {regime:<12}")


class CIIntegration:
    """GitHub Actions CI連携クラス（standard_analysisから流用）"""

    WORKFLOW_NAME = "backtest.yml"
    ARTIFACT_NAME = "backtest-results"
    DOWNLOAD_DIR = Path("docs/検証記録/ci_downloads")

    @classmethod
    def fetch_latest_backtest(cls) -> Tuple[Optional[str], Optional[str]]:
        """最新のCIバックテスト結果を取得"""
        print("CI最新バックテスト結果を検索中...")

        if not cls._check_gh_cli():
            return None, "gh CLI がインストールされていません"

        run_id, run_info = cls._get_latest_successful_run()
        if not run_id:
            return None, run_info

        print(f"最新実行を検出: Run ID {run_id}")
        print(f"   {run_info}")

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
        cls.DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

        for f in cls.DOWNLOAD_DIR.glob("*"):
            if f.is_file():
                f.unlink()
            elif f.is_dir():
                shutil.rmtree(f)

        print(f"artifact ダウンロード中 (Run ID: {run_id})...")

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
                print(f"ダウンロード失敗: {result.stderr}")
                return None

            json_files = list(cls.DOWNLOAD_DIR.glob("**/*.json"))
            if not json_files:
                print("JSONファイルが見つかりません")
                return None

            json_path = max(json_files, key=lambda p: p.stat().st_mtime)
            print(f"JSONファイル取得: {json_path}")

            return str(json_path)

        except subprocess.TimeoutExpired:
            print("ダウンロードタイムアウト")
            return None
        except Exception as e:
            print(f"ダウンロードエラー: {e}")
            return None


def main():
    parser = argparse.ArgumentParser(description="SL決済パターン分析スクリプト")
    parser.add_argument(
        "json_path",
        nargs="?",
        help="バックテストJSONファイルパス（--from-ci時は不要）",
    )
    parser.add_argument(
        "--from-ci",
        action="store_true",
        help="CIの最新バックテスト結果を自動取得して分析",
    )
    parser.add_argument(
        "--tp-target",
        type=float,
        default=500.0,
        help="TP目標額（円）。デフォルト: 500",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="詳細出力（SL取引一覧を表示）",
    )

    args = parser.parse_args()

    # JSONパス決定
    json_path = args.json_path

    if args.from_ci:
        json_path, run_info = CIIntegration.fetch_latest_backtest()
        if not json_path:
            print(f"CIからの取得に失敗: {run_info}")
            sys.exit(1)
        print(f"CI実行情報: {run_info}")
        print()
    elif not json_path:
        print("json_path または --from-ci オプションが必要です")
        parser.print_help()
        sys.exit(1)

    # 分析実行
    analyzer = SLPatternAnalyzer(json_path, tp_target=args.tp_target)
    result = analyzer.analyze()

    # レポート出力
    reporter = SLPatternReporter(result)
    reporter.print_console(verbose=args.verbose)

    print("SL決済パターン分析完了")


if __name__ == "__main__":
    main()
