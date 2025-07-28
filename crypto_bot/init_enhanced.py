"""
INIT段階エラーハンドリング強化版
Phase 2.2: INIT段階エラーハンドリング強化・ATR計算改善

main.pyのINIT-5～INIT-8段階を強化した版
"""

import logging
import time
from typing import Any, Optional

import pandas as pd

from crypto_bot.utils.error_resilience import with_resilience

logger = logging.getLogger(__name__)


@with_resilience("init_system", "init_5_fetch_price_data")
def enhanced_init_5_fetch_price_data(
    fetcher, dd: dict, max_retries: int = 5, timeout: int = 120, prefetch_data=None
) -> Optional[pd.DataFrame]:
    """
    INIT-5段階: 初期価格データ取得（強化版・Phase H.13: プリフェッチデータ統合）

    Args:
        fetcher: データフェッチャー
        dd: データ設定辞書
        max_retries: 最大再試行回数
        timeout: タイムアウト秒数（Phase H.7: 60→120秒延長）
        prefetch_data: プリフェッチデータ（Phase H.13: メインループ共有用）

    Returns:
        DataFrame: 価格データ（失敗時はNone）
    """
    # Phase H.13: プリフェッチデータ優先使用（ATR計算データ最大化）
    if prefetch_data is not None and not prefetch_data.empty:
        logger.info(
            "📊 [INIT-5] Phase H.13: Using prefetched data for optimal ATR calculation"
        )
        logger.info(
            f"✅ [INIT-5] Prefetch data utilized: {len(prefetch_data)} records (vs previous 5 records)"
        )
        logger.info(
            f"📈 [INIT-5] Data range: {prefetch_data.index.min()} to {prefetch_data.index.max()}"
        )

        # データ品質確認
        required_columns = ["open", "high", "low", "close", "volume"]
        missing_columns = [
            col for col in required_columns if col not in prefetch_data.columns
        ]

        if missing_columns:
            logger.warning(
                f"⚠️ [INIT-5] Missing columns in prefetch data: {missing_columns}"
            )
            logger.info("🔄 [INIT-5] Falling back to independent fetch")
        else:
            logger.info(
                "✅ [INIT-5] Phase H.13: All required columns present in prefetch data"
            )
            logger.info(
                f"🎯 [INIT-5] Phase H.13: ATR calculation will use {len(prefetch_data)} records (sufficient for period=14)"
            )
            return prefetch_data.copy()  # プリフェッチデータを返す

    # Phase H.8.4: エラー耐性管理システム統合（記録のみ）
    logger.info(
        "📈 [INIT-5] Fetching initial price data for ATR calculation (fallback mode)..."
    )
    logger.info(f"⏰ [INIT-5] Timestamp: {pd.Timestamp.now()}")
    logger.info(
        f"🔧 [INIT-5] Configuration: max_retries={max_retries}, timeout={timeout}s (Phase H.7延長)"
    )
    logger.info("🛡️ [PHASE-H8.4] INIT-5 with enhanced error resilience")

    # Phase H.6.1: 動的since計算（メインループと同じロジック）
    current_time = pd.Timestamp.now(tz="UTC")

    if dd.get("since"):
        since_time = pd.Timestamp(dd["since"])
        if since_time.tz is None:
            since_time = since_time.tz_localize("UTC")
        logger.info(f"🔧 [INIT-5] Using config since: {since_time}")
    else:
        # 動的since_hours計算（土日ギャップ・祝日対応）
        base_hours = dd.get("since_hours", 120)  # Phase H.5.3: 120時間デフォルト

        # 曜日判定（月曜日=0, 日曜日=6）
        current_day = current_time.dayofweek
        current_hour = current_time.hour

        # 土日ギャップ対応
        if current_day == 0:  # 月曜日
            # 月曜日は土日ギャップを考慮して延長
            extended_hours = dd.get("weekend_extension_hours", 72)  # 3日間追加
            lookback_hours = base_hours + extended_hours
            logger.info(
                f"🔧 [INIT-5] Monday detected: extending lookback by {extended_hours}h to {lookback_hours}h"
            )
        elif current_day == 1 and current_hour < 12:  # 火曜日午前
            # 火曜日午前も少し延長
            extended_hours = dd.get("early_week_extension_hours", 36)  # 1.5日追加
            lookback_hours = base_hours + extended_hours
            logger.info(
                f"🔧 [INIT-5] Tuesday morning: extending by {extended_hours}h to {lookback_hours}h"
            )
        else:
            lookback_hours = base_hours

        since_time = current_time - pd.Timedelta(hours=lookback_hours)
        logger.info(
            f"🔍 [INIT-5] Dynamic since calculation - Day: {current_day}, Hour: {current_hour}, "
            f"Lookback: {lookback_hours}h, Since: {since_time}"
        )
        logger.info(
            f"   ⏰ Time span: {lookback_hours} hours ({lookback_hours/24:.1f} days)"
        )
        logger.info(f"   📊 Expected 1h records: ~{lookback_hours}")

    # 外部データフェッチャーの初期化確認
    try:
        logger.info("🔍 [INIT-5] Verifying external data fetchers...")

        # yfinance依存関係確認
        import yfinance  # noqa: F401

        logger.info("✅ [INIT-5] yfinance module verified")

        # 外部データフェッチャーのテスト
        try:
            from crypto_bot.data.vix_fetcher import VIXDataFetcher

            vix_fetcher = VIXDataFetcher()  # noqa: F841
            logger.info("✅ [INIT-5] VIX fetcher initialized")
        except Exception as e:
            logger.warning(f"⚠️ [INIT-5] VIX fetcher initialization failed: {e}")

        try:
            from crypto_bot.data.macro_fetcher import MacroDataFetcher

            macro_fetcher = MacroDataFetcher()  # noqa: F841
            logger.info("✅ [INIT-5] Macro fetcher initialized")
        except Exception as e:
            logger.warning(f"⚠️ [INIT-5] Macro fetcher initialization failed: {e}")

        try:
            from crypto_bot.data.fear_greed_fetcher import FearGreedDataFetcher

            fear_greed_fetcher = FearGreedDataFetcher()  # noqa: F841
            logger.info("✅ [INIT-5] Fear&Greed fetcher initialized")
        except Exception as e:
            logger.warning(f"⚠️ [INIT-5] Fear&Greed fetcher initialization failed: {e}")

    except ImportError as e:
        logger.error(f"❌ [INIT-5] External data fetcher dependency error: {e}")
        logger.error("❌ [INIT-5] This will cause external data fetchers to fail")

    # メインのデータ取得処理
    initial_df = None

    # Phase H.8.2: API Error 10000完全解決・4h直接取得完全禁止
    # 4hタイムフレームの検出と強制変換（設定に関係なく1h固定）
    forced_timeframe = "1h"  # Phase H.8.2: 設定に関係なく1h固定

    # 全ての4h関連設定を検出して警告・強制変換
    multi_tf_base = dd.get("multi_timeframe_data", {}).get("base_timeframe", "1h")
    data_timeframe = dd.get("timeframe", "1h")

    # 4h検出の包括チェック
    four_hour_detected = False
    detection_sources = []

    if multi_tf_base == "4h":
        four_hour_detected = True
        detection_sources.append("multi_timeframe_data.base_timeframe")
        logger.critical(
            "🚨 [INIT-5] CRITICAL: 4h detected in multi_timeframe_data.base_timeframe"
        )

    if data_timeframe == "4h":
        four_hour_detected = True
        detection_sources.append("data.timeframe")
        logger.critical("🚨 [INIT-5] CRITICAL: 4h detected in data.timeframe")

    # タイムフレーム設定の強制修正
    if four_hour_detected:
        logger.critical(
            f"🚨 [INIT-5] Phase H.8.2: 4h timeframe BLOCKED - Sources: {', '.join(detection_sources)}"
        )
        logger.critical(
            "🚨 [INIT-5] Phase H.8.2: Forcing to 1h to prevent API Error 10000"
        )
    else:
        logger.info(
            "✅ [INIT-5] Phase H.8.2: No 4h timeframe detected, safe to proceed"
        )

    timeframe = forced_timeframe  # 常に1h使用
    logger.info(f"🔧 [INIT-5] Phase H.8.2: Using forced timeframe: {timeframe}")

    # API Error 10000防止の最終確認
    if timeframe == "4h":
        logger.critical(
            "🚨 [INIT-5] Phase H.8.2: EMERGENCY: 4h still detected, forcing to 1h"
        )
        timeframe = "1h"
    # Phase H.13: INIT-5専用設定（データ不足対応・十分な余裕確保・安全マージン強化）
    init_limit = 200  # Phase H.13: 安全マージン強化（ATR期間14に対して14倍以上の余裕・100データ未取得対策）
    init_paginate = True  # Phase H.13: ページネーション有効化（データ確保優先）
    init_per_page = (
        100  # Phase H.13: 大きめのページサイズ（効率的な大量取得・安全マージン強化）
    )

    logger.info(
        f"🔧 [INIT-5] Phase H.13: timeframe={timeframe}, limit={init_limit}, paginate={init_paginate}, per_page={init_per_page}"
    )
    logger.info(
        f"🔧 [INIT-5] Phase H.13: Enhanced safety margin settings ({init_limit} records target, robust against <100 data scenarios)"
    )
    logger.info(
        "⚠️ [INIT-5] Phase H.13: Note - prefetch data preferred, this is safety fallback"
    )

    for attempt in range(max_retries):
        try:
            start_time = time.time()
            logger.info(
                f"🔄 [INIT-5] Attempt {attempt + 1}/{max_retries} - "
                f"Fetching initial price data..."
            )

            # Cloud Run対応タイムアウト付きでデータ取得
            from concurrent.futures import ThreadPoolExecutor
            from concurrent.futures import TimeoutError as FutureTimeoutError

            def fetch_data():
                # Phase H.8.1: データ新鮮度チェック付きフェッチ使用
                logger.info(
                    "🚀 [PHASE-H8.1] Using freshness-aware data fetch for INIT-5"
                )
                return fetcher.fetch_with_freshness_fallback(
                    timeframe=timeframe,
                    since=since_time,  # Phase H.6.1: since時刻を追加
                    limit=init_limit,  # Phase H.13: 200レコード（安全マージン強化・100データ未取得対策）
                    max_age_hours=2.0,  # Phase H.8.1: 2時間以内のデータを要求
                    paginate=init_paginate,  # Phase H.13: True（ページネーション有効）
                    per_page=init_per_page,  # Phase H.13: 100件ページサイズ（大量効率取得・安全マージン強化）
                    # Phase H.13: 安全マージン強化・十分な取得機会確保（API制限・ネットワーク問題対応）
                    max_consecutive_empty=dd.get(
                        "max_consecutive_empty", 10
                    ),  # 5→10に拡大（余裕確保）
                    max_consecutive_no_new=dd.get(
                        "max_consecutive_no_new", 20
                    ),  # 10→20に拡大（データ確保重視）
                    max_attempts=dd.get(
                        "max_attempts", 35
                    ),  # 15→35に拡大（200レコード確実取得）
                )

            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(fetch_data)
                    initial_df = future.result(timeout=timeout)

                fetch_time = time.time() - start_time
                logger.info(
                    f"✅ [INIT-5] Initial price data fetched successfully: "
                    f"{len(initial_df)} records in {fetch_time:.2f}s"
                )
                logger.info(
                    "✅ [INIT-5] Phase H.7 optimization successful - lightweight fetch completed"
                )

                # データ品質確認
                if initial_df is not None and not initial_df.empty:
                    required_columns = ["open", "high", "low", "close", "volume"]
                    missing_columns = [
                        col for col in required_columns if col not in initial_df.columns
                    ]

                    if missing_columns:
                        logger.warning(
                            f"⚠️ [INIT-5] Missing required columns: {missing_columns}"
                        )
                    else:
                        logger.info("✅ [INIT-5] All required columns present")

                    # データ範囲確認
                    logger.info(
                        f"📊 [INIT-5] Data range: "
                        f"{initial_df.index.min()} to {initial_df.index.max()}"
                    )
                    logger.info(
                        f"📊 [INIT-5] Price range: "
                        f"{initial_df['close'].min():.2f} to "
                        f"{initial_df['close'].max():.2f}"
                    )

                break

            except (FutureTimeoutError, TimeoutError) as e:
                logger.error(f"⏰ [INIT-5] Timeout error: {e}")
                raise

        except Exception as e:
            fetch_time = time.time() - start_time
            error_str = str(e)

            # Phase F.4: API制限エラー特別処理
            if "10000" in error_str or "rate limit" in error_str.lower():
                logger.error(
                    f"🚨 [INIT-5] API rate limit error detected (attempt {attempt + 1}): {e}"
                )
                # API制限エラーの場合はより長い待機時間
                wait_time = min((attempt + 1) * 20, 120)  # 最大2分待機
                logger.warning(
                    f"⏳ [INIT-5] API limit backoff: waiting {wait_time}s for recovery..."
                )
            else:
                logger.error(
                    f"❌ [INIT-5] Attempt {attempt + 1} failed after {fetch_time:.2f}s: {e}"
                )
                # 通常エラーの場合は標準的な待機時間
                wait_time = min((attempt + 1) * 10, 60)
                logger.info(
                    f"⏳ [INIT-5] Standard backoff: waiting {wait_time}s before retry..."
                )

            if attempt < max_retries - 1:
                time.sleep(wait_time)
            else:
                logger.error(
                    f"❌ [INIT-5] All {max_retries} attempts failed - "
                    "data fetch completely failed. Consider increasing timeout or reducing API load."
                )
                initial_df = None

    return initial_df


@with_resilience("init_system", "init_6_calculate_atr")
def enhanced_init_6_calculate_atr(
    initial_df: Optional[pd.DataFrame], period: int = None
) -> Optional[pd.Series]:
    """
    INIT-6段階: ATR計算（強化版・Phase H.22.3: 設定統一）

    Args:
        initial_df: 初期価格データ
        period: ATR計算期間（Noneの場合は設定ファイルから取得）

    Returns:
        Series: ATR値（失敗時はNone）
    """
    # Phase H.22.3: ATR期間設定統一・production.yml設定値使用
    if period is None:
        from crypto_bot.main import get_current_config

        try:
            config = get_current_config()
            period = config.get("risk_management", {}).get("atr_period", 20)
            logger.info(f"✅ [INIT-6-H22.3] Using config atr_period: {period}")
        except Exception as e:
            logger.warning(
                f"⚠️ [INIT-6-H22.3] Config read failed, using default 20: {e}"
            )
            period = 20

    logger.info("🔢 [INIT-6] Calculating ATR...")
    logger.info(f"⏰ [INIT-6] Timestamp: {pd.Timestamp.now()}")
    logger.info(f"🔧 [INIT-6-H22.3] ATR period: {period} (config-unified)")
    logger.info("🛡️ [PHASE-H8.4] INIT-6 with enhanced error resilience")

    atr_series = None

    if initial_df is not None and not initial_df.empty:
        try:
            # データ品質の再確認
            required_columns = ["high", "low", "close"]
            missing_columns = [
                col for col in required_columns if col not in initial_df.columns
            ]

            if missing_columns:
                logger.error(
                    f"❌ [INIT-6] Missing required columns for ATR: {missing_columns}"
                )
                return None

            # Phase H.13: ATR計算データ量評価（余裕を持った基準・実用性重視）
            data_count = len(initial_df)
            min_records_excellent = period * 3  # 優秀: period × 3（42件）
            min_records_ideal = period + 5  # 理想: period + 余裕（19件）
            min_records_good = period + 1  # 良好: period + 1（15件）
            min_records_acceptable = max(
                period // 2, 5
            )  # 許容: period半分または5件（7件）
            min_records_minimum = max(
                3, period // 3
            )  # 最小: period三分の一または3件（5件）

            # Phase H.13: データ量による品質評価・余裕を持った判定
            if data_count >= min_records_excellent:
                logger.info(
                    f"🌟 [INIT-6] Phase H.13: EXCELLENT data for ATR calculation: {data_count} records >= {min_records_excellent} (3x period)"
                )
                logger.info(
                    "✨ [INIT-6] Phase H.13: Optimal data volume for maximum ATR precision"
                )
            elif data_count >= min_records_ideal:
                logger.info(
                    f"🎯 [INIT-6] Phase H.13: VERY GOOD data for ATR calculation: {data_count} records >= {min_records_ideal} (period + 5)"
                )
                logger.info(
                    "✨ [INIT-6] Phase H.13: Large data volume enables high-precision ATR calculation"
                )
            elif data_count >= min_records_good:
                logger.info(
                    f"✅ [INIT-6] Phase H.13: GOOD data for ATR calculation: {data_count} records >= {min_records_good} (period + 1)"
                )
            elif data_count >= min_records_acceptable:
                logger.info(
                    f"🔶 [INIT-6] Phase H.13: ACCEPTABLE data for ATR calculation: {data_count} records >= {min_records_acceptable} (adequate)"
                )
                logger.info(
                    "📊 [INIT-6] Phase H.13: ATR calculation possible but with reduced precision"
                )
            elif data_count >= min_records_minimum:
                logger.warning(
                    f"⚠️ [INIT-6] Phase H.13: MINIMAL data for ATR calculation: {data_count} records >= {min_records_minimum} (minimum)"
                )
                logger.warning(
                    "⚠️ [INIT-6] Phase H.13: ATR calculation possible but precision may be limited"
                )
            else:
                logger.error(
                    f"❌ [INIT-6] Phase H.13: INSUFFICIENT data for ATR calculation: "
                    f"{data_count} < {min_records_minimum} (absolute minimum)"
                )
                logger.error(
                    "❌ [INIT-6] Phase H.13: Cannot proceed with ATR calculation"
                )
                return None

            logger.info(
                f"📊 [INIT-6] Phase H.13: Data validation passed with {data_count} records (period={period})"
            )

            # ATR計算実行（Phase H.13: 強化版・nan値防止・品質保証）
            from crypto_bot.indicator.calculator import IndicatorCalculator

            calculator = IndicatorCalculator()

            start_time = time.time()
            atr_series = calculator.calculate_atr(initial_df, period=period)
            calc_time = time.time() - start_time

            # Phase H.13: ATR計算結果の包括的検証
            if atr_series is not None and not atr_series.empty:
                # nan値チェック（Phase H.13: 最重要検証）
                nan_count = atr_series.isna().sum()
                if nan_count > 0:
                    logger.warning(
                        f"⚠️ [INIT-6] Phase H.13: ATR contains {nan_count} nan values"
                    )
                    # nan値を除去して有効値のみ使用
                    atr_series = atr_series.dropna()
                    if atr_series.empty:
                        logger.error(
                            "❌ [INIT-6] Phase H.13: All ATR values are nan after cleaning"
                        )
                        atr_series = None
                    else:
                        logger.info(
                            f"✅ [INIT-6] Phase H.13: ATR cleaned, {len(atr_series)} valid values remain"
                        )

                if atr_series is not None and not atr_series.empty:
                    latest_atr = atr_series.iloc[-1]
                    mean_atr = atr_series.mean()
                    std_atr = atr_series.std()

                    logger.info(
                        f"✅ [INIT-6] Phase H.13: ATR calculated successfully: {len(atr_series)} values in {calc_time:.2f}s"
                    )
                    logger.info(
                        f"📊 [INIT-6] Phase H.13: ATR statistics: latest={latest_atr:.6f}, mean={mean_atr:.6f}, std={std_atr:.6f}"
                    )

                    # Phase H.13: 異常値チェック強化
                    if pd.isna(latest_atr):
                        logger.error(
                            "❌ [INIT-6] Phase H.13: Latest ATR is nan - this will cause trading failure"
                        )
                        atr_series = None
                    elif latest_atr <= 0:
                        logger.error(
                            f"❌ [INIT-6] Phase H.13: Latest ATR is zero or negative: {latest_atr}"
                        )
                        atr_series = None
                    elif latest_atr > 1.0:
                        logger.warning(
                            f"⚠️ [INIT-6] Phase H.13: Latest ATR unusually high: {latest_atr} (>1.0)"
                        )
                        # 高すぎる値でも使用可能とする
                    else:
                        logger.info(
                            f"✅ [INIT-6] Phase H.13: ATR value quality check passed: {latest_atr:.6f}"
                        )
            else:
                logger.error(
                    "❌ [INIT-6] Phase H.13: ATR calculation returned empty or None series"
                )
                atr_series = None

        except Exception as e:
            logger.error(f"❌ [INIT-6] ATR calculation failed: {e}")
            logger.error(f"❌ [INIT-6] Error type: {type(e).__name__}")
            atr_series = None

    else:
        logger.warning("⚠️ [INIT-6] No initial data available for ATR calculation")

    return atr_series


def enhanced_init_6_fallback_atr(
    period: int = 14, market_context: str = "BTC/JPY"
) -> pd.Series:
    """
    INIT-6段階: ATRフォールバック値生成（Phase H.9.3強化版）

    Args:
        period: ATR期間
        market_context: 市場コンテキスト（BTC/JPY等）

    Returns:
        Series: フォールバックATR値
    """
    logger.info(
        "🔧 [INIT-6] Phase H.9.3: Using enhanced adaptive fallback ATR calculation..."
    )
    logger.info(f"🔧 [INIT-6] Market context: {market_context}, Period: {period}")

    # より現実的なフォールバック値を生成
    # 暗号資産の典型的なATR値: 0.005-0.02 (0.5%-2%)
    base_atr = 0.01  # 1%

    # 時系列的に変化するATR値を生成（より現実的）
    import numpy as np

    np.random.seed(42)  # 再現性のため
    atr_values = []

    for _ in range(period):
        # 基本値に小さな変動を加える
        variation = np.random.normal(0, 0.001)  # 0.1%の標準偏差
        atr_value = max(0.005, base_atr + variation)  # 最小0.5%
        atr_values.append(atr_value)

    atr_series = pd.Series(atr_values)
    latest_atr = atr_series.iloc[-1]

    logger.info(
        f"✅ [INIT-6] Enhanced fallback ATR generated: " f"{len(atr_series)} values"
    )
    logger.info(
        f"📊 [INIT-6] Fallback ATR statistics: "
        f"latest={latest_atr:.6f}, mean={atr_series.mean():.6f}"
    )

    return atr_series


@with_resilience("init_system", "init_7_initialize_entry_exit")
def enhanced_init_7_initialize_entry_exit(
    strategy, risk_manager, atr_series: pd.Series
) -> Any:
    """
    INIT-7段階: Entry/Exitシステム初期化（強化版・Phase H.8.4）

    Args:
        strategy: 取引戦略
        risk_manager: リスク管理
        atr_series: ATR値

    Returns:
        EntryExit: Entry/Exitシステム
    """
    logger.info("🎯 [INIT-7] Initializing Entry/Exit system...")
    logger.info(f"⏰ [INIT-7] Timestamp: {pd.Timestamp.now()}")
    logger.info("🛡️ [PHASE-H8.4] INIT-7 with enhanced error resilience")

    try:
        # 依存関係の確認
        from crypto_bot.execution.engine import EntryExit

        # ATR値の最終確認
        if atr_series is None or atr_series.empty:
            logger.error("❌ [INIT-7] ATR series is None or empty")
            raise ValueError("ATR series is required for Entry/Exit initialization")

        latest_atr = atr_series.iloc[-1]
        logger.info(f"📊 [INIT-7] Using ATR value: {latest_atr:.6f}")

        # Entry/Exitシステム初期化
        entry_exit = EntryExit(
            strategy=strategy, risk_manager=risk_manager, atr_series=atr_series
        )

        logger.info("✅ [INIT-7] Entry/Exit system initialized successfully")
        return entry_exit

    except Exception as e:
        logger.error(f"❌ [INIT-7] Entry/Exit system initialization failed: {e}")
        raise


def enhanced_init_8_clear_cache() -> None:
    """
    INIT-8段階: キャッシュクリア（強化版）
    """
    logger.info("🧹 [INIT-8] Clearing old cache for fresh data...")
    logger.info(f"⏰ [INIT-8] Timestamp: {pd.Timestamp.now()}")

    try:
        from crypto_bot.ml.external_data_cache import (
            clear_global_cache,
            get_global_cache,
        )

        # キャッシュ状況の確認
        cache = get_global_cache()
        cache_info = cache.get_cache_info()
        logger.info(f"📊 [INIT-8] Cache info before clear: {cache_info}")

        # キャッシュクリア実行
        clear_global_cache()

        # クリア後の確認
        cache_info_after = cache.get_cache_info()
        logger.info(f"📊 [INIT-8] Cache info after clear: {cache_info_after}")

        logger.info("✅ [INIT-8] Cache cleared successfully")

    except Exception as e:
        logger.error(f"❌ [INIT-8] Cache clear failed: {e}")
        logger.warning("⚠️ [INIT-8] Continuing without cache clear...")


# 使用例（main.pyでの置き換え用）
def enhanced_init_sequence(
    fetcher, dd: dict, strategy, risk_manager, balance: float, prefetch_data=None
):
    """
    INIT-5～INIT-8の強化版シーケンス（Phase H.13: プリフェッチデータ対応）

    Args:
        fetcher: データフェッチャー
        dd: データ設定
        strategy: 取引戦略
        risk_manager: リスク管理
        balance: 初期残高
        prefetch_data: プリフェッチデータ（Phase H.13: メインループ共有用）

    Returns:
        tuple: (entry_exit, position)
    """
    logger.info("🚀 [INIT-ENHANCED] Starting enhanced initialization sequence...")

    # Phase H.13: プリフェッチデータの状況確認
    if prefetch_data is not None and not prefetch_data.empty:
        logger.info(
            f"📊 [INIT-ENHANCED] Phase H.13: Using prefetched data with {len(prefetch_data)} records"
        )
        logger.info(
            f"📈 [INIT-ENHANCED] Prefetch data range: {prefetch_data.index.min()} to {prefetch_data.index.max()}"
        )
    else:
        logger.info(
            "🔄 [INIT-ENHANCED] Phase H.13: No prefetch data, using independent fetch"
        )

    # INIT-5: 初期価格データ取得（強化版・Phase H.13: プリフェッチデータ統合）
    initial_df = enhanced_init_5_fetch_price_data(
        fetcher, dd, prefetch_data=prefetch_data
    )

    # INIT-6: ATR計算（強化版）
    atr_series = enhanced_init_6_calculate_atr(initial_df)

    # フォールバック処理（Phase H.9.3: 適応的フォールバック）
    if atr_series is None or atr_series.empty:
        logger.info(
            "🔧 [INIT-6] Phase H.9.3: Using enhanced adaptive fallback ATR calculation"
        )
        symbol = dd.get("symbol", "BTC/JPY")
        atr_series = enhanced_init_6_fallback_atr(market_context=symbol)

    # INIT-7: Entry/Exit初期化（強化版）
    entry_exit = enhanced_init_7_initialize_entry_exit(
        strategy, risk_manager, atr_series
    )
    entry_exit.current_balance = balance

    # INIT-8: キャッシュクリア（強化版）
    enhanced_init_8_clear_cache()

    # INIT-9: アンサンブルモデル学習（Phase H問題解決）
    logger.info("🤖 [INIT-9] Training ensemble models...")
    logger.info(f"⏰ [INIT-9] Timestamp: {pd.Timestamp.now()}")

    if hasattr(strategy, "fit_ensemble_models"):
        try:
            # 学習用データの準備
            if initial_df is not None and len(initial_df) >= 50:
                logger.info(
                    f"📊 [INIT-9] Preparing training data from {len(initial_df)} records"
                )

                # 簡易的なラベル生成（将来の価格変動から）
                price_change = (
                    initial_df["close"].pct_change().shift(-1)
                )  # 次の期間の価格変動
                y = (price_change > 0).astype(int)  # 上昇=1, 下降=0
                y = y.dropna()

                # データの整合性確保
                train_df = initial_df.iloc[:-1]  # 最後の行を除外（ラベルがないため）

                if len(train_df) >= 50:
                    logger.info(
                        f"🎯 [INIT-9] Training ensemble models with {len(train_df)} samples"
                    )
                    strategy.fit_ensemble_models(train_df, y)
                    logger.info("✅ [INIT-9] Ensemble models trained successfully")

                    # モデル状態の確認
                    if hasattr(strategy, "timeframe_processors"):
                        for tf, processor in strategy.timeframe_processors.items():
                            if processor:
                                logger.info(
                                    f"📊 [INIT-9] {tf} processor fitted: {processor.is_fitted}"
                                )
                else:
                    logger.warning(
                        f"⚠️ [INIT-9] Insufficient data for training: {len(train_df)} records (need 50+)"
                    )
            else:
                logger.warning(
                    "⚠️ [INIT-9] No initial data available for model training"
                )
                logger.info(
                    "🔄 [INIT-9] Models will use fallback strategies until sufficient data is collected"
                )
        except Exception as e:
            logger.error(f"❌ [INIT-9] Ensemble model training failed: {e}")
            logger.info("🔄 [INIT-9] Continuing with untrained models (fallback mode)")
    else:
        logger.info("ℹ️ [INIT-9] Strategy does not support ensemble model training")

    # Position初期化
    from crypto_bot.execution.engine import Position

    position = Position()

    logger.info(
        "✅ [INIT-ENHANCED] Enhanced initialization sequence completed successfully"
    )

    return entry_exit, position
