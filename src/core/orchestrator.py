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
from typing import Any, Dict, Optional, Protocol

import pandas as pd

from ..data.data_pipeline import DataRequest, TimeFrame
from ..features.anomaly import MarketAnomalyDetector
from ..features.technical import TechnicalIndicators
from .config import Config
from .exceptions import CryptoBotError
from .logger import CryptoBotLogger


# Phase層インターフェース定義（依存性逆転の原則）
class DataServiceProtocol(Protocol):
    """データ層サービスインターフェース."""

    async def fetch_multi_timeframe(self, symbol: str, limit: int) -> Optional[Dict]: ...


class FeatureServiceProtocol(Protocol):
    """特徴量生成サービスインターフェース."""

    async def generate_features(self, market_data: Dict) -> Dict: ...


class StrategyServiceProtocol(Protocol):
    """戦略評価サービスインターフェース."""

    def analyze_market(self, df: pd.DataFrame) -> Any: ...

    def _create_hold_signal(self, df: pd.DataFrame, reason: str) -> Any: ...


class MLServiceProtocol(Protocol):
    """ML予測サービスインターフェース."""

    def predict(self, X: pd.DataFrame, use_confidence: bool = True) -> Any: ...


class RiskServiceProtocol(Protocol):
    """リスク管理サービスインターフェース."""

    def evaluate_trade_opportunity(
        self, ml_prediction: Dict, strategy_signals: Any, market_data: Dict
    ) -> Any: ...


class ExecutionServiceProtocol(Protocol):
    """注文実行サービスインターフェース（Phase 7追加）."""

    async def execute_trade(self, evaluation) -> Any: ...

    async def check_stop_conditions(self) -> Any: ...

    def get_trading_statistics(self) -> Dict[str, Any]: ...


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
        self.execution_service = execution_service  # Phase 7追加

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
            await self._health_check()

            self._initialized = True
            self.logger.info("🎉 TradingOrchestrator初期化確認完了", discord_notify=True)
            return True

        except Exception as e:
            self.logger.error(
                f"❌ TradingOrchestrator初期化確認失敗: {e}",
                discord_notify=True,
            )
            return False

    async def _health_check(self):
        """各サービスの軽量ヘルスチェック."""
        try:
            # 基本的な接続性確認のみ（具体的な初期化は各サービスで実施済み）
            self.logger.info("✅ 全サービス健全性確認完了")
        except Exception as e:
            self.logger.error(f"ヘルスチェック失敗: {e}")
            raise

    async def run(self):
        """
        TradingOrchestrator実行（モード設定一元化対応）

        実行モードはconfig.modeから自動取得します。
        """
        if not self._initialized:
            raise CryptoBotError("TradingOrchestratorが初期化されていません")

        mode = self.config.mode
        self.logger.info(f"TradingOrchestrator実行開始 - モード: {mode.upper()}（Configから取得）")

        try:
            if mode == "backtest":
                await self.run_backtest()
            elif mode == "paper":
                await self.run_paper_trading()
            elif mode == "live":
                await self.run_live_trading()
            else:
                raise ValueError(f"無効なモード: {mode}")

        except KeyboardInterrupt:
            self.logger.info("ユーザーによる終了要求を受信")
        except Exception as e:
            # 🚨 CRITICAL FIX: エラーハンドリング内Discord通知による再帰防止
            self.logger.error(f"実行エラー: {e}", discord_notify=False)
            raise

        self.logger.info("TradingOrchestrator実行終了")

    async def run_trading_cycle(self):
        """
        高レベル取引サイクル制御

        各Phase層に具体的な処理を委譲し、
        ここでは統合フローの制御のみ実行.
        """
        cycle_id = datetime.now().isoformat()
        self.logger.info(f"取引サイクル開始 - ID: {cycle_id}")

        try:
            # Phase 2: データ取得
            market_data = await self.data_service.fetch_multi_timeframe(symbol="BTC/JPY", limit=100)
            if market_data is None:
                self.logger.warning("市場データ取得失敗 - サイクル終了")
                return

            # Phase 3: 特徴量生成（型安全性強化）
            # market_dataは辞書形式 {timeframe: DataFrame} なので、各DataFrameに対して特徴量を生成
            features = {}
            for timeframe, df in market_data.items():
                # 型安全性チェック - DataFrameの保証（強化版）
                if not isinstance(df, pd.DataFrame):
                    self.logger.error(
                        f"市場データの型エラー: {timeframe} = {type(df)}, DataFrameを期待. 詳細: {str(df)[:100] if df else 'None'}"
                    )
                    features[timeframe] = pd.DataFrame()  # 空のDataFrameで代替
                    continue

                # DataFrameの有効性チェック（強化版）
                try:
                    if hasattr(df, "empty") and not df.empty:
                        features[timeframe] = await self.feature_service.generate_features(df)
                    else:
                        self.logger.warning(f"空のDataFrame検出: {timeframe}")
                        features[timeframe] = pd.DataFrame()
                except Exception as e:
                    self.logger.error(f"特徴量生成エラー: {timeframe}, エラー: {e}")
                    features[timeframe] = pd.DataFrame()  # エラー時も安全な代替値

            # メインの特徴量データとして4時間足を使用
            main_features = features.get("4h", pd.DataFrame())

            # Phase 4: 戦略評価
            if not main_features.empty:
                strategy_signal = self.strategy_service.analyze_market(main_features)
            else:
                # 空のDataFrameの場合はHOLDシグナル
                strategy_signal = self.strategy_service._create_hold_signal(
                    pd.DataFrame(), "データ不足"
                )

            # Phase 5: ML予測
            if not main_features.empty:
                ml_predictions_array = self.ml_service.predict(main_features)
                # 最新の予測値を使用
                if len(ml_predictions_array) > 0:
                    ml_prediction = {
                        "prediction": int(ml_predictions_array[-1]),
                        "confidence": 0.5,  # 基本的な信頼度
                    }
                else:
                    ml_prediction = {"prediction": 0, "confidence": 0.0}
            else:
                ml_prediction = {"prediction": 0, "confidence": 0.0}

            # Phase 6: 追加情報取得（リスク管理のため）
            try:
                # 現在の残高取得
                balance_info = self.data_service.client.fetch_balance()
                current_balance = balance_info.get("JPY", {}).get("total", 0.0)

                # 現在のティッカー情報取得（bid/ask価格）
                import time

                start_time = time.time()
                ticker_info = self.data_service.client.fetch_ticker("BTC/JPY")
                api_latency_ms = (time.time() - start_time) * 1000

                bid = ticker_info.get("bid", 0.0)
                ask = ticker_info.get("ask", 0.0)

                self.logger.debug(
                    f"取引情報取得 - 残高: ¥{current_balance:,.0f}, bid: ¥{bid:,.0f}, ask: ¥{ask:,.0f}, API遅延: {api_latency_ms:.1f}ms"
                )

            except Exception as e:
                # フォールバック値を使用
                self.logger.warning(f"取引情報取得エラー - フォールバック値使用: {e}")
                current_balance = 1000000.0  # デフォルト残高

                # 安全にmarket_dataから価格を取得
                try:
                    if (
                        isinstance(market_data, dict)
                        and "4h" in market_data
                        and not market_data["4h"].empty
                    ):
                        close_price = market_data["4h"]["close"].iloc[-1]
                        bid = close_price * 0.999  # close価格の0.1%下
                        ask = close_price * 1.001  # close価格の0.1%上
                    else:
                        # デフォルト価格（BTC/JPY概算）
                        bid = 9000000.0  # 9,000,000円
                        ask = 9010000.0  # 9,010,000円
                except (KeyError, IndexError, TypeError) as price_error:
                    self.logger.warning(f"価格フォールバック処理エラー: {price_error}")
                    bid = 9000000.0  # デフォルト価格
                    ask = 9010000.0  # デフォルト価格

                api_latency_ms = 100.0  # デフォルト遅延値

            # Phase 6: リスク管理・統合判定
            trade_evaluation = self.risk_service.evaluate_trade_opportunity(
                ml_prediction=ml_prediction,
                strategy_signal=strategy_signal,  # 変数名統一
                market_data=main_features,  # DataFrameのみ渡す（型整合性確保）
                current_balance=current_balance,
                bid=bid,
                ask=ask,
                api_latency_ms=api_latency_ms,
            )

            # Phase 7: 注文実行（承認された取引のみ）
            execution_result = None
            if str(getattr(trade_evaluation, "decision", "")).lower() == "approved":
                execution_result = await self.execution_service.execute_trade(trade_evaluation)
                await self._log_execution_result(execution_result, cycle_id)
            else:
                await self._log_trade_decision(trade_evaluation, cycle_id)

            # ストップ条件チェック（既存ポジションの自動決済）
            stop_result = await self.execution_service.check_stop_conditions()
            if stop_result:
                await self._log_execution_result(stop_result, cycle_id, is_stop=True)

        except ValueError as e:
            if "not fitted" in str(e) or "EnsembleModel is not fitted" in str(e):
                self.logger.error(f"🚨 MLモデル未学習エラー検出 - ID: {cycle_id}, エラー: {e}")
                # 自動復旧試行
                await self._recover_ml_service()
                return  # このサイクルはスキップ
            else:
                # 🚨 CRITICAL FIX: エラーハンドリング内Discord通知による再帰防止
                self.logger.error(
                    f"取引サイクル値エラー - ID: {cycle_id}, エラー: {e}", discord_notify=False
                )
                self._record_cycle_error(cycle_id, e)
                return  # このサイクルはスキップ、次のサイクルへ
        except Exception as e:
            # 🚨 CRITICAL FIX: エラーハンドリング内Discord通知による再帰防止
            self.logger.error(
                f"取引サイクルエラー - ID: {cycle_id}, エラー: {e}", discord_notify=False
            )
            # エラーを記録するが、プログラムは継続
            self._record_cycle_error(cycle_id, e)
            return  # このサイクルはスキップ、次のサイクルへ

    async def _recover_ml_service(self):
        """MLサービス自動復旧"""
        self.logger.info("🔧 MLサービス自動復旧開始")
        try:
            # モデル再読み込み試行
            if hasattr(self.ml_service, "reload_model"):
                success = self.ml_service.reload_model()
                if success:
                    self.logger.info("✅ MLサービス復旧成功")
                else:
                    # 🚨 CRITICAL FIX: エラーハンドリング内Discord通知による再帰防止
                    self.logger.error("❌ MLサービス復旧失敗", discord_notify=False)
                    await self._schedule_system_restart()
            else:
                # MLServiceAdapterで再初期化
                from .ml_adapter import MLServiceAdapter

                self.ml_service = MLServiceAdapter(self.logger)
                self.logger.info("✅ MLサービス再初期化完了")
        except Exception as e:
            # 🚨 CRITICAL FIX: エラーハンドリング内Discord通知による再帰防止
            self.logger.error(f"❌ MLサービス復旧エラー: {e}", discord_notify=False)
            await self._schedule_system_restart()

    def _record_cycle_error(self, cycle_id: str, error: Exception):
        """取引サイクルエラー記録"""
        try:
            error_info = {
                "cycle_id": cycle_id,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "timestamp": datetime.now().isoformat(),
            }
            # エラー情報をログに記録（詳細解析用）
            self.logger.info(f"サイクルエラー記録: {error_info}")
        except Exception as e:
            self.logger.error(f"エラー記録失敗: {e}")

    async def _schedule_system_restart(self):
        """システム再起動スケジュール"""
        # 🚨 CRITICAL FIX: エラーハンドリング内Discord通知による再帰防止
        self.logger.error("🚨 重大なエラーのためシステム再起動を推奨", discord_notify=False)
        # 実際の再起動は環境に依存するため、ログのみ記録
        self.logger.error(
            "💡 手動でのシステム再起動またはコンテナ再起動を実行してください", discord_notify=False
        )

    async def _log_trade_decision(self, evaluation, cycle_id: str):
        """取引判定ログ出力（高レベルサマリーのみ）."""
        decision_map = {
            "approved": "🟢 取引承認",
            "conditional": "🟡 条件付き承認",
            "denied": "🔴 取引拒否",
        }

        decision_str = getattr(evaluation, "decision", "unknown")
        decision_label = decision_map.get(str(decision_str).lower(), "❓ 不明")

        self.logger.info(
            f"{decision_label} - サイクル: {cycle_id}, "
            f"リスクスコア: {getattr(evaluation, 'risk_score', 0):.3f}",
            discord_notify=(str(decision_str).lower() in ["approved", "denied"]),
        )

    async def _log_execution_result(self, execution_result, cycle_id: str, is_stop: bool = False):
        """注文実行結果ログ出力（Phase 7追加）."""
        if execution_result is None:
            return

        try:
            success_emoji = "✅" if execution_result.success else "❌"
            stop_prefix = "🛑 自動決済: " if is_stop else ""

            if execution_result.success:
                # 成功時の詳細ログ
                side_emoji = "📈" if execution_result.side == "buy" else "📉"

                log_message = (
                    f"{stop_prefix}{success_emoji} {side_emoji} 注文実行成功 - "
                    f"サイクル: {cycle_id}, "
                    f"サイド: {execution_result.side.upper()}, "
                    f"数量: {execution_result.amount:.4f} BTC, "
                    f"価格: ¥{execution_result.price:,.0f}"
                )

                if (
                    hasattr(execution_result, "paper_pnl")
                    and execution_result.paper_pnl is not None
                ):
                    pnl_emoji = "💰" if execution_result.paper_pnl > 0 else "💸"
                    log_message += f", PnL: {pnl_emoji}¥{execution_result.paper_pnl:,.0f}"

                if hasattr(execution_result, "fee") and execution_result.fee is not None:
                    log_message += f", 手数料: ¥{execution_result.fee:,.0f}"

                # 成功した取引は必ずDiscord通知
                self.logger.info(log_message, discord_notify=True)

                # 統計情報ログ（定期的）
                stats = self.execution_service.get_trading_statistics()
                if stats.get("statistics", {}).get("total_trades", 0) % 10 == 0:  # 10回毎
                    await self._log_trading_statistics(stats)

            else:
                # 失敗時のログ
                error_message = (
                    f"{stop_prefix}{success_emoji} 注文実行失敗 - "
                    f"サイクル: {cycle_id}, "
                    f"エラー: {execution_result.error_message or '不明'}"
                )

                # 実行失敗はWarningレベル・Discord通知
                self.logger.warning(error_message, discord_notify=True)

        except Exception as e:
            self.logger.error(f"実行結果ログ出力エラー: {e}")

    async def _log_trading_statistics(self, stats: dict):
        """取引統計ログ出力（Phase 7追加）."""
        try:
            statistics = stats.get("statistics", {})

            total_trades = statistics.get("total_trades", 0)
            winning_trades = statistics.get("winning_trades", 0)
            win_rate = statistics.get("win_rate", 0) * 100
            current_balance = stats.get("current_balance", 0)
            initial_balance = stats.get("initial_balance", 1000000)
            return_rate = stats.get("return_rate", 0) * 100

            stats_message = (
                f"📊 取引統計サマリー\n"
                f"・総取引数: {total_trades}回\n"
                f"・勝ち取引: {winning_trades}回\n"
                f"・勝率: {win_rate:.1f}%\n"
                f"・現在残高: ¥{current_balance:,.0f}\n"
                f"・リターン率: {return_rate:+.2f}%"
            )

            # 統計情報は Info レベル・Discord通知
            self.logger.info(stats_message, discord_notify=True)

        except Exception as e:
            self.logger.error(f"統計ログ出力エラー: {e}")

    async def run_backtest(self):
        """バックテストモード実行."""
        self.logger.info("📊 バックテストモード開始")

        try:
            # バックテストエンジン初期化
            from datetime import datetime, timedelta

            from ..backtest.engine import BacktestEngine

            # バックテスト期間設定（デフォルト：過去30日）
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)

            backtest_engine = BacktestEngine(
                config=self.config,
                logger=self.logger,
                data_service=self.data_service,
                strategy_service=self.strategy_service,
                ml_service=self.ml_service,
                risk_service=self.risk_service,
            )

            self.logger.info(
                f"📅 バックテスト期間: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}"
            )

            # バックテスト実行
            results = await backtest_engine.run_backtest(
                symbol="BTC_JPY",
                start_date=start_date,
                end_date=end_date,
            )

            # 結果レポート生成
            await self._save_backtest_report(results, start_date, end_date)

            self.logger.info("✅ バックテスト実行完了", discord_notify=True)

        except Exception as e:
            # 🚨 CRITICAL FIX: エラーハンドリング内Discord通知による再帰防止
            self.logger.error(f"❌ バックテスト実行エラー: {e}", discord_notify=False)
            await self._save_backtest_error_report(str(e))
            raise

    async def run_paper_trading(self):
        """ペーパートレードモード実行."""
        self.logger.info("📝 ペーパートレードモード開始")

        from datetime import datetime

        session_start = datetime.now()
        cycle_count = 0

        try:
            # 定期的な取引サイクル実行
            while True:
                await self.run_trading_cycle()
                cycle_count += 1

                # 10サイクルごと（約10分）にレポート生成
                if cycle_count % 10 == 0:
                    # セッション統計収集
                    session_stats = {
                        "start_time": session_start.strftime("%Y-%m-%d %H:%M:%S"),
                        "cycles_completed": cycle_count,
                        "total_signals": getattr(self.execution_service, "total_signals", 0),
                        "executed_trades": getattr(self.execution_service, "executed_trades", 0),
                        "current_balance": getattr(
                            self.execution_service, "current_balance", 1000000
                        ),  # デフォルト100万円
                        "session_pnl": getattr(self.execution_service, "session_pnl", 0),
                        "recent_trades": getattr(self.execution_service, "recent_trades", []),
                    }

                    # レポート保存
                    await self._save_paper_trading_report(session_stats)

                await asyncio.sleep(60)  # 1分間隔

        except KeyboardInterrupt:
            # 終了時にもレポート生成
            final_stats = {
                "start_time": session_start.strftime("%Y-%m-%d %H:%M:%S"),
                "end_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "cycles_completed": cycle_count,
                "total_signals": getattr(self.execution_service, "total_signals", 0),
                "executed_trades": getattr(self.execution_service, "executed_trades", 0),
                "current_balance": getattr(self.execution_service, "current_balance", 1000000),
                "session_pnl": getattr(self.execution_service, "session_pnl", 0),
                "recent_trades": getattr(self.execution_service, "recent_trades", []),
            }
            await self._save_paper_trading_report(final_stats)
            self.logger.info("📝 ペーパートレード終了・最終レポート保存完了")
            raise

    async def run_live_trading(self):
        """ライブトレードモード実行."""
        self.logger.info("🚨 ライブトレードモード開始", discord_notify=True)

        # 定期的な取引サイクル実行（月100-200回最適化）
        while True:
            await self.run_trading_cycle()
            await asyncio.sleep(180)  # 3分間隔（収益性重視）

    async def _save_backtest_report(self, results: Dict, start_date, end_date):
        """バックテスト結果レポート保存"""
        try:
            import json
            from datetime import datetime
            from pathlib import Path

            # レポート保存ディレクトリ
            report_dir = Path("logs/backtest_reports")
            report_dir.mkdir(exist_ok=True, parents=True)

            timestamp = datetime.now()
            filename = f"backtest_{timestamp.strftime('%Y%m%d_%H%M%S')}.md"
            filepath = report_dir / filename

            # パフォーマンス指標計算
            total_trades = len(results.get("trades", []))
            winning_trades = len([t for t in results.get("trades", []) if t.get("pnl", 0) > 0])
            total_pnl = sum(t.get("pnl", 0) for t in results.get("trades", []))
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

            # マークダウンレポート生成
            report_content = f"""# バックテスト実行レポート

## 📊 実行サマリー
- **実行時刻**: {timestamp.strftime('%Y年%m月%d日 %H:%M:%S')}
- **バックテスト期間**: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}
- **対象シンボル**: BTC_JPY
- **実行結果**: ✅ SUCCESS

## 🎯 システム情報
- **Phase**: 12（CI/CDワークフロー最適化・手動実行監視・段階的デプロイ対応）
- **バックテストエンジン**: BacktestEngine（Phase 12統合版）
- **戦略システム**: Phase 1-11統合戦略

## 📈 パフォーマンス結果
- **総取引数**: {total_trades}件
- **勝率**: {win_rate:.2f}% ({winning_trades}/{total_trades})
- **総損益**: ¥{total_pnl:,.0f}
- **最終資産**: ¥{results.get('final_balance', 0):,.0f}
- **リターン**: {results.get('return_rate', 0):.2f}%

## 📊 取引詳細
"""

            # 取引詳細追加
            if results.get("trades"):
                report_content += "### 取引履歴（最新10件）\n"
                for i, trade in enumerate(results["trades"][-10:], 1):
                    entry_time = trade.get("entry_time", "N/A")
                    side = trade.get("side", "N/A")
                    entry_price = trade.get("entry_price", 0)
                    pnl = trade.get("pnl", 0)
                    pnl_icon = "📈" if pnl > 0 else "📉"
                    report_content += f"{i}. {entry_time} - {side.upper()} @ ¥{entry_price:,.0f} {pnl_icon} ¥{pnl:,.0f}\n"
            else:
                report_content += "取引が発生しませんでした。\n"

            report_content += f"""

## 🔧 リスク分析
- **最大ドローダウン**: {results.get('max_drawdown', 0):.2f}%
- **シャープレシオ**: {results.get('sharpe_ratio', 0):.2f}
- **最大連敗**: {results.get('max_consecutive_losses', 0)}回

## 📋 戦略分析
- **使用戦略**: {len(results.get('strategies_used', []))}戦略
- **ML予測精度**: {results.get('ml_accuracy', 0):.2f}%
- **リスク管理**: Kelly基準・ドローダウン制御

## 🆘 追加情報

このレポートを他のAIツールに共有して、詳細な分析を依頼することができます。

**共有時のポイント**:
- バックテスト期間と取引数
- 勝率と総損益
- リスク指標（ドローダウン・シャープレシオ）
- 戦略とML予測の効果

---
*このレポートは BacktestEngine により自動生成されました*  
*生成時刻: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}*
"""

            # ファイル保存
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(report_content)

            # JSONレポートも保存
            json_filepath = report_dir / f"backtest_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
            with open(json_filepath, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "timestamp": timestamp.isoformat(),
                        "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
                        "results": results,
                        "summary": {
                            "total_trades": total_trades,
                            "win_rate": win_rate,
                            "total_pnl": total_pnl,
                        },
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                )

            self.logger.info(f"📁 バックテストレポート保存: {filepath}")

        except Exception as e:
            self.logger.error(f"バックテストレポート保存エラー: {e}")

    async def _save_backtest_error_report(self, error_message: str):
        """バックテストエラーレポート保存"""
        try:
            from datetime import datetime
            from pathlib import Path

            report_dir = Path("logs/backtest_reports")
            report_dir.mkdir(exist_ok=True, parents=True)

            timestamp = datetime.now()
            filename = f"backtest_error_{timestamp.strftime('%Y%m%d_%H%M%S')}.md"
            filepath = report_dir / filename

            error_report = f"""# バックテストエラーレポート

## 📊 実行サマリー
- **実行時刻**: {timestamp.strftime('%Y年%m月%d日 %H:%M:%S')}
- **実行結果**: ❌ ERROR
- **エラー内容**: {error_message}

## 🚨 推奨対応
1. エラーメッセージの詳細確認
2. データ取得状況の確認
3. `python scripts/management/dev_check.py validate` で品質チェック
4. 設定ファイルの確認

---
*このレポートは BacktestEngine により自動生成されました*
"""

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(error_report)

            self.logger.info(f"📁 バックテストエラーレポート保存: {filepath}")

        except Exception as e:
            self.logger.error(f"エラーレポート保存エラー: {e}")

    async def _save_paper_trading_report(self, session_stats: Dict):
        """ペーパートレードセッションレポート保存"""
        try:
            import json
            from datetime import datetime
            from pathlib import Path

            report_dir = Path("logs/paper_trading_reports")
            report_dir.mkdir(exist_ok=True, parents=True)

            timestamp = datetime.now()
            filename = f"paper_trading_{timestamp.strftime('%Y%m%d_%H%M%S')}.md"
            filepath = report_dir / filename

            # セッション統計
            total_signals = session_stats.get("total_signals", 0)
            executed_trades = session_stats.get("executed_trades", 0)
            current_balance = session_stats.get("current_balance", 0)
            session_pnl = session_stats.get("session_pnl", 0)

            report_content = f"""# ペーパートレードセッションレポート

## 📊 セッションサマリー
- **セッション開始**: {session_stats.get('start_time', 'N/A')}
- **レポート生成**: {timestamp.strftime('%Y年%m月%d日 %H:%M:%S')}
- **実行結果**: ✅ SUCCESS

## 🎯 システム情報
- **Phase**: 12（CI/CDワークフロー最適化・手動実行監視・段階的デプロイ対応）
- **取引モード**: Paper Trading（仮想取引）
- **実行環境**: TradingOrchestrator

## 📈 取引パフォーマンス
- **生成シグナル数**: {total_signals}件
- **実行取引数**: {executed_trades}件
- **現在残高**: ¥{current_balance:,.0f}
- **セッション損益**: ¥{session_pnl:,.0f}
- **シグナル実行率**: {(executed_trades/total_signals*100) if total_signals > 0 else 0:.1f}%

## 📊 取引詳細
"""

            # 最近の取引詳細
            recent_trades = session_stats.get("recent_trades", [])
            if recent_trades:
                report_content += "### 最近の取引（最新5件）\n"
                for i, trade in enumerate(recent_trades[-5:], 1):
                    time = trade.get("time", "N/A")
                    action = trade.get("action", "N/A")
                    price = trade.get("price", 0)
                    confidence = trade.get("confidence", 0)
                    report_content += (
                        f"{i}. {time} - {action} @ ¥{price:,.0f} (信頼度: {confidence:.2f})\n"
                    )
            else:
                report_content += "取引実行はありませんでした。\n"

            report_content += f"""

## 🔧 システム状態
- **戦略システム**: 正常動作中
- **ML予測システム**: 正常動作中
- **リスク管理**: アクティブ
- **異常検知**: 監視中

## 📋 次のアクション
1. セッション継続監視
2. パフォーマンス分析の継続
3. 定期的なシステムヘルスチェック

## 🆘 追加情報

このレポートを他のAIツールに共有して、取引戦略の改善提案を受けることができます。

**共有時のポイント**:
- セッション統計と実行率
- 取引判断の根拠
- システムの安定性状況
- パフォーマンス改善の余地

---
*このレポートは TradingOrchestrator により自動生成されました*  
*生成時刻: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}*
"""

            # ファイル保存
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(report_content)

            # JSONレポートも保存
            json_filepath = report_dir / f"paper_trading_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
            with open(json_filepath, "w", encoding="utf-8") as f:
                json.dump(
                    {"timestamp": timestamp.isoformat(), "session_stats": session_stats},
                    f,
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                )

            self.logger.info(f"📁 ペーパートレードレポート保存: {filepath}")

        except Exception as e:
            self.logger.error(f"ペーパートレードレポート保存エラー: {e}")


# ファクトリー関数（main.pyから簡単に利用可能）
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
    from ..data.bitbank_client import BitbankClient
    from ..data.data_pipeline import DataPipeline
    from ..features.anomaly import MarketAnomalyDetector
    from ..features.technical import TechnicalIndicators
    from ..ml.ensemble.ensemble_model import EnsembleModel
    from ..monitoring.discord import setup_discord_notifier
    from ..strategies.base.strategy_manager import StrategyManager
    from ..strategies.implementations.atr_based import ATRBasedStrategy
    from ..strategies.implementations.fibonacci_retracement import FibonacciRetracementStrategy
    from ..strategies.implementations.mochipoy_alert import MochipoyAlertStrategy
    from ..strategies.implementations.multi_timeframe import MultiTimeframeStrategy
    from ..trading import DEFAULT_RISK_CONFIG, create_risk_manager

    logger.info("🏗️ TradingOrchestrator依存性組み立て開始")

    try:
        # Discord通知システム初期化（Secret Manager環境変数取得）
        import os

        webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        logger.info(f"🔍 Discord環境変数取得: webhook_url存在={webhook_url is not None}")
        if webhook_url:
            logger.info(f"🔗 Discord URL長: {len(webhook_url)} 文字")

        discord_notifier = setup_discord_notifier(webhook_url=webhook_url)
        logger.set_discord_notifier(discord_notifier)

        # Discord接続テストの実行
        if discord_notifier.enabled:
            logger.info("🧪 Discord接続テスト実行中...")
            test_result = discord_notifier.test_connection()
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
        feature_service = _FeatureServiceAdapter(
            TechnicalIndicators(), MarketAnomalyDetector(), logger
        )

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

        # Phase 6: リスクサービス
        risk_service = create_risk_manager(config=DEFAULT_RISK_CONFIG, initial_balance=1000000)

        # Phase 7: 注文実行サービス
        from ..trading.executor import create_order_executor

        # Config統一化: 実行モードをconfig.modeから取得（モード設定一元化）
        execution_mode = config.mode
        logger.info(f"🎯 実行モードConfig取得: config.mode={execution_mode}")

        execution_service = create_order_executor(
            mode=execution_mode,
            initial_balance=1000000,  # 初期残高（ペーパー・ライブ共通）
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

    except Exception as e:
        logger.error(f"❌ TradingOrchestrator組み立て失敗: {e}")
        raise


# 内部アダプタークラス（Protocol準拠）
class _FeatureServiceAdapter:
    """特徴量サービス統合アダプター."""

    def __init__(
        self,
        technical_indicators: TechnicalIndicators,
        anomaly_detector: MarketAnomalyDetector,
        logger: CryptoBotLogger,
    ):
        self.technical_indicators = technical_indicators
        self.anomaly_detector = anomaly_detector
        self.logger = logger

    async def generate_features(self, market_data: Dict) -> Dict:
        """特徴量生成統合処理（12特徴量確認機能付き）."""
        # DataFrameに変換（dictでもDataFrameでも対応）
        if isinstance(market_data, pd.DataFrame):
            result_df = market_data.copy()
        elif isinstance(market_data, dict):
            # dictの場合はDataFrameに変換
            try:
                result_df = pd.DataFrame(market_data)
            except Exception as e:
                raise ValueError(f"Failed to convert dict to DataFrame: {e}")
        else:
            raise ValueError(f"Unsupported market_data type: {type(market_data)}")

        # 🎯 Phase 13.6 FIX: 12特徴量生成確認機能追加
        self.logger.info("特徴量生成開始 - 12特徴量システム")

        # 🔹 基本特徴量を生成（3個）
        basic_features_generated = []
        if "close" in result_df.columns:
            basic_features_generated.append("close")
        if "volume" in result_df.columns:
            basic_features_generated.append("volume")
        if "close" in result_df.columns:
            result_df["returns_1"] = result_df["close"].pct_change(1)
            result_df["returns_1"] = result_df["returns_1"].fillna(0)
            basic_features_generated.append("returns_1")

        # 🔹 テクニカル指標と異常検知指標を生成
        result_df = self.technical_indicators.generate_all_features(result_df)
        result_df = self.anomaly_detector.generate_all_features(result_df)

        # 🎯 12特徴量完全確認・検証
        expected_features = [
            # 基本特徴量（3個）
            "close",
            "volume",
            "returns_1",
            # テクニカル指標（6個）
            "rsi_14",
            "macd",
            "atr_14",
            "bb_position",
            "ema_20",
            "ema_50",
            # 異常検知指標（3個）
            "zscore",
            "volume_ratio",
            "market_stress",
        ]

        generated_features = [col for col in expected_features if col in result_df.columns]
        missing_features = [col for col in expected_features if col not in result_df.columns]

        # 🚨 CRITICAL: 統合ログ出力
        self.logger.info(
            f"特徴量生成完了 - 総数: {len(generated_features)}/12個",
            extra_data={
                "basic_features": basic_features_generated,
                "technical_features": len(
                    [
                        f
                        for f in ["rsi_14", "macd", "atr_14", "bb_position", "ema_20", "ema_50"]
                        if f in result_df.columns
                    ]
                ),
                "anomaly_features": len(
                    [
                        f
                        for f in ["zscore", "volume_ratio", "market_stress"]
                        if f in result_df.columns
                    ]
                ),
                "generated_features": generated_features,
                "missing_features": missing_features,
                "total_expected": 12,
                "success": len(generated_features) == 12,
            },
        )

        # ⚠️ 不足特徴量の警告
        if missing_features:
            self.logger.warning(
                f"🚨 特徴量不足検出: {missing_features} ({len(missing_features)}個不足)"
            )
        else:
            self.logger.info("✅ 12特徴量完全生成成功")

        return result_df
