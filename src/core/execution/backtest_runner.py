"""
バックテストランナー - Phase 52.4

バックテストモード実行・戦略検証・パフォーマンス分析を担当。

機能:
- 戦略シグナル事前計算（look-ahead bias完全防止）
- TP/SL決済ロジック（高値・安値判定・リアル取引再現）
- TradeTracker統合（エントリー/エグジットペアリング・損益計算）
- matplotlib可視化（エクイティカーブ・損益分布・ドローダウン・価格チャート）
- CSV履歴データ読込（4h足・15m足）
- バックテスト高速化（特徴量事前計算・ML予測事前計算）

設計原則:
- Look-ahead bias完全防止
- リアル取引完全再現
- 正確な損益計算・パフォーマンス指標
"""

import asyncio
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd

from ..config import get_threshold
from ..services.market_regime_classifier import MarketRegimeClassifier
from .base_runner import BaseRunner


class BacktestRunner(BaseRunner):
    """バックテストモード実行クラス（Phase 49完了・完全改修版・信頼性100%達成）"""

    def __init__(self, orchestrator_ref, logger):
        """
        バックテストランナー初期化

        Args:
            orchestrator_ref: TradingOrchestratorへの参照
            logger: ログシステム
        """
        super().__init__(orchestrator_ref, logger)

        # バックテスト状態管理
        self.backtest_start = None
        self.backtest_end = None
        self.current_timestamp = None
        self.csv_data = {}  # タイムフレーム別CSVデータ
        self.precomputed_features = {}  # Phase 35: 事前計算済み特徴量（10倍高速化）
        self.precomputed_ml_predictions = {}  # Phase 35.4: 事前計算済みML予測（10倍高速化）
        self.data_index = 0  # 現在の処理位置
        self.total_data_points = 0

        # バックテスト設定（Phase 28完了・Phase 29最適化）
        self.symbol = get_threshold("backtest.symbol", "BTC/JPY")
        self.timeframes = get_threshold("backtest.timeframes", ["15m", "4h"])
        self.lookback_window = get_threshold(
            "backtest.lookback_window", 100
        )  # 各時点で過去N件のデータを供給

        # 統計情報
        self.cycle_count = 0
        self.processed_timestamps = []
        self.session_stats = {}

        # Phase 51.8-J4-G: レジーム分類器（エントリー時のregime記録用）
        self.regime_classifier = MarketRegimeClassifier()

        # Phase 52.2: DrawdownManager統合（設定ファイル制御）
        self._initialize_drawdown_manager()

    async def run(self) -> bool:
        """
        バックテストモード実行

        Returns:
            実行成功・失敗
        """
        try:
            self.logger.warning("📊 バックテストモード開始（Phase 35最適化: ログ=WARNING）")

            # 1. バックテスト期間設定
            await self._setup_backtest_period()

            # 2. CSVデータ読み込み
            await self._load_csv_data()

            # 3. 特徴量事前計算（Phase 35: 10倍高速化）
            await self._precompute_features()

            # 3.5. 戦略シグナル事前計算（Phase 49.1: バックテスト完全改修）
            # Phase 57.7: 軽量モード対応 - 設定ファイル/環境変数でスキップ可能
            # 優先順位: 環境変数 > thresholds.yaml
            env_skip = os.environ.get("BACKTEST_SKIP_STRATEGY_SIGNALS", "").lower()
            if env_skip:
                skip_strategy_signals = env_skip == "true"
            else:
                skip_strategy_signals = get_threshold("backtest.skip_strategy_signals", False)

            if not skip_strategy_signals:
                await self._precompute_strategy_signals()
            else:
                self.logger.warning("⚡ 軽量モード: 戦略シグナル事前計算スキップ (Phase 57.7)")

            # 3.6. ML予測事前計算（Phase 35.4: さらなる高速化）
            await self._precompute_ml_predictions()

            # 4. データ検証
            if not await self._validate_data():
                self.logger.error("❌ CSVデータが不十分です")
                return False

            # 5. 時系列バックテスト実行
            await self._run_time_series_backtest()

            # 6. 最終レポート生成
            await self._generate_final_backtest_report()

            self.logger.warning("✅ バックテスト実行完了", discord_notify=True)
            return True

        except Exception as e:
            self.logger.error(f"❌ バックテスト実行エラー: {e}", discord_notify=True)
            await self._save_error_report(str(e))
            raise

    async def _setup_backtest_period(self):
        """バックテスト期間設定"""
        # 優先順位: 環境変数 > 設定ファイル > デフォルト（Phase 55.3）
        env_days = os.environ.get("BACKTEST_DAYS")
        if env_days:
            backtest_days = int(env_days)
            self.logger.info(f"📅 環境変数BACKTEST_DAYSから期間取得: {backtest_days}日間")
        else:
            backtest_days = get_threshold("execution.backtest_period_days", 30)

        self.backtest_end = datetime.now()
        self.backtest_start = self.backtest_end - timedelta(days=backtest_days)

        self.logger.info(
            f"📅 バックテスト期間: {self.backtest_start.strftime('%Y-%m-%d')} "
            f"~ {self.backtest_end.strftime('%Y-%m-%d')} ({backtest_days}日間)"
        )

    async def _load_csv_data(self):
        """CSVデータ読み込み"""
        try:
            # CSV データローダーを使用
            from ...backtest.data.csv_data_loader import get_csv_loader

            csv_loader = get_csv_loader()

            # マルチタイムフレームデータ読み込み
            self.csv_data = csv_loader.load_multi_timeframe(
                symbol=self.symbol,
                timeframes=self.timeframes,
                start_date=self.backtest_start,
                end_date=self.backtest_end,
                limit=get_threshold("backtest.data_limit", 10000),  # 十分な量を確保
            )

            # 設定からメインタイムフレームを取得
            main_timeframe = self.timeframes[0] if self.timeframes else "15m"

            if (
                not self.csv_data
                or main_timeframe not in self.csv_data
                or self.csv_data[main_timeframe].empty
            ):
                raise ValueError(f"主要データ（{main_timeframe}）が不足: {self.symbol}")

            # データ統計
            self.total_data_points = len(self.csv_data[main_timeframe])

            # タイムフレーム別データ統計を動的に生成
            timeframe_stats = []
            for tf in self.timeframes:
                count = len(self.csv_data.get(tf, []))
                timeframe_stats.append(f"{tf}:{count}件")

            self.logger.warning(f"📈 CSVデータ読み込み完了: {', '.join(timeframe_stats)}")

            # Phase 40.5拡張: データサンプリング処理（Optuna最適化高速化）
            # Phase 57.7拡張: 環境変数優先対応（subprocess経由でのパラメータ注入）
            # 優先順位: 環境変数 > thresholds.yaml
            env_sampling = os.environ.get("BACKTEST_DATA_SAMPLING_RATIO", "")
            if env_sampling:
                try:
                    sampling_ratio = float(env_sampling)
                except ValueError:
                    sampling_ratio = get_threshold("backtest.data_sampling_ratio", 1.0)
            else:
                sampling_ratio = get_threshold("backtest.data_sampling_ratio", 1.0)

            if sampling_ratio < 1.0:
                self._apply_data_sampling(sampling_ratio)

        except Exception as e:
            self.logger.error(f"❌ CSVデータ読み込みエラー: {e}")
            raise

    def _apply_data_sampling(self, sampling_ratio: float) -> None:
        """
        データサンプリング処理（Phase 40.5拡張: Optuna最適化高速化）

        等間隔サンプリングを使用して時系列の連続性を保持しつつデータ量を削減。

        Args:
            sampling_ratio: サンプリング比率（0.0-1.0）
                例: 0.1 = 10%サンプリング、0.2 = 20%サンプリング

        効果:
            - 10%サンプリング: 実行時間1/10（予想）
            - 20%サンプリング: 実行時間1/5（予想）
        """
        if sampling_ratio >= 1.0:
            return  # サンプリング不要

        self.logger.warning(
            f"🔬 データサンプリング開始: {sampling_ratio * 100:.0f}% "
            "(Optuna最適化高速化・Phase 40.5)"
        )

        for timeframe in self.csv_data.keys():
            original_df = self.csv_data[timeframe]
            original_count = len(original_df)

            if original_count == 0:
                continue

            # 等間隔サンプリング（時系列連続性保持）
            step = max(1, int(1 / sampling_ratio))
            sampled_df = original_df.iloc[::step].copy()

            # 最後の行は必ず含める（最新データ確保）
            if original_df.index[-1] not in sampled_df.index:
                sampled_df = pd.concat([sampled_df, original_df.iloc[[-1]]])

            sampled_count = len(sampled_df)

            self.csv_data[timeframe] = sampled_df

            self.logger.warning(
                f"  {timeframe}: {original_count}件 → {sampled_count}件 "
                f"({sampled_count / original_count * 100:.1f}%)"
            )

        # メインタイムフレームのデータポイント数更新
        main_timeframe = self.timeframes[0] if self.timeframes else "15m"
        self.total_data_points = len(self.csv_data[main_timeframe])

    async def _precompute_features(self):
        """
        特徴量事前計算（Phase 35: 10倍高速化）

        全CSVデータに対して一度だけ特徴量を計算し、
        各サイクルではスライスのみ実行することで大幅高速化。

        最適化効果:
        - 17,271回の特徴量計算 → 1回（タイムフレーム毎）
        - 理論値: 17,271倍高速化
        - 実測予想: 20-30分 → 2-3分（10倍高速化）
        """
        try:
            import time

            from ...features.feature_generator import FeatureGenerator

            self.logger.warning("🚀 特徴量事前計算開始（Phase 35最適化）")
            start_time = time.time()

            feature_gen = FeatureGenerator()

            for timeframe, df in self.csv_data.items():
                if df.empty:
                    continue

                # Phase 35.2: 詳細ログ削除（高速化）
                # 未使用: tf_start = time.time()

                # 同期版特徴量生成（全データ一括計算）
                features_df = feature_gen.generate_features_sync(df)

                # Phase 49.1: 戦略シグナル特徴量は_precompute_strategy_signals()で別途計算
                # ここでは0.0で初期化のみ（後で上書きされる）
                # Phase 51.7 Day 7: 6戦略シグナル（設定駆動型・動的生成）
                from ...strategies.strategy_loader import StrategyLoader

                loader = StrategyLoader()
                strategies_data = loader.load_strategies()
                strategy_signal_features = [
                    f"strategy_signal_{s['metadata']['name']}" for s in strategies_data
                ]
                for col in strategy_signal_features:
                    if col not in features_df.columns:
                        features_df[col] = 0.0

                # 事前計算結果をキャッシュ
                self.precomputed_features[timeframe] = features_df

            elapsed = time.time() - start_time
            total_records = sum(len(df) for df in self.csv_data.values())
            self.logger.warning(
                f"✅ 特徴量事前計算完了: {total_records}件 "
                f"（{elapsed:.1f}秒, {total_records / elapsed:.0f}件/秒）",
                discord_notify=False,
            )

        except Exception as e:
            self.logger.error(f"❌ 特徴量事前計算エラー: {e}")
            raise

    async def _precompute_strategy_signals(self):
        """
        戦略シグナル事前計算（Phase 49.1: バックテスト完全改修）

        各タイムスタンプで過去データのみを使って5戦略を実行し、
        実戦略シグナル特徴量を生成することでライブモードと完全一致を実現。

        重要ポイント:
        - Look-ahead bias防止: df.iloc[:i+1]で過去データのみ使用
        - Phase 41.8 Strategy-Aware ML完全対応
        - 各タイムスタンプで特徴量生成+戦略実行が必要（処理時間増）

        最適化効果:
        - バックテスト精度: BUY偏重 → ライブモード完全一致
        - Strategy-Aware ML正常動作: 戦略シグナル0.0埋め → 実シグナル使用
        """
        try:
            import time

            from ...features.feature_generator import FeatureGenerator

            self.logger.warning("🎯 戦略シグナル事前計算開始（Phase 49.1: 実戦略実行）")
            start_time = time.time()

            # メインタイムフレームのみ処理（15m足）
            main_timeframe = self.timeframes[0] if self.timeframes else "15m"
            if main_timeframe not in self.csv_data:
                self.logger.warning(f"⚠️ メインタイムフレーム {main_timeframe} が存在しません")
                return

            main_df = self.csv_data[main_timeframe]
            if main_df.empty:
                self.logger.warning("⚠️ メインタイムフレームデータが空です")
                return

            feature_gen = FeatureGenerator()
            total_rows = len(main_df)

            # 戦略シグナル特徴量の初期化（Phase 51.7 Day 7: 6戦略・設定駆動型）
            from ...strategies.strategy_loader import StrategyLoader

            loader = StrategyLoader()
            strategies_data = loader.load_strategies()
            strategy_names = [s["metadata"]["name"] for s in strategies_data]
            strategy_signal_columns = {f"strategy_signal_{name}": [] for name in strategy_names}

            self.logger.warning(f"✅ {len(strategy_names)}戦略でバックテスト実行: {strategy_names}")

            # 進捗報告用
            progress_percentage = get_threshold("backtest.progress_report_percentage", 10)
            progress_interval = max(1, total_rows // progress_percentage)

            # 各タイムスタンプで過去データのみ使用して戦略実行
            for i in range(total_rows):
                # Phase 49.1: Look-ahead bias防止 - 過去データのみ使用
                historical_data = main_df.iloc[: i + 1].copy()

                # Phase 54.9: Bug #3修正 - DatetimeIndex強制保持（Bug #1/#2のトリガー排除）
                if not isinstance(historical_data.index, pd.DatetimeIndex):
                    if "timestamp" in historical_data.columns:
                        historical_data.index = pd.to_datetime(
                            historical_data["timestamp"], unit="ms"
                        )
                        historical_data = historical_data.drop(columns=["timestamp"])
                        self.logger.debug(f"📅 DatetimeIndex復元: {len(historical_data)}件")

                # 進捗報告
                if i % progress_interval == 0 and i > 0:
                    progress = (i / total_rows) * 100
                    elapsed = time.time() - start_time
                    eta = (elapsed / i) * (total_rows - i) if i > 0 else 0
                    self.logger.warning(
                        f"  進捗: {progress:.1f}% ({i}/{total_rows}) - "
                        f"経過: {elapsed:.1f}秒, 残り: {eta:.1f}秒"
                    )

                # データ不足時は0.0で埋める（最初の数行）
                min_data_rows = get_threshold("backtest.strategy_signal_min_data_rows", 20)
                if len(historical_data) < min_data_rows:
                    for col in strategy_signal_columns.keys():
                        strategy_signal_columns[col].append(0.0)
                    continue

                try:
                    # 1. 特徴量生成（過去データのみ）- Look-ahead bias防止
                    features_df = feature_gen.generate_features_sync(historical_data)
                    if features_df.empty or len(features_df) == 0:
                        for col in strategy_signal_columns.keys():
                            strategy_signal_columns[col].append(0.0)
                        continue

                    # 2. 全タイムフレーム特徴量準備（ライブモード一致）
                    # 戦略は特徴量DataFrame（全履歴）を期待している
                    all_features = {main_timeframe: features_df}

                    # 3. 個別戦略シグナル取得（Phase 41.8準拠）
                    # features_df（過去全体の特徴量）を渡すことでライブモードと一致
                    strategy_signals = (
                        self.orchestrator.strategy_service.get_individual_strategy_signals(
                            features_df, multi_timeframe_data=all_features
                        )
                    )

                    # 4. 戦略シグナルエンコーディング（action × confidence）
                    for strategy_name in strategy_names:
                        if strategy_name in strategy_signals:
                            signal = strategy_signals[strategy_name]
                            encoded_value = signal.get("encoded", 0.0)
                            strategy_signal_columns[f"strategy_signal_{strategy_name}"].append(
                                encoded_value
                            )
                        else:
                            # 戦略シグナル取得失敗時は0.0
                            strategy_signal_columns[f"strategy_signal_{strategy_name}"].append(0.0)

                except Exception as e:
                    # エラー時は0.0で埋める
                    self.logger.debug(f"⚠️ タイムスタンプ {i} で戦略シグナル計算エラー: {e}")
                    for col in strategy_signal_columns.keys():
                        strategy_signal_columns[col].append(0.0)

            # 5. precomputed_featuresに戦略シグナル特徴量を追加
            if main_timeframe in self.precomputed_features:
                features_df = self.precomputed_features[main_timeframe]
                for col_name, values in strategy_signal_columns.items():
                    if len(values) == len(features_df):
                        features_df[col_name] = values
                    else:
                        self.logger.warning(
                            f"⚠️ 戦略シグナル長さ不一致: {col_name} = {len(values)}, features = {len(features_df)}"
                        )

                self.precomputed_features[main_timeframe] = features_df

            elapsed = time.time() - start_time
            self.logger.warning(
                f"✅ 戦略シグナル事前計算完了: {total_rows}件 "
                f"（{elapsed:.1f}秒, {total_rows / elapsed:.1f}件/秒）",
                discord_notify=False,
            )

        except Exception as e:
            self.logger.error(f"❌ 戦略シグナル事前計算エラー: {e}")
            # エラー時は0.0埋めにフォールバック（既存動作維持）

    async def _precompute_ml_predictions(self):
        """
        ML予測事前計算（Phase 35.4: さらなる高速化）

        全特徴量データに対して一度だけML予測を実行し、
        各サイクルでは事前計算済み予測を使用することで大幅高速化。

        最適化効果:
        - 2,747回のML予測 → 1回のバッチ予測
        - 理論値: 2,747倍高速化
        - 実測予想: 15分 → 1-2分（10倍高速化）
        """
        try:
            import time

            import numpy as np

            from ...core.config.feature_manager import get_feature_names

            self.logger.warning("🤖 ML予測事前計算開始（Phase 35.4最適化）")
            start_time = time.time()

            # メインタイムフレームの特徴量に対してML予測
            main_timeframe = self.timeframes[0] if self.timeframes else "15m"
            if main_timeframe in self.precomputed_features:
                features_df = self.precomputed_features[main_timeframe]

                # Phase 40.6: 50特徴量抽出（動的取得）
                features_to_use = get_feature_names()
                available_features = [col for col in features_to_use if col in features_df.columns]

                if len(available_features) == len(features_to_use):
                    ml_features = features_df[available_features]

                    # バッチ予測実行
                    predictions_array = self.orchestrator.ml_service.predict(ml_features)
                    probabilities_array = self.orchestrator.ml_service.predict_proba(ml_features)

                    # 予測結果を保存（インデックス対応）
                    self.precomputed_ml_predictions[main_timeframe] = {
                        "predictions": predictions_array,
                        "probabilities": probabilities_array,
                    }

                    elapsed = time.time() - start_time
                    self.logger.warning(
                        f"✅ ML予測事前計算完了: {len(predictions_array)}件 "
                        f"（{elapsed:.1f}秒, {len(predictions_array) / elapsed:.0f}件/秒）",
                        discord_notify=False,
                    )
                else:
                    self.logger.warning(
                        f"⚠️ 特徴量不足: {len(available_features)}/{len(features_to_use)}個 - ML予測スキップ"
                    )

        except Exception as e:
            self.logger.error(f"❌ ML予測事前計算エラー: {e}")
            # エラー時は通常のML予測にフォールバック（処理継続）
            self.precomputed_ml_predictions = {}

    async def _validate_data(self) -> bool:
        """データ検証"""
        min_data_points = get_threshold("backtest.min_data_points", 50)

        if self.total_data_points < min_data_points:
            self.logger.warning(
                f"⚠️ データが不足: {self.total_data_points}件 " f"（最小{min_data_points}件必要）"
            )
            return False

        # データ品質チェック
        main_timeframe = self.timeframes[0] if self.timeframes else "15m"
        main_data = self.csv_data[main_timeframe]
        if main_data.isnull().any().any():
            self.logger.warning("⚠️ データに欠損値が含まれています")

        if not main_data.index.is_monotonic_increasing:
            self.logger.warning("⚠️ データが時系列順序になっていません")

        return True

    async def _run_time_series_backtest(self):
        """
        時系列バックテスト実行（Phase 35: 高速化最適化版）
        Phase 51.8-J4-B: 5分間隔実行対応（ライブモード一致化）
        Phase 51.8-J4-H: 完了保証（例外ハンドリング強化）
        """
        main_timeframe = self.timeframes[0] if self.timeframes else "15m"
        main_data = self.csv_data[main_timeframe]

        # Phase 51.8-J4-B: ライブモード実行間隔取得（デフォルト5分）
        live_interval_minutes = get_threshold("execution.interval_minutes", 5)
        # 15分足データから何回実行するか計算（15分 / 5分 = 3回）
        executions_per_candle_default = 15 // live_interval_minutes

        # Phase 51.8-J4-H: バックテスト高速化オーバーライド（1回実行で1/3の時間）
        # 注: Phase 51.8-K完了後、最終検証時は3回に戻すこと（ライブモード一致性確認）
        executions_per_candle = get_threshold(
            "backtest.inner_loop_count", executions_per_candle_default
        )

        # Phase 51.8-J4-H: ループ完了保証
        total_candles = len(main_data) - self.lookback_window
        processed_candles = 0

        # Phase 51.10-C: ETA計算用の開始時刻記録
        backtest_start_time = time.time()

        try:
            # データを時系列順で処理
            for i in range(self.lookback_window, len(main_data)):
                self.data_index = i
                candle_timestamp = main_data.index[i]
                processed_candles += 1

                # Phase 51.10-C: 進捗表示（ETA追加・間隔改善）
                progress_interval = get_threshold("backtest.progress_interval", 100)
                if i % progress_interval == 0:
                    progress = (i / len(main_data)) * 100

                    # ETA計算
                    elapsed_time = time.time() - backtest_start_time
                    if i > self.lookback_window:  # 最初の数サンプル後に計算開始
                        samples_processed = i - self.lookback_window
                        samples_remaining = len(main_data) - i
                        avg_time_per_sample = elapsed_time / samples_processed
                        eta_seconds = avg_time_per_sample * samples_remaining

                        # 残り時間を人間が読みやすい形式に変換
                        if eta_seconds < 60:
                            eta_str = f"{int(eta_seconds)}秒"
                        elif eta_seconds < 3600:
                            eta_str = f"{int(eta_seconds / 60)}分{int(eta_seconds % 60)}秒"
                        else:
                            hours = int(eta_seconds / 3600)
                            minutes = int((eta_seconds % 3600) / 60)
                            eta_str = f"{hours}時間{minutes}分"

                        self.logger.warning(
                            f"📊 バックテスト進行中: {progress:.1f}% "
                            f"({i}/{len(main_data)}) - {candle_timestamp.strftime('%Y-%m-%d %H:%M')} "
                            f"[残り時間: {eta_str}]"
                        )
                    else:
                        self.logger.warning(
                            f"📊 バックテスト進行中: {progress:.1f}% "
                            f"({i}/{len(main_data)}) - {candle_timestamp.strftime('%Y-%m-%d %H:%M')}"
                        )

                # 現在時点のデータを準備（Phase 35: 高速化版）
                await self._setup_current_market_data_fast(i)

                # Phase 51.8-J4-B: 15分足1本につき、5分間隔で複数回実行
                for exec_offset in range(executions_per_candle):
                    # 5分間隔のタイムスタンプ計算（0分、5分、10分）
                    self.current_timestamp = candle_timestamp + timedelta(
                        minutes=exec_offset * live_interval_minutes
                    )

                    # Phase 49.3: サイクル前のポジション数記録（エントリー検出用）
                    positions_before = set(
                        p["order_id"] for p in self.orchestrator.execution_service.virtual_positions
                    )

                    # Phase 52.2: DrawdownManager制限チェック（本番シミュレーション時のみ）
                    if self.drawdown_manager is not None:
                        if not self.drawdown_manager.check_trading_allowed(self.current_timestamp):
                            # 取引停止中（cooldown期間）
                            self.logger.debug(
                                "⏸️ Phase 52.2: DrawdownManager制限により取引スキップ "
                                f"({self.current_timestamp})"
                            )
                            continue  # 次の5分間隔へスキップ

                    # 取引サイクル実行（本番と同じロジック）
                    try:
                        await self.orchestrator.run_trading_cycle()
                        self.cycle_count += 1
                        self.processed_timestamps.append(self.current_timestamp)

                        # Phase 49.3: サイクル後の新規ポジションをTradeTrackerに記録
                        positions_after = self.orchestrator.execution_service.virtual_positions
                        for position in positions_after:
                            order_id = position.get("order_id")
                            if order_id not in positions_before:
                                # 新規エントリー検出
                                if (
                                    hasattr(self.orchestrator, "backtest_reporter")
                                    and self.orchestrator.backtest_reporter
                                ):
                                    # Phase 51.8-J4-G: レジーム情報取得（エントリー時点の市場状況）
                                    regime_str = "unknown"
                                    try:
                                        # 現在時点までの特徴量データを取得してregime分類
                                        current_features = self.precomputed_features.get(
                                            self.current_timestamp
                                        )
                                        if current_features is not None:
                                            # 現在時点のデータフレームを構築（最低限の必要カラム）
                                            regime = self.regime_classifier.classify(
                                                current_features
                                            )
                                            regime_str = regime.value
                                    except Exception as regime_error:
                                        self.logger.debug(
                                            f"⚠️ レジーム分類エラー（デフォルト'unknown'使用）: {regime_error}"
                                        )

                                    self.orchestrator.backtest_reporter.trade_tracker.record_entry(
                                        order_id=order_id,
                                        side=position.get("side"),
                                        amount=position.get("amount"),
                                        price=position.get("price"),
                                        timestamp=self.current_timestamp,
                                        strategy=position.get("strategy_name", "unknown"),
                                        regime=regime_str,  # Phase 51.8-J4-G: レジーム情報追加
                                    )

                    except Exception as e:
                        self.logger.warning(f"⚠️ 取引サイクルエラー ({self.current_timestamp}): {e}")
                        continue

                # Phase 49.2: TP/SLトリガーチェック・決済シミュレーション
                # Phase 51.8-J4-C: ローソク足内トリガー対応（high/low使用）
                try:
                    # ローソク足OHLC取得
                    candle = main_data.iloc[i]
                    close_price = candle.get("close", None)
                    high_price = candle.get("high", None)
                    low_price = candle.get("low", None)

                    if close_price is not None and high_price is not None and low_price is not None:
                        await self._check_tp_sl_triggers(
                            close_price, high_price, low_price, self.current_timestamp
                        )
                except Exception as e:
                    self.logger.debug(
                        f"⚠️ TP/SLトリガーチェックエラー ({self.current_timestamp}): {e}"
                    )

                # Phase 35.5: 進捗レポート保存を完全削除（バックテスト中は不要・I/Oオーバーヘッド削減）
                # report_interval = get_threshold("backtest.report_interval", 10000)
                # if i % report_interval == 0:
                #     await self._save_progress_report()

            # Phase 51.8-J4-H: ループ完了ログ
            self.logger.warning(
                f"✅ バックテストループ完了: {processed_candles}/{total_candles}本処理完了"
            )

        except Exception as e:
            # Phase 51.8-J4-H: 例外発生時のエラーログ
            self.logger.error(f"❌ バックテスト実行中にエラー発生: {e}")
            self.logger.error(f"処理済みローソク足: {processed_candles}/{total_candles}")
            import traceback

            self.logger.error(f"トレースバック:\n{traceback.format_exc()}")
            raise  # エラーを再送出して上位で処理

        finally:
            # Phase 51.8-J4-H: クリーンアップ保証（成功・失敗問わず実行）
            self.logger.warning("🔄 バックテスト後処理開始: 残ポジション決済・最終レポート生成")

            # 残ポジション強制決済
            await self._force_close_remaining_positions()

            # 最終レポート生成保証は run() メソッドで実施（既存ロジック維持）
            self.logger.warning(
                f"✅ バックテスト後処理完了: 処理済み={processed_candles}本、サイクル数={self.cycle_count}"
            )

    def _calculate_pnl(
        self, side: str, entry_price: float, exit_price: float, amount: float
    ) -> float:
        """
        損益計算（Phase 51.7 Phase 3-2: ライブモード一致化）

        Args:
            side: エントリーサイド（"buy" or "sell"）
            entry_price: エントリー価格
            exit_price: 決済価格
            amount: 取引量（BTC）

        Returns:
            損益（円）
        """
        if side == "buy":
            # ロングポジション決済: (決済価格 - エントリー価格) × 数量
            pnl = (exit_price - entry_price) * amount
        else:  # side == "sell"
            # ショートポジション決済: (エントリー価格 - 決済価格) × 数量
            pnl = (entry_price - exit_price) * amount

        return pnl

    async def _check_tp_sl_triggers(
        self, close_price: float, high_price: float, low_price: float, timestamp
    ):
        """
        TP/SLトリガーチェック・決済シミュレーション（Phase 49.2: バックテスト完全改修）
        （Phase 51.7 Phase 3-2: 仮想残高更新追加 - ライブモード一致化）
        （Phase 51.8-J4-C: ローソク足内トリガー対応 - high/low価格使用）

        ローソク足のOHLC価格とTP/SL価格を比較し、トリガー時に決済注文シミュレーションを実行。
        これによりバックテストでSELL注文が生成され、完全な取引サイクルを実現。

        Args:
            close_price: ローソク足の終値
            high_price: ローソク足の高値（TPチェック用）
            low_price: ローソク足の安値（SLチェック用）
            timestamp: 現在タイムスタンプ

        処理フロー:
            1. PositionTrackerから全ポジション取得
            2. 各ポジションのTP/SL価格とローソク足high/lowを比較
            3. TP/SLトリガー時に決済注文シミュレーション（両方トリガー時はSL優先）
            4. 仮想残高更新（Phase 51.7 Phase 3-2追加）
            5. ポジション削除
        """
        try:
            # 1. 全ポジション取得
            positions = (
                self.orchestrator.execution_service.virtual_positions.copy()
            )  # コピーして安全にイテレーション

            if not positions:
                return  # ポジションなし

            # 2. 各ポジションのTP/SLチェック
            for position in positions:
                order_id = position.get("order_id")
                side = position.get("side")  # "buy" or "sell"
                amount = position.get("amount")
                entry_price = position.get("price")
                take_profit = position.get("take_profit")
                stop_loss = position.get("stop_loss")
                strategy_name = position.get("strategy_name", "unknown")

                # TP/SL価格がない場合はスキップ
                if take_profit is None and stop_loss is None:
                    continue

                # 3. TP/SLトリガー判定（Phase 51.8-J4-C: ローソク足内トリガー対応）
                tp_triggered = False
                sl_triggered = False

                if side == "buy":
                    # ロングポジション: 高値でTPチェック・安値でSLチェック
                    if take_profit and high_price >= take_profit:
                        tp_triggered = True
                    if stop_loss and low_price <= stop_loss:
                        sl_triggered = True
                elif side == "sell":
                    # ショートポジション: 安値でTPチェック・高値でSLチェック
                    if take_profit and low_price <= take_profit:
                        tp_triggered = True
                    if stop_loss and high_price >= stop_loss:
                        sl_triggered = True

                # 両方トリガーされた場合はSL優先（保守的判定）
                if tp_triggered and sl_triggered:
                    tp_triggered = False  # SLを優先

                # 4. トリガー時に決済シミュレーション
                if tp_triggered or sl_triggered:
                    trigger_type = "TP" if tp_triggered else "SL"
                    exit_price = take_profit if tp_triggered else stop_loss

                    self.logger.info(
                        f"✅ Phase 49.2: {trigger_type}トリガー - "
                        f"{side} {amount} BTC @ {exit_price:.0f}円 "
                        f"(エントリー: {entry_price:.0f}円, 戦略: {strategy_name}) - {timestamp}"
                    )

                    # 5. 決済処理（Phase 51.7 Phase 3-3.5: バックテスト最適化）
                    # Phase 51.8-J4-D: 証拠金返還処理追加
                    # Phase 51.8-J4-E: 手数料シミュレーション追加
                    # バックテストモードではbitbank API呼び出し不要（残高更新とTradeTracker記録のみ）
                    try:
                        # Phase 51.8-J4-D: 証拠金返還（エントリー時に控除した証拠金を戻す）
                        # Phase 54.9: ハードコード削除（4→get_threshold）
                        from src.core.config.threshold_manager import get_threshold

                        leverage = get_threshold("backtest.leverage", 4)
                        entry_order_total = entry_price * amount
                        margin_to_return = entry_order_total / leverage  # エントリー時の証拠金
                        current_balance = self.orchestrator.execution_service.virtual_balance
                        self.orchestrator.execution_service.virtual_balance += margin_to_return

                        # Phase 51.8-J4-E: エグジット手数料シミュレーション（Maker: -0.02%リベート）
                        # Phase 54.9: ハードコード削除（-0.0002→get_threshold）
                        exit_order_total = exit_price * amount
                        exit_fee_rate = get_threshold(
                            "backtest.exit_fee_rate", -0.0002
                        )  # Maker手数料（指値注文）
                        exit_fee_amount = exit_order_total * exit_fee_rate  # 負の値（リベート）
                        self.orchestrator.execution_service.virtual_balance -= (
                            exit_fee_amount  # リベート加算
                        )

                        # Phase 51.7 Phase 3-2: 仮想残高更新（ライブモード一致化）
                        pnl = self._calculate_pnl(side, entry_price, exit_price, amount)
                        self.orchestrator.execution_service.virtual_balance += pnl
                        new_balance = self.orchestrator.execution_service.virtual_balance

                        # Phase 52.2: DrawdownManagerに取引結果記録（本番シミュレーション時のみ）
                        if self.drawdown_manager is not None:
                            self.drawdown_manager.update_balance(new_balance)
                            self.drawdown_manager.record_trade_result(
                                pnl, strategy_name, current_time=timestamp
                            )
                            self.logger.debug(
                                "📊 Phase 52.2: DrawdownManager更新 - "
                                f"残高: ¥{new_balance:,.0f}, PnL: {pnl:+.0f}円, 戦略: {strategy_name}, "
                                f"時刻: {timestamp}"
                            )

                        # Phase 51.8-J4-D再修正: WARNINGレベルでログ出力（バックテストモードで可視化）
                        self.logger.warning(
                            "💰 Phase 51.8-J4-D/E: 決済処理 - "
                            f"証拠金返還: +¥{margin_to_return:,.0f}, "
                            f"手数料リベート: +¥{abs(exit_fee_amount):,.2f}, "
                            f"{trigger_type}決済損益: {pnl:+.0f}円 → 残高: ¥{new_balance:,.0f} "
                            f"(前残高: ¥{current_balance:,.0f})"
                        )

                        # 6. ポジション削除（Phase 51.8-J4-A: ゴーストポジションバグ修正）
                        # position_trackerとexecutor.virtual_positionsの両方から削除
                        self.orchestrator.execution_service.position_tracker.remove_position(
                            order_id
                        )

                        # Phase 51.8-J4-A: executor.virtual_positionsからも削除（同期化）
                        try:
                            virtual_positions = (
                                self.orchestrator.execution_service.virtual_positions
                            )
                            virtual_positions[:] = [
                                pos for pos in virtual_positions if pos.get("order_id") != order_id
                            ]
                            self.logger.debug(
                                f"🗑️ Phase 51.8-J4-A: executor.virtual_positionsから削除 - {order_id}"
                            )
                        except Exception as sync_error:
                            self.logger.warning(
                                f"⚠️ Phase 51.8-J4-A: virtual_positions同期エラー: {sync_error}"
                            )

                        # Phase 49.3: TradeTrackerにエグジット記録
                        if (
                            hasattr(self.orchestrator, "backtest_reporter")
                            and self.orchestrator.backtest_reporter
                        ):
                            self.orchestrator.backtest_reporter.trade_tracker.record_exit(
                                order_id=order_id,
                                exit_price=exit_price,
                                exit_timestamp=timestamp,
                                exit_reason=f"{trigger_type}トリガー",
                            )

                        self.logger.info(
                            "✅ Phase 49.2: ポジション決済完了 - "
                            f"ID: {order_id}, {trigger_type}価格: {exit_price:.0f}円"
                        )

                    except Exception as e:
                        self.logger.warning(
                            f"⚠️ Phase 49.2: 決済シミュレーションエラー - {order_id}: {e}"
                        )

        except Exception as e:
            self.logger.error(f"❌ Phase 49.2: TP/SLトリガーチェックエラー: {e}")

    async def _force_close_remaining_positions(self):
        """
        Phase 51.8-J4-H: 残ポジション強制決済（バックテスト終了時）

        バックテスト終了時に残っている全ポジションを最終価格で強制決済。
        完全な統計記録のため、未決済ポジションをゼロにする。

        処理フロー:
            1. 全残ポジション取得
            2. 最終ローソク足の終値で決済
            3. 損益計算・仮想残高更新
            4. TradeTrackerに記録（exit_reason="バックテスト終了時の強制決済"）
            5. ポジション削除
        """
        try:
            # 1. 全ポジション取得
            positions = (
                self.orchestrator.execution_service.virtual_positions.copy()
            )  # コピーして安全にイテレーション

            if not positions:
                self.logger.warning("✅ Phase 51.8-J4-H: 残ポジションなし（全決済完了）")
                return

            # 最終ローソク足の終値取得
            main_timeframe = self.timeframes[0] if self.timeframes else "15m"
            main_data = self.csv_data[main_timeframe]
            last_candle = main_data.iloc[-1]
            final_price = last_candle.get("close")
            final_timestamp = main_data.index[-1]

            if final_price is None:
                self.logger.error("❌ Phase 51.8-J4-H: 最終価格取得失敗 - 強制決済中止")
                return

            self.logger.warning(
                "🔄 Phase 51.8-J4-H: 残ポジション強制決済開始 - "
                f"残{len(positions)}件 @ {final_price:.0f}円 ({final_timestamp})"
            )

            # 2. 各ポジションを強制決済
            closed_count = 0
            for position in positions:
                order_id = position.get("order_id")
                side = position.get("side")  # "buy" or "sell"
                amount = position.get("amount")
                entry_price = position.get("price")
                # 未使用: strategy_name = position.get("strategy_name", "unknown")

                try:
                    # 3. 決済処理（_check_tp_sl_triggersと同じロジック）
                    # Phase 51.8-J4-D: 証拠金返還処理
                    # Phase 54.9: ハードコード削除（4→get_threshold）
                    entry_order_total = entry_price * amount
                    leverage = get_threshold("backtest.leverage", 4)
                    margin_to_return = entry_order_total / leverage  # エントリー時の証拠金
                    # 未使用: current_balance = self.orchestrator.execution_service.virtual_balance
                    self.orchestrator.execution_service.virtual_balance += margin_to_return

                    # Phase 51.8-J4-E: エグジット手数料シミュレーション（Maker: -0.02%リベート）
                    # Phase 54.9: ハードコード削除（-0.0002→get_threshold）
                    exit_order_total = final_price * amount
                    exit_fee_rate = get_threshold(
                        "backtest.exit_fee_rate", -0.0002
                    )  # Maker手数料（指値注文）
                    exit_fee_amount = exit_order_total * exit_fee_rate  # 負の値（リベート）
                    self.orchestrator.execution_service.virtual_balance -= (
                        exit_fee_amount  # リベート加算
                    )

                    # 損益計算・仮想残高更新
                    pnl = self._calculate_pnl(side, entry_price, final_price, amount)
                    self.orchestrator.execution_service.virtual_balance += pnl
                    new_balance = self.orchestrator.execution_service.virtual_balance

                    self.logger.warning(
                        f"💰 Phase 51.8-J4-H: 強制決済 - {side} {amount} BTC "
                        f"(エントリー: {entry_price:.0f}円 → 決済: {final_price:.0f}円) "
                        f"証拠金返還: +¥{margin_to_return:,.0f}, "
                        f"手数料リベート: +¥{abs(exit_fee_amount):,.2f}, "
                        f"損益: {pnl:+.0f}円 → 残高: ¥{new_balance:,.0f}"
                    )

                    # 4. ポジション削除（Phase 51.8-J4-A: 同期化）
                    self.orchestrator.execution_service.position_tracker.remove_position(order_id)
                    virtual_positions = self.orchestrator.execution_service.virtual_positions
                    virtual_positions[:] = [
                        pos for pos in virtual_positions if pos.get("order_id") != order_id
                    ]

                    # 5. TradeTrackerに記録
                    if (
                        hasattr(self.orchestrator, "backtest_reporter")
                        and self.orchestrator.backtest_reporter
                    ):
                        self.orchestrator.backtest_reporter.trade_tracker.record_exit(
                            order_id=order_id,
                            exit_price=final_price,
                            exit_timestamp=final_timestamp,
                            exit_reason="バックテスト終了時の強制決済",
                        )

                    closed_count += 1

                except Exception as e:
                    self.logger.warning(f"⚠️ Phase 51.8-J4-H: 強制決済エラー - {order_id}: {e}")

            self.logger.warning(
                f"✅ Phase 51.8-J4-H: 残ポジション強制決済完了 - {closed_count}/{len(positions)}件決済"
            )

        except Exception as e:
            self.logger.error(f"❌ Phase 51.8-J4-H: 残ポジション強制決済エラー: {e}")

    async def _setup_current_market_data_fast(self, current_index: int):
        """
        現在時点の市場データを準備（Phase 35: 高速化版）

        最適化:
        - df[df.index <= timestamp]を排除（O(n)→O(1)）
        - インデックスベース直接スライシング使用
        - 100倍以上の高速化
        """
        # グローバル時刻をバックテスト時刻に設定
        await self._set_simulated_time(self.current_timestamp)

        # 各タイムフレームのデータを準備
        current_market_data = {}

        for timeframe, df in self.csv_data.items():
            if df.empty:
                continue

            # Phase 35: インデックスベース高速スライシング
            # メインタイムフレームと同じインデックス位置を使用
            end_idx = min(current_index + 1, len(df))
            start_idx = max(0, end_idx - self.lookback_window)

            # Phase 35.1: 事前計算済み特徴量を使用（10倍高速化）
            if timeframe in self.precomputed_features:
                # 事前計算済み特徴量から直接スライス（特徴量計算スキップ）
                current_market_data[timeframe] = self.precomputed_features[timeframe].iloc[
                    start_idx:end_idx
                ]
            else:
                # フォールバック: 事前計算なしの場合は元のデータ
                current_market_data[timeframe] = df.iloc[start_idx:end_idx]

        # データサービスにバックテスト用データを設定
        self.orchestrator.data_service.set_backtest_data(current_market_data)

        # Phase 35.4: 事前計算済みML予測を設定
        main_timeframe = self.timeframes[0] if self.timeframes else "15m"
        if main_timeframe in self.precomputed_ml_predictions and current_index < len(
            self.precomputed_ml_predictions[main_timeframe]["predictions"]
        ):
            import numpy as np

            predictions = self.precomputed_ml_predictions[main_timeframe]["predictions"]
            probabilities = self.precomputed_ml_predictions[main_timeframe]["probabilities"]

            # 現在インデックスの予測値を取得
            prediction = int(predictions[current_index])
            confidence = float(np.max(probabilities[current_index]))

            # data_serviceにML予測を設定
            self.orchestrator.data_service.set_backtest_ml_prediction(
                {"prediction": prediction, "confidence": confidence}
            )

    async def _setup_current_market_data(self):
        """現在時点の市場データを準備（旧版・後方互換性維持）"""
        # Phase 35で_setup_current_market_data_fast()に置き換え
        # 互換性のため残すが、使用されない
        await self._setup_current_market_data_fast(self.data_index)

    async def _set_simulated_time(self, timestamp: datetime):
        """シミュレーション時刻設定"""
        # グローバル時刻管理クラスがあれば設定
        # 現在は実装せず、将来的に時刻シミュレーションを追加
        pass

    async def _save_progress_report(self):
        """進捗レポート保存（Phase 35: JSON serializable修正）"""
        try:
            progress_stats = {
                "current_timestamp": (
                    self.current_timestamp.isoformat() if self.current_timestamp else None
                ),
                "progress_percentage": (
                    (self.data_index / self.total_data_points) * 100
                    if self.total_data_points > 0
                    else 0
                ),
                "cycles_completed": self.cycle_count,
                "processed_data_points": len(self.processed_timestamps),
            }

            # バックテストレポーターに進捗保存
            await self.orchestrator.backtest_reporter.save_progress_report(progress_stats)

        except Exception as e:
            self.logger.warning(f"⚠️ 進捗レポート保存エラー: {e}")

    async def _generate_final_backtest_report(self):
        """最終バックテストレポート生成（Phase 35: JSON serializable修正）"""
        try:
            # Phase 51.7: バックテスト終了時に全オープンポジションを強制決済
            await self._close_all_open_positions()

            # 最終統計収集（Phase 35: datetime→ISO文字列変換でJSON serializable化）
            final_stats = {
                "backtest_period": {
                    "start": self.backtest_start.isoformat() if self.backtest_start else None,
                    "end": self.backtest_end.isoformat() if self.backtest_end else None,
                    "duration_days": (self.backtest_end - self.backtest_start).days,
                },
                "data_processing": {
                    "total_data_points": self.total_data_points,
                    "processed_cycles": self.cycle_count,
                    "processed_timestamps": len(self.processed_timestamps),
                    "success_rate": (
                        len(self.processed_timestamps) / self.total_data_points * 100
                        if self.total_data_points > 0
                        else 0
                    ),
                },
                "timeframes": list(self.csv_data.keys()),
                "symbol": self.symbol,
            }

            # バックテストレポーター経由で詳細レポート生成
            # Phase 35: datetime→ISO文字列変換
            await self.orchestrator.backtest_reporter.generate_backtest_report(
                final_stats,
                self.backtest_start.isoformat() if self.backtest_start else None,
                self.backtest_end.isoformat() if self.backtest_end else None,
            )

        except Exception as e:
            self.logger.error(f"❌ 最終レポート生成エラー: {e}")

    async def _close_all_open_positions(self):
        """
        バックテスト終了時に全オープンポジションを強制決済（Phase 51.7追加）

        TP/SL決済が発生しなかったポジションを最終価格で決済し、
        TradeTrackerに記録することで統計計算を可能にする。
        """
        try:
            # 全オープンポジション取得
            open_positions = self.orchestrator.execution_service.virtual_positions.copy()

            if not open_positions:
                self.logger.warning("📊 オープンポジションなし - 決済不要")
                return

            self.logger.warning(
                f"📊 バックテスト終了 - {len(open_positions)}件のオープンポジションを強制決済"
            )

            # 最終価格取得
            main_timeframe = self.timeframes[0] if self.timeframes else "15m"
            if main_timeframe in self.csv_data:
                main_data = self.csv_data[main_timeframe]
                if not main_data.empty:
                    final_price = main_data.iloc[-1]["close"]
                    final_timestamp = main_data.index[-1]

                    # 各ポジションを決済
                    for position in open_positions:
                        order_id = position.get("order_id")

                        # TradeTrackerにエグジット記録
                        if (
                            hasattr(self.orchestrator, "backtest_reporter")
                            and self.orchestrator.backtest_reporter
                        ):
                            self.orchestrator.backtest_reporter.trade_tracker.record_exit(
                                order_id=order_id,
                                exit_price=final_price,
                                exit_timestamp=final_timestamp,
                                exit_reason="バックテスト終了時強制決済",
                            )

                        self.logger.info(
                            f"✅ 強制決済: {order_id} @ {final_price:.0f}円 (バックテスト終了)"
                        )

                    self.logger.warning(f"✅ {len(open_positions)}件のポジション強制決済完了")
                else:
                    self.logger.warning("⚠️ データが空のため強制決済スキップ")
            else:
                self.logger.warning(f"⚠️ メインタイムフレーム {main_timeframe} が見つかりません")

        except Exception as e:
            self.logger.error(f"❌ オープンポジション強制決済エラー: {e}")

    async def _save_error_report(self, error_message: str):
        """エラーレポート保存"""
        try:
            context = {
                "backtest_runner": "Phase22_BacktestRunner",
                "current_timestamp": self.current_timestamp,
                "data_index": self.data_index,
                "cycle_count": self.cycle_count,
            }

            await self.orchestrator.backtest_reporter.save_error_report(error_message, context)

        except Exception as e:
            self.logger.warning(f"⚠️ エラーレポート保存失敗: {e}")

    def _initialize_drawdown_manager(self):
        """
        Phase 52.2: DrawdownManager初期化（設定ファイル制御）

        features.yamlの設定に基づいてDrawdownManagerを初期化。
        enabled=false: 戦略評価モード（制限なし）
        enabled=true: 本番シミュレーションモード（-20%制限適用）
        """
        from ...core.config import get_features_config
        from ...trading.risk.drawdown import DrawdownManager

        # features.yamlから設定読み込み
        features_config = get_features_config()
        backtest_config = features_config.get("development", {}).get("backtest", {})
        drawdown_config = backtest_config.get("drawdown_limits", {})

        drawdown_enabled = drawdown_config.get("enabled", False)

        if drawdown_enabled:
            # 本番シミュレーションモード: DrawdownManager有効化
            max_drawdown_ratio = drawdown_config.get("max_drawdown_ratio", 0.2)
            consecutive_loss_limit = drawdown_config.get("consecutive_loss_limit", 8)
            cooldown_hours = drawdown_config.get("cooldown_hours", 6)

            self.drawdown_manager = DrawdownManager(
                max_drawdown_ratio=max_drawdown_ratio,
                consecutive_loss_limit=consecutive_loss_limit,
                cooldown_hours=cooldown_hours,
                mode="backtest",  # バックテストモード（状態永続化は無効）
            )

            # 初期残高設定（unified.yamlから取得）
            initial_balance = get_threshold("mode_balances.backtest.initial_balance", 100000.0)
            self.drawdown_manager.initialize_balance(initial_balance)

            self.logger.warning(
                "✅ DrawdownManager有効化（本番シミュレーションモード）: "
                f"DD制限={max_drawdown_ratio * 100:.0f}%, "
                f"連敗制限={consecutive_loss_limit}回, "
                f"クールダウン={cooldown_hours}時間"
            )
        else:
            # 戦略評価モード: DrawdownManager無効化
            self.drawdown_manager = None
            self.logger.warning("ℹ️ DrawdownManager無効化（戦略評価モード・制限なし）")
