"""
戦略マネージャー実装 - 複数戦略の統合管理

5つの戦略を統合し、シグナルの優先度付けと
最適な戦略選択を行う管理システム。

主要機能:
- 複数戦略の同時実行
- シグナル統合とコンフリクト解決
- 戦略パフォーマンス追跡
- 動的戦略重み付け

Phase 21完了: 2025年9月12日.
"""

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ...core.config import get_threshold
from ...core.exceptions import StrategyError
from ...core.logger import get_logger
from .strategy_base import StrategyBase, StrategySignal


class StrategyManager:
    """
    戦略統合管理クラス

    複数の取引戦略を統合し、最適なシグナル選択と
    リスク管理を行う。.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        戦略マネージャーの初期化

        Args:
            config: 管理設定辞書.
        """
        self.config = config or {}
        self.logger = get_logger()

        # 戦略管理
        self.strategies: Dict[str, StrategyBase] = {}
        self.strategy_weights: Dict[str, float] = {}

        # 統合シグナル管理
        self.last_combined_signal: Optional[StrategySignal] = None
        self.signal_conflicts = 0

        # 基本統計（簡素化）
        self.total_decisions = 0

        self.logger.info("戦略マネージャー初期化完了")

    def register_strategy(self, strategy: StrategyBase, weight: float = 1.0) -> None:
        """
        戦略を登録

        Args:
            strategy: 登録する戦略
            weight: 戦略の重み (0.0-1.0).
        """
        if not isinstance(strategy, StrategyBase):
            raise StrategyError("StrategyBaseを継承した戦略を登録してください")

        if weight < 0 or weight > 1:
            raise StrategyError("戦略重みは0.0-1.0の範囲で指定してください")

        self.strategies[strategy.name] = strategy
        self.strategy_weights[strategy.name] = weight

        self.logger.info(f"戦略登録: {strategy.name} (重み: {weight})")

    def unregister_strategy(self, strategy_name: str) -> None:
        """戦略の登録解除."""
        if strategy_name in self.strategies:
            del self.strategies[strategy_name]
            del self.strategy_weights[strategy_name]
            self.logger.info(f"戦略登録解除: {strategy_name}")
        else:
            self.logger.warning(f"未登録戦略の解除試行: {strategy_name}")

    def analyze_market(
        self, df: pd.DataFrame, multi_timeframe_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> StrategySignal:
        """
        全戦略を実行して統合シグナルを生成

        Args:
            df: 市場データ（メインタイムフレーム）
            multi_timeframe_data: マルチタイムフレームデータ（Phase 31対応）

        Returns:
            統合された最終シグナル.
        """
        try:
            self.logger.debug("市場分析開始 - 全戦略実行")

            # 全戦略からシグナル取得（Phase 31: multi_timeframe_data渡し）
            strategy_signals = self._collect_all_signals(df, multi_timeframe_data)

            # シグナル統合
            combined_signal = self._combine_signals(strategy_signals, df)

            # 統合結果記録
            self._record_decision(strategy_signals, combined_signal)

            self.logger.info(
                f"統合シグナル生成: {combined_signal.action} (信頼度: {combined_signal.confidence:.3f})"
            )

            return combined_signal

        except Exception as e:
            # Phase 35: バックテストモード時はDEBUGレベル（環境変数直接チェック）
            import os

            if os.environ.get("BACKTEST_MODE") == "true":
                self.logger.debug(f"市場分析エラー: {e}")
            else:
                self.logger.error(f"市場分析エラー: {e}")
            raise StrategyError(f"統合分析失敗: {e}")

    def _collect_all_signals(
        self, df: pd.DataFrame, multi_timeframe_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> Dict[str, StrategySignal]:
        """全戦略からシグナルを収集."""
        signals = {}
        errors = []

        self.logger.debug(f"戦略シグナル収集開始: {len(self.strategies)}戦略登録済み")
        for name, strategy in self.strategies.items():
            self.logger.debug(f"戦略チェック: {name}, is_enabled={strategy.is_enabled}")
            if not strategy.is_enabled:
                self.logger.debug(f"戦略スキップ（無効）: {name}")
                continue

            try:
                self.logger.debug(f"[{name}] シグナル生成開始 - データシェイプ: {df.shape}")
                self.logger.debug(f"[{name}] 利用可能な列: {list(df.columns)}")

                # Phase 31: multi_timeframe_dataを渡す
                signal = strategy.generate_signal(df, multi_timeframe_data=multi_timeframe_data)
                signals[name] = signal
                self.logger.info(
                    f"[{name}] シグナル取得成功: {signal.action} ({signal.confidence:.3f})"
                )

            except Exception as e:
                error_msg = f"[{name}] シグナル生成エラー: {type(e).__name__}: {e}"
                # Phase 35: バックテストモード時はDEBUGレベル（環境変数直接チェック）
                import os

                if os.environ.get("BACKTEST_MODE") == "true":
                    self.logger.debug(error_msg)
                    self.logger.debug(f"[{name}] 必要特徴量: {strategy.get_required_features()}")
                else:
                    self.logger.error(error_msg)
                    self.logger.error(f"[{name}] 必要特徴量: {strategy.get_required_features()}")
                errors.append(error_msg)

        if not signals and errors:
            raise StrategyError(f"全戦略でエラー発生: {'; '.join(errors)}")

        self.logger.debug(f"シグナル収集完了: {len(signals)}戦略")
        return signals

    def _combine_signals(
        self, signals: Dict[str, StrategySignal], df: pd.DataFrame
    ) -> StrategySignal:
        """シグナルを統合して最終決定を生成."""
        if not signals:
            return self._create_hold_signal(df)

        # シグナルタイプ別グループ化
        signal_groups = self._group_signals_by_action(signals)

        # コンフリクト検出
        if self._has_signal_conflict(signal_groups):
            self.signal_conflicts += 1
            return self._resolve_signal_conflict(signal_groups, signals, df)

        # 統合ロジック実行
        return self._integrate_consistent_signals(signal_groups, signals, df)

    def _group_signals_by_action(
        self, signals: Dict[str, StrategySignal]
    ) -> Dict[str, List[Tuple[str, StrategySignal]]]:
        """シグナルをアクション別にグループ化."""
        groups = defaultdict(list)

        for strategy_name, signal in signals.items():
            groups[signal.action].append((strategy_name, signal))

        return dict(groups)

    def _has_signal_conflict(self, signal_groups: Dict[str, List]) -> bool:
        """シグナルコンフリクトの検出."""
        # buy と sell が同時にある場合はコンフリクト
        has_buy = "buy" in signal_groups and len(signal_groups["buy"]) > 0
        has_sell = "sell" in signal_groups and len(signal_groups["sell"]) > 0

        return has_buy and has_sell

    def _resolve_signal_conflict(
        self,
        signal_groups: Dict[str, List],
        all_signals: Dict[str, StrategySignal],
        df: pd.DataFrame,
    ) -> StrategySignal:
        """シグナルコンフリクトの解決."""
        # Phase 35.5: バックテストモードではログ抑制（不要なI/Oオーバーヘッド削減）
        import os

        is_backtest = os.environ.get("BACKTEST_MODE") == "true"

        if not is_backtest:  # Phase 35.5: バックテストモード時はログ出力しない
            self.logger.warning("シグナルコンフリクト検出 - 解決処理開始")

        # 解決方法1: 信頼度ベースの選択
        buy_signals = signal_groups.get("buy", [])
        sell_signals = signal_groups.get("sell", [])

        # 各グループの重み付け信頼度計算
        buy_weighted_confidence = self._calculate_weighted_confidence(buy_signals)
        sell_weighted_confidence = self._calculate_weighted_confidence(sell_signals)

        self.logger.debug(
            f"コンフリクト解決: BUY={buy_weighted_confidence:.3f} vs SELL={sell_weighted_confidence:.3f}"
        )

        # 差が小さい場合はホールド
        min_conflict_threshold = self.config.get("min_conflict_threshold", 0.1)
        if abs(buy_weighted_confidence - sell_weighted_confidence) < min_conflict_threshold:
            self.logger.info("コンフリクト解決: 差が小さいためホールド選択")
            return self._create_hold_signal(df, reason="信頼度差が小さいためコンフリクト回避")

        # より高い信頼度のグループを選択
        if buy_weighted_confidence > sell_weighted_confidence:
            winning_group = buy_signals
            action = "buy"
            confidence = buy_weighted_confidence
        else:
            winning_group = sell_signals
            action = "sell"
            confidence = sell_weighted_confidence

        self.logger.info(f"コンフリクト解決: {action.upper()}選択 (信頼度: {confidence:.3f})")

        # 勝利グループから最も信頼度の高いシグナルをベースに統合
        best_signal = max(winning_group, key=lambda x: x[1].confidence)[1]

        return StrategySignal(
            strategy_name="StrategyManager",
            timestamp=datetime.now(),
            action=action,
            confidence=confidence,
            strength=best_signal.strength,
            current_price=best_signal.current_price,
            entry_price=best_signal.entry_price,
            stop_loss=best_signal.stop_loss,
            take_profit=best_signal.take_profit,
            position_size=best_signal.position_size,
            risk_ratio=best_signal.risk_ratio,
            reason=f"コンフリクト解決 - {len(winning_group)}戦略の統合結果",
            metadata={
                "conflict_resolved": True,
                "competing_signals": len(buy_signals) + len(sell_signals),
                "resolution_method": "weighted_confidence",
            },
        )

    def _integrate_consistent_signals(
        self,
        signal_groups: Dict[str, List],
        all_signals: Dict[str, StrategySignal],
        df: pd.DataFrame,
    ) -> StrategySignal:
        """一貫したシグナルの統合."""
        # 最も多いアクションを選択
        action_counts = {action: len(signals) for action, signals in signal_groups.items()}
        dominant_action = max(action_counts, key=action_counts.get)

        if dominant_action == "hold":
            return self._create_hold_signal(df, reason=f"{action_counts['hold']}戦略がホールド推奨")

        # 同じアクションのシグナルを統合
        same_action_signals = signal_groups[dominant_action]

        # 重み付け信頼度計算
        weighted_confidence = self._calculate_weighted_confidence(same_action_signals)

        # 最も信頼度の高いシグナルをベースとして使用
        best_signal = max(same_action_signals, key=lambda x: x[1].confidence)[1]

        # 統合シグナル生成
        return StrategySignal(
            strategy_name="StrategyManager",
            timestamp=datetime.now(),
            action=dominant_action,
            confidence=weighted_confidence,
            strength=np.mean([s[1].strength for s in same_action_signals]),
            current_price=best_signal.current_price,
            entry_price=best_signal.entry_price,
            stop_loss=best_signal.stop_loss,
            take_profit=best_signal.take_profit,
            position_size=best_signal.position_size,
            risk_ratio=best_signal.risk_ratio,
            reason=f"{len(same_action_signals)}戦略の統合結果",
            metadata={
                "contributing_strategies": [s[0] for s in same_action_signals],
                "individual_confidences": [s[1].confidence for s in same_action_signals],
                "integration_method": "weighted_average",
            },
        )

    def _calculate_weighted_confidence(self, signals: List[Tuple[str, StrategySignal]]) -> float:
        """重み付け信頼度計算."""
        if not signals:
            return 0.0

        total_weighted_confidence = 0.0
        total_weight = 0.0

        for strategy_name, signal in signals:
            weight = self.strategy_weights.get(strategy_name, 1.0)
            weighted_confidence = signal.confidence * weight

            total_weighted_confidence += weighted_confidence
            total_weight += weight

        return total_weighted_confidence / total_weight if total_weight > 0 else 0.0

    def _create_hold_signal(self, df: pd.DataFrame, reason: str = "条件不適合") -> StrategySignal:
        """ホールドシグナル生成 - 動的confidence実装."""
        current_price = float(df["close"].iloc[-1]) if "close" in df.columns else 0.0

        # 動的confidence計算（攻撃的設定・市場状況反映）
        base_confidence = get_threshold("ml.dynamic_confidence.base_hold", 0.3)

        # 市場ボラティリティに応じた調整
        try:
            if len(df) >= 20 and "close" in df.columns:
                # 過去20期間のボラティリティ計算
                returns = df["close"].pct_change().tail(20)
                volatility = returns.std()

                # ボラティリティが高い = 取引機会多い = HOLD信頼度下げる（攻撃的）
                if volatility > 0.02:  # 高ボラティリティ
                    confidence = base_confidence * 0.8  # さらに下げる
                elif volatility < 0.005:  # 低ボラティリティ
                    confidence = base_confidence * 1.2  # 少し上げる
                else:
                    confidence = base_confidence
            else:
                confidence = base_confidence
        except Exception:
            # エラー時はフォールバック値
            confidence = get_threshold("ml.dynamic_confidence.error_fallback", 0.2)

        # 信頼度を0.1-0.8の範囲にクランプ
        confidence = max(0.1, min(0.8, confidence))

        return StrategySignal(
            strategy_name="StrategyManager",
            timestamp=datetime.now(),
            action="hold",
            confidence=confidence,  # 動的confidence
            strength=0.0,
            current_price=current_price,
            reason=f"{reason} (動的confidence: {confidence:.3f})",
        )

    def _record_decision(
        self,
        strategy_signals: Dict[str, StrategySignal],
        final_signal: StrategySignal,
    ) -> None:
        """決定記録 - 簡素化版."""
        self.total_decisions += 1
        self.last_combined_signal = final_signal

        # デバッグログのみ（履歴保存なし）
        self.logger.debug(
            f"決定記録: {len(strategy_signals)}戦略 → {final_signal.action} (信頼度: {final_signal.confidence:.3f})"
        )

    def get_strategy_performance(self) -> Dict[str, Any]:
        """戦略パフォーマンス取得."""
        return {
            name: {
                "stats": strategy.get_signal_stats(),
                "weight": self.strategy_weights[name],
                "enabled": strategy.is_enabled,
            }
            for name, strategy in self.strategies.items()
        }

    def get_manager_stats(self) -> Dict[str, Any]:
        """マネージャー統計情報取得 - 簡素化版."""
        return {
            "total_strategies": len(self.strategies),
            "enabled_strategies": sum(1 for s in self.strategies.values() if s.is_enabled),
            "total_decisions": self.total_decisions,
            "signal_conflicts": self.signal_conflicts,
            "strategy_weights": self.strategy_weights.copy(),
        }

    def update_strategy_weights(self, new_weights: Dict[str, float]) -> None:
        """戦略重み更新."""
        for name, weight in new_weights.items():
            if name not in self.strategies:
                self.logger.warning(f"未登録戦略: {name}")
                continue
            if not 0 <= weight <= 1:
                self.logger.warning(f"無効重み: {name}={weight}")
                continue

            self.strategy_weights[name] = weight
            self.logger.info(f"重み更新: {name}={weight}")

    def reset_stats(self) -> None:
        """統計情報リセット - 簡素化版."""
        self.last_combined_signal = None
        self.signal_conflicts = 0
        self.total_decisions = 0

        self.logger.info("統計情報リセット完了")
