"""
閾値設定管理システム - Phase 65.12

thresholds.yaml統合管理・6専用アクセス関数

Phase 65.12: unified.yaml統合（2→1ファイル体系・thresholds.yaml単一読み込み）
Phase 64.13: Optuna runtime override削除・未使用アクセサ削除
Phase 28-29: 閾値設定管理システム確立
"""

import copy
from pathlib import Path
from typing import Any, Dict

import yaml

# キャッシュ変数
_thresholds_cache: Dict[str, Any] = None


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    辞書の深いマージ

    baseの値をoverrideの値で上書き。overrideに存在しないキーはbaseの値を保持。

    Args:
        base: ベース辞書
        override: 上書き辞書

    Returns:
        マージ済み辞書
    """
    result = copy.deepcopy(base)

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # 両方とも辞書の場合は再帰的にマージ
            result[key] = _deep_merge(result[key], value)
        else:
            # それ以外はoverrideの値で上書き
            result[key] = copy.deepcopy(value)

    return result


def load_thresholds() -> Dict[str, Any]:
    """
    設定をYAMLファイルから読み込み（Phase 65.12: thresholds.yaml単一ファイル）

    Returns:
        設定辞書
    """
    global _thresholds_cache

    if _thresholds_cache is not None:
        return _thresholds_cache

    config_path = Path("config/core/thresholds.yaml")
    try:
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                _thresholds_cache = yaml.safe_load(f) or {}
        else:
            print(f"⚠️ 設定ファイルが存在しません: {config_path}")
            _thresholds_cache = {}
    except Exception as e:
        print(f"⚠️ 設定読み込みエラー: {e}")
        _thresholds_cache = {}

    return _thresholds_cache


def get_threshold(key_path: str, default_value: Any = None) -> Any:
    """
    階層キーで設定値を取得

    Args:
        key_path: ドット記法のキー（例: "ml.default_confidence"）
        default_value: デフォルト値

    Returns:
        設定値またはデフォルト値

    Examples:
        >>> get_threshold("ml.default_confidence", 0.5)
        0.5
        >>> get_threshold("mode_balances.backtest.initial_balance", 100000.0)
        500000.0
    """
    thresholds = load_thresholds()

    keys = key_path.split(".")
    current_value = thresholds

    try:
        for key in keys:
            current_value = current_value[key]
        return current_value
    except (KeyError, TypeError):
        if default_value is not None:
            return default_value
        raise KeyError(f"閾値設定が見つかりません: {key_path}")


def reload_thresholds() -> None:
    """閾値設定のキャッシュをクリアして再読み込み."""
    global _thresholds_cache
    _thresholds_cache = None
    load_thresholds()


def get_all_thresholds() -> Dict[str, Any]:
    """全閾値設定を取得（デバッグ用）."""
    return copy.deepcopy(load_thresholds())


# ========================================
# Phase 22: 専用アクセス関数（可読性・保守性向上・ハードコード排除）
# ========================================


def get_monitoring_config(key: str, default: Any = None) -> Any:
    """
    監視関連設定取得

    Args:
        key: 監視設定のキー（例: "discord.min_interval"）
        default: デフォルト値

    Examples:
        >>> get_monitoring_config("discord.min_interval", 2)
        2
        >>> get_monitoring_config("health_check.interval_seconds", 60.0)
        60.0
    """
    return get_threshold(f"monitoring.{key}", default)


def get_anomaly_config(key: str, default: Any = None) -> Any:
    """
    異常検知設定取得

    Args:
        key: 異常検知設定のキー（例: "spread.warning_threshold"）
        default: デフォルト値

    Examples:
        >>> get_anomaly_config("spread.warning_threshold", 0.003)
        0.003
        >>> get_anomaly_config("spike_detection.price_zscore_threshold", 3.0)
        3.0
    """
    return get_threshold(f"anomaly_detection.{key}", default)


def get_position_config(key: str, default: Any = None) -> Any:
    """
    ポジション管理設定取得

    Args:
        key: ポジション管理設定のキー（例: "kelly_criterion.max_position_ratio"）
        default: デフォルト値

    Examples:
        >>> get_position_config("kelly_criterion.max_position_ratio", 0.03)
        0.03
        >>> get_position_config("drawdown.consecutive_loss_limit", 5)
        5
    """
    return get_threshold(f"position_management.{key}", default)


def get_backtest_config(key: str, default: Any = None) -> Any:
    """
    バックテスト設定取得

    Args:
        key: バックテスト設定のキー（例: "stop_loss.default_rate"）
        default: デフォルト値

    Examples:
        >>> get_backtest_config("stop_loss.default_rate", 0.02)
        0.02
        >>> get_backtest_config("data.bitbank_limit", 2000)
        2000
    """
    return get_threshold(f"backtest.{key}", default)


def get_data_config(key: str, default: Any = None) -> Any:
    """
    データ取得設定取得

    Args:
        key: データ取得設定のキー（例: "limits.default"）
        default: デフォルト値

    Examples:
        >>> get_data_config("limits.default", 100)
        100
        >>> get_data_config("timeframes.default", ["15m", "1h", "4h"])
        ["15m", "1h", "4h"]
    """
    return get_threshold(f"data_fetching.{key}", default)


def get_file_config(key: str, default: Any = None) -> Any:
    """
    ファイルI/O設定取得

    Args:
        key: ファイルI/O設定のキー（例: "logging.retention_days"）
        default: デフォルト値

    Examples:
        >>> get_file_config("logging.retention_days", 7)
        7
        >>> get_file_config("reports.max_files", 100)
        100
    """
    return get_threshold(f"file_io.{key}", default)
