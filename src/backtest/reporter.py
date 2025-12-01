"""
バックテストレポートシステム

最終更新: 2025/11/16 (Phase 52.4-B)

主要機能:
- TradeTracker: 取引ペア追跡（エントリー/エグジットペアリング）
- 損益計算（取引毎・合計）・パフォーマンス指標計算
- JSON/テキスト形式レポート生成
- 週次レポート対応（Phase 48統合）
- Phase 51-52: ML統合・レジーム分類対応レポート

開発履歴:
- Phase 52.4-B: コード整理・ドキュメント統一
- Phase 52.3: 最大ドローダウン計算バグ修正
- Phase 51.8: レジーム分類レポート対応
- Phase 49.3: TradeTracker実装・完全損益分析
- Phase 34-35: バックテスト10倍高速化対応
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.config import get_threshold
from ..core.logger import get_logger

# Phase 49.4: BacktestVisualizer統合（遅延インポート）


def _get_backtest_initial_balance() -> float:
    """
    バックテスト用初期残高を設定から取得（Phase 56.1修正）

    Returns:
        初期残高（デフォルト: ¥10,000）
    """
    return get_threshold("mode_balances.backtest.initial_balance", 10000.0)


class TradeTracker:
    """
    取引ペア追跡システム

    最終更新: 2025/11/30 (Phase 56.1)

    エントリー/エグジットをペアリングし、取引毎の損益を計算。
    パフォーマンス指標（勝率・プロフィットファクター・最大DD等）を提供。

    実装履歴:
    - Phase 56.1: 初期残高を設定ファイルから取得（unified.yaml連携）
    - Phase 52.3: 最大ドローダウン計算バグ修正
    - Phase 49.3: 初回実装（損益計算・レポート機能）
    """

    def __init__(self, initial_balance: float = None):
        """
        TradeTracker初期化

        Args:
            initial_balance: 初期残高（Noneの場合は設定ファイルから取得）
        """
        # Phase 56.1: 設定ファイルから初期残高を取得（デフォルト値問題修正）
        if initial_balance is None:
            initial_balance = _get_backtest_initial_balance()
        self.logger = get_logger(__name__)
        self.open_entries: Dict[str, Dict] = {}  # オープンエントリー（order_id → entry info）
        self.completed_trades: List[Dict] = []  # 完了した取引ペア
        self.total_pnl = 0.0
        self.initial_balance = initial_balance  # Phase 52.3: 初期残高記録
        self.equity_curve: List[float] = [0.0]  # エクイティカーブ（累積損益）

    def record_entry(
        self,
        order_id: str,
        side: str,
        amount: float,
        price: float,
        timestamp,
        strategy: str = "unknown",
        regime: Optional[str] = None,  # Phase 51.8-J4-G: レジーム情報追加
    ):
        """
        エントリー注文記録

        Args:
            order_id: 注文ID
            side: "buy" or "sell"
            amount: 数量
            price: エントリー価格
            timestamp: タイムスタンプ
            strategy: 戦略名
            regime: 市場レジーム（Phase 51.8-J4-G追加）
        """
        # Phase 51.8-9準備: Timestamp serialization対応
        timestamp_str = str(timestamp) if hasattr(timestamp, "__str__") else timestamp

        # Phase 51.8-10修正: 既存order_idの上書き防止（executor.py優先）
        if order_id in self.open_entries:
            self.logger.debug(
                f"既存エントリー検出・スキップ: {order_id} "
                f"(既存regime={self.open_entries[order_id].get('regime')}, 新regime={regime})"
            )
            return  # 既存エントリーを保持（executor.pyの呼び出しを優先）

        self.open_entries[order_id] = {
            "order_id": order_id,
            "side": side,
            "amount": amount,
            "entry_price": price,
            "entry_timestamp": timestamp,  # 計算用（元オブジェクト）
            "entry_timestamp_str": timestamp_str,  # JSON出力用（文字列）
            "strategy": strategy,
            "regime": regime,  # Phase 51.8-J4-G: レジーム情報保存
        }
        self.logger.debug(
            f"📝 エントリー記録: {order_id} - {side} {amount} BTC @ {price:.0f}円 (regime={regime})"
        )

    def record_exit(
        self, order_id: str, exit_price: float, exit_timestamp, exit_reason: str = "unknown"
    ) -> Optional[Dict]:
        """
        エグジット注文記録・損益計算

        Args:
            order_id: エントリー注文ID
            exit_price: エグジット価格
            exit_timestamp: タイムスタンプ
            exit_reason: エグジット理由（TP/SL等）

        Returns:
            完了した取引情報（損益含む）、エントリーが見つからない場合はNone
        """
        if order_id not in self.open_entries:
            self.logger.warning(f"⚠️ エントリーが見つかりません: {order_id}")
            return None

        entry = self.open_entries.pop(order_id)

        # 損益計算
        pnl = self._calculate_pnl(entry["side"], entry["amount"], entry["entry_price"], exit_price)

        # 保有期間計算（分単位）- Phase 51.4-Day2追加
        if hasattr(entry["entry_timestamp"], "timestamp"):
            # datetime objectの場合
            holding_period = (
                exit_timestamp.timestamp() - entry["entry_timestamp"].timestamp()
            ) / 60
        elif isinstance(entry["entry_timestamp"], (int, float)):
            # Unix timestampの場合
            holding_period = (exit_timestamp - entry["entry_timestamp"]) / 60
        else:
            # その他の場合は0
            holding_period = 0.0

        # Phase 51.8-9準備: Timestamp serialization対応
        exit_timestamp_str = (
            str(exit_timestamp) if hasattr(exit_timestamp, "__str__") else exit_timestamp
        )

        # 取引完了情報
        trade = {
            "order_id": order_id,
            "side": entry["side"],
            "amount": entry["amount"],
            "entry_price": entry["entry_price"],
            "exit_price": exit_price,
            "entry_timestamp": entry.get(
                "entry_timestamp_str", str(entry["entry_timestamp"])
            ),  # Phase 51.8-9: JSON用文字列
            "exit_timestamp": exit_timestamp_str,  # Phase 51.8-9: JSON用文字列
            "strategy": entry["strategy"],
            "exit_reason": exit_reason,
            "pnl": pnl,
            "holding_period": holding_period,  # Phase 51.4-Day2追加
            "regime": entry.get("regime"),  # Phase 51.8-J4-G: レジーム情報追加
        }

        self.completed_trades.append(trade)
        self.total_pnl += pnl
        self.equity_curve.append(self.total_pnl)

        self.logger.info(
            f"✅ 取引完了: {order_id} - {entry['side']} {entry['amount']} BTC "
            f"@ {entry['entry_price']:.0f}円 → {exit_price:.0f}円 "
            f"(損益: {pnl:+.0f}円, 累積: {self.total_pnl:+.0f}円)"
        )

        return trade

    def _calculate_pnl(
        self, side: str, amount: float, entry_price: float, exit_price: float
    ) -> float:
        """
        損益計算（手数料考慮なし・簡易版）

        Args:
            side: "buy" or "sell"
            amount: 数量
            entry_price: エントリー価格
            exit_price: エグジット価格

        Returns:
            損益（円）
        """
        if side == "buy":
            # ロング: (エグジット価格 - エントリー価格) × 数量
            pnl = (exit_price - entry_price) * amount
        else:
            # ショート: (エントリー価格 - エグジット価格) × 数量
            pnl = (entry_price - exit_price) * amount

        return pnl

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        パフォーマンス指標計算

        Returns:
            パフォーマンス指標辞書:
                - total_trades: 総取引数
                - winning_trades: 勝ちトレード数
                - losing_trades: 負けトレード数
                - win_rate: 勝率（%）
                - total_pnl: 総損益
                - total_profit: 総利益
                - total_loss: 総損失
                - profit_factor: プロフィットファクター
                - max_drawdown: 最大ドローダウン
                - max_drawdown_pct: 最大ドローダウン（%）
                - average_win: 平均勝ちトレード
                - average_loss: 平均負けトレード
        """
        if not self.completed_trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "total_profit": 0.0,
                "total_loss": 0.0,
                "profit_factor": 0.0,
                "max_drawdown": 0.0,
                "max_drawdown_pct": 0.0,
                "average_win": 0.0,
                "average_loss": 0.0,
            }

        # 基本統計
        total_trades = len(self.completed_trades)
        winning_trades = [t for t in self.completed_trades if t["pnl"] > 0]
        losing_trades = [t for t in self.completed_trades if t["pnl"] < 0]

        total_profit = sum(t["pnl"] for t in winning_trades) if winning_trades else 0.0
        total_loss = sum(t["pnl"] for t in losing_trades) if losing_trades else 0.0

        # 勝率
        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0.0

        # プロフィットファクター
        profit_factor = (total_profit / abs(total_loss)) if total_loss != 0 else 0.0

        # 最大ドローダウン計算
        max_dd, max_dd_pct = self._calculate_max_drawdown()

        # 平均勝ちトレード/負けトレード
        avg_win = (total_profit / len(winning_trades)) if winning_trades else 0.0
        avg_loss = (total_loss / len(losing_trades)) if losing_trades else 0.0

        return {
            "total_trades": total_trades,
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": win_rate,
            "total_pnl": self.total_pnl,
            "total_profit": total_profit,
            "total_loss": total_loss,
            "profit_factor": profit_factor,
            "max_drawdown": max_dd,
            "max_drawdown_pct": max_dd_pct,
            "average_win": avg_win,
            "average_loss": avg_loss,
        }

    def _calculate_max_drawdown(self) -> tuple:
        """
        最大ドローダウン計算（Phase 52.3修正: 初期残高を考慮）

        equity_curveは累積損益を記録しているため、初期残高を加算して
        絶対残高ベースでドローダウンを計算する。

        Returns:
            (max_drawdown, max_drawdown_pct): 最大ドローダウン（円）、最大ドローダウン（%）
        """
        if len(self.equity_curve) < 2:
            return (0.0, 0.0)

        # Phase 52.3修正: 初期残高から開始
        max_equity = self.initial_balance
        max_dd = 0.0
        max_dd_pct = 0.0

        for cumulative_pnl in self.equity_curve:
            # 累積損益を絶対残高に変換
            current_equity = self.initial_balance + cumulative_pnl

            if current_equity > max_equity:
                max_equity = current_equity

            dd = max_equity - current_equity
            if dd > max_dd:
                max_dd = dd
                max_dd_pct = (dd / max_equity * 100) if max_equity > 0 else 0.0

        return (max_dd, max_dd_pct)

    def get_regime_performance(self) -> Dict[str, Dict[str, Any]]:
        """
        Phase 51.8-J4-G: レジーム別パフォーマンス集計

        各市場レジームでの取引パフォーマンスを集計し、
        レジーム別の最適戦略重み決定に必要なデータを提供。

        Returns:
            レジーム別パフォーマンス辞書:
                {
                    "tight_range": {
                        "total_trades": 10,
                        "winning_trades": 7,
                        "win_rate": 70.0,
                        "total_pnl": 1500.0,
                        "average_pnl": 150.0
                    },
                    ...
                }
        """
        regime_stats: Dict[str, Dict[str, Any]] = {}

        # レジーム別に取引を集計
        for trade in self.completed_trades:
            regime = trade.get("regime", "unknown")

            # レジーム統計初期化
            if regime not in regime_stats:
                regime_stats[regime] = {
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "win_rate": 0.0,
                    "total_pnl": 0.0,
                    "total_profit": 0.0,
                    "total_loss": 0.0,
                    "average_pnl": 0.0,
                    "trades": [],  # 詳細取引リスト（オプション）
                }

            # 統計更新
            regime_stats[regime]["total_trades"] += 1
            regime_stats[regime]["total_pnl"] += trade["pnl"]
            regime_stats[regime]["trades"].append(trade)

            if trade["pnl"] > 0:
                regime_stats[regime]["winning_trades"] += 1
                regime_stats[regime]["total_profit"] += trade["pnl"]
            elif trade["pnl"] < 0:
                regime_stats[regime]["losing_trades"] += 1
                regime_stats[regime]["total_loss"] += trade["pnl"]

        # 勝率・平均損益計算
        for regime, stats in regime_stats.items():
            total = stats["total_trades"]
            if total > 0:
                stats["win_rate"] = (stats["winning_trades"] / total) * 100
                stats["average_pnl"] = stats["total_pnl"] / total

        return regime_stats

    def get_strategy_performance(self) -> Dict[str, Dict[str, Any]]:
        """
        Phase 57.1: 戦略別パフォーマンス集計

        各戦略の取引パフォーマンスを集計し、
        6戦略それぞれの寄与度を可視化するためのデータを提供。

        Returns:
            戦略別パフォーマンス辞書:
                {
                    "atr_based": {
                        "total_trades": 15,
                        "winning_trades": 9,
                        "losing_trades": 6,
                        "win_rate": 60.0,
                        "total_pnl": 2500.0,
                        "total_profit": 4000.0,
                        "total_loss": -1500.0,
                        "profit_factor": 2.67,
                        "average_pnl": 166.67,
                        "average_win": 444.44,
                        "average_loss": -250.0
                    },
                    ...
                }
        """
        strategy_stats: Dict[str, Dict[str, Any]] = {}

        # 戦略別に取引を集計
        for trade in self.completed_trades:
            strategy = trade.get("strategy", "unknown")

            # 戦略統計初期化
            if strategy not in strategy_stats:
                strategy_stats[strategy] = {
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "win_rate": 0.0,
                    "total_pnl": 0.0,
                    "total_profit": 0.0,
                    "total_loss": 0.0,
                    "profit_factor": 0.0,
                    "average_pnl": 0.0,
                    "average_win": 0.0,
                    "average_loss": 0.0,
                    "trades": [],  # 詳細取引リスト（オプション）
                }

            # 統計更新
            strategy_stats[strategy]["total_trades"] += 1
            strategy_stats[strategy]["total_pnl"] += trade["pnl"]
            strategy_stats[strategy]["trades"].append(trade)

            if trade["pnl"] > 0:
                strategy_stats[strategy]["winning_trades"] += 1
                strategy_stats[strategy]["total_profit"] += trade["pnl"]
            elif trade["pnl"] < 0:
                strategy_stats[strategy]["losing_trades"] += 1
                strategy_stats[strategy]["total_loss"] += trade["pnl"]

        # 勝率・平均損益・PF計算
        for strategy, stats in strategy_stats.items():
            total = stats["total_trades"]
            wins = stats["winning_trades"]
            losses = stats["losing_trades"]

            if total > 0:
                stats["win_rate"] = (wins / total) * 100
                stats["average_pnl"] = stats["total_pnl"] / total

            if wins > 0:
                stats["average_win"] = stats["total_profit"] / wins

            if losses > 0:
                stats["average_loss"] = stats["total_loss"] / losses

            # プロフィットファクター計算
            if stats["total_loss"] != 0:
                stats["profit_factor"] = stats["total_profit"] / abs(stats["total_loss"])

        return strategy_stats


class BacktestReporter:
    """
    バックテストレポート生成システム

    最終更新: 2025/11/16 (Phase 52.4-B)

    本番同一ロジックバックテスト用のレポート生成機能。
    TradeTracker統合・週次レポート対応。

    実装履歴:
    - Phase 52.3: ドローダウン計算バグ修正
    - Phase 51.8: レジーム分類レポート対応
    - Phase 49.3: TradeTracker統合
    - Phase 34-35: バックテスト高速化対応
    """

    def __init__(self, output_dir: Optional[str] = None):
        self.logger = get_logger(__name__)

        # 出力ディレクトリ設定（Phase 29: バックテスト統合フォルダ）
        if output_dir is None:
            # src/backtest/logs/ 配下に保存（集約済み）
            base_dir = Path(__file__).parent / "logs"
        else:
            base_dir = Path(output_dir)
        self.output_dir = base_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Phase 49.3: TradeTracker統合
        self.trade_tracker = TradeTracker()

        self.logger.info(f"BacktestReporter初期化完了: {self.output_dir}")

    async def generate_backtest_report(
        self, final_stats: Dict[str, Any], start_date: datetime, end_date: datetime
    ) -> str:
        """
        バックテストレポート生成（Phase 49.3拡張: 損益分析統合）

        Args:
            final_stats: バックテスト統計データ
            start_date: バックテスト開始日
            end_date: バックテスト終了日

        Returns:
            生成されたレポートファイルパス
        """
        self.logger.info("バックテストレポート生成開始")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_filename = f"backtest_{timestamp}.json"
        json_filepath = self.output_dir / json_filename

        try:
            # Phase 49.3: パフォーマンス指標取得
            performance_metrics = self.trade_tracker.get_performance_metrics()

            # Phase 51.8-J4-G: レジーム別パフォーマンス取得
            regime_performance = self.trade_tracker.get_regime_performance()

            # レポートデータ構築
            # Phase 35.5: 型チェック追加（文字列/datetime両対応）
            start_date_str = start_date if isinstance(start_date, str) else start_date.isoformat()
            end_date_str = end_date if isinstance(end_date, str) else end_date.isoformat()

            # Phase 57.1: 戦略別パフォーマンス取得
            strategy_performance = self.trade_tracker.get_strategy_performance()

            report_data = {
                "backtest_info": {
                    "start_date": start_date_str,
                    "end_date": end_date_str,
                    "duration_days": (
                        (end_date - start_date).days
                        if isinstance(start_date, datetime) and isinstance(end_date, datetime)
                        else 0
                    ),
                    "generated_at": datetime.now().isoformat(),
                    "phase": "Phase_57.1_戦略別パフォーマンス対応",
                },
                "execution_stats": final_stats,
                "system_info": {
                    "runner_type": "BacktestRunner",
                    "data_source": "CSV",
                    "logic_type": "本番同一ロジック",
                },
                # Phase 49.3: 損益分析追加
                "performance_metrics": performance_metrics,
                "completed_trades": len(self.trade_tracker.completed_trades),
                # Phase 51.8-J4-G: レジーム別パフォーマンス追加
                "regime_performance": regime_performance,
                # Phase 57.1: 戦略別パフォーマンス追加
                "strategy_performance": strategy_performance,
            }

            # JSONファイル保存
            with open(json_filepath, "w", encoding="utf-8") as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"バックテストレポート生成完了(JSON): {json_filepath}")

            # Phase 51.7: パフォーマンス指標サマリーをWARNINGレベルで出力（バックテスト時に確認しやすく）
            self.logger.warning("=" * 60)
            self.logger.warning("📊 バックテスト結果サマリー")
            self.logger.warning("=" * 60)
            self.logger.warning(f"総取引数: {performance_metrics.get('total_trades', 0)}件")
            self.logger.warning(f"勝ちトレード: {performance_metrics.get('winning_trades', 0)}件")
            self.logger.warning(f"負けトレード: {performance_metrics.get('losing_trades', 0)}件")
            self.logger.warning(f"勝率: {performance_metrics.get('win_rate', 0.0):.2f}%")
            self.logger.warning(f"総損益: ¥{performance_metrics.get('total_pnl', 0.0):,.0f}")
            self.logger.warning(f"総利益: ¥{performance_metrics.get('total_profit', 0.0):,.0f}")
            self.logger.warning(f"総損失: ¥{performance_metrics.get('total_loss', 0.0):,.0f}")
            self.logger.warning(
                f"プロフィットファクター: {performance_metrics.get('profit_factor', 0.0):.2f}"
            )
            self.logger.warning(
                f"最大ドローダウン: ¥{performance_metrics.get('max_drawdown', 0.0):,.0f} ({performance_metrics.get('max_drawdown_pct', 0.0):.2f}%)"
            )
            self.logger.warning(
                f"平均勝ちトレード: ¥{performance_metrics.get('average_win', 0.0):,.0f}"
            )
            self.logger.warning(
                f"平均負けトレード: ¥{performance_metrics.get('average_loss', 0.0):,.0f}"
            )
            self.logger.warning("=" * 60)

            # Phase 51.8-J4-G: レジーム別パフォーマンスサマリー
            if regime_performance:
                self.logger.warning("")
                self.logger.warning("=" * 60)
                self.logger.warning("📊 レジーム別パフォーマンス（Phase 51.8-J4-G）")
                self.logger.warning("=" * 60)
                for regime, stats in regime_performance.items():
                    self.logger.warning(f"\n【{regime}】")
                    self.logger.warning(f"  総取引数: {stats.get('total_trades', 0)}件")
                    self.logger.warning(f"  勝ちトレード: {stats.get('winning_trades', 0)}件")
                    self.logger.warning(f"  負けトレード: {stats.get('losing_trades', 0)}件")
                    self.logger.warning(f"  勝率: {stats.get('win_rate', 0.0):.2f}%")
                    self.logger.warning(f"  総損益: ¥{stats.get('total_pnl', 0.0):,.0f}")
                    self.logger.warning(f"  平均損益: ¥{stats.get('average_pnl', 0.0):,.0f}")
                self.logger.warning("=" * 60)

            # Phase 57.1: 戦略別パフォーマンスサマリー
            strategy_performance = self.trade_tracker.get_strategy_performance()
            if strategy_performance:
                self.logger.warning("")
                self.logger.warning("=" * 60)
                self.logger.warning("📊 戦略別パフォーマンス（Phase 57.1）")
                self.logger.warning("=" * 60)
                for strategy, stats in strategy_performance.items():
                    self.logger.warning(f"\n【{strategy}】")
                    self.logger.warning(f"  総取引数: {stats.get('total_trades', 0)}件")
                    self.logger.warning(f"  勝ちトレード: {stats.get('winning_trades', 0)}件")
                    self.logger.warning(f"  負けトレード: {stats.get('losing_trades', 0)}件")
                    self.logger.warning(f"  勝率: {stats.get('win_rate', 0.0):.2f}%")
                    self.logger.warning(f"  総損益: ¥{stats.get('total_pnl', 0.0):,.0f}")
                    self.logger.warning(f"  PF: {stats.get('profit_factor', 0.0):.2f}")
                    self.logger.warning(f"  平均損益: ¥{stats.get('average_pnl', 0.0):,.0f}")
                self.logger.warning("=" * 60)

                # JSON出力にも追加
                report_data["strategy_performance"] = {
                    k: {kk: vv for kk, vv in v.items() if kk != "trades"}
                    for k, v in strategy_performance.items()
                }

            # Phase 49.3: テキストレポート生成
            text_filename = f"backtest_{timestamp}.txt"
            text_filepath = self.output_dir / text_filename
            await self._generate_text_report(
                text_filepath, report_data, start_date_str, end_date_str
            )

            self.logger.info(f"バックテストレポート生成完了(TEXT): {text_filepath}")

            # Phase 49.4: matplotlib可視化実行
            try:
                from .visualizer import BacktestVisualizer

                visualizer = BacktestVisualizer()
                # 価格データ準備（簡易版 - 今回はNoneで省略可）
                graphs_dir = visualizer.generate_all_charts(
                    trade_tracker=self.trade_tracker,
                    price_data=None,  # 価格データは今回省略（必要に応じて後で追加）
                    session_id=timestamp,
                )
                self.logger.info(f"バックテストグラフ生成完了: {graphs_dir}")

            except Exception as viz_error:
                # グラフ生成失敗してもレポートは生成済みなので継続
                self.logger.warning(f"⚠️ グラフ生成エラー（処理継続）: {viz_error}")

            return str(json_filepath)

        except Exception as e:
            self.logger.error(f"レポート生成エラー: {e}")
            raise

    async def _generate_text_report(
        self, filepath: Path, report_data: Dict, start_date: str, end_date: str
    ):
        """
        テキストレポート生成（詳細な損益レポート）

        Args:
            filepath: 出力ファイルパス
            report_data: レポートデータ
            start_date: 開始日
            end_date: 終了日
        """
        perf = report_data.get("performance_metrics", {})

        report_lines = [
            "=" * 80,
            "バックテストレポート - Phase 49.3完了版",
            "=" * 80,
            "",
            "【バックテスト期間】",
            f"  開始日: {start_date}",
            f"  終了日: {end_date}",
            f"  期間: {report_data['backtest_info'].get('duration_days', 0)}日間",
            "",
            "【取引サマリー】",
            f"  総取引数: {perf.get('total_trades', 0)}回",
            f"  勝ちトレード: {perf.get('winning_trades', 0)}回",
            f"  負けトレード: {perf.get('losing_trades', 0)}回",
            f"  勝率: {perf.get('win_rate', 0):.2f}%",
            "",
            "【損益サマリー】",
            f"  総損益: {perf.get('total_pnl', 0):+,.0f}円",
            f"  総利益: {perf.get('total_profit', 0):+,.0f}円",
            f"  総損失: {perf.get('total_loss', 0):+,.0f}円",
            f"  プロフィットファクター: {perf.get('profit_factor', 0):.2f}",
            "",
            "【リスク指標】",
            f"  最大ドローダウン: {perf.get('max_drawdown', 0):,.0f}円 ({perf.get('max_drawdown_pct', 0):.2f}%)",
            f"  平均勝ちトレード: {perf.get('average_win', 0):+,.0f}円",
            f"  平均負けトレード: {perf.get('average_loss', 0):+,.0f}円",
            "",
            "【実行統計】",
            f"  処理サイクル数: {report_data.get('execution_stats', {}).get('data_processing', {}).get('processed_cycles', 0)}回",
            f"  データポイント数: {report_data.get('execution_stats', {}).get('data_processing', {}).get('total_data_points', 0)}件",
            "",
            "=" * 80,
            f"レポート生成日時: {report_data['backtest_info'].get('generated_at', 'N/A')}",
            "=" * 80,
        ]

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))

    async def save_progress_report(self, progress_stats: Dict[str, Any]) -> str:
        """
        進捗レポート保存（時系列バックテスト用）

        Args:
            progress_stats: 進捗統計データ

        Returns:
            保存されたファイルパス
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"progress_{timestamp}.json"
            filepath = self.output_dir / filename

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(progress_stats, f, ensure_ascii=False, indent=2, default=str)

            self.logger.debug(f"進捗レポート保存: {filepath}")
            return str(filepath)

        except Exception as e:
            self.logger.warning(f"進捗レポート保存エラー: {e}")
            raise

    async def save_error_report(self, error_message: str, context: Dict[str, Any]) -> str:
        """
        エラーレポート保存

        Args:
            error_message: エラーメッセージ
            context: エラーコンテキスト

        Returns:
            保存されたファイルパス
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"error_{timestamp}.json"
            filepath = self.output_dir / filename

            error_data = {
                "error_message": error_message,
                "context": context,
                "timestamp": datetime.now().isoformat(),
                "phase": "Phase_38.4_BacktestSystem",
            }

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(error_data, f, ensure_ascii=False, indent=2, default=str)

            self.logger.info(f"エラーレポート保存: {filepath}")
            return str(filepath)

        except Exception as e:
            self.logger.error(f"エラーレポート保存失敗: {e}")
            raise
