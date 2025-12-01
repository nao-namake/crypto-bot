"""
閾値設定管理システム - Phase 57.5

thresholds.yaml統合管理・プリセット機能・8専用アクセス関数・実行時オーバーライド対応。

機能:
- get_threshold(): 階層キーアクセス（"position_management.stop_loss.max_loss_ratio"）
- 8専用アクセス関数: get_trading_thresholds・get_monitoring_config等
- 実行時オーバーライド（Optuna最適化対応）
- thresholds.yamlキャッシュ・reload_thresholds()再読み込み
- Phase 57.5: プリセットシステム（戦略設定の変数化・ロールバック機能）

Phase 57.5 プリセットシステム:
- active.yamlで使用するプリセットを選択
- presets/*.yamlに各フェーズの設定を保存
- 優先順位: runtime_overrides > preset > thresholds.yaml > default
"""

import copy
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

# キャッシュ変数
_thresholds_cache: Dict[str, Any] = None

# Phase 40.1: 実行時パラメータオーバーライド（Optuna最適化用）
_runtime_overrides: Dict[str, Any] = {}

# Phase 57.5: プリセットキャッシュ
_preset_cache: Optional[Dict[str, Any]] = None
_active_preset_name: Optional[str] = None


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


# ========================================
# Phase 57.5: プリセットシステム
# ========================================


def load_active_preset() -> Dict[str, Any]:
    """
    Phase 57.5: アクティブなプリセットを読み込み

    優先順位: active.yaml → presets/xxx.yaml → 空辞書

    Returns:
        プリセット設定辞書（存在しない場合は空辞書）
    """
    global _preset_cache, _active_preset_name

    # キャッシュがあれば返す
    if _preset_cache is not None:
        return _preset_cache

    active_path = Path("config/core/strategies/active.yaml")

    # active.yamlが存在しない場合は従来動作（プリセットなし）
    if not active_path.exists():
        _preset_cache = {}
        _active_preset_name = None
        return _preset_cache

    try:
        with open(active_path, "r", encoding="utf-8") as f:
            active_config = yaml.safe_load(f) or {}

        preset_name = active_config.get("active_preset", "")
        if not preset_name:
            _preset_cache = {}
            _active_preset_name = None
            return _preset_cache

        # プリセットファイル読み込み
        preset_path = Path(f"config/core/strategies/presets/{preset_name}.yaml")
        if not preset_path.exists():
            print(f"⚠️ プリセットファイルが存在しません: {preset_path}")
            _preset_cache = {}
            _active_preset_name = None
            return _preset_cache

        with open(preset_path, "r", encoding="utf-8") as f:
            _preset_cache = yaml.safe_load(f) or {}
            _active_preset_name = preset_name
            print(f"📋 プリセット読み込み完了: {preset_name}")

    except Exception as e:
        print(f"⚠️ プリセット読み込みエラー: {e}")
        _preset_cache = {}
        _active_preset_name = None

    return _preset_cache


def _get_nested_value(data: Dict[str, Any], key_path: str) -> Optional[Any]:
    """
    ネストされた辞書から値を取得

    Args:
        data: 辞書データ
        key_path: ドット区切りのキーパス（例: "strategies.atr_based.min_confidence"）

    Returns:
        値（存在しない場合はNone）
    """
    keys = key_path.split(".")
    current = data

    try:
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current
    except (KeyError, TypeError):
        return None


def _convert_preset_key_to_threshold_key(key_path: str) -> Optional[str]:
    """
    Phase 57.5: プリセットのキーパスをthresholds.yamlのキーパスに変換

    Args:
        key_path: thresholds.yamlのキーパス

    Returns:
        プリセット内の対応キーパス（マッピングがない場合はNone）
    """
    # プリセットキー → thresholds.yamlキーのマッピング
    # 逆引きで使用
    preset_mappings = {
        # 戦略有効化
        "dynamic_strategy_selection.regime_active_strategies": "regime_active_strategies",
        # 戦略重み
        "dynamic_strategy_selection.regime_strategy_mapping": "regime_strategy_mapping",
        # TP設定
        "position_management.take_profit.regime_based.tight_range": "take_profit.tight_range",
        "position_management.take_profit.regime_based.normal_range": "take_profit.normal_range",
        "position_management.take_profit.regime_based.trending": "take_profit.trending",
        "position_management.take_profit.regime_based.high_volatility": "take_profit.high_volatility",
        # SL設定
        "position_management.stop_loss.regime_based.tight_range": "stop_loss.tight_range",
        "position_management.stop_loss.regime_based.normal_range": "stop_loss.normal_range",
        "position_management.stop_loss.regime_based.trending": "stop_loss.trending",
        "position_management.stop_loss.regime_based.high_volatility": "stop_loss.high_volatility",
        # ML統合
        "ml.strategy_integration": "ml_integration",
        "ml.strategy_integration.hold_conversion_threshold": "ml_integration.hold_conversion_threshold",
        "ml.strategy_integration.min_ml_confidence": "ml_integration.min_ml_confidence",
        "ml.strategy_integration.high_confidence_threshold": "ml_integration.high_confidence_threshold",
        "ml.strategy_integration.disagreement_penalty": "ml_integration.disagreement_penalty",
        "ml.strategy_integration.ml_weight": "ml_integration.ml_weight",
        "ml.strategy_integration.strategy_weight": "ml_integration.strategy_weight",
        "ml.strategy_integration.agreement_bonus": "ml_integration.agreement_bonus",
        # レジーム別ML統合
        "ml.regime_ml_integration": "regime_ml_integration",
        "ml.regime_ml_integration.tight_range": "regime_ml_integration.tight_range",
        "ml.regime_ml_integration.normal_range": "regime_ml_integration.normal_range",
        "ml.regime_ml_integration.trending": "regime_ml_integration.trending",
        # 信頼度レベル
        "trading.confidence_levels": "confidence_levels",
        "trading.confidence_levels.high": "confidence_levels.high",
        "trading.confidence_levels.medium": "confidence_levels.medium",
        "trading.confidence_levels.low": "confidence_levels.low",
        "trading.confidence_levels.min_ml": "confidence_levels.min_ml",
        "trading.confidence_levels.very_high": "confidence_levels.very_high",
        # 戦略パラメータ
        "strategies.atr_based": "strategies.atr_based",
        "strategies.bb_reversal": "strategies.bb_reversal",
        "strategies.stochastic_reversal": "strategies.stochastic_reversal",
        "strategies.donchian_channel": "strategies.donchian_channel",
        "strategies.adx_trend": "strategies.adx_trend",
        "strategies.macd_ema_crossover": "strategies.macd_ema_crossover",
        # レジーム判定
        "market_regime": "market_regime",
        "market_regime.tight_range": "market_regime.tight_range",
        "market_regime.normal_range": "market_regime.normal_range",
        "market_regime.trending": "market_regime.trending",
        "market_regime.high_volatility": "market_regime.high_volatility",
    }

    # 完全一致でマッピング
    if key_path in preset_mappings:
        return preset_mappings[key_path]

    # プレフィックスマッチでマッピング（strategies.atr_based.xxx → strategies.atr_based.xxx）
    for threshold_prefix, preset_prefix in preset_mappings.items():
        if key_path.startswith(threshold_prefix + "."):
            suffix = key_path[len(threshold_prefix) + 1 :]
            return f"{preset_prefix}.{suffix}"

    return None


def get_active_preset_name() -> Optional[str]:
    """
    Phase 57.5: 現在アクティブなプリセット名を取得

    Returns:
        プリセット名（未設定の場合はNone）
    """
    # プリセットを読み込んでキャッシュを更新
    load_active_preset()
    return _active_preset_name


def reload_preset() -> None:
    """Phase 57.5: プリセットキャッシュをクリアして再読み込み."""
    global _preset_cache, _active_preset_name
    _preset_cache = None
    _active_preset_name = None
    load_active_preset()


def get_threshold(key_path: str, default_value: Any = None) -> Any:
    """
    階層キーで閾値設定を取得（Phase 57.5: プリセット対応）

    優先順位:
    1. 実行時オーバーライド（Optuna最適化時）
    2. プリセット設定（Phase 57.5: 戦略設定の変数化）
    3. thresholds.yaml設定値
    4. default_value

    Args:
        key_path: ドット記法のキー（例: "ml.default_confidence"）
        default_value: デフォルト値

    Returns:
        設定値またはデフォルト値
    """
    # 優先順位1: 実行時オーバーライドを最優先でチェック
    if key_path in _runtime_overrides:
        return _runtime_overrides[key_path]

    # 優先順位2: Phase 57.5 プリセット設定をチェック
    preset = load_active_preset()
    if preset:
        # thresholds.yamlキー → プリセットキーに変換
        preset_key = _convert_preset_key_to_threshold_key(key_path)
        if preset_key:
            preset_value = _get_nested_value(preset, preset_key)
            if preset_value is not None:
                return preset_value

    # 優先順位3: thresholds.yaml設定値
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
    """閾値設定のキャッシュをクリアして再読み込み（Phase 57.5: プリセットも含む）."""
    global _thresholds_cache, _preset_cache, _active_preset_name
    _thresholds_cache = None
    _preset_cache = None
    _active_preset_name = None
    load_thresholds()
    load_active_preset()


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
    """
    return get_threshold(f"monitoring.{key}", default)


def get_anomaly_config(key: str, default: Any = None) -> Any:
    """
    異常検知設定取得

    Args:
        key: 異常検知設定のキー（例: "spread.warning_threshold"）
        default: デフォルト値
    """
    return get_threshold(f"anomaly_detection.{key}", default)


def get_position_config(key: str, default: Any = None) -> Any:
    """
    ポジション管理設定取得

    Args:
        key: ポジション管理設定のキー（例: "kelly_criterion.max_position_ratio"）
        default: デフォルト値
    """
    return get_threshold(f"position_management.{key}", default)


def get_backtest_config(key: str, default: Any = None) -> Any:
    """
    バックテスト設定取得

    Args:
        key: バックテスト設定のキー（例: "stop_loss.default_rate"）
        default: デフォルト値
    """
    return get_threshold(f"backtest.{key}", default)


def get_data_config(key: str, default: Any = None) -> Any:
    """
    データ取得設定取得

    Args:
        key: データ取得設定のキー（例: "limits.default"）
        default: デフォルト値
    """
    return get_threshold(f"data_fetching.{key}", default)


def get_file_config(key: str, default: Any = None) -> Any:
    """
    ファイルI/O設定取得

    Args:
        key: ファイルI/O設定のキー（例: "logging.retention_days"）
        default: デフォルト値
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
        key_path: ドット記法のキー
        value: 設定する値
    """
    _runtime_overrides[key_path] = value


def set_runtime_overrides_batch(overrides: Dict[str, Any]) -> None:
    """
    実行時パラメータを一括オーバーライド（Optuna最適化用）

    Args:
        overrides: キーと値の辞書
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
