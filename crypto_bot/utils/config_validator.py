# crypto_bot/utils/config_validator.py
"""
設定ファイル（YAML）の検証機能

このモジュールは、config/default.ymlの設定値が有効かどうかを検証し、
起動時やテスト時に不正な設定を早期発見することを目的としています。
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """設定検証エラー"""

    pass


class ConfigValidator:
    """
    設定ファイルの検証を行うクラス

    使用例:
        validator = ConfigValidator()
        validator.validate(config_dict)
    """

    def __init__(self):
        self.errors: List[str] = []

    def validate(self, config: Dict[str, Any]) -> None:
        """
        設定全体を検証する

        Parameters
        ----------
        config : Dict[str, Any]
            YAMLから読み込んだ設定辞書

        Raises
        ------
        ConfigValidationError
            設定に問題がある場合
        """
        self.errors.clear()

        # 各セクションの検証
        self._validate_data_section(config.get("data", {}))
        self._validate_strategy_section(config.get("strategy", {}))
        self._validate_risk_section(config.get("risk", {}))
        self._validate_backtest_section(config.get("backtest", {}))
        self._validate_walk_forward_section(config.get("walk_forward", {}))
        self._validate_ml_section(config.get("ml", {}))

        # エラーがあれば例外を発生
        if self.errors:
            error_msg = "設定検証エラー:\n" + "\n".join(
                f"  - {error}" for error in self.errors
            )
            raise ConfigValidationError(error_msg)

        logger.info("設定検証が正常に完了しました")

    def _validate_data_section(self, data_config: Dict[str, Any]) -> None:
        """データ取得設定の検証"""
        # 必須フィールド
        required_fields = ["exchange", "symbol", "timeframe"]
        for field in required_fields:
            if field not in data_config:
                self.errors.append(f"data.{field} は必須です")

        # exchange validation
        if "exchange" in data_config:
            valid_exchanges = ["bybit", "bitbank", "bitflyer", "okcoinjp", "csv"]
            if data_config["exchange"] not in valid_exchanges:
                self.errors.append(
                    f"data.exchange は {valid_exchanges} のいずれかである必要があります"
                )

        # timeframe validation
        if "timeframe" in data_config:
            valid_timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
            if data_config["timeframe"] not in valid_timeframes:
                self.errors.append(
                    f"data.timeframe は {valid_timeframes} のいずれかである必要があります"
                )

        # limit validation
        if "limit" in data_config:
            limit = data_config["limit"]
            if not isinstance(limit, int) or limit <= 0:
                self.errors.append("data.limit は正の整数である必要があります")

    def _validate_strategy_section(self, strategy_config: Dict[str, Any]) -> None:
        """戦略設定の検証"""
        if "params" in strategy_config:
            params = strategy_config["params"]

            # threshold validation
            if "threshold" in params:
                threshold = params["threshold"]
                if (
                    not isinstance(threshold, (int, float))
                    or not -1.0 <= threshold <= 1.0
                ):
                    self.errors.append(
                        "strategy.params.threshold は -1.0 から 1.0 の間である必要があります"
                    )

            # thresholds_to_test validation
            if "thresholds_to_test" in params:
                thresholds = params["thresholds_to_test"]
                if not isinstance(thresholds, list) or not thresholds:
                    self.errors.append(
                        "strategy.params.thresholds_to_test は空でないリストである必要があります"
                    )
                else:
                    for i, t in enumerate(thresholds):
                        if not isinstance(t, (int, float)) or not -1.0 <= t <= 1.0:
                            self.errors.append(
                                f"strategy.params.thresholds_to_test[{i}] は "
                                f"-1.0 から 1.0 の間である必要があります"
                            )

    def _validate_risk_section(self, risk_config: Dict[str, Any]) -> None:
        """リスク管理設定の検証"""
        # risk_per_trade validation
        if "risk_per_trade" in risk_config:
            risk = risk_config["risk_per_trade"]
            if not isinstance(risk, (int, float)) or not 0 < risk <= 1.0:
                self.errors.append(
                    "risk.risk_per_trade は 0 より大きく 1.0 以下である必要があります"
                )

        # stop_atr_mult validation
        if "stop_atr_mult" in risk_config:
            mult = risk_config["stop_atr_mult"]
            if not isinstance(mult, (int, float)) or mult <= 0:
                self.errors.append("risk.stop_atr_mult は正の数である必要があります")

        # dynamic_position_sizing validation
        if "dynamic_position_sizing" in risk_config:
            dps = risk_config["dynamic_position_sizing"]
            if not isinstance(dps, dict):
                self.errors.append(
                    "risk.dynamic_position_sizing は辞書である必要があります"
                )
            else:
                if "enabled" in dps and not isinstance(dps["enabled"], bool):
                    self.errors.append(
                        "risk.dynamic_position_sizing.enabled はbool値である必要があります"
                    )

    def _validate_backtest_section(self, backtest_config: Dict[str, Any]) -> None:
        """バックテスト設定の検証"""
        # starting_balance validation
        if "starting_balance" in backtest_config:
            balance = backtest_config["starting_balance"]
            if not isinstance(balance, (int, float)) or balance <= 0:
                self.errors.append(
                    "backtest.starting_balance は正の数である必要があります"
                )

        # slippage_rate validation
        if "slippage_rate" in backtest_config:
            slippage = backtest_config["slippage_rate"]
            if not isinstance(slippage, (int, float)) or not 0 <= slippage <= 1.0:
                self.errors.append(
                    "backtest.slippage_rate は 0 から 1.0 の間である必要があります"
                )

    def _validate_walk_forward_section(self, wf_config: Dict[str, Any]) -> None:
        """ウォークフォワード設定の検証"""
        required_fields = ["train_window", "test_window", "step"]
        for field in required_fields:
            if field in wf_config:
                value = wf_config[field]
                if not isinstance(value, int) or value <= 0:
                    self.errors.append(
                        f"walk_forward.{field} は正の整数である必要があります"
                    )

    def _validate_ml_section(self, ml_config: Dict[str, Any]) -> None:
        """機械学習設定の検証"""
        # model_type validation
        if "model_type" in ml_config:
            model_type = ml_config["model_type"]
            valid_types = ["lgbm", "rf", "xgb"]
            if model_type not in valid_types:
                self.errors.append(
                    f"ml.model_type は {valid_types} のいずれかである必要があります"
                )

        # target_type validation
        if "target_type" in ml_config:
            target_type = ml_config["target_type"]
            valid_types = ["classification", "regression"]
            if target_type not in valid_types:
                self.errors.append(
                    f"ml.target_type は {valid_types} のいずれかである必要があります"
                )

        # feat_period validation
        if "feat_period" in ml_config:
            period = ml_config["feat_period"]
            if not isinstance(period, int) or period <= 0:
                self.errors.append("ml.feat_period は正の整数である必要があります")

        # horizon validation
        if "horizon" in ml_config:
            horizon = ml_config["horizon"]
            if not isinstance(horizon, int) or horizon <= 0:
                self.errors.append("ml.horizon は正の整数である必要があります")

        # rolling_window validation
        if "rolling_window" in ml_config:
            window = ml_config["rolling_window"]
            if not isinstance(window, int) or window <= 0:
                self.errors.append("ml.rolling_window は正の整数である必要があります")

        # lags validation
        if "lags" in ml_config:
            lags = ml_config["lags"]
            if not isinstance(lags, list):
                self.errors.append("ml.lags はリストである必要があります")
            else:
                for i, lag in enumerate(lags):
                    if not isinstance(lag, int) or lag <= 0:
                        self.errors.append(
                            f"ml.lags[{i}] は正の整数である必要があります"
                        )

        # extra_features validation
        if "extra_features" in ml_config:
            features = ml_config["extra_features"]
            if not isinstance(features, list):
                self.errors.append("ml.extra_features はリストである必要があります")
            else:
                # 65特徴量システム対応 - 実装済み全特徴量リスト
                valid_features = [
                    # 基本テクニカル指標
                    "rsi_14",
                    "rsi_21",
                    "rsi_9",  # RSI系
                    "macd",  # MACD
                    "rci_9",
                    "rci_14",  # RCI系
                    "volume_zscore",
                    "volume_zscore_20",
                    "volume_zscore_14",  # 出来高系
                    # 移動平均系
                    "sma_200",
                    "sma_50",
                    "sma_20",
                    "sma_10",
                    "sma_5",
                    "ema_50",
                    "ema_20",
                    "ema_12",
                    "ema_26",
                    # 高度テクニカル指標
                    "stoch",  # ストキャスティクス
                    "bb",
                    "bollinger",  # ボリンジャーバンド
                    "adx",  # ADX
                    "willr",
                    "williams",  # Williams %R
                    "cmf",  # チャイキンマネーフロー
                    "fisher",  # フィッシャートランスフォーム
                    # マクロ経済統合特徴量（実装済み）
                    "vix",  # VIX恐怖指数統合（6特徴量）
                    "dxy",
                    "macro",
                    "treasury",  # DXY・金利統合（10特徴量）
                    "fear_greed",
                    "fg",  # Fear & Greed指数統合
                    "funding",
                    "oi",  # Funding Rate・OI統合（17特徴量）
                    # 時間特徴量
                    "day_of_week",
                    "hour_of_day",
                    # 独自シグナル
                    "mochipoyo_long_signal",
                    "mochipoyo_short_signal",
                    # 追加可能な拡張特徴量（将来実装用）
                    "momentum_14",
                    "momentum_21",  # モメンタム系
                    "trend_strength",  # トレンド強度
                    "market_regime",  # 市場環境判定
                    "volatility_regime",  # ボラティリティレジーム
                    "correlation_spy",  # SPY相関
                    "correlation_gold",  # 金相関
                ]
                for feature in features:
                    if not isinstance(feature, str):
                        self.errors.append(
                            f"ml.extra_features の要素は文字列である必要があります: {feature}"
                        )
                    # 警告レベル - 無効な特徴量があっても動作は可能（エラー耐性強化）
                    elif feature not in valid_features:
                        logger.info(f"ℹ️ 未実装特徴量（デフォルト値使用）: {feature}")

        # optuna section validation
        if "optuna" in ml_config:
            optuna = ml_config["optuna"]
            if "n_trials" in optuna:
                n_trials = optuna["n_trials"]
                if not isinstance(n_trials, int) or n_trials <= 0:
                    self.errors.append(
                        "ml.optuna.n_trials は正の整数である必要があります"
                    )

            if "timeout" in optuna:
                timeout = optuna["timeout"]
                if not isinstance(timeout, (int, float)) or timeout <= 0:
                    self.errors.append("ml.optuna.timeout は正の数である必要があります")


def validate_config_file(config_path: str) -> None:
    """
    設定ファイルを読み込んで検証する便利関数

    Parameters
    ----------
    config_path : str
        設定ファイルのパス

    Raises
    ------
    ConfigValidationError
        設定に問題がある場合
    FileNotFoundError
        ファイルが見つからない場合
    """
    import yaml

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    validator = ConfigValidator()
    validator.validate(config)
