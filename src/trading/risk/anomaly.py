"""
異常検出システム - Phase 49完了

Phase 28完了・市場異常検知機能：
- スプレッド異常検知（Warning/Critical閾値）
- API遅延監視
- 価格スパイク検出
- ボリューム異常検出
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional

import pandas as pd

from ...core.config import get_threshold
from ...core.logger import get_logger


class AnomalyLevel(Enum):
    """異常レベル."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AnomalyAlert:
    """異常アラート."""

    timestamp: datetime
    level: AnomalyLevel
    message: str
    details: dict


class TradingAnomalyDetector:
    """市場異常検知システム"""

    def __init__(
        self,
        spread_warning_threshold: float = None,
        spread_critical_threshold: float = None,
        api_latency_warning_ms: float = None,
        api_latency_critical_ms: float = None,
        price_spike_zscore_threshold: float = None,
        volume_spike_zscore_threshold: float = None,
    ):
        """
        異常検知器初期化

        Args:
            spread_warning_threshold: スプレッド警告閾値
            spread_critical_threshold: スプレッド危険閾値
            api_latency_warning_ms: API遅延警告閾値
            api_latency_critical_ms: API遅延危険閾値
            price_spike_zscore_threshold: 価格スパイクZスコア閾値
            volume_spike_zscore_threshold: ボリュームスパイクZスコア閾値
        """
        self.spread_warning_threshold = spread_warning_threshold or get_threshold(
            "risk.anomaly_detector.spread_warning_threshold", 0.003
        )
        self.spread_critical_threshold = spread_critical_threshold or get_threshold(
            "risk.anomaly_detector.spread_critical_threshold", 0.005
        )
        self.api_latency_warning_ms = (
            api_latency_warning_ms
            or get_threshold("risk.anomaly_detector.api_latency_warning", 1.0) * 1000
        )
        self.api_latency_critical_ms = (
            api_latency_critical_ms
            or get_threshold("risk.anomaly_detector.api_latency_critical", 3.0) * 1000
        )
        self.price_spike_zscore_threshold = price_spike_zscore_threshold or get_threshold(
            "risk.anomaly_detector.price_spike_zscore_threshold", 3.0
        )
        self.volume_spike_zscore_threshold = volume_spike_zscore_threshold or get_threshold(
            "risk.anomaly_detector.volume_spike_zscore_threshold", 3.0
        )

        self.anomaly_history: List[AnomalyAlert] = []
        self.logger = get_logger()

    def comprehensive_anomaly_check(
        self,
        bid: float,
        ask: float,
        last_price: float,
        volume: float,
        api_latency_ms: float,
        market_data: pd.DataFrame,
    ) -> List[AnomalyAlert]:
        """
        包括的異常チェック

        Args:
            bid: 買い価格
            ask: 売り価格
            last_price: 最終取引価格
            volume: 出来高
            api_latency_ms: API応答時間（ミリ秒）
            market_data: 市場データ履歴

        Returns:
            検出された異常アラートリスト
        """
        alerts = []

        # 1. スプレッド異常チェック
        spread_alert = self._check_spread_anomaly(bid, ask, last_price)
        if spread_alert:
            alerts.append(spread_alert)

        # 2. API遅延チェック
        latency_alert = self._check_api_latency(api_latency_ms)
        if latency_alert:
            alerts.append(latency_alert)

        # 3. 価格スパイクチェック
        price_alert = self._check_price_spike(last_price, market_data)
        if price_alert:
            alerts.append(price_alert)

        # 4. ボリューム異常チェック
        volume_alert = self._check_volume_anomaly(volume, market_data)
        if volume_alert:
            alerts.append(volume_alert)

        # 履歴に追加
        for alert in alerts:
            self.anomaly_history.append(alert)

        # 古い履歴削除（24時間以上前）
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.anomaly_history = [a for a in self.anomaly_history if a.timestamp >= cutoff_time]

        return alerts

    def _check_spread_anomaly(
        self, bid: float, ask: float, last_price: float
    ) -> Optional[AnomalyAlert]:
        """スプレッド異常チェック"""
        if last_price <= 0:
            return None

        spread_pct = (ask - bid) / last_price

        if spread_pct >= self.spread_critical_threshold:
            return AnomalyAlert(
                timestamp=datetime.now(),
                level=AnomalyLevel.CRITICAL,
                message=f"危険なスプレッド: {spread_pct:.2%}",
                details={"bid": bid, "ask": ask, "spread_pct": spread_pct},
            )
        elif spread_pct >= self.spread_warning_threshold:
            return AnomalyAlert(
                timestamp=datetime.now(),
                level=AnomalyLevel.WARNING,
                message=f"広いスプレッド: {spread_pct:.2%}",
                details={"bid": bid, "ask": ask, "spread_pct": spread_pct},
            )

        return None

    def _check_api_latency(self, api_latency_ms: float) -> Optional[AnomalyAlert]:
        """API遅延チェック"""
        if api_latency_ms >= self.api_latency_critical_ms:
            return AnomalyAlert(
                timestamp=datetime.now(),
                level=AnomalyLevel.CRITICAL,
                message=f"重大なAPI遅延: {api_latency_ms:.0f}ms",
                details={"latency_ms": api_latency_ms},
            )
        elif api_latency_ms >= self.api_latency_warning_ms:
            return AnomalyAlert(
                timestamp=datetime.now(),
                level=AnomalyLevel.WARNING,
                message=f"API遅延: {api_latency_ms:.0f}ms",
                details={"latency_ms": api_latency_ms},
            )

        return None

    def _check_price_spike(
        self, last_price: float, market_data: pd.DataFrame
    ) -> Optional[AnomalyAlert]:
        """価格スパイクチェック"""
        try:
            if len(market_data) < 20:
                return None

            recent_prices = market_data["close"].tail(20)
            price_mean = recent_prices.mean()
            price_std = recent_prices.std()

            if price_std > 0:
                z_score = abs((last_price - price_mean) / price_std)

                if z_score >= self.price_spike_zscore_threshold:
                    return AnomalyAlert(
                        timestamp=datetime.now(),
                        level=AnomalyLevel.CRITICAL,
                        message=f"価格急変検出: Zスコア={z_score:.2f}",
                        details={
                            "last_price": last_price,
                            "mean_price": price_mean,
                            "z_score": z_score,
                        },
                    )
        except Exception as e:
            self.logger.error(f"価格スパイクチェックエラー: {e}")

        return None

    def _check_volume_anomaly(
        self, volume: float, market_data: pd.DataFrame
    ) -> Optional[AnomalyAlert]:
        """ボリューム異常チェック"""
        try:
            if len(market_data) < 20 or "volume" not in market_data.columns:
                return None

            recent_volumes = market_data["volume"].tail(20)
            volume_mean = recent_volumes.mean()
            volume_std = recent_volumes.std()

            if volume_std > 0:
                z_score = abs((volume - volume_mean) / volume_std)

                if z_score >= self.volume_spike_zscore_threshold:
                    return AnomalyAlert(
                        timestamp=datetime.now(),
                        level=AnomalyLevel.WARNING,
                        message=f"ボリューム異常: Zスコア={z_score:.2f}",
                        details={
                            "current_volume": volume,
                            "mean_volume": volume_mean,
                            "z_score": z_score,
                        },
                    )
        except Exception as e:
            self.logger.error(f"ボリューム異常チェックエラー: {e}")

        return None

    def get_anomaly_statistics(self) -> dict:
        """異常検出統計取得"""
        try:
            recent_time = datetime.now() - timedelta(hours=24)
            recent_alerts = [a for a in self.anomaly_history if a.timestamp >= recent_time]

            return {
                "total_alerts_24h": len(recent_alerts),
                "critical_alerts": len(
                    [a for a in recent_alerts if a.level == AnomalyLevel.CRITICAL]
                ),
                "warning_alerts": len(
                    [a for a in recent_alerts if a.level == AnomalyLevel.WARNING]
                ),
                "info_alerts": len([a for a in recent_alerts if a.level == AnomalyLevel.INFO]),
            }
        except Exception as e:
            self.logger.error(f"異常統計取得エラー: {e}")
            return {}
