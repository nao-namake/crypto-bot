"""
TP/SL設定パス定数 + 取得ヘルパー - Phase 64.1

設定パス文字列リテラルの一元管理により、typoバグを根絶する。
Phase 63.6でCRITICALバグ3件が設定パスtypoに起因したことへの対策。

使用法:
    from src.trading.execution.tp_sl_config import TPSLConfig
    from src.core.config import get_threshold

    tp_ratio = get_threshold(TPSLConfig.TP_MIN_PROFIT_RATIO, 0.009)
    regime_tp = get_threshold(TPSLConfig.tp_regime_path("tight_range", "min_profit_ratio"), 0.004)
"""


class TPSLConfig:
    """TP/SL設定パス定数 + 取得ヘルパー"""

    # === TP設定パス ===
    TP_ENABLED = "position_management.take_profit.enabled"
    TP_MIN_PROFIT_RATIO = "position_management.take_profit.min_profit_ratio"
    TP_USE_NATIVE_TYPE = "position_management.take_profit.use_native_type"
    TP_FIXED_AMOUNT_ENABLED = "position_management.take_profit.fixed_amount.enabled"
    TP_FIXED_AMOUNT_TARGET = "position_management.take_profit.fixed_amount.target_net_profit"
    TP_FIXED_AMOUNT_INCLUDE_ENTRY_FEE = (
        "position_management.take_profit.fixed_amount.include_entry_fee"
    )
    TP_FIXED_AMOUNT_INCLUDE_EXIT_FEE = (
        "position_management.take_profit.fixed_amount.include_exit_fee_rebate"
    )
    TP_FIXED_AMOUNT_INCLUDE_INTEREST = (
        "position_management.take_profit.fixed_amount.include_interest"
    )
    TP_FIXED_AMOUNT_FALLBACK_ENTRY_RATE = (
        "position_management.take_profit.fixed_amount.fallback_entry_fee_rate"
    )
    TP_FIXED_AMOUNT_FALLBACK_EXIT_RATE = (
        "position_management.take_profit.fixed_amount.fallback_exit_fee_rate"
    )
    TP_MAKER_ENABLED = "position_management.take_profit.maker_strategy.enabled"
    TP_MAKER_MAX_RETRIES = "position_management.take_profit.maker_strategy.max_retries"
    TP_MAKER_RETRY_INTERVAL_MS = "position_management.take_profit.maker_strategy.retry_interval_ms"
    TP_MAKER_TIMEOUT_SECONDS = "position_management.take_profit.maker_strategy.timeout_seconds"
    TP_MAKER_FALLBACK_TO_NATIVE = (
        "position_management.take_profit.maker_strategy.fallback_to_native"
    )

    # === SL設定パス ===
    SL_ENABLED = "position_management.stop_loss.enabled"
    SL_MAX_LOSS_RATIO = "position_management.stop_loss.max_loss_ratio"
    SL_ORDER_TYPE = "position_management.stop_loss.order_type"
    SL_SLIPPAGE_BUFFER = "position_management.stop_loss.slippage_buffer"
    SL_STOP_LIMIT_TIMEOUT = "position_management.stop_loss.stop_limit_timeout"
    SL_SKIP_BOT_MONITORING = "position_management.stop_loss.skip_bot_monitoring"
    SL_DEFAULT_ATR_MULTIPLIER = "position_management.stop_loss.default_atr_multiplier"
    SL_USE_NATIVE_TYPE = "position_management.stop_loss.use_native_type"
    SL_FILL_TIMEOUT = "position_management.stop_loss.fill_confirmation.timeout_seconds"
    SL_FILL_INTERVAL = "position_management.stop_loss.fill_confirmation.check_interval_seconds"
    SL_FILL_CONFIRMATION = "position_management.stop_loss.fill_confirmation"
    SL_RETRY_MAX = "position_management.stop_loss.retry_on_unfilled.max_retries"
    SL_RETRY_UNFILLED = "position_management.stop_loss.retry_on_unfilled"
    SL_RETRY_SLIPPAGE_INCREASE = (
        "position_management.stop_loss.retry_on_unfilled.slippage_increase_per_retry"
    )
    SL_MIN_DISTANCE_RATIO = "position_management.stop_loss.min_distance.ratio"

    # === TP/SLトップレベル設定パス ===
    TP_CONFIG = "position_management.take_profit"
    SL_CONFIG = "position_management.stop_loss"

    # === レジーム別パスヘルパー ===
    @staticmethod
    def tp_regime_path(regime: str, key: str) -> str:
        """レジーム別TP設定パスを生成"""
        return f"position_management.take_profit.regime_based.{regime}.{key}"

    @staticmethod
    def sl_regime_path(regime: str, key: str) -> str:
        """レジーム別SL設定パスを生成"""
        return f"position_management.stop_loss.regime_based.{regime}.{key}"

    @staticmethod
    def tp_regime_config(regime: str) -> str:
        """レジーム別TP設定ブロックパスを生成"""
        return f"position_management.take_profit.regime_based.{regime}"

    @staticmethod
    def sl_regime_config(regime: str) -> str:
        """レジーム別SL設定ブロックパスを生成"""
        return f"position_management.stop_loss.regime_based.{regime}"

    # === 検証・監視パス ===
    VERIFICATION_ENABLED = "tp_sl_verification.enabled"
    VERIFICATION_DELAY = "tp_sl_verification.delay_seconds"
    VERIFICATION_REBUILD = "tp_sl_verification.rebuild_on_missing"
    VERIFICATION_DEFAULT_REGIME = "tp_sl_verification.default_regime"
    CHECK_INTERVAL = "tp_sl_check.interval_seconds"
    ORPHAN_SCAN_INTERVAL = "orphan_scan.interval_seconds"
    AUTO_DETECTION = "tp_sl_auto_detection"

    # === 共通パス ===
    CURRENCY_PAIR = "trading_constraints.currency_pair"
    FALLBACK_BTC_JPY = "trading.fallback_btc_jpy"
    FALLBACK_ATR = "risk.fallback_atr"
    ENTRY_TAKER_RATE = "trading.fees.entry_taker_rate"
    EXIT_TAKER_RATE = "trading.fees.exit_taker_rate"
    EMERGENCY_SL = "position_management.emergency_stop_loss"
    MAKER_STRATEGY = "order_execution.maker_strategy"
    MIN_TRADE_SIZE = "position_management.min_trade_size"
    REQUIRE_TPSL_RECALCULATION = "risk.require_tpsl_recalculation"

    # === ハードコード撲滅: 定数化 ===
    API_ORDER_LIMIT = 100  # bitbank APIアクティブ注文取得上限
    DEFAULT_TP_RATIO = 0.004  # デフォルトTP比率（tight_range）
    DEFAULT_SL_RATIO = 0.004  # デフォルトSL比率（tight_range）
    SL_SAFETY_MARGIN_BUY = 1.015  # SLタイムアウト時の安全マージン（買い）
    SL_SAFETY_MARGIN_SELL = 0.985  # SLタイムアウト時の安全マージン（売り）
    SL_MIN_DISTANCE_WARNING = 0.001  # SL距離警告閾値（0.1%）
    DEFAULT_FALLBACK_BTC_JPY = 16500000.0  # フォールバックBTC/JPY価格
    CLEANUP_THRESHOLD_COUNT = 25  # クリーンアップ発動閾値（30件制限の83%）
    CLEANUP_MAX_AGE_HOURS = 24  # クリーンアップ対象注文経過時間
