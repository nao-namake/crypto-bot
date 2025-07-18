"""
拡張ステータス管理システム
リアルタイム統計更新・システム監視・パフォーマンス追跡統合
"""

import json
import logging
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .trading_statistics_manager import TradeRecord, TradingStatisticsManager


@dataclass
class SystemHealth:
    """システムヘルス状況"""

    status: str = "unknown"  # running, stopped, error, maintenance
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    network_latency: float = 0.0
    api_response_time: float = 0.0
    last_health_check: Optional[str] = None
    error_count_24h: int = 0
    uptime_hours: float = 0.0


@dataclass
class MarketConditions:
    """市場状況"""

    symbol: str = "BTC/JPY"
    current_price: float = 0.0
    price_change_24h: float = 0.0
    price_change_percentage: float = 0.0
    volume_24h: float = 0.0
    bid_ask_spread: float = 0.0
    volatility: float = 0.0
    trend: str = "neutral"  # bullish, bearish, neutral
    support_levels: List[float] = None
    resistance_levels: List[float] = None
    last_market_update: Optional[str] = None

    def __post_init__(self):
        if self.support_levels is None:
            self.support_levels = []
        if self.resistance_levels is None:
            self.resistance_levels = []


@dataclass
class TradingSignals:
    """取引シグナル状況"""

    current_signal: str = "neutral"  # buy, sell, hold, neutral
    signal_strength: float = 0.0
    confidence_level: float = 0.0
    signal_source: str = "unknown"
    entry_conditions_met: bool = False
    exit_conditions_met: bool = False
    risk_assessment: str = "medium"  # low, medium, high
    expected_profit: float = 0.0
    stop_loss_level: float = 0.0
    take_profit_level: float = 0.0
    signal_generated_at: Optional[str] = None


@dataclass
class PositionStatus:
    """ポジション状況"""

    total_positions: int = 0
    long_positions: int = 0
    short_positions: int = 0
    total_exposure: float = 0.0
    unrealized_pnl: float = 0.0
    margin_used: float = 0.0
    margin_available: float = 0.0
    margin_ratio: float = 0.0
    largest_position_size: float = 0.0
    average_entry_price: float = 0.0
    position_duration_hours: float = 0.0


@dataclass
class RiskMetrics:
    """リスク指標"""

    current_risk_level: str = "medium"  # low, medium, high, critical
    var_95: float = 0.0  # Value at Risk 95%
    expected_shortfall: float = 0.0
    risk_per_trade: float = 0.0
    portfolio_heat: float = 0.0  # Current risk as % of account
    correlation_risk: float = 0.0
    leverage_ratio: float = 0.0
    stress_test_result: str = "pass"  # pass, warning, fail
    risk_adjusted_return: float = 0.0
    kelly_fraction: float = 0.0


class EnhancedStatusManager:
    """拡張ステータス管理メインクラス"""

    def __init__(self, base_dir: str = ".", update_interval: int = 30):
        self.base_dir = Path(base_dir)
        self.update_interval = update_interval

        # ファイルパス
        self.status_file = self.base_dir / "status.json"
        self.enhanced_status_file = self.base_dir / "enhanced_status.json"
        self.system_log_file = self.base_dir / "logs" / "system.log"

        # ログディレクトリ作成
        (self.base_dir / "logs").mkdir(exist_ok=True)

        # 統計管理システム
        self.stats_manager = TradingStatisticsManager(base_dir)

        # 状態データ
        self.system_health = SystemHealth()
        self.market_conditions = MarketConditions()
        self.trading_signals = TradingSignals()
        self.position_status = PositionStatus()
        self.risk_metrics = RiskMetrics()

        # 内部状態
        self.is_running = False
        self.update_thread = None
        self.start_time = datetime.now()

        # ログ設定
        self.logger = logging.getLogger(__name__)
        self._setup_logging()

        # 既存ステータス読み込み
        self._load_existing_status()

    def _setup_logging(self):
        """ログ設定"""
        if not self.logger.handlers:
            handler = logging.FileHandler(self.system_log_file, encoding="utf-8")
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def _load_existing_status(self):
        """既存ステータス読み込み"""
        try:
            if self.enhanced_status_file.exists():
                with open(self.enhanced_status_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                    if "system_health" in data:
                        self.system_health = SystemHealth(**data["system_health"])
                    if "market_conditions" in data:
                        self.market_conditions = MarketConditions(
                            **data["market_conditions"]
                        )
                    if "trading_signals" in data:
                        self.trading_signals = TradingSignals(**data["trading_signals"])
                    if "position_status" in data:
                        self.position_status = PositionStatus(**data["position_status"])
                    if "risk_metrics" in data:
                        self.risk_metrics = RiskMetrics(**data["risk_metrics"])

        except Exception as e:
            self.logger.error(f"既存ステータス読み込みエラー: {e}")

    def start_monitoring(self):
        """監視開始"""
        if self.is_running:
            self.logger.warning("監視は既に実行中です")
            return

        self.is_running = True
        self.update_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.update_thread.start()

        self.logger.info("拡張ステータス監視を開始しました")

    def stop_monitoring(self):
        """監視停止"""
        self.is_running = False
        if self.update_thread:
            self.update_thread.join(timeout=5)

        self.logger.info("拡張ステータス監視を停止しました")

    def _monitoring_loop(self):
        """監視ループ"""
        while self.is_running:
            try:
                self._update_all_status()
                self._save_enhanced_status()
                self._save_legacy_status()

                time.sleep(self.update_interval)

            except Exception as e:
                self.logger.error(f"監視ループエラー: {e}")
                time.sleep(self.update_interval)

    def _update_all_status(self):
        """全ステータス更新"""
        self._update_system_health()
        self._update_market_conditions()
        self._update_trading_signals()
        self._update_position_status()
        self._update_risk_metrics()

    def _update_system_health(self):
        """システムヘルス更新"""
        try:
            import psutil

            # CPU・メモリ・ディスク使用率
            self.system_health.cpu_usage = psutil.cpu_percent(interval=1)
            self.system_health.memory_usage = psutil.virtual_memory().percent
            self.system_health.disk_usage = psutil.disk_usage("/").percent

            # システム状態判定
            if (
                self.system_health.cpu_usage > 90
                or self.system_health.memory_usage > 90
                or self.system_health.disk_usage > 95
            ):
                self.system_health.status = "warning"
            else:
                self.system_health.status = "running"

            # 稼働時間
            self.system_health.uptime_hours = (
                datetime.now() - self.start_time
            ).total_seconds() / 3600
            self.system_health.last_health_check = datetime.now().isoformat()

        except ImportError:
            # psutilが利用できない場合
            self.system_health.status = "running"
            self.system_health.last_health_check = datetime.now().isoformat()
            self.system_health.uptime_hours = (
                datetime.now() - self.start_time
            ).total_seconds() / 3600

        except Exception as e:
            self.logger.error(f"システムヘルス更新エラー: {e}")
            self.system_health.status = "error"

    def _update_market_conditions(self):
        """市場状況更新（プレースホルダー）"""
        # 実際の実装では取引所APIから市場データを取得
        self.market_conditions.last_market_update = datetime.now().isoformat()

        # デモデータ（本番では実際のAPIデータに置き換え）
        if self.market_conditions.current_price == 0.0:
            self.market_conditions.current_price = 3000000.0
            self.market_conditions.volume_24h = 1000.0
            self.market_conditions.trend = "neutral"

    def _update_trading_signals(self):
        """取引シグナル更新（プレースホルダー）"""
        # 実際の実装ではMLモデルからシグナルを取得
        pass

    def _update_position_status(self):
        """ポジション状況更新"""
        # オープンポジション数計算
        open_trades = [t for t in self.stats_manager.trades if t.status == "open"]

        self.position_status.total_positions = len(open_trades)
        self.position_status.long_positions = len(
            [t for t in open_trades if t.side.lower() == "buy"]
        )
        self.position_status.short_positions = len(
            [t for t in open_trades if t.side.lower() == "sell"]
        )

        if open_trades:
            self.position_status.total_exposure = sum(
                t.quantity * t.entry_price for t in open_trades
            )
            self.position_status.largest_position_size = max(
                t.quantity * t.entry_price for t in open_trades
            )

            # 平均エントリー価格
            total_value = sum(t.quantity * t.entry_price for t in open_trades)
            total_quantity = sum(t.quantity for t in open_trades)
            if total_quantity > 0:
                self.position_status.average_entry_price = total_value / total_quantity

    def _update_risk_metrics(self):
        """リスク指標更新"""
        performance = self.stats_manager.performance_metrics

        # 基本リスク指標
        self.risk_metrics.var_95 = performance.max_drawdown * 0.95  # 簡易VaR推定
        self.risk_metrics.expected_shortfall = performance.max_drawdown * 1.1

        # リスクレベル判定
        if performance.current_drawdown > performance.max_drawdown * 0.8:
            self.risk_metrics.current_risk_level = "high"
        elif performance.current_drawdown > performance.max_drawdown * 0.5:
            self.risk_metrics.current_risk_level = "medium"
        else:
            self.risk_metrics.current_risk_level = "low"

        # リスク調整リターン
        if performance.max_drawdown > 0:
            self.risk_metrics.risk_adjusted_return = (
                performance.roi / performance.max_drawdown
            )

    def _save_enhanced_status(self):
        """拡張ステータス保存"""
        enhanced_status = {
            "timestamp": datetime.now().isoformat(),
            "version": "2.0",
            "system_health": asdict(self.system_health),
            "market_conditions": asdict(self.market_conditions),
            "trading_signals": asdict(self.trading_signals),
            "position_status": asdict(self.position_status),
            "risk_metrics": asdict(self.risk_metrics),
            "performance_summary": self.stats_manager.get_performance_summary(),
            "metadata": {
                "update_interval_seconds": self.update_interval,
                "monitoring_active": self.is_running,
                "system_start_time": self.start_time.isoformat(),
            },
        }

        with open(self.enhanced_status_file, "w", encoding="utf-8") as f:
            json.dump(enhanced_status, f, indent=2, ensure_ascii=False)

    def _save_legacy_status(self):
        """レガシーstatus.json更新（後方互換性）"""
        performance = self.stats_manager.performance_metrics

        legacy_status = {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_profit": round(performance.net_profit, 2),
            "trade_count": performance.total_trades,
            "position": f"{self.position_status.total_positions} positions",
            # 追加情報（後方互換性を保ちながら拡張）
            "win_rate": round(performance.win_rate, 4),
            "max_drawdown": round(performance.max_drawdown, 2),
            "sharpe_ratio": round(performance.sharpe_ratio, 4),
            "system_status": self.system_health.status,
            "current_risk_level": self.risk_metrics.current_risk_level,
        }

        with open(self.status_file, "w", encoding="utf-8") as f:
            json.dump(legacy_status, f, indent=2, ensure_ascii=False)

    def record_trade_entry(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        quantity: float,
        strategy_type: str = "unknown",
        confidence_score: float = 0.0,
        entry_fee: float = 0.0,
    ) -> str:
        """取引エントリー記録"""
        trade = TradeRecord(
            trade_id="",  # 自動生成される
            timestamp=datetime.now(),
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            quantity=quantity,
            entry_fee=entry_fee,
            strategy_type=strategy_type,
            confidence_score=confidence_score,
            market_conditions={
                "price": self.market_conditions.current_price,
                "volatility": self.market_conditions.volatility,
                "trend": self.market_conditions.trend,
                "bid_ask_spread": self.market_conditions.bid_ask_spread,
            },
            status="open",
        )

        trade_id = self.stats_manager.record_trade(trade)
        self.logger.info(f"取引エントリー記録: {trade_id}")

        return trade_id

    def record_trade_exit(
        self, trade_id: str, exit_price: float, exit_fee: float = 0.0
    ) -> bool:
        """取引エグジット記録"""
        success = self.stats_manager.close_trade(trade_id, exit_price, exit_fee)
        if success:
            self.logger.info(f"取引エグジット記録: {trade_id}")
        else:
            self.logger.error(f"取引エグジット記録失敗: {trade_id}")

        return success

    def update_market_data(
        self,
        price: float,
        volume: float = None,
        volatility: float = None,
        trend: str = None,
        **kwargs,
    ):
        """市場データ更新"""
        self.market_conditions.current_price = price

        if volume is not None:
            self.market_conditions.volume_24h = volume
        if volatility is not None:
            self.market_conditions.volatility = volatility
        if trend is not None:
            self.market_conditions.trend = trend

        # 追加パラメータ
        for key, value in kwargs.items():
            if hasattr(self.market_conditions, key):
                setattr(self.market_conditions, key, value)

        self.market_conditions.last_market_update = datetime.now().isoformat()

    def update_trading_signal(
        self,
        signal: str,
        strength: float,
        confidence: float,
        source: str = "ML",
        **kwargs,
    ):
        """取引シグナル更新"""
        self.trading_signals.current_signal = signal
        self.trading_signals.signal_strength = strength
        self.trading_signals.confidence_level = confidence
        self.trading_signals.signal_source = source

        # 追加パラメータ
        for key, value in kwargs.items():
            if hasattr(self.trading_signals, key):
                setattr(self.trading_signals, key, value)

        self.trading_signals.signal_generated_at = datetime.now().isoformat()

        self.logger.info(
            f"取引シグナル更新: {signal} (強度: {strength}, 信頼度: {confidence})"
        )

    def get_comprehensive_status(self) -> Dict[str, Any]:
        """包括的ステータス取得"""
        return {
            "timestamp": datetime.now().isoformat(),
            "system_health": asdict(self.system_health),
            "market_conditions": asdict(self.market_conditions),
            "trading_signals": asdict(self.trading_signals),
            "position_status": asdict(self.position_status),
            "risk_metrics": asdict(self.risk_metrics),
            "performance_summary": self.stats_manager.get_performance_summary(),
            "system_info": {
                "monitoring_active": self.is_running,
                "uptime_hours": (datetime.now() - self.start_time).total_seconds()
                / 3600,
                "update_interval": self.update_interval,
            },
        }

    def generate_status_report(self) -> str:
        """ステータスレポート生成"""
        report = []
        report.append("=" * 80)
        report.append("🎯 システム統合ステータスレポート")
        report.append("=" * 80)
        report.append(f"📅 生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # システムヘルス
        report.append("🖥️ システムヘルス:")
        report.append(f"   状況: {self.system_health.status}")
        report.append(f"   CPU使用率: {self.system_health.cpu_usage:.1f}%")
        report.append(f"   メモリ使用率: {self.system_health.memory_usage:.1f}%")
        report.append(f"   稼働時間: {self.system_health.uptime_hours:.1f}時間")
        report.append("")

        # ポジション状況
        report.append("📊 ポジション状況:")
        report.append(f"   総ポジション数: {self.position_status.total_positions}")
        report.append(f"   ロングポジション: {self.position_status.long_positions}")
        report.append(f"   ショートポジション: {self.position_status.short_positions}")
        report.append(
            f"   総エクスポージャー: {self.position_status.total_exposure:,.2f}円"
        )
        report.append("")

        # リスク指標
        report.append("⚠️ リスク指標:")
        report.append(f"   現在のリスクレベル: {self.risk_metrics.current_risk_level}")
        report.append(f"   VaR(95%): {self.risk_metrics.var_95:,.2f}円")
        report.append(
            f"   リスク調整リターン: {self.risk_metrics.risk_adjusted_return:.4f}"
        )
        report.append("")

        # 取引シグナル
        report.append("📡 最新取引シグナル:")
        report.append(f"   シグナル: {self.trading_signals.current_signal}")
        report.append(f"   強度: {self.trading_signals.signal_strength:.2f}")
        report.append(f"   信頼度: {self.trading_signals.confidence_level:.2f}")
        report.append(f"   ソース: {self.trading_signals.signal_source}")
        report.append("")

        # パフォーマンス要約
        perf = self.stats_manager.performance_metrics
        report.append("💰 パフォーマンス要約:")
        report.append(f"   総取引数: {perf.total_trades}")
        report.append(f"   勝率: {perf.win_rate:.2%}")
        report.append(f"   純利益: {perf.net_profit:,.2f}円")
        report.append(f"   ROI: {perf.roi:.2f}%")
        report.append("")

        report.append("=" * 80)

        return "\n".join(report)


def main():
    """テスト実行"""
    # 拡張ステータス管理システム初期化
    status_manager = EnhancedStatusManager()

    # 監視開始
    status_manager.start_monitoring()

    # テストデータ更新
    status_manager.update_market_data(
        price=3000000.0, volume=1000.0, volatility=0.02, trend="bullish"
    )

    status_manager.update_trading_signal(
        signal="buy", strength=0.8, confidence=0.7, source="ML_Enhanced"
    )

    # テスト取引記録
    _ = status_manager.record_trade_entry(
        symbol="BTC/JPY",
        side="buy",
        entry_price=3000000.0,
        quantity=0.0001,
        strategy_type="ML_Strategy",
        confidence_score=0.8,
    )

    # レポート生成
    print(status_manager.generate_status_report())

    # 監視停止
    time.sleep(2)
    status_manager.stop_monitoring()


if __name__ == "__main__":
    main()
