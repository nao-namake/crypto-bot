"""
取引サイクルマネージャー - Phase 22 リファクタリング

orchestrator.pyから分離した取引サイクル実行機能。
データ取得→特徴量生成→戦略評価→ML予測→リスク管理→注文実行の
フロー全体を担当。
"""

import time
from datetime import datetime

import pandas as pd

# Silent Failure修正: RiskDecision Enum は動的インポートで回避
from ..config import get_threshold
from ..exceptions import CryptoBotError, ModelLoadError
from ..logger import CryptoBotLogger


class TradingCycleManager:
    """取引サイクル実行管理クラス"""

    def __init__(self, orchestrator_ref, logger: CryptoBotLogger):
        """
        取引サイクルマネージャー初期化

        Args:
            orchestrator_ref: TradingOrchestratorへの参照
            logger: ログシステム
        """
        self.orchestrator = orchestrator_ref
        self.logger = logger

    async def execute_trading_cycle(self):
        """
        取引サイクル実行

        高レベル取引サイクル制御。各Phase層に具体的な処理を委譲し、
        ここでは統合フローの制御のみ実行。
        """
        cycle_id = datetime.now().isoformat()
        self.logger.info(f"取引サイクル開始 - ID: {cycle_id}")

        try:
            # Phase 2: データ取得
            market_data = await self._fetch_market_data()
            if market_data is None:
                self.logger.warning("市場データ取得失敗 - サイクル終了")
                return

            # Phase 3: 特徴量生成
            features, main_features = await self._generate_features(market_data)

            # Phase 4: 戦略評価
            strategy_signal = await self._evaluate_strategy(main_features)

            # Phase 5: ML予測
            ml_prediction = await self._get_ml_prediction(main_features)

            # Phase 6: 追加情報取得（リスク管理のため）
            trading_info = await self._fetch_trading_info(market_data)

            # Phase 7: リスク管理・統合判定
            trade_evaluation = await self._evaluate_risk(
                ml_prediction, strategy_signal, main_features, trading_info
            )

            # Phase 8: 注文実行
            await self._execute_approved_trades(trade_evaluation, cycle_id)
            await self._check_stop_conditions(cycle_id)

        except ValueError as e:
            await self._handle_value_error(e, cycle_id)
        except ModelLoadError as e:
            await self._handle_model_error(e, cycle_id)
        except (ConnectionError, TimeoutError) as e:
            await self._handle_connection_error(e, cycle_id)
        except (AttributeError, TypeError) as e:
            await self._handle_attribute_error(e, cycle_id)
        except (RuntimeError, SystemError) as e:
            await self._handle_system_error(e, cycle_id)
        except Exception as e:
            await self._handle_unexpected_error(e, cycle_id)

    async def _fetch_market_data(self):
        """Phase 2: データ取得"""
        try:
            return await self.orchestrator.data_service.fetch_multi_timeframe(
                symbol="BTC/JPY", limit=100
            )
        except Exception as e:
            self.logger.error(f"市場データ取得エラー: {e}")
            return None

    async def _generate_features(self, market_data):
        """Phase 3: 特徴量生成（型安全性強化）"""
        features = {}

        for timeframe, df in market_data.items():
            try:
                # 型安全性チェック - DataFrameの保証（強化版）
                if not isinstance(df, pd.DataFrame):
                    self.logger.error(
                        f"市場データの型エラー: {timeframe} = {type(df)}, DataFrameを期待. "
                        f"詳細: {str(df)[:100] if df else 'None'}"
                    )
                    features[timeframe] = pd.DataFrame()  # 空のDataFrameで代替
                    continue

                # DataFrameの有効性チェック（強化版）
                if hasattr(df, "empty") and not df.empty:
                    features[timeframe] = await self.orchestrator.feature_service.generate_features(
                        df
                    )
                else:
                    self.logger.warning(f"空のDataFrame検出: {timeframe}")
                    features[timeframe] = pd.DataFrame()

            except (KeyError, ValueError) as e:
                self.logger.error(f"特徴量データエラー: {timeframe}, エラー: {e}")
                features[timeframe] = pd.DataFrame()
            except AttributeError as e:
                self.logger.error(f"特徴量メソッドエラー: {timeframe}, エラー: {e}")
                features[timeframe] = pd.DataFrame()
            except (ImportError, ModuleNotFoundError) as e:
                self.logger.error(f"特徴量生成ライブラリエラー: {timeframe}, エラー: {e}")
                features[timeframe] = pd.DataFrame()
            except Exception as e:
                self.logger.critical(f"特徴量生成予期しないエラー: {timeframe}, エラー: {e}")
                features[timeframe] = pd.DataFrame()

        # 設定からメインタイムフレームを取得
        from ..config import get_data_config

        main_timeframe = get_data_config("timeframes", ["4h", "15m"])[0]  # 最初の要素がメイン
        main_features = features.get(main_timeframe, pd.DataFrame())
        return features, main_features

    async def _evaluate_strategy(self, main_features):
        """Phase 4: 戦略評価"""
        try:
            if not main_features.empty:
                return self.orchestrator.strategy_service.analyze_market(main_features)
            else:
                # 空のDataFrameの場合はHOLDシグナル
                return self.orchestrator.strategy_service._create_hold_signal(
                    pd.DataFrame(), "データ不足"
                )
        except Exception as e:
            self.logger.error(f"戦略評価エラー: {e}")
            return self.orchestrator.strategy_service._create_hold_signal(
                pd.DataFrame(), f"戦略評価エラー: {e}"
            )

    async def _get_ml_prediction(self, main_features):
        """Phase 5: ML予測"""
        try:
            if not main_features.empty:
                # Phase 22: 15特徴量のみを選択してML予測（特徴量数不一致修正）
                from ...core.config.feature_manager import get_feature_names

                features_to_use = get_feature_names()

                # 利用可能な特徴量のみを選択
                available_features = [
                    col for col in features_to_use if col in main_features.columns
                ]
                if len(available_features) != len(features_to_use):
                    self.logger.warning(
                        f"特徴量不足検出: {len(available_features)}/{len(features_to_use)}個"
                    )

                main_features_for_ml = main_features[available_features]
                self.logger.debug(f"ML予測用特徴量選択完了: {main_features_for_ml.shape}")

                # ML予測と信頼度を同時取得
                self.logger.info("🤖 ML予測実行開始: ProductionEnsemble予測中")
                ml_predictions_array = self.orchestrator.ml_service.predict(main_features_for_ml)
                ml_probabilities = self.orchestrator.ml_service.predict_proba(main_features_for_ml)

                # 最新の予測値と実際の信頼度を使用
                if len(ml_predictions_array) > 0 and len(ml_probabilities) > 0:
                    prediction = int(ml_predictions_array[-1])
                    # 最大確率を信頼度として使用（実際MLモデルの出力）
                    import numpy as np

                    confidence = float(np.max(ml_probabilities[-1]))

                    self.logger.info(
                        f"✅ ML予測完了: prediction={['売り', '保持', '買い'][prediction + 1]}, confidence={confidence:.3f}"
                    )

                    return {
                        "prediction": prediction,
                        "confidence": confidence,
                    }
                else:
                    return {
                        "prediction": 0,
                        "confidence": get_threshold("ml.prediction_fallback_confidence", 0.0),
                    }
            else:
                return {
                    "prediction": 0,
                    "confidence": get_threshold("ml.prediction_fallback_confidence", 0.0),
                }
        except Exception as e:
            self.logger.error(f"ML予測エラー: {e}")
            return {
                "prediction": 0,
                "confidence": get_threshold("ml.prediction_fallback_confidence", 0.0),
            }

    async def _fetch_trading_info(self, market_data):
        """Phase 6: 追加情報取得（リスク管理のため）"""
        try:
            # 現在の残高取得
            balance_info = self.orchestrator.data_service.client.fetch_balance()
            current_balance = balance_info.get("JPY", {}).get("total", 0.0)

            # 現在のティッカー情報取得（bid/ask価格）
            start_time = time.time()
            ticker_info = self.orchestrator.data_service.client.fetch_ticker("BTC/JPY")
            api_latency_ms = (time.time() - start_time) * 1000

            bid = ticker_info.get("bid", 0.0)
            ask = ticker_info.get("ask", 0.0)

            self.logger.debug(
                f"取引情報取得 - 残高: ¥{current_balance:,.0f}, bid: ¥{bid:,.0f}, "
                f"ask: ¥{ask:,.0f}, API遅延: {api_latency_ms:.1f}ms"
            )

            return {
                "current_balance": current_balance,
                "bid": bid,
                "ask": ask,
                "api_latency_ms": api_latency_ms,
            }

        except (ConnectionError, TimeoutError) as e:
            # API接続エラー - フォールバック値を使用
            self.logger.warning(f"API接続エラー - フォールバック値使用: {e}")
            return self._get_fallback_trading_info(market_data)
        except (KeyError, ValueError) as e:
            # APIレスポンスデータエラー - フォールバック値を使用
            self.logger.warning(f"APIデータエラー - フォールバック値使用: {e}")
            return self._get_fallback_trading_info(market_data)
        except Exception as e:
            # 予期しないAPI取得エラー
            self.logger.error(f"予期しない取引情報取得エラー - フォールバック値使用: {e}")
            return self._get_fallback_trading_info(market_data)

    def _get_fallback_trading_info(self, market_data):
        """取引情報フォールバック値取得"""
        current_balance = get_threshold("trading.default_balance_jpy", 1000000.0)

        # 安全にmarket_dataから価格を取得
        try:
            # 設定からメインタイムフレームを取得
            from ..config import get_data_config

            main_timeframe = get_data_config("timeframes", ["4h", "15m"])[0]  # 最初の要素がメイン

            if (
                isinstance(market_data, dict)
                and main_timeframe in market_data
                and not market_data[main_timeframe].empty
            ):
                close_price = market_data[main_timeframe]["close"].iloc[-1]
                bid = close_price * get_threshold("trading.bid_spread_ratio", 0.999)
                ask = close_price * get_threshold("trading.ask_spread_ratio", 1.001)
            else:
                # デフォルト価格（BTC/JPY概算）
                bid = get_threshold("trading.fallback_prices.bid", 9000000.0)
                ask = get_threshold("trading.fallback_prices.ask", 9010000.0)
        except (KeyError, IndexError, TypeError) as price_error:
            self.logger.warning(f"価格フォールバック処理エラー: {price_error}")
            bid = get_threshold("trading.fallback_prices.default_bid", 9000000.0)
            ask = get_threshold("trading.fallback_prices.default_ask", 9010000.0)

        api_latency_ms = get_threshold("performance.default_latency_ms", 100.0)

        return {
            "current_balance": current_balance,
            "bid": bid,
            "ask": ask,
            "api_latency_ms": api_latency_ms,
        }

    async def _evaluate_risk(self, ml_prediction, strategy_signal, main_features, trading_info):
        """Phase 7: リスク管理・統合判定"""
        try:
            return self.orchestrator.risk_service.evaluate_trade_opportunity(
                ml_prediction=ml_prediction,
                strategy_signal=strategy_signal,  # 変数名統一
                market_data=main_features,  # DataFrameのみ渡す（型整合性確保）
                current_balance=trading_info["current_balance"],
                bid=trading_info["bid"],
                ask=trading_info["ask"],
                api_latency_ms=trading_info["api_latency_ms"],
            )
        except Exception as e:
            self.logger.error(f"リスク評価エラー: {e}")
            # エラー時はデフォルトで拒否
            return type(
                "TradeEvaluation",
                (),
                {
                    "decision": "denied",
                    "risk_score": 1.0,
                    "reason": f"リスク評価エラー: {e}",
                },
            )()

    async def _execute_approved_trades(self, trade_evaluation, cycle_id):
        """Phase 8a: 承認された取引の実行（Silent Failure修正済み）"""
        try:
            execution_result = None
            # Enum比較を正しく実装（str変換問題解決・循環import回避）
            decision_value = getattr(trade_evaluation, "decision", None)
            # RiskDecision.APPROVEDの値は"approved"なので文字列比較で回避
            if decision_value == "approved" or (
                hasattr(decision_value, "value") and decision_value.value == "approved"
            ):
                self.logger.debug(
                    f"取引実行開始 - サイクル: {cycle_id}, アクション: {getattr(trade_evaluation, 'side', 'unknown')}"
                )

                execution_result = await self.orchestrator.execution_service.execute_trade(
                    trade_evaluation
                )

                self.logger.info(
                    f"✅ 取引実行完了 - サイクル: {cycle_id}, 結果: {execution_result.success if execution_result else 'None'}"
                )

                await self.orchestrator.trading_logger.log_execution_result(
                    execution_result, cycle_id
                )
            else:
                # holdシグナルや取引拒否の詳細説明
                decision = getattr(trade_evaluation, "decision", "unknown")
                side = getattr(trade_evaluation, "side", "unknown")
                reason = getattr(trade_evaluation, "denial_reasons", ["理由不明"])

                if side.lower() in ["hold", "none"]:
                    self.logger.info(
                        f"📤 holdシグナル処理 - サイクル: {cycle_id}, アクション: {side}, 判定: {decision}"
                    )
                else:
                    self.logger.debug(
                        f"取引未承認 - サイクル: {cycle_id}, 決定: {decision}, アクション: {side}, 理由: {reason}"
                    )
                await self.orchestrator.trading_logger.log_trade_decision(
                    trade_evaluation, cycle_id
                )
        except AttributeError as e:
            # ExecutionServiceにexecute_tradeメソッドがない場合の詳細エラー
            self.logger.error(f"❌ ExecutionServiceメソッドエラー - サイクル: {cycle_id}: {e}")
            self.logger.error(f"ExecutionService型: {type(self.orchestrator.execution_service)}")
            self.logger.error(f"利用可能メソッド: {dir(self.orchestrator.execution_service)}")
        except Exception as e:
            # その他のエラーの詳細情報
            self.logger.error(f"❌ 取引実行エラー - サイクル: {cycle_id}: {type(e).__name__}: {e}")
            if hasattr(e, "__traceback__"):
                import traceback

                self.logger.error(f"スタックトレース: {traceback.format_exc()}")

    async def _check_stop_conditions(self, cycle_id):
        """Phase 8b: ストップ条件チェック（既存ポジションの自動決済）"""
        try:
            stop_result = await self.orchestrator.execution_service.check_stop_conditions()
            if stop_result:
                await self.orchestrator.trading_logger.log_execution_result(
                    stop_result, cycle_id, is_stop=True
                )
        except Exception as e:
            self.logger.error(f"ストップ条件チェックエラー: {e}")

    async def _handle_value_error(self, e, cycle_id):
        """ValueError処理"""
        if "not fitted" in str(e) or "EnsembleModel is not fitted" in str(e):
            self.logger.error(f"🚨 MLモデル未学習エラー検出 - ID: {cycle_id}, エラー: {e}")
            # 自動復旧試行
            await self.orchestrator.system_recovery.recover_ml_service()
            return  # このサイクルはスキップ
        else:
            # 🚨 CRITICAL FIX: エラーハンドリング内Discord通知による再帰防止
            self.logger.error(
                f"取引サイクル値エラー - ID: {cycle_id}, エラー: {e}",
                discord_notify=False,
            )
            self.orchestrator.system_recovery.record_cycle_error(cycle_id, e)
            return  # このサイクルはスキップ、次のサイクルへ

    async def _handle_model_error(self, e, cycle_id):
        """ModelLoadError処理"""
        # MLモデル読み込みエラー専用処理
        self.logger.error(f"❌ MLモデルエラー - ID: {cycle_id}: {e}", discord_notify=False)
        await self.orchestrator.system_recovery.recover_ml_service()
        self.orchestrator.system_recovery.record_cycle_error(cycle_id, e)
        return  # このサイクルはスキップ、次のサイクルへ

    async def _handle_connection_error(self, e, cycle_id):
        """ConnectionError/TimeoutError処理"""
        # 外部サービス接続エラー
        self.logger.error(
            f"外部サービス接続エラー - ID: {cycle_id}, エラー: {e}",
            discord_notify=False,
        )
        self.orchestrator.system_recovery.record_cycle_error(cycle_id, e)
        return  # このサイクルはスキップ、次のサイクルへ

    async def _handle_attribute_error(self, e, cycle_id):
        """AttributeError/TypeError処理"""
        # オブジェクト・型エラー
        self.logger.error(
            f"オブジェクト・型エラー - ID: {cycle_id}, エラー: {e}",
            discord_notify=False,
        )
        self.orchestrator.system_recovery.record_cycle_error(cycle_id, e)
        return  # このサイクルはスキップ、次のサイクルへ

    async def _handle_system_error(self, e, cycle_id):
        """RuntimeError/SystemError処理"""
        # システムレベルエラー
        self.logger.error(
            f"システムレベルエラー - ID: {cycle_id}, エラー: {e}", discord_notify=False
        )
        self.orchestrator.system_recovery.record_cycle_error(cycle_id, e)
        return  # このサイクルはスキップ、次のサイクルへ

    async def _handle_unexpected_error(self, e, cycle_id):
        """予期しないエラー処理"""
        # 予期しないエラーは再送出
        self.logger.critical(
            f"❌ 予期しない取引サイクルエラー - ID: {cycle_id}: {e}",
            discord_notify=False,
        )
        self.orchestrator.system_recovery.record_cycle_error(cycle_id, e)
        raise CryptoBotError(f"取引サイクルで予期しないエラー - ID: {cycle_id}: {e}")
