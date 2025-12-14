"""
統合リスク管理システム - Phase 49完了

IntegratedRiskManagerの新構造実装。
Kelly基準ポジションサイジング、ドローダウン管理、異常検知を統合し、
包括的なリスク管理とトレード評価を提供。
"""

import asyncio
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import pandas as pd

from ...core.config import get_threshold, load_config
from ...core.exceptions import RiskManagementError
from ...core.logger import get_logger
from ...core.reporting.discord_notifier import DiscordManager
from ..balance import BalanceMonitor
from ..core import RiskDecision, RiskMetrics, TradeEvaluation
from .anomaly import TradingAnomalyDetector
from .drawdown import DrawdownManager, TradingStatus
from .kelly import KellyCriterion
from .sizer import PositionSizeIntegrator

if TYPE_CHECKING:
    from .anomaly import AnomalyAlert


class IntegratedRiskManager:
    """
    統合リスク管理システム（Phase 38リファクタリング版）

    Kelly基準ポジションサイジング、ドローダウン管理、異常検知を統合し、
    包括的なリスク管理とトレード評価を提供
    """

    def __init__(
        self,
        config: Dict[str, Any],
        initial_balance: Optional[float] = None,
        enable_discord_notifications: bool = True,
        mode: str = "live",
        bitbank_client=None,
        execution_service=None,  # Phase 51.7 Phase 3-3: バックテスト証拠金維持率チェック用
    ):
        """
        統合リスク管理器初期化

        Args:
            config: リスク管理設定
            initial_balance: 初期残高
            enable_discord_notifications: Discord通知有効化
            mode: 実行モード（paper/live/backtest）
            bitbank_client: Bitbank APIクライアント（Phase 49.15: 証拠金維持率API取得用）
            execution_service: ExecutionServiceインスタンス（Phase 51.7: バックテスト対応）
        """
        self.config = config
        self.enable_discord_notifications = enable_discord_notifications
        self.mode = mode
        self.bitbank_client = bitbank_client  # Phase 49.15: 証拠金維持率API取得用
        self.execution_service = execution_service  # Phase 51.7: バックテスト対応
        self.logger = get_logger()

        # 初期残高設定（統一設定管理体系）
        if initial_balance is None:
            drawdown_config = config.get("drawdown_manager", {}) if config else {}
            initial_balance = drawdown_config.get("initial_balance", 10000.0)
        self.initial_balance = initial_balance

        # Discord通知システム初期化
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
            # Kelly基準ポジションサイジング
            kelly_config = config.get("kelly_criterion", {})
            self.kelly = KellyCriterion(
                max_position_ratio=kelly_config.get("max_position_ratio"),
                safety_factor=kelly_config.get("safety_factor"),
                min_trades_for_kelly=kelly_config.get("min_trades_for_kelly"),
            )

            # ポジションサイズ統合器
            self.position_integrator = PositionSizeIntegrator(self.kelly)

            # ドローダウン管理
            drawdown_config = config.get("drawdown_manager", {})
            self.drawdown_manager = DrawdownManager(
                max_drawdown_ratio=drawdown_config.get("max_drawdown_ratio", 0.20),
                consecutive_loss_limit=drawdown_config.get("consecutive_loss_limit", 5),
                cooldown_hours=drawdown_config.get("cooldown_hours", 24),
                config=drawdown_config,
                mode=self.mode,
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

            # 保証金監視システム（Phase 38: BalanceMonitor使用）
            self.balance_monitor = BalanceMonitor()
            self.logger.info("✅ 保証金監視システム初期化完了（監視のみ・制限なし）")

        except Exception as e:
            self.logger.error(f"リスクコンポーネント初期化エラー: {e}")
            raise RiskManagementError(f"リスク管理システム初期化失敗: {e}")

    async def evaluate_trade_opportunity(
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
            ml_prediction: ML予測結果
            strategy_signal: 戦略シグナル
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
                self.logger.debug(f"🔍 StrategySignal型: {type(strategy_signal).__name__}")
            elif isinstance(strategy_signal, dict):
                self.logger.warning(
                    "⚠️ strategy_signalが辞書型です。StrategySignalオブジェクトが期待されます。"
                )
            else:
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

            critical_anomalies = [a for a in anomaly_alerts if a.level.value == "critical"]
            warning_anomalies = [a for a in anomaly_alerts if a.level.value == "warning"]

            if critical_anomalies:
                denial_reasons.extend([a.message for a in critical_anomalies])
            if warning_anomalies:
                warnings.extend([a.message for a in warning_anomalies])

            # 3. ML信頼度チェック・取引方向取得
            ml_confidence = ml_prediction.get("confidence", 0.0)
            min_ml_confidence = get_threshold("trading.risk_thresholds.min_ml_confidence", 0.25)

            # 取引方向（side）の決定
            if isinstance(strategy_signal, dict):
                strategy_action = strategy_signal.get("action") or strategy_signal.get("side")
            else:
                strategy_action = getattr(strategy_signal, "action", None) or getattr(
                    strategy_signal, "side", None
                )

            # Phase 53.13: side属性を"buy"/"sell"/"hold"に正規化
            # デフォルトを"hold"に変更（BUYバイアス除去）
            raw_side = (
                strategy_action
                or ml_prediction.get("action")
                or ml_prediction.get("side")
                or "hold"
            )

            # holdの場合は実取引しないため、適切なside値を設定
            if raw_side.lower() in ["hold", "none", ""]:
                trade_side = "none"
            else:
                trade_side = raw_side

            if ml_confidence < min_ml_confidence:
                denial_reasons.append(
                    f"ML信頼度不足: {ml_confidence:.3f} < {min_ml_confidence:.3f}"
                )

            # 4. 残高利用率チェック
            capital_usage_check = self._check_capital_usage_limits(current_balance, last_price)
            if not capital_usage_check["allowed"]:
                denial_reasons.append(capital_usage_check["reason"])
                self.logger.warning(f"🚫 残高利用率制限: {capital_usage_check['reason']}")

            # 5. 保証金維持率監視（Phase 43: 拒否機能追加）
            should_deny, margin_message = await self._check_margin_ratio(
                current_balance, last_price, ml_prediction, strategy_signal
            )
            if should_deny and margin_message:
                denial_reasons.append(margin_message)  # 拒否
                self.logger.warning(f"🚫 Phase 43: 維持率制限: {margin_message}")
            elif margin_message:
                warnings.append(margin_message)  # 警告のみ

            # 6. ポジションサイジング計算
            position_size = 0.0
            kelly_recommendation = 0.0
            stop_loss = None
            take_profit = None

            if trading_allowed and not critical_anomalies:
                try:
                    # 統合ポジションサイズ計算
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
                        current_balance=current_balance,
                        btc_price=last_price,
                    )

                    # Kelly推奨値取得
                    kelly_result = self.kelly.calculate_from_history()
                    if kelly_result:
                        kelly_recommendation = kelly_result.kelly_fraction

                    # ストップロス・テイクプロフィット
                    if isinstance(strategy_signal, dict):
                        stop_loss = strategy_signal.get("stop_loss")
                        take_profit = strategy_signal.get("take_profit")
                    else:
                        stop_loss = getattr(strategy_signal, "stop_loss", None)
                        take_profit = getattr(strategy_signal, "take_profit", None)

                except Exception as e:
                    self.logger.error(f"ポジションサイジング計算エラー: {e}")
                    warnings.append(f"ポジションサイジング計算エラー: {e}")
                    position_size = 0.01

            # 7. リスクスコア算出
            risk_score = self._calculate_risk_score(
                ml_confidence=ml_confidence,
                anomaly_alerts=anomaly_alerts,
                drawdown_ratio=self.drawdown_manager.calculate_current_drawdown(),
                consecutive_losses=self.drawdown_manager.consecutive_losses,
                market_volatility=self._estimate_market_volatility(market_data),
            )

            # 8. 最終判定
            decision = self._make_final_decision(
                trading_allowed=trading_allowed,
                critical_anomalies=critical_anomalies,
                ml_confidence=ml_confidence,
                risk_score=risk_score,
                denial_reasons=denial_reasons,
            )

            # 9. 市場状況記録 + Phase 51.8-10: レジーム情報追加
            from ...core.services.market_regime_classifier import MarketRegimeClassifier

            # レジーム分類（Phase 51.8-10: ポジション制限・記録用）
            regime_classifier = MarketRegimeClassifier()
            regime = regime_classifier.classify(market_data)
            regime_value = (
                regime.value if hasattr(regime, "value") else str(regime)
            )  # Phase 51.8-10: 文字列化

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
                "regime": regime,  # Phase 51.8-10: レジーム情報（ポジション制限用・RegimeTypeオブジェクト）
                "regime_value": regime_value,  # Phase 51.8-10: レジーム文字列（記録用）
            }

            # 10. 評価結果構築
            evaluation = TradeEvaluation(
                decision=decision,
                side=trade_side,
                risk_score=risk_score,
                position_size=(position_size if decision == RiskDecision.APPROVED else 0.0),
                stop_loss=stop_loss,
                take_profit=take_profit,
                confidence_level=ml_confidence,
                entry_price=last_price,
                warnings=warnings,
                denial_reasons=denial_reasons,
                evaluation_timestamp=evaluation_timestamp,
                kelly_recommendation=kelly_recommendation,
                drawdown_status=self.drawdown_manager.trading_status.value,
                anomaly_alerts=[a.message for a in anomaly_alerts],
                market_conditions=market_conditions,
            )

            # 11. 統計更新
            self._update_statistics(evaluation)

            # 12. 履歴記録
            self.evaluation_history.append(evaluation)
            if len(self.evaluation_history) > 1000:
                self.evaluation_history = self.evaluation_history[-1000:]

            # 13. Discord通知（必要に応じて）
            if self.enable_discord_notifications:
                asyncio.create_task(self._send_discord_notifications(evaluation))

            # 14. ログ出力
            self._log_evaluation_result(evaluation)

            return evaluation

        except Exception as e:
            self.logger.error(f"取引評価エラー: {e}")
            # エラー時の安全な評価結果
            return TradeEvaluation(
                decision=RiskDecision.DENIED,
                side="buy",
                risk_score=1.0,
                position_size=0.0,
                stop_loss=None,
                take_profit=None,
                confidence_level=0.0,
                entry_price=0.0,
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
            profit_loss: 損益
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

    def _check_capital_usage_limits(
        self, current_balance: float, btc_price: float
    ) -> Dict[str, Any]:
        """残高利用率制限チェック"""
        try:
            max_capital_usage = get_threshold("risk.max_capital_usage", 0.3)

            # 初期残高取得
            config = load_config("config/core/unified.yaml")
            mode_balances = getattr(config, "mode_balances", {})

            # 実行モード判定
            if current_balance >= 90000:
                mode = "live"
            elif current_balance >= 8000:
                mode = "paper"
            else:
                mode = "paper"

            mode_balance_config = mode_balances.get(mode, {})
            initial_balance = mode_balance_config.get("initial_balance", 10000.0)

            # 使用済み資金計算
            used_capital = initial_balance - current_balance
            current_usage_ratio = used_capital / initial_balance if initial_balance > 0 else 1.0

            # 制限チェック
            if current_usage_ratio >= max_capital_usage:
                return {
                    "allowed": False,
                    "reason": f"資金利用率上限超過: {current_usage_ratio * 100:.1f}% >= {max_capital_usage * 100:.0f}%",
                    "usage_ratio": current_usage_ratio,
                }

            return {
                "allowed": True,
                "reason": "残高利用率制限内",
                "usage_ratio": current_usage_ratio,
            }

        except Exception as e:
            self.logger.error(f"❌ 残高利用率チェックエラー: {e}")
            return {
                "allowed": False,
                "reason": f"残高利用率チェック処理エラー: {e}",
                "usage_ratio": 1.0,
            }

    def _calculate_risk_score(
        self,
        ml_confidence: float,
        anomaly_alerts: List["AnomalyAlert"],
        drawdown_ratio: float,
        consecutive_losses: int,
        market_volatility: float,
    ) -> float:
        """総合リスクスコア算出（0.0-1.0、高いほど危険）"""
        try:
            risk_components = []

            # ML信頼度リスク
            ml_risk = 1.0 - ml_confidence
            risk_components.append(("ml_confidence", ml_risk, 0.3))

            # 異常検知リスク
            critical_count = len([a for a in anomaly_alerts if a.level.value == "critical"])
            warning_count = len([a for a in anomaly_alerts if a.level.value == "warning"])
            anomaly_risk = min(1.0, (critical_count * 0.5 + warning_count * 0.2))
            risk_components.append(("anomaly", anomaly_risk, 0.25))

            # ドローダウンリスク
            drawdown_risk = drawdown_ratio / 0.20
            risk_components.append(("drawdown", drawdown_risk, 0.25))

            # 連続損失リスク
            consecutive_risk = consecutive_losses / 5.0
            risk_components.append(("consecutive_losses", consecutive_risk, 0.1))

            # 市場ボラティリティリスク
            volatility_risk = min(1.0, market_volatility / 0.05)
            risk_components.append(("volatility", volatility_risk, 0.1))

            # 重み付き平均
            total_risk = sum(score * weight for _, score, weight in risk_components)
            total_risk = min(1.0, max(0.0, total_risk))

            return total_risk

        except Exception as e:
            self.logger.error(f"リスクスコア計算エラー: {e}")
            return 1.0

    def _estimate_market_volatility(self, market_data: pd.DataFrame) -> float:
        """市場ボラティリティ推定"""
        try:
            if "atr_14" in market_data.columns and len(market_data) > 1:
                current_price = float(market_data["close"].iloc[-1])
                atr_value = float(market_data["atr_14"].iloc[-1])
                return atr_value / current_price if current_price > 0 else 0.02
            else:
                returns = market_data["close"].pct_change().dropna()
                if len(returns) > 5:
                    return float(returns.std())
                return 0.02
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
            if not trading_allowed or critical_anomalies or denial_reasons:
                return RiskDecision.DENIED

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
        """
        Phase 51.6: Discord通知完全停止（週間サマリーのみ）
        旧コード: send_error_notification()は存在しないメソッドだったため削除
        """
        # Phase 51.6: features.yamlでcritical/warning/trade全てfalse設定済み
        # リスク管理の通知は全て停止（ログ出力のみ）
        return

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
            else:
                self.logger.info(
                    f"条件付き承認: リスクスコア={evaluation.risk_score:.1%}, "
                    f"警告={len(evaluation.warnings)}件"
                )

        except Exception as e:
            self.logger.error(f"評価結果ログエラー: {e}")

    async def _check_margin_ratio(
        self,
        current_balance: float,
        btc_price: float,
        ml_prediction: Dict[str, Any],
        strategy_signal: Any,
    ) -> Tuple[bool, Optional[str]]:
        """
        保証金維持率監視チェック（Phase 50.4: API直接取得方式に変更）

        Args:
            current_balance: 現在の口座残高（円）
            btc_price: 現在のBTC価格（円）
            ml_prediction: ML予測結果
            strategy_signal: 戦略シグナル

        Returns:
            Tuple[bool, Optional[str]]:
                - bool: True=拒否すべき, False=許可
                - Optional[str]: 拒否/警告メッセージ（問題なしの場合はNone）
        """
        try:
            # Phase 50.4: 新規ポジションサイズを推定（実BTC価格・実残高使用）
            ml_confidence = ml_prediction.get("confidence", 0.5)
            estimated_new_position_size = self._estimate_new_position_size(
                ml_confidence, btc_price, current_balance
            )

            # Phase 51.7 Phase 3-3: バックテストモードでは仮想ポジションから現在価値を計算
            from ...core.config.runtime_flags import is_backtest_mode

            current_position_value_jpy = 0.0  # デフォルト（API取得時）

            if is_backtest_mode() and self.execution_service:
                # バックテストモード: virtual_positionsから現在のポジション価値を計算
                if hasattr(self.execution_service, "virtual_positions"):
                    virtual_positions = self.execution_service.virtual_positions
                    for position in virtual_positions:
                        position_amount = position.get("amount", 0.0)
                        current_position_value_jpy += position_amount * btc_price

                    self.logger.info(
                        f"📊 Phase 51.7 Phase 3-3: バックテスト現在ポジション価値計算 - "
                        f"{len(virtual_positions)}ポジション, 合計価値: {current_position_value_jpy:.0f}円"
                    )

            # Phase 50.4: predict_future_margin()内でAPI直接取得するため、
            # current_position_value_jpyは使用されない（0.0でも動作）
            # Phase 51.7 Phase 3-3: バックテストモードでは計算した値を使用
            margin_prediction = await self.balance_monitor.predict_future_margin(
                current_balance_jpy=current_balance,
                current_position_value_jpy=current_position_value_jpy,  # Phase 51.7: バックテスト対応
                new_position_size_btc=estimated_new_position_size,
                btc_price_jpy=btc_price,
                bitbank_client=self.bitbank_client,  # Phase 50.4: API取得用
            )

            future_margin_ratio = margin_prediction.future_margin_ratio
            current_margin_ratio = margin_prediction.current_margin.margin_ratio
            estimated_position_value = margin_prediction.current_margin.position_value_jpy

            # Phase 49.5: 維持率80%未満で新規エントリー拒否（確実な遵守）
            critical_threshold = get_threshold("margin.thresholds.critical", 80.0)

            # Phase 50.4: 詳細ログ出力（ポジション価値追加）
            self.logger.info(
                f"📊 Phase 50.4 維持率チェック: "
                f"残高={current_balance:.0f}円, "
                f"現在ポジション={estimated_position_value:.0f}円, "
                f"新規サイズ={estimated_new_position_size:.4f}BTC, "
                f"現在={current_margin_ratio:.1f}%, "
                f"予測={future_margin_ratio:.1f}%, "
                f"閾値={critical_threshold:.0f}%"
            )

            if future_margin_ratio < critical_threshold:
                deny_message = (
                    f"🚨 Phase 50.4: 維持率{critical_threshold:.0f}%未満予測 - エントリー拒否 "
                    f"(現在={current_margin_ratio:.1f}% → 予測={future_margin_ratio:.1f}% < {critical_threshold:.0f}%)"
                )
                self.logger.warning(deny_message)
                return True, deny_message  # True = 拒否

            # 4. ユーザー警告が必要かチェック（警告レベル：許可するが通知）
            should_warn, warning_message = self.balance_monitor.should_warn_user(margin_prediction)

            if should_warn:
                warning_msg = f"保証金維持率警告: {warning_message}"
                return False, warning_msg  # False = 許可（警告のみ）

            return False, None  # 問題なし

        except Exception as e:
            # Phase 50.4: エラー時は拒否（安全側に倒す）
            self.logger.error(
                f"❌ Phase 50.4: 保証金監視チェックエラー - 安全のためエントリー拒否: {e}"
            )
            error_msg = f"🚨 保証金監視システムエラー - 安全のためエントリー拒否: {str(e)}"
            return True, error_msg  # Phase 50.4: エラー時は拒否（安全側に倒す）

    # Phase 50.4: _get_current_position_value() と _estimate_current_position_value() を削除
    # 理由: predict_future_margin()がAPI直接取得方式に変更されたため不要

    def _estimate_new_position_size(
        self, ml_confidence: float, btc_price: float, current_balance: float
    ) -> float:
        """
        Phase 50.1.5: 新規ポジションサイズ推定（実BTC価格・実残高使用）

        Args:
            ml_confidence: ML信頼度
            btc_price: 現在のBTC価格（JPY）
            current_balance: 現在の残高（JPY）

        Returns:
            推定ポジションサイズ（BTC）
        """
        try:
            dynamic_enabled = get_threshold(
                "position_management.dynamic_position_sizing.enabled", False
            )

            if dynamic_enabled:
                if ml_confidence < 0.6:
                    estimated_ratio = get_threshold(
                        "position_management.dynamic_position_sizing.low_confidence.min_ratio", 0.01
                    )
                elif ml_confidence < 0.75:
                    estimated_ratio = get_threshold(
                        "position_management.dynamic_position_sizing.medium_confidence.min_ratio",
                        0.03,
                    )
                else:
                    estimated_ratio = get_threshold(
                        "position_management.dynamic_position_sizing.high_confidence.min_ratio",
                        0.05,
                    )

                # Phase 50.1.5: 実際の値を使用（ハードコード削除）
                estimated_position_size = (current_balance * estimated_ratio) / btc_price

            else:
                estimated_position_size = get_threshold("trading.min_trade_size", 0.0001)

            return estimated_position_size

        except Exception as e:
            self.logger.error(f"新規ポジションサイズ推定エラー: {e}")
            return get_threshold("trading.min_trade_size", 0.0001)

    def get_risk_summary(self) -> Dict[str, Any]:
        """リスク管理サマリー取得"""
        try:
            kelly_stats = self.kelly.get_kelly_statistics()
            drawdown_stats = self.drawdown_manager.get_drawdown_statistics()
            anomaly_stats = self.anomaly_detector.get_anomaly_statistics()

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
        """停止条件チェック"""
        try:
            drawdown_stats = self.drawdown_manager.get_drawdown_statistics()

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
                "should_stop": False,
                "stop_reasons": [f"チェックエラー: {str(e)}"],
                "trading_allowed": True,
                "system_status": "unknown",
                "error": str(e),
            }
