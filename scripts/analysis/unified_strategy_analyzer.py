#!/usr/bin/env python3
"""
統合戦略分析スクリプト v2.0 - Phase 61

戦略分析の統合ツール。Phase 61.3/61.4の戦略評価・改善に使用。

使用方法:
    python scripts/analysis/unified_strategy_analyzer.py --mode theoretical  # 理論分析（数秒）
    python scripts/analysis/unified_strategy_analyzer.py --mode quick        # 簡易実証（30秒）
    python scripts/analysis/unified_strategy_analyzer.py --mode full         # 完全実証（3分）
    python scripts/analysis/unified_strategy_analyzer.py --mode regime-only  # レジーム統計のみ
    python scripts/analysis/unified_strategy_analyzer.py --days 60 --export ./output --format all

分析モード:
    theoretical - 設定ベース理論分析（レジームカバレッジ・冗長性）（~数秒）
    quick       - 基本メトリクスのみ（~30秒）
    full        - 全分析（時間帯別・連敗・相関）（~3分）
    regime-only - レジーム分類精度のみ（~10秒）
"""

import argparse
import asyncio
import json
import sys
from dataclasses import asdict, dataclass, field
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
    load_config("config/core/thresholds.yaml")
except Exception:
    pass

from src.core.config.threshold_manager import get_threshold
from src.core.services.market_regime_classifier import MarketRegimeClassifier
from src.core.services.regime_types import RegimeType
from src.features.feature_generator import FeatureGenerator
from src.strategies.utils import EntryAction

# ============================================================================
# データモデル
# ============================================================================


@dataclass
class StrategyMetrics:
    """戦略評価メトリクス"""

    strategy_name: str
    # 基本メトリクス
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    # シグナル分布
    buy_count: int = 0
    sell_count: int = 0
    hold_count: int = 0
    hold_rate: float = 0.0
    # 信頼度
    avg_buy_confidence: float = 0.0
    avg_sell_confidence: float = 0.0
    # レジーム別パフォーマンス
    regime_performance: Dict[str, Dict[str, float]] = field(default_factory=dict)
    # 相関・貢献度
    correlation_with_others: Dict[str, float] = field(default_factory=dict)
    ensemble_contribution: float = 0.0
    # 時間帯別（full mode）
    hourly_performance: Dict[int, Dict[str, float]] = field(default_factory=dict)
    best_hours: List[int] = field(default_factory=list)
    worst_hours: List[int] = field(default_factory=list)
    # 連敗分析（full mode）
    max_consecutive_losses: int = 0
    max_consecutive_wins: int = 0
    # 評価・提案
    overall_score: float = 0.0
    improvement_suggestions: List[str] = field(default_factory=list)
    deletion_reasons: List[str] = field(default_factory=list)


@dataclass
class RegimeStats:
    """レジーム分類統計"""

    total_rows: int = 0
    tight_range_count: int = 0
    normal_range_count: int = 0
    trending_count: int = 0
    high_volatility_count: int = 0

    @property
    def tight_range_pct(self) -> float:
        return (self.tight_range_count / self.total_rows * 100) if self.total_rows > 0 else 0

    @property
    def normal_range_pct(self) -> float:
        return (self.normal_range_count / self.total_rows * 100) if self.total_rows > 0 else 0

    @property
    def trending_pct(self) -> float:
        return (self.trending_count / self.total_rows * 100) if self.total_rows > 0 else 0

    @property
    def high_volatility_pct(self) -> float:
        return (self.high_volatility_count / self.total_rows * 100) if self.total_rows > 0 else 0

    @property
    def range_total_pct(self) -> float:
        return self.tight_range_pct + self.normal_range_pct


@dataclass
class AnalysisResult:
    """分析結果全体"""

    analysis_date: str
    analysis_days: int
    mode: str
    total_data_points: int
    regime_stats: RegimeStats
    strategy_metrics: List[StrategyMetrics]
    deletion_candidates: List[str]
    overall_recommendations: List[str]


@dataclass
class TheoreticalResult:
    """理論分析結果"""

    analysis_date: str
    strategies: List[str]
    strategy_types: Dict[str, str]
    regime_weights: Dict[str, Dict[str, float]]
    regime_coverage: Dict[str, Dict[str, Any]]
    redundant_strategies: List[Dict[str, str]]
    deletion_candidates: List[Dict[str, str]]
    remaining_strategies: List[str]


# ============================================================================
# メイン分析クラス
# ============================================================================


class UnifiedStrategyAnalyzer:
    """統合戦略分析器"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.df: Optional[pd.DataFrame] = None
        self.df_with_features: Optional[pd.DataFrame] = None
        self.strategies: Dict[str, Any] = {}
        self.regime_classifier = MarketRegimeClassifier()
        self.regime_stats = RegimeStats()
        self.strategy_metrics: List[StrategyMetrics] = []

    # ========================================================================
    # Phase 1: データ準備
    # ========================================================================

    async def load_data(self, days: int = 60) -> None:
        """CSVからデータ読み込み・特徴量生成"""
        print(f"\n📊 {days}日分のデータを取得中...")

        csv_path = project_root / "src/backtest/data/historical/BTC_JPY_15m.csv"
        print(f"   📁 CSVから読み込み: {csv_path}")

        df = pd.read_csv(csv_path)

        # timestamp処理
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp")

        # 日数フィルタリング
        if days > 0 and len(df) > days * 96:
            df = df.tail(days * 96)

        self.df = df
        print(f"   ✅ {len(df)}データポイントを取得")

        # 特徴量生成
        print("   🔧 特徴量生成中...")
        feature_gen = FeatureGenerator()
        self.df_with_features = await feature_gen.generate_features(df.copy())
        print(f"   ✅ 特徴量生成完了: {len(self.df_with_features.columns)}列")

    def load_strategies(self, target_strategy: Optional[str] = None) -> None:
        """戦略をロード"""
        print("\n🔧 戦略をロード中...")

        # 戦略を直接インポート
        from src.strategies.implementations.adx_trend import ADXTrendStrengthStrategy
        from src.strategies.implementations.atr_based import ATRBasedStrategy
        from src.strategies.implementations.bb_reversal import BBReversalStrategy
        from src.strategies.implementations.donchian_channel import DonchianChannelStrategy
        from src.strategies.implementations.macd_ema_crossover import MACDEMACrossoverStrategy
        from src.strategies.implementations.stochastic_reversal import StochasticReversalStrategy

        strategy_classes = {
            "ATRBased": ATRBasedStrategy,
            "DonchianChannel": DonchianChannelStrategy,
            "ADXTrendStrength": ADXTrendStrengthStrategy,
            "BBReversal": BBReversalStrategy,
            "StochasticReversal": StochasticReversalStrategy,
            "MACDEMACrossover": MACDEMACrossoverStrategy,
        }

        for name, cls in strategy_classes.items():
            if target_strategy and name != target_strategy:
                continue
            try:
                self.strategies[name] = cls()
                if self.verbose:
                    print(f"   ✅ {name} ロード完了")
            except Exception as e:
                print(f"   ⚠️ {name} ロード失敗: {e}")

        print(f"   ✅ {len(self.strategies)}戦略をロード")

    def classify_regimes(self) -> None:
        """全行のレジーム分類・統計計算"""
        print("\n📈 レジーム分類中...")

        if self.df_with_features is None:
            print("   ⚠️ データが読み込まれていません")
            return

        self.regime_stats.total_rows = len(self.df_with_features)

        # BB幅計算に必要な最小行数（MarketRegimeClassifierのbb_period=20）
        min_period = 20

        for idx in range(len(self.df_with_features)):
            if idx < min_period:
                # データ不足時はnormal_rangeとしてカウント
                self.regime_stats.normal_range_count += 1
                continue

            # その時点までの履歴データを渡す（BB幅計算に必要な行数を確保）
            df_slice = self.df_with_features.iloc[max(0, idx - 100) : idx + 1]
            try:
                regime = self.regime_classifier.classify(df_slice)
                if regime == RegimeType.TIGHT_RANGE:
                    self.regime_stats.tight_range_count += 1
                elif regime == RegimeType.NORMAL_RANGE:
                    self.regime_stats.normal_range_count += 1
                elif regime == RegimeType.TRENDING:
                    self.regime_stats.trending_count += 1
                elif regime == RegimeType.HIGH_VOLATILITY:
                    self.regime_stats.high_volatility_count += 1
            except Exception:
                pass

        print(f"   ✅ {self.regime_stats.total_rows}行を分類完了")

    # ========================================================================
    # Phase 2: 戦略評価
    # ========================================================================

    async def evaluate_strategies(self, mode: str = "full") -> None:
        """全戦略の評価"""
        print(f"\n🔍 戦略評価開始（mode={mode}）...")

        for name, strategy in self.strategies.items():
            print(f"\n   📊 {name} 評価中...")
            metrics = await self._evaluate_single_strategy(name, strategy, mode)
            self.strategy_metrics.append(metrics)

        # 相関分析（full modeのみ）
        if mode == "full" and len(self.strategy_metrics) > 1:
            self._calculate_correlation()
            self._measure_ensemble_contribution()

        # 削除候補特定
        self._identify_deletion_candidates()

    async def _evaluate_single_strategy(
        self, name: str, strategy: Any, mode: str
    ) -> StrategyMetrics:
        """単一戦略の詳細評価"""
        metrics = StrategyMetrics(strategy_name=name)

        # シグナル分析
        signals = await self._analyze_signals(strategy)
        metrics.buy_count = signals["buy_count"]
        metrics.sell_count = signals["sell_count"]
        metrics.hold_count = signals["hold_count"]
        metrics.hold_rate = signals["hold_rate"]
        metrics.avg_buy_confidence = signals["avg_buy_confidence"]
        metrics.avg_sell_confidence = signals["avg_sell_confidence"]

        # バックテスト実行
        backtest_result = await self._run_backtest(strategy)
        metrics.total_trades = backtest_result["total_trades"]
        metrics.winning_trades = backtest_result["winning_trades"]
        metrics.losing_trades = backtest_result["losing_trades"]
        metrics.win_rate = backtest_result["win_rate"]
        metrics.total_pnl = backtest_result["total_pnl"]
        metrics.avg_win = backtest_result["avg_win"]
        metrics.avg_loss = backtest_result["avg_loss"]
        metrics.profit_factor = backtest_result["profit_factor"]
        metrics.sharpe_ratio = backtest_result["sharpe_ratio"]
        metrics.max_drawdown = backtest_result["max_drawdown"]

        # レジーム別パフォーマンス
        metrics.regime_performance = await self._analyze_regime_performance(strategy)

        # 時間帯別・連敗分析（full modeのみ）
        if mode == "full":
            hourly = self._analyze_hourly_performance(backtest_result.get("trades", []))
            metrics.hourly_performance = hourly["performance"]
            metrics.best_hours = hourly["best_hours"]
            metrics.worst_hours = hourly["worst_hours"]

            consecutive = self._analyze_consecutive_results(backtest_result.get("trades", []))
            metrics.max_consecutive_losses = consecutive["max_losses"]
            metrics.max_consecutive_wins = consecutive["max_wins"]

        # 総合スコア計算
        metrics.overall_score = self._calculate_overall_score(metrics)

        # 改善提案生成
        metrics.improvement_suggestions = self._generate_suggestions(metrics)

        return metrics

    async def _analyze_signals(self, strategy: Any) -> Dict[str, Any]:
        """シグナル分布分析"""
        buy_count, sell_count, hold_count = 0, 0, 0
        buy_confidences, sell_confidences = [], []

        # サンプリング（5行ごと）- 最低100行から開始（指標計算に必要）
        min_start = min(100, len(self.df_with_features) - 1)
        sample_indices = range(min_start, len(self.df_with_features), 5)

        for idx in sample_indices:
            # 戦略はDataFrameを期待し、最後の行を分析する
            df_slice = self.df_with_features.iloc[: idx + 1]
            try:
                decision = strategy.analyze(df_slice)
                if decision.action == EntryAction.BUY:
                    buy_count += 1
                    buy_confidences.append(decision.confidence)
                elif decision.action == EntryAction.SELL:
                    sell_count += 1
                    sell_confidences.append(decision.confidence)
                else:
                    hold_count += 1
            except Exception:
                hold_count += 1

        total = buy_count + sell_count + hold_count
        return {
            "buy_count": buy_count,
            "sell_count": sell_count,
            "hold_count": hold_count,
            "hold_rate": (hold_count / total * 100) if total > 0 else 100,
            "avg_buy_confidence": np.mean(buy_confidences) if buy_confidences else 0,
            "avg_sell_confidence": np.mean(sell_confidences) if sell_confidences else 0,
        }

    async def _run_backtest(self, strategy: Any) -> Dict[str, Any]:
        """シンプルバックテスト実行"""
        position = None
        entry_price = 0
        entry_idx = 0
        trades = []
        equity_curve = [0.0]  # 累積損益

        # 設定から読み込み（デフォルト: normal_range）
        tp_rate = get_threshold("regime_settings.normal_range.tp_percent", 1.0) / 100
        sl_rate = get_threshold("regime_settings.normal_range.sl_percent", 0.7) / 100

        # 最低100行から開始（指標計算に必要）
        min_start = min(100, len(self.df_with_features) - 1)
        for idx in range(min_start, len(self.df_with_features)):
            row = self.df_with_features.iloc[idx]
            current_price = row["close"]

            # ポジション決済チェック
            if position:
                pnl = 0
                exit_reason = None

                if position == "long":
                    if current_price >= entry_price * (1 + tp_rate):
                        pnl = (current_price - entry_price) * 0.01
                        exit_reason = "TP"
                    elif current_price <= entry_price * (1 - sl_rate):
                        pnl = (current_price - entry_price) * 0.01
                        exit_reason = "SL"
                elif position == "short":
                    if current_price <= entry_price * (1 - tp_rate):
                        pnl = (entry_price - current_price) * 0.01
                        exit_reason = "TP"
                    elif current_price >= entry_price * (1 + sl_rate):
                        pnl = (entry_price - current_price) * 0.01
                        exit_reason = "SL"

                if exit_reason:
                    # 累積損益を更新
                    equity_curve.append(equity_curve[-1] + pnl)
                    trades.append(
                        {
                            "entry_idx": entry_idx,
                            "exit_idx": idx,
                            "position": position,
                            "entry_price": entry_price,
                            "exit_price": current_price,
                            "pnl": pnl,
                            "exit_reason": exit_reason,
                            "hour": row.get("hour", 0) if hasattr(row, "get") else 0,
                        }
                    )
                    position = None

            # 新規エントリー
            if not position:
                try:
                    # 戦略はDataFrameを期待し、最後の行を分析する
                    df_slice = self.df_with_features.iloc[: idx + 1]
                    decision = strategy.analyze(df_slice)
                    if decision.action == EntryAction.BUY:
                        position = "long"
                        entry_price = current_price
                        entry_idx = idx
                    elif decision.action == EntryAction.SELL:
                        position = "short"
                        entry_price = current_price
                        entry_idx = idx
                except Exception:
                    pass

        # メトリクス計算
        wins = [t["pnl"] for t in trades if t["pnl"] > 0]
        losses = [t["pnl"] for t in trades if t["pnl"] < 0]

        total_wins = sum(wins)
        total_losses = abs(sum(losses))

        # シャープレシオ計算（日次リターンベース）
        pnl_list = [t["pnl"] for t in trades]
        sharpe_ratio = 0.0
        if len(pnl_list) > 1:
            mean_return = np.mean(pnl_list)
            std_return = np.std(pnl_list)
            if std_return > 0:
                sharpe_ratio = (mean_return / std_return) * np.sqrt(252)

        # 最大ドローダウン計算
        max_drawdown = 0.0
        peak = equity_curve[0]
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            drawdown = peak - equity
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        return {
            "total_trades": len(trades),
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate": (len(wins) / len(trades) * 100) if trades else 0,
            "total_pnl": sum(t["pnl"] for t in trades),
            "avg_win": np.mean(wins) if wins else 0,
            "avg_loss": np.mean(losses) if losses else 0,
            "profit_factor": (total_wins / total_losses) if total_losses > 0 else 0,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "trades": trades,
        }

    async def _analyze_regime_performance(self, strategy: Any) -> Dict[str, Dict[str, float]]:
        """レジーム別パフォーマンス分析"""
        regime_trades: Dict[str, List[float]] = {
            "tight_range": [],
            "normal_range": [],
            "trending": [],
            "high_volatility": [],
        }

        position = None
        entry_price = 0
        entry_regime = None

        # 設定から読み込み（デフォルト: normal_range）
        tp_rate = get_threshold("regime_settings.normal_range.tp_percent", 1.0) / 100
        sl_rate = get_threshold("regime_settings.normal_range.sl_percent", 0.7) / 100

        # 最低100行から開始（指標計算に必要）
        min_start = min(100, len(self.df_with_features) - 1)
        for idx in range(min_start, len(self.df_with_features)):
            row = self.df_with_features.iloc[idx]
            current_price = row["close"]

            # レジーム判定（1行のDataFrameを渡す）
            try:
                row_df = self.df_with_features.iloc[[idx]]
                regime = self.regime_classifier.classify(row_df)
                regime_key = regime.value if hasattr(regime, "value") else str(regime)
            except Exception:
                regime_key = "normal_range"

            # 決済チェック
            if position:
                pnl = 0
                exit_reason = None

                if position == "long":
                    if current_price >= entry_price * (1 + tp_rate):
                        pnl = (current_price - entry_price) * 0.01
                        exit_reason = "TP"
                    elif current_price <= entry_price * (1 - sl_rate):
                        pnl = (current_price - entry_price) * 0.01
                        exit_reason = "SL"
                elif position == "short":
                    if current_price <= entry_price * (1 - tp_rate):
                        pnl = (entry_price - current_price) * 0.01
                        exit_reason = "TP"
                    elif current_price >= entry_price * (1 + sl_rate):
                        pnl = (entry_price - current_price) * 0.01
                        exit_reason = "SL"

                if exit_reason and entry_regime in regime_trades:
                    regime_trades[entry_regime].append(pnl)
                    position = None

            # 新規エントリー
            if not position:
                try:
                    # 戦略はDataFrameを期待し、最後の行を分析する
                    df_slice = self.df_with_features.iloc[: idx + 1]
                    decision = strategy.analyze(df_slice)
                    if decision.action in [EntryAction.BUY, EntryAction.SELL]:
                        position = "long" if decision.action == EntryAction.BUY else "short"
                        entry_price = current_price
                        entry_regime = regime_key
                except Exception:
                    pass

        # 統計計算
        result = {}
        for regime, pnls in regime_trades.items():
            if pnls:
                wins = [p for p in pnls if p > 0]
                result[regime] = {
                    "trades": len(pnls),
                    "win_rate": (len(wins) / len(pnls) * 100) if pnls else 0,
                    "total_pnl": sum(pnls),
                    "avg_pnl": np.mean(pnls),
                }
            else:
                result[regime] = {"trades": 0, "win_rate": 0, "total_pnl": 0, "avg_pnl": 0}

        return result

    def _analyze_hourly_performance(self, trades: List[Dict]) -> Dict[str, Any]:
        """時間帯別パフォーマンス分析"""
        hourly: Dict[int, List[float]] = {h: [] for h in range(24)}

        for trade in trades:
            hour = trade.get("hour", 0)
            if 0 <= hour < 24:
                hourly[hour].append(trade["pnl"])

        performance = {}
        for hour, pnls in hourly.items():
            if pnls:
                wins = [p for p in pnls if p > 0]
                performance[hour] = {
                    "trades": len(pnls),
                    "win_rate": (len(wins) / len(pnls) * 100) if pnls else 0,
                    "total_pnl": sum(pnls),
                }
            else:
                performance[hour] = {"trades": 0, "win_rate": 0, "total_pnl": 0}

        # ベスト/ワースト時間帯
        sorted_hours = sorted(
            [(h, p["total_pnl"]) for h, p in performance.items() if p["trades"] > 0],
            key=lambda x: x[1],
            reverse=True,
        )
        best_hours = [h for h, _ in sorted_hours[:3]] if sorted_hours else []
        worst_hours = [h for h, _ in sorted_hours[-3:]] if sorted_hours else []

        return {"performance": performance, "best_hours": best_hours, "worst_hours": worst_hours}

    def _analyze_consecutive_results(self, trades: List[Dict]) -> Dict[str, int]:
        """連敗・連勝分析"""
        if not trades:
            return {"max_losses": 0, "max_wins": 0}

        max_losses = 0
        max_wins = 0
        current_losses = 0
        current_wins = 0

        for trade in trades:
            if trade["pnl"] > 0:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)

        return {"max_losses": max_losses, "max_wins": max_wins}

    def _calculate_correlation(self) -> None:
        """戦略間相関分析"""
        if len(self.strategy_metrics) < 2:
            return

        # シグナル配列を構築
        signals = {}
        # 最低100行から開始（指標計算に必要）
        min_start = min(100, len(self.df_with_features) - 1)
        sample_size = min(500, len(self.df_with_features) - min_start)
        sample_indices = np.linspace(
            min_start, len(self.df_with_features) - 1, sample_size, dtype=int
        )

        for name, strategy in self.strategies.items():
            signal_array = []
            for idx in sample_indices:
                # 戦略はDataFrameを期待し、最後の行を分析する
                df_slice = self.df_with_features.iloc[: idx + 1]
                try:
                    decision = strategy.analyze(df_slice)
                    if decision.action == EntryAction.BUY:
                        signal_array.append(1)
                    elif decision.action == EntryAction.SELL:
                        signal_array.append(-1)
                    else:
                        signal_array.append(0)
                except Exception:
                    signal_array.append(0)
            signals[name] = signal_array

        # 相関係数計算
        names = list(signals.keys())
        for metrics in self.strategy_metrics:
            for other_name in names:
                if other_name != metrics.strategy_name:
                    if metrics.strategy_name in signals and other_name in signals:
                        corr = np.corrcoef(signals[metrics.strategy_name], signals[other_name])[
                            0, 1
                        ]
                        metrics.correlation_with_others[other_name] = float(corr)

    def _measure_ensemble_contribution(self) -> None:
        """アンサンブル貢献度測定"""
        # 簡易版: 各戦略のPFベースで貢献度を計算
        total_pf = sum(m.profit_factor for m in self.strategy_metrics)
        for metrics in self.strategy_metrics:
            if total_pf > 0:
                metrics.ensemble_contribution = (metrics.profit_factor / total_pf) * 100

    def _calculate_overall_score(self, metrics: StrategyMetrics) -> float:
        """総合スコア計算（0-100）"""
        score = 0

        # PFベース（40点）
        if metrics.profit_factor >= 1.5:
            score += 40
        elif metrics.profit_factor >= 1.2:
            score += 30
        elif metrics.profit_factor >= 1.0:
            score += 20
        elif metrics.profit_factor >= 0.9:
            score += 10

        # 勝率ベース（30点）
        if metrics.win_rate >= 60:
            score += 30
        elif metrics.win_rate >= 55:
            score += 25
        elif metrics.win_rate >= 50:
            score += 15

        # 取引数ベース（20点）
        if metrics.total_trades >= 100:
            score += 20
        elif metrics.total_trades >= 50:
            score += 15
        elif metrics.total_trades >= 20:
            score += 10

        # HOLD率ベース（10点）
        if metrics.hold_rate <= 80:
            score += 10
        elif metrics.hold_rate <= 90:
            score += 5

        return score

    def _generate_suggestions(self, metrics: StrategyMetrics) -> List[str]:
        """改善提案生成"""
        suggestions = []

        if metrics.profit_factor < 1.0:
            suggestions.append(f"PFが{metrics.profit_factor:.2f}で赤字。閾値調整を検討")

        if metrics.hold_rate > 95:
            suggestions.append(f"HOLD率{metrics.hold_rate:.1f}%が高すぎる。閾値緩和を検討")

        if metrics.win_rate < 50 and metrics.total_trades > 10:
            suggestions.append(f"勝率{metrics.win_rate:.1f}%が低い。エントリー条件の見直しを")

        if metrics.max_consecutive_losses > 5:
            suggestions.append(f"最大連敗{metrics.max_consecutive_losses}回。リスク管理強化を")

        return suggestions

    # ========================================================================
    # Phase 3: 削除候補特定
    # ========================================================================

    def _identify_deletion_candidates(self) -> None:
        """削除候補戦略の特定"""
        for metrics in self.strategy_metrics:
            reasons = []

            # 基準1: PF < 0.9（赤字戦略）
            if metrics.profit_factor < 0.9:
                reasons.append(f"PF {metrics.profit_factor:.2f} < 0.9")

            # 基準2: 全レジームで勝率 < 50%
            all_low_win = all(
                rp.get("win_rate", 0) < 50
                for rp in metrics.regime_performance.values()
                if rp.get("trades", 0) > 0
            )
            if all_low_win and metrics.regime_performance:
                reasons.append("全レジームで勝率<50%")

            # 基準3: 他戦略と高相関（>0.7）
            high_corr = [
                (name, corr) for name, corr in metrics.correlation_with_others.items() if corr > 0.7
            ]
            if high_corr:
                for name, corr in high_corr:
                    reasons.append(f"{name}と高相関({corr:.2f})")

            metrics.deletion_reasons = reasons

    # ========================================================================
    # Phase 3b: 理論分析（設定ベース）
    # ========================================================================

    def run_theoretical_analysis(self) -> TheoreticalResult:
        """設定ファイルベースの理論分析"""
        print("\n📊 理論分析開始...")

        # 戦略情報取得
        from src.strategies.strategy_loader import StrategyLoader

        loader = StrategyLoader()
        strategies_data = loader.load_strategies()

        strategies = [s["metadata"]["name"] for s in strategies_data]
        strategy_types = {
            s["metadata"]["name"]: s.get("regime_affinity", "both") for s in strategies_data
        }

        print(f"   ✅ {len(strategies)}戦略を取得")

        # レジーム別重み取得
        regime_weights = self._get_regime_weights()
        print("   ✅ レジーム別重みを取得")

        # レジームカバレッジ分析
        coverage = self._analyze_regime_coverage(regime_weights)
        print("   ✅ レジームカバレッジ分析完了")

        # 冗長性分析
        redundant = self._identify_theoretical_redundancy(strategies, strategy_types, coverage)
        print(f"   ✅ 冗長性分析完了: {len(redundant)}件検出")

        # 削除推奨生成
        deletion_candidates, remaining = self._generate_theoretical_recommendation(
            strategies, redundant
        )
        print(f"   ✅ 削除候補: {len(deletion_candidates)}戦略")

        return TheoreticalResult(
            analysis_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            strategies=strategies,
            strategy_types=strategy_types,
            regime_weights=regime_weights,
            regime_coverage=coverage,
            redundant_strategies=redundant,
            deletion_candidates=deletion_candidates,
            remaining_strategies=remaining,
        )

    def _get_regime_weights(self) -> Dict[str, Dict[str, float]]:
        """レジーム別戦略重みを取得"""
        regime_weights = {}
        for regime in [
            RegimeType.TIGHT_RANGE,
            RegimeType.NORMAL_RANGE,
            RegimeType.TRENDING,
            RegimeType.HIGH_VOLATILITY,
        ]:
            weights = get_threshold(
                f"dynamic_strategy_selection.regime_strategy_mapping.{regime.value}",
                {},
            )
            regime_weights[regime.value] = weights
        return regime_weights

    def _analyze_regime_coverage(
        self, regime_weights: Dict[str, Dict[str, float]]
    ) -> Dict[str, Dict[str, Any]]:
        """レジーム別の戦略カバレッジ分析"""
        coverage = {}
        for regime, weights in regime_weights.items():
            active_strategies = [s for s, w in weights.items() if w > 0]
            coverage[regime] = {
                "active_count": len(active_strategies),
                "active_strategies": active_strategies,
                "weights": weights,
            }
        return coverage

    def _identify_theoretical_redundancy(
        self,
        strategies: List[str],
        strategy_types: Dict[str, str],
        coverage: Dict[str, Dict[str, Any]],
    ) -> List[Dict[str, str]]:
        """理論的冗長性を特定"""
        redundant = []

        # 基準1: 全レジームで重みが0の戦略
        for strategy in strategies:
            used_count = sum(
                1
                for regime_data in coverage.values()
                if strategy in regime_data["active_strategies"]
            )
            if used_count == 0:
                redundant.append(
                    {
                        "strategy": strategy,
                        "reason": "全レジームで重み0（未使用）",
                        "severity": "high",
                    }
                )

        # 基準2: 使用頻度が極めて低い戦略（1レジームのみ）
        for strategy in strategies:
            used_count = sum(
                1
                for regime_data in coverage.values()
                if strategy in regime_data["active_strategies"]
            )
            if 0 < used_count <= 1:
                redundant.append(
                    {
                        "strategy": strategy,
                        "reason": f"使用レジーム数が少ない（{used_count}/4レジーム）",
                        "severity": "medium",
                    }
                )

        # 基準3: 同じタイプの戦略が複数存在（トレンド型3つ以上）
        trend_strategies = [s for s, t in strategy_types.items() if t == "trend"]
        if len(trend_strategies) >= 3:
            trend_usage = {}
            for strategy in trend_strategies:
                total_weight = sum(data["weights"].get(strategy, 0) for data in coverage.values())
                trend_usage[strategy] = total_weight
            min_weight_strategy = min(trend_usage, key=trend_usage.get)
            if trend_usage[min_weight_strategy] < 0.5:
                redundant.append(
                    {
                        "strategy": min_weight_strategy,
                        "reason": f"トレンド型で最も使用頻度が低い（合計重み: {trend_usage[min_weight_strategy]:.2f}）",
                        "severity": "medium",
                    }
                )

        return redundant

    def _generate_theoretical_recommendation(
        self, strategies: List[str], redundant: List[Dict[str, str]]
    ) -> Tuple[List[Dict[str, str]], List[str]]:
        """削除推奨リスト生成"""
        sorted_redundant = sorted(redundant, key=lambda x: 0 if x["severity"] == "high" else 1)
        deletion_candidates = (
            sorted_redundant[:4] if len(sorted_redundant) >= 4 else sorted_redundant
        )
        remaining = [s for s in strategies if s not in [c["strategy"] for c in deletion_candidates]]
        return deletion_candidates, remaining

    def print_theoretical_report(self, result: TheoreticalResult) -> None:
        """理論分析レポート出力"""
        print("\n" + "=" * 80)
        print("📊 理論分析レポート（設定ベース）")
        print("=" * 80)

        print(f"\n📅 分析日時: {result.analysis_date}")

        # 戦略一覧
        print("\n" + "-" * 40)
        print("📋 現行戦略")
        print("-" * 40)
        for strategy in result.strategies:
            stype = result.strategy_types.get(strategy, "unknown")
            print(f"  - {strategy}: {stype}型")

        # レジーム別カバレッジ
        print("\n" + "-" * 40)
        print("🎯 レジーム別戦略カバレッジ")
        print("-" * 40)
        for regime, data in result.regime_coverage.items():
            print(f"  {regime}:")
            print(f"    有効戦略数: {data['active_count']}戦略")
            if data["active_strategies"]:
                for strategy in data["active_strategies"]:
                    weight = data["weights"].get(strategy, 0)
                    print(f"      - {strategy}: {weight:.0%}")
            else:
                print("      - なし（全戦略無効化）")

        # 冗長性分析
        print("\n" + "-" * 40)
        print("🔍 冗長性分析")
        print("-" * 40)
        if result.redundant_strategies:
            for item in result.redundant_strategies:
                severity_mark = "⚠️" if item["severity"] == "high" else "📋"
                print(f"  {severity_mark} {item['strategy']}: {item['reason']}")
        else:
            print("  ✅ 冗長な戦略なし")

        # 削除推奨
        print("\n" + "-" * 40)
        print("🗑️ 削除候補")
        print("-" * 40)
        if result.deletion_candidates:
            for i, candidate in enumerate(result.deletion_candidates, 1):
                print(f"  {i}. {candidate['strategy']}")
                print(f"     理由: {candidate['reason']}")
                print(f"     重要度: {candidate['severity']}")
        else:
            print("  ✅ 削除推奨戦略なし")

        # 残存戦略
        print("\n" + "-" * 40)
        print("✅ 削除後の残存戦略")
        print("-" * 40)
        if result.remaining_strategies:
            print(f"  残存戦略数: {len(result.remaining_strategies)}戦略")
            for strategy in result.remaining_strategies:
                stype = result.strategy_types.get(strategy, "unknown")
                print(f"    - {strategy} ({stype}型)")

        print("\n" + "=" * 80)

    # ========================================================================
    # Phase 4: レポート出力
    # ========================================================================

    def generate_result(self, days: int, mode: str) -> AnalysisResult:
        """分析結果オブジェクト生成"""
        deletion_candidates = [m.strategy_name for m in self.strategy_metrics if m.deletion_reasons]

        recommendations = []
        if deletion_candidates:
            recommendations.append(f"削除候補: {', '.join(deletion_candidates)}")

        best_strategy = max(self.strategy_metrics, key=lambda m: m.overall_score)
        recommendations.append(
            f"最優秀戦略: {best_strategy.strategy_name} (スコア: {best_strategy.overall_score})"
        )

        return AnalysisResult(
            analysis_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            analysis_days=days,
            mode=mode,
            total_data_points=(
                len(self.df_with_features) if self.df_with_features is not None else 0
            ),
            regime_stats=self.regime_stats,
            strategy_metrics=self.strategy_metrics,
            deletion_candidates=deletion_candidates,
            overall_recommendations=recommendations,
        )

    def print_console_report(self, result: AnalysisResult) -> None:
        """コンソールレポート出力"""
        print("\n" + "=" * 80)
        print("📊 統合戦略分析レポート")
        print("=" * 80)

        print(f"\n📅 分析日時: {result.analysis_date}")
        print(f"📆 分析期間: {result.analysis_days}日")
        print(f"🔧 分析モード: {result.mode}")
        print(f"📈 データポイント: {result.total_data_points:,}")

        # レジーム分布
        print("\n" + "-" * 40)
        print("📊 レジーム分布")
        print("-" * 40)
        rs = result.regime_stats
        print(f"  tight_range:     {rs.tight_range_count:5,} ({rs.tight_range_pct:5.1f}%)")
        print(f"  normal_range:    {rs.normal_range_count:5,} ({rs.normal_range_pct:5.1f}%)")
        print(f"  trending:        {rs.trending_count:5,} ({rs.trending_pct:5.1f}%)")
        print(f"  high_volatility: {rs.high_volatility_count:5,} ({rs.high_volatility_pct:5.1f}%)")
        print(
            f"  レンジ合計:      {rs.tight_range_count + rs.normal_range_count:5,} ({rs.range_total_pct:5.1f}%)"
        )

        # 戦略別パフォーマンス
        print("\n" + "-" * 40)
        print("📈 戦略別パフォーマンス")
        print("-" * 40)
        print(f"{'戦略':<20} {'取引数':>6} {'勝率':>7} {'PF':>6} {'損益':>10} {'スコア':>6}")
        print("-" * 60)

        for m in sorted(self.strategy_metrics, key=lambda x: x.overall_score, reverse=True):
            pnl_str = f"+{m.total_pnl:,.0f}" if m.total_pnl >= 0 else f"{m.total_pnl:,.0f}"
            status = "✅" if m.profit_factor >= 1.0 else "❌"
            print(
                f"{status} {m.strategy_name:<17} {m.total_trades:>6} {m.win_rate:>6.1f}% "
                f"{m.profit_factor:>5.2f} {pnl_str:>10}円 {m.overall_score:>5.0f}"
            )

        # 削除候補
        if result.deletion_candidates:
            print("\n" + "-" * 40)
            print("⚠️ 削除候補戦略")
            print("-" * 40)
            for m in self.strategy_metrics:
                if m.deletion_reasons:
                    print(f"  {m.strategy_name}:")
                    for reason in m.deletion_reasons:
                        print(f"    - {reason}")

        # 推奨事項
        print("\n" + "-" * 40)
        print("💡 推奨事項")
        print("-" * 40)
        for rec in result.overall_recommendations:
            print(f"  • {rec}")

        print("\n" + "=" * 80)

    def export_json(self, result: AnalysisResult, output_dir: Path) -> Path:
        """JSON形式で出力"""
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"strategy_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = output_dir / filename

        # dataclassをdictに変換
        data = {
            "analysis_date": result.analysis_date,
            "analysis_days": result.analysis_days,
            "mode": result.mode,
            "total_data_points": result.total_data_points,
            "regime_stats": {
                "total_rows": result.regime_stats.total_rows,
                "tight_range": {
                    "count": result.regime_stats.tight_range_count,
                    "pct": result.regime_stats.tight_range_pct,
                },
                "normal_range": {
                    "count": result.regime_stats.normal_range_count,
                    "pct": result.regime_stats.normal_range_pct,
                },
                "trending": {
                    "count": result.regime_stats.trending_count,
                    "pct": result.regime_stats.trending_pct,
                },
                "high_volatility": {
                    "count": result.regime_stats.high_volatility_count,
                    "pct": result.regime_stats.high_volatility_pct,
                },
            },
            "strategies": [
                {
                    "name": m.strategy_name,
                    "total_trades": m.total_trades,
                    "win_rate": m.win_rate,
                    "profit_factor": m.profit_factor,
                    "total_pnl": m.total_pnl,
                    "sharpe_ratio": m.sharpe_ratio,
                    "max_drawdown": m.max_drawdown,
                    "overall_score": m.overall_score,
                    "regime_performance": m.regime_performance,
                    "deletion_reasons": m.deletion_reasons,
                    "improvement_suggestions": m.improvement_suggestions,
                }
                for m in result.strategy_metrics
            ],
            "deletion_candidates": result.deletion_candidates,
            "recommendations": result.overall_recommendations,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\n💾 JSON出力: {filepath}")
        return filepath

    def export_markdown(self, result: AnalysisResult, output_dir: Path) -> Path:
        """Markdown形式で出力"""
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"strategy_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        filepath = output_dir / filename

        lines = [
            f"# 戦略分析レポート - {result.analysis_date}",
            "",
            "## 1. サマリー",
            "",
            f"- **分析期間**: {result.analysis_days}日",
            f"- **分析モード**: {result.mode}",
            f"- **データポイント**: {result.total_data_points:,}",
            "",
            "## 2. レジーム分布",
            "",
            "| レジーム | 件数 | 割合 |",
            "|----------|------|------|",
        ]

        rs = result.regime_stats
        lines.extend(
            [
                f"| tight_range | {rs.tight_range_count:,} | {rs.tight_range_pct:.1f}% |",
                f"| normal_range | {rs.normal_range_count:,} | {rs.normal_range_pct:.1f}% |",
                f"| trending | {rs.trending_count:,} | {rs.trending_pct:.1f}% |",
                f"| high_volatility | {rs.high_volatility_count:,} | {rs.high_volatility_pct:.1f}% |",
                "",
                "## 3. 戦略別パフォーマンス",
                "",
                "| 戦略 | 取引数 | 勝率 | PF | 損益 | スコア | 評価 |",
                "|------|--------|------|-----|------|--------|------|",
            ]
        )

        for m in sorted(result.strategy_metrics, key=lambda x: x.overall_score, reverse=True):
            pnl_str = f"+{m.total_pnl:,.0f}" if m.total_pnl >= 0 else f"{m.total_pnl:,.0f}"
            status = "✅" if m.profit_factor >= 1.0 else "❌"
            lines.append(
                f"| {m.strategy_name} | {m.total_trades} | {m.win_rate:.1f}% | "
                f"{m.profit_factor:.2f} | {pnl_str}円 | {m.overall_score:.0f} | {status} |"
            )

        if result.deletion_candidates:
            lines.extend(
                [
                    "",
                    "## 4. 削除候補",
                    "",
                ]
            )
            for m in result.strategy_metrics:
                if m.deletion_reasons:
                    lines.append(f"### {m.strategy_name}")
                    for reason in m.deletion_reasons:
                        lines.append(f"- {reason}")
                    lines.append("")

        lines.extend(
            [
                "",
                "## 5. 推奨事項",
                "",
            ]
        )
        for rec in result.overall_recommendations:
            lines.append(f"- {rec}")

        lines.extend(
            [
                "",
                "---",
                f"*Generated by unified_strategy_analyzer.py at {result.analysis_date}*",
            ]
        )

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        print(f"💾 Markdown出力: {filepath}")
        return filepath


# ============================================================================
# メイン処理
# ============================================================================


async def main():
    parser = argparse.ArgumentParser(
        description="統合戦略分析スクリプト",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python scripts/analysis/unified_strategy_analyzer.py --mode theoretical       # 理論分析（数秒）
  python scripts/analysis/unified_strategy_analyzer.py --mode quick             # 簡易実証（30秒）
  python scripts/analysis/unified_strategy_analyzer.py --mode full              # 完全実証（3分）
  python scripts/analysis/unified_strategy_analyzer.py --days 60 --strategy ATRBased
  python scripts/analysis/unified_strategy_analyzer.py --days 60 --export ./output --format all
        """,
    )
    parser.add_argument("--days", type=int, default=60, help="分析日数（デフォルト: 60）")
    parser.add_argument("--strategy", type=str, default=None, help="特定戦略のみ分析")
    parser.add_argument(
        "--mode",
        type=str,
        default="full",
        choices=["theoretical", "quick", "full", "regime-only"],
        help="分析モード（theoretical/quick/full/regime-only）",
    )
    parser.add_argument("--export", type=str, default=None, help="出力ディレクトリ")
    parser.add_argument(
        "--format",
        type=str,
        default="all",
        help="出力形式（console,json,md,all）",
    )
    parser.add_argument("--verbose", action="store_true", help="詳細ログ出力")

    args = parser.parse_args()

    print("=" * 80)
    print("🔍 統合戦略分析スクリプト v2.0")
    print("=" * 80)

    try:
        analyzer = UnifiedStrategyAnalyzer(verbose=args.verbose)

        if args.mode == "theoretical":
            # 理論分析モード（設定ファイルベース、データ不要）
            result = analyzer.run_theoretical_analysis()
            analyzer.print_theoretical_report(result)
        elif args.mode == "regime-only":
            # レジーム分類のみの場合
            await analyzer.load_data(days=args.days)
            analyzer.classify_regimes()
            result = analyzer.generate_result(args.days, args.mode)
            analyzer.print_console_report(result)
        else:
            # Phase 1: データ準備
            await analyzer.load_data(days=args.days)
            analyzer.classify_regimes()

            # Phase 2: 戦略評価
            analyzer.load_strategies(target_strategy=args.strategy)
            await analyzer.evaluate_strategies(mode=args.mode)

            # Phase 3: レポート出力
            result = analyzer.generate_result(args.days, args.mode)

            formats = args.format.lower().split(",")
            if "all" in formats:
                formats = ["console", "json", "md"]

            if "console" in formats:
                analyzer.print_console_report(result)

            if args.export:
                output_dir = Path(args.export)
                if "json" in formats:
                    analyzer.export_json(result, output_dir)
                if "md" in formats:
                    analyzer.export_markdown(result, output_dir)

        print("\n✅ 分析完了")

    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
