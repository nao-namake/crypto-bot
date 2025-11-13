"""
統合設定管理システム - Phase 49完了

環境変数とYAMLファイルの統合管理・unified.yaml統合デフォルト値

Phase 49完了:
- 3層設定体系（features.yaml・unified.yaml・thresholds.yaml）
- threshold_manager: 8専用アクセス関数・実行時オーバーライド対応（Phase 40.1 Optuna最適化）
- feature_manager: 55特徴量管理（Phase 41 Strategy-Aware ML）
- runtime_flags: バックテストモード・ペーパーモード制御（Phase 35）
Phase 28-29: 統合設定管理システム確立
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

from .config_classes import DataConfig, ExchangeConfig, LoggingConfig, MLConfig, RiskConfig

# Phase 35: ランタイムフラグシステム
from .runtime_flags import (
    get_all_flags,
    get_backtest_log_level,
    is_backtest_mode,
    is_paper_mode,
    reset_all_flags,
    set_backtest_log_level,
    set_backtest_mode,
    set_paper_mode,
)

# threshold_manager関数をインポートして再エクスポート
from .threshold_manager import (
    clear_runtime_overrides,
    get_all_thresholds,
    get_anomaly_config,
    get_backtest_config,
    get_data_config,
    get_file_config,
    get_monitoring_config,
    get_position_config,
    get_runtime_overrides,
    get_system_thresholds,
    get_threshold,
    get_trading_thresholds,
    load_thresholds,
    reload_thresholds,
    set_runtime_override,
    set_runtime_overrides_batch,
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
        YAMLファイルから設定を読み込み（モード設定一元化・thresholds.yaml統合）

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

        # モード設定一元化: コマンドライン > 環境変数 > YAML
        mode = "paper"

        if "mode" in config_data and config_data["mode"]:
            mode = config_data["mode"]

        env_mode = os.getenv("MODE")
        if env_mode:
            mode = env_mode.lower()

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
    def _create_generic_config(config_class, section_name: str, config_data: dict, extra_data: dict = None) -> any:
        """汎用設定作成メソッド（重複コード削減・深いマージ対応）"""
        data = config_data.get(section_name, {}).copy()

        # デフォルト値で深いマージ補完
        defaults = config_data.get(section_name, {})

        def deep_merge(base: dict, defaults: dict) -> dict:
            """深いマージ（デフォルト値で補完）"""
            for key, default_value in defaults.items():
                if key not in base or base[key] is None:
                    base[key] = default_value
                elif isinstance(base[key], dict) and isinstance(default_value, dict):
                    deep_merge(base[key], default_value)
            return base

        data = deep_merge(data, defaults)

        # 除外フィールド（MLConfigのみ）
        if section_name == "ml":
            excluded_fields = {"dynamic_confidence"}
            data = {k: v for k, v in data.items() if k not in excluded_fields}

        # extra_dataがある場合はマージ
        if extra_data:
            data.update(extra_data)

        return config_class(**data)

    @staticmethod
    def _create_exchange_config(config_data: dict, exchange_data: dict) -> ExchangeConfig:
        """取引所設定を作成（unified.yamlからデフォルト値取得）"""
        extra_data = {
            "api_key": os.getenv("BITBANK_API_KEY"),
            "api_secret": os.getenv("BITBANK_API_SECRET"),
        }
        # exchange_dataの内容をextra_dataに追加
        extra_data.update(exchange_data)

        return Config._create_generic_config(ExchangeConfig, "exchange", config_data, extra_data)

    @staticmethod
    def _create_ml_config(config_data: dict) -> MLConfig:
        """機械学習設定を作成（unified.yamlからデフォルト値取得）"""
        return Config._create_generic_config(MLConfig, "ml", config_data)

    @staticmethod
    def _create_risk_config(config_data: dict) -> RiskConfig:
        """リスク管理設定を作成（unified.yamlからデフォルト値取得）"""
        return Config._create_generic_config(RiskConfig, "risk", config_data)

    @staticmethod
    def _create_data_config(config_data: dict) -> DataConfig:
        """データ取得設定を作成（unified.yamlからデフォルト値取得）"""
        return Config._create_generic_config(DataConfig, "data", config_data)

    @staticmethod
    def _create_logging_config(config_data: dict) -> LoggingConfig:
        """ログ設定を作成（unified.yamlからデフォルト値取得）"""
        return Config._create_generic_config(LoggingConfig, "logging", config_data)

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


# === Phase 31.1: features.yaml読み込みAPI ===

# グローバルキャッシュ
_features_config_cache: Optional[dict] = None


def load_features_config(force_reload: bool = False) -> dict:
    """
    features.yamlを読み込む（キャッシュ付き）

    Args:
        force_reload: 強制再読み込みフラグ

    Returns:
        features.yaml の内容（辞書）
    """
    global _features_config_cache

    if _features_config_cache is not None and not force_reload:
        return _features_config_cache

    features_path = Path("config/core/features.yaml")

    if not features_path.exists():
        raise FileNotFoundError(f"features.yaml が見つかりません: {features_path}")

    try:
        with open(features_path, "r", encoding="utf-8") as f:
            _features_config_cache = yaml.safe_load(f) or {}
        return _features_config_cache
    except Exception as e:
        raise RuntimeError(f"features.yaml 読み込みエラー: {e}")


def get_features_config() -> dict:
    """
    features.yamlの内容を取得（キャッシュ使用）

    Returns:
        features.yaml の内容（辞書）
    """
    return load_features_config()


def reload_features_config() -> dict:
    """
    features.yamlを強制再読み込み

    Returns:
        features.yaml の内容（辞書）
    """
    return load_features_config(force_reload=True)


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
    # Phase 40.1: 実行時オーバーライド機能
    "set_runtime_override",
    "set_runtime_overrides_batch",
    "clear_runtime_overrides",
    "get_runtime_overrides",
    # features.yaml管理関数（Phase 31.1）
    "load_features_config",
    "get_features_config",
    "reload_features_config",
    # ランタイムフラグ管理関数（Phase 35）
    "set_backtest_mode",
    "is_backtest_mode",
    "set_paper_mode",
    "is_paper_mode",
    "set_backtest_log_level",
    "get_backtest_log_level",
    "reset_all_flags",
    "get_all_flags",
]
