"""
統合リスク管理・ポジションサイジングシステム

Phase 22統合取引管理システムの中核機能：
- 統合リスク管理システム
- Kelly基準ポジションサイジング
- 取引実行結果管理（executor.pyから移行）

設計思想:
- 資金保全を最優先
- 複数のリスク要素を総合判定
- Kelly公式による理論的最適ポジションサイズ計算
- 実用的な安全制約の適用

主要機能:
- 統合取引評価・包括的リスクスコア算出
- Kelly基準による動的ポジションサイジング
- Discord通知連携・実時間リスク監視
- 複数レベルフォールバック機能
- 取引実行結果処理統合
"""

import asyncio
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum

# 循環インポート回避のため、型ヒントでのみ使用
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import pandas as pd

from ..core.config import get_position_config, get_threshold
from ..core.exceptions import RiskManagementError
from ..core.logger import get_logger
from ..core.reporting.discord_notifier import DiscordManager
from .risk_monitor import DrawdownManager, TradingAnomalyDetector, TradingStatus

if TYPE_CHECKING:
    from .risk_monitor import AnomalyAlert, AnomalyLevel


# === データクラス定義 ===


class RiskDecision(Enum):
    """リスク判定結果."""

    APPROVED = "approved"
    DENIED = "denied"
    CONDITIONAL = "conditional"


class ExecutionMode(Enum):
    """実行モード."""

    PAPER = "paper"  # ペーパートレード
    LIVE = "live"  # 実取引


class OrderStatus(Enum):
    """注文状態."""

    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    CANCELLED = "cancelled"
    FAILED = "failed"


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


@dataclass
class TradeEvaluation:
    """取引評価結果."""

    decision: RiskDecision
    side: str  # "buy" or "sell" - executor.pyで必要
    risk_score: float  # 0.0-1.0, 高いほど危険
    position_size: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    confidence_level: float
    warnings: List[str]
    denial_reasons: List[str]
    evaluation_timestamp: datetime

    # 詳細情報
    kelly_recommendation: float
    drawdown_status: str
    anomaly_alerts: List[str]
    market_conditions: Dict[str, Any]

    # 後方互換性のためのactionプロパティ（Silent Failure修正）
    @property
    def action(self) -> str:
        """後方互換性のため、sideフィールドをactionとしてもアクセス可能にする"""
        return self.side


@dataclass
class ExecutionResult:
    """注文実行結果."""

    success: bool
    mode: ExecutionMode
    order_id: Optional[str] = None
    side: Optional[str] = None
    amount: Optional[float] = None
    price: Optional[float] = None
    filled_amount: Optional[float] = None
    filled_price: Optional[float] = None
    fee: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    timestamp: datetime = None
    error_message: Optional[str] = None
    # ペーパートレード用追加情報
    paper_balance_before: Optional[float] = None
    paper_balance_after: Optional[float] = None
    paper_pnl: Optional[float] = None
    # レイテンシー監視・デバッグ情報
    execution_time_ms: Optional[float] = None
    notes: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class RiskMetrics:
    """リスク指標."""

    current_drawdown: float
    consecutive_losses: int
    kelly_fraction: float
    anomaly_count_24h: int
    trading_status: str
    last_evaluation: datetime
    total_evaluations: int
    approved_trades: int
    denied_trades: int


# === Kelly基準ポジションサイジング ===


class KellyCriterion:
    """
    Kelly基準によるポジションサイジング計算

    特徴:
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
        self, lookback_days: Optional[int] = None, strategy_filter: Optional[str] = None
    ) -> Optional[KellyCalculationResult]:
        """
        取引履歴からKelly値を計算

        Args:
            lookback_days: 遡る日数
            strategy_filter: 特定戦略のみでフィルタ（Noneで全戦略）

        Returns:
            Kelly計算結果（データ不足の場合はNone）
        """
        try:
            # 設定からデフォルト値を取得
            if lookback_days is None:
                lookback_days = get_threshold("risk.kelly_lookback_days", 30)

            # 期間フィルタ
            cutoff_date = datetime.now() - timedelta(days=lookback_days)
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
    ) -> float:
        """
        ML予測信頼度を考慮した最適ポジションサイズ計算

        Args:
            ml_confidence: ML予測の信頼度（0.0-1.0）
            strategy_name: 戦略名
            expected_return: 期待リターン（Noneの場合は履歴ベース）

        Returns:
            推奨ポジションサイズ（最大3%制限済み）
        """
        try:
            # 履歴ベースのKelly値取得
            kelly_result = self.calculate_from_history(strategy_filter=strategy_name)

            if kelly_result is None:
                # 🚀 Silent failure修正: Kelly履歴不足時は固定で最小取引単位使用
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
                            f"⚠️ 初期固定サイズをmax_order_size制限: {fixed_initial_size:.6f} BTC"
                        )

                    self.logger.info(
                        f"🚀 Kelly履歴不足({trade_history_count}<{self.min_trades_for_kelly})"
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
                            f"🚨 ポジションサイズ制限超過検出: 計算値={conservative_size:.6f} > "
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

            # 🚨 Silent failure対策: max_order_size制限チェック（Kelly履歴がある場合も）
            max_order_size = get_threshold("production.max_order_size", 0.02)
            if final_size > max_order_size:
                self.logger.error(
                    f"🚨 Kelly計算済みポジションサイズ制限超過: 計算値={final_size:.4f} > "
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

            # 1) ベースKellyサイズ計算
            base_kelly_size = self.calculate_optimal_size(
                ml_confidence=ml_confidence, strategy_name="dynamic"
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


# === ポジションサイズ統合器 ===


class PositionSizeIntegrator:
    """
    Kelly基準と既存RiskManagerの統合クラス
    """

    def __init__(self, kelly_criterion: KellyCriterion):
        """
        統合ポジションサイジング初期化

        Args:
            kelly_criterion: Kelly基準計算器
        """
        self.kelly = kelly_criterion
        self.logger = get_logger()

    def calculate_integrated_position_size(
        self,
        ml_confidence: float,
        risk_manager_confidence: float,
        strategy_name: str,
        config: Dict,
    ) -> float:
        """
        Kelly基準と既存RiskManagerの統合ポジションサイズ計算

        Args:
            ml_confidence: ML予測信頼度
            risk_manager_confidence: RiskManager用信頼度
            strategy_name: 戦略名
            config: 戦略設定

        Returns:
            統合ポジションサイズ（より保守的な値を採用）
        """
        try:
            # Kelly基準によるサイズ
            kelly_size = self.kelly.calculate_optimal_size(
                ml_confidence=ml_confidence, strategy_name=strategy_name
            )

            # 既存RiskManagerによるサイズ
            from ..strategies.utils import RiskManager

            risk_manager_size = RiskManager.calculate_position_size(
                confidence=risk_manager_confidence, config=config
            )

            # より保守的な値を採用
            integrated_size = min(kelly_size, risk_manager_size)

            self.logger.info(
                f"📊 統合ポジションサイズ計算: Kelly={kelly_size:.6f}, "
                f"RiskManager={risk_manager_size:.6f}, 採用={integrated_size:.6f} BTC"
            )

            return integrated_size

        except Exception as e:
            self.logger.error(f"統合ポジションサイズ計算エラー: {e}")
            return 0.01  # フォールバック値


# === 統合リスク管理システム ===


class IntegratedRiskManager:
    """
    統合リスク管理システム

    Kelly基準ポジションサイジング、ドローダウン管理、異常検知を統合し、
    包括的なリスク管理とトレード評価を提供
    """

    def __init__(
        self,
        config: Dict[str, Any],
        initial_balance: Optional[float] = None,  # 初期残高（設定ファイル参照）
        enable_discord_notifications: bool = True,
        mode: str = "live",  # 新規: 実行モード（paper/live/backtest）
    ):
        """
        統合リスク管理器初期化

        Args:
            config: リスク管理設定
            initial_balance: 初期残高
            enable_discord_notifications: Discord通知有効化
        """
        self.config = config
        self.enable_discord_notifications = enable_discord_notifications
        self.mode = mode  # モード保持
        self.logger = get_logger()

        # 初期残高設定（統一設定管理体系：unified.yamlから取得）
        if initial_balance is None:
            drawdown_config = config.get("drawdown_manager", {}) if config else {}
            initial_balance = drawdown_config.get("initial_balance", 10000.0)
        self.initial_balance = initial_balance

        # Discord通知システム初期化（Phase 15新実装）
        self.discord_manager = None
        if enable_discord_notifications:
            try:
                self.discord_manager = DiscordManager()
                self.logger.info("✅ Discord通知システム初期化完了（リスク管理）")
            except Exception as e:
                self.logger.warning(f"⚠️ Discord通知システム初期化失敗: {e}")

        # コアコンポーネント初期化
        self._initialize_components(config, initial_balance)

        # 統計・履歴管理
        self.evaluation_history: List[TradeEvaluation] = []
        self.risk_metrics = RiskMetrics(
            current_drawdown=0.0,
            consecutive_losses=0,
            kelly_fraction=0.0,
            anomaly_count_24h=0,
            trading_status=TradingStatus.ACTIVE.value,
            last_evaluation=datetime.now(),
            total_evaluations=0,
            approved_trades=0,
            denied_trades=0,
        )

        self.logger.info("統合リスク管理システム初期化完了")

    def _initialize_components(self, config: Dict[str, Any], initial_balance: float) -> None:
        """リスクコンポーネント初期化"""
        try:
            # Kelly基準ポジションサイジング（設定ファイルから動的取得）
            kelly_config = config.get("kelly_criterion", {})
            self.kelly = KellyCriterion(
                max_position_ratio=kelly_config.get("max_position_ratio"),
                safety_factor=kelly_config.get("safety_factor"),
                min_trades_for_kelly=kelly_config.get("min_trades_for_kelly"),
            )

            # ポジションサイズ統合器
            self.position_integrator = PositionSizeIntegrator(self.kelly)

            # ドローダウン管理（モード別分離対応）
            drawdown_config = config.get("drawdown_manager", {})
            self.drawdown_manager = DrawdownManager(
                max_drawdown_ratio=drawdown_config.get("max_drawdown_ratio", 0.20),
                consecutive_loss_limit=drawdown_config.get("consecutive_loss_limit", 5),
                cooldown_hours=drawdown_config.get("cooldown_hours", 24),
                config=drawdown_config,  # persistence設定を含む
                mode=self.mode,  # モード伝播
            )
            self.drawdown_manager.initialize_balance(initial_balance)

            # 異常検知
            anomaly_config = config.get("anomaly_detector", {})
            self.anomaly_detector = TradingAnomalyDetector(
                spread_warning_threshold=anomaly_config.get("spread_warning_threshold", 0.003),
                spread_critical_threshold=anomaly_config.get("spread_critical_threshold", 0.005),
                api_latency_warning_ms=anomaly_config.get("api_latency_warning_ms", 1000),
                api_latency_critical_ms=anomaly_config.get("api_latency_critical_ms", 3000),
                price_spike_zscore_threshold=anomaly_config.get(
                    "price_spike_zscore_threshold", 3.0
                ),
                volume_spike_zscore_threshold=anomaly_config.get(
                    "volume_spike_zscore_threshold", 3.0
                ),
            )

        except Exception as e:
            self.logger.error(f"リスクコンポーネント初期化エラー: {e}")
            raise RiskManagementError(f"リスク管理システム初期化失敗: {e}")

    def evaluate_trade_opportunity(
        self,
        ml_prediction: Dict[str, Any],
        strategy_signal: Dict[str, Any],
        market_data: pd.DataFrame,
        current_balance: float,
        bid: float,
        ask: float,
        api_latency_ms: float = 0,
    ) -> TradeEvaluation:
        """
        取引機会の包括的評価

        Args:
            ml_prediction: ML予測結果 (confidence, action, expected_return等)
            strategy_signal: 戦略シグナル (action, confidence, stop_loss等)
            market_data: 市場データ履歴
            current_balance: 現在残高
            bid: 買い価格
            ask: 売り価格
            api_latency_ms: API応答時間

        Returns:
            包括的な取引評価結果
        """
        try:
            warnings = []
            denial_reasons = []
            evaluation_timestamp = datetime.now()

            # StrategySignalオブジェクト型チェック・互換性確保
            if hasattr(strategy_signal, "__dict__"):
                # StrategySignalオブジェクトの場合（正常）
                self.logger.debug(f"🔍 StrategySignal型: {type(strategy_signal).__name__}")
            elif isinstance(strategy_signal, dict):
                # 辞書の場合は警告ログ
                self.logger.warning(
                    "⚠️ strategy_signalが辞書型です。StrategySignalオブジェクトが期待されます。"
                )
                self.logger.debug(f"🔍 辞書内容: {strategy_signal}")
            else:
                # その他の型の場合はエラー
                self.logger.error(f"❌ strategy_signalの型が不正: {type(strategy_signal)}")
                denial_reasons.append(f"不正なstrategy_signal型: {type(strategy_signal)}")

            # 残高更新
            self.drawdown_manager.update_balance(current_balance)

            # 基本情報取得
            last_price = float(market_data["close"].iloc[-1])
            volume = float(market_data["volume"].iloc[-1])

            # 1. ドローダウン制限チェック
            trading_allowed = self.drawdown_manager.check_trading_allowed()
            if not trading_allowed:
                drawdown_stats = self.drawdown_manager.get_drawdown_statistics()
                denial_reasons.append(f"ドローダウン制限: {drawdown_stats['trading_status']}")

            # 2. 異常検知
            anomaly_alerts = self.anomaly_detector.comprehensive_anomaly_check(
                bid=bid,
                ask=ask,
                last_price=last_price,
                volume=volume,
                api_latency_ms=api_latency_ms,
                market_data=market_data,
            )

            critical_anomalies = [a for a in anomaly_alerts if a.level == "critical"]
            warning_anomalies = [a for a in anomaly_alerts if a.level == "warning"]

            if critical_anomalies:
                denial_reasons.extend([a.message for a in critical_anomalies])
            if warning_anomalies:
                warnings.extend([a.message for a in warning_anomalies])

            # 3. ML信頼度チェック・取引方向取得（Phase 16-B: thresholds.yamlから取得）
            ml_confidence = ml_prediction.get("confidence", 0.0)
            min_ml_confidence = get_threshold("trading.risk_thresholds.min_ml_confidence", 0.25)

            # 取引方向（side）の決定
            # StrategySignalオブジェクトの属性アクセス修正（辞書型互換性付き）
            if isinstance(strategy_signal, dict):
                # 辞書型の場合（後方互換性）
                strategy_action = strategy_signal.get("action") or strategy_signal.get("side")
            else:
                # StrategySignalオブジェクトの場合（正常）
                strategy_action = getattr(strategy_signal, "action", None) or getattr(
                    strategy_signal, "side", None
                )

            # side属性を"buy"/"sell"のみに正規化（holdシグナル対応）
            raw_side = (
                strategy_action
                or ml_prediction.get("action")
                or ml_prediction.get("side")
                or "buy"  # デフォルト
            )

            # holdの場合は実取引しないため、適切なside値を設定
            if raw_side.lower() in ["hold", "none", ""]:
                # 最後の有効取引方向を使用、または中立値として"none"
                trade_side = "none"  # ExecutionServiceでガードされるため、実際には使用されない
            else:
                trade_side = raw_side

            if ml_confidence < min_ml_confidence:
                denial_reasons.append(
                    f"ML信頼度不足: {ml_confidence:.3f} < {min_ml_confidence:.3f}"
                )

            # 4. ポジションサイジング計算（エラー時でも継続）
            position_size = 0.0
            kelly_recommendation = 0.0
            stop_loss = None
            take_profit = None

            if trading_allowed and not critical_anomalies:
                try:
                    # 統合ポジションサイズ計算（辞書型互換性付き・Phase 16-B: 設定ファイル化）
                    default_confidence = get_threshold("trading.confidence_levels.medium", 0.5)
                    if isinstance(strategy_signal, dict):
                        strategy_confidence = strategy_signal.get("confidence", default_confidence)
                    else:
                        strategy_confidence = getattr(
                            strategy_signal, "confidence", default_confidence
                        )
                    position_size = self.position_integrator.calculate_integrated_position_size(
                        ml_confidence=ml_confidence,
                        risk_manager_confidence=strategy_confidence,
                        strategy_name=(
                            strategy_signal.get("strategy_name", "unknown")
                            if isinstance(strategy_signal, dict)
                            else getattr(strategy_signal, "strategy_name", "unknown")
                        ),
                        config=self.config,
                    )

                    # Kelly推奨値取得
                    kelly_result = self.kelly.calculate_from_history()
                    if kelly_result:
                        kelly_recommendation = kelly_result.kelly_fraction

                    # ストップロス・テイクプロフィット（辞書型互換性付き）
                    if isinstance(strategy_signal, dict):
                        stop_loss = strategy_signal.get("stop_loss")
                        take_profit = strategy_signal.get("take_profit")
                    else:
                        stop_loss = getattr(strategy_signal, "stop_loss", None)
                        take_profit = getattr(strategy_signal, "take_profit", None)

                except Exception as e:
                    self.logger.error(f"ポジションサイジング計算エラー: {e}")
                    warnings.append(f"ポジションサイジング計算エラー: {e}")
                    position_size = 0.01  # 最小安全値

            # 5. リスクスコア算出
            risk_score = self._calculate_risk_score(
                ml_confidence=ml_confidence,
                anomaly_alerts=anomaly_alerts,
                drawdown_ratio=self.drawdown_manager.calculate_current_drawdown(),
                consecutive_losses=self.drawdown_manager.consecutive_losses,
                market_volatility=self._estimate_market_volatility(market_data),
            )

            # 6. 最終判定
            decision = self._make_final_decision(
                trading_allowed=trading_allowed,
                critical_anomalies=critical_anomalies,
                ml_confidence=ml_confidence,
                risk_score=risk_score,
                denial_reasons=denial_reasons,
            )

            # 7. 市場状況記録
            market_conditions = {
                "last_price": last_price,
                "bid": bid,
                "ask": ask,
                "spread_pct": (ask - bid) / last_price,
                "volume": volume,
                "api_latency_ms": api_latency_ms,
                "atr_current": (
                    float(market_data["atr_14"].iloc[-1])
                    if "atr_14" in market_data.columns
                    else 0.0
                ),
            }

            # 8. 評価結果構築
            evaluation = TradeEvaluation(
                decision=decision,
                side=trade_side,
                risk_score=risk_score,
                position_size=(position_size if decision == RiskDecision.APPROVED else 0.0),
                stop_loss=stop_loss,
                take_profit=take_profit,
                confidence_level=ml_confidence,
                warnings=warnings,
                denial_reasons=denial_reasons,
                evaluation_timestamp=evaluation_timestamp,
                kelly_recommendation=kelly_recommendation,
                drawdown_status=self.drawdown_manager.trading_status.value,
                anomaly_alerts=[a.message for a in anomaly_alerts],
                market_conditions=market_conditions,
            )

            # 9. 統計更新
            self._update_statistics(evaluation)

            # 10. 履歴記録
            self.evaluation_history.append(evaluation)
            if len(self.evaluation_history) > 1000:
                self.evaluation_history = self.evaluation_history[-1000:]

            # 11. Discord通知（必要に応じて）
            if self.enable_discord_notifications:
                asyncio.create_task(self._send_discord_notifications(evaluation))

            # 12. ログ出力
            self._log_evaluation_result(evaluation)

            return evaluation

        except Exception as e:
            self.logger.error(f"取引評価エラー: {e}")
            # エラー時の安全な評価結果
            return TradeEvaluation(
                decision=RiskDecision.DENIED,
                side="buy",  # エラー時デフォルト
                risk_score=1.0,  # 最大リスク
                position_size=0.0,
                stop_loss=None,
                take_profit=None,
                confidence_level=0.0,
                warnings=[],
                denial_reasons=[f"評価システムエラー: {e}"],
                evaluation_timestamp=datetime.now(),
                kelly_recommendation=0.0,
                drawdown_status="error",
                anomaly_alerts=[],
                market_conditions={},
            )

    def record_trade_result(
        self,
        profit_loss: float,
        strategy_name: str = "default",
        confidence: float = 0.5,
    ) -> None:
        """
        取引結果記録（全コンポーネント更新）

        Args:
            profit_loss: 損益（正値=利益、負値=損失）
            strategy_name: 戦略名
            confidence: 取引時の信頼度
        """
        try:
            # Kelly基準用の取引履歴追加
            self.kelly.add_trade_result(
                profit_loss=profit_loss,
                strategy=strategy_name,
                confidence=confidence,
            )

            # ドローダウン管理への取引結果記録
            self.drawdown_manager.record_trade_result(
                profit_loss=profit_loss, strategy=strategy_name
            )

            self.logger.info(f"取引結果記録完了: P&L={profit_loss:.2f}, 戦略={strategy_name}")

        except Exception as e:
            self.logger.error(f"取引結果記録エラー: {e}")

    def _calculate_risk_score(
        self,
        ml_confidence: float,
        anomaly_alerts: List["AnomalyAlert"],
        drawdown_ratio: float,
        consecutive_losses: int,
        market_volatility: float,
    ) -> float:
        """
        総合リスクスコア算出（0.0-1.0、高いほど危険）
        """
        try:
            risk_components = []

            # ML信頼度リスク（信頼度が低いほど高リスク）
            ml_risk = 1.0 - ml_confidence
            risk_components.append(("ml_confidence", ml_risk, 0.3))

            # 異常検知リスク
            critical_count = len([a for a in anomaly_alerts if a.level == "critical"])
            warning_count = len([a for a in anomaly_alerts if a.level == "warning"])
            anomaly_risk = min(1.0, (critical_count * 0.5 + warning_count * 0.2))
            risk_components.append(("anomaly", anomaly_risk, 0.25))

            # ドローダウンリスク
            drawdown_risk = drawdown_ratio / 0.20  # 20%で最大リスク
            risk_components.append(("drawdown", drawdown_risk, 0.25))

            # 連続損失リスク
            consecutive_risk = consecutive_losses / 5.0  # 5回で最大リスク
            risk_components.append(("consecutive_losses", consecutive_risk, 0.1))

            # 市場ボラティリティリスク
            volatility_risk = min(1.0, market_volatility / 0.05)  # 5%で最大リスク
            risk_components.append(("volatility", volatility_risk, 0.1))

            # 重み付き平均
            total_risk = sum(score * weight for _, score, weight in risk_components)
            total_risk = min(1.0, max(0.0, total_risk))

            self.logger.debug(f"リスクスコア構成: {risk_components}, 総合={total_risk:.3f}")

            return total_risk

        except Exception as e:
            self.logger.error(f"リスクスコア計算エラー: {e}")
            return 1.0  # エラー時は最大リスク

    def _estimate_market_volatility(self, market_data: pd.DataFrame) -> float:
        """市場ボラティリティ推定"""
        try:
            if "atr_14" in market_data.columns and len(market_data) > 1:
                current_price = float(market_data["close"].iloc[-1])
                atr_value = float(market_data["atr_14"].iloc[-1])
                return atr_value / current_price if current_price > 0 else 0.02
            else:
                # フォールバック: 価格変動率から推定
                returns = market_data["close"].pct_change().dropna()
                if len(returns) > 5:
                    return float(returns.std())
                return 0.02  # デフォルト2%
        except Exception:
            return 0.02

    def _make_final_decision(
        self,
        trading_allowed: bool,
        critical_anomalies: List["AnomalyAlert"],
        ml_confidence: float,
        risk_score: float,
        denial_reasons: List[str],
    ) -> RiskDecision:
        """最終取引判定"""
        try:
            # 重大な拒否理由がある場合は拒否
            if not trading_allowed or critical_anomalies or denial_reasons:
                return RiskDecision.DENIED

            # リスクスコアベースの判定（Phase 16-B: thresholds.yamlから取得）
            risk_threshold_deny = get_threshold("trading.risk_thresholds.deny", 0.8)
            risk_threshold_conditional = get_threshold("trading.risk_thresholds.conditional", 0.6)

            if risk_score >= risk_threshold_deny:
                return RiskDecision.DENIED
            elif risk_score >= risk_threshold_conditional:
                return RiskDecision.CONDITIONAL
            else:
                return RiskDecision.APPROVED

        except Exception as e:
            self.logger.error(f"最終判定エラー: {e}")
            return RiskDecision.DENIED

    def _update_statistics(self, evaluation: TradeEvaluation) -> None:
        """統計情報更新"""
        try:
            self.risk_metrics.total_evaluations += 1
            self.risk_metrics.last_evaluation = evaluation.evaluation_timestamp
            self.risk_metrics.current_drawdown = self.drawdown_manager.calculate_current_drawdown()
            self.risk_metrics.consecutive_losses = self.drawdown_manager.consecutive_losses
            self.risk_metrics.trading_status = evaluation.drawdown_status

            if evaluation.decision == RiskDecision.APPROVED:
                self.risk_metrics.approved_trades += 1
            elif evaluation.decision == RiskDecision.DENIED:
                self.risk_metrics.denied_trades += 1

            # Kelly値更新
            kelly_result = self.kelly.calculate_from_history()
            if kelly_result:
                self.risk_metrics.kelly_fraction = kelly_result.kelly_fraction

            # 24時間以内の異常数
            lookback_hours = get_threshold("risk.recent_lookback_hours", 24)
            recent_time = datetime.now() - timedelta(hours=lookback_hours)
            self.risk_metrics.anomaly_count_24h = len(
                [
                    alert
                    for alert in self.anomaly_detector.anomaly_history
                    if alert.timestamp >= recent_time
                ]
            )

        except Exception as e:
            self.logger.error(f"統計更新エラー: {e}")

    async def _send_discord_notifications(self, evaluation: TradeEvaluation) -> None:
        """Discord通知送信（Phase 15 DiscordManager実装）"""
        try:
            # Discord通知システムが無効な場合は何もしない
            if not self.enable_discord_notifications or not self.discord_manager:
                return

            # 重大異常時のみ通知（取引拒否）
            if evaluation.decision == RiskDecision.DENIED and evaluation.denial_reasons:
                # エラー通知データ構築
                error_data = {
                    "type": "RiskManagementDenial",
                    "message": "取引がリスク管理により拒否されました",
                    "component": "IntegratedRiskManager",
                    "severity": ("warning" if evaluation.risk_score < 0.8 else "critical"),
                    "details": {
                        "risk_score": f"{evaluation.risk_score:.1%}",
                        "denial_reasons": evaluation.denial_reasons[:3],
                        "action": evaluation.side,
                        "market_conditions": evaluation.market_conditions,
                    },
                }

                # Discord通知送信
                try:
                    success = self.discord_manager.send_error_notification(error_data)
                    if success:
                        self.logger.info("✅ リスク管理Discord通知送信完了")
                    else:
                        self.logger.warning("⚠️ Discord通知送信失敗（Rate limit等）")
                except Exception as discord_error:
                    self.logger.error(f"❌ Discord通知送信エラー: {discord_error}")

        except Exception as e:
            self.logger.error(f"Discord通知処理エラー: {e}")

    def _log_evaluation_result(self, evaluation: TradeEvaluation) -> None:
        """評価結果ログ出力"""
        try:
            if evaluation.decision == RiskDecision.APPROVED:
                self.logger.info(
                    f"取引承認: リスクスコア={evaluation.risk_score:.1%}, "
                    f"ポジションサイズ={evaluation.position_size:.4f}, "
                    f"信頼度={evaluation.confidence_level:.1%}"
                )
            elif evaluation.decision == RiskDecision.DENIED:
                self.logger.warning(
                    f"取引拒否: リスクスコア={evaluation.risk_score:.1%}, "
                    f"理由={', '.join(evaluation.denial_reasons[:2])}"
                )
            else:  # CONDITIONAL
                self.logger.info(
                    f"条件付き承認: リスクスコア={evaluation.risk_score:.1%}, "
                    f"警告={len(evaluation.warnings)}件"
                )

        except Exception as e:
            self.logger.error(f"評価結果ログエラー: {e}")

    def get_risk_summary(self) -> Dict[str, Any]:
        """リスク管理サマリー取得"""
        try:
            # 各コンポーネントの統計
            kelly_stats = self.kelly.get_kelly_statistics()
            drawdown_stats = self.drawdown_manager.get_drawdown_statistics()
            anomaly_stats = self.anomaly_detector.get_anomaly_statistics()

            # 統合サマリー
            summary = {
                "risk_metrics": asdict(self.risk_metrics),
                "kelly_statistics": kelly_stats,
                "drawdown_statistics": drawdown_stats,
                "anomaly_statistics": anomaly_stats,
                "recent_evaluations": len(
                    [
                        e
                        for e in self.evaluation_history
                        if e.evaluation_timestamp >= datetime.now() - timedelta(hours=24)
                    ]
                ),
                "approval_rate": (
                    self.risk_metrics.approved_trades / max(1, self.risk_metrics.total_evaluations)
                ),
                "system_status": (
                    "active" if drawdown_stats.get("trading_allowed", False) else "paused"
                ),
            }

            return summary

        except Exception as e:
            self.logger.error(f"リスクサマリー取得エラー: {e}")
            return {"status": "エラー", "error": str(e)}

    def check_stop_conditions(self) -> Dict[str, Any]:
        """停止条件チェック（取引サイクル管理用）"""
        try:
            # ドローダウンマネージャーから停止条件を確認
            drawdown_stats = self.drawdown_manager.get_drawdown_statistics()

            # 停止条件判定
            should_stop = False
            stop_reasons = []

            # ドローダウン制限チェック
            if not drawdown_stats.get("trading_allowed", True):
                should_stop = True
                stop_reasons.append("最大ドローダウン到達")

            # 連続損失チェック
            if drawdown_stats.get("consecutive_losses", 0) >= 5:
                should_stop = True
                stop_reasons.append("連続損失5回到達")

            # 異常検知チェック
            anomaly_stats = self.anomaly_detector.get_anomaly_statistics()
            if anomaly_stats.get("critical_alerts", 0) > 0:
                should_stop = True
                stop_reasons.append("重大異常検知")

            # 結果返却
            result = {
                "should_stop": should_stop,
                "stop_reasons": stop_reasons,
                "trading_allowed": drawdown_stats.get("trading_allowed", True),
                "system_status": "active" if not should_stop else "paused",
                "check_timestamp": datetime.now().isoformat(),
            }

            if should_stop:
                self.logger.warning(f"停止条件検出: {', '.join(stop_reasons)}")

            return result

        except Exception as e:
            self.logger.error(f"停止条件チェックエラー: {e}")
            return {
                "should_stop": False,  # エラー時は安全側で継続
                "stop_reasons": [f"チェックエラー: {str(e)}"],
                "trading_allowed": True,
                "system_status": "unknown",
                "error": str(e),
            }
