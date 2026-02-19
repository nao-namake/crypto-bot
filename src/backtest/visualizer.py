"""
バックテスト可視化システム

matplotlibでエクイティカーブ・損益分布・ドローダウン・価格チャートを生成。
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

from ..core.logger import get_logger

# バックグラウンド実行用（GUIなし環境対応）
matplotlib.use("Agg")


class BacktestVisualizer:
    """
    バックテスト可視化システム（Phase 49.4: matplotlib可視化実装）

    TradeTrackerのデータを使用してパフォーマンスグラフを生成。
    """

    def __init__(self, output_dir: Optional[str] = None):
        """
        BacktestVisualizer初期化

        Args:
            output_dir: 出力ディレクトリ（Noneの場合はlogs/backtest/graphs/）
        """
        self.logger = get_logger(__name__)

        if output_dir is None:
            base_dir = Path(__file__).parent.parent.parent / "logs" / "backtest" / "graphs"
        else:
            base_dir = Path(output_dir)

        self.output_dir = base_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # グラフスタイル設定
        plt.style.use("seaborn-v0_8-darkgrid")
        plt.rcParams["figure.figsize"] = (12, 6)
        plt.rcParams["font.size"] = 10

        self.logger.info(f"BacktestVisualizer初期化完了: {self.output_dir}")

    def generate_all_charts(
        self, trade_tracker, price_data: Optional[Dict] = None, session_id: Optional[str] = None
    ) -> Path:
        """
        全グラフ一括生成

        Args:
            trade_tracker: TradeTrackerインスタンス
            price_data: 価格データ（Dict[timestamp, price]）
            session_id: セッションID（ディレクトリ名用）

        Returns:
            出力ディレクトリパス
        """
        if session_id is None:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        session_dir = self.output_dir / f"backtest_{session_id}"
        session_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"📊 グラフ生成開始: {session_dir}")

        try:
            # 1. エクイティカーブ
            self.plot_equity_curve(trade_tracker.equity_curve, session_dir / "equity_curve.png")

            # 2. 損益分布
            if trade_tracker.completed_trades:
                pnl_list = [t["pnl"] for t in trade_tracker.completed_trades]
                self.plot_pnl_distribution(pnl_list, session_dir / "pnl_distribution.png")

            # 3. ドローダウン
            self.plot_drawdown(trade_tracker.equity_curve, session_dir / "drawdown.png")

            # 4. 価格チャート + エントリー/エグジットマーカー（価格データがある場合）
            if price_data and trade_tracker.completed_trades:
                self.plot_price_with_trades(
                    price_data,
                    trade_tracker.completed_trades,
                    session_dir / "price_with_trades.png",
                )

            self.logger.info(f"✅ グラフ生成完了: {session_dir}")

            # Phase 64.11: 古いグラフフォルダの自動クリーンアップ
            self._cleanup_old_graphs()

            return session_dir

        except Exception as e:
            self.logger.error(f"❌ グラフ生成エラー: {e}")
            raise

    def _cleanup_old_graphs(self, keep: int = 5):
        """古いグラフフォルダを自動削除（最新keep件のみ保持）"""
        graph_dirs = sorted(
            [d for d in self.output_dir.iterdir() if d.is_dir() and d.name.startswith("backtest_")],
            key=lambda d: d.stat().st_mtime,
        )
        if len(graph_dirs) > keep:
            import shutil

            for old_dir in graph_dirs[: len(graph_dirs) - keep]:
                try:
                    shutil.rmtree(old_dir)
                    self.logger.debug(f"古いグラフフォルダ削除: {old_dir.name}")
                except OSError:
                    pass

    def plot_equity_curve(self, equity_curve: List[float], output_path: Path):
        """
        エクイティカーブ生成

        Args:
            equity_curve: エクイティカーブデータ（累積損益リスト）
            output_path: 出力ファイルパス
        """
        try:
            fig, ax = plt.subplots(figsize=(12, 6))

            # エクイティカーブプロット
            ax.plot(equity_curve, linewidth=2, color="#2E86AB", label="Equity")
            ax.axhline(y=0, color="red", linestyle="--", linewidth=1, alpha=0.5)

            # ゼロラインより上は緑背景、下は赤背景
            ax.fill_between(
                range(len(equity_curve)),
                equity_curve,
                0,
                where=np.array(equity_curve) >= 0,
                interpolate=True,
                alpha=0.2,
                color="green",
            )
            ax.fill_between(
                range(len(equity_curve)),
                equity_curve,
                0,
                where=np.array(equity_curve) < 0,
                interpolate=True,
                alpha=0.2,
                color="red",
            )

            ax.set_title("エクイティカーブ（累積損益推移）", fontsize=14, fontweight="bold")
            ax.set_xlabel("取引回数", fontsize=12)
            ax.set_ylabel("累積損益（円）", fontsize=12)
            ax.legend(loc="best")
            ax.grid(True, alpha=0.3)

            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches="tight")
            plt.close()

            self.logger.debug(f"✅ エクイティカーブ生成: {output_path}")

        except Exception as e:
            self.logger.error(f"❌ エクイティカーブ生成エラー: {e}")
            plt.close()

    def plot_pnl_distribution(self, pnl_list: List[float], output_path: Path):
        """
        損益分布ヒストグラム生成

        Args:
            pnl_list: 損益リスト
            output_path: 出力ファイルパス
        """
        try:
            fig, ax = plt.subplots(figsize=(12, 6))

            # ヒストグラム
            ax.hist(pnl_list, bins=30, color="#A23B72", alpha=0.7, edgecolor="black")

            # 平均値ライン
            mean_pnl = np.mean(pnl_list)
            ax.axvline(
                x=mean_pnl,
                color="blue",
                linestyle="--",
                linewidth=2,
                label=f"平均: {mean_pnl:+,.0f}円",
            )

            # ゼロライン
            ax.axvline(x=0, color="red", linestyle="-", linewidth=1, alpha=0.5, label="損益0")

            ax.set_title("損益分布ヒストグラム", fontsize=14, fontweight="bold")
            ax.set_xlabel("損益（円）", fontsize=12)
            ax.set_ylabel("取引回数", fontsize=12)
            ax.legend(loc="best")
            ax.grid(True, alpha=0.3, axis="y")

            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches="tight")
            plt.close()

            self.logger.debug(f"✅ 損益分布ヒストグラム生成: {output_path}")

        except Exception as e:
            self.logger.error(f"❌ 損益分布ヒストグラム生成エラー: {e}")
            plt.close()

    def plot_drawdown(self, equity_curve: List[float], output_path: Path):
        """
        ドローダウンチャート生成

        Args:
            equity_curve: エクイティカーブデータ
            output_path: 出力ファイルパス
        """
        try:
            fig, ax = plt.subplots(figsize=(12, 6))

            # ドローダウン計算
            drawdowns = []
            peak = equity_curve[0]
            for equity in equity_curve:
                if equity > peak:
                    peak = equity
                dd = peak - equity
                drawdowns.append(dd)

            # ドローダウンプロット
            ax.fill_between(range(len(drawdowns)), drawdowns, 0, color="#F18F01", alpha=0.6)
            ax.plot(drawdowns, linewidth=2, color="#C73E1D", label="Drawdown")

            # 最大ドローダウン
            max_dd = max(drawdowns)
            max_dd_idx = drawdowns.index(max_dd)
            ax.plot(max_dd_idx, max_dd, "ro", markersize=10, label=f"最大DD: {max_dd:,.0f}円")

            ax.set_title("ドローダウンチャート", fontsize=14, fontweight="bold")
            ax.set_xlabel("取引回数", fontsize=12)
            ax.set_ylabel("ドローダウン（円）", fontsize=12)
            ax.legend(loc="best")
            ax.grid(True, alpha=0.3)

            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches="tight")
            plt.close()

            self.logger.debug(f"✅ ドローダウンチャート生成: {output_path}")

        except Exception as e:
            self.logger.error(f"❌ ドローダウンチャート生成エラー: {e}")
            plt.close()

    def plot_price_with_trades(self, price_data: Dict, trades: List[Dict], output_path: Path):
        """
        価格チャート + エントリー/エグジットマーカー生成

        Args:
            price_data: 価格データ（Dict[timestamp, price]）
            trades: 完了した取引リスト
            output_path: 出力ファイルパス
        """
        try:
            fig, ax = plt.subplots(figsize=(14, 7))

            # 価格チャート（簡易版 - タイムスタンプソート済み前提）
            timestamps = sorted(price_data.keys())
            prices = [price_data[ts] for ts in timestamps]

            ax.plot(
                range(len(prices)), prices, linewidth=1.5, color="#2E86AB", label="Price", alpha=0.7
            )

            # エントリー/エグジットマーカー
            for trade in trades:
                entry_ts = trade.get("entry_timestamp")
                exit_ts = trade.get("exit_timestamp")
                entry_price = trade.get("entry_price")
                exit_price = trade.get("exit_price")
                pnl = trade.get("pnl", 0)

                # タイムスタンプからインデックス取得（簡易版）
                try:
                    entry_idx = timestamps.index(entry_ts) if entry_ts in timestamps else None
                    exit_idx = timestamps.index(exit_ts) if exit_ts in timestamps else None

                    if entry_idx is not None:
                        # エントリーマーカー（青丸）
                        ax.plot(entry_idx, entry_price, "bo", markersize=8, alpha=0.6)

                    if exit_idx is not None:
                        # エグジットマーカー（利益=緑、損失=赤）
                        marker_color = "go" if pnl > 0 else "ro"
                        ax.plot(exit_idx, exit_price, marker_color, markersize=8, alpha=0.6)

                        # エントリー→エグジットライン
                        if entry_idx is not None:
                            line_color = "green" if pnl > 0 else "red"
                            ax.plot(
                                [entry_idx, exit_idx],
                                [entry_price, exit_price],
                                color=line_color,
                                linestyle="--",
                                linewidth=1,
                                alpha=0.3,
                            )

                except ValueError:
                    continue  # タイムスタンプが見つからない場合はスキップ

            ax.set_title(
                "価格チャート + エントリー/エグジットマーカー", fontsize=14, fontweight="bold"
            )
            ax.set_xlabel("時間軸（インデックス）", fontsize=12)
            ax.set_ylabel("価格（円）", fontsize=12)
            ax.legend(["Price", "Entry", "Exit (Win)", "Exit (Loss)"], loc="best")
            ax.grid(True, alpha=0.3)

            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches="tight")
            plt.close()

            self.logger.debug(f"✅ 価格チャート生成: {output_path}")

        except Exception as e:
            self.logger.error(f"❌ 価格チャート生成エラー: {e}")
            plt.close()
