"""
統合設定管理システム - Phase 17 config階層化
環境変数とYAMLファイルの統合管理・設定一元化
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

from .config_classes import (
    DataConfig,
    ExchangeConfig,
    LoggingConfig,
    MLConfig,
    RiskConfig,
)

# threshold_manager関数をインポートして再エクスポート
from .threshold_manager import (
    get_all_thresholds,
    get_anomaly_config,
    get_backtest_config,
    get_data_config,
    get_file_config,
    get_monitoring_config,
    get_position_config,
    get_system_thresholds,
    get_threshold,
    get_trading_thresholds,
    load_thresholds,
    reload_thresholds,
)


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
    def load_from_file(cls, config_path: str, cmdline_mode: Optional[str] = None) -> "Config":
        """
        YAMLファイルから設定を読み込み（モード設定一元化・3層優先順位）
        ハードコーディング排除版 - thresholds.yamlと統合ロード

        モード設定の優先順位:
        1. コマンドライン引数（最優先）
        2. 環境変数 MODE
        3. YAMLファイル（デフォルト）

        設定値の優先順位:
        1. メインYAMLファイル（config_path）
        2. thresholds.yaml（フォールバック値）
        3. 組み込みデフォルト値

        Args:
            config_path: 設定ファイルパス
            cmdline_mode: コマンドライン引数で指定されたモード

        Returns:
            設定済みConfigオブジェクト
        """
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")

        # メインYAMLファイル読み込み
        with open(config_file, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f) or {}

        # thresholds.yamlを統合ロード（フォールバック値として使用）
        try:
            thresholds_data = load_thresholds()
            # 設定データをthresholdsで補完
            config_data = cls._merge_config_with_thresholds(config_data, thresholds_data)
        except Exception as e:
            # thresholds.yaml読み込み失敗時は警告を出して継続
            print(f"⚠️ thresholds.yaml読み込み失敗: {e}")

        # 🎯 モード設定一元化: 3層優先順位の実装
        mode = "paper"  # デフォルト

        # レイヤー3: YAMLファイル（最低優先）
        if "mode" in config_data and config_data["mode"]:
            mode = config_data["mode"]

        # レイヤー2: 環境変数（中優先）
        env_mode = os.getenv("MODE")
        if env_mode:
            mode = env_mode.lower()

        # レイヤー1: コマンドライン引数（最優先）
        if cmdline_mode:
            mode = cmdline_mode.lower()

        # モード検証
        valid_modes = ["paper", "live", "backtest"]
        if mode not in valid_modes:
            raise ValueError(f"無効なモード: {mode}. 有効な値: {valid_modes}")

        # 環境変数から機密情報を取得（YAMLの機密情報は除外）
        exchange_data = config_data.get("exchange", {}).copy()
        # YAMLファイルからapi_key/api_secretを除外（環境変数を優先）
        exchange_data.pop("api_key", None)
        exchange_data.pop("api_secret", None)

        # 設定クラスの作成（デフォルト値補完付き）
        exchange_config = cls._create_exchange_config(config_data, exchange_data)
        ml_config = cls._create_ml_config(config_data)
        risk_config = cls._create_risk_config(config_data)
        data_config = cls._create_data_config(config_data)
        logging_config = cls._create_logging_config(config_data)

        return cls(
            exchange=exchange_config,
            ml=ml_config,
            risk=risk_config,
            data=data_config,
            logging=logging_config,
            mode=mode,
        )

    @staticmethod
    def _merge_config_with_thresholds(config_data: dict, thresholds_data: dict) -> dict:
        """設定データとthresholdsデータをマージ（深いマージ + フィールド名正規化）"""

        def deep_merge(base: dict, updates: dict) -> dict:
            """深いマージ（ベースの値を優先）"""
            result = base.copy()
            for key, value in updates.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                elif key not in result:  # ベースにない場合のみ追加
                    result[key] = value
            return result

        # フィールド名の正規化（thresholds.yamlのキー名をdataclassのフィールド名に変換）
        normalized_thresholds = Config._normalize_threshold_keys(thresholds_data)
        return deep_merge(config_data, normalized_thresholds)

    @staticmethod
    def _normalize_threshold_keys(thresholds_data: dict) -> dict:
        """thresholds.yamlのキー名をdataclassフィールド名に正規化"""
        result = {}

        for section, values in thresholds_data.items():
            if not isinstance(values, dict):
                result[section] = values
                continue

            normalized_section = {}

            # セクション別の正規化ルール
            if section == "ml":
                # MLセクションのフィールド名マッピング
                field_mapping = {"default_confidence": "confidence_threshold"}  # 重要な修正
                for key, value in values.items():
                    normalized_key = field_mapping.get(key, key)
                    normalized_section[normalized_key] = value
            else:
                # その他のセクションはそのまま
                normalized_section = values

            result[section] = normalized_section

        return result

    @staticmethod
    def _create_exchange_config(config_data: dict, exchange_data: dict) -> ExchangeConfig:
        """取引所設定を作成（デフォルト値補完付き）"""
        defaults = {
            "name": "bitbank",
            "symbol": "BTC/JPY",
            "leverage": 1.0,
            "rate_limit_ms": 35000,
            "timeout_ms": 120000,
            "retries": 5,
            "ssl_verify": True,
            "api_version": "v1",
        }

        # デフォルト値とマージ
        for key, default_value in defaults.items():
            if key not in exchange_data or exchange_data[key] is None:
                exchange_data[key] = default_value

        return ExchangeConfig(
            **exchange_data,
            api_key=os.getenv("BITBANK_API_KEY"),
            api_secret=os.getenv("BITBANK_API_SECRET"),
        )

    @staticmethod
    def _create_ml_config(config_data: dict) -> MLConfig:
        """機械学習設定を作成（デフォルト値補完付き）"""
        ml_data = config_data.get("ml", {}).copy()  # コピーして元データを保護

        # dynamic_confidenceはMLConfigに渡さない（get_thresholdで直接アクセスするため）
        if "dynamic_confidence" in ml_data:
            del ml_data["dynamic_confidence"]
        defaults = {
            "confidence_threshold": 0.65,
            "ensemble_enabled": True,
            "models": ["lgbm", "xgb", "rf"],
            "model_weights": [0.5, 0.3, 0.2],
            "model_path": None,
            "model_update_check": False,
            "fallback_enabled": True,
            "prediction": {"lookback_periods": 100, "retrain_frequency": "weekly"},
        }

        for key, default_value in defaults.items():
            if key not in ml_data or ml_data[key] is None:
                ml_data[key] = default_value

        return MLConfig(**ml_data)

    @staticmethod
    def _create_risk_config(config_data: dict) -> RiskConfig:
        """リスク管理設定を作成（デフォルト値補完付き）"""
        risk_data = config_data.get("risk", {})
        defaults = {
            "risk_per_trade": 0.01,
            "kelly_max_fraction": 0.03,
            "max_drawdown": 0.20,
            "stop_loss_atr_multiplier": 1.2,
            "consecutive_loss_limit": 5,
            "take_profit_ratio": 2.0,
            "daily_loss_limit": 0.05,
            "weekly_loss_limit": 0.10,
            "emergency_stop_enabled": True,
            "kelly_criterion": {
                "max_position_ratio": 0.05,
                "safety_factor": 0.7,
                "min_trades_for_kelly": 20,
            },
            "drawdown_manager": {
                "max_drawdown_ratio": 0.20,
                "consecutive_loss_limit": 5,
                "cooldown_hours": 24,
            },
            "anomaly_detector": {
                "lookback_period": 20,
            },
            "risk_thresholds": {
                "min_ml_confidence": 0.5,
                "risk_threshold_deny": 0.8,
                "risk_threshold_conditional": 0.6,
            },
        }

        for key, default_value in defaults.items():
            if key not in risk_data or risk_data[key] is None:
                risk_data[key] = default_value

        return RiskConfig(**risk_data)

    @staticmethod
    def _create_data_config(config_data: dict) -> DataConfig:
        """データ取得設定を作成（デフォルト値補完付き）"""
        data_data = config_data.get("data", {})
        defaults = {
            "timeframes": ["15m", "1h", "4h"],
            "since_hours": 96,
            "limit": 100,
            "cache_enabled": True,
            "cache": {
                "enabled": True,
                "ttl_minutes": 5,
                "max_size": 1000,
                "disk_cache": True,
                "retention_days": 90,
            },
        }

        for key, default_value in defaults.items():
            if key not in data_data or data_data[key] is None:
                data_data[key] = default_value

        return DataConfig(**data_data)

    @staticmethod
    def _create_logging_config(config_data: dict) -> LoggingConfig:
        """ログ設定を作成（デフォルト値補完付き）"""
        logging_data = config_data.get("logging", {})
        defaults = {
            "level": "INFO",
            "file_enabled": True,
            "discord_enabled": True,
            "retention_days": 7,
            "file": {
                "enabled": True,
                "path": "logs/production",
                "rotation": "daily",
                "retention_days": 30,
                "max_size_mb": 100,
            },
            "discord": {
                "enabled": True,
                "webhook_url": "${DISCORD_WEBHOOK_URL}",
                "levels": {"critical": True, "warning": True, "info": False},
            },
        }

        for key, default_value in defaults.items():
            if key not in logging_data or logging_data[key] is None:
                logging_data[key] = default_value

        return LoggingConfig(**logging_data)

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
            errors.append("max_drawdownは0.01-0.5の範囲で設定してください")

        # エラーがある場合は出力して失敗
        if errors:
            for error in errors:
                print(f"❌ 設定エラー: {error}")
            return False

        return True


class ConfigManager:
    """設定管理クラス."""

    def __init__(self) -> None:
        self._config: Optional[Config] = None
        self._config_path: Optional[str] = None

    def load_config(self, config_path: str, cmdline_mode: Optional[str] = None) -> Config:
        """設定ファイルを読み込み（モード設定一元化対応）."""
        self._config = Config.load_from_file(config_path, cmdline_mode=cmdline_mode)
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


def load_config(config_path: str, cmdline_mode: Optional[str] = None) -> Config:
    """設定を読み込み（モード設定一元化対応）."""
    return config_manager.load_config(config_path, cmdline_mode=cmdline_mode)


# 分離されたクラスと関数を再エクスポート
__all__ = [
    # 設定クラス
    "Config",
    "ConfigManager",
    "ExchangeConfig",
    "MLConfig",
    "RiskConfig",
    "DataConfig",
    "LoggingConfig",
    # 設定管理関数
    "get_config",
    "load_config",
    "config_manager",
    # 閾値管理関数
    "get_threshold",
    "load_thresholds",
    "reload_thresholds",
    "get_all_thresholds",
    "get_monitoring_config",
    "get_anomaly_config",
    "get_position_config",
    "get_backtest_config",
    "get_data_config",
    "get_file_config",
    "get_trading_thresholds",
    "get_system_thresholds",
]
