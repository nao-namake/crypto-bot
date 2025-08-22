"""
設定管理システム - 環境変数とYAMLファイルの統合管理

レガシーシステムの420行の設定から、重要な項目のみを抽出してシンプル化。
環境変数での機密情報管理とYAMLでの構造化設定を統合。.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


@dataclass
class ExchangeConfig:
    """取引所接続設定."""

    name: str = "bitbank"
    symbol: str = "BTC/JPY"
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    rate_limit_ms: int = 30000
    timeout_ms: int = 90000
    retries: int = 3


@dataclass
class MLConfig:
    """機械学習設定."""

    confidence_threshold: float = 0.35
    ensemble_enabled: bool = True
    models: list = None
    model_weights: list = None

    def __post_init__(self):
        if self.models is None:
            self.models = ["lgbm", "xgb", "rf"]
        if self.model_weights is None:
            self.model_weights = [0.5, 0.3, 0.2]


@dataclass
class RiskConfig:
    """リスク管理設定."""

    risk_per_trade: float = 0.01  # 1取引あたり1%
    kelly_max_fraction: float = 0.03  # Kelly基準最大3%
    max_drawdown: float = 0.20  # 最大ドローダウン20%
    stop_loss_atr_multiplier: float = 1.2
    consecutive_loss_limit: int = 5  # 連続損失限界


@dataclass
class DataConfig:
    """データ取得設定."""

    timeframes: list = None
    since_hours: int = 96  # 4日分
    limit: int = 100
    cache_enabled: bool = True

    def __post_init__(self):
        if self.timeframes is None:
            self.timeframes = ["15m", "1h", "4h"]


@dataclass
class LoggingConfig:
    """ログ設定."""

    level: str = "INFO"
    file_enabled: bool = True
    discord_enabled: bool = True
    retention_days: int = 7


@dataclass
class Config:
    """統合設定クラス."""

    exchange: ExchangeConfig
    ml: MLConfig
    risk: RiskConfig
    data: DataConfig
    logging: LoggingConfig
    mode: str = "paper"  # paper, live

    @classmethod
    def load_from_file(cls, config_path: str) -> "Config":
        """YAMLファイルから設定を読み込み."""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")

        with open(config_file, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        # 環境変数から機密情報を取得
        exchange_config = ExchangeConfig(
            **config_data.get("exchange", {}),
            api_key=os.getenv("BITBANK_API_KEY"),
            api_secret=os.getenv("BITBANK_API_SECRET"),
        )

        ml_config = MLConfig(**config_data.get("ml", {}))
        risk_config = RiskConfig(**config_data.get("risk", {}))
        data_config = DataConfig(**config_data.get("data", {}))
        logging_config = LoggingConfig(**config_data.get("logging", {}))

        return cls(
            exchange=exchange_config,
            ml=ml_config,
            risk=risk_config,
            data=data_config,
            logging=logging_config,
            mode=config_data.get("mode", "paper"),
        )

    def validate(self) -> bool:
        """設定の妥当性をチェック."""
        errors = []

        # API認証情報チェック（本番モードのみ）
        if self.mode == "live":
            if not self.exchange.api_key:
                errors.append("BITBANK_API_KEY環境変数が設定されていません")
            if not self.exchange.api_secret:
                errors.append("BITBANK_API_SECRET環境変数が設定されていません")

        # リスク設定チェック
        if self.risk.risk_per_trade <= 0 or self.risk.risk_per_trade > 0.05:
            errors.append("risk_per_tradeは0.001-0.05の範囲で設定してください")

        if self.risk.max_drawdown <= 0 or self.risk.max_drawdown > 0.5:
            errors.append("max_drawdownは0.1-0.5の範囲で設定してください")

        # ML設定チェック
        if self.ml.confidence_threshold <= 0 or self.ml.confidence_threshold > 1:
            errors.append("confidence_thresholdは0-1の範囲で設定してください")

        if len(self.ml.models) != len(self.ml.model_weights):
            errors.append("modelsとmodel_weightsの数が一致していません")

        # データ設定チェック
        if self.data.since_hours <= 0 or self.data.since_hours > 168:
            errors.append("since_hoursは1-168時間の範囲で設定してください")

        if errors:
            print("⚠️ 設定エラー:")
            for error in errors:
                print(f"  - {error}")
            return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        """設定をDict形式で返す（IntegratedRiskManager等での利用）."""
        return {
            "mode": self.mode,
            "exchange": {
                "name": self.exchange.name,
                "symbol": self.exchange.symbol,
                "rate_limit_ms": self.exchange.rate_limit_ms,
                "timeout_ms": self.exchange.timeout_ms,
                "retries": self.exchange.retries,
            },
            "ml": {
                "confidence_threshold": self.ml.confidence_threshold,
                "ensemble_enabled": self.ml.ensemble_enabled,
                "models": self.ml.models,
                "model_weights": self.ml.model_weights,
            },
            "risk": {
                "risk_per_trade": self.risk.risk_per_trade,
                "kelly_max_fraction": self.risk.kelly_max_fraction,
                "max_drawdown": self.risk.max_drawdown,
                "stop_loss_atr_multiplier": self.risk.stop_loss_atr_multiplier,
                "consecutive_loss_limit": self.risk.consecutive_loss_limit,
            },
            "data": {
                "timeframes": self.data.timeframes,
                "since_hours": self.data.since_hours,
                "limit": self.data.limit,
                "cache_enabled": self.data.cache_enabled,
            },
            "logging": {
                "level": self.logging.level,
                "file_enabled": self.logging.file_enabled,
                "discord_enabled": self.logging.discord_enabled,
                "retention_days": self.logging.retention_days,
            },
            # リスク管理で使用される設定項目
            "kelly_criterion": {
                "max_position_ratio": self.risk.kelly_max_fraction,
                "safety_factor": 0.5,  # デフォルト値
                "min_trades_for_kelly": 20,  # デフォルト値
            },
            "drawdown_manager": {
                "max_drawdown_ratio": self.risk.max_drawdown,
                "consecutive_loss_limit": self.risk.consecutive_loss_limit,
                "cooldown_hours": 24,  # デフォルト値
            },
            "anomaly_detector": {
                "lookback_period": 20,  # デフォルト値
            }
        }

    def get_summary(self) -> Dict[str, Any]:
        """設定のサマリーを取得（機密情報除外）."""
        return {
            "mode": self.mode,
            "exchange": {
                "name": self.exchange.name,
                "symbol": self.exchange.symbol,
                "rate_limit_ms": self.exchange.rate_limit_ms,
                "api_key_set": bool(self.exchange.api_key),
            },
            "ml": {
                "confidence_threshold": self.ml.confidence_threshold,
                "ensemble_enabled": self.ml.ensemble_enabled,
                "models": self.ml.models,
            },
            "risk": {
                "risk_per_trade": self.risk.risk_per_trade,
                "kelly_max_fraction": self.risk.kelly_max_fraction,
                "max_drawdown": self.risk.max_drawdown,
            },
            "data": {
                "timeframes": self.data.timeframes,
                "since_hours": self.data.since_hours,
                "cache_enabled": self.data.cache_enabled,
            },
        }


class ConfigManager:
    """設定管理クラス."""

    def __init__(self):
        self._config: Optional[Config] = None
        self._config_path: Optional[str] = None

    def load_config(self, config_path: str) -> Config:
        """設定ファイルを読み込み."""
        self._config = Config.load_from_file(config_path)
        self._config_path = config_path

        if not self._config.validate():
            raise ValueError("設定の検証に失敗しました")

        return self._config

    def get_config(self) -> Config:
        """現在の設定を取得."""
        if self._config is None:
            raise RuntimeError("設定が読み込まれていません。load_config()を先に実行してください")
        return self._config

    def reload_config(self) -> Config:
        """設定を再読み込み."""
        if self._config_path is None:
            raise RuntimeError("設定ファイルパスが不明です")
        return self.load_config(self._config_path)


# グローバル設定マネージャー（シングルトン）
config_manager = ConfigManager()


def get_config() -> Config:
    """グローバル設定を取得."""
    return config_manager.get_config()


def load_config(config_path: str) -> Config:
    """設定を読み込み."""
    return config_manager.load_config(config_path)
