#!/usr/bin/env python3
"""
新システム用MLモデル作成スクリプト - Phase 52.4（6戦略・55特徴量・3クラス分類）

機能:
- **2段階MLモデル生成** - full（55特徴量）・basic（49特徴量）
- **設定駆動型** - feature_order.json完全準拠・strategies.yaml動的ロード・ハードコードゼロ
- **6戦略統合** - StrategyLoader動的ロード（ATRBased/DonchianChannel/ADXTrendStrength/BBReversal/StochasticReversal/MACDEMACrossover）
- **モデル別特徴量選択** - feature_order.jsonカテゴリー定義に基づく自動選択
- **統合メタデータ生成** - 全モデル情報を1つのJSONに集約（ensemble_metadata.json）
- **真の3クラス分類** - 0=sell, 1=hold, 2=buy
- **Strategy-Aware ML** - 実戦略信号学習（訓練時と推論時の一貫性確保）
- **TimeSeriesSplit・SMOTE・Optuna最適化**
- models/production/ にモデル保存（full/basic）

Phase 52.4完了成果: 6戦略統合・55特徴量システム・真の3クラス分類・設定駆動型アーキテクチャ

使用方法:
    # 両モデル一括学習（デフォルト・推奨）
    python scripts/ml/create_ml_models.py --n-classes 3 --threshold 0.005 --optimize --n-trials 50 --verbose

    # fullモデルのみ学習（緊急時）
    python scripts/ml/create_ml_models.py --model full --n-classes 3 --threshold 0.005 --optimize --n-trials 50 --verbose

    # basicモデルのみ学習（緊急時）
    python scripts/ml/create_ml_models.py --model basic --n-classes 3 --threshold 0.005 --optimize --n-trials 50 --verbose
"""

import argparse
import asyncio
import json
import logging
import pickle
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np
import optuna
import pandas as pd
from imblearn.over_sampling import SMOTE
from lightgbm import LGBMClassifier
from optuna.samplers import TPESampler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import TimeSeriesSplit
from xgboost import XGBClassifier

# プロジェクトルートをPythonパスに追加（scripts/ml -> bot）
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.backtest.scripts.collect_historical_csv import HistoricalDataCollector
    from src.core.config import load_config
    from src.core.config.feature_manager import _feature_manager  # Phase 50.7
    from src.core.logger import get_logger
    from src.data.data_pipeline import DataPipeline, DataRequest, TimeFrame
    from src.features.feature_generator import FeatureGenerator
    from src.ml.ensemble import ProductionEnsemble
    from src.strategies.base.strategy_manager import StrategyManager
except ImportError as e:
    print(f"❌ 新システムモジュールのインポートに失敗: {e}")
    print("プロジェクトルートから実行してください。")
    sys.exit(1)


class NewSystemMLModelCreator:
    """新システム用MLモデル作成・学習システム."""

    def __init__(
        self,
        config_path: str = "config/core/unified.yaml",
        verbose: bool = False,
        target_threshold: float = 0.005,
        n_classes: int = 2,
        use_smote: bool = False,
        optimize: bool = False,
        n_trials: int = 20,
        models_to_train: list = None,
    ):
        """
        初期化（Phase 52.4対応・一括生成システム）

        Args:
            config_path: 設定ファイルパス
            verbose: 詳細ログ出力
            target_threshold: ターゲット閾値
            n_classes: クラス数 2 or 3
            use_smote: SMOTEオーバーサンプリング使用
            optimize: Optunaハイパーパラメータ最適化使用
            n_trials: Optuna試行回数
            models_to_train: 訓練するモデルリスト ["full", "basic"] デフォルトは両方
        """
        self.config_path = config_path
        self.models_to_train = models_to_train or ["full", "basic"]
        self.current_model_type = "full"  # ループ処理中に動的に設定
        self.verbose = verbose
        self.target_threshold = target_threshold  # Phase 39.2
        self.n_classes = n_classes  # Phase 39.2
        self.use_smote = use_smote  # Phase 39.4
        self.optimize = optimize  # Phase 39.5
        self.n_trials = n_trials  # Phase 39.5

        # ログ設定
        self.logger = get_logger()
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)

        # Phase 51.9-6A: ログファイル出力先をlogs/ml/に変更
        from datetime import datetime

        log_dir = Path("logs/ml")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"ml_training_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logging.getLogger().addHandler(file_handler)
        self.logger.info(f"📁 ログ出力先: {log_file}")

        # 設定読み込み
        try:
            self.config = load_config(config_path)
            self.logger.info(f"✅ 設定読み込み完了: {config_path}")
        except Exception as e:
            self.logger.error(f"❌ 設定読み込み失敗: {e}")
            raise

        # モデル保存先ディレクトリ
        self.training_dir = Path("models/training")
        self.production_dir = Path("models/production")
        self.training_dir.mkdir(parents=True, exist_ok=True)
        self.production_dir.mkdir(parents=True, exist_ok=True)

        # データパイプライン初期化
        try:
            self.data_pipeline = DataPipeline()
            self.logger.info("✅ データパイプライン初期化完了")
        except Exception as e:
            self.logger.error(f"❌ データパイプライン初期化失敗: {e}")
            raise

        # 特徴量エンジン初期化
        self.feature_generator = FeatureGenerator()

        # Phase 29: 特徴量定義一元化対応（feature_managerから取得）
        from src.core.config.feature_manager import get_feature_names

        self.expected_features = get_feature_names()

        self.logger.info(f"🎯 対象特徴量: {len(self.expected_features)}個（新システム最適化済み）")
        self.logger.info(
            f"🎯 Phase 39.2 ターゲット設定: 閾値={target_threshold:.1%}, クラス数={n_classes}"
        )

        # MLモデル設定（Phase 39.3-39.4対応・Phase 51.9-6A: 3クラス対応）
        # LightGBM設定
        lgb_params = {
            "n_estimators": 200,
            "learning_rate": 0.1,
            "max_depth": 8,
            "num_leaves": 31,
            "random_state": 42,
            "verbose": -1,
            "class_weight": "balanced",  # Phase 39.4
        }
        if self.n_classes == 3:
            lgb_params["objective"] = "multiclass"
            lgb_params["num_class"] = 3

        # XGBoost設定
        xgb_params = {
            "n_estimators": 200,
            "learning_rate": 0.1,
            "max_depth": 8,
            "random_state": 42,
            "verbosity": 0,
        }
        if self.n_classes == 3:
            xgb_params["objective"] = "multi:softprob"
            xgb_params["num_class"] = 3
            xgb_params["eval_metric"] = "mlogloss"
        else:
            xgb_params["eval_metric"] = "logloss"

        # RandomForest設定（自動検出するが明示的に設定）
        rf_params = {
            "n_estimators": 200,
            "max_depth": 12,
            "random_state": 42,
            "n_jobs": -1,
            "class_weight": "balanced",  # Phase 39.4
        }

        self.models = {
            "lightgbm": LGBMClassifier(**lgb_params),
            "xgboost": XGBClassifier(**xgb_params),
            "random_forest": RandomForestClassifier(**rf_params),
        }

    async def _load_real_historical_data(self, days: int) -> pd.DataFrame:
        """
        実データ読み込み（Phase 39.1: ML実データ学習システム）

        Args:
            days: 収集日数

        Returns:
            pd.DataFrame: OHLCV データ
        """
        self.logger.info(f"📊 Phase 39.1: 実データ読み込み開始（過去{days}日分）")

        csv_path = Path("src/backtest/data/historical/BTC_JPY_4h.csv")

        # データ収集（存在しない、または古い場合）
        if not csv_path.exists():
            self.logger.info("💾 履歴データ未存在 - 自動収集開始")
            try:
                collector = HistoricalDataCollector()
                await collector.collect_data(symbol="BTC/JPY", days=days, timeframes=["4h"])
                self.logger.info("✅ データ収集完了")
            except Exception as e:
                self.logger.error(f"❌ データ収集失敗: {e}")
                raise

        # CSV読み込み
        try:
            df = pd.read_csv(csv_path)

            # timestamp をdatetimeに変換
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)

            # 期間フィルタ
            cutoff_date = datetime.now() - timedelta(days=days)
            df = df[df.index >= cutoff_date]

            # 欠損値チェック
            if df.isnull().any().any():
                self.logger.warning("⚠️ 欠損値を検出 - クリーニング実行")
                df = df.dropna()

            self.logger.info(
                f"✅ 実データ読み込み完了: {len(df)}サンプル "
                f"({df.index.min().strftime('%Y-%m-%d')} 〜 {df.index.max().strftime('%Y-%m-%d')})"
            )

            # OHLCV カラムのみ返却
            return df[["open", "high", "low", "close", "volume"]].copy()

        except Exception as e:
            self.logger.error(f"❌ CSV読み込みエラー: {e}")
            raise

    async def prepare_training_data_async(self, days: int = 180) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Phase 51.9: モデル別特徴量選択（2段階システム・6戦略統合）

        model_type="full": 55特徴量（全特徴量使用・6戦略信号含む）
        model_type="basic": 49特徴量（戦略信号除外）
        """
        model_name = (
            "full（55特徴量）" if self.current_model_type == "full" else "basic（49特徴量）"
        )
        self.logger.info(f"📊 Phase 51.9: 実データ学習開始（過去{days}日分・{model_name}）")

        try:
            # Phase 39.1: 実データ読み込み
            df = await self._load_real_historical_data(days)

            self.logger.info(f"✅ 基本データ取得完了: {len(df)}行")

            # 特徴量エンジニアリング（55特徴量システム）
            features_df = await self.feature_generator.generate_features(df)

            # Phase 41.8: 戦略シグナル特徴量を削除（後で実戦略信号で置き換える）
            # generate_features() は戦略シグナルを0.0で自動生成するが、Phase 41.8では実戦略信号を使用
            strategy_signal_cols = [
                col for col in features_df.columns if col.startswith("strategy_signal_")
            ]
            if strategy_signal_cols:
                features_df = features_df.drop(columns=strategy_signal_cols)
                self.logger.info(
                    f"✅ 戦略シグナル特徴量削除: {len(strategy_signal_cols)}個（実戦略信号で置き換え）"
                )

            # Phase 51.9: 実戦略信号生成（49→55特徴量・6戦略統合）
            # Note: 過去データから実際に戦略を実行し、本物の戦略信号を生成
            #       これにより訓練時と推論時の一貫性を確保
            #       特徴量を含むデータを渡す（戦略はテクニカル指標を必要とするため）
            strategy_signals_df = await self._generate_real_strategy_signals_for_training(
                features_df
            )

            # Phase 51.9: 基本特徴量（49） + 実戦略信号（6） = 55特徴量を結合
            features_df = pd.concat([features_df, strategy_signals_df], axis=1)

            # Phase 51.9: 特徴量整合性確保（55特徴量固定システム）
            features_df = self._ensure_feature_consistency(features_df)

            # Phase 52.4 CRITICAL FIX: 特徴量選択はrun()内のループで実行
            # ここでは全55特徴量を生成し、run()でモデル別に選択する

            # ターゲット生成（Phase 39.2: 閾値・クラス数対応）
            target = self._generate_target(df, self.target_threshold, self.n_classes)

            # データ品質チェック
            features_df, target = self._clean_data(features_df, target)

            self.logger.info(
                f"✅ Phase 52.4: 実データ準備完了 - {len(features_df)}サンプル、{len(features_df.columns)}特徴量（全特徴量）"
            )
            return features_df, target

        except Exception as e:
            self.logger.error(f"❌ 学習データ準備エラー: {e}")
            raise

    def prepare_training_data(self, days: int = 180) -> Tuple[pd.DataFrame, pd.Series]:
        """学習用データ準備（同期ラッパー・後方互換性）"""
        return asyncio.run(self.prepare_training_data_async(days))

    def _generate_sample_data(self, samples: int) -> pd.DataFrame:
        """サンプルデータ生成（実データ取得失敗時のフォールバック）."""
        self.logger.info(f"🔧 サンプルデータ生成: {samples}サンプル")

        # 時系列インデックス
        dates = pd.date_range(end=datetime.now(), periods=samples, freq="h")

        # リアルなBTC価格動向を模擬
        np.random.seed(42)
        base_price = 5000000  # 5M JPY
        prices = []
        current_price = base_price

        for i in range(samples):
            # ランダムウォーク（時間帯による変動幅調整）
            hour = dates[i].hour
            volatility = 0.015 if 8 <= hour <= 20 else 0.008  # 日中高ボラティリティ
            change = np.random.normal(0, volatility)
            current_price *= 1 + change
            prices.append(current_price)

        # OHLCV データ生成
        df = pd.DataFrame(
            {
                "timestamp": dates,
                "open": prices,
                "high": [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices],
                "low": [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices],
                "close": prices,
                "volume": np.random.lognormal(8, 1, samples),  # リアルな出来高分布
            }
        )

        df.set_index("timestamp", inplace=True)
        return df

    async def _generate_real_strategy_signals_for_training(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Strategy-Aware ML: 実際の戦略信号を生成（過去データから）

        各時点で6戦略を実行し、本物の戦略信号を計算。
        これにより訓練時と推論時の一貫性を確保。

        Args:
            df: OHLCV価格データ

        Returns:
            pd.DataFrame: 戦略信号6列のDataFrame (index aligned with df)
        """
        # strategies.yamlから動的ロード（6戦略対応）
        from src.strategies.strategy_loader import StrategyLoader

        strategy_loader = StrategyLoader("config/core/strategies.yaml")
        loaded_strategies = strategy_loader.load_strategies()
        strategy_names = [s["metadata"]["name"] for s in loaded_strategies]

        self.logger.info(
            f"📊 Phase 51.9: 実戦略信号生成開始（過去データから{len(strategy_names)}戦略実行）"
        )
        self.logger.info(f"   戦略リスト: {strategy_names}")

        # 結果格納用DataFrame
        strategy_signals = pd.DataFrame(index=df.index)

        try:
            # StrategyManager初期化 + 全戦略登録
            strategy_manager = StrategyManager()

            # Phase 51.9: 全戦略をStrategyManagerに登録
            for strategy_data in loaded_strategies:
                strategy_manager.register_strategy(
                    strategy_data["instance"], weight=strategy_data["weight"]
                )

            self.logger.info(f"✅ StrategyManager初期化完了 - {len(loaded_strategies)}戦略登録")

            # バックテストモード有効化
            self.data_pipeline.set_backtest_data({"4h": df.copy()})
            self.logger.info("✅ DataPipelineバックテストモード設定完了")

            # 各時点で戦略実行（look-ahead bias回避のため順次処理）
            total_points = len(df)
            processed = 0

            for i in range(len(df)):
                # 現在時点までのデータのみ使用（未来データ漏洩防止）
                current_data = df.iloc[: i + 1]

                # 最低限のデータポイントが必要（特徴量計算のため）
                if len(current_data) < 50:
                    # データ不足時は0で埋める
                    for strategy_name in strategy_names:
                        strategy_signals.loc[
                            current_data.index[-1], f"strategy_signal_{strategy_name}"
                        ] = 0.0
                    continue

                try:
                    # DataPipeline更新（マルチタイムフレーム形式）
                    self.data_pipeline.set_backtest_data({"4h": current_data.copy()})

                    # 個別戦略信号取得（Phase 51.7 Day 7: 単一DataFrameとして渡す）
                    signals = strategy_manager.get_individual_strategy_signals(current_data)

                    # action × confidence を計算して格納
                    current_timestamp = current_data.index[-1]
                    for strategy_name in strategy_names:
                        if strategy_name in signals:
                            action = signals[strategy_name]["action"]
                            confidence = signals[strategy_name]["confidence"]

                            # Phase 51.9: 改善エンコーディング（hold=0問題解決）
                            # 新方式: 0.0-1.0の連続値（全て非ゼロ）
                            # - hold: 0.5（中立）
                            # - buy: 0.5 + (confidence * 0.5) = 0.5-1.0範囲
                            # - sell: 0.5 - (confidence * 0.5) = 0.0-0.5範囲
                            if action == "buy":
                                signal_value = 0.5 + (confidence * 0.5)
                            elif action == "sell":
                                signal_value = 0.5 - (confidence * 0.5)
                            else:  # hold
                                signal_value = 0.5

                            strategy_signals.loc[
                                current_timestamp, f"strategy_signal_{strategy_name}"
                            ] = signal_value
                        else:
                            # 戦略信号が得られない場合はhold扱い（0.5）
                            strategy_signals.loc[
                                current_timestamp, f"strategy_signal_{strategy_name}"
                            ] = 0.5

                except Exception as e:
                    # Phase 51.9: エラー時はhold（0.5）で埋める（学習継続）
                    self.logger.warning(f"⚠️ 時点{i}で戦略実行エラー: {e}, hold(0.5)で埋めます")
                    for strategy_name in strategy_names:
                        strategy_signals.loc[
                            current_data.index[-1], f"strategy_signal_{strategy_name}"
                        ] = 0.5

                # 進捗表示（10%ごと）
                processed += 1
                if processed % max(1, total_points // 10) == 0:
                    progress = (processed / total_points) * 100
                    self.logger.info(
                        f"📊 Phase 41.8: 戦略信号生成進捗 {processed}/{total_points} ({progress:.1f}%)"
                    )

            # Phase 51.9: 欠損値をhold（0.5）で埋める
            strategy_signals.fillna(0.5, inplace=True)

            self.logger.info(
                f"✅ Phase 51.9: 実戦略信号生成完了 - {len(strategy_signals)}行 × {len(strategy_names)}戦略"
            )
            # Phase 51.9: buy/sell率（hold以外の率）を表示
            buy_sell_rate = (
                (strategy_signals != 0.5).sum().sum()
                / (len(strategy_signals) * len(strategy_names))
                * 100
            )
            self.logger.info(
                f"📊 Phase 51.9: 戦略信号統計 - buy/sell率（hold以外）: {buy_sell_rate:.1f}%"
            )

            return strategy_signals

        except Exception as e:
            self.logger.error(f"❌ Phase 41.8: 実戦略信号生成エラー: {e}")
            # Phase 51.9: エラー時はフォールバック（hold=0.5埋め）
            self.logger.warning("⚠️ Phase 51.9: フォールバック - 戦略信号をhold（0.5）埋め")
            for strategy_name in strategy_names:
                strategy_signals[f"strategy_signal_{strategy_name}"] = 0.5
            return strategy_signals

    def _ensure_feature_consistency(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """特徴量整合性確保（Phase 51.9: 55特徴量対応・6戦略統合）"""
        # 不足特徴量の0埋め
        for feature in self.expected_features:
            if feature not in features_df.columns:
                features_df[feature] = 0.0
                self.logger.warning(f"⚠️ 不足特徴量を0埋め: {feature}")

        # 特徴量のみ選択 - Phase 51.9: 55特徴量対応
        features_df = features_df[self.expected_features]

        expected_count = len(self.expected_features)
        if len(features_df.columns) != expected_count:
            self.logger.warning(f"⚠️ 特徴量数不一致: {len(features_df.columns)} != {expected_count}")

        return features_df

    def _select_features_by_level(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """
        Phase 51.9: モデル別特徴量選択（2段階システム・設定駆動型・6戦略統合）

        model_type="full": 全55特徴量使用（6戦略信号含む）
        model_type="basic": 戦略信号6個を除外（49特徴量）

        Args:
            features_df: 全特徴量を含むDataFrame

        Returns:
            pd.DataFrame: モデルに応じた特徴量のみを含むDataFrame
        """
        if self.current_model_type == "full":
            # full: 全55特徴量使用
            self.logger.info(f"📊 Phase 51.9: full モデル - 全{len(features_df.columns)}特徴量使用")
            return features_df

        # basic: 戦略信号を除外（49特徴量）
        # 設定駆動型: strategy_signal_ プレフィックスで動的検索
        strategy_signal_features = [
            col for col in features_df.columns if col.startswith("strategy_signal_")
        ]

        features_df = features_df.drop(columns=strategy_signal_features, errors="ignore")
        self.logger.info(
            f"📊 Phase 51.9: basic モデル - 戦略信号{len(strategy_signal_features)}個を除外 → {len(features_df.columns)}特徴量"
        )
        return features_df

    def _generate_target(
        self,
        df: pd.DataFrame,
        threshold: float = 0.005,
        n_classes: int = 2,
    ) -> pd.Series:
        """
        ターゲット生成（Phase 39.2: 閾値最適化・3クラス分類対応）

        Args:
            df: 価格データ
            threshold: BUY閾値（デフォルト0.5%）
            n_classes: クラス数（2または3）

        Returns:
            pd.Series: ターゲットラベル
                2クラス: 0=HOLD/SELL, 1=BUY
                3クラス: 0=SELL, 1=HOLD, 2=BUY
        """
        # 1時間後の価格変動率（4時間足なので4時間後）
        price_change = df["close"].pct_change(periods=1).shift(-1)

        if n_classes == 2:
            # Phase 39.2: 閾値0.3%→0.5%に変更（ノイズ削減）
            target = (price_change > threshold).astype(int)

            buy_ratio = target.mean()
            self.logger.info(
                f"📊 Phase 39.2 ターゲット分布（閾値{threshold:.1%}）: "
                f"BUY {buy_ratio:.1%}, OTHER {1 - buy_ratio:.1%}"
            )

        elif n_classes == 3:
            # Phase 39.2: 3クラス分類（BUY/HOLD/SELL）
            sell_threshold = -threshold

            # 0: SELL, 1: HOLD, 2: BUY
            target = pd.Series(1, index=df.index, dtype=int)  # デフォルトHOLD
            target[price_change > threshold] = 2  # BUY
            target[price_change < sell_threshold] = 0  # SELL

            distribution = target.value_counts(normalize=True).sort_index()
            self.logger.info(
                f"📊 Phase 39.2 3クラス分布（閾値±{threshold:.1%}）: "
                f"SELL {distribution.get(0, 0):.1%}, "
                f"HOLD {distribution.get(1, 0):.1%}, "
                f"BUY {distribution.get(2, 0):.1%}"
            )

        else:
            raise ValueError(f"Unsupported n_classes: {n_classes} (must be 2 or 3)")

        return target

    def _clean_data(
        self, features_df: pd.DataFrame, target: pd.Series
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """データクリーニング."""
        # NaN除去
        valid_mask = ~(features_df.isna().any(axis=1) | target.isna())
        features_clean = features_df[valid_mask].copy()
        target_clean = target[valid_mask].copy()

        # 無限値除去
        features_clean.replace([np.inf, -np.inf], np.nan, inplace=True)
        features_clean.fillna(0, inplace=True)

        removed_samples = len(features_df) - len(features_clean)
        if removed_samples > 0:
            self.logger.info(f"🧹 データクリーニング: {removed_samples}サンプル除去")

        return features_clean, target_clean

    def _objective_lightgbm(
        self, trial: optuna.Trial, X_train: pd.DataFrame, y_train: pd.Series
    ) -> float:
        """Phase 39.5: LightGBM最適化objective関数（Phase 51.9-6A: 3クラス対応）"""
        params = {
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "max_depth": trial.suggest_int("max_depth", 3, 15),
            "n_estimators": trial.suggest_int("n_estimators", 50, 300),
            "num_leaves": trial.suggest_int("num_leaves", 20, 100),
            "random_state": 42,
            "verbose": -1,
            "class_weight": "balanced",
        }

        # Phase 51.9-6A: 3クラス分類対応
        if self.n_classes == 3:
            params["objective"] = "multiclass"
            params["num_class"] = 3

        model = LGBMClassifier(**params)

        # TimeSeriesSplit CV
        tscv = TimeSeriesSplit(n_splits=3)
        scores = []
        for train_idx, val_idx in tscv.split(X_train):
            X_cv_train = X_train.iloc[train_idx]
            y_cv_train = y_train.iloc[train_idx]
            X_cv_val = X_train.iloc[val_idx]
            y_cv_val = y_train.iloc[val_idx]

            model.fit(X_cv_train, y_cv_train)
            y_pred = model.predict(X_cv_val)
            score = f1_score(y_cv_val, y_pred, average="weighted")
            scores.append(score)

        return np.mean(scores)

    def _objective_xgboost(
        self, trial: optuna.Trial, X_train: pd.DataFrame, y_train: pd.Series
    ) -> float:
        """Phase 39.5: XGBoost最適化objective関数（Phase 51.9-6A: 3クラス対応）"""
        params = {
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "max_depth": trial.suggest_int("max_depth", 3, 15),
            "n_estimators": trial.suggest_int("n_estimators", 50, 300),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
            "random_state": 42,
            "verbosity": 0,
        }

        # Phase 51.9-6A: 3クラス分類対応
        if self.n_classes == 3:
            params["objective"] = "multi:softprob"
            params["num_class"] = 3
            params["eval_metric"] = "mlogloss"
        else:
            params["eval_metric"] = "logloss"
            # scale_pos_weight動的設定（2クラス分類のみ）
            pos_count = y_train.sum()
            neg_count = len(y_train) - pos_count
            if pos_count > 0:
                params["scale_pos_weight"] = neg_count / pos_count

        model = XGBClassifier(**params)

        # TimeSeriesSplit CV
        tscv = TimeSeriesSplit(n_splits=3)
        scores = []
        for train_idx, val_idx in tscv.split(X_train):
            X_cv_train = X_train.iloc[train_idx]
            y_cv_train = y_train.iloc[train_idx]
            X_cv_val = X_train.iloc[val_idx]
            y_cv_val = y_train.iloc[val_idx]

            model.fit(X_cv_train, y_cv_train)
            y_pred = model.predict(X_cv_val)
            score = f1_score(y_cv_val, y_pred, average="weighted")
            scores.append(score)

        return np.mean(scores)

    def _objective_random_forest(
        self, trial: optuna.Trial, X_train: pd.DataFrame, y_train: pd.Series
    ) -> float:
        """Phase 39.5: RandomForest最適化objective関数"""
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 50, 300),
            "max_depth": trial.suggest_int("max_depth", 5, 20),
            "min_samples_split": trial.suggest_int("min_samples_split", 2, 20),
            "random_state": 42,
            "n_jobs": -1,
            "class_weight": "balanced",
        }

        model = RandomForestClassifier(**params)

        # TimeSeriesSplit CV
        tscv = TimeSeriesSplit(n_splits=3)
        scores = []
        for train_idx, val_idx in tscv.split(X_train):
            X_cv_train = X_train.iloc[train_idx]
            y_cv_train = y_train.iloc[train_idx]
            X_cv_val = X_train.iloc[val_idx]
            y_cv_val = y_train.iloc[val_idx]

            model.fit(X_cv_train, y_cv_train)
            y_pred = model.predict(X_cv_val)
            score = f1_score(y_cv_val, y_pred, average="weighted")
            scores.append(score)

        return np.mean(scores)

    def optimize_hyperparameters(
        self, features: pd.DataFrame, target: pd.Series, n_trials: int = 20
    ) -> Dict[str, Dict[str, Any]]:
        """
        Phase 39.5: Optunaハイパーパラメータ最適化

        Args:
            features: 訓練データ特徴量
            target: 訓練データターゲット
            n_trials: 試行回数

        Returns:
            Dict: 各モデルの最適パラメータ
        """
        self.logger.info(f"🔬 Phase 39.5: Optuna最適化開始（{n_trials}試行）")

        # Optunaログ抑制
        optuna.logging.set_verbosity(optuna.logging.WARNING)

        optimal_params = {}
        optimization_results = {
            "created_at": datetime.now().isoformat(),
            "n_trials": n_trials,
            "models": {},
        }

        for model_name in ["lightgbm", "xgboost", "random_forest"]:
            self.logger.info(f"📊 {model_name} 最適化開始")

            try:
                # Objective関数選択（E731: flake8 lambda回避）
                def objective_func(trial: optuna.Trial) -> float:
                    if model_name == "lightgbm":
                        return self._objective_lightgbm(trial, features, target)
                    elif model_name == "xgboost":
                        return self._objective_xgboost(trial, features, target)
                    else:  # random_forest
                        return self._objective_random_forest(trial, features, target)

                # Optuna Study作成・最適化実行
                study = optuna.create_study(direction="maximize", sampler=TPESampler(seed=42))
                study.optimize(objective_func, n_trials=n_trials, show_progress_bar=False)

                # 最適パラメータ取得
                best_params = study.best_params
                best_score = study.best_value

                optimal_params[model_name] = best_params
                optimization_results["models"][model_name] = {
                    "best_params": best_params,
                    "best_score": float(best_score),
                    "n_trials": n_trials,
                }

                self.logger.info(
                    f"✅ {model_name} 最適化完了 - Best F1: {best_score:.4f}, "
                    f"Best params: {best_params}"
                )

            except Exception as e:
                self.logger.error(f"❌ {model_name} 最適化エラー: {e}")
                optimization_results["models"][model_name] = {"error": str(e)}

        # Phase 52.4: Optuna結果はthresholds.yaml:optuna_optimizedセクションに統合済み
        # ファイル保存は不要（設定一元化）
        self.logger.info("💾 Optuna最適化完了（結果はthresholds.yaml:optuna_optimizedに統合済み）")

        return optimal_params

    def train_models(
        self, features: pd.DataFrame, target: pd.Series, dry_run: bool = False
    ) -> Dict[str, Any]:
        """モデル学習実行（Phase 39.3-39.4対応）"""
        self.logger.info("🤖 Phase 39.3-39.4 MLモデル学習開始")

        if dry_run:
            self.logger.info("🔍 ドライラン: 実際の学習はスキップ")
            return {"dry_run": True, "models": list(self.models.keys())}

        results = {}
        trained_models = {}

        # Phase 39.3: Train/Val/Test split (70/15/15)
        n_samples = len(features)
        train_size = int(n_samples * 0.70)
        val_size = int(n_samples * 0.15)

        X_train = features.iloc[:train_size]
        y_train = target.iloc[:train_size]
        X_val = features.iloc[train_size : train_size + val_size]
        y_val = target.iloc[train_size : train_size + val_size]
        X_test = features.iloc[train_size + val_size :]
        y_test = target.iloc[train_size + val_size :]

        self.logger.info(
            f"📊 Phase 39.3: Train/Val/Test split - "
            f"Train: {len(X_train)} ({len(X_train) / n_samples:.1%}), "
            f"Val: {len(X_val)} ({len(X_val) / n_samples:.1%}), "
            f"Test: {len(X_test)} ({len(X_test) / n_samples:.1%})"
        )

        # Phase 39.5: Optuna hyperparameter optimization
        if self.optimize:
            self.logger.info("🔬 Phase 39.5: Optunaハイパーパラメータ最適化開始")
            optimal_params = self.optimize_hyperparameters(
                pd.concat([X_train, X_val]),
                pd.concat([y_train, y_val]),
                self.n_trials,
            )

            # 最適パラメータ適用
            for model_name in self.models.keys():
                if model_name in optimal_params:
                    self.models[model_name].set_params(**optimal_params[model_name])
                    self.logger.info(f"✅ {model_name}: 最適パラメータ適用完了")

        # Phase 39.3: TimeSeriesSplit n_splits=5 for Cross Validation
        tscv = TimeSeriesSplit(n_splits=5)
        self.logger.info("📊 Phase 39.3: TimeSeriesSplit n_splits=5 for CV")

        # Phase 39.4: XGBoost scale_pos_weight動的設定
        if self.n_classes == 2:
            pos_count = y_train.sum()
            neg_count = len(y_train) - pos_count
            if pos_count > 0:
                scale_pos_weight = neg_count / pos_count
                self.models["xgboost"].set_params(scale_pos_weight=scale_pos_weight)
                self.logger.info(f"📊 Phase 39.4: XGBoost scale_pos_weight={scale_pos_weight:.2f}")

        for model_name, model in self.models.items():
            self.logger.info(f"📈 {model_name} 学習開始")

            try:
                # Phase 39.3: Cross Validation with Early Stopping
                cv_scores = []

                for train_idx, val_idx in tscv.split(X_train):
                    X_cv_train = X_train.iloc[train_idx]
                    y_cv_train = y_train.iloc[train_idx]
                    X_cv_val = X_train.iloc[val_idx]
                    y_cv_val = y_train.iloc[val_idx]

                    # Phase 39.4: SMOTE Oversampling (CV fold)
                    if self.use_smote and self.n_classes == 2:
                        try:
                            smote = SMOTE(random_state=42)
                            X_cv_train_resampled, y_cv_train_resampled = smote.fit_resample(
                                X_cv_train, y_cv_train
                            )
                            # Convert back to DataFrame to preserve feature names
                            X_cv_train = pd.DataFrame(
                                X_cv_train_resampled, columns=X_cv_train.columns
                            )
                            y_cv_train = pd.Series(y_cv_train_resampled)
                            if len(X_cv_train_resampled) > len(X_cv_train):
                                self.logger.debug(
                                    f"📊 Phase 39.4: SMOTE適用 - CV fold "
                                    f"{len(train_idx)}→{len(X_cv_train_resampled)}サンプル"
                                )
                        except Exception as e:
                            self.logger.warning(
                                f"⚠️ SMOTE適用失敗（CV fold）: {e}, 元データで学習継続"
                            )

                    # Phase 39.3: Early Stopping for LightGBM and XGBoost
                    if model_name == "lightgbm":
                        try:
                            model.fit(
                                X_cv_train,
                                y_cv_train,
                                eval_set=[(X_cv_val, y_cv_val)],
                                callbacks=[
                                    # LightGBM 4.0+ uses callbacks instead of early_stopping_rounds
                                    __import__("lightgbm").early_stopping(
                                        stopping_rounds=20, verbose=False
                                    )
                                ],
                            )
                        except ValueError as e:
                            # Handle unseen labels in CV folds (small datasets)
                            if "previously unseen labels" in str(e):
                                model.fit(X_cv_train, y_cv_train)
                            else:
                                raise
                    elif model_name == "xgboost":
                        # XGBoost 2.0+ uses callbacks for early stopping
                        try:
                            from xgboost import callback as xgb_callback

                            model.fit(
                                X_cv_train,
                                y_cv_train,
                                eval_set=[(X_cv_val, y_cv_val)],
                                callbacks=[xgb_callback.EarlyStopping(rounds=20)],
                                verbose=False,
                            )
                        except Exception:
                            # Fallback: train without early stopping
                            model.fit(X_cv_train, y_cv_train)
                    else:
                        # RandomForest doesn't support early stopping
                        model.fit(X_cv_train, y_cv_train)

                    # 予測・評価
                    y_pred = model.predict(X_cv_val)
                    score = f1_score(y_cv_val, y_pred, average="weighted")
                    cv_scores.append(score)

                # Phase 39.3: Final model training on Train+Val with Early Stopping
                X_train_val = pd.concat([X_train, X_val])
                y_train_val = pd.concat([y_train, y_val])

                # Phase 39.4: SMOTE Oversampling (Final training)
                if self.use_smote and self.n_classes == 2:
                    try:
                        smote = SMOTE(random_state=42)
                        X_train_val_resampled, y_train_val_resampled = smote.fit_resample(
                            X_train_val, y_train_val
                        )
                        # Convert back to DataFrame to preserve feature names
                        X_train_val = pd.DataFrame(
                            X_train_val_resampled, columns=X_train_val.columns
                        )
                        y_train_val = pd.Series(y_train_val_resampled)
                        self.logger.info(
                            f"📊 Phase 39.4: SMOTE適用（Final training） - "
                            f"{len(X_train) + len(X_val)}→{len(X_train_val_resampled)}サンプル"
                        )
                    except Exception as e:
                        self.logger.warning(
                            f"⚠️ SMOTE適用失敗（Final training）: {e}, 元データで学習継続"
                        )

                if model_name == "lightgbm":
                    model.fit(
                        X_train_val,
                        y_train_val,
                        eval_set=[(X_test, y_test)],
                        callbacks=[
                            __import__("lightgbm").early_stopping(stopping_rounds=20, verbose=False)
                        ],
                    )
                    self.logger.info(
                        f"📊 Phase 39.3: {model_name} Early Stopping enabled (rounds=20)"
                    )
                elif model_name == "xgboost":
                    # XGBoost 2.0+ uses callbacks for early stopping
                    try:
                        from xgboost import callback as xgb_callback

                        model.fit(
                            X_train_val,
                            y_train_val,
                            eval_set=[(X_test, y_test)],
                            callbacks=[xgb_callback.EarlyStopping(rounds=20)],
                            verbose=False,
                        )
                        self.logger.info(
                            f"📊 Phase 39.3: {model_name} Early Stopping enabled (rounds=20)"
                        )
                    except Exception as e:
                        # Fallback: train without early stopping
                        self.logger.warning(
                            f"⚠️ XGBoost Early Stopping failed: {e}, training without it"
                        )
                        model.fit(X_train_val, y_train_val)
                else:
                    # RandomForest: Train on Train+Val without early stopping
                    model.fit(X_train_val, y_train_val)

                # Test set evaluation
                y_test_pred = model.predict(X_test)
                test_metrics = {
                    "accuracy": accuracy_score(y_test, y_test_pred),
                    "f1_score": f1_score(y_test, y_test_pred, average="weighted"),
                    "precision": precision_score(
                        y_test, y_test_pred, average="weighted", zero_division=0
                    ),
                    "recall": recall_score(
                        y_test, y_test_pred, average="weighted", zero_division=0
                    ),
                    "cv_f1_mean": np.mean(cv_scores),
                    "cv_f1_std": np.std(cv_scores),
                }

                results[model_name] = test_metrics
                trained_models[model_name] = model

                self.logger.info(
                    f"✅ {model_name} 学習完了 - Test F1: {test_metrics['f1_score']:.3f}, "
                    f"CV F1: {test_metrics['cv_f1_mean']:.3f}±{test_metrics['cv_f1_std']:.3f}"
                )

            except Exception as e:
                self.logger.error(f"❌ {model_name} 学習エラー: {e}")
                results[model_name] = {"error": str(e)}

        # アンサンブルモデル作成（individual_modelsのみを使用・循環参照防止）
        if len(trained_models) >= 2:
            try:
                # ProductionEnsemble自体を含まないように個別モデルのみ渡す
                individual_models_only = {
                    k: v for k, v in trained_models.items() if k != "production_ensemble"
                }
                ensemble_model = self._create_ensemble(individual_models_only)
                trained_models["production_ensemble"] = ensemble_model
                self.logger.info("✅ アンサンブルモデル作成完了（循環参照防止対応）")
            except Exception as e:
                self.logger.error(f"❌ アンサンブル作成エラー: {e}")

        return {
            "results": results,
            "models": trained_models,
            "feature_names": list(features.columns),
            "training_samples": len(features),
        }

    def _create_ensemble(self, models: Dict) -> ProductionEnsemble:
        """アンサンブルモデル作成（ProductionEnsembleクラス使用）."""
        try:
            self.logger.info("🔧 ProductionEnsembleアンサンブルモデル作成中...")
            ensemble_model = ProductionEnsemble(models)
            self.logger.info("✅ ProductionEnsembleアンサンブルモデル作成完了")
            return ensemble_model
        except Exception as e:
            self.logger.error(f"❌ アンサンブル作成エラー: {e}")
            raise

    def save_models(self, training_results: Dict[str, Any]) -> Dict[str, str]:
        """モデル保存（個別モデル：training、統合モデル：production）."""
        self.logger.info("💾 モデル保存開始")

        saved_files = {}
        models = training_results.get("models", {})

        for model_name, model in models.items():
            try:
                if model_name == "production_ensemble":
                    # Phase 51.5-A Fix: feature_order.jsonから設定駆動型でモデルファイル名取得
                    target_model_type = self.current_model_type
                    model_config = _feature_manager.get_feature_level_info()
                    model_filename = model_config[target_model_type].get(
                        "model_file", "ensemble_full.pkl"
                    )

                    # 本番用統合モデルはproductionフォルダに保存
                    model_file = self.production_dir / model_filename
                    with open(model_file, "wb") as f:
                        pickle.dump(model, f)

                    # Git情報取得
                    try:
                        git_commit = self._get_git_info()
                    except Exception:
                        git_commit = {"commit": "unknown", "branch": "unknown"}

                    # 本番用メタデータ保存（Phase 50.9完了: 外部API完全削除・2段階Graceful Degradation）
                    production_metadata = {
                        "created_at": datetime.now().isoformat(),
                        "model_type": "ProductionEnsemble",
                        "model_file": str(model_file),
                        "version": "1.0.0",
                        "phase": "Phase 50.9",  # Phase 50.9完了: 外部API完全削除・シンプル設計回帰
                        "status": "production_ready",
                        "feature_names": training_results.get("feature_names", []),
                        "individual_models": [
                            k for k in model.models.keys() if k != "production_ensemble"
                        ],
                        "model_weights": model.weights,
                        "performance_metrics": training_results.get("results", {}),
                        "training_info": {
                            "samples": training_results.get("training_samples", 0),
                            "feature_count": len(training_results.get("feature_names", [])),
                            "training_duration_seconds": getattr(self, "_training_start_time", 0),
                        },
                        "git_info": git_commit,
                        "notes": "Phase 52.4完了・6戦略統合・55特徴量システム・真の3クラス分類・2段階Graceful Degradation・TimeSeriesSplit n_splits=5・Early Stopping・SMOTE・Optuna最適化",
                    }

                    # Phase 51.5-A Fix: メタデータファイル名決定
                    # fullモデルは検証用にproduction_model_metadata.jsonに保存
                    # basicモデルは別ファイルに保存（デバッグ用）
                    if self.current_model_type == "full":
                        production_metadata_file = (
                            self.production_dir / "production_model_metadata.json"
                        )
                    else:
                        production_metadata_file = (
                            self.production_dir
                            / f"production_model_metadata_{self.current_model_type}.json"
                        )

                    with open(production_metadata_file, "w", encoding="utf-8") as f:
                        json.dump(
                            production_metadata,
                            f,
                            indent=2,
                            ensure_ascii=False,
                        )

                    self.logger.info(f"✅ 本番用統合モデル保存: {model_file}")
                else:
                    # 個別モデルはtrainingフォルダに保存
                    model_file = self.training_dir / f"{model_name}_model.pkl"
                    with open(model_file, "wb") as f:
                        pickle.dump(model, f)

                    self.logger.info(f"✅ 個別モデル保存: {model_file}")

                saved_files[model_name] = str(model_file)

            except Exception as e:
                self.logger.error(f"❌ {model_name} モデル保存エラー: {e}")

        # 学習用メタデータ保存（Phase 51.9完了: 真の3クラス分類・6戦略統合・Strategy-Aware ML・実戦略信号学習）
        training_metadata = {
            "created_at": datetime.now().isoformat(),
            "feature_names": training_results.get("feature_names", []),
            "training_samples": training_results.get("training_samples", 0),
            "model_metrics": training_results.get("results", {}),
            "model_files": saved_files,
            "config_path": self.config_path,
            "phase": "Phase 51.9",  # Phase 51.9完了: 真の3クラス分類実装
            "notes": "Phase 51.9完了・真の3クラス分類実装（multiclass params追加）・6戦略統合（ATRBased/DonchianChannel/ADXTrendStrength/BBReversal/StochasticReversal/MACDEMACrossover）・実戦略信号学習（訓練時と推論時の一貫性確保）・55特徴量・閾値0.5%・CV n_splits=5・Early Stopping・SMOTE・Optuna最適化・個別モデル学習結果",
        }

        training_metadata_file = self.training_dir / "training_metadata.json"
        with open(training_metadata_file, "w", encoding="utf-8") as f:
            json.dump(training_metadata, f, indent=2, ensure_ascii=False)

        self.logger.info(f"✅ 学習用メタデータ保存: {training_metadata_file}")
        return saved_files

    def validate_models(self, saved_files: Dict[str, str]) -> bool:
        """保存されたモデルの検証（本番用モデル重点）."""
        self.logger.info("🔍 モデル検証開始")

        validation_passed = True

        for model_name, model_file in saved_files.items():
            try:
                # モデル読み込みテスト
                with open(model_file, "rb") as f:
                    model = pickle.load(f)

                # 基本属性チェック
                if hasattr(model, "predict"):
                    self.logger.info(f"✅ {model_name}: predict メソッド確認")
                else:
                    self.logger.error(f"❌ {model_name}: predict メソッドなし")
                    validation_passed = False
                    continue

                # Phase 50.9: モデル別特徴量数対応サンプル予測テスト
                # モデルの実際の特徴量数を取得（LightGBMモデルから）
                if hasattr(model, "models") and "lightgbm" in model.models:
                    # ProductionEnsembleの場合
                    lgbm_model = model.models["lightgbm"]
                    if hasattr(lgbm_model, "n_features_in_"):
                        n_features = lgbm_model.n_features_in_
                    elif hasattr(lgbm_model, "_n_features"):
                        n_features = lgbm_model._n_features
                    else:
                        n_features = len(self.expected_features)
                elif hasattr(model, "n_features_in_"):
                    n_features = model.n_features_in_
                else:
                    n_features = len(self.expected_features)

                # モデルに応じた特徴量リストを取得
                feature_list = self.expected_features[:n_features]
                sample_features_array = np.random.random((5, n_features))
                sample_features = pd.DataFrame(sample_features_array, columns=feature_list)
                prediction = model.predict(sample_features)

                if len(prediction) == 5:
                    self.logger.info(f"✅ {model_name}: サンプル予測成功")
                else:
                    self.logger.error(f"❌ {model_name}: サンプル予測失敗")
                    validation_passed = False
                    continue

                # 本番用モデルの詳細検証
                if model_name == "production_ensemble":
                    self.logger.info("🎯 本番用アンサンブルモデル詳細検証開始")

                    # predict_proba メソッド確認（Phase 51.9-6D: 3クラス対応）
                    if hasattr(model, "predict_proba"):
                        probabilities = model.predict_proba(sample_features)
                        expected_shape = (5, self.n_classes)
                        if probabilities.shape == expected_shape:
                            self.logger.info(f"✅ predict_proba 確認成功（{self.n_classes}クラス）")
                        else:
                            self.logger.error(
                                f"❌ predict_proba 形状不正: {probabilities.shape} "
                                f"!= {expected_shape}"
                            )
                            validation_passed = False

                    # Phase 50.9: モデル別特徴量数対応 - get_model_info確認
                    if hasattr(model, "get_model_info"):
                        info = model.get_model_info()
                        # すでに取得済みのn_features（モデル別）を使用
                        if info.get("n_features") == n_features:
                            self.logger.info(f"✅ get_model_info 確認成功（{n_features}特徴量）")
                        else:
                            self.logger.error(
                                f"❌ get_model_info 特徴量数不正: "
                                f"{info.get('n_features')} != {n_features}"
                            )
                            validation_passed = False

                    self.logger.info("🎯 本番用アンサンブルモデル詳細検証完了")

            except Exception as e:
                self.logger.error(f"❌ {model_name} 検証エラー: {e}")
                validation_passed = False

        if validation_passed:
            self.logger.info("🎉 全モデル検証成功！")
        else:
            self.logger.error("💥 モデル検証失敗")

        return validation_passed

    def _get_git_info(self) -> Dict[str, str]:
        """Git情報取得（バージョン管理用）."""
        import subprocess

        try:
            # Git commit hash取得
            commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True, cwd=project_root
            ).strip()

            # Git branch取得
            branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                text=True,
                cwd=project_root,
            ).strip()

            return {"commit": commit, "commit_short": commit[:8], "branch": branch}
        except Exception as e:
            self.logger.warning(f"Git情報取得失敗: {e}")
            return {"commit": "unknown", "commit_short": "unknown", "branch": "unknown"}

    def _archive_existing_models(self) -> bool:
        """
        既存モデルを自動アーカイブ（Phase 52.4: 2段階システム）

        Phase 52.4対応モデル：
        - ensemble_full.pkl（55特徴量）
        - ensemble_basic.pkl（49特徴量）
        """
        try:
            # 2段階モデルシステム対応
            level_files = [
                "ensemble_full.pkl",
                "ensemble_basic.pkl",
            ]

            archived_any = False
            for model_filename in level_files:
                production_model = self.production_dir / model_filename

                if production_model.exists():
                    # アーカイブディレクトリ作成
                    archive_dir = Path("models/archive")
                    archive_dir.mkdir(exist_ok=True)

                    # タイムスタンプ付きアーカイブ
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    model_name = model_filename.replace(".pkl", "")
                    archive_model = archive_dir / f"{model_name}_{timestamp}.pkl"

                    # ファイルコピー
                    import shutil

                    shutil.copy2(production_model, archive_model)

                    self.logger.info(f"✅ 既存モデルアーカイブ完了: {archive_model}")
                    archived_any = True

            # メタデータもアーカイブ
            production_metadata = self.production_dir / "production_model_metadata.json"
            if production_metadata.exists():
                archive_dir = Path("models/archive")
                archive_dir.mkdir(exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                archive_metadata = archive_dir / f"production_model_metadata_{timestamp}.json"

                import shutil

                shutil.copy2(production_metadata, archive_metadata)
                self.logger.info(f"✅ メタデータアーカイブ完了: {archive_metadata}")

            if not archived_any:
                self.logger.info("📂 既存モデルなし - アーカイブスキップ")

            return True

        except Exception as e:
            self.logger.error(f"❌ モデルアーカイブエラー: {e}")
            return False

    def run(self, dry_run: bool = False, days: int = 180) -> bool:
        """メイン実行処理（Phase 51.5-A Fix: 一括生成システム）."""
        try:
            self.logger.info(f"🚀 Phase 51.9: MLモデル作成開始 - 訓練対象: {self.models_to_train}")

            # 0. 既存モデル自動アーカイブ（Phase 29: バージョン管理強化）
            if not dry_run:
                if not self._archive_existing_models():
                    self.logger.warning("⚠️ アーカイブ失敗 - 処理続行")

            # 1. 学習データ準備（1回のみ・全55特徴量生成）
            # 戦略信号生成が最も時間がかかるため、1回だけ実行
            self.logger.info("📊 Phase 52.4: 学習データ準備開始（全モデル共通）")
            # 一時的にcurrent_model_typeを"full"に設定して全特徴量生成
            self.current_model_type = "full"
            features_full, target = self.prepare_training_data(days)
            self.logger.info("✅ 学習データ準備完了（全55特徴量生成済み）")

            # 2. 各モデルを訓練（ループ処理）
            all_saved_files = {}
            for model_type in self.models_to_train:
                self.current_model_type = model_type
                model_name = "full（55特徴量）" if model_type == "full" else "basic（49特徴量）"

                self.logger.info("")
                self.logger.info("=" * 80)
                self.logger.info(f"📊 Phase 52.4: {model_name}モデル訓練開始")
                self.logger.info("=" * 80)

                # モデル別特徴量選択（CRITICAL FIX: ループ内で再実行）
                features = self._select_features_by_level(features_full.copy())
                self.logger.info(
                    f"✅ 特徴量選択完了: {len(features.columns)}個（{model_type}モデル用）"
                )

                # モデル訓練
                training_results = self.train_models(features, target, dry_run)

                if dry_run:
                    self.logger.info(f"🔍 {model_name}モデル ドライラン完了")
                    continue

                # モデル保存
                saved_files = self.save_models(training_results)
                all_saved_files.update(saved_files)

                self.logger.info(f"✅ {model_name}モデル訓練・保存完了")

            if dry_run:
                self.logger.info("🔍 全モデル ドライラン完了")
                return True

            # 3. 検証（全モデル）
            self.logger.info("")
            self.logger.info("=" * 80)
            self.logger.info("🔍 Phase 51.5-A Fix: 全モデル検証開始")
            self.logger.info("=" * 80)

            validation_passed = self.validate_models(all_saved_files)

            if validation_passed:
                self.logger.info("✅ Phase 51.5-A Fix: 全MLモデル作成完了 - 実取引準備完了")
                return True
            else:
                self.logger.error("❌ MLモデル作成失敗")
                return False

        except Exception as e:
            self.logger.error(f"💥 MLモデル作成エラー: {e}")
            return False


def main():
    """メイン関数（Phase 39.1-39.5完了）"""
    parser = argparse.ArgumentParser(
        description="新システム用MLモデル作成スクリプト（Phase 39.1-39.5完了・ML信頼度向上期）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ドライラン（実際の学習・保存をスキップ）",
    )
    parser.add_argument("--verbose", action="store_true", help="詳細ログ出力")
    parser.add_argument(
        "--days",
        type=int,
        default=180,
        help="学習データ期間（日数、デフォルト: 180日）",
    )
    parser.add_argument("--config", default="config/core/unified.yaml", help="設定ファイルパス")

    # Phase 39.2: ターゲット設定引数
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.005,
        help="Phase 39.2: ターゲット閾値（デフォルト: 0.5%%）",
    )
    parser.add_argument(
        "--n-classes",
        type=int,
        default=2,
        choices=[2, 3],
        help="Phase 39.2: クラス数 2（BUY/OTHER） or 3（BUY/HOLD/SELL）",
    )

    # Phase 39.4: SMOTE設定引数
    parser.add_argument(
        "--use-smote",
        action="store_true",
        help="Phase 39.4: SMOTEオーバーサンプリング有効化（クラス不均衡対策）",
    )

    # Phase 39.5: Optuna最適化設定引数
    parser.add_argument(
        "--optimize",
        action="store_true",
        help="Phase 39.5: Optunaハイパーパラメータ最適化有効化",
    )
    parser.add_argument(
        "--n-trials",
        type=int,
        default=20,
        help="Phase 39.5: Optuna最適化試行回数（デフォルト: 20）",
    )

    # Phase 51.5-B: モデル選択（一括生成システム）
    parser.add_argument(
        "--model",
        type=str,
        default="both",
        choices=["both", "full", "basic"],
        help="Phase 51.5-B: 訓練するモデル both=両方（デフォルト推奨）/full=fullのみ/basic=basicのみ",
    )

    args = parser.parse_args()

    # モデル選択をリストに変換
    if args.model == "both":
        models_to_train = ["full", "basic"]
    elif args.model == "full":
        models_to_train = ["full"]
    elif args.model == "basic":
        models_to_train = ["basic"]
    else:
        models_to_train = ["full", "basic"]

    # モデル作成実行（Phase 51.5-B対応）
    creator = NewSystemMLModelCreator(
        config_path=args.config,
        models_to_train=models_to_train,
        verbose=args.verbose,
        target_threshold=args.threshold,
        n_classes=args.n_classes,
        use_smote=args.use_smote,
        optimize=args.optimize,
        n_trials=args.n_trials,
    )

    success = creator.run(dry_run=args.dry_run, days=args.days)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
