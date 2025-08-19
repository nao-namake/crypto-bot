"""
取引実行用異常検知システム

Phase 6リスク管理層の重要コンポーネント。取引実行時の実用的な異常を検出し、
資金保全と取引品質の向上を図ります。

Phase 3の統計的異常検知と連携し、以下の実用的異常を検出:
- 異常スプレッド検知
- API遅延・接続問題検知
- 急激な価格変動検知
- 出来高異常検知
- システム負荷異常検知

設計方針: 保守的・安全第一.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from ..core.logger import get_logger
from ..features.anomaly import AnomalyDetector as MarketAnomalyDetector


class AnomalyLevel(Enum):
    """異常レベル."""

    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AnomalyAlert:
    """異常アラート."""

    timestamp: datetime
    anomaly_type: str
    level: AnomalyLevel
    value: float
    threshold: float
    message: str
    should_pause_trading: bool


@dataclass
class MarketCondition:
    """市場状況記録."""

    timestamp: datetime
    bid: float
    ask: float
    last_price: float
    volume: float
    spread_pct: float
    api_latency_ms: float


class TradingAnomalyDetector:
    """
    取引実行用異常検知システム

    取引を安全に実行するための実用的な異常検知機能を提供。
    Phase 3の市場異常検知と連携し、包括的な異常監視を実現。.
    """

    def __init__(
        self,
        spread_warning_threshold: float = 0.003,  # 0.3%
        spread_critical_threshold: float = 0.005,  # 0.5%
        api_latency_warning_ms: float = 1000,  # 1秒
        api_latency_critical_ms: float = 3000,  # 3秒
        price_spike_zscore_threshold: float = 3.0,  # 3σ
        volume_spike_zscore_threshold: float = 3.0,  # 3σ
        lookback_period: int = 100,
    ):
        """
        異常検知器初期化

        Args:
            spread_warning_threshold: スプレッド警告閾値
            spread_critical_threshold: スプレッド重大異常閾値
            api_latency_warning_ms: API遅延警告閾値（ms）
            api_latency_critical_ms: API遅延重大異常閾値（ms）
            price_spike_zscore_threshold: 価格スパイク検知Z-score閾値
            volume_spike_zscore_threshold: 出来高スパイク検知Z-score閾値
            lookback_period: 統計計算用の参照期間.
        """
        self.spread_warning_threshold = spread_warning_threshold
        self.spread_critical_threshold = spread_critical_threshold
        self.api_latency_warning_ms = api_latency_warning_ms
        self.api_latency_critical_ms = api_latency_critical_ms
        self.price_spike_zscore_threshold = price_spike_zscore_threshold
        self.volume_spike_zscore_threshold = volume_spike_zscore_threshold
        self.lookback_period = lookback_period

        # 履歴データ
        self.market_conditions: List[MarketCondition] = []
        self.anomaly_history: List[AnomalyAlert] = []

        # Phase 3異常検知との連携
        self.market_anomaly_detector = MarketAnomalyDetector(lookback_period)

        self.logger = get_logger()

    def check_spread_anomaly(
        self, bid: float, ask: float, last_price: float
    ) -> Optional[AnomalyAlert]:
        """
        スプレッド異常検知

        Args:
            bid: 買い価格
            ask: 売り価格
            last_price: 最終取引価格

        Returns:
            スプレッド異常アラート（正常時はNone）.
        """
        try:
            if bid <= 0 or ask <= 0 or last_price <= 0:
                return AnomalyAlert(
                    timestamp=datetime.now(),
                    anomaly_type="invalid_price",
                    level=AnomalyLevel.CRITICAL,
                    value=0,
                    threshold=0,
                    message=f"無効な価格データ: bid={bid}, ask={ask}, last={last_price}",
                    should_pause_trading=True,
                )

            if ask <= bid:
                return AnomalyAlert(
                    timestamp=datetime.now(),
                    anomaly_type="inverted_spread",
                    level=AnomalyLevel.CRITICAL,
                    value=ask - bid,
                    threshold=0,
                    message=f"逆転スプレッド検出: bid={bid:.2f} >= ask={ask:.2f}",
                    should_pause_trading=True,
                )

            # スプレッド率計算（最終価格基準）
            spread_pct = (ask - bid) / last_price

            if spread_pct >= self.spread_critical_threshold:
                return AnomalyAlert(
                    timestamp=datetime.now(),
                    anomaly_type="critical_spread",
                    level=AnomalyLevel.CRITICAL,
                    value=spread_pct,
                    threshold=self.spread_critical_threshold,
                    message=f"重大スプレッド異常: {spread_pct:.1%} >= {self.spread_critical_threshold:.1%}",
                    should_pause_trading=True,
                )
            elif spread_pct >= self.spread_warning_threshold:
                return AnomalyAlert(
                    timestamp=datetime.now(),
                    anomaly_type="wide_spread",
                    level=AnomalyLevel.WARNING,
                    value=spread_pct,
                    threshold=self.spread_warning_threshold,
                    message=f"ワイドスプレッド警告: {spread_pct:.1%} >= {self.spread_warning_threshold:.1%}",
                    should_pause_trading=False,
                )

            return None

        except Exception as e:
            self.logger.error(f"スプレッド異常検知エラー: {e}")
            return AnomalyAlert(
                timestamp=datetime.now(),
                anomaly_type="spread_check_error",
                level=AnomalyLevel.CRITICAL,
                value=0,
                threshold=0,
                message=f"スプレッド検証エラー: {e}",
                should_pause_trading=True,
            )

    def check_api_latency_anomaly(
        self, response_time_ms: float
    ) -> Optional[AnomalyAlert]:
        """
        API遅延異常検知

        Args:
            response_time_ms: API応答時間（ミリ秒）

        Returns:
            API遅延異常アラート（正常時はNone）.
        """
        try:
            if response_time_ms < 0:
                return AnomalyAlert(
                    timestamp=datetime.now(),
                    anomaly_type="invalid_latency",
                    level=AnomalyLevel.CRITICAL,
                    value=response_time_ms,
                    threshold=0,
                    message=f"無効なレイテンシ値: {response_time_ms}ms",
                    should_pause_trading=True,
                )

            if response_time_ms >= self.api_latency_critical_ms:
                return AnomalyAlert(
                    timestamp=datetime.now(),
                    anomaly_type="critical_latency",
                    level=AnomalyLevel.CRITICAL,
                    value=response_time_ms,
                    threshold=self.api_latency_critical_ms,
                    message=f"重大API遅延: {response_time_ms:.0f}ms >= {self.api_latency_critical_ms:.0f}ms",
                    should_pause_trading=True,
                )
            elif response_time_ms >= self.api_latency_warning_ms:
                return AnomalyAlert(
                    timestamp=datetime.now(),
                    anomaly_type="high_latency",
                    level=AnomalyLevel.WARNING,
                    value=response_time_ms,
                    threshold=self.api_latency_warning_ms,
                    message=f"API遅延警告: {response_time_ms:.0f}ms >= {self.api_latency_warning_ms:.0f}ms",
                    should_pause_trading=False,
                )

            return None

        except Exception as e:
            self.logger.error(f"API遅延異常検知エラー: {e}")
            return AnomalyAlert(
                timestamp=datetime.now(),
                anomaly_type="latency_check_error",
                level=AnomalyLevel.CRITICAL,
                value=response_time_ms,
                threshold=0,
                message=f"レイテンシ検証エラー: {e}",
                should_pause_trading=True,
            )

    def check_price_spike_anomaly(
        self, current_price: float, price_history: pd.Series
    ) -> Optional[AnomalyAlert]:
        """
        急激な価格変動検知

        Args:
            current_price: 現在価格
            price_history: 価格履歴（最新値を除く）

        Returns:
            価格スパイク異常アラート（正常時はNone）.
        """
        try:
            # 無効価格チェックは最優先（データ量に関係なく）
            if current_price <= 0:
                return AnomalyAlert(
                    timestamp=datetime.now(),
                    anomaly_type="invalid_current_price",
                    level=AnomalyLevel.CRITICAL,
                    value=current_price,
                    threshold=0,
                    message=f"無効な現在価格: {current_price}",
                    should_pause_trading=True,
                )

            if len(price_history) < 10:
                # データ不足時は価格スパイク検知しない
                return None

            # 価格変化率のZ-score計算
            returns = price_history.pct_change().dropna()
            if len(returns) < 5:
                return None

            current_return = (
                current_price - price_history.iloc[-1]
            ) / price_history.iloc[-1]

            mean_return = returns.mean()
            std_return = returns.std()

            if std_return == 0:
                # ボラティリティがゼロの場合は異常とみなす
                if abs(current_return) > 0.001:  # 0.1%以上の変動
                    return AnomalyAlert(
                        timestamp=datetime.now(),
                        anomaly_type="price_spike_zero_volatility",
                        level=AnomalyLevel.WARNING,
                        value=current_return,
                        threshold=0.001,
                        message=f"ゼロボラティリティ中の価格変動: {current_return:.1%}",
                        should_pause_trading=False,
                    )
                return None

            zscore = (current_return - mean_return) / std_return

            if abs(zscore) >= self.price_spike_zscore_threshold:
                return AnomalyAlert(
                    timestamp=datetime.now(),
                    anomaly_type="price_spike",
                    level=AnomalyLevel.WARNING,
                    value=abs(zscore),
                    threshold=self.price_spike_zscore_threshold,
                    message=f"価格スパイク検出: Z-score={zscore:.2f}, 変化率={current_return:.1%}",
                    should_pause_trading=False,
                )

            return None

        except Exception as e:
            self.logger.error(f"価格スパイク異常検知エラー: {e}")
            return AnomalyAlert(
                timestamp=datetime.now(),
                anomaly_type="price_spike_check_error",
                level=AnomalyLevel.CRITICAL,
                value=0,
                threshold=0,
                message=f"価格スパイク検証エラー: {e}",
                should_pause_trading=True,
            )

    def check_volume_anomaly(
        self, current_volume: float, volume_history: pd.Series
    ) -> Optional[AnomalyAlert]:
        """
        出来高異常検知

        Args:
            current_volume: 現在出来高
            volume_history: 出来高履歴

        Returns:
            出来高異常アラート（正常時はNone）.
        """
        try:
            if len(volume_history) < 10:
                return None

            if current_volume < 0:
                return AnomalyAlert(
                    timestamp=datetime.now(),
                    anomaly_type="invalid_volume",
                    level=AnomalyLevel.CRITICAL,
                    value=current_volume,
                    threshold=0,
                    message=f"無効な出来高: {current_volume}",
                    should_pause_trading=True,
                )

            # 出来高のZ-score計算
            volume_mean = volume_history.mean()
            volume_std = volume_history.std()

            if volume_std == 0:
                # 出来高の標準偏差がゼロの場合
                if current_volume != volume_mean:
                    return AnomalyAlert(
                        timestamp=datetime.now(),
                        anomaly_type="volume_deviation_zero_std",
                        level=AnomalyLevel.WARNING,
                        value=current_volume,
                        threshold=volume_mean,
                        message=f"一定出来高中の変動: {current_volume} vs 平均{volume_mean}",
                        should_pause_trading=False,
                    )
                return None

            zscore = (current_volume - volume_mean) / volume_std

            if abs(zscore) >= self.volume_spike_zscore_threshold:
                return AnomalyAlert(
                    timestamp=datetime.now(),
                    anomaly_type="volume_spike",
                    level=AnomalyLevel.WARNING,
                    value=abs(zscore),
                    threshold=self.volume_spike_zscore_threshold,
                    message=f"出来高スパイク: Z-score={zscore:.2f}, 出来高={current_volume:.0f}",
                    should_pause_trading=False,
                )

            return None

        except Exception as e:
            self.logger.error(f"出来高異常検知エラー: {e}")
            return AnomalyAlert(
                timestamp=datetime.now(),
                anomaly_type="volume_check_error",
                level=AnomalyLevel.CRITICAL,
                value=current_volume,
                threshold=0,
                message=f"出来高検証エラー: {e}",
                should_pause_trading=True,
            )

    def comprehensive_anomaly_check(
        self,
        bid: float,
        ask: float,
        last_price: float,
        volume: float,
        api_latency_ms: float,
        market_data: Optional[pd.DataFrame] = None,
    ) -> List[AnomalyAlert]:
        """
        包括的異常検知

        Args:
            bid: 買い価格
            ask: 売り価格
            last_price: 最終取引価格
            volume: 出来高
            api_latency_ms: API応答時間
            market_data: 市場データ履歴（価格スパイク検知用）

        Returns:
            検出された異常アラートのリスト.
        """
        alerts = []

        try:
            # 市場状況記録
            condition = MarketCondition(
                timestamp=datetime.now(),
                bid=bid,
                ask=ask,
                last_price=last_price,
                volume=volume,
                spread_pct=(ask - bid) / last_price if last_price > 0 else 0,
                api_latency_ms=api_latency_ms,
            )
            self.market_conditions.append(condition)

            # 履歴サイズ制限
            if len(self.market_conditions) > self.lookback_period * 2:
                self.market_conditions = self.market_conditions[
                    -self.lookback_period :
                ]

            # 1. スプレッド異常検知
            spread_alert = self.check_spread_anomaly(bid, ask, last_price)
            if spread_alert:
                alerts.append(spread_alert)

            # 2. API遅延異常検知
            latency_alert = self.check_api_latency_anomaly(api_latency_ms)
            if latency_alert:
                alerts.append(latency_alert)

            # 3. 価格スパイク検知（市場データがある場合）
            if market_data is not None and len(market_data) > 10:
                price_spike_alert = self.check_price_spike_anomaly(
                    last_price, market_data["close"].iloc[:-1]  # 最新値を除く
                )
                if price_spike_alert:
                    alerts.append(price_spike_alert)

            # 4. 出来高スパイク検知（市場データがある場合）
            if market_data is not None and len(market_data) > 10:
                volume_alert = self.check_volume_anomaly(
                    volume, market_data["volume"].iloc[:-1]  # 最新値を除く
                )
                if volume_alert:
                    alerts.append(volume_alert)

            # Phase 3異常検知との連携（市場データがある場合）
            if market_data is not None:
                try:
                    market_features = (
                        self.market_anomaly_detector.generate_all_features(
                            market_data
                        )
                    )
                    if "market_stress" in market_features.columns:
                        latest_stress = market_features["market_stress"].iloc[
                            -1
                        ]
                        if (
                            not pd.isna(latest_stress) and latest_stress > 2.0
                        ):  # 2σ以上
                            alerts.append(
                                AnomalyAlert(
                                    timestamp=datetime.now(),
                                    anomaly_type="market_stress",
                                    level=AnomalyLevel.WARNING,
                                    value=latest_stress,
                                    threshold=2.0,
                                    message=f"市場ストレス検出: {latest_stress:.2f}σ",
                                    should_pause_trading=False,
                                )
                            )
                except Exception as market_error:
                    self.logger.warning(
                        f"Phase 3異常検知連携エラー: {market_error}"
                    )

            # アラート履歴に追加
            self.anomaly_history.extend(alerts)

            # 履歴サイズ制限
            if len(self.anomaly_history) > 1000:
                self.anomaly_history = self.anomaly_history[-1000:]

            # ログ出力
            if alerts:
                critical_alerts = [
                    a for a in alerts if a.level == AnomalyLevel.CRITICAL
                ]
                warning_alerts = [
                    a for a in alerts if a.level == AnomalyLevel.WARNING
                ]

                if critical_alerts:
                    self.logger.critical(
                        f"重大異常検出: {len(critical_alerts)}件"
                    )
                    for alert in critical_alerts:
                        self.logger.critical(f"  - {alert.message}")

                if warning_alerts:
                    self.logger.warning(
                        f"警告レベル異常: {len(warning_alerts)}件"
                    )
                    for alert in warning_alerts:
                        self.logger.warning(f"  - {alert.message}")

            return alerts

        except Exception as e:
            self.logger.error(f"包括的異常検知エラー: {e}")
            error_alert = AnomalyAlert(
                timestamp=datetime.now(),
                anomaly_type="comprehensive_check_error",
                level=AnomalyLevel.CRITICAL,
                value=0,
                threshold=0,
                message=f"異常検知システムエラー: {e}",
                should_pause_trading=True,
            )
            return [error_alert]

    def should_pause_trading(self) -> Tuple[bool, List[str]]:
        """
        取引停止判定

        Returns:
            (停止すべきかどうか, 停止理由リスト).
        """
        try:
            # 直近の重大異常チェック（5分以内）
            recent_time = datetime.now() - timedelta(minutes=5)
            recent_critical_alerts = [
                alert
                for alert in self.anomaly_history
                if alert.timestamp >= recent_time
                and alert.should_pause_trading
            ]

            if recent_critical_alerts:
                reasons = [alert.message for alert in recent_critical_alerts]
                return True, reasons

            return False, []

        except Exception as e:
            self.logger.error(f"取引停止判定エラー: {e}")
            return True, [f"取引停止判定エラー: {e}"]

    def get_anomaly_statistics(self) -> Dict:
        """
        異常検知統計情報取得

        Returns:
            統計情報辞書.
        """
        try:
            if not self.anomaly_history:
                return {
                    "total_alerts": 0,
                    "recent_alerts": 0,
                    "critical_alerts": 0,
                    "warning_alerts": 0,
                    "should_pause": False,
                }

            # 直近24時間の統計
            recent_time = datetime.now() - timedelta(hours=24)
            recent_alerts = [
                a for a in self.anomaly_history if a.timestamp >= recent_time
            ]

            critical_count = len(
                [a for a in recent_alerts if a.level == AnomalyLevel.CRITICAL]
            )
            warning_count = len(
                [a for a in recent_alerts if a.level == AnomalyLevel.WARNING]
            )

            should_pause, pause_reasons = self.should_pause_trading()

            # 異常タイプ別統計
            alert_types = {}
            for alert in recent_alerts:
                alert_types[alert.anomaly_type] = (
                    alert_types.get(alert.anomaly_type, 0) + 1
                )

            return {
                "total_alerts": len(self.anomaly_history),
                "recent_alerts": len(recent_alerts),
                "critical_alerts": critical_count,
                "warning_alerts": warning_count,
                "should_pause": should_pause,
                "pause_reasons": pause_reasons,
                "alert_types": alert_types,
                "thresholds": {
                    "spread_warning": self.spread_warning_threshold,
                    "spread_critical": self.spread_critical_threshold,
                    "api_latency_warning": self.api_latency_warning_ms,
                    "api_latency_critical": self.api_latency_critical_ms,
                    "price_spike_zscore": self.price_spike_zscore_threshold,
                    "volume_spike_zscore": self.volume_spike_zscore_threshold,
                },
            }

        except Exception as e:
            self.logger.error(f"異常検知統計取得エラー: {e}")
            return {"status": "エラー", "error": str(e)}
