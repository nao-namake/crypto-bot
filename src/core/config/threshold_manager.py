"""
閾値設定管理システム - Phase 38.4完了版

thresholds.yaml統合管理・8個専用アクセス関数実装・フォールバック値削除

Phase 28-29最適化: 閾値設定管理システム確立
Phase 38: trading層レイヤードアーキテクチャ実装完了
Phase 38.4: 全モジュールPhase統一・コード品質保証完了
"""

import copy
from pathlib import Path
from typing import Any, Dict

import yaml

# キャッシュ変数
_thresholds_cache: Dict[str, Any] = None

# Phase 40.1: 実行時パラメータオーバーライド（Optuna最適化用）
_runtime_overrides: Dict[str, Any] = {}


def load_thresholds() -> Dict[str, Any]:
    """閾値設定をYAMLファイルから読み込み."""
    global _thresholds_cache

    if _thresholds_cache is not None:
        return _thresholds_cache

    thresholds_path = Path("config/core/thresholds.yaml")

    try:
        if thresholds_path.exists():
            with open(thresholds_path, "r", encoding="utf-8") as f:
                _thresholds_cache = yaml.safe_load(f) or {}
        else:
            print(f"⚠️ 閾値設定ファイルが存在しません: {thresholds_path}")
            _thresholds_cache = {}
    except Exception as e:
        print(f"⚠️ 閾値設定読み込みエラー: {e}")
        _thresholds_cache = {}

    return _thresholds_cache


def get_threshold(key_path: str, default_value: Any = None) -> Any:
    """
    階層キーで閾値設定を取得（Phase 40.1: 実行時オーバーライド対応）

    優先順位:
    1. 実行時オーバーライド（Optuna最適化時）
    2. thresholds.yaml設定値
    3. default_value

    Args:
        key_path: ドット記法のキー（例: "ml.default_confidence"）
        default_value: デフォルト値

    Returns:
        設定値またはデフォルト値

    Examples:
        >>> get_threshold("ml.default_confidence", 0.5)
        0.5
        >>> get_threshold("trading.default_balance_jpy", 1000000.0)
        1000000.0
    """
    # Phase 40.1: 実行時オーバーライドを最優先でチェック
    if key_path in _runtime_overrides:
        return _runtime_overrides[key_path]

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


def get_trading_thresholds() -> Dict[str, Any]:
    """取引関連の閾値設定を一括取得."""
    return get_threshold("trading", {})


def get_system_thresholds() -> Dict[str, Any]:
    """システム関連の閾値設定を一括取得."""
    return get_threshold("system", {})


# ========================================
# Phase 40.1: 実行時パラメータオーバーライド機能（Optuna最適化用）
# ========================================


def set_runtime_override(key_path: str, value: Any) -> None:
    """
    実行時パラメータオーバーライド設定（Optuna最適化用）

    Args:
        key_path: ドット記法のキー（例: "position_management.stop_loss.default_atr_multiplier"）
        value: 設定する値

    Examples:
        >>> set_runtime_override("position_management.stop_loss.default_atr_multiplier", 2.5)
        >>> get_threshold("position_management.stop_loss.default_atr_multiplier")
        2.5
    """
    _runtime_overrides[key_path] = value


def set_runtime_overrides_batch(overrides: Dict[str, Any]) -> None:
    """
    実行時パラメータを一括オーバーライド（Optuna最適化用）

    Args:
        overrides: キーと値の辞書

    Examples:
        >>> set_runtime_overrides_batch({
        ...     "position_management.stop_loss.default_atr_multiplier": 2.5,
        ...     "position_management.take_profit.default_ratio": 3.0,
        ... })
    """
    _runtime_overrides.update(overrides)


def clear_runtime_overrides() -> None:
    """
    全実行時オーバーライドをクリア

    Optuna最適化終了後やバックテスト完了後に使用
    """
    global _runtime_overrides
    _runtime_overrides = {}


def get_runtime_overrides() -> Dict[str, Any]:
    """
    現在の実行時オーバーライド設定を取得（デバッグ用）

    Returns:
        実行時オーバーライド設定の辞書
    """
    return copy.deepcopy(_runtime_overrides)
