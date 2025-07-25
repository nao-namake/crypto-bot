"""
INIT段階エラーハンドリング強化版
Phase 2.2: INIT段階エラーハンドリング強化・ATR計算改善

main.pyのINIT-5～INIT-8段階を強化した版
"""

import logging
import time
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def enhanced_init_5_fetch_price_data(
    fetcher, dd: dict, max_retries: int = 5, timeout: int = 120
) -> Optional[pd.DataFrame]:
    """
    INIT-5段階: 初期価格データ取得（強化版）

    Args:
        fetcher: データフェッチャー
        dd: データ設定辞書
        max_retries: 最大再試行回数
        timeout: タイムアウト秒数（Phase H.7: 60→120秒延長）

    Returns:
        DataFrame: 価格データ（失敗時はNone）
    """
    logger.info("📈 [INIT-5] Fetching initial price data for ATR calculation...")
    logger.info(f"⏰ [INIT-5] Timestamp: {pd.Timestamp.now()}")
    logger.info(
        f"🔧 [INIT-5] Configuration: max_retries={max_retries}, timeout={timeout}s (Phase H.7延長)"
    )

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

    # Phase H.3.2: マルチタイムフレーム戦略対応・INIT-5ベースタイムフレーム強制
    # 設定ファイルからベースタイムフレームを明示的に取得（4h直接要求防止）
    base_timeframe = "1h"  # デフォルト

    # multi_timeframe_data設定からベースタイムフレームを取得
    if "multi_timeframe_data" in dd and "base_timeframe" in dd["multi_timeframe_data"]:
        base_timeframe = dd["multi_timeframe_data"]["base_timeframe"]
        logger.info(
            f"🔧 [INIT-5] Using base_timeframe from multi_timeframe_data: {base_timeframe}"
        )
    else:
        # フォールバック: 通常のtimeframe設定を使用（ただし4hは強制的に1hに変更）
        timeframe_raw = dd.get("timeframe", "1h")
        if timeframe_raw == "4h":
            base_timeframe = "1h"  # 4h要求を強制的に1hに変換
            logger.warning(
                "🚨 [INIT-5] Phase H.3.2: 4h timeframe detected, forcing to 1h (Bitbank API compatibility)"
            )
        else:
            base_timeframe = timeframe_raw
            logger.info(
                f"🔧 [INIT-5] Using timeframe from data config: {base_timeframe}"
            )

    timeframe = base_timeframe
    # Phase H.7.1: INIT-5専用の軽量設定（ATR計算に必要な最小限）
    init_limit = 30  # ATR計算に十分な量（period=14 + バッファ）
    init_paginate = False  # ページネーション無効化で高速化

    logger.info(
        f"🔧 [INIT-5] Phase H.7 Optimized: timeframe={timeframe}, limit={init_limit}, paginate={init_paginate}"
    )
    logger.info(
        "🔧 [INIT-5] Using lightweight settings for faster initialization (30 records, no pagination)"
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
                # Phase H.7.1: INIT-5専用の軽量設定を使用
                return fetcher.get_price_df(
                    timeframe=timeframe,
                    since=since_time,  # Phase H.6.1: since時刻を追加
                    limit=init_limit,  # Phase H.7.1: 30レコードのみ
                    paginate=init_paginate,  # Phase H.7.1: False（ページネーション無効）
                    per_page=30,  # Phase H.7.1: 単一呼び出しで全データ取得
                    # ページネーション無効なので以下は不要だが念のため設定
                    max_consecutive_empty=1,
                    max_consecutive_no_new=1,
                    max_attempts=1,
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


def enhanced_init_6_calculate_atr(
    initial_df: Optional[pd.DataFrame], period: int = 14
) -> Optional[pd.Series]:
    """
    INIT-6段階: ATR計算（強化版）

    Args:
        initial_df: 初期価格データ
        period: ATR計算期間

    Returns:
        Series: ATR値（失敗時はNone）
    """
    logger.info("🔢 [INIT-6] Calculating ATR...")
    logger.info(f"⏰ [INIT-6] Timestamp: {pd.Timestamp.now()}")
    logger.info(f"🔧 [INIT-6] ATR period: {period}")

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

            # ATR計算に必要な最小レコード数確認
            min_records = period + 1
            if len(initial_df) < min_records:
                logger.error(
                    f"❌ [INIT-6] Insufficient data for ATR calculation: "
                    f"{len(initial_df)} < {min_records}"
                )
                return None

            logger.info(
                f"📊 [INIT-6] Data validation passed: "
                f"{len(initial_df)} records available"
            )

            # ATR計算実行
            from crypto_bot.indicator.calculator import IndicatorCalculator

            calculator = IndicatorCalculator()

            start_time = time.time()
            atr_series = calculator.calculate_atr(initial_df, period=period)
            calc_time = time.time() - start_time

            logger.info(
                f"✅ [INIT-6] ATR calculated successfully: "
                f"{len(atr_series)} values in {calc_time:.2f}s"
            )

            # ATR値の品質確認
            if atr_series is not None and not atr_series.empty:
                latest_atr = atr_series.iloc[-1]
                mean_atr = atr_series.mean()
                logger.info(
                    f"📊 [INIT-6] ATR statistics: "
                    f"latest={latest_atr:.6f}, mean={mean_atr:.6f}"
                )

                # 異常値チェック
                if latest_atr <= 0 or latest_atr > 1.0:
                    logger.warning(
                        f"⚠️ [INIT-6] ATR value may be unusual: {latest_atr}"
                    )  # noqa: E501

            else:
                logger.error("❌ [INIT-6] ATR calculation returned empty series")
                atr_series = None

        except Exception as e:
            logger.error(f"❌ [INIT-6] ATR calculation failed: {e}")
            logger.error(f"❌ [INIT-6] Error type: {type(e).__name__}")
            atr_series = None

    else:
        logger.warning("⚠️ [INIT-6] No initial data available for ATR calculation")

    return atr_series


def enhanced_init_6_fallback_atr(period: int = 14) -> pd.Series:
    """
    INIT-6段階: ATRフォールバック値生成（強化版）

    Args:
        period: ATR期間

    Returns:
        Series: フォールバックATR値
    """
    logger.info("🔧 [INIT-6] Using enhanced fallback ATR calculation...")

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


def enhanced_init_7_initialize_entry_exit(
    strategy, risk_manager, atr_series: pd.Series
) -> Any:
    """
    INIT-7段階: Entry/Exitシステム初期化（強化版）

    Args:
        strategy: 取引戦略
        risk_manager: リスク管理
        atr_series: ATR値

    Returns:
        EntryExit: Entry/Exitシステム
    """
    logger.info("🎯 [INIT-7] Initializing Entry/Exit system...")
    logger.info(f"⏰ [INIT-7] Timestamp: {pd.Timestamp.now()}")

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
def enhanced_init_sequence(fetcher, dd: dict, strategy, risk_manager, balance: float):
    """
    INIT-5～INIT-8の強化版シーケンス

    Args:
        fetcher: データフェッチャー
        dd: データ設定
        strategy: 取引戦略
        risk_manager: リスク管理
        balance: 初期残高

    Returns:
        tuple: (entry_exit, position)
    """
    logger.info("🚀 [INIT-ENHANCED] Starting enhanced initialization sequence...")

    # INIT-5: 初期価格データ取得（強化版）
    initial_df = enhanced_init_5_fetch_price_data(fetcher, dd)

    # INIT-6: ATR計算（強化版）
    atr_series = enhanced_init_6_calculate_atr(initial_df)

    # フォールバック処理
    if atr_series is None or atr_series.empty:
        logger.info("🔧 [INIT-6] Using enhanced fallback ATR calculation")
        atr_series = enhanced_init_6_fallback_atr()

    # INIT-7: Entry/Exit初期化（強化版）
    entry_exit = enhanced_init_7_initialize_entry_exit(
        strategy, risk_manager, atr_series
    )
    entry_exit.current_balance = balance

    # INIT-8: キャッシュクリア（強化版）
    enhanced_init_8_clear_cache()

    # Position初期化
    from crypto_bot.execution.engine import Position

    position = Position()

    logger.info(
        "✅ [INIT-ENHANCED] Enhanced initialization sequence completed successfully"
    )

    return entry_exit, position
