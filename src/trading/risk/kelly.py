"""
Kelly基準ポジションサイジングシステム

Phase 28完了・取引実行結果管理統合システムの中核機能：
- Kelly基準による理論的最適ポジションサイズ計算
- 実用的な安全制約の適用
- 複数レベルフォールバック機能

設計思想:
- Kelly公式による動的ポジションサイジング
- 過去の取引実績から動的にKelly値を計算
- 安全係数適用（通常Kelly値の25-50%）
- ML予測信頼度の考慮
- 最大ポジション制限（3%）の厳守

Kelly公式: f = (bp - q) / b
- f: 最適ポジション比率
- b: 平均利益/平均損失の比率
- p: 勝率
- q: 敗率(1-p)
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from ...core.config import get_position_config, get_threshold
from ...core.logger import get_logger


@dataclass
class TradeResult:
    """取引結果記録用データクラス."""

    timestamp: datetime
    profit_loss: float
    is_win: bool
    strategy: str
    confidence: float


@dataclass
class KellyCalculationResult:
    """Kelly計算結果格納用データクラス."""

    kelly_fraction: float
    win_rate: float
    avg_win_loss_ratio: float
    safety_adjusted_fraction: float
    recommended_position_size: float
    sample_size: int
    confidence_level: float


class KellyCriterion:
    """
    Kelly基準によるポジションサイジング計算

    特徴:
    - 過去の取引実績から動的にKelly値を計算
    - 安全係数適用（通常Kelly値の25-50%）
    - ML予測信頼度の考慮
    - 最大ポジション制限（3%）の厳守
    """

    def __init__(
        self,
        max_position_ratio: float = None,
        safety_factor: float = None,
        min_trades_for_kelly: int = None,
    ):
        """
        Kelly基準計算器初期化（設定ファイルから動的取得）

        Args:
            max_position_ratio: 最大ポジション比率（Noneの場合は設定ファイルから取得）
            safety_factor: 安全係数（Noneの場合は設定ファイルから取得）
            min_trades_for_kelly: Kelly計算に必要な最小取引数（Noneの場合は設定ファイルから取得）
        """
        # 設定ファイルから動的取得（ハードコード排除）
        self.max_position_ratio = max_position_ratio or get_threshold(
            "risk.kelly_max_fraction", 0.03
        )
        self.safety_factor = safety_factor or get_threshold(
            "risk.kelly_criterion.safety_factor", 0.7
        )
        self.min_trades_for_kelly = min_trades_for_kelly or get_threshold(
            "trading.kelly_min_trades", 5
        )
        self.trade_history: List[TradeResult] = []
        self.logger = get_logger()

    def add_trade_result(
        self,
        profit_loss: float,
        strategy: str = "default",
        confidence: float = 0.5,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        取引結果をhistoryに追加

        Args:
            profit_loss: 損益（正値=利益、負値=損失）
            strategy: 戦略名
            confidence: 取引時の信頼度
            timestamp: 取引時刻（Noneの場合は現在時刻）
        """
        if timestamp is None:
            timestamp = datetime.now()

        trade_result = TradeResult(
            timestamp=timestamp,
            profit_loss=profit_loss,
            is_win=profit_loss > 0,
            strategy=strategy,
            confidence=confidence,
        )

        self.trade_history.append(trade_result)
        self.logger.debug(f"取引結果追加: P&L={profit_loss:.2f}, 勝利={trade_result.is_win}")

    def calculate_kelly_fraction(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """
        Kelly公式による最適ポジション比率計算

        Args:
            win_rate: 勝率（0.0-1.0）
            avg_win: 平均利益
            avg_loss: 平均損失（正値で入力）

        Returns:
            Kelly比率（0.0-1.0、負値の場合は0.0を返す）
        """
        try:
            if avg_loss <= 0 or win_rate <= 0 or win_rate >= 1:
                self.logger.warning(f"無効なパラメータ: win_rate={win_rate}, avg_loss={avg_loss}")
                return 0.0

            # Kelly公式: f = (bp - q) / b
            # b = 平均利益/平均損失, p = 勝率, q = 敗率
            b = avg_win / avg_loss
            p = win_rate
            q = 1 - win_rate

            kelly_f = (b * p - q) / b

            # 負のKelly値は0にクリップ（取引しない）
            kelly_f = max(0.0, kelly_f)

            # 理論上100%を超える場合は100%にクリップ
            kelly_f = min(1.0, kelly_f)

            self.logger.debug(f"Kelly計算: b={b:.3f}, p={p:.3f}, q={q:.3f}, f={kelly_f:.3f}")

            return kelly_f

        except Exception as e:
            self.logger.error(f"Kelly計算エラー: {e}")
            return 0.0

    def calculate_from_history(
        self,
        lookback_days: Optional[int] = None,
        strategy_filter: Optional[str] = None,
        reference_timestamp: Optional[datetime] = None,
    ) -> Optional[KellyCalculationResult]:
        """
        取引履歴からKelly値を計算

        Args:
            lookback_days: 遡る日数
            strategy_filter: 特定戦略のみでフィルタ（Noneで全戦略）
            reference_timestamp: 基準時刻（バックテスト用、Noneの場合は現在時刻）

        Returns:
            Kelly計算結果（データ不足の場合はNone）
        """
        try:
            # 設定からデフォルト値を取得
            if lookback_days is None:
                lookback_days = get_threshold("risk.kelly_lookback_days", 30)

            # 期間フィルタ（バックテストモードでは参照タイムスタンプを使用）
            base_time = reference_timestamp if reference_timestamp else datetime.now()
            cutoff_date = base_time - timedelta(days=lookback_days)
            filtered_trades = [
                trade for trade in self.trade_history if trade.timestamp >= cutoff_date
            ]

            # 戦略フィルタ
            if strategy_filter:
                filtered_trades = [
                    trade for trade in filtered_trades if trade.strategy == strategy_filter
                ]

            # 最小取引数チェック
            if len(filtered_trades) < self.min_trades_for_kelly:
                self.logger.debug(
                    f"Kelly計算に必要な取引数不足: {len(filtered_trades)} < {self.min_trades_for_kelly}"
                )
                return None

            # 統計計算
            wins = [trade.profit_loss for trade in filtered_trades if trade.is_win]
            losses = [abs(trade.profit_loss) for trade in filtered_trades if not trade.is_win]

            if not wins or not losses:
                self.logger.warning("勝ち取引または負け取引がありません")
                return None

            win_rate = len(wins) / len(filtered_trades)
            avg_win = sum(wins) / len(wins)
            avg_loss = sum(losses) / len(losses)

            # Kelly値計算
            kelly_fraction = self.calculate_kelly_fraction(win_rate, avg_win, avg_loss)

            # 安全係数適用
            safety_adjusted = kelly_fraction * self.safety_factor

            # 最大ポジション制限適用
            recommended_size = min(safety_adjusted, self.max_position_ratio)

            # 信頼度計算（サンプルサイズベース）
            confidence_level = min(1.0, len(filtered_trades) / (self.min_trades_for_kelly * 2))

            result = KellyCalculationResult(
                kelly_fraction=kelly_fraction,
                win_rate=win_rate,
                avg_win_loss_ratio=avg_win / avg_loss,
                safety_adjusted_fraction=safety_adjusted,
                recommended_position_size=recommended_size,
                sample_size=len(filtered_trades),
                confidence_level=confidence_level,
            )

            self.logger.info(
                f"Kelly計算完了: Kelly={kelly_fraction:.3f}, "
                f"調整後={safety_adjusted:.3f}, 推奨={recommended_size:.3f}, "
                f"勝率={win_rate:.1%}, サンプル={len(filtered_trades)}"
            )

            return result

        except Exception as e:
            self.logger.error(f"履歴からのKelly計算エラー: {e}")
            return None

    def calculate_optimal_size(
        self,
        ml_confidence: float,
        strategy_name: str = "default",
        expected_return: Optional[float] = None,
        reference_timestamp: Optional[datetime] = None,
    ) -> float:
        """
        ML予測信頼度を考慮した最適ポジションサイズ計算

        Args:
            ml_confidence: ML予測の信頼度（0.0-1.0）
            strategy_name: 戦略名
            expected_return: 期待リターン（Noneの場合は履歴ベース）
            reference_timestamp: 基準時刻（バックテスト用、Noneの場合は現在時刻）

        Returns:
            推奨ポジションサイズ（最大3%制限済み）
        """
        try:
            # 履歴ベースのKelly値取得
            kelly_result = self.calculate_from_history(
                strategy_filter=strategy_name,
                reference_timestamp=reference_timestamp,
            )

            if kelly_result is None:
                # Silent failure修正: Kelly履歴不足時は固定で最小取引単位使用
                # 最初の5取引は最小ロット（0.0001 BTC）で確実に取引実行
                min_trade_size = get_threshold("trading.min_trade_size", 0.0001)  # Bitbank最小単位
                trade_history_count = len(self.trade_history)

                if trade_history_count < self.min_trades_for_kelly:
                    # 最初の5取引は固定サイズ（Kelly適用前）
                    fixed_initial_size = min_trade_size

                    # max_order_size制限チェック
                    max_order_size = get_threshold("production.max_order_size", 0.02)
                    if fixed_initial_size > max_order_size:
                        fixed_initial_size = max_order_size
                        self.logger.warning(
                            f"初期固定サイズをmax_order_size制限: {fixed_initial_size:.6f} BTC"
                        )

                    self.logger.info(
                        f"Kelly履歴不足({trade_history_count}<{self.min_trades_for_kelly})"
                        f"、初期固定サイズ使用: {fixed_initial_size:.6f} BTC"
                    )
                    return fixed_initial_size
                else:
                    # 取引履歴があるがKelly計算エラーの場合
                    base_initial_size = get_threshold("trading.initial_position_size", 0.01)
                    conservative_size = max(base_initial_size * ml_confidence, min_trade_size)

                    # max_order_size制限チェック
                    max_order_size = get_threshold("production.max_order_size", 0.02)
                    if conservative_size > max_order_size:
                        self.logger.error(
                            f"ポジションサイズ制限超過検出: 計算値={conservative_size:.6f} > "
                            f"max_order_size={max_order_size:.6f} - 制限値適用"
                        )
                        conservative_size = max_order_size

                    self.logger.warning(
                        f"Kelly計算エラー、保守的サイズ使用: {conservative_size:.6f}"
                    )
                    return min(conservative_size, self.max_position_ratio)

            # ML信頼度による調整
            confidence_adjusted_size = kelly_result.recommended_position_size * ml_confidence

            # データ信頼度による調整
            data_confidence_adjusted = confidence_adjusted_size * kelly_result.confidence_level

            # 最終制限適用
            final_size = min(data_confidence_adjusted, self.max_position_ratio)

            # Silent failure対策: max_order_size制限チェック（Kelly履歴がある場合も）
            max_order_size = get_threshold("production.max_order_size", 0.02)
            if final_size > max_order_size:
                self.logger.error(
                    f"Kelly計算済みポジションサイズ制限超過: 計算値={final_size:.4f} > "
                    f"max_order_size={max_order_size:.4f} - Silent failure発生可能性"
                )
                final_size = min(final_size, max_order_size)

            self.logger.debug(
                f"最適サイズ計算: Kelly推奨={kelly_result.recommended_position_size:.3f}, "
                f"ML信頼度={ml_confidence:.3f}, 最終={final_size:.3f}"
            )

            return final_size

        except Exception as e:
            self.logger.error(f"最適サイズ計算エラー: {e}")
            # フォールバック値も設定から取得
            fallback_size = get_threshold("trading.initial_position_size", 0.01)
            return fallback_size

    def calculate_dynamic_position_size(
        self,
        balance: float,
        entry_price: float,
        atr_value: float,
        ml_confidence: float,
        target_volatility: float = 0.01,
        max_scale: float = 3.0,
        reference_timestamp: Optional[datetime] = None,
    ) -> Tuple[float, float]:
        """
        ボラティリティ連動ダイナミックポジションサイジング

        ボラティリティに応じてポジションサイズを調整し、
        高ボラ時は小さく、低ボラ時は大きくする。

        Args:
            balance: 現在の口座残高
            entry_price: エントリー予定価格
            atr_value: 現在のATR値
            ml_confidence: ML予測信頼度
            target_volatility: 目標ボラティリティ（0.01 = 1%）
            max_scale: 最大スケール倍率
            reference_timestamp: 基準時刻（バックテスト用、Noneの場合は現在時刻）

        Returns:
            (調整済みポジションサイズ, ストップロス価格)
        """
        try:
            # 入力検証
            if balance <= 0:
                raise ValueError(f"残高は正値である必要があります: {balance}")
            if entry_price <= 0:
                raise ValueError(f"エントリー価格は正値である必要があります: {entry_price}")
            if atr_value < 0:
                raise ValueError(f"ATR値は非負値である必要があります: {atr_value}")
            if not 0 < target_volatility <= 1.0:
                raise ValueError(f"目標ボラティリティは0-1.0の範囲: {target_volatility}")

            # 1) ベースKellyサイズ計算（バックテスト用タイムスタンプを渡す）
            base_kelly_size = self.calculate_optimal_size(
                ml_confidence=ml_confidence,
                strategy_name="dynamic",
                reference_timestamp=reference_timestamp,
            )

            # 2) ATRベースのストップロス計算（設定ファイルから取得）
            stop_atr_multiplier = get_position_config("dynamic_sizing.stop_atr_multiplier", 2.0)
            stop_loss_price = entry_price - (atr_value * stop_atr_multiplier)

            # ストップロス安全チェック
            if stop_loss_price <= 0:
                safety_ratio = get_position_config("dynamic_sizing.stop_loss_safety_ratio", 0.99)
                self.logger.warning(
                    f"計算されたストップロス価格が負値: {stop_loss_price:.2f}, "
                    f"エントリー価格の{(1 - safety_ratio) * 100:.1f}%下に設定"
                )
                stop_loss_price = entry_price * safety_ratio

            # 3) ボラティリティスケール計算
            if atr_value == 0:
                volatility_pct = target_volatility  # フォールバック
                self.logger.warning("ATR値が0、目標ボラティリティを使用")
            else:
                volatility_pct = atr_value / entry_price

            # スケール係数（ボラティリティが高いほど小さくなる）
            if volatility_pct <= 0:
                scale = 1.0
            else:
                scale = target_volatility / volatility_pct

            # スケール制限適用
            scale = max(0.1, min(scale, max_scale))

            # 4) 最終ポジションサイズ計算
            dynamic_position_size = base_kelly_size * scale

            # 5) 安全制限適用
            # 設定から安全制限比率を取得
            safe_balance_ratio = get_threshold("risk.safe_balance_ratio", 0.3)
            max_safe_position = min(
                balance * safe_balance_ratio / entry_price,  # 設定化された安全制限
                balance * self.max_position_ratio,  # Kelly最大制限
            )

            final_position_size = min(dynamic_position_size, max_safe_position)

            self.logger.info(
                f"ダイナミックポジションサイジング: "
                f"ベースKelly={base_kelly_size:.4f}, スケール={scale:.2f}, "
                f"最終サイズ={final_position_size:.4f}, ATR={atr_value:.6f}"
            )

            return final_position_size, stop_loss_price

        except Exception as e:
            self.logger.error(f"ダイナミックポジションサイジングエラー: {e}")
            # 複数レベルフォールバック
            return self._safe_fallback_position_size(balance, entry_price)

    def _safe_fallback_position_size(
        self, balance: float, entry_price: float
    ) -> Tuple[float, float]:
        """
        安全なフォールバックポジションサイズ計算

        複数レベルフォールバック機能を実装
        """
        try:
            # レベル1: 最小安全サイズ
            fallback_min_ratio = get_threshold("risk.fallback_min_ratio", 0.01)
            fallback_stop_ratio = get_threshold("risk.fallback_stop_ratio", 0.95)
            safe_position = balance * fallback_min_ratio / entry_price  # 設定化された最小比率
            safe_stop = entry_price * fallback_stop_ratio  # 設定化されたストップ比率

            # レベル2: 最大制限チェック
            fallback_max_ratio = get_threshold("risk.fallback_max_ratio", 0.1)
            max_safe = balance * fallback_max_ratio / entry_price  # 設定化された最大比率
            final_position = min(safe_position, max_safe)

            self.logger.warning(
                f"フォールバックポジションサイズ使用: {final_position:.4f}, "
                f"ストップ: {safe_stop:.2f}"
            )

            return final_position, safe_stop

        except Exception as fallback_error:
            self.logger.critical(f"フォールバック計算も失敗: {fallback_error}")
            # 最終安全値
            emergency_ratio = get_threshold("risk.emergency_ratio", 0.005)
            emergency_stop_ratio = get_threshold("risk.emergency_stop_ratio", 0.98)
            emergency_position = balance * emergency_ratio / entry_price  # 設定化された緊急比率
            emergency_stop = entry_price * emergency_stop_ratio  # 設定化された緊急ストップ比率
            return emergency_position, emergency_stop

    def get_kelly_statistics(self) -> Dict:
        """
        Kelly計算の統計情報取得

        Returns:
            統計情報辞書
        """
        try:
            if not self.trade_history:
                return {"status": "データなし"}

            recent_result = self.calculate_from_history()

            stats = {
                "total_trades": len(self.trade_history),
                "recent_kelly_result": recent_result,
                "max_position_limit": self.max_position_ratio,
                "safety_factor": self.safety_factor,
                "min_trades_required": self.min_trades_for_kelly,
            }

            if recent_result:
                stats.update(
                    {
                        "current_kelly_fraction": recent_result.kelly_fraction,
                        "recommended_size": recent_result.recommended_position_size,
                        "win_rate": recent_result.win_rate,
                        "confidence_level": recent_result.confidence_level,
                    }
                )

            return stats

        except Exception as e:
            self.logger.error(f"Kelly統計情報取得エラー: {e}")
            return {"status": "エラー", "error": str(e)}

    def validate_kelly_parameters(self) -> bool:
        """
        Kelly計算パラメータの妥当性確認

        Returns:
            パラメータが妥当かどうか
        """
        try:
            issues = []

            if not (0.001 <= self.max_position_ratio <= 0.1):
                issues.append(f"max_position_ratio範囲外: {self.max_position_ratio}")

            if not (0.1 <= self.safety_factor <= 1.0):
                issues.append(f"safety_factor範囲外: {self.safety_factor}")

            if not (5 <= self.min_trades_for_kelly <= 100):
                issues.append(f"min_trades_for_kelly範囲外: {self.min_trades_for_kelly}")

            if issues:
                self.logger.warning(f"Kelly パラメータ問題: {', '.join(issues)}")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Kellyパラメータ検証エラー: {e}")
            return False
