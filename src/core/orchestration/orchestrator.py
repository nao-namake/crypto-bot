"""
統合取引システム制御 - TradingOrchestrator

Application Service Layer として、Phase 1-12の高レベル統合制御のみを担当・CI/CDワークフロー最適化・手動実行監視・段階的デプロイ対応。
具体的なビジネスロジックは各Phase層に委譲し、真のレイヤー分離を実現。

設計原則:
- Application Service Pattern: 高レベルフロー制御のみ
- 依存性注入: テスト容易性の確保
- 責任分離: 具体的実装は各Phaseに委譲
- エラーハンドリング階層化: 適切なレベルでの例外処理

メリット:
1. テスト容易性: 完全にモック可能な設計
2. 保守性: main.pyを変更せずに機能拡張可能
3. 可読性: システム全体のフローが明確
4. 拡張性: 新モードやPhaseの追加が容易.
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

from ...backtest.engine import BacktestEngine
from ...backtest.reporter import BacktestReporter
from ...trading.executor import ExecutionResult
from ...trading.risk_manager import TradeEvaluation

# from ...features.core_adapter import FeatureServiceAdapter  # Phase 18統合: feature_generator.pyに統合済み
from ..config import Config, get_threshold
from ..exceptions import (
    CryptoBotError,
    DataProcessingError,
    FileIOError,
    HealthCheckError,
    ModelLoadError,
)
from ..execution import LiveTradingRunner, PaperTradingRunner
from ..logger import CryptoBotLogger
from ..protocols import (
    DataServiceProtocol,
    ExecutionServiceProtocol,
    FeatureServiceProtocol,
    MLServiceProtocol,
    RiskServiceProtocol,
    StrategyServiceProtocol,
)

# BacktestReportWriter削除: reporter.pyに統合済み
from ..reporting.paper_trading_reporter import PaperTradingReporter
from ..services import (
    HealthChecker,
    SystemRecoveryService,
    TradingCycleManager,
    TradingLoggerService,
)

# Phase層インターフェース定義は protocols.py に移動


class TradingOrchestrator:
    """
    Application Service Layer - 統合取引システム制御

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
            execution_service: 注文実行サービス（Phase 7追加）.
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

        # Phase 18 統合システム: バックテストレポーター初期化
        self.backtest_reporter = BacktestReporter()
        self.paper_trading_reporter = PaperTradingReporter(logger)

        # Phase 18 統合システム: BacktestEngine直接管理
        self.backtest_engine = None  # バックテスト実行時に初期化
        self.paper_trading_runner = PaperTradingRunner(self, logger)
        self.live_trading_runner = LiveTradingRunner(self, logger)

        # Phase 14-B リファクタリング: サービス層初期化（分離済み）
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
            # Phase 18 統合システム: BacktestEngine直接実行
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
        取引サイクル実行（Phase 14-B リファクタリング）

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
        バックテストモード実行（Phase 18統合版）

        BacktestRunnerを除去し、BacktestEngineを直接使用
        """
        try:
            self.logger.info("📊 バックテストモード開始（Phase 18統合版）")

            # バックテストエンジン初期化
            await self._setup_backtest_engine()

            # バックテスト実行
            from datetime import datetime, timedelta

            from ..config import get_threshold

            # バックテスト期間設定（外部化）
            backtest_days = get_threshold("execution.backtest_period_days", 30)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=backtest_days)

            self.logger.info(
                f"📅 バックテスト期間: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}"
            )

            results = await self.backtest_engine.run_backtest(
                symbol="BTC/JPY",
                start_date=start_date,
                end_date=end_date,
                timeframes=["15m", "4h"],  # 設定通り15分足と4時間足
            )

            # 結果処理・レポート生成
            await self._process_backtest_results(results, start_date, end_date)

            self.logger.info("✅ バックテスト実行完了", discord_notify=True)

        except (FileNotFoundError, OSError) as e:
            # データファイル・I/Oエラー
            self.logger.error(f"❌ バックテストデータI/Oエラー: {e}", discord_notify=False)
            await self._save_backtest_error_report(str(e))
            raise DataProcessingError(f"バックテスト用データ読み込みエラー: {e}")
        except (ValueError, KeyError) as e:
            # データ形式・設定値エラー
            self.logger.error(f"❌ バックテストデータ形式エラー: {e}", discord_notify=False)
            await self._save_backtest_error_report(str(e))
            raise DataProcessingError(f"バックテストデータ処理エラー: {e}")
        except (ImportError, ModuleNotFoundError) as e:
            # モジュール・ライブラリエラー
            self.logger.error(f"❌ バックテストモジュールエラー: {e}", discord_notify=False)
            await self._save_backtest_error_report(str(e))
            raise HealthCheckError(f"バックテスト依存モジュールエラー: {e}")
        except Exception as e:
            # その他の予期しないエラー
            self.logger.error(f"❌ バックテスト予期しないエラー: {e}", discord_notify=True)
            await self._save_backtest_error_report(str(e))
            raise

    async def _setup_backtest_engine(self):
        """バックテストエンジン初期化"""
        try:
            # バックテストエンジン作成
            self.backtest_engine = BacktestEngine(
                initial_balance=1000000.0,  # 100万円（現実的なポジションサイズ）
                slippage_rate=0.0005,
                commission_rate=0.0012,
                max_position_ratio=0.05,
                risk_profile="balanced",
            )

            self.logger.info("🔧 BacktestEngine初期化完了")

        except Exception as e:
            self.logger.error(f"❌ バックテストエンジン初期化エラー: {e}")
            raise

    async def _process_backtest_results(self, results, start_date, end_date):
        """結果処理・レポート生成"""
        try:
            if not results:
                self.logger.warning("⚠️ バックテスト結果が空です")
                return

            # 結果レポート生成（Phase 18統合版）
            await self.backtest_reporter.generate_backtest_report(results, start_date, end_date)

        except Exception as e:
            self.logger.error(f"❌ バックテスト結果処理エラー: {e}")
            raise

    async def _save_backtest_error_report(self, error_message: str):
        """エラーレポート保存"""
        try:
            context = {
                "engine_initialized": self.backtest_engine is not None,
                "phase": "18_integrated_system",
            }

            await self.backtest_reporter.save_error_report(error_message, context)

        except Exception as e:
            self.logger.error(f"❌ バックテストエラーレポート保存失敗: {e}")


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
    from ...data.bitbank_client import BitbankClient
    from ...data.data_pipeline import DataPipeline

    # Phase 18統合: feature_generator.py統合により削除・EnsembleModel → MLServiceAdapter移行完了
    from ...monitoring.discord_notifier import DiscordManager
    from ...strategies.base.strategy_manager import StrategyManager
    from ...strategies.implementations.atr_based import ATRBasedStrategy
    from ...strategies.implementations.fibonacci_retracement import (
        FibonacciRetracementStrategy,
    )
    from ...strategies.implementations.mochipoy_alert import MochipoyAlertStrategy
    from ...strategies.implementations.multi_timeframe import MultiTimeframeStrategy
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
                logger.info(f"🌐 環境変数からフォールバック")
        else:
            webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
            logger.info(f"🌐 Discord Webhook URLを環境変数から読み込み")

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

        # Phase 2: データサービス
        bitbank_client = BitbankClient()
        data_service = DataPipeline(client=bitbank_client)

        # Phase 3: 特徴量サービス（統合アダプター）
        # Phase 18統合: FeatureGenerator統合クラスを使用
        feature_service = FeatureGenerator()

        # Phase 4: 戦略サービス
        strategy_service = StrategyManager()
        strategies = [
            ATRBasedStrategy(),
            MochipoyAlertStrategy(),
            MultiTimeframeStrategy(),
            FibonacciRetracementStrategy(),
        ]
        # 戦略を個別に登録
        for strategy in strategies:
            strategy_service.register_strategy(strategy, weight=1.0)

        # Phase 5: MLサービス（根本問題解決版）
        from .ml_adapter import MLServiceAdapter

        ml_service = MLServiceAdapter(logger)
        logger.info(f"🤖 MLサービス初期化完了: {ml_service.get_model_info()['model_type']}")

        # Phase 6: リスクサービス（Phase 16-B: thresholds.yamlから取得）
        from ..config import get_threshold

        initial_balance = get_threshold("trading.initial_balance_jpy", 10000.0)
        risk_service = create_risk_manager(
            config=DEFAULT_RISK_CONFIG, initial_balance=initial_balance
        )

        # Phase 7: 注文実行サービス
        from ...trading.executor import create_order_executor

        # Config統一化: 実行モードをconfig.modeから取得（モード設定一元化）
        execution_mode = config.mode
        logger.info(f"🎯 実行モードConfig取得: config.mode={execution_mode}")

        execution_service = create_order_executor(
            mode=execution_mode,
            initial_balance=initial_balance,  # Phase 16-B: thresholds.yamlから動的取得（1万円）
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


# 内部アダプタークラス（Protocol準拠）
# Phase 18統合: FeatureServiceAdapterは features/feature_generator.py に統合済み
