"""
統合取引システム制御 - TradingOrchestrator - Phase 49完了

Application Service Layer として、高レベル統合制御のみを担当。
具体的なビジネスロジックは各Phase層に委譲し、真のレイヤー分離を実現。

Phase 49完了:
- 高レベルフロー制御（データ取得→特徴量生成→戦略実行→ML予測→リスク評価→取引判断）
- 依存性注入基盤（DataService・FeatureService・StrategyManager・ExecutionService等）
- バックテストモード対応（ログレベル動的変更・Discord無効化・API呼び出しモック化）
- エラーハンドリング階層化（DataFetchError・ModelPredictionError・TradingError等）

設計原則:
- Application Service Pattern: 高レベルフロー制御のみ
- 依存性注入: テスト容易性の確保
- 責任分離: 具体的実装は各Phaseに委譲
- エラーハンドリング階層化: 適切なレベルでの例外処理

Phase 35: バックテスト最適化実装
Phase 28-29: Application Service Pattern確立・責任分離・依存性注入基盤
"""

import asyncio
import time
from datetime import datetime

# 循環インポート回避のため、型ヒントでのみ使用
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Protocol, Union

import numpy as np
import pandas as pd

from ...data.data_pipeline import DataRequest, TimeFrame
from ...features.feature_generator import FeatureGenerator

if TYPE_CHECKING:
    from ...strategies.base.strategy_base import StrategySignal
    from ...trading import ExecutionResult, TradeEvaluation

# BacktestReporter は遅延インポートで循環インポート回避
from ..config import Config, get_threshold
from ..exceptions import (
    CryptoBotError,
    DataProcessingError,
    FileIOError,
    HealthCheckError,
    ModelLoadError,
)
from ..execution import BacktestRunner, LiveTradingRunner, PaperTradingRunner
from ..logger import CryptoBotLogger

# BacktestReportWriter削除: reporter.pyに統合済み
from ..reporting.paper_trading_reporter import PaperTradingReporter
from ..services import (
    HealthChecker,
    SystemRecoveryService,
    TradingCycleManager,
    TradingLoggerService,
)
from .protocols import (
    DataServiceProtocol,
    ExecutionServiceProtocol,
    FeatureServiceProtocol,
    MLServiceProtocol,
    RiskServiceProtocol,
    StrategyServiceProtocol,
)

# Phase層インターフェース定義は protocols.py に移動


class TradingOrchestrator:
    """
    Application Service Layer - 統合取引システム制御（Phase 38.4完了版）

    高レベルなフロー制御のみを担当し、具体的なビジネスロジックは
    各Phase層に委譲。依存性注入によりテスト容易性を確保。.
    """

    def __init__(
        self,
        config: Config,
        logger: CryptoBotLogger,
        data_service: DataServiceProtocol,
        feature_service: FeatureServiceProtocol,
        strategy_service: StrategyServiceProtocol,
        ml_service: MLServiceProtocol,
        risk_service: RiskServiceProtocol,
        execution_service: ExecutionServiceProtocol,
    ):
        """
        TradingOrchestrator初期化（依存性注入）

        Args:
            config: システム設定
            logger: ログシステム
            data_service: データ層サービス
            feature_service: 特徴量生成サービス
            strategy_service: 戦略評価サービス
            ml_service: ML予測サービス
            risk_service: リスク管理サービス
            execution_service: 注文実行サービス（Phase 38.4完了版）.
        """
        self.config = config
        self.logger = logger

        # 依存性注入されたサービス（Protocolベース）
        self.data_service = data_service
        self.feature_service = feature_service
        self.strategy_service = strategy_service
        self.ml_service = ml_service
        self.risk_service = risk_service
        self.execution_service = execution_service

        # Phase 28-29最適化: バックテストレポーター初期化（遅延インポート）
        from ...backtest.reporter import BacktestReporter

        self.backtest_reporter = BacktestReporter()

        # Phase 49.15: ExecutionServiceにTradeTracker注入（統一インスタンス使用）
        self.execution_service.trade_tracker = self.backtest_reporter.trade_tracker

        self.paper_trading_reporter = PaperTradingReporter(logger)

        # Phase 28-29最適化: 新バックテストシステム（本番同一ロジック）
        self.backtest_runner = BacktestRunner(self, logger)
        self.paper_trading_runner = PaperTradingRunner(self, logger)
        self.live_trading_runner = LiveTradingRunner(self, logger)

        # Phase 28-29最適化: サービス層初期化（分離済み）
        self.health_checker = HealthChecker(self, logger)
        self.system_recovery = SystemRecoveryService(self, logger)
        self.trading_logger = TradingLoggerService(self, logger)
        self.trading_cycle_manager = TradingCycleManager(self, logger)

        # 初期化フラグ
        self._initialized = False

    async def initialize(self) -> bool:
        """
        サービス初期化確認

        実際の初期化は各サービスで完了済み前提
        ここでは接続性確認のみ実行

        Returns:
            初期化成功の可否.
        """
        try:
            self.logger.info("🚀 TradingOrchestrator初期化確認開始")

            # 各サービスの健全性チェック（軽量）
            await self.health_checker.check_all_services()

            self._initialized = True
            self.logger.info("🎉 TradingOrchestrator初期化確認完了", discord_notify=True)
            return True

        except AttributeError as e:
            self.logger.error(
                f"❌ サービス初期化不完了: {e}",
                discord_notify=True,
            )
            return False
        except (RuntimeError, SystemError) as e:
            self.logger.error(
                f"❌ システム初期化エラー: {e}",
                discord_notify=True,
            )
            return False
        except Exception as e:
            # 予期しないエラーは再送出
            self.logger.critical(
                f"❌ 予期しない初期化エラー: {e}",
                discord_notify=True,
            )
            raise CryptoBotError(f"TradingOrchestrator初期化で予期しないエラー: {e}")

    async def run(self) -> None:
        """
        TradingOrchestrator実行（モード設定一元化対応）

        実行モードはconfig.modeから自動取得します。
        """
        if not self._initialized:
            raise CryptoBotError("TradingOrchestratorが初期化されていません")

        mode = self.config.mode
        self.logger.info(f"TradingOrchestrator実行開始 - モード: {mode.upper()}（Configから取得）")

        try:
            # Phase 28-29最適化: BacktestRunner統合実行
            if mode == "backtest":
                await self._run_backtest_mode()
            elif mode == "paper":
                await self.paper_trading_runner.run_with_error_handling()
            elif mode == "live":
                await self.live_trading_runner.run_with_error_handling()
            else:
                raise ValueError(f"無効なモード: {mode}")

        except KeyboardInterrupt:
            self.logger.info("ユーザーによる終了要求を受信")
        except (AttributeError, TypeError) as e:
            # 設定やサービスの初期化問題
            self.logger.error(f"設定・初期化エラー: {e}", discord_notify=False)
            raise CryptoBotError(f"システム初期化エラー: {e}")
        except (ConnectionError, TimeoutError) as e:
            # 外部サービス接続問題
            self.logger.error(f"外部サービス接続エラー: {e}", discord_notify=False)
            raise CryptoBotError(f"外部接続エラー: {e}")
        except (RuntimeError, SystemError, MemoryError) as e:
            # システムリソース・実行時エラー
            self.logger.error(f"システム実行エラー: {e}", discord_notify=False)
            raise CryptoBotError(f"システム実行エラー: {e}")
        except Exception as e:
            # 🚨 真に予期しないエラーのみ - 詳細調査のためcricitialログ
            self.logger.critical(f"予期しないシステムエラー: {e}")
            raise CryptoBotError(f"予期しないシステム実行エラー: {e}")

        self.logger.info("TradingOrchestrator実行終了")

    async def run_trading_cycle(self) -> None:
        """
        取引サイクル実行（Phase 38.4完了版）

        TradingCycleManagerに処理を委譲し、orchestratorは制御のみ担当。
        約200行のロジックをサービス層に分離。
        """
        try:
            await self.trading_cycle_manager.execute_trading_cycle()
        except CryptoBotError:
            # 既にTradingCycleManager内で処理済み
            raise
        except Exception as e:
            # 予期しない最上位エラー
            self.logger.critical(f"❌ 取引サイクル最上位エラー: {e}")
            raise CryptoBotError(f"取引サイクル最上位で予期しないエラー: {e}")

    async def _run_backtest_mode(self) -> None:
        """
        バックテストモード実行（Phase 35: 高速化最適化）

        Phase 35最適化:
        - ログレベル動的変更（INFO→WARNING: 99.9%削減）
        - Discord通知無効化（ネットワーク通信削減）
        - API呼び出しモック化（エラー20003排除）
        - 進捗ログ間隔拡大（90%削減）
        実行時間: 6-8時間 → 5-10分（60-96倍高速化）
        """
        import logging

        from ..config import get_threshold

        # Phase 35: バックテスト最適化設定取得
        backtest_log_level = get_threshold("backtest.log_level", "WARNING")
        discord_enabled = get_threshold("backtest.discord_enabled", False)

        # 元の設定を保存（復元用）
        original_log_level = self.logger.logger.level
        original_discord_enabled = getattr(self.logger, "_discord_manager", None) is not None

        try:
            # Phase 35: ログレベルを動的変更（大量ログ出力を抑制）
            log_level_value = getattr(logging, backtest_log_level.upper(), logging.WARNING)
            self.logger.logger.setLevel(log_level_value)
            # Phase 35: すべてのハンドラーのログレベルも変更
            for handler in self.logger.logger.handlers:
                handler.setLevel(log_level_value)
            # Phase 35: rootロガーも変更（全コンポーネントに適用）
            logging.getLogger().setLevel(log_level_value)
            self.logger.info(
                f"📊 バックテストモード開始（Phase 35最適化: ログ={backtest_log_level}）"
            )

            # Phase 35: Discord通知を一時的に無効化（ネットワーク通信削減）
            discord_manager_backup = None
            if not discord_enabled and hasattr(self.logger, "_discord_manager"):
                discord_manager_backup = self.logger._discord_manager
                self.logger._discord_manager = None
                self.logger.info("🔇 Discord通知を一時的に無効化（バックテスト最適化）")

            # データサービスをバックテストモードに設定
            self.data_service.set_backtest_mode(True)

            # バックテスト実行（BacktestRunnerに委譲）
            success = await self.backtest_runner.run()

            if success:
                self.logger.info("✅ オーケストレーターバックテスト制御完了", discord_notify=True)
            else:
                self.logger.warning("⚠️ バックテスト実行で問題が発生しました", discord_notify=False)

        except (FileNotFoundError, OSError) as e:
            # データファイル・I/Oエラー
            self.logger.error(f"❌ バックテストデータI/Oエラー: {e}", discord_notify=False)
            raise DataProcessingError(f"バックテスト用データ読み込みエラー: {e}")
        except (ValueError, KeyError) as e:
            # データ形式・設定値エラー
            self.logger.error(f"❌ バックテストデータ形式エラー: {e}", discord_notify=False)
            raise DataProcessingError(f"バックテストデータ処理エラー: {e}")
        except (ImportError, ModuleNotFoundError) as e:
            # モジュール・ライブラリエラー
            self.logger.error(f"❌ バックテストモジュールエラー: {e}", discord_notify=False)
            raise HealthCheckError(f"バックテスト依存モジュールエラー: {e}")
        except Exception as e:
            # その他の予期しないエラー
            self.logger.error(f"❌ バックテスト予期しないエラー: {e}", discord_notify=True)
            raise
        finally:
            # Phase 35: ログレベルを元に戻す
            self.logger.logger.setLevel(original_log_level)
            # Phase 35: すべてのハンドラーのログレベルも復元
            for handler in self.logger.logger.handlers:
                handler.setLevel(original_log_level)
            # Phase 35: rootロガーも復元
            logging.getLogger().setLevel(original_log_level)

            # Phase 35: Discord通知を元に戻す
            if discord_manager_backup is not None:
                self.logger._discord_manager = discord_manager_backup

            # バックテストモード解除・クリーンアップ
            self.data_service.set_backtest_mode(False)
            self.data_service.clear_backtest_data()

            self.logger.info("✅ バックテストモード設定を復元しました")


async def create_trading_orchestrator(
    config: Config, logger: CryptoBotLogger
) -> TradingOrchestrator:
    """
    TradingOrchestrator作成用ファクトリー関数

    依存性の組み立てとサービス初期化を自動化し、
    main.pyからの利用を簡潔にします。

    Args:
        config: システム設定
        logger: ログシステム

    Returns:
        初期化済みTradingOrchestrator.
    """
    from ...core.reporting.discord_notifier import DiscordManager
    from ...data.bitbank_client import BitbankClient
    from ...data.data_pipeline import DataPipeline
    from ...strategies.base.strategy_manager import StrategyManager
    from ...strategies.implementations.adx_trend import ADXTrendStrengthStrategy
    from ...strategies.implementations.atr_based import ATRBasedStrategy
    from ...strategies.implementations.donchian_channel import DonchianChannelStrategy
    from ...trading import DEFAULT_RISK_CONFIG, create_risk_manager

    logger.info("🏗️ TradingOrchestrator依存性組み立て開始")

    try:
        # Discord通知システム初期化（ローカルファイル優先）
        import os
        from pathlib import Path

        # ローカル設定優先で読み込み
        webhook_path = Path("config/secrets/discord_webhook.txt")
        if webhook_path.exists():
            try:
                webhook_url = webhook_path.read_text().strip()
                logger.info(
                    f"📁 Discord Webhook URLをローカルファイルから読み込み（{len(webhook_url)}文字）"
                )
            except Exception as e:
                logger.error(f"⚠️ ローカルファイル読み込み失敗: {e}")
                webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
                logger.info("🌐 環境変数からフォールバック")
        else:
            webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
            logger.info("🌐 Discord Webhook URLを環境変数から読み込み")

        logger.info(f"🔍 Discord Webhook URL取得結果: 存在={webhook_url is not None}")
        if webhook_url:
            logger.info(f"🔗 Discord URL長: {len(webhook_url)} 文字")

        discord_manager = DiscordManager(webhook_url=webhook_url)
        logger.set_discord_manager(discord_manager)

        # Discord接続テストの実行
        if discord_manager.enabled:
            logger.info("🧪 Discord接続テスト実行中...")
            test_result = discord_manager.test_connection()
            if test_result:
                logger.info("✅ Discord接続テスト成功")
            else:
                logger.warning("⚠️ Discord接続テスト失敗 - 通知は無効化されています")
        else:
            logger.warning("⚠️ Discord通知は無効化されています - 環境変数を確認してください")

        # Phase 28-29最適化: データサービス
        bitbank_client = BitbankClient()
        data_service = DataPipeline(client=bitbank_client)

        # Phase 28-29最適化: 特徴量サービス（統合アダプター）
        # FeatureGenerator統合クラスを使用
        feature_service = FeatureGenerator()

        # Phase 51.5-A: 3戦略構成（ATRBased・DonchianChannel・ADXTrendStrength）
        strategy_service = StrategyManager()
        strategies = [
            ATRBasedStrategy(),
            DonchianChannelStrategy(),
            ADXTrendStrengthStrategy(),
        ]
        # 戦略を個別に登録
        for strategy in strategies:
            strategy_service.register_strategy(strategy, weight=1.0)

        # Phase 28-29最適化: MLサービス（根本問題解決版）
        from .ml_adapter import MLServiceAdapter

        ml_service = MLServiceAdapter(logger)
        logger.info(f"🤖 MLサービス初期化完了: {ml_service.get_model_info()['model_type']}")

        # Phase 28-29最適化: リスクサービス（BitbankAPI実残高取得対応・モード別分離対応）
        initial_balance = await _get_actual_balance(config, logger)
        risk_service = create_risk_manager(
            config=DEFAULT_RISK_CONFIG,
            initial_balance=initial_balance,
            mode=config.mode,
            bitbank_client=bitbank_client,  # Phase 49.15: 証拠金維持率API取得用
        )

        # Phase 28-29最適化: 実行サービス（risk_manager統合）
        # executor.pyから移行されたexecution機能をrisk_manager経由で使用
        from ...trading import create_risk_manager

        # Config統一化: 実行モードをconfig.modeから取得（モード設定一元化）
        execution_mode = config.mode
        logger.info(f"🎯 実行モードConfig取得: config.mode={execution_mode}")

        # Phase 28-29最適化: 取引実行サービス（新規実装）
        from ...trading.execution import ExecutionService

        execution_service = ExecutionService(mode=execution_mode, bitbank_client=bitbank_client)
        execution_service.update_balance(initial_balance)

        # Phase 38.1: PositionLimits/CooldownManager/BalanceMonitor注入（クールダウン機能復活）
        # Phase 42: PositionTracker注入追加（統合TP/SL対応）
        from ...trading.balance import BalanceMonitor
        from ...trading.execution import OrderStrategy, StopManager
        from ...trading.position import CooldownManager, PositionLimits, PositionTracker

        position_limits = PositionLimits()  # 引数なし・内部でget_logger()使用
        cooldown_manager = CooldownManager()  # 引数なし・内部でget_logger()使用
        position_limits.cooldown_manager = cooldown_manager
        balance_monitor = BalanceMonitor()  # 引数なし・内部でget_logger()使用
        order_strategy = OrderStrategy()  # Phase 38.6: 指値/成行注文戦略決定サービス
        stop_manager = StopManager()  # Phase 38.6: TP/SL注文配置サービス
        position_tracker = PositionTracker()  # Phase 42: 統合TP/SL用ポジション追跡

        execution_service.inject_services(
            position_limits=position_limits,
            balance_monitor=balance_monitor,
            order_strategy=order_strategy,
            stop_manager=stop_manager,
            position_tracker=position_tracker,
        )
        logger.info(
            "✅ ExecutionService依存サービス注入完了（PositionLimits・BalanceMonitor・OrderStrategy・StopManager・PositionTracker）"
        )

        # TradingOrchestrator組み立て
        orchestrator = TradingOrchestrator(
            config=config,
            logger=logger,
            data_service=data_service,
            feature_service=feature_service,
            strategy_service=strategy_service,
            ml_service=ml_service,
            risk_service=risk_service,
            execution_service=execution_service,
        )

        logger.info("🎉 TradingOrchestrator依存性組み立て完了")
        return orchestrator

    except (ImportError, ModuleNotFoundError) as e:
        # 依存モジュール読み込みエラー
        logger.error(f"❌ TradingOrchestrator依存モジュールエラー: {e}")
        raise CryptoBotError(f"TradingOrchestrator依存モジュール読み込みエラー: {e}")
    except (FileNotFoundError, OSError) as e:
        # 設定ファイル・I/Oエラー
        logger.error(f"❌ TradingOrchestrator設定ファイルエラー: {e}")
        raise FileIOError(f"TradingOrchestrator設定ファイル読み込みエラー: {e}")
    except (ValueError, KeyError) as e:
        # 設定値・初期化パラメータエラー
        logger.error(f"❌ TradingOrchestrator設定値エラー: {e}")
        raise CryptoBotError(f"TradingOrchestrator設定値エラー: {e}")
    except Exception as e:
        # 予期しないエラー
        logger.critical(f"❌ TradingOrchestrator組み立て予期しないエラー: {e}")
        raise CryptoBotError(f"TradingOrchestrator組み立てで予期しないエラー: {e}")


# BitbankAPI実残高取得関数
async def _get_actual_balance(config, logger) -> float:
    """残高取得（モード別一元管理対応・Phase 38.4完了版）"""

    # モード別初期残高をunified.yamlから取得（Phase 28-29最適化）
    def _get_mode_balance(mode: str) -> float:
        """mode_balancesから該当モードの初期残高を取得"""
        from ..config import load_config

        unified_config = load_config("config/core/unified.yaml")
        mode_balances = getattr(unified_config, "mode_balances", {})
        mode_balance_config = mode_balances.get(mode, {})
        return mode_balance_config.get("initial_balance", 10000.0)

    # Phase 35: ペーパー/バックテストモード時はAPI呼び出しをスキップ
    current_mode = getattr(config, "mode", "paper").lower()  # 大文字小文字統一
    if current_mode in ["paper", "backtest"]:
        mode_label = "ペーパー" if current_mode == "paper" else "バックテスト"
        logger.info(f"📝 {mode_label}モード: API呼び出しをスキップ、mode_balances残高使用")
        mode_balance = _get_mode_balance(current_mode)
        logger.info(f"💰 {mode_label}モード残高（mode_balances）: {mode_balance}円")
        return mode_balance

    # ライブモード時のみAPI呼び出し実行
    try:
        from ...core.exceptions import ExchangeAPIError
        from ...data.bitbank_client import BitbankClient

        logger.info("🏦 BitbankAPI実残高取得開始（ライブモード）")

        # BitbankClientで実際の残高を取得（Cloud Run環境デバッグ強化）
        bitbank_client = BitbankClient()
        logger.info("🔐 BitbankClient初期化完了、残高取得API呼び出し実行")

        balance_data = bitbank_client.fetch_balance()
        logger.info(f"📊 Bitbank残高データ受信: キー={list(balance_data.keys())}")

        # JPY残高（自由残高）を取得
        jpy_balance = balance_data.get("JPY", {}).get("free", 0.0)
        total_balance = balance_data.get("JPY", {}).get("total", 0.0)
        logger.info(f"💴 JPY残高詳細: 自由残高={jpy_balance}, 総残高={total_balance}")

        if jpy_balance <= 0:
            logger.warning(f"⚠️ Bitbank残高が0円以下（{jpy_balance}円）、mode_balances値使用")
            # Phase 28-29最適化: mode_balancesからフォールバック残高取得
            fallback_balance = _get_mode_balance(current_mode)
            logger.info(f"💰 フォールバック残高（mode_balances）: {fallback_balance}円")
            return fallback_balance

        logger.info(f"✅ Bitbank実残高取得成功: {jpy_balance:,.0f}円")
        return jpy_balance

    except ExchangeAPIError as e:
        logger.error(f"❌ BitbankAPI認証エラー: {e}")
        # Phase 28-29最適化: mode_balancesからフォールバック残高取得
        fallback_balance = _get_mode_balance(current_mode)
        logger.warning(f"💰 認証エラーのためmode_balances残高使用: {fallback_balance}円")
        return fallback_balance

    except Exception as e:
        logger.error(f"❌ 残高取得予期しないエラー: {e}")
        # Phase 28-29最適化: mode_balancesからフォールバック残高取得
        fallback_balance = _get_mode_balance(current_mode)
        logger.warning(f"💰 エラーのためmode_balances残高使用: {fallback_balance}円")
        return fallback_balance


# 内部アダプタークラス（Protocol準拠）
