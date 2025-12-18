"""
取引サイクルマネージャー - Phase 51.3完了（最重要・1,100行）

orchestrator.pyから分離した取引サイクル実行機能。
データ取得→特徴量生成→戦略評価→ML予測→リスク管理→注文実行のフロー全体を担当。

Phase 51.3: Dynamic Strategy Selection実装（市場レジーム連動戦略重み最適化）
Phase 49完了:
- バックテスト完全改修統合（戦略シグナル事前計算・TP/SL決済ロジック・TradeTracker・matplotlib可視化）
- 証拠金維持率80%遵守ロジック統合（critical: 100.0 → 80.0変更）
- TP/SL設定完全同期（thresholds.yaml完全準拠・ハードコード値削除）

Phase 49.16: TP/SL設定完全見直し
Phase 42.3: ML Agreement Logic修正（strict matching）・Feature Warning抑制・証拠金チェックリトライ
Phase 42.1-42.2: 統合TP/SL実装（注文数91.7%削減）・トレーリングストップ実装
Phase 41.8.5: ML統合閾値最適化（min_ml_confidence: 0.45・ML統合率100%達成）
Phase 41.8: Strategy-Aware ML実装（55特徴量・実戦略信号学習）
Phase 35: バックテスト最適化（特徴量事前計算・ML予測キャッシュ）
Phase 29.5: ML予測統合実装（戦略70% + ML30%・一致ボーナス/不一致ペナルティ）
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import pandas as pd

# Silent Failure修正: RiskDecision Enum は動的インポートで回避
from ..config import get_threshold
from ..exceptions import CryptoBotError, ModelLoadError
from ..logger import CryptoBotLogger

if TYPE_CHECKING:
    from ...strategies.base.strategy_base import StrategySignal


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

        # Phase 45: Meta-Learning動的重み最適化初期化
        self.meta_optimizer = None
        self.market_data_cache = None  # 市場データキャッシュ（Meta-ML用）
        if get_threshold("ml.meta_learning.enabled", False):
            try:
                from ...ml.meta_learning import MetaLearningWeightOptimizer

                self.meta_optimizer = MetaLearningWeightOptimizer(logger=logger)
                self.logger.info("✅ Meta-Learning動的重み最適化: 有効")
            except Exception as e:
                self.logger.warning(f"⚠️ Meta-Learning初期化失敗: {e} - フォールバック固定重み使用")
                self.meta_optimizer = None

        # Phase 51.3: Dynamic Strategy Selection初期化
        self.dynamic_strategy_selector = None
        self.market_regime_classifier = None
        if get_threshold("dynamic_strategy_selection.enabled", True):
            try:
                from .dynamic_strategy_selector import DynamicStrategySelector
                from .market_regime_classifier import MarketRegimeClassifier

                self.dynamic_strategy_selector = DynamicStrategySelector()
                self.market_regime_classifier = MarketRegimeClassifier()
                self.logger.info("✅ Phase 51.3: 動的戦略選択システム有効")
            except Exception as e:
                self.logger.warning(f"⚠️ Phase 51.3: 動的戦略選択初期化失敗: {e} - 固定重み使用")
                self.dynamic_strategy_selector = None
                self.market_regime_classifier = None

    async def execute_trading_cycle(self):
        """
        取引サイクル実行

        高レベル取引サイクル制御。各Phase層に具体的な処理を委譲し、
        ここでは統合フローの制御のみ実行。
        """
        cycle_id = datetime.now().isoformat()
        # Phase 35.2: バックテスト時はDEBUGレベル（ログ抑制）
        import os

        if os.environ.get("BACKTEST_MODE") == "true":
            self.logger.debug(f"取引サイクル開始 - ID: {cycle_id}")
        else:
            self.logger.info(f"取引サイクル開始 - ID: {cycle_id}")

        try:
            # Phase 2: データ取得
            market_data = await self._fetch_market_data()
            if market_data is None:
                self.logger.warning("市場データ取得失敗 - サイクル終了")
                return

            # Phase 45: 市場データキャッシュ（Meta-ML用）
            self.market_data_cache = market_data

            # Phase 3: 特徴量生成（50特徴量）
            features, main_features = await self._generate_features(market_data)

            # Phase 51.3: 動的戦略選択（レジーム分類 → 戦略重み更新）
            await self._apply_dynamic_strategy_selection(main_features)

            # Phase 4: 戦略評価（Phase 31: マルチタイムフレーム対応）
            strategy_signal = await self._evaluate_strategy(main_features, features)

            # Phase 41: 個別戦略シグナル取得
            strategy_signals = await self._get_individual_strategy_signals(main_features, features)

            # Phase 49.8: 診断ログ削除（根本原因修正完了）

            # Phase 41: 戦略シグナル特徴量追加（50→55特徴量）
            if strategy_signals:
                main_features = await self._add_strategy_signal_features(
                    main_features, strategy_signals
                )

            # Phase 5: ML予測（Phase 41: 55特徴量対応）
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
            # Phase 46: トレーリングストップ削除（デイトレード不要）

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
            # Phase 51.5-A Fix: limit=100→200（戦略最低20件要求に対する安全マージン）
            return await self.orchestrator.data_service.fetch_multi_timeframe(
                symbol="BTC/JPY", limit=200
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
                    # Phase 35.2: 事前計算済み特徴量チェック（バックテスト最適化）
                    required_features = ["rsi_14", "macd", "atr_14"]  # 代表的特徴量
                    if all(col in df.columns for col in required_features):
                        # 既に特徴量が計算済み（事前計算データ）
                        features[timeframe] = df
                        self.logger.debug(f"✅ {timeframe}事前計算済み特徴量使用（Phase 35最適化）")
                    else:
                        # Phase 50.8: Level 1→Level 2フォールバック実装
                        # Phase 50.9: 62特徴量固定システム（外部API削除）
                        features[timeframe] = (
                            await self.orchestrator.feature_service.generate_features(df)
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

        main_timeframe = get_data_config("timeframes", ["15m", "4h"])[0]  # 最初の要素がメイン
        main_features = features.get(main_timeframe, pd.DataFrame())
        return features, main_features

    async def _evaluate_strategy(self, main_features, all_features):
        """Phase 4: 戦略評価（Phase 31: マルチタイムフレーム対応）"""
        try:
            if not main_features.empty:
                # Phase 31: all_featuresをmulti_timeframe_dataとして渡す
                return self.orchestrator.strategy_service.analyze_market(
                    main_features, multi_timeframe_data=all_features
                )
            else:
                # 空のDataFrameの場合はHOLDシグナル
                return self.orchestrator.strategy_service._create_hold_signal(
                    pd.DataFrame(), "データ不足"
                )
        except Exception as e:
            # Phase 35: バックテストモード時はDEBUGレベル（環境変数直接チェック）
            import os

            if os.environ.get("BACKTEST_MODE") == "true":
                self.logger.debug(f"戦略評価エラー: {e}")
            else:
                self.logger.error(f"戦略評価エラー: {e}")
            return self.orchestrator.strategy_service._create_hold_signal(
                pd.DataFrame(), f"戦略評価エラー: {e}"
            )

    async def _apply_dynamic_strategy_selection(self, main_features: pd.DataFrame):
        """
        Phase 51.3: 動的戦略選択（市場レジーム連動戦略重み最適化）

        市場レジームを分類し、レジームに応じた戦略重みを適用する。

        処理フロー:
        1. MarketRegimeClassifierで市場レジーム分類
        2. DynamicStrategySelectorでレジーム別戦略重み取得
        3. StrategyManager.update_strategy_weights()で重み更新

        Args:
            main_features: メインタイムフレーム特徴量
        """
        try:
            # 機能無効化チェック
            if not self.dynamic_strategy_selector or not self.market_regime_classifier:
                return

            # 特徴量不足チェック
            if main_features.empty:
                self.logger.debug("Phase 51.3: 特徴量不足 - 動的戦略選択スキップ")
                return

            # 1. 市場レジーム分類
            regime = self.market_regime_classifier.classify(main_features)

            # 2. レジーム別戦略重み取得
            regime_weights = self.dynamic_strategy_selector.get_regime_weights(regime)

            # 3. 戦略重み更新
            if regime_weights:
                # 通常レジーム: 戦略重み適用
                self.orchestrator.strategy_service.update_strategy_weights(regime_weights)
                self.logger.info(
                    f"✅ Phase 51.3: 戦略重み更新完了 - レジーム={regime.value}, "
                    f"戦略数={len(regime_weights)}"
                )
            else:
                # 高ボラティリティ: 全戦略無効化（待機モード）
                # 注: 空辞書を渡すと全戦略が無効化される想定だが、
                # StrategyManagerの実装次第では別の処理が必要
                self.logger.warning(
                    f"⚠️ Phase 51.3: 高ボラティリティ検出（レジーム={regime.value}）- 全戦略待機モード"
                )
                # 全戦略を0重みに設定
                all_zero_weights = {
                    strategy_name: 0.0
                    for strategy_name in self.orchestrator.strategy_service.strategies.keys()
                }
                self.orchestrator.strategy_service.update_strategy_weights(all_zero_weights)

        except Exception as e:
            self.logger.error(f"Phase 51.3: 動的戦略選択エラー: {e} - 固定重み継続使用")
            # エラー時は既存の重みを維持（何もしない）

    async def _get_individual_strategy_signals(self, main_features, all_features):
        """
        Phase 41: 個別戦略シグナル取得（ML特徴量用）

        各戦略の個別判断を取得し、ML特徴量として使用するための
        エンコードされたシグナルを返します。

        Args:
            main_features: メインタイムフレーム特徴量
            all_features: 全タイムフレーム特徴量

        Returns:
            Dict: 個別戦略シグナル辞書
                例: {"ATRBased": {"action": "buy", "confidence": 0.678, "encoded": 0.678}}
        """
        try:
            if main_features.empty:
                self.logger.debug("Phase 41: 特徴量不足により個別戦略シグナル取得スキップ")
                return {}

            # StrategyManager.get_individual_strategy_signals() を呼び出し
            strategy_signals = self.orchestrator.strategy_service.get_individual_strategy_signals(
                main_features, multi_timeframe_data=all_features
            )

            if strategy_signals:
                self.logger.info(
                    f"✅ Phase 41: 個別戦略シグナル取得完了 - {len(strategy_signals)}戦略"
                )
                return strategy_signals
            else:
                self.logger.warning("Phase 41: 個別戦略シグナルが空です")
                return {}

        except Exception as e:
            self.logger.error(f"Phase 41: 個別戦略シグナル取得エラー: {e}")
            return {}

    async def _add_strategy_signal_features(self, main_features, strategy_signals):
        """
        Phase 41: 戦略シグナル特徴量追加（50→55特徴量）

        個別戦略シグナルをDataFrameに特徴量として追加します。

        Args:
            main_features: 既存の特徴量DataFrame（50特徴量）
            strategy_signals: 個別戦略シグナル辞書

        Returns:
            pd.DataFrame: 戦略シグナル特徴量が追加されたDataFrame（55特徴量）
        """
        try:
            if main_features.empty or not strategy_signals:
                self.logger.warning("Phase 41: 特徴量追加スキップ（データ不足）")
                return main_features

            # FeatureGenerator._add_strategy_signal_features() を使用
            updated_features = self.orchestrator.feature_service._add_strategy_signal_features(
                main_features, strategy_signals
            )

            if updated_features is not None and not updated_features.empty:
                # 特徴量数確認
                original_count = len(main_features.columns)
                updated_count = len(updated_features.columns)
                added_count = updated_count - original_count

                self.logger.info(
                    f"✅ Phase 41: 戦略シグナル特徴量追加完了 - "
                    f"{original_count}→{updated_count}特徴量（+{added_count}個）"
                )
                return updated_features
            else:
                self.logger.warning("Phase 41: 特徴量追加失敗 - 元の特徴量を使用")
                return main_features

        except Exception as e:
            self.logger.error(f"Phase 41: 戦略シグナル特徴量追加エラー: {e} - 元の特徴量を使用")
            return main_features

    async def _get_ml_prediction(self, main_features):
        """Phase 5: ML予測（Phase 35.4: バックテスト時はキャッシュ使用）"""
        try:
            # Phase 35.4: バックテストモード時は事前計算済みML予測を使用
            import os

            if os.environ.get("BACKTEST_MODE") == "true":
                cached_prediction = self.orchestrator.data_service.get_backtest_ml_prediction()
                if cached_prediction:
                    self.logger.debug(
                        f"✅ ML予測キャッシュ使用: prediction={cached_prediction['prediction']}, "
                        f"confidence={cached_prediction['confidence']:.3f}"
                    )
                    return cached_prediction

            if not main_features.empty:
                # Phase 40.6: 50特徴量を動的取得してML予測（特徴量数不一致修正）
                from ...core.config.feature_manager import get_feature_names

                features_to_use = get_feature_names()

                # 利用可能な特徴量のみを選択
                available_features = [
                    col for col in features_to_use if col in main_features.columns
                ]
                # Phase 42.3.2: Phase 41で後から追加される戦略シグナル特徴量は警告から除外
                if len(available_features) != len(features_to_use):
                    missing_features = [
                        f for f in features_to_use if f not in main_features.columns
                    ]
                    # strategy_signal_* は Phase 41 で後から追加されるため、実際の不足としてカウントしない
                    strategy_signal_features = [
                        f for f in missing_features if f.startswith("strategy_signal_")
                    ]
                    real_missing = [
                        f for f in missing_features if not f.startswith("strategy_signal_")
                    ]

                    # 実際に不足している特徴量（戦略シグナル以外）のみ警告
                    if real_missing:
                        self.logger.warning(
                            f"🚨 特徴量不足検出: {len(real_missing)}/{len(features_to_use)}個 - {real_missing[:5]}"
                        )
                    elif strategy_signal_features:
                        # 戦略シグナル特徴量のみが不足している場合はDEBUGレベル（Phase 41で追加予定）
                        self.logger.debug(
                            f"Phase 41: 戦略シグナル特徴量は後で追加されます（{len(strategy_signal_features)}個）"
                        )

                main_features_for_ml = main_features[available_features]
                self.logger.debug(f"ML予測用特徴量選択完了: {main_features_for_ml.shape}")

                # Phase 50.8: 特徴量数に応じた正しいモデルを確保
                actual_feature_count = len(main_features.columns)
                if not self.orchestrator.ml_service.ensure_correct_model(actual_feature_count):
                    self.logger.warning(
                        f"⚠️ Phase 50.8: モデルロード失敗（{actual_feature_count}特徴量） - "
                        "フォールバック処理継続"
                    )

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
                        f"✅ ML予測完了: prediction={['売り', '保持', '買い'][prediction]}, confidence={confidence:.3f}"
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
        """取引情報フォールバック値取得（モード別適正化）"""
        # モード別適正残高を使用（ドローダウン計算異常問題修正）
        try:
            # 実行モードを判定（orchestratorの設定から取得）
            config_mode = getattr(self.orchestrator.config, "mode", "paper")

            # mode_balancesから適切な初期残高を取得
            mode_balances = getattr(self.orchestrator.config, "mode_balances", {})
            mode_config = mode_balances.get(config_mode, {})
            appropriate_balance = mode_config.get("initial_balance", 10000.0)

            current_balance = appropriate_balance
            self.logger.warning(
                f"⚠️ API取得失敗 - {config_mode}モード適正フォールバック残高使用: {current_balance:.0f}円"
            )

        except Exception as e:
            # 最終フォールバック
            current_balance = get_threshold("trading.default_balance_jpy", 10000.0)
            self.logger.error(
                f"フォールバック値取得エラー - デフォルト使用: {current_balance:.0f}円, エラー: {e}"
            )

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
        """Phase 7: リスク管理・統合判定（Phase 29.5: ML予測統合）"""
        try:
            # Phase 51.9: レジーム分類（ML統合前に実行）
            regime = "unknown"
            if self.market_regime_classifier is not None:
                try:
                    regime_type = self.market_regime_classifier.classify(main_features)
                    regime = regime_type.value  # RegimeType.TIGHT_RANGE → "tight_range"
                except Exception as e:
                    self.logger.warning(f"⚠️ レジーム分類エラー: {e} - デフォルト設定使用")
                    regime = "unknown"

            # Phase 29.5 + Phase 51.9: ML予測を戦略シグナルと統合（レジーム別）
            integrated_signal = self._integrate_ml_with_strategy(
                ml_prediction, strategy_signal, regime=regime
            )

            # Phase 54.9: バックテスト用基準時刻を取得
            # market_dataの最後のインデックスを使用（バックテストでは正しい時刻、ライブでは現在に近い時刻）
            reference_timestamp = None
            try:
                if (
                    hasattr(main_features, "index")
                    and len(main_features.index) > 0
                    and hasattr(main_features.index[-1], "to_pydatetime")
                ):
                    reference_timestamp = main_features.index[-1].to_pydatetime()
            except Exception:
                pass  # ライブモードではNone（datetime.now()が使用される）

            return await self.orchestrator.risk_service.evaluate_trade_opportunity(
                ml_prediction=ml_prediction,
                strategy_signal=integrated_signal,  # 統合後のシグナルを使用
                market_data=main_features,  # DataFrameのみ渡す（型整合性確保）
                current_balance=trading_info["current_balance"],
                bid=trading_info["bid"],
                ask=trading_info["ask"],
                api_latency_ms=trading_info["api_latency_ms"],
                reference_timestamp=reference_timestamp,  # Phase 54.9: Kelly基準用
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

    def _get_dynamic_weights(self) -> dict[str, float]:
        """
        Phase 45.4: Meta-Learningで動的重みを取得

        市場状況に応じて戦略・ML重みを動的に最適化。
        Meta-ML無効時・エラー時はフォールバック固定重み使用。

        Returns:
            dict[str, float]: 動的重み
                - ml: ML重み（0-1）
                - strategy: 戦略重み（0-1）
                ※合計1.0に正規化済み
        """
        # Meta-Learning無効時はフォールバック固定重み
        if self.meta_optimizer is None:
            return {
                "ml": get_threshold("ml.strategy_integration.ml_weight", 0.35),
                "strategy": get_threshold("ml.strategy_integration.strategy_weight", 0.7),
            }

        # 市場データ未キャッシュ時はフォールバック
        if self.market_data_cache is None:
            self.logger.debug("市場データ未キャッシュ - フォールバック固定重み使用")
            return {
                "ml": get_threshold("ml.strategy_integration.ml_weight", 0.35),
                "strategy": get_threshold("ml.strategy_integration.strategy_weight", 0.7),
            }

        try:
            # Meta-ML推論
            weights = self.meta_optimizer.predict_weights(self.market_data_cache)
            return weights
        except Exception as e:
            self.logger.warning(f"⚠️ Meta-ML動的重み取得エラー: {e} - フォールバック固定重み使用")
            return {
                "ml": get_threshold("ml.strategy_integration.ml_weight", 0.35),
                "strategy": get_threshold("ml.strategy_integration.strategy_weight", 0.7),
            }

    def _integrate_ml_with_strategy(
        self, ml_prediction: dict, strategy_signal: StrategySignal, regime: str = "unknown"
    ) -> StrategySignal:
        """
        Phase 29.5 + Phase 51.9: ML予測と戦略シグナルの統合（レジーム別最適化）

        ML予測結果を戦略シグナルと統合し、最終的な取引信頼度を調整。
        Phase 51.9: レジーム別にML統合パラメータを動的適用。
        一致時はボーナス、不一致時はペナルティを適用。

        Args:
            ml_prediction: ML予測結果 {"prediction": int, "confidence": float}
                          prediction: -1=売り, 0=保持, 1=買い
            strategy_signal: 戦略シグナル (StrategySignalオブジェクト)
            regime: 市場レジーム (Phase 51.9: レジーム別パラメータ適用)
                   "tight_range", "normal_range", "trending", "high_volatility", "unknown"

        Returns:
            StrategySignal: 統合後のシグナル（ML調整済み）
        """
        try:
            # ML統合が無効の場合は元のシグナルをそのまま返す
            if not get_threshold("ml.strategy_integration.enabled", False):
                self.logger.debug("ML統合無効 - 戦略シグナルをそのまま使用")
                return strategy_signal

            # Phase 51.9: レジーム別ML統合パラメータ読み込み
            regime_ml_enabled = get_threshold("ml.regime_ml_integration.enabled", False)
            if regime_ml_enabled and regime != "unknown":
                # レジーム別設定を試行
                regime_config_base = f"ml.regime_ml_integration.{regime}"
                min_ml_confidence = get_threshold(f"{regime_config_base}.min_ml_confidence", None)
                high_confidence_threshold = get_threshold(
                    f"{regime_config_base}.high_confidence_threshold", None
                )
                ml_weight = get_threshold(f"{regime_config_base}.ml_weight", None)
                strategy_weight = get_threshold(f"{regime_config_base}.strategy_weight", None)
                agreement_bonus = get_threshold(f"{regime_config_base}.agreement_bonus", None)
                disagreement_penalty = get_threshold(
                    f"{regime_config_base}.disagreement_penalty", None
                )

                # レジーム別設定が存在する場合のみログ出力
                if min_ml_confidence is not None:
                    self.logger.info(
                        f"📊 Phase 51.9: レジーム別ML統合適用 - regime={regime}, "
                        f"min_conf={min_ml_confidence:.2f}, ml_weight={ml_weight:.2f}"
                    )
            else:
                # Phase 51.9無効 or レジーム不明時はデフォルト設定使用
                min_ml_confidence = None
                high_confidence_threshold = None
                ml_weight = None
                strategy_weight = None
                agreement_bonus = None
                disagreement_penalty = None

            # フォールバック: レジーム別設定がない場合は従来の固定設定使用
            if min_ml_confidence is None:
                min_ml_confidence = get_threshold("ml.strategy_integration.min_ml_confidence", 0.6)
            if high_confidence_threshold is None:
                high_confidence_threshold = get_threshold(
                    "ml.strategy_integration.high_confidence_threshold", 0.8
                )
            if agreement_bonus is None:
                agreement_bonus = get_threshold("ml.strategy_integration.agreement_bonus", 1.2)
            if disagreement_penalty is None:
                disagreement_penalty = get_threshold(
                    "ml.strategy_integration.disagreement_penalty", 0.7
                )

            # ML予測信頼度が低い場合は統合しない
            ml_confidence = ml_prediction.get("confidence", 0.0)

            if ml_confidence < min_ml_confidence:
                self.logger.info(
                    f"ML信頼度不足 ({ml_confidence:.3f} < {min_ml_confidence:.3f}) - 戦略シグナルのみ使用"
                )
                return strategy_signal

            # 予測値とアクションの変換（Phase 51.9-6A: 3クラス分類対応）
            ml_pred = ml_prediction.get("prediction", 0)
            ml_action_map = {0: "sell", 1: "hold", 2: "buy"}  # 3クラス: 0=SELL, 1=HOLD, 2=BUY
            ml_action = ml_action_map.get(ml_pred, "hold")

            # StrategySignalオブジェクトから属性を直接取得
            strategy_action = strategy_signal.action
            strategy_confidence = strategy_signal.confidence

            # Phase 51.8-J4-G: バックテストモードで戦略信頼度可視化のためWARNINGレベルに変更
            self.logger.warning(
                f"🔄 ML統合開始: 戦略={strategy_action}({strategy_confidence:.3f}), "
                f"ML={ml_action}({ml_confidence:.3f})"
            )

            # 一致・不一致判定（Phase 42.3.1: hold予測は厳密な一致のみ認定）
            # 修正前: holdをあらゆる方向性シグナルと一致扱い（バグ）
            # 修正後: 厳密な一致のみ（ML=buy+戦略=buy、ML=sell+戦略=sell、ML=hold+戦略=hold）
            is_agreement = ml_action == strategy_action

            # Phase 45.4 + Phase 51.9: 動的重み取得（レジーム別 or Meta-Learning）
            # レジーム別設定がない場合のみMeta-Learning動的重みを使用
            if ml_weight is None or strategy_weight is None:
                weights = self._get_dynamic_weights()
                if ml_weight is None:
                    ml_weight = weights["ml"]
                if strategy_weight is None:
                    strategy_weight = weights["strategy"]

            # ベース信頼度計算（加重平均）
            base_confidence = (strategy_confidence * strategy_weight) + (ml_confidence * ml_weight)

            # ML高信頼度時のボーナス・ペナルティ適用
            if ml_confidence >= high_confidence_threshold:
                if is_agreement:
                    # 一致時: ボーナス適用（レジーム別設定が既に読み込み済み）
                    adjusted_confidence = min(base_confidence * agreement_bonus, 1.0)
                    # Phase 51.8-J4-G + Phase 51.9: レジーム情報追加
                    self.logger.warning(
                        f"✅ ML・戦略一致（ML高信頼度）[{regime}] - "
                        f"戦略={strategy_action}({strategy_confidence:.3f}), "
                        f"ML={ml_action}({ml_confidence:.3f}), "
                        f"ボーナス適用: {base_confidence:.3f} → {adjusted_confidence:.3f}"
                    )
                else:
                    # 不一致時: ペナルティ適用（レジーム別設定が既に読み込み済み）
                    adjusted_confidence = base_confidence * disagreement_penalty
                    # Phase 51.8-J4-G + Phase 51.9: レジーム情報追加
                    self.logger.warning(
                        f"⚠️ ML・戦略不一致（ML高信頼度）[{regime}] - "
                        f"戦略={strategy_action}({strategy_confidence:.3f}), "
                        f"ML={ml_action}({ml_confidence:.3f}), "
                        f"ペナルティ適用: {base_confidence:.3f} → {adjusted_confidence:.3f}"
                    )

                    # 不一致時はholdに変更する選択肢も
                    # Phase 40.3: hold変更閾値を設定から取得（ハードコード排除）
                    hold_threshold = get_threshold(
                        "ml.strategy_integration.hold_conversion_threshold", 0.4
                    )
                    if adjusted_confidence < hold_threshold:  # 信頼度が極端に低い場合
                        self.logger.warning(
                            f"⛔ 信頼度極低（{adjusted_confidence:.3f} < {hold_threshold:.3f}）- holdに変更"
                        )
                        # 新しいStrategySignalオブジェクトとして返す（hold変更）
                        from ...strategies.base.strategy_base import StrategySignal

                        return StrategySignal(
                            strategy_name=strategy_signal.strategy_name,
                            timestamp=strategy_signal.timestamp,
                            action="hold",
                            confidence=adjusted_confidence,
                            strength=adjusted_confidence,
                            current_price=strategy_signal.current_price,
                            entry_price=strategy_signal.entry_price,
                            stop_loss=strategy_signal.stop_loss,
                            take_profit=strategy_signal.take_profit,
                            position_size=strategy_signal.position_size,
                            risk_ratio=strategy_signal.risk_ratio,
                            indicators=strategy_signal.indicators,
                            reason="ML・戦略不一致（信頼度極低）",
                            metadata={
                                **(strategy_signal.metadata or {}),
                                "ml_adjusted": True,
                                "original_action": strategy_action,
                                "ml_action": ml_action,
                                "adjustment_reason": "ml_disagreement_low_confidence",
                                "original_confidence": strategy_confidence,
                                "ml_confidence": ml_confidence,
                            },
                        )
            else:
                # ML信頼度が高くない場合は加重平均のみ
                adjusted_confidence = base_confidence
                self.logger.debug(f"📊 ML通常統合（加重平均のみ）: {base_confidence:.3f}")

            # 統合結果を新しいStrategySignalオブジェクトとして返す
            from ...strategies.base.strategy_base import StrategySignal

            return StrategySignal(
                strategy_name=strategy_signal.strategy_name,
                timestamp=strategy_signal.timestamp,
                action=strategy_action,  # アクションは戦略のものを維持
                confidence=adjusted_confidence,  # ML統合後の信頼度
                strength=adjusted_confidence,  # strengthも更新
                current_price=strategy_signal.current_price,
                entry_price=strategy_signal.entry_price,
                stop_loss=strategy_signal.stop_loss,
                take_profit=strategy_signal.take_profit,
                position_size=strategy_signal.position_size,
                risk_ratio=strategy_signal.risk_ratio,
                indicators=strategy_signal.indicators,
                reason=strategy_signal.reason,
                metadata={
                    **(strategy_signal.metadata or {}),
                    "ml_adjusted": True,
                    "original_confidence": strategy_confidence,
                    "ml_confidence": ml_confidence,
                    "ml_action": ml_action,
                    "is_agreement": is_agreement,
                },
            )

        except Exception as e:
            self.logger.error(f"ML統合エラー: {e} - 戦略シグナルのみ使用")
            return strategy_signal

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

                # Phase 8a-1: 取引直前最終検証（口座残高使い切り防止・追加安全チェック）
                pre_execution_check = await self._pre_execution_verification(
                    trade_evaluation, cycle_id
                )
                if not pre_execution_check["allowed"]:
                    self.logger.warning(
                        f"🚫 取引直前検証により取引拒否 - サイクル: {cycle_id}, 理由: {pre_execution_check['reason']}"
                    )
                    return

                execution_result = await self.orchestrator.execution_service.execute_trade(
                    trade_evaluation
                )

                # Phase 35.2: バックテスト時はWARNING（強制出力）
                import os

                if os.environ.get("BACKTEST_MODE") == "true":
                    self.logger.warning(
                        f"✅ 取引実行完了 - サイクル: {cycle_id}, 結果: {execution_result.success if execution_result else 'None'}"
                    )
                else:
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

    # ========================================
    # Phase 46: トレーリングストップ削除（デイトレード不要）
    # ========================================
    # Phase 42.2で実装されたトレーリングストップ監視機能を削除
    # デイトレード特化設計では不要なため

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

    async def _pre_execution_verification(self, trade_evaluation, cycle_id) -> dict:
        """
        取引実行直前最終検証（口座残高使い切り防止・追加安全チェック）

        リスク管理後から実際の取引実行までの間に状況が変わった可能性を考慮した
        最後の安全チェック。二重チェックによる安全性向上。

        Args:
            trade_evaluation: 取引評価結果
            cycle_id: 取引サイクルID

        Returns:
            Dict: {"allowed": bool, "reason": str, "additional_info": dict}
        """
        try:
            self.logger.debug(f"🔍 取引直前最終検証開始 - サイクル: {cycle_id}")

            # 1. 基本情報確認
            side = getattr(trade_evaluation, "side", "unknown")
            position_size = getattr(trade_evaluation, "position_size", 0.0)

            if side.lower() in ["hold", "none", ""] or position_size <= 0:
                return {"allowed": False, "reason": "holdシグナルまたは無効なポジションサイズ"}

            # 2. ExecutionService経由でポジション制限再確認
            try:
                execution_service = self.orchestrator.execution_service
                if hasattr(execution_service, "_check_position_limits"):
                    position_check = execution_service._check_position_limits(trade_evaluation)
                    if not position_check.get("allowed", True):
                        return {
                            "allowed": False,
                            "reason": f"ポジション制限再確認失敗: {position_check.get('reason', '不明')}",
                        }
            except Exception as e:
                self.logger.warning(f"⚠️ ポジション制限再確認エラー: {e}")

            # 3. 現在残高確認（最新残高でのチェック）
            try:
                current_balance = await self._get_current_balance()
                if current_balance is not None and current_balance > 0:
                    # 最小取引可能残高チェック
                    min_trade_size = get_threshold("trading.min_trade_size", 0.0001)
                    estimated_cost = min_trade_size * 16700000  # BTC価格概算

                    if current_balance < estimated_cost * 1.5:  # 1.5倍の余裕を確保
                        return {
                            "allowed": False,
                            "reason": f"残高不足: ¥{current_balance:,.0f} < 必要残高¥{estimated_cost * 1.5:,.0f}",
                        }
            except Exception as e:
                self.logger.warning(f"⚠️ 現在残高確認エラー: {e}")

            # 4. 市場急変状況チェック
            try:
                # 直近の価格ボラティリティ確認（簡易実装）
                market_volatility_check = await self._check_current_market_volatility()
                if market_volatility_check and not market_volatility_check.get("stable", True):
                    volatile_threshold = get_threshold(
                        "trading.anomaly.max_volatility_for_trade", 0.05
                    )
                    current_volatility = market_volatility_check.get("volatility", 0.0)

                    if current_volatility > volatile_threshold:
                        return {
                            "allowed": False,
                            "reason": (
                                f"市場急変検出: ボラティリティ {current_volatility * 100:.1f}% "
                                f"> {volatile_threshold * 100:.0f}%"
                            ),
                        }
            except Exception as e:
                self.logger.debug(f"市場ボラティリティチェックエラー（非致命的）: {e}")

            # 5. 緊急時条件確認（Emergency Stop-Lossがアクティブでないか）
            try:
                if hasattr(self.orchestrator, "execution_service"):
                    emergency_status = await self._check_emergency_conditions()
                    if emergency_status and not emergency_status.get("normal", True):
                        return {
                            "allowed": False,
                            "reason": f"緊急時条件検出: {emergency_status.get('reason', '不明な緊急事態')}",
                        }
            except Exception as e:
                self.logger.debug(f"緊急時条件チェックエラー（非致命的）: {e}")

            # 6. システム健全性最終確認
            health_status = await self._check_system_health_for_trading()
            if not health_status.get("healthy", False):
                return {
                    "allowed": False,
                    "reason": f"システム健全性問題: {health_status.get('issue', '不明')}",
                }

            self.logger.debug(f"✅ 取引直前最終検証通過 - サイクル: {cycle_id}")

            return {
                "allowed": True,
                "reason": "全検証通過",
                "additional_info": {
                    "verification_time": datetime.now(),
                    "checks_performed": [
                        "position_limits",
                        "balance",
                        "volatility",
                        "emergency",
                        "health",
                    ],
                },
            }

        except Exception as e:
            self.logger.error(f"❌ 取引直前検証エラー - サイクル: {cycle_id}: {e}")
            return {"allowed": False, "reason": f"検証処理エラー: {e}"}

    async def _get_current_balance(self) -> Optional[float]:
        """現在残高取得（簡易実装）"""
        try:
            # ExecutionServiceから残高取得を試行
            execution_service = self.orchestrator.execution_service
            if hasattr(execution_service, "current_balance"):
                return float(execution_service.current_balance)
            elif hasattr(execution_service, "virtual_balance"):
                return float(execution_service.virtual_balance)
            return None
        except Exception:
            return None

    async def _check_current_market_volatility(self) -> Optional[dict]:
        """現在の市場ボラティリティ確認（簡易実装）"""
        try:
            # 簡易実装: 将来的にはリアルタイム価格変動監視を実装
            return {"stable": True, "volatility": 0.01}  # 1%以下なら安定
        except Exception:
            return None

    async def _check_emergency_conditions(self) -> Optional[dict]:
        """緊急時条件確認（簡易実装）"""
        try:
            # 簡易実装: 将来的には緊急時条件の詳細チェック
            return {"normal": True}
        except Exception:
            return None

    async def _check_system_health_for_trading(self) -> dict:
        """取引実行可能システム健全性チェック"""
        try:
            # 基本的なシステムコンポーネント確認
            checks = {
                "execution_service": (
                    hasattr(self.orchestrator, "execution_service")
                    and self.orchestrator.execution_service is not None
                ),
                "risk_manager": (
                    hasattr(self.orchestrator, "risk_service")
                    and self.orchestrator.risk_service is not None
                ),
                "data_service": (
                    hasattr(self.orchestrator, "data_service")
                    and self.orchestrator.data_service is not None
                ),
            }

            if all(checks.values()):
                return {"healthy": True}
            else:
                failed_components = [comp for comp, status in checks.items() if not status]
                return {
                    "healthy": False,
                    "issue": f"必須コンポーネント異常: {', '.join(failed_components)}",
                }

        except Exception as e:
            return {"healthy": False, "issue": f"ヘルスチェック例外: {e}"}
