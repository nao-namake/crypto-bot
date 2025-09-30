"""
取引リスク監視統合システム - Phase 28完了・Phase 29最適化版

異常検知とドローダウン管理を統合し、
取引実行時のリスク監視機能を一元化。

統合機能:
- 異常検知システム（スプレッド、API遅延、価格スパイク）
- ドローダウン管理（連続損失、最大ドローダウン制御）
- 取引状況監視（ACTIVE/PAUSED状態管理）
- リスク状態の永続化・復元

Phase 28完了・Phase 29最適化: 2025年9月27日.
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from ..core.config import get_anomaly_config, get_position_config
from ..core.logger import get_logger
from ..core.state.drawdown_persistence import DrawdownPersistence, create_persistence
from ..features.feature_generator import FeatureGenerator

# === 異常検知システム関連 ===


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


# === ドローダウン管理システム関連 ===


class TradingStatus(Enum):
    """取引状態."""

    ACTIVE = "active"
    PAUSED_DRAWDOWN = "paused_drawdown"
    PAUSED_CONSECUTIVE_LOSS = "paused_consecutive_loss"
    PAUSED_MANUAL = "paused_manual"


@dataclass
class DrawdownSnapshot:
    """ドローダウン記録用スナップショット."""

    timestamp: datetime
    current_balance: float
    peak_balance: float
    drawdown_ratio: float
    consecutive_losses: int
    status: TradingStatus


@dataclass
class TradingSession:
    """取引セッション記録."""

    start_time: datetime
    end_time: Optional[datetime]
    reason: str
    initial_balance: float
    final_balance: Optional[float]
    total_trades: int
    profitable_trades: int


# === 取引実行用異常検知システム ===


class TradingAnomalyDetector:
    """
    取引実行用異常検知システム

    取引を安全に実行するための実用的な異常検知機能を提供。
    Phase 3の市場異常検知と連携し、包括的な異常監視を実現。.
    """

    def __init__(
        self,
        spread_warning_threshold: Optional[float] = None,
        spread_critical_threshold: Optional[float] = None,
        api_latency_warning_ms: Optional[float] = None,
        api_latency_critical_ms: Optional[float] = None,
        price_spike_zscore_threshold: Optional[float] = None,
        volume_spike_zscore_threshold: Optional[float] = None,
        lookback_period: Optional[int] = None,
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
        # 設定ファイルから閾値取得
        self.spread_warning_threshold = spread_warning_threshold or get_anomaly_config(
            "spread.warning_threshold", 0.003
        )
        self.spread_critical_threshold = spread_critical_threshold or get_anomaly_config(
            "spread.critical_threshold", 0.005
        )
        self.api_latency_warning_ms = api_latency_warning_ms or get_anomaly_config(
            "api_latency.warning_ms", 1000
        )
        self.api_latency_critical_ms = api_latency_critical_ms or get_anomaly_config(
            "api_latency.critical_ms", 3000
        )
        self.price_spike_zscore_threshold = price_spike_zscore_threshold or get_anomaly_config(
            "spike_detection.price_zscore_threshold", 3.0
        )
        self.volume_spike_zscore_threshold = volume_spike_zscore_threshold or get_anomaly_config(
            "spike_detection.volume_zscore_threshold", 3.0
        )
        self.lookback_period = lookback_period or get_anomaly_config(
            "spike_detection.lookback_period", 100
        )

        # 履歴データ
        self.market_conditions: List[MarketCondition] = []
        self.anomaly_history: List[AnomalyAlert] = []

        # Phase 22統合: FeatureGenerator統合クラスを使用
        self.market_anomaly_detector = FeatureGenerator(lookback_period)

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

    def check_api_latency_anomaly(self, response_time_ms: float) -> Optional[AnomalyAlert]:
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

            current_return = (current_price - price_history.iloc[-1]) / price_history.iloc[-1]

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
                self.market_conditions = self.market_conditions[-self.lookback_period :]

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
                    volume, market_data["volume"].iloc[:-1]
                )  # 最新値を除く
                if volume_alert:
                    alerts.append(volume_alert)

            # Phase 3異常検知との連携（Phase 19で削除済み）
            # if market_data is not None:
            #     try:
            #         # Phase 22: market_stress削除（15特徴量統一）により特徴量生成を無効化
            #         market_features = self.market_anomaly_detector.generate_features_sync(market_data)
            #         if "market_stress" in market_features.columns:
            #             latest_stress = market_features["market_stress"].iloc[-1]
            #             if not pd.isna(latest_stress) and latest_stress > 2.0:  # 2σ以上
            #                 alerts.append(
            #                     AnomalyAlert(
            #                         timestamp=datetime.now(),
            #                         anomaly_type="market_stress",
            #                         level=AnomalyLevel.WARNING,
            #                         value=latest_stress,
            #                         threshold=2.0,
            #                         message=f"市場ストレス検出: {latest_stress:.2f}σ",
            #                         should_pause_trading=False,
            #                     )
            #     except Exception as market_error:
            #         self.logger.warning(f"Phase 3異常検知連携エラー: {market_error}")

            # アラート履歴に追加
            self.anomaly_history.extend(alerts)

            # 履歴サイズ制限
            if len(self.anomaly_history) > 1000:
                self.anomaly_history = self.anomaly_history[-1000:]

            # ログ出力
            if alerts:
                critical_alerts = [a for a in alerts if a.level == AnomalyLevel.CRITICAL]
                warning_alerts = [a for a in alerts if a.level == AnomalyLevel.WARNING]

                if critical_alerts:
                    self.logger.critical(f"重大異常検出: {len(critical_alerts)}件")
                    for alert in critical_alerts:
                        self.logger.critical(f"  - {alert.message}")

                if warning_alerts:
                    self.logger.warning(f"警告レベル異常: {len(warning_alerts)}件")
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
            # 直近の重大異常チェック（設定から取得）
            recent_minutes = get_anomaly_config("detection.recent_alert_minutes", 5)
            recent_time = datetime.now() - timedelta(minutes=recent_minutes)
            recent_critical_alerts = [
                alert
                for alert in self.anomaly_history
                if alert.timestamp >= recent_time and alert.should_pause_trading
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
            recent_alerts = [a for a in self.anomaly_history if a.timestamp >= recent_time]

            critical_count = len([a for a in recent_alerts if a.level == AnomalyLevel.CRITICAL])
            warning_count = len([a for a in recent_alerts if a.level == AnomalyLevel.WARNING])

            should_pause, pause_reasons = self.should_pause_trading()

            # 異常タイプ別統計
            alert_types = {}
            for alert in recent_alerts:
                alert_types[alert.anomaly_type] = alert_types.get(alert.anomaly_type, 0) + 1

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


# === ドローダウン管理システム ===


class DrawdownManager:
    """
    ドローダウン管理システム

    資金保全を最優先とした取引制御を行います。
    設定可能な制限:
    - 最大ドローダウン率（デフォルト20%）
    - 連続損失限界（デフォルト5回）
    - 停止期間（デフォルト24時間）.
    """

    def __init__(
        self,
        max_drawdown_ratio: float = 0.20,
        consecutive_loss_limit: int = 5,
        cooldown_hours: int = 24,
        persistence: Optional[DrawdownPersistence] = None,
        config: Optional[Dict] = None,
        mode: str = "live",  # 新規: 実行モード（paper/live/backtest）
    ):
        """
        ドローダウン管理器初期化

        Args:
            max_drawdown_ratio: 最大ドローダウン率（0.20 = 20%）
            consecutive_loss_limit: 連続損失制限回数
            cooldown_hours: 停止期間（時間）
            persistence: 永続化実装（None時は設定から自動作成）
            config: 設定辞書（persistence設定含む）
        """
        self.max_drawdown_ratio = max_drawdown_ratio
        self.consecutive_loss_limit = consecutive_loss_limit
        self.cooldown_hours = cooldown_hours

        # モード保持（ペーパーモード判定用）
        self.mode = mode

        # 永続化システム初期化（モード別分離対応）
        if persistence is not None:
            self.persistence = persistence
        else:
            # 設定から永続化システム作成
            persistence_config = config.get("persistence", {}) if config else {}
            local_path = persistence_config.get(
                "local_path"
            )  # Noneの場合はcreate_persistenceがモード別パスを生成
            gcs_bucket = persistence_config.get("gcs_bucket")
            gcs_path = persistence_config.get(
                "gcs_path"
            )  # Noneの場合はcreate_persistenceがモード別パスを生成

            self.persistence = create_persistence(
                mode=mode, local_path=local_path, gcs_bucket=gcs_bucket, gcs_path=gcs_path
            )

        # 状態管理
        self.current_balance = 0.0
        self.peak_balance = 0.0
        self.consecutive_losses = 0
        self.last_loss_time: Optional[datetime] = None
        self.trading_status = TradingStatus.ACTIVE
        self.pause_until: Optional[datetime] = None

        # 履歴管理
        self.drawdown_history: List[DrawdownSnapshot] = []
        self.trading_sessions: List[TradingSession] = []
        self.current_session: Optional[TradingSession] = None

        self.logger = get_logger()

        # 状態復元
        self._load_state()

    def initialize_balance(self, initial_balance: float) -> None:
        """
        初期残高設定

        Args:
            initial_balance: 初期残高.
        """
        try:
            if initial_balance <= 0:
                raise ValueError(f"無効な初期残高: {initial_balance}")

            self.current_balance = initial_balance

            # 新しいピークかチェック
            if initial_balance > self.peak_balance:
                self.peak_balance = initial_balance
                self.logger.info(f"新しいピーク残高更新: {self.peak_balance:.2f}")

            # 新セッション開始
            if self.current_session is None:
                self._start_new_session(initial_balance)

            self._save_state()

        except Exception as e:
            self.logger.error(f"初期残高設定エラー: {e}")

    def update_balance(self, new_balance: float) -> Tuple[float, bool]:
        """
        残高更新とドローダウン計算

        Args:
            new_balance: 新しい残高

        Returns:
            (現在のドローダウン率, 取引許可フラグ).
        """
        try:
            if new_balance < 0:
                self.logger.warning(f"残高が負値: {new_balance:.2f}")

            old_balance = self.current_balance

            # 異常な残高変化検出（ドローダウン計算異常対策）
            if old_balance > 0 and abs(new_balance - old_balance) / old_balance > 0.50:
                balance_change_ratio = (new_balance - old_balance) / old_balance
                self.logger.warning(
                    f"⚠️ 異常な残高変化検出: {old_balance:.0f}円 → {new_balance:.0f}円 "
                    f"({balance_change_ratio:+.1%}) - API取得エラーの可能性"
                )

                # 極端な増加（フォールバック値エラー）の場合は以前の残高を維持
                if balance_change_ratio > 10.0:  # 1000%以上の増加
                    self.logger.error(
                        f"💥 異常な残高増加を検出 - フォールバック値エラーの可能性: "
                        f"{old_balance:.0f}円 → {new_balance:.0f}円 - 以前の残高を維持"
                    )
                    new_balance = old_balance

            self.current_balance = new_balance

            # ピーク更新チェック
            if new_balance > self.peak_balance:
                self.peak_balance = new_balance
                # ピーク更新時は連続損失リセット
                if self.consecutive_losses > 0:
                    self.logger.info(
                        f"ピーク更新により連続損失リセット: {self.consecutive_losses} -> 0"
                    )
                    self.consecutive_losses = 0
                    self.last_loss_time = None

            # ドローダウン計算
            current_drawdown = self.calculate_current_drawdown()

            # 取引許可判定
            trading_allowed = self.check_trading_allowed()

            # スナップショット記録
            snapshot = DrawdownSnapshot(
                timestamp=datetime.now(),
                current_balance=new_balance,
                peak_balance=self.peak_balance,
                drawdown_ratio=current_drawdown,
                consecutive_losses=self.consecutive_losses,
                status=self.trading_status,
            )
            self.drawdown_history.append(snapshot)

            # 履歴サイズ制限（直近1000件）
            if len(self.drawdown_history) > 1000:
                self.drawdown_history = self.drawdown_history[-1000:]

            self._save_state()

            self.logger.debug(
                f"残高更新: {old_balance:.2f} -> {new_balance:.2f}, "
                f"ドローダウン: {current_drawdown:.1%}, 取引許可: {trading_allowed}"
            )

            return current_drawdown, trading_allowed

        except Exception as e:
            self.logger.error(f"残高更新エラー: {e}")
            return 0.0, False

    def record_trade_result(
        self,
        profit_loss: float,
        strategy: str = "default",
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        取引結果記録と連続損失管理

        Args:
            profit_loss: 損益（正値=利益、負値=損失）
            strategy: 戦略名
            timestamp: 取引時刻（Noneの場合は現在時刻）.
        """
        try:
            if timestamp is None:
                timestamp = datetime.now()

            is_profitable = profit_loss > 0

            # セッション統計更新
            if self.current_session:
                self.current_session.total_trades += 1
                if is_profitable:
                    self.current_session.profitable_trades += 1

            if is_profitable:
                # 利益の場合は連続損失リセット
                if self.consecutive_losses > 0:
                    self.logger.info(f"利益により連続損失リセット: {self.consecutive_losses} -> 0")
                    self.consecutive_losses = 0
                    self.last_loss_time = None

                    # 一時停止状態の場合は解除チェック
                    if self.trading_status == TradingStatus.PAUSED_CONSECUTIVE_LOSS:
                        self._resume_trading("利益による連続損失解除")
            else:
                # 損失の場合は連続損失カウント
                self.consecutive_losses += 1
                self.last_loss_time = timestamp

                self.logger.warning(
                    f"連続損失カウント: {self.consecutive_losses}/{self.consecutive_loss_limit}, "
                    f"損失額: {profit_loss:.2f}"
                )

                # 連続損失制限チェック
                if self.consecutive_losses >= self.consecutive_loss_limit:
                    self._pause_trading_consecutive_loss()

            self.logger.info(
                f"取引結果記録: P&L={profit_loss:.2f}, "
                f"戦略={strategy}, 連続損失={self.consecutive_losses}"
            )

            self._save_state()

        except Exception as e:
            self.logger.error(f"取引結果記録エラー: {e}")

    def calculate_current_drawdown(self) -> float:
        """
        現在のドローダウン率計算

        Returns:
            ドローダウン率（0.0-1.0、0.2 = 20%）.
        """
        try:
            if self.peak_balance <= 0:
                return 0.0

            drawdown = max(
                0.0,
                (self.peak_balance - self.current_balance) / self.peak_balance,
            )
            return drawdown

        except Exception as e:
            self.logger.error(f"ドローダウン計算エラー: {e}")
            return 0.0

    def check_trading_allowed(self) -> bool:
        """
        取引許可チェック

        Returns:
            取引が許可されているかどうか.
        """
        try:
            current_time = datetime.now()

            # 手動停止チェック
            if self.trading_status == TradingStatus.PAUSED_MANUAL:
                return False

            # 一時停止期間チェック
            if self.pause_until and current_time < self.pause_until:
                return False
            elif self.pause_until and current_time >= self.pause_until:
                # 停止期間終了
                self._resume_trading("停止期間終了")

            # ドローダウン制限チェック
            current_drawdown = self.calculate_current_drawdown()
            if current_drawdown >= self.max_drawdown_ratio:
                if self.trading_status != TradingStatus.PAUSED_DRAWDOWN:
                    self._pause_trading_drawdown()
                return False

            # 連続損失チェック
            if self.consecutive_losses >= self.consecutive_loss_limit:
                if self.trading_status != TradingStatus.PAUSED_CONSECUTIVE_LOSS:
                    self._pause_trading_consecutive_loss()
                return False

            return True

        except Exception as e:
            self.logger.error(f"取引許可チェックエラー: {e}")
            return False

    def get_drawdown_statistics(self) -> Dict:
        """
        ドローダウン統計情報取得

        Returns:
            統計情報辞書.
        """
        try:
            current_drawdown = self.calculate_current_drawdown()
            trading_allowed = self.check_trading_allowed()

            # 履歴統計
            max_historical_drawdown = 0.0
            if self.drawdown_history:
                max_historical_drawdown = max(
                    snapshot.drawdown_ratio for snapshot in self.drawdown_history
                )

            # セッション統計
            session_stats = {}
            if self.current_session:
                win_rate = 0.0
                if self.current_session.total_trades > 0:
                    win_rate = (
                        self.current_session.profitable_trades / self.current_session.total_trades
                    )

                session_stats = {
                    "session_start": self.current_session.start_time.isoformat(),
                    "total_trades": self.current_session.total_trades,
                    "profitable_trades": self.current_session.profitable_trades,
                    "win_rate": win_rate,
                    "initial_balance": self.current_session.initial_balance,
                }

            stats = {
                "current_balance": self.current_balance,
                "peak_balance": self.peak_balance,
                "current_drawdown": current_drawdown,
                "max_drawdown_limit": self.max_drawdown_ratio,
                "max_historical_drawdown": max_historical_drawdown,
                "consecutive_losses": self.consecutive_losses,
                "consecutive_loss_limit": self.consecutive_loss_limit,
                "trading_status": self.trading_status.value,
                "trading_allowed": trading_allowed,
                "last_loss_time": (
                    self.last_loss_time.isoformat() if self.last_loss_time else None
                ),
                "pause_until": (self.pause_until.isoformat() if self.pause_until else None),
                "session_statistics": session_stats,
            }

            return stats

        except Exception as e:
            self.logger.error(f"ドローダウン統計取得エラー: {e}")
            return {"status": "エラー", "error": str(e)}

    def manual_pause_trading(self, reason: str = "手動停止") -> None:
        """
        手動での取引停止

        Args:
            reason: 停止理由.
        """
        try:
            self.trading_status = TradingStatus.PAUSED_MANUAL
            self.logger.warning(f"手動取引停止: {reason}")
            self._save_state()

        except Exception as e:
            self.logger.error(f"手動停止エラー: {e}")

    def manual_resume_trading(self, reason: str = "手動再開") -> None:
        """
        手動での取引再開

        Args:
            reason: 再開理由.
        """
        try:
            # 他の制限が解除されているかチェック
            if self.check_trading_allowed():
                self._resume_trading(reason)
            else:
                self.logger.warning("他の制限により取引再開不可")

        except Exception as e:
            self.logger.error(f"手動再開エラー: {e}")

    def _pause_trading_drawdown(self) -> None:
        """ドローダウン制限による取引停止."""
        self.trading_status = TradingStatus.PAUSED_DRAWDOWN
        current_drawdown = self.calculate_current_drawdown()

        self.logger.critical(
            f"ドローダウン制限到達！取引停止: {current_drawdown:.1%} >= {self.max_drawdown_ratio:.1%}"
        )

        # セッション終了
        if self.current_session:
            self._end_current_session(f"ドローダウン制限: {current_drawdown:.1%}")

    def _pause_trading_consecutive_loss(self) -> None:
        """連続損失による取引停止."""
        self.trading_status = TradingStatus.PAUSED_CONSECUTIVE_LOSS
        self.pause_until = datetime.now() + timedelta(hours=self.cooldown_hours)

        self.logger.critical(
            f"連続損失制限到達！{self.cooldown_hours}時間停止: "
            f"{self.consecutive_losses}回 >= {self.consecutive_loss_limit}回"
        )

        # セッション終了
        if self.current_session:
            self._end_current_session(
                f"連続損失: {self.consecutive_losses}回, " f"{self.cooldown_hours}時間停止"
            )

    def _resume_trading(self, reason: str) -> None:
        """取引再開."""
        old_status = self.trading_status
        self.trading_status = TradingStatus.ACTIVE
        self.pause_until = None

        self.logger.info(f"取引再開: {reason} (旧状態: {old_status.value})")

        # 新セッション開始
        self._start_new_session(self.current_balance)

    def _start_new_session(self, initial_balance: float) -> None:
        """新しい取引セッション開始."""
        self.current_session = TradingSession(
            start_time=datetime.now(),
            end_time=None,
            reason="セッション開始",
            initial_balance=initial_balance,
            final_balance=None,
            total_trades=0,
            profitable_trades=0,
        )

        self.logger.info(f"新セッション開始: 初期残高={initial_balance:.2f}")

    def _end_current_session(self, reason: str) -> None:
        """現在の取引セッション終了."""
        if self.current_session:
            self.current_session.end_time = datetime.now()
            self.current_session.reason = reason
            self.current_session.final_balance = self.current_balance

            self.trading_sessions.append(self.current_session)

            self.logger.info(
                f"セッション終了: {reason}, "
                f"取引数={self.current_session.total_trades}, "
                f"利益取引={self.current_session.profitable_trades}"
            )

            self.current_session = None

    def _save_state(self) -> None:
        """状態を永続化システムに保存."""
        try:
            state = {
                "current_balance": self.current_balance,
                "peak_balance": self.peak_balance,
                "consecutive_losses": self.consecutive_losses,
                "last_loss_time": (
                    self.last_loss_time.isoformat() if self.last_loss_time else None
                ),
                "trading_status": self.trading_status.value,
                "pause_until": (self.pause_until.isoformat() if self.pause_until else None),
                "current_session": (asdict(self.current_session) if self.current_session else None),
            }

            # 非同期メソッドを安全に実行（イベントループ競合回避）
            import asyncio

            try:
                # 現在のイベントループが実行中かチェック
                current_loop = asyncio.get_running_loop()
                # 実行中の場合は、threadで実行して競合回避
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        lambda: asyncio.run(self.persistence.save_state(state))
                    )
                    success = future.result(timeout=5.0)
                    if not success:
                        self.logger.warning("ドローダウン状態保存に失敗しました")
            except RuntimeError:
                # イベントループが実行されていない場合は直接実行
                success = asyncio.run(self.persistence.save_state(state))
                if not success:
                    self.logger.warning("ドローダウン状態保存に失敗しました")

        except Exception as e:
            self.logger.error(f"状態保存エラー: {e}")

    def _force_reset_to_safe_state(self) -> None:
        """
        🚨 強制的に安全な状態にリセット

        あらゆる異常状態から確実に復旧するための終極的解決機能
        """
        try:
            # デフォルト安全値で強制初期化（Phase 16-B：設定ファイル参照）
            default_balance = get_position_config("drawdown.default_balance", 10000.0)
            self.current_balance = default_balance
            self.peak_balance = default_balance
            self.consecutive_losses = 0
            self.last_loss_time = None
            self.trading_status = TradingStatus.ACTIVE
            self.pause_until = None

            # セッション状態もクリア
            self.current_session = None

            self.logger.warning(
                "🔄 強制ドローダウンリセット完了 - 全状態を安全値に初期化\n"
                f"  - 残高: {self.current_balance:.2f}円\n"
                f"  - ピーク: {self.peak_balance:.2f}円\n"
                f"  - 状態: {self.trading_status.value}\n"
                f"  - 連続損失: {self.consecutive_losses}\n"
                "✅ 取引再開可能状態"
            )

        except Exception as e:
            self.logger.error(f"強制リセットエラー: {e}")
            # それでも失敗する場合は最小限の安全状態
            self.trading_status = TradingStatus.ACTIVE

    def _load_state(self) -> None:
        """永続化システムから状態を復元."""
        try:
            # 🚨 CRITICAL FIX: 強制リセット機能
            import os

            force_reset = os.getenv("FORCE_DRAWDOWN_RESET", "false").lower() == "true"

            if force_reset:
                self.logger.warning("🔄 強制ドローダウンリセットが要求されました")
                self._force_reset_to_safe_state()
                return

            # 非同期メソッドを安全に実行（イベントループ競合回避）
            import asyncio

            try:
                # 現在のイベントループが実行中かチェック
                current_loop = asyncio.get_running_loop()
                # 実行中の場合は、threadで実行して競合回避
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(lambda: asyncio.run(self.persistence.load_state()))
                    state = future.result(timeout=5.0)
                    if state is None:
                        self.logger.info("ドローダウン状態ファイルが存在しません（初回起動）")
                        return
            except RuntimeError:
                # イベントループが実行されていない場合は直接実行
                state = asyncio.run(self.persistence.load_state())
                if state is None:
                    self.logger.info("ドローダウン状態ファイルが存在しません（初回起動）")
                    return

            # 型安全性チェック強化
            if not isinstance(state, dict):
                self.logger.error(f"状態データが辞書ではありません: {type(state)}")
                raise TypeError(f"Invalid state data type: {type(state)}")

            self.current_balance = float(state.get("current_balance", 0.0))
            self.peak_balance = float(state.get("peak_balance", 0.0))
            self.consecutive_losses = int(state.get("consecutive_losses", 0))

            if state.get("last_loss_time"):
                try:
                    self.last_loss_time = datetime.fromisoformat(state["last_loss_time"])
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"last_loss_time解析エラー: {e}")

            if state.get("trading_status"):
                try:
                    self.trading_status = TradingStatus(state["trading_status"])
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"trading_status解析エラー: {e}")

            if state.get("pause_until"):
                try:
                    self.pause_until = datetime.fromisoformat(state["pause_until"])
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"pause_until解析エラー: {e}")

            if state.get("current_session"):
                session_data = state["current_session"]
                # 型チェック：dictであることを確認（後方互換性）
                if isinstance(session_data, dict):
                    self.current_session = TradingSession(
                        start_time=datetime.fromisoformat(session_data["start_time"]),
                        end_time=(
                            datetime.fromisoformat(session_data["end_time"])
                            if session_data.get("end_time")
                            else None
                        ),
                        reason=session_data.get("reason", ""),
                        initial_balance=session_data.get("initial_balance", 0.0),
                        final_balance=session_data.get("final_balance"),
                        total_trades=session_data.get("total_trades", 0),
                        profitable_trades=session_data.get("profitable_trades", 0),
                    )
                else:
                    # 古い形式（文字列など）の場合は新セッション開始
                    self.logger.warning(
                        f"古い形式のcurrent_session検出、新セッション開始: {type(session_data)}"
                    )
                    self.current_session = None

            # 🚨 CRITICAL FIX: 異常な状態のサニティチェック強化版
            needs_reset = False

            # 1. PAUSED_DRAWDOWN状態の強制リセット
            if self.trading_status == TradingStatus.PAUSED_DRAWDOWN:
                self.logger.warning("🚨 PAUSED_DRAWDOWN状態検出 - 強制リセット実行")
                needs_reset = True

            # 2. 異常なドローダウン値検出
            if self.peak_balance > 0 and self.current_balance > 0:
                calculated_drawdown = (self.peak_balance - self.current_balance) / self.peak_balance
                if calculated_drawdown > 0.5:  # 50%以上のドローダウンは異常値として扱う
                    self.logger.warning(
                        f"🚨 異常なドローダウン検出: {calculated_drawdown:.1%} "
                        f"(ピーク: {self.peak_balance:.2f}, 現在: {self.current_balance:.2f})"
                    )
                    needs_reset = True

            # 3. 残高異常検出
            if self.current_balance <= 0 or self.peak_balance <= 0:
                self.logger.warning("🚨 残高異常検出 - 強制リセット実行")
                needs_reset = True

            # 強制リセット実行
            if needs_reset:
                self._force_reset_to_safe_state()
                # リセット後の状態を保存
                self._save_state()

            self.logger.info(
                f"ドローダウン状態復元完了: 残高={self.current_balance:.2f}, "
                f"ピーク={self.peak_balance:.2f}, 状態={self.trading_status.value}"
            )

        except Exception as e:
            self.logger.error(f"状態復元エラー: {e}")
            # ファイル破損の可能性があるため、バックアップを作成してから削除
            try:
                if hasattr(self.persistence, "file_path") and self.persistence.file_path.exists():
                    backup_path = self.persistence.file_path.with_suffix(".corrupted.backup")
                    import shutil

                    shutil.copy2(self.persistence.file_path, backup_path)
                    self.logger.info(f"破損ファイルをバックアップ: {backup_path}")

                    # 破損ファイルを削除
                    self.persistence.file_path.unlink()
                    self.logger.info("破損した状態ファイルを削除しました")
            except Exception as backup_error:
                self.logger.error(f"破損ファイル処理エラー: {backup_error}")

            # デフォルト状態で強制リセット
            self._force_reset_to_safe_state()
            self.logger.info("デフォルト状態にリセットしました")


# 後方互換性のためのエイリアス
__all__ = [
    # 異常検知システム
    "TradingAnomalyDetector",
    "AnomalyAlert",
    "AnomalyLevel",
    "MarketCondition",
    # ドローダウン管理システム
    "DrawdownManager",
    "DrawdownSnapshot",
    "TradingSession",
    "TradingStatus",
]
