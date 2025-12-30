"""
バックテストレポートシステム - Phase 49.3完了

Phase 34-35完了実績:
- バックテスト10倍高速化対応（6-8時間→45分実行）
- 特徴量・ML予測バッチ化レポート対応
- 15分足データ収集80倍改善レポート対応

Phase 49.3新機能:
- TradeTracker: 取引ペア追跡（エントリー/エグジットペアリング）
- 損益計算（取引毎・合計）
- パフォーマンス指標計算（勝率・プロフィットファクター・最大DD等）
- 詳細テキストレポート生成

主要機能:
- JSON形式レポート生成（構造化・時系列対応）
- 進捗レポート（時系列バックテスト用）
- エラーレポート（デバッグ用）
- 実行統計レポート（勝率・PnL・取引回数）
- Phase 49: 完全な損益分析レポート
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from ..core.config import get_threshold
from ..core.logger import get_logger

# Phase 49.4: BacktestVisualizer統合（遅延インポート）


class TradeTracker:
    """
    取引ペア追跡システム（Phase 49.3: 損益計算・レポート実装）

    エントリー/エグジットをペアリングし、取引毎の損益を計算。
    パフォーマンス指標（勝率・プロフィットファクター・最大DD等）を提供。
    """

    def __init__(self):
        """TradeTracker初期化"""
        self.logger = get_logger(__name__)
        self.open_entries: Dict[str, Dict] = {}  # オープンエントリー（order_id → entry info）
        self.completed_trades: List[Dict] = []  # 完了した取引ペア
        self.total_pnl = 0.0
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
        ml_prediction: Optional[int] = None,  # Phase 54.8: ML予測クラス（0=SELL, 1=HOLD, 2=BUY）
        ml_confidence: Optional[float] = None,  # Phase 54.8: ML信頼度
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
            ml_prediction: ML予測クラス（Phase 54.8追加）
            ml_confidence: ML信頼度（Phase 54.8追加）
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
            "ml_prediction": ml_prediction,  # Phase 54.8: ML予測クラス
            "ml_confidence": ml_confidence,  # Phase 54.8: ML信頼度
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
            "ml_prediction": entry.get("ml_prediction"),  # Phase 54.8: ML予測クラス
            "ml_confidence": entry.get("ml_confidence"),  # Phase 54.8: ML信頼度
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
        パフォーマンス指標計算（Phase 53: 追加指標含む）

        Returns:
            パフォーマンス指標辞書:
                基本指標:
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

                Phase 53追加（重要度: 高）:
                - sharpe_ratio: シャープレシオ（年率換算）
                - expectancy: 期待値（1取引あたり期待収益）
                - recovery_factor: リカバリーファクター（DD回復力）

                Phase 53追加（重要度: 中）:
                - sortino_ratio: ソルティノレシオ（下方リスク調整）
                - calmar_ratio: カルマーレシオ（年率/DD%）
                - payoff_ratio: ペイオフレシオ（勝ち負け比）

                Phase 53追加（重要度: 低）:
                - max_consecutive_wins: 最大連勝数
                - max_consecutive_losses: 最大連敗数
                - trades_per_month: 月間取引頻度
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
                # Phase 53: 追加指標
                "sharpe_ratio": 0.0,
                "expectancy": 0.0,
                "recovery_factor": 0.0,
                "sortino_ratio": 0.0,
                "calmar_ratio": 0.0,
                "payoff_ratio": 0.0,
                "max_consecutive_wins": 0,
                "max_consecutive_losses": 0,
                "trades_per_month": 0.0,
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

        # Phase 53: 追加評価指標（重要度別）
        # === 重要度: 高 ===
        # シャープレシオ（リスク調整後リターン）
        sharpe_ratio = self._calculate_sharpe_ratio()

        # 期待値（1取引あたり期待収益）
        win_rate_decimal = win_rate / 100
        expectancy = (win_rate_decimal * avg_win) + ((1 - win_rate_decimal) * avg_loss)

        # リカバリーファクター（DD回復力）
        recovery_factor = (total_profit / max_dd) if max_dd > 0 else 0.0

        # === 重要度: 中 ===
        # ソルティノレシオ（下方リスク調整リターン）
        sortino_ratio = self._calculate_sortino_ratio()

        # カルマーレシオ（年率リターン / 最大DD%）
        calmar_ratio = self._calculate_calmar_ratio(max_dd_pct)

        # ペイオフレシオ（勝ち負け比率）
        payoff_ratio = (avg_win / abs(avg_loss)) if avg_loss != 0 else 0.0

        # === 重要度: 低 ===
        # 連勝・連敗数
        max_consecutive_wins, max_consecutive_losses = self._calculate_consecutive_streaks()

        # 取引頻度（月間）
        trades_per_month = self._calculate_trades_per_month()

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
            # Phase 53: 追加指標
            "sharpe_ratio": sharpe_ratio,
            "expectancy": expectancy,
            "recovery_factor": recovery_factor,
            "sortino_ratio": sortino_ratio,
            "calmar_ratio": calmar_ratio,
            "payoff_ratio": payoff_ratio,
            "max_consecutive_wins": max_consecutive_wins,
            "max_consecutive_losses": max_consecutive_losses,
            "trades_per_month": trades_per_month,
        }

    def _calculate_max_drawdown(self) -> tuple:
        """
        最大ドローダウン計算（Phase 53.11修正: 実残高ベースDD%計算）

        Returns:
            (max_drawdown, max_drawdown_pct): 最大ドローダウン（円）、最大ドローダウン（%）
        """
        if len(self.equity_curve) < 2:
            return (0.0, 0.0)

        # Phase 57.5: 設定キー修正（mode_balances.backtest.initial_balance）
        initial_capital = get_threshold("mode_balances.backtest.initial_balance", 500000.0)

        max_equity = self.equity_curve[0]
        max_dd = 0.0
        max_dd_pct = 0.0

        for equity in self.equity_curve:
            if equity > max_equity:
                max_equity = equity

            dd = max_equity - equity
            if dd > max_dd:
                max_dd = dd
                # Phase 53.11: DD%は実残高（初期資金+累積損益のピーク）で計算
                actual_balance_at_peak = initial_capital + max_equity
                max_dd_pct = (
                    (dd / actual_balance_at_peak * 100) if actual_balance_at_peak > 0 else 0.0
                )

        return (max_dd, max_dd_pct)

    def _calculate_sharpe_ratio(self) -> float:
        """
        Phase 53: シャープレシオ計算（重要度: 高）

        リスク調整後リターンを測定。
        計算式: (平均リターン / リターンの標準偏差) × √252

        Returns:
            シャープレシオ（年率換算）
        """
        import math

        if len(self.completed_trades) < 2:
            return 0.0

        # 各取引のリターン（損益）
        returns = [t["pnl"] for t in self.completed_trades]

        # 平均リターン
        mean_return = sum(returns) / len(returns)

        # 標準偏差
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance) if variance > 0 else 0.0

        if std_dev == 0:
            return 0.0

        # 年率換算（252営業日ベース、5分足なので調整）
        # 1日約96取引（24時間 × 60分 / 5分 × 取引確率）として概算
        annualization_factor = math.sqrt(252 * 20)  # 約71
        sharpe = (mean_return / std_dev) * annualization_factor

        return round(sharpe, 2)

    def _calculate_sortino_ratio(self) -> float:
        """
        Phase 53: ソルティノレシオ計算（重要度: 中）

        下方リスクのみを考慮したリスク調整後リターン。
        計算式: 平均リターン / 下方偏差 × √252

        Returns:
            ソルティノレシオ（年率換算）
        """
        import math

        if len(self.completed_trades) < 2:
            return 0.0

        returns = [t["pnl"] for t in self.completed_trades]
        mean_return = sum(returns) / len(returns)

        # 下方偏差（負のリターンのみ）
        negative_returns = [r for r in returns if r < 0]
        if not negative_returns:
            return 0.0  # 負のリターンがない場合

        downside_variance = sum(r**2 for r in negative_returns) / len(returns)
        downside_dev = math.sqrt(downside_variance) if downside_variance > 0 else 0.0

        if downside_dev == 0:
            return 0.0

        annualization_factor = math.sqrt(252 * 20)
        sortino = (mean_return / downside_dev) * annualization_factor

        return round(sortino, 2)

    def _calculate_calmar_ratio(self, max_dd_pct: float) -> float:
        """
        Phase 53: カルマーレシオ計算（重要度: 中）

        年率リターン / 最大ドローダウン%
        DD対比のリターン効率を測定。

        Args:
            max_dd_pct: 最大ドローダウン（%）

        Returns:
            カルマーレシオ
        """
        if max_dd_pct == 0 or not self.completed_trades:
            return 0.0

        # 総リターン率（初期資金100,000円ベース）
        initial_capital = 100000.0
        total_return_pct = (self.total_pnl / initial_capital) * 100

        # 年率換算（バックテスト期間から推定）
        # 完了取引数から取引日数を推定
        if len(self.completed_trades) >= 2:
            first_trade = self.completed_trades[0]
            last_trade = self.completed_trades[-1]
            try:
                from datetime import datetime

                # タイムスタンプ取得
                first_ts = first_trade.get("entry_timestamp")
                last_ts = last_trade.get("exit_timestamp")
                if first_ts and last_ts:
                    if hasattr(first_ts, "timestamp"):
                        days = (last_ts - first_ts).days
                    else:
                        days = 180  # デフォルト
                else:
                    days = 180
            except Exception:
                days = 180
        else:
            days = 180

        # 年率換算
        annual_return_pct = (total_return_pct / days) * 365 if days > 0 else 0.0

        calmar = annual_return_pct / max_dd_pct if max_dd_pct > 0 else 0.0

        return round(calmar, 2)

    def _calculate_consecutive_streaks(self) -> tuple:
        """
        Phase 53: 連勝・連敗数計算（重要度: 低）

        Returns:
            (max_consecutive_wins, max_consecutive_losses): 最大連勝数、最大連敗数
        """
        if not self.completed_trades:
            return (0, 0)

        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0

        for trade in self.completed_trades:
            pnl = trade.get("pnl", 0)
            if pnl > 0:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            elif pnl < 0:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)
            else:
                # 損益0の場合はリセットしない
                pass

        return (max_wins, max_losses)

    def _calculate_trades_per_month(self) -> float:
        """
        Phase 53: 月間取引頻度計算（重要度: 低）

        Returns:
            月間平均取引数
        """
        if len(self.completed_trades) < 2:
            return 0.0

        try:
            first_trade = self.completed_trades[0]
            last_trade = self.completed_trades[-1]

            first_ts = first_trade.get("entry_timestamp")
            last_ts = last_trade.get("exit_timestamp")

            if first_ts and last_ts:
                if hasattr(first_ts, "timestamp"):
                    days = (last_ts - first_ts).days
                else:
                    days = 180  # デフォルト
            else:
                days = 180

            months = days / 30.0 if days > 0 else 1.0
            trades_per_month = len(self.completed_trades) / months

            return round(trades_per_month, 1)
        except Exception:
            return 0.0

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


class MLAnalyzer:
    """
    ML予測分析システム（Phase 54.8: バックテストML分析）

    バックテストのML予測結果を分析し、レポートに追加。

    分析項目:
    - 予測分布（SELL/HOLD/BUY件数・比率）
    - 信頼度統計（平均・高信頼度比率）
    - ML vs 戦略一致率
    """

    def __init__(self):
        """MLAnalyzer初期化"""
        self.logger = get_logger(__name__)

    def analyze_predictions(
        self,
        predictions: np.ndarray,
        probabilities: np.ndarray,
        completed_trades: List[Dict],
    ) -> Dict[str, Any]:
        """
        ML予測全体分析

        Args:
            predictions: 全予測クラス配列（0=SELL, 1=HOLD, 2=BUY）
            probabilities: 全予測確率配列（shape: [n_samples, 3]）
            completed_trades: 完了した取引リスト（ML情報含む）

        Returns:
            ML分析結果辞書
        """
        result = {}

        # 1. 予測分布分析
        result["prediction_distribution"] = self._analyze_prediction_distribution(predictions)

        # 2. 信頼度統計分析
        result["confidence_statistics"] = self._analyze_confidence_statistics(probabilities)

        # 3. ML vs 戦略一致率分析（取引にML情報がある場合のみ）
        result["ml_strategy_agreement"] = self._analyze_ml_strategy_agreement(completed_trades)

        return result

    def _analyze_prediction_distribution(self, predictions: np.ndarray) -> Dict[str, Any]:
        """
        ML予測分布分析

        Args:
            predictions: 予測クラス配列

        Returns:
            予測分布統計
        """
        if len(predictions) == 0:
            return {
                "sell_count": 0,
                "hold_count": 0,
                "buy_count": 0,
                "sell_pct": 0.0,
                "hold_pct": 0.0,
                "buy_pct": 0.0,
                "hold_target_met": True,
                "total_predictions": 0,
            }

        total = len(predictions)
        sell_count = int(np.sum(predictions == 0))
        hold_count = int(np.sum(predictions == 1))
        buy_count = int(np.sum(predictions == 2))

        sell_pct = (sell_count / total) * 100
        hold_pct = (hold_count / total) * 100
        buy_pct = (buy_count / total) * 100

        # Phase 54.8: HOLD ≤ 60% 目標達成チェック
        hold_target_met = hold_pct <= 60.0

        return {
            "sell_count": sell_count,
            "hold_count": hold_count,
            "buy_count": buy_count,
            "sell_pct": round(sell_pct, 1),
            "hold_pct": round(hold_pct, 1),
            "buy_pct": round(buy_pct, 1),
            "hold_target_met": hold_target_met,
            "total_predictions": total,
        }

    def _analyze_confidence_statistics(self, probabilities: np.ndarray) -> Dict[str, Any]:
        """
        ML信頼度統計分析

        Args:
            probabilities: 予測確率配列（shape: [n_samples, 3]）

        Returns:
            信頼度統計
        """
        if len(probabilities) == 0:
            return {
                "avg_confidence": 0.0,
                "min_confidence": 0.0,
                "max_confidence": 0.0,
                "std_confidence": 0.0,
                "high_confidence_ratio": 0.0,
                "high_confidence_threshold": 0.60,
            }

        # 各予測の最大確率（信頼度）を取得
        max_probs = np.max(probabilities, axis=1)

        avg_confidence = float(np.mean(max_probs))
        min_confidence = float(np.min(max_probs))
        max_confidence = float(np.max(max_probs))
        std_confidence = float(np.std(max_probs))

        # 高信頼度（>60%）の割合
        high_conf_threshold = 0.60
        high_confidence_ratio = float(np.sum(max_probs > high_conf_threshold) / len(max_probs))

        return {
            "avg_confidence": round(avg_confidence, 3),
            "min_confidence": round(min_confidence, 3),
            "max_confidence": round(max_confidence, 3),
            "std_confidence": round(std_confidence, 3),
            "high_confidence_ratio": round(high_confidence_ratio * 100, 1),
            "high_confidence_threshold": high_conf_threshold,
        }

    def _analyze_ml_strategy_agreement(self, completed_trades: List[Dict]) -> Dict[str, Any]:
        """
        ML vs 戦略一致率分析

        Args:
            completed_trades: 完了した取引リスト（ml_prediction含む）

        Returns:
            一致率統計
        """
        # ML情報を持つ取引を抽出
        trades_with_ml = [t for t in completed_trades if t.get("ml_prediction") is not None]

        if len(trades_with_ml) == 0:
            return {
                "total_trades_with_ml": 0,
                "agreement_count": 0,
                "disagreement_count": 0,
                "agreement_rate": 0.0,
                "agreement_win_rate": 0.0,
                "disagreement_win_rate": 0.0,
                "agreement_avg_pnl": 0.0,
                "disagreement_avg_pnl": 0.0,
            }

        agreement_trades = []
        disagreement_trades = []

        for trade in trades_with_ml:
            ml_pred = trade.get("ml_prediction")
            side = trade.get("side")

            # ML予測と取引方向の一致判定
            # BUY(2) と buy、SELL(0) と sell が一致
            if (ml_pred == 2 and side == "buy") or (ml_pred == 0 and side == "sell"):
                agreement_trades.append(trade)
            else:
                disagreement_trades.append(trade)

        total = len(trades_with_ml)
        agreement_count = len(agreement_trades)
        disagreement_count = len(disagreement_trades)

        # 勝率計算
        agreement_wins = [t for t in agreement_trades if t.get("pnl", 0) > 0]
        disagreement_wins = [t for t in disagreement_trades if t.get("pnl", 0) > 0]

        agreement_win_rate = (
            (len(agreement_wins) / agreement_count * 100) if agreement_count > 0 else 0.0
        )
        disagreement_win_rate = (
            (len(disagreement_wins) / disagreement_count * 100) if disagreement_count > 0 else 0.0
        )

        # 平均損益計算
        agreement_avg_pnl = (
            sum(t.get("pnl", 0) for t in agreement_trades) / agreement_count
            if agreement_count > 0
            else 0.0
        )
        disagreement_avg_pnl = (
            sum(t.get("pnl", 0) for t in disagreement_trades) / disagreement_count
            if disagreement_count > 0
            else 0.0
        )

        return {
            "total_trades_with_ml": total,
            "agreement_count": agreement_count,
            "disagreement_count": disagreement_count,
            "agreement_rate": round((agreement_count / total) * 100, 1) if total > 0 else 0.0,
            "agreement_win_rate": round(agreement_win_rate, 1),
            "disagreement_win_rate": round(disagreement_win_rate, 1),
            "agreement_avg_pnl": round(agreement_avg_pnl, 0),
            "disagreement_avg_pnl": round(disagreement_avg_pnl, 0),
        }

    def log_analysis_summary(self, analysis: Dict[str, Any]) -> None:
        """
        ML分析サマリーをログ出力

        Args:
            analysis: ML分析結果
        """
        pred_dist = analysis.get("prediction_distribution", {})
        conf_stats = analysis.get("confidence_statistics", {})
        agreement = analysis.get("ml_strategy_agreement", {})

        self.logger.warning("")
        self.logger.warning("=" * 60)
        self.logger.warning("📊 ML Analysis (Phase 54.8)")
        self.logger.warning("=" * 60)

        # 予測分布
        self.logger.warning("Prediction Distribution:")
        hold_status = "[PASS]" if pred_dist.get("hold_target_met", False) else "[FAIL]"
        self.logger.warning(
            f"  SELL: {pred_dist.get('sell_count', 0):,} ({pred_dist.get('sell_pct', 0):.1f}%)"
        )
        self.logger.warning(
            f"  HOLD: {pred_dist.get('hold_count', 0):,} ({pred_dist.get('hold_pct', 0):.1f}%)  "
            f"← Target ≤60% {hold_status}"
        )
        self.logger.warning(
            f"  BUY:  {pred_dist.get('buy_count', 0):,} ({pred_dist.get('buy_pct', 0):.1f}%)"
        )

        # 信頼度統計
        self.logger.warning("")
        self.logger.warning("Confidence Statistics:")
        self.logger.warning(
            f"  Average: {conf_stats.get('avg_confidence', 0):.3f} | "
            f"High (>60%): {conf_stats.get('high_confidence_ratio', 0):.1f}%"
        )

        # ML vs 戦略一致率
        if agreement.get("total_trades_with_ml", 0) > 0:
            self.logger.warning("")
            self.logger.warning("ML vs Strategy Agreement:")
            self.logger.warning(
                f"  Agreement Rate: {agreement.get('agreement_rate', 0):.1f}% "
                f"({agreement.get('agreement_count', 0)}/{agreement.get('total_trades_with_ml', 0)} trades)"
            )
            self.logger.warning(
                f"  Agreement Win Rate: {agreement.get('agreement_win_rate', 0):.1f}% | "
                f"Disagreement Win Rate: {agreement.get('disagreement_win_rate', 0):.1f}%"
            )

        self.logger.warning("=" * 60)


class BacktestReporter:
    """
    バックテストレポート生成システム（Phase 38.4完了）

    本番同一ロジックバックテスト用のシンプルなレポート機能。
    Phase 34-35高速化対応完了。
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
        self,
        final_stats: Dict[str, Any],
        start_date: datetime,
        end_date: datetime,
        ml_predictions_data: Optional[Dict[str, np.ndarray]] = None,  # Phase 54.8: ML分析用
    ) -> str:
        """
        バックテストレポート生成（Phase 49.3拡張: 損益分析統合）

        Args:
            final_stats: バックテスト統計データ
            start_date: バックテスト開始日
            end_date: バックテスト終了日
            ml_predictions_data: ML予測データ（Phase 54.8追加）
                {"predictions": np.ndarray, "probabilities": np.ndarray}

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

            # Phase 54.8: ML分析実行
            ml_analysis = {}
            if ml_predictions_data is not None:
                try:
                    ml_analyzer = MLAnalyzer()
                    ml_analysis = ml_analyzer.analyze_predictions(
                        predictions=ml_predictions_data.get("predictions", np.array([])),
                        probabilities=ml_predictions_data.get("probabilities", np.array([])),
                        completed_trades=self.trade_tracker.completed_trades,
                    )
                except Exception as ml_error:
                    self.logger.warning(f"⚠️ ML分析エラー（処理継続）: {ml_error}")

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
                    "phase": "Phase_54.8_ML分析追加",
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
                # Phase 54.8: ML分析追加
                "ml_analysis": ml_analysis,
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

            # Phase 54.8: ML分析サマリー出力
            if ml_analysis:
                ml_analyzer = MLAnalyzer()
                ml_analyzer.log_analysis_summary(ml_analysis)

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
        テキストレポート生成（Phase 49.3: 詳細な損益レポート）

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
