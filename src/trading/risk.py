"""
統合リスク管理システム

Phase 6リスク管理層の中核モジュール。Kelly基準ポジションサイジング、
ドローダウン管理、異常検知を統合し、包括的なリスク管理を提供します。

設計思想:
- 資金保全を最優先
- 複数のリスク要素を総合判定
- Phase 1-11システムとの完全統合
- 保守的・安全第一の取引判定

主要機能:
- 統合取引評価
- 包括的リスクスコア算出
- Discord通知連携
- 動的ポジションサイジング
- 実時間リスク監視.
"""

import asyncio
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from ..core.exceptions import RiskManagementError
from ..core.logger import get_logger
from .anomaly_detector import (
    AnomalyAlert,
    AnomalyLevel,
    TradingAnomalyDetector,
)
from .drawdown_manager import DrawdownManager, TradingStatus
from .position_sizing import (
    KellyCriterion,
    PositionSizeIntegrator,
    TradeResult,
)


class RiskDecision(Enum):
    """リスク判定結果."""

    APPROVED = "approved"
    DENIED = "denied"
    CONDITIONAL = "conditional"


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


class IntegratedRiskManager:
    """
    統合リスク管理システム

    Phase 6の3つのリスクコンポーネントを統合し、
    包括的なリスク管理とトレード評価を提供。.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        initial_balance: float = 1000000,  # 初期残高100万円
        enable_discord_notifications: bool = True,
    ):
        """
        統合リスク管理器初期化

        Args:
            config: リスク管理設定
            initial_balance: 初期残高
            enable_discord_notifications: Discord通知有効化.
        """
        self.config = config
        self.enable_discord_notifications = enable_discord_notifications
        self.logger = get_logger()

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
        """リスクコンポーネント初期化."""
        try:
            # Kelly基準ポジションサイジング
            kelly_config = config.get("kelly_criterion", {})
            self.kelly = KellyCriterion(
                max_position_ratio=kelly_config.get("max_position_ratio", 0.03),
                safety_factor=kelly_config.get("safety_factor", 0.5),
                min_trades_for_kelly=kelly_config.get("min_trades_for_kelly", 20),
            )

            # ポジションサイズ統合器
            self.position_integrator = PositionSizeIntegrator(self.kelly)

            # ドローダウン管理
            drawdown_config = config.get("drawdown_manager", {})
            self.drawdown_manager = DrawdownManager(
                max_drawdown_ratio=drawdown_config.get("max_drawdown_ratio", 0.20),
                consecutive_loss_limit=drawdown_config.get("consecutive_loss_limit", 5),
                cooldown_hours=drawdown_config.get("cooldown_hours", 24),
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
            包括的な取引評価結果.
        """
        try:
            warnings = []
            denial_reasons = []
            evaluation_timestamp = datetime.now()

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

            critical_anomalies = [a for a in anomaly_alerts if a.level == AnomalyLevel.CRITICAL]
            warning_anomalies = [a for a in anomaly_alerts if a.level == AnomalyLevel.WARNING]

            if critical_anomalies:
                denial_reasons.extend([a.message for a in critical_anomalies])
            if warning_anomalies:
                warnings.extend([a.message for a in warning_anomalies])

            # 3. ML信頼度チェック・取引方向取得
            ml_confidence = ml_prediction.get("confidence", 0.0)
            min_ml_confidence = self.config.get("min_ml_confidence", 0.25)

            # 取引方向（side）の決定
            trade_side = (
                strategy_signal.get("action")
                or strategy_signal.get("side")
                or ml_prediction.get("action")
                or ml_prediction.get("side")
                or "buy"  # デフォルト
            )

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
                    # 統合ポジションサイズ計算
                    strategy_confidence = strategy_signal.get("confidence", 0.5)
                    position_size = self.position_integrator.calculate_integrated_position_size(
                        ml_confidence=ml_confidence,
                        risk_manager_confidence=strategy_confidence,
                        strategy_name=strategy_signal.get("strategy_name", "unknown"),
                        config=self.config,
                    )

                    # Kelly推奨値取得
                    kelly_result = self.kelly.calculate_from_history()
                    if kelly_result:
                        kelly_recommendation = kelly_result.kelly_fraction

                    # ストップロス・テイクプロフィット
                    stop_loss = strategy_signal.get("stop_loss")
                    take_profit = strategy_signal.get("take_profit")

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
            confidence: 取引時の信頼度.
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
        anomaly_alerts: List[AnomalyAlert],
        drawdown_ratio: float,
        consecutive_losses: int,
        market_volatility: float,
    ) -> float:
        """
        総合リスクスコア算出（0.0-1.0、高いほど危険）.
        """
        try:
            risk_components = []

            # ML信頼度リスク（信頼度が低いほど高リスク）
            ml_risk = 1.0 - ml_confidence
            risk_components.append(("ml_confidence", ml_risk, 0.3))

            # 異常検知リスク
            critical_count = len([a for a in anomaly_alerts if a.level == AnomalyLevel.CRITICAL])
            warning_count = len([a for a in anomaly_alerts if a.level == AnomalyLevel.WARNING])
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
        """市場ボラティリティ推定."""
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
        critical_anomalies: List[AnomalyAlert],
        ml_confidence: float,
        risk_score: float,
        denial_reasons: List[str],
    ) -> RiskDecision:
        """最終取引判定."""
        try:
            # 重大な拒否理由がある場合は拒否
            if not trading_allowed or critical_anomalies or denial_reasons:
                return RiskDecision.DENIED

            # リスクスコアベースの判定
            risk_threshold_deny = self.config.get("risk_threshold_deny", 0.8)
            risk_threshold_conditional = self.config.get("risk_threshold_conditional", 0.6)

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
        """統計情報更新."""
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
            recent_time = datetime.now() - timedelta(hours=24)
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
        """Discord通知送信."""
        try:
            # 重大異常時のみ通知（実装は Phase 1のDiscord通知システムを活用）
            if evaluation.decision == RiskDecision.DENIED and evaluation.denial_reasons:
                message = f"🚨 **取引拒否**\n"
                message += f"リスクスコア: {evaluation.risk_score:.1%}\n"
                message += f"理由: {', '.join(evaluation.denial_reasons[:3])}"

                # 実際のDiscord通知実装はPhase 1の機能を活用
                self.logger.warning(f"Discord通知対象: {message}")

        except Exception as e:
            self.logger.error(f"Discord通知エラー: {e}")

    def _log_evaluation_result(self, evaluation: TradeEvaluation) -> None:
        """評価結果ログ出力."""
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
        """リスク管理サマリー取得."""
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
