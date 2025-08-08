"""
Live trading command for Bitbank
"""

import logging
import os
import sys
import time
from typing import Optional

import click
import pandas as pd

from crypto_bot.api.health import update_init_status, update_status
from crypto_bot.data.fetcher import MarketDataFetcher
from crypto_bot.execution.engine import EntryExit, Position
from crypto_bot.execution.factory import create_exchange_client
from crypto_bot.risk.manager import RiskManager
from crypto_bot.strategy.factory import StrategyFactory
from crypto_bot.utils.config import load_config
from crypto_bot.utils.pre_computed_cache import PreComputedCache
from crypto_bot.utils.trading_integration_service import TradingIntegrationService

logger = logging.getLogger(__name__)


def resolve_env_var(value):
    """環境変数置換パターン ${ENV_VAR} を解決"""
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        env_var_name = value[2:-1]  # ${} を除去
        return os.getenv(env_var_name)
    return value


def initialize_bitbank_credentials(dd: dict) -> tuple[str, str]:
    """Bitbank API認証情報を初期化"""
    api_key = resolve_env_var(dd.get("api_key")) or os.getenv("BITBANK_API_KEY")
    api_secret = resolve_env_var(dd.get("api_secret")) or os.getenv(
        "BITBANK_API_SECRET"
    )

    if not api_key or not api_secret:
        logger.error(
            "Bitbank API credentials not found. Please set BITBANK_API_KEY "
            "and BITBANK_API_SECRET environment variables"
        )
        logger.error(f"Config api_key: {dd.get('api_key', 'Not set')}")
        api_key_status = "Set" if os.getenv("BITBANK_API_KEY") else "Not set"
        logger.error(f"Env BITBANK_API_KEY: {api_key_status}")
        secret_status = "Set" if os.getenv("BITBANK_API_SECRET") else "Not set"
        logger.error(f"Env BITBANK_API_SECRET: {secret_status}")
        sys.exit(1)

    logger.info(
        f"✅ Bitbank API credentials resolved successfully - " f"Key: {api_key[:8]}..."
    )
    if dd.get("api_key", "").startswith("${"):
        logger.info(
            "📝 Environment variable substitution performed for API credentials"
        )

    return api_key, api_secret


def initialize_strategy(cfg: dict, config_path: str, fetcher) -> object:
    """戦略を初期化"""
    strategy_config = cfg.get("strategy", {})
    strategy_type = strategy_config.get("type", "single")
    strategy_name = strategy_config.get("name", "ml")

    logger.info(f"📊 [INIT-3] Strategy Type: {strategy_type}")
    logger.info(f"📊 [INIT-3] Strategy Name: {strategy_name}")
    logger.info(f"⏰ [INIT-3] Timestamp: {pd.Timestamp.now()}")
    logger.info("🤖 [INIT-3] Initializing Strategy (this may take time)...")

    # モデルパス検証
    sp = strategy_config.get("params", {})
    model_path = sp.get("model_path", "model.pkl")

    if not os.path.isabs(model_path):
        # 相対パスの場合、プロジェクトルートまたはmodelフォルダを基準に解決
        possible_paths = [
            os.path.join(os.getcwd(), model_path),
            os.path.join(os.getcwd(), "model", model_path),
            os.path.join(os.path.dirname(config_path), "..", "model", model_path),
        ]
        for path in possible_paths:
            if os.path.exists(path):
                model_path = path
                strategy_config["params"]["model_path"] = model_path
                break
        else:
            logger.error(f"Model file not found: {model_path}")
            sys.exit(1)

    logger.info(f"📊 [INIT-3] Using model: {model_path}")

    # StrategyFactoryで戦略作成
    if strategy_type == "multi_timeframe_ensemble":
        logger.info("🔄 [INIT-3] Initializing Multi-Timeframe Ensemble Strategy...")
        strategy = StrategyFactory.create_strategy(strategy_config, cfg)

        # マルチタイムフレーム戦略にデータフェッチャーを設定
        if hasattr(strategy, "set_data_fetcher"):
            logger.info(
                "🔗 [INIT-3] Setting data fetcher for multi-timeframe strategy..."
            )
            strategy.set_data_fetcher(fetcher)
            logger.info(
                "✅ [INIT-3] Data fetcher configured for multi-timeframe strategy"
            )

        logger.info(
            "✅ [INIT-3] Multi-Timeframe Ensemble Strategy initialized successfully"
        )
    else:
        # 従来のML戦略（後方互換性のため）
        logger.info("🤖 [INIT-3] Initializing traditional ML Strategy...")
        strategy = StrategyFactory.create_strategy(strategy_config, cfg)
        logger.info("✅ [INIT-3] Traditional Strategy initialized successfully")

    # 特徴量システム初期化を記録
    try:
        update_init_status("features", "feature_system")
    except Exception:
        pass

    return strategy


def get_account_balance(fetcher, cfg: dict) -> float:
    """口座残高を取得（フォールバック付き）"""
    try:
        # 実際の口座残高を取得
        balance_data = fetcher.fetch_balance()
        jpy_balance = balance_data.get("JPY", {}).get("free", 0.0)
        if jpy_balance > 0:
            balance = jpy_balance
            logger.info(f"💰 [INIT-4] Real account balance: {balance:.2f} JPY")
            return balance
        else:
            raise ValueError("JPY balance is 0 or not found")
    except Exception as e:
        logger.warning(f"⚠️ Failed to get real balance: {e}")
        # フォールバック: live設定またはbacktest設定から取得
        live_config = cfg.get("live", {})
        if "starting_balance" in live_config:
            balance = live_config["starting_balance"]
            logger.info(f"💰 [INIT-4] Using live.starting_balance: {balance:.2f} JPY")
        else:
            balance = cfg["backtest"]["starting_balance"]
            logger.info(
                f"💰 [INIT-4] Using backtest.starting_balance as fallback: "
                f"{balance:.2f} JPY"
            )
        return balance


def fetch_latest_data(fetcher, dd: dict, symbol: str) -> Optional[pd.DataFrame]:
    """最新のマーケットデータを取得"""
    try:
        logger.info("📊 [DATA-FETCH] Fetching price data from Bitbank API...")
        logger.info(f"⏰ [DATA-FETCH] Timestamp: {pd.Timestamp.now()}")

        # 最新データを確実に取得（設定ファイルのsince設定を使用）
        current_time = pd.Timestamp.now(tz="UTC")

        if dd.get("since"):
            since_time = pd.Timestamp(dd["since"])
            if since_time.tz is None:
                since_time = since_time.tz_localize("UTC")
            logger.info(f"🔍 [DEBUG] Using config since: {since_time}")
        else:
            # 動的since_hours計算（土日ギャップ・祝日対応）
            base_hours = dd.get("since_hours", 48)

            # 曜日判定（月曜日=0, 日曜日=6）
            current_day = current_time.dayofweek
            current_hour = current_time.hour

            # 土日ギャップ対応
            if current_day == 0:  # 月曜日
                # 月曜日は土日ギャップを考慮して延長
                extended_hours = base_hours + 48  # 2日間追加
                logger.info(
                    f"🗓️ Monday detected: extending lookback from {base_hours}h to {extended_hours}h"
                )
                hours_back = extended_hours
            elif current_day <= 1 and current_hour < 12:  # 月曜・火曜午前
                # 月曜午後・火曜午前も少し延長
                extended_hours = base_hours + 24  # 1日間追加
                logger.info(
                    f"🌅 Early week detected: extending lookback from {base_hours}h to {extended_hours}h"
                )
                hours_back = extended_hours
            else:
                # 平日は通常の設定
                hours_back = base_hours

            # タイムスタンプ妥当性検証・修正
            since_time = current_time - pd.Timedelta(hours=hours_back)
            current_timestamp = int(current_time.timestamp() * 1000)
            since_timestamp = int(since_time.timestamp() * 1000)

            # 未来タイムスタンプ検出・修正
            if since_timestamp > current_timestamp:
                logger.error(
                    f"🚨 [PHASE-H22.2] CRITICAL: Future timestamp detected! since={since_timestamp}, current={current_timestamp}"
                )
                # 安全な過去時刻に修正（96時間前）
                since_time = current_time - pd.Timedelta(hours=96)
                since_timestamp = int(since_time.timestamp() * 1000)
                logger.warning(
                    f"🔧 [PHASE-H22.2] Auto-corrected to safe past time: {since_time} (timestamp={since_timestamp})"
                )

            # 極端に古いタイムスタンプ検出・修正
            max_hours_back = 720  # 30日間の上限
            if hours_back > max_hours_back:
                logger.warning(
                    f"⚠️ [PHASE-H22.2] Excessive hours_back detected: {hours_back}h > {max_hours_back}h, capping"
                )
                hours_back = max_hours_back
                since_time = current_time - pd.Timedelta(hours=hours_back)

        logger.info(
            f"🔄 Fetching latest data since: {since_time} " f"(current: {current_time})"
        )

        # ベースタイムフレーム決定
        base_timeframe = "1h"  # デフォルト
        if (
            "multi_timeframe_data" in dd
            and "base_timeframe" in dd["multi_timeframe_data"]
        ):
            base_timeframe = dd["multi_timeframe_data"]["base_timeframe"]
            logger.info(
                f"🔧 [DATA-FETCH] Using base_timeframe from multi_timeframe_data: {base_timeframe}"
            )
        else:
            # フォールバック: 通常のtimeframe設定を使用（ただし4hは強制的に1hに変更）
            timeframe_raw = dd.get("timeframe", "1h")
            if timeframe_raw == "4h":
                base_timeframe = "1h"  # 4h要求を強制的に1hに変換
                logger.warning(
                    "🚨 [DATA-FETCH] Phase H.3.2: 4h timeframe detected in main loop, forcing to 1h (Bitbank API compatibility)"
                )
            else:
                base_timeframe = timeframe_raw
                logger.info(
                    f"🔧 [DATA-FETCH] Using timeframe from data config: {base_timeframe}"
                )

        price_df = fetcher.get_price_df(
            timeframe=base_timeframe,
            since=since_time,
            limit=dd.get("limit", 500),
            paginate=dd.get("paginate", True),
            per_page=dd.get("per_page", 100),
            max_consecutive_empty=dd.get("max_consecutive_empty", None),
            max_consecutive_no_new=dd.get("max_consecutive_no_new", None),
            max_attempts=dd.get("max_attempts", None),
        )
        logger.info(
            f"✅ [DATA-FETCH] Price data fetched successfully: "
            f"{len(price_df)} records"
        )
        logger.info(f"⏰ [DATA-FETCH] Fetch completed at: {pd.Timestamp.now()}")
        return price_df
    except Exception as e:
        logger.error(f"❌ [DATA-FETCH] Failed to fetch price data: {e}")
        logger.info("⏰ [DATA-FETCH] Waiting 30 seconds before retry...")
        return None


def execute_bitbank_trade(
    order,
    position,
    symbol: str,
    exchange_id: str,
    api_key: str,
    api_secret: str,
    cfg: dict,
    dd: dict,
    integration_service=None,
    is_exit: bool = False,
) -> bool:
    """Bitbank実取引を実行"""
    try:
        if exchange_id == "bitbank":
            # Bitbank実取引
            # 信用取引モード設定の取得
            live_config = cfg.get("live", {})
            margin_config = live_config.get("margin_trading", {})
            margin_enabled = margin_config.get("enabled", False)
            force_margin = margin_config.get("force_margin_mode", False)
            verify_margin = margin_config.get("verify_margin_status", False)

            # force_margin_mode設定処理
            if force_margin:
                margin_enabled = True
                logger.info(
                    "🔒 Force margin mode enabled - overriding margin_enabled setting"
                )

            logger.info(
                f"Margin trading mode: {margin_enabled} (force: {force_margin}, verify: {verify_margin})"
            )

            client = create_exchange_client(
                exchange_id=exchange_id,
                api_key=api_key,
                api_secret=api_secret,
                ccxt_options=dd.get("ccxt_options", {}),
                margin_mode=margin_enabled,  # 信用取引モード有効化
            )

            # マージン状態検証（verify_margin_status=trueの場合）
            if verify_margin:
                try:
                    if hasattr(client, "is_margin_enabled"):
                        actual_margin_status = client.is_margin_enabled()
                        logger.info(
                            f"🔍 Margin status verification: expected={margin_enabled}, actual={actual_margin_status}"
                        )
                        if margin_enabled and not actual_margin_status:
                            logger.warning(
                                "⚠️ Margin mode mismatch - expected enabled but actual disabled"
                            )
                    elif hasattr(client, "exchange") and hasattr(
                        client.exchange, "privateGetAccount"
                    ):
                        # Bitbank APIでアカウント情報確認
                        account_info = client.exchange.privateGetAccount()
                        logger.info(
                            f"🔍 Account info retrieved for margin verification: {account_info}"
                        )
                except Exception as e:
                    logger.warning(f"🔍 Margin status verification failed: {e}")

            # Phase 8統計システムとExecutionClient統合（Noneチェック追加）
            if integration_service is not None:
                integration_service.integrate_with_execution_client(client)
                logger.debug("📊 Statistics system integrated with execution client")
            else:
                logger.debug("📊 Statistics system not available (fallback mode)")

            # 最小注文量チェック（Bitbank BTC/JPYは0.0001以上）
            min_amount = 0.0001
            if order.lot < min_amount:
                logger.warning(
                    f"⚠️ Order amount {order.lot} "
                    f"too small, adjusting to minimum "
                    f"{min_amount}"
                )
                adjusted_amount = min_amount
            else:
                adjusted_amount = order.lot

            # 実際の注文送信
            order_result = client.create_order(
                symbol=symbol,
                type="market",
                side=order.side.lower(),
                amount=adjusted_amount,
            )

            order_type = "EXIT" if is_exit else "ENTRY"
            logger.info(f"✅ REAL BITBANK {order_type} ORDER EXECUTED: {order_result}")
            return True
        else:
            # 実取引強制化: 非対応取引所での実行を拒否
            logger.error(f"🚨 UNSUPPORTED EXCHANGE: {exchange_id}")
            logger.error("Real trading is only supported for Bitbank")
            logger.error("Configure exchange_id='bitbank' for real trading")
            raise RuntimeError(f"Unsupported exchange for real trading: {exchange_id}")

    except Exception as e:
        logger.error(f"❌ BITBANK ORDER FAILED: {e}")
        logger.error(f"Error details: {type(e).__name__}: {str(e)}")

        if exchange_id == "bitbank":
            # Bitbank APIエラーの詳細ログ
            api_key_status = "Yes" if api_key else "No"
            api_secret_status = "Yes" if api_secret else "No"
            logger.error(f"API Key present: {api_key_status}")
            logger.error(f"API Secret present: {api_secret_status}")
            logger.error(f"Margin mode: {margin_enabled}")
            logger.error(
                f"Order details: {order.side} " f"{order.lot} at {order.price}"
            )

            # エラー40024の場合は信用取引設定の問題として継続実行
            if "40024" in str(e):
                logger.warning(
                    "⚠️ Error 40024 detected - likely " "margin trading permission issue"
                )
                logger.warning(
                    "🔄 Continuing trading loop - " "will retry on next iteration"
                )
            elif "timeout" in str(e).lower() or "connection" in str(e).lower():
                logger.warning("⚠️ Network/timeout error detected")
                logger.warning(
                    "🔄 Continuing trading loop - " "will retry on next iteration"
                )
            else:
                logger.warning("⚠️ Trading error occurred - continuing loop")

        return False


@click.command()
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
@click.option(
    "--max-trades",
    type=int,
    default=0,
    help="0=無限。成立した約定数がこの値に達したらループ終了",
)
@click.option(
    "--simple",
    is_flag=True,
    default=False,
    help="シンプルモード（統計システムなし、最小限の初期化）",
)
def live_bitbank_command(config_path: str, max_trades: int, simple: bool):
    """
    Bitbank本番でのライブトレードを実行。
    97特徴量システムでBTC/JPYペアの実取引を行う。

    --simple フラグを使用すると、統計システムなしの軽量版で実行。
    通常版ではAPIサーバー機能も統合し、ヘルスチェック・トレード状況確認が可能。
    """
    cfg = load_config(config_path)

    # 設定確認
    exchange_id = cfg["data"].get("exchange", "bitbank")
    symbol = cfg["data"].get("symbol", "BTC/JPY")

    init_prefix = "[SIMPLE-INIT]" if simple else "[INIT-1]"
    logger.info(
        f"🚀 {init_prefix} Starting Bitbank live trading{' (Simple Mode)' if simple else ''} - "
        f"Exchange: {exchange_id}, Symbol: {symbol}"
    )
    if not simple:
        logger.info(f"⏰ {init_prefix} Timestamp: {pd.Timestamp.now()}")

    # 初期化状況を更新（通常モードのみ）
    if not simple:
        try:
            update_init_status("basic", "basic_system")
        except Exception:
            pass

    # Phase 3: 外部データ完全無効化 - 外部データキャッシュは使用しない
    dd = cfg.get("data", {})
    # Phase 3で外部API完全除去

    # Bitbank用データフェッチャー初期化
    logger.info("🔌 [INIT-2] Initializing Bitbank data fetcher...")
    logger.info(f"⏰ [INIT-2] Timestamp: {pd.Timestamp.now()}")
    fetcher = MarketDataFetcher(
        exchange_id=exchange_id,
        symbol=symbol,
        ccxt_options=dd.get("ccxt_options", {}),
    )
    logger.info("✅ [INIT-2] Bitbank data fetcher initialized successfully")

    # API認証情報の初期化
    api_key, api_secret = initialize_bitbank_credentials(dd)

    # 戦略の初期化
    strategy = initialize_strategy(cfg, config_path, fetcher)

    # RiskManager初期化
    logger.info("⚖️ [INIT-4] Initializing Risk Manager...")
    logger.info(f"⏰ [INIT-4] Timestamp: {pd.Timestamp.now()}")
    risk_config = cfg.get("risk", {})
    kelly_config = risk_config.get("kelly_criterion", {})
    risk_manager = RiskManager(
        risk_per_trade=risk_config.get("risk_per_trade", 0.01),
        stop_atr_mult=risk_config.get("stop_atr_mult", 1.5),
        kelly_enabled=kelly_config.get("enabled", False),
        kelly_lookback_window=kelly_config.get("lookback_window", 50),
        kelly_max_fraction=kelly_config.get("max_fraction", 0.25),
    )
    logger.info("✅ [INIT-4] Risk Manager initialized successfully")

    position = Position()

    # 口座残高の取得
    balance = get_account_balance(fetcher, cfg)

    # 改善版: 初期データキャッシュを優先し、なければ最小限のデータ取得
    logger.info("🚀 [INIT-5] Starting improved initialization with cache support...")

    # 初期データキャッシュのチェック
    initial_data = None
    cache_loaded = False

    # 事前取得した初期データキャッシュをチェック
    try:
        import pickle
        from pathlib import Path

        # Docker内とローカルの両方で動作するようにパスをチェック
        cache_paths = [
            Path("/app/cache/initial_data.pkl"),  # Docker内
            Path("cache/initial_data.pkl"),  # ローカル
        ]

        for cache_path in cache_paths:
            if cache_path.exists():
                logger.info(f"📦 [INIT-CACHE] Loading initial data from {cache_path}")
                with open(cache_path, "rb") as f:
                    cache_content = pickle.load(f)
                    initial_data = cache_content.get("data")
                    # metadata = cache_content.get("metadata", {})  # 使用されていないためコメントアウト

                if initial_data is not None and not initial_data.empty:
                    logger.info(
                        f"✅ [INIT-CACHE] Loaded {len(initial_data)} records from cache"
                    )
                    logger.info(
                        f"📈 [INIT-CACHE] Data range: {initial_data.index.min()} to {initial_data.index.max()}"
                    )
                    cache_loaded = True

                    # 戦略に初期データを設定
                    if hasattr(strategy, "set_initial_data"):
                        strategy.set_initial_data(initial_data)
                    break

    except Exception as e:
        logger.warning(f"⚠️ [INIT-CACHE] Failed to load cache: {e}")

    # キャッシュがない場合は最小限のデータを取得
    if not cache_loaded:
        logger.info("📊 [INIT-5] No cache found, fetching minimal initial data...")
        try:
            # 最小限の200レコードのみ取得（タイムアウト対策）
            initial_data = fetch_latest_data(fetcher, dd, symbol)
            if initial_data is not None and len(initial_data) >= 100:
                logger.info(
                    f"✅ [INIT-5] Fetched {len(initial_data)} records successfully"
                )
            else:
                logger.warning(
                    "⚠️ [INIT-5] Insufficient initial data, will fetch in main loop"
                )
        except Exception as e:
            logger.error(f"❌ [INIT-5] Failed to fetch initial data: {e}")
            logger.info("🔄 [INIT-5] Will retry in main loop")

    # Phase 12.3: PreComputedCacheもチェック（フォールバック）
    cache = PreComputedCache()
    if not cache_loaded and cache.has_valid_cache():
        logger.info("📦 [INIT-CACHE] Loading from PreComputedCache as fallback...")
        cache_data = cache.load_all()
        if cache_data:
            logger.info(
                f"✅ [INIT-CACHE] Loaded: {len(cache_data.get('market_data', []))} records"
            )
            if hasattr(strategy, "set_cached_data"):
                strategy.set_cached_data(cache_data)

    # 最小限の初期化のみ実行
    entry_exit = EntryExit(cfg, fetcher, risk_manager)
    position = Position()

    # モデル状態の最終確認
    logger.info(
        "🔍 [INIT-VERIFY] Verifying ensemble model states after initialization..."
    )
    if hasattr(strategy, "timeframe_processors"):
        model_ready = False
        for tf, processor in strategy.timeframe_processors.items():
            if processor:
                fitted = processor.is_fitted
                enabled = processor.ensemble_enabled
                logger.info(f"  ✅ {tf} processor: fitted={fitted}, enabled={enabled}")
                if fitted and enabled:
                    model_ready = True
            else:
                logger.warning(f"  ❌ {tf} processor: NOT INITIALIZED")

        if model_ready:
            logger.info(
                "🎯 [INIT-VERIFY] At least one ensemble model is ready for trading"
            )
        else:
            logger.warning(
                "⚠️ [INIT-VERIFY] No ensemble models are ready - will use fallback strategies"
            )
            logger.info(
                "🔄 [INIT-VERIFY] Models will be trained automatically when sufficient data is collected"
            )
    else:
        logger.info("ℹ️ [INIT-VERIFY] Strategy does not use ensemble models")

    # Phase 8統計システム初期化（通常モードのみ）
    integration_service = None
    if not simple:
        logger.info("📊 [INIT-10] Initializing Phase 8 Statistics System...")
        logger.info(f"⏰ [INIT-10] Timestamp: {pd.Timestamp.now()}")

        try:
            # TradingIntegrationService初期化（Cloud Run環境統一）
            integration_service = TradingIntegrationService(
                base_dir="/app",
                initial_balance=balance,  # Phase G.2.4.1: Cloud Run環境パス統一
            )

            # MLStrategyとの統合
            integration_service.integrate_with_ml_strategy(strategy)
            logger.info(
                "✅ [INIT-9] Phase 8 Statistics System initialized successfully"
            )

        except Exception as e:
            logger.warning(f"⚠️ [INIT-9] Statistics System initialization failed: {e}")
            logger.info(
                "🔄 [INIT-9] Continuing with basic status.json fallback system..."
            )

            # Phase G.2.4.2: フォールバック - 基本的なstatus.json作成
            try:
                import json

                basic_status = {
                    "last_updated": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "system_status": "running",
                    "total_profit": 0.0,
                    "trade_count": 0,
                    "position": "No active position",
                    "status": "Statistics system fallback active",
                }
                with open("/app/status.json", "w", encoding="utf-8") as f:
                    json.dump(basic_status, f, indent=2, ensure_ascii=False)
                logger.info(
                    "✅ [INIT-9] Basic status.json created successfully (fallback mode)"
                )
            except Exception as fallback_error:
                logger.error(
                    f"❌ [INIT-9] Fallback status.json creation failed: {fallback_error}"
                )
                logger.info("🔄 [INIT-9] Continuing without status file (minimal mode)")

            integration_service = None  # フォールバックモードではNone
    else:
        logger.info("📊 [SIMPLE-INIT] Skipping statistics system (simple mode)")

    # 初期化状況を更新（通常モードのみ）
    if not simple:
        try:
            update_init_status("statistics", "statistics_system")
        except Exception:
            pass

    trade_done = 0
    complete_prefix = "[SIMPLE-COMPLETE]" if simple else "[INIT-COMPLETE]"
    logger.info(
        f"🎊 {complete_prefix} === Bitbank Live Trading Started{' (Simple)' if simple else ''} ===  Ctrl+C で停止"
    )
    logger.info(
        f"🚀 {complete_prefix} 97特徴量システム稼働中 - Symbol: {symbol}, Balance: {balance}"
    )
    if not simple:
        logger.info(f"⏰ {complete_prefix} Timestamp: {pd.Timestamp.now()}")

    loop_prefix = "[SIMPLE-LOOP]" if simple else "[LOOP-START]"
    logger.info(f"🔄 {loop_prefix} Starting main trading loop...")
    if not simple:
        logger.info(f"⏰ {loop_prefix} Timestamp: {pd.Timestamp.now()}")

    # 初期化完了を記録（通常モードのみ）
    if not simple:
        try:
            update_init_status("complete", "trading_loop")
        except Exception:
            pass

    try:
        while True:
            iter_prefix = "[SIMPLE-LOOP]" if simple else "[LOOP-ITER]"
            logger.info(f"🔄 {iter_prefix} Starting new trading iteration...")
            if not simple:
                logger.info(f"⏰ {iter_prefix} Timestamp: {pd.Timestamp.now()}")

            # 最新データを取得
            price_df = fetch_latest_data(fetcher, dd, symbol)
            if price_df is None:
                time.sleep(30)
                continue

            if price_df.empty:
                logger.warning("No price data received, waiting...")
                time.sleep(30)
                continue

            latest_time = price_df.index[-1]
            # タイムゾーン一致: latest_timeにUTCを付加してtz-aware timestamp同士で計算
            if latest_time.tz is None:
                latest_time = latest_time.tz_localize("UTC")
            time_diff = pd.Timestamp.now(tz="UTC") - latest_time
            hours_old = time_diff.total_seconds() / 3600

            logger.info(
                f"Received {len(price_df)} price records, "
                f"latest: {latest_time} ({hours_old:.1f}h ago)"
            )

            # データ鮮度監視（1時間以上古い場合は警告、3時間以上は強制再取得）
            if hours_old > 3:
                logger.error(
                    f"🚨 Data is {hours_old:.1f} hours old - FORCING FRESH DATA FETCH"
                )
                logger.info("⏰ Waiting 30 seconds before fresh data fetch...")
                time.sleep(30)
                continue
            elif hours_old > 1:
                logger.warning(
                    f"⚠️ Data is {hours_old:.1f} hours old - monitoring for freshness"
                )

            # エントリー判定
            logger.info("📊 [ENTRY-JUDGE] Starting entry order generation...")
            logger.info(f"⏰ [ENTRY-JUDGE] Timestamp: {pd.Timestamp.now()}")
            logger.info(f"🔍 [DEBUG] Price data shape: {tuple(price_df.shape)}")
            logger.info(f"🔍 [DEBUG] Price data latest: {price_df.tail(1).to_dict()}")

            try:
                entry_order = entry_exit.generate_entry_order(price_df, position)
                logger.info(
                    f"✅ [ENTRY-JUDGE] Entry judgment completed - "
                    f"Order exists: {entry_order.exist}"
                )

                # シグナル詳細情報ログ
                if hasattr(entry_order, "side") and hasattr(entry_order, "price"):
                    logger.info(
                        f"🔍 [DEBUG] Entry order details: side={getattr(entry_order, 'side', 'N/A')}, price={getattr(entry_order, 'price', 'N/A')}, lot={getattr(entry_order, 'lot', 'N/A')}"
                    )

            except Exception as entry_error:
                logger.error(
                    f"❌ [ENTRY-JUDGE] Entry order generation failed: {entry_error}"
                )
                logger.info("🔄 [ENTRY-JUDGE] Continuing to next iteration...")
                time.sleep(30)
                continue

            prev_trades = trade_done
            if entry_order.exist:
                logger.info(
                    f"Entry order generated: {entry_order.side} "
                    f"{entry_order.lot} at {entry_order.price}"
                )

                # 実際のBitbank取引実行
                if execute_bitbank_trade(
                    entry_order,
                    position,
                    symbol,
                    exchange_id,
                    api_key,
                    api_secret,
                    cfg,
                    dd,
                    integration_service,
                ):
                    # ポジション更新
                    position.exist = True
                    position.side = entry_order.side
                    position.entry_price = entry_order.price
                    position.lot = entry_order.lot
                    position.stop_price = entry_order.stop_price

                    trade_done += 1
                    logger.info(
                        f"Trade #{trade_done} executed on Bitbank - "
                        f"Position: {position.side} {position.lot}"
                    )
                else:
                    # エラーが発生した場合は60秒待機
                    logger.info("⏰ Waiting 60 seconds before next trading attempt...")
                    time.sleep(60)

            # エグジット判定
            logger.info("📊 [EXIT-JUDGE] Starting exit order generation...")
            logger.info(f"⏰ [EXIT-JUDGE] Timestamp: {pd.Timestamp.now()}")
            logger.info(
                f"🔍 [DEBUG] Current position state: exist={position.exist}, side={getattr(position, 'side', 'N/A')}"
            )

            try:
                exit_order = entry_exit.generate_exit_order(price_df, position)
                logger.info(
                    f"✅ [EXIT-JUDGE] Exit judgment completed - "
                    f"Order exists: {exit_order.exist}"
                )

                # エグジットシグナル詳細情報ログ
                if hasattr(exit_order, "side") and hasattr(exit_order, "price"):
                    logger.info(
                        f"🔍 [DEBUG] Exit order details: side={getattr(exit_order, 'side', 'N/A')}, price={getattr(exit_order, 'price', 'N/A')}, lot={getattr(exit_order, 'lot', 'N/A')}"
                    )

            except Exception as exit_error:
                logger.error(
                    f"❌ [EXIT-JUDGE] Exit order generation failed: {exit_error}"
                )
                logger.info("🔄 [EXIT-JUDGE] Continuing to next iteration...")
                time.sleep(30)
                continue

            if exit_order.exist:
                logger.info(
                    f"Exit order generated: {exit_order.side} "
                    f"{exit_order.lot} at {exit_order.price}"
                )

                # 実際のBitbank取引実行
                if execute_bitbank_trade(
                    exit_order,
                    position,
                    symbol,
                    exchange_id,
                    api_key,
                    api_secret,
                    cfg,
                    dd,
                    integration_service,
                    is_exit=True,
                ):
                    # ポジション解消
                    position.exist = False
                    position.side = None

                    trade_done += 1
                    logger.info(
                        f"Trade #{trade_done} exit executed on Bitbank - "
                        f"Position closed"
                    )

            # 残高を EntryExit へ反映
            entry_exit.current_balance = balance

            # ダッシュボード用ステータス更新（通常モードのみ）
            profit = balance - cfg["backtest"]["starting_balance"]
            if not simple:
                update_status(
                    total_profit=profit,
                    trade_count=trade_done,
                    position=position.side if position.exist else None,
                )

            # 定期的なステータス出力
            if trade_done != prev_trades:
                pos_str = position.side if position.exist else "None"
                logger.info(
                    f"Status - Trades: {trade_done}, "
                    f"Profit: {profit:.2f}, Position: {pos_str}"
                )

            if max_trades and trade_done >= max_trades:
                logger.info("Reached max-trades. Exit.")
                break

            # 取引間隔の設定
            interval = cfg.get("live", {}).get("trade_interval", 60)
            logger.info(
                f"⏰ [SLEEP] Waiting {interval} seconds until next iteration..."
            )
            logger.info(f"⏰ [SLEEP] Sleep start: {pd.Timestamp.now()}")
            time.sleep(interval)
            logger.info(f"⏰ [SLEEP] Sleep end: {pd.Timestamp.now()}")

    except KeyboardInterrupt:
        logger.info("🛑 [SHUTDOWN] Interrupted. Bye.")
    except Exception as e:
        logger.error(f"❌ [ERROR] Live trading error: {e}")
        logger.error(f"⏰ [ERROR] Error occurred at: {pd.Timestamp.now()}")
        import traceback

        logger.error(f"🔍 [ERROR] Traceback: {traceback.format_exc()}")
        raise
