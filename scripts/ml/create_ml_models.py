#!/usr/bin/env python3
"""
新システム用MLモデル作成スクリプト - Phase 41.8完了版（Strategy-Aware ML・完全実装）

Phase 41.8対応: 実戦略信号学習（訓練時と推論時の一貫性確保）
Phase 41対応: 戦略シグナル特徴量統合（50→55特徴量）
Phase 39対応: 実データ学習・閾値最適化・CV強化・SMOTE・Optuna最適化

機能:
- 55特徴量での LightGBM・XGBoost・RandomForest アンサンブル学習
- Phase 41.8: 実戦略信号学習 - 過去データから実際に5戦略を実行して学習データ生成
- Phase 41: Strategy-Aware ML - 戦略シグナル5特徴量追加
- Phase 40.6: Feature Engineering拡張 - 15→50特徴量
- Phase 39.1: 実データ学習（CSV読み込み・過去180日分15分足データ）
- Phase 39.2: 閾値最適化（0.3% → 0.5%）・3クラス分類（BUY/HOLD/SELL）
- Phase 39.3: TimeSeriesSplit n_splits=5・Early Stopping rounds=20・Train/Val/Test 70/15/15
- Phase 39.4: SMOTE oversampling・class_weight='balanced'
- Phase 39.5: Optunaハイパーパラメータ最適化（TPESampler）
- 新システム src/ 構造に対応
- models/production/ にモデル保存
- 実取引前の品質保証・性能検証

Phase 41.8完了成果: 55特徴量完全統合・訓練時と推論時の一貫性確保・実戦略信号学習

使用方法:
    # Phase 41.8: 55特徴量で学習（実戦略信号・推奨）
    python scripts/ml/create_ml_models.py --n-classes 3 --threshold 0.005 --optimize --n-trials 50 --verbose

    # 基本実行（Phase 39.1-39.4）
    python scripts/ml/create_ml_models.py [--dry-run] [--verbose]

    # Phase 39.4: SMOTE oversampling有効化
    python scripts/ml/create_ml_models.py --use-smote
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
    from src.core.logger import get_logger
    from src.data.data_pipeline import DataPipeline, DataRequest, TimeFrame
    from src.features.feature_generator import FeatureGenerator
    from src.ml.ensemble import ProductionEnsemble
    from src.strategies.base.strategy_manager import StrategyManager  # Phase 41.8
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
    ):
        """
        初期化（Phase 39.2-39.5対応）

        Args:
            config_path: 設定ファイルパス
            verbose: 詳細ログ出力
            target_threshold: ターゲット閾値（Phase 39.2）
            n_classes: クラス数 2 or 3（Phase 39.2）
            use_smote: SMOTEオーバーサンプリング使用（Phase 39.4）
            optimize: Optunaハイパーパラメータ最適化使用（Phase 39.5）
            n_trials: Optuna試行回数（Phase 39.5）
        """
        self.config_path = config_path
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
        self.optuna_dir = Path("models/optuna")  # Phase 39.5
        self.training_dir.mkdir(parents=True, exist_ok=True)
        self.production_dir.mkdir(parents=True, exist_ok=True)
        self.optuna_dir.mkdir(parents=True, exist_ok=True)  # Phase 39.5

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

        # MLモデル設定（Phase 39.3-39.4対応）
        self.models = {
            "lightgbm": LGBMClassifier(
                n_estimators=200,
                learning_rate=0.1,
                max_depth=8,
                num_leaves=31,
                random_state=42,
                verbose=-1,
                class_weight="balanced",  # Phase 39.4
            ),
            "xgboost": XGBClassifier(
                n_estimators=200,
                learning_rate=0.1,
                max_depth=8,
                random_state=42,
                eval_metric="logloss",
                verbosity=0,
                # Phase 39.4: scale_pos_weightは学習時に動的設定
            ),
            "random_forest": RandomForestClassifier(
                n_estimators=200,
                max_depth=12,
                random_state=42,
                n_jobs=-1,
                class_weight="balanced",  # Phase 39.4
            ),
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
        """学習用データ準備（Phase 50.3: 70特徴量・外部API・実戦略信号統合）"""
        self.logger.info(
            f"📊 Phase 50.3: 実データ学習開始（過去{days}日分・70特徴量・外部API・実戦略信号）"
        )

        try:
            # Phase 39.1: 実データ読み込み
            df = await self._load_real_historical_data(days)

            self.logger.info(f"✅ 基本データ取得完了: {len(df)}行")

            # Phase 50.3: 特徴量エンジニアリング（70特徴量: 62基本 + 8外部API）
            features_df = await self.feature_generator.generate_features(df)

            # Phase 50.3: 戦略シグナル特徴量を削除（後で実戦略信号で置き換える）
            # generate_features() は戦略シグナルを0.0で自動生成するが、Phase 41.8では実戦略信号を使用
            strategy_signal_cols = [
                col for col in features_df.columns if col.startswith("strategy_signal_")
            ]
            if strategy_signal_cols:
                features_df = features_df.drop(columns=strategy_signal_cols)
                self.logger.info(
                    f"✅ 戦略シグナル特徴量削除: {len(strategy_signal_cols)}個（実戦略信号で置き換え）"
                )

            # Phase 41.8: 実戦略信号生成（62→70特徴量 or 65→70特徴量）
            # Note: 過去データから実際に5戦略を実行し、本物の戦略信号を生成
            #       これにより訓練時と推論時の一貫性を確保
            strategy_signals_df = await self._generate_real_strategy_signals_for_training(df)

            # Phase 50.3: 基本特徴量 + 外部API特徴量 + 実戦略信号 = 70特徴量を結合
            features_df = pd.concat([features_df, strategy_signals_df], axis=1)

            # Phase 50.3: 特徴量整合性確保（70特徴量）
            features_df = self._ensure_feature_consistency(features_df)

            # ターゲット生成（Phase 39.2: 閾値・クラス数対応）
            target = self._generate_target(df, self.target_threshold, self.n_classes)

            # データ品質チェック
            features_df, target = self._clean_data(features_df, target)

            self.logger.info(
                f"✅ Phase 50.3 実データ準備完了: {len(features_df)}サンプル、"
                f"{len(features_df.columns)}特徴量（70特徴量: 62基本+8外部API・実戦略信号統合完了）"
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
        Phase 41.8: 実際の戦略信号を生成（過去データから）

        各時点で5戦略を実行し、本物の戦略信号を計算。
        これにより訓練時と推論時の一貫性を確保。

        Args:
            df: OHLCV価格データ

        Returns:
            pd.DataFrame: 戦略信号5列のDataFrame (index aligned with df)
        """
        self.logger.info("📊 Phase 41.8: 実戦略信号生成開始（過去データから5戦略実行）")

        # 戦略シグナル特徴量名
        strategy_names = [
            "ATRBased",
            "MochipoyAlert",
            "MultiTimeframe",
            "DonchianChannel",
            "ADXTrendStrength",
        ]

        # 結果格納用DataFrame
        strategy_signals = pd.DataFrame(index=df.index)

        try:
            # StrategyManager初期化
            strategy_manager = StrategyManager()
            self.logger.info("✅ StrategyManager初期化完了")

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
                    # DataPipeline更新
                    self.data_pipeline.set_backtest_data({"4h": current_data.copy()})

                    # 個別戦略信号取得
                    signals = strategy_manager.get_individual_strategy_signals({"4h": current_data})

                    # action × confidence を計算して格納
                    current_timestamp = current_data.index[-1]
                    for strategy_name in strategy_names:
                        if strategy_name in signals:
                            action = signals[strategy_name]["action"]
                            confidence = signals[strategy_name]["confidence"]

                            # action を数値化: buy=+1, hold=0, sell=-1
                            action_value = {"buy": 1.0, "hold": 0.0, "sell": -1.0}.get(action, 0.0)

                            # 戦略信号 = action × confidence
                            signal_value = action_value * confidence

                            strategy_signals.loc[
                                current_timestamp, f"strategy_signal_{strategy_name}"
                            ] = signal_value
                        else:
                            # 戦略信号が得られない場合は0
                            strategy_signals.loc[
                                current_timestamp, f"strategy_signal_{strategy_name}"
                            ] = 0.0

                except Exception as e:
                    # エラー時は0で埋める（学習継続）
                    self.logger.warning(f"⚠️ 時点{i}で戦略実行エラー: {e}, 0で埋めます")
                    for strategy_name in strategy_names:
                        strategy_signals.loc[
                            current_data.index[-1], f"strategy_signal_{strategy_name}"
                        ] = 0.0

                # 進捗表示（10%ごと）
                processed += 1
                if processed % max(1, total_points // 10) == 0:
                    progress = (processed / total_points) * 100
                    self.logger.info(
                        f"📊 Phase 41.8: 戦略信号生成進捗 {processed}/{total_points} ({progress:.1f}%)"
                    )

            # 欠損値を0で埋める
            strategy_signals.fillna(0.0, inplace=True)

            self.logger.info(
                f"✅ Phase 41.8: 実戦略信号生成完了 - {len(strategy_signals)}行 × 5戦略"
            )
            self.logger.info(
                f"📊 Phase 41.8: 戦略信号統計 - "
                f"非ゼロ率: {(strategy_signals != 0).sum().sum() / (len(strategy_signals) * 5) * 100:.1f}%"
            )

            return strategy_signals

        except Exception as e:
            self.logger.error(f"❌ Phase 41.8: 実戦略信号生成エラー: {e}")
            # エラー時はフォールバック（0埋め）
            self.logger.warning("⚠️ Phase 41.8: フォールバック - 戦略信号を0埋め")
            for strategy_name in strategy_names:
                strategy_signals[f"strategy_signal_{strategy_name}"] = 0.0
            return strategy_signals

    def _add_strategy_signal_features_for_training(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """
        Phase 41: ML学習用に戦略シグナル特徴量を追加（5個・0埋め）

        Deprecated: Phase 41.8で_generate_real_strategy_signals_for_training()に置き換え
        後方互換性のために残置

        Note:
            ML学習時は過去データから戦略を実行していないため、
            戦略シグナル特徴量を0埋めで追加します。
            実運用時には本物の戦略シグナルが使用されます。

        Returns:
            pd.DataFrame: 戦略シグナル特徴量が追加されたDataFrame
        """
        self.logger.info("📊 Phase 41: 戦略シグナル特徴量追加（ML学習用・0埋め）")

        # 戦略シグナル特徴量名
        strategy_signal_features = [
            "strategy_signal_ATRBased",
            "strategy_signal_MochipoyAlert",
            "strategy_signal_MultiTimeframe",
            "strategy_signal_DonchianChannel",
            "strategy_signal_ADXTrendStrength",
        ]

        # 0埋めで追加
        for feature_name in strategy_signal_features:
            features_df[feature_name] = 0.0

        self.logger.info(
            f"✅ Phase 41: 戦略シグナル特徴量5個追加完了 "
            f"({len(features_df.columns)}特徴量 - ML学習用0埋め)"
        )

        return features_df

    def _ensure_feature_consistency(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """特徴量整合性確保（Phase 41: 55特徴量対応）"""
        # 不足特徴量の0埋め
        for feature in self.expected_features:
            if feature not in features_df.columns:
                features_df[feature] = 0.0
                self.logger.warning(f"⚠️ 不足特徴量を0埋め: {feature}")

        # 特徴量のみ選択 - Phase 41: 55特徴量対応
        features_df = features_df[self.expected_features]

        expected_count = len(self.expected_features)
        if len(features_df.columns) != expected_count:
            self.logger.warning(f"⚠️ 特徴量数不一致: {len(features_df.columns)} != {expected_count}")

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
        """Phase 39.5: LightGBM最適化objective関数"""
        params = {
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "max_depth": trial.suggest_int("max_depth", 3, 15),
            "n_estimators": trial.suggest_int("n_estimators", 50, 300),
            "num_leaves": trial.suggest_int("num_leaves", 20, 100),
            "random_state": 42,
            "verbose": -1,
            "class_weight": "balanced",
        }

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
        """Phase 39.5: XGBoost最適化objective関数"""
        params = {
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "max_depth": trial.suggest_int("max_depth", 3, 15),
            "n_estimators": trial.suggest_int("n_estimators", 50, 300),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
            "random_state": 42,
            "eval_metric": "logloss",
            "verbosity": 0,
        }

        # scale_pos_weight動的設定（2クラス分類のみ）
        if self.n_classes == 2:
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

        # 結果保存
        try:
            results_file = self.optuna_dir / "phase39_5_results.json"
            with open(results_file, "w", encoding="utf-8") as f:
                json.dump(optimization_results, f, indent=2, ensure_ascii=False)
            self.logger.info(f"💾 最適化結果保存: {results_file}")
        except Exception as e:
            self.logger.error(f"❌ 最適化結果保存エラー: {e}")

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
                    # 本番用統合モデルはproductionフォルダに保存
                    model_file = self.production_dir / "production_ensemble.pkl"
                    with open(model_file, "wb") as f:
                        pickle.dump(model, f)

                    # Git情報取得
                    try:
                        git_commit = self._get_git_info()
                    except Exception:
                        git_commit = {"commit": "unknown", "branch": "unknown"}

                    # 本番用メタデータ保存（Phase 41.8完了: Strategy-Aware ML・実戦略信号学習）
                    production_metadata = {
                        "created_at": datetime.now().isoformat(),
                        "model_type": "ProductionEnsemble",
                        "model_file": str(model_file),
                        "version": "1.0.0",
                        "phase": "Phase 41.8",  # Phase 41.8完了: 実戦略信号学習
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
                        "notes": "Phase 41.8完了・実戦略信号学習（訓練時と推論時の一貫性確保）・55特徴量・閾値0.5%・TimeSeriesSplit n_splits=5・Early Stopping・SMOTE・Optuna最適化",
                    }

                    production_metadata_file = (
                        self.production_dir / "production_model_metadata.json"
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

        # 学習用メタデータ保存（Phase 41.8完了: Strategy-Aware ML・実戦略信号学習）
        training_metadata = {
            "created_at": datetime.now().isoformat(),
            "feature_names": training_results.get("feature_names", []),
            "training_samples": training_results.get("training_samples", 0),
            "model_metrics": training_results.get("results", {}),
            "model_files": saved_files,
            "config_path": self.config_path,
            "phase": "Phase 41.8",  # Phase 41.8完了: 実戦略信号学習
            "notes": "Phase 41.8完了・実戦略信号学習（訓練時と推論時の一貫性確保）・55特徴量・閾値0.5%・CV n_splits=5・Early Stopping・SMOTE・Optuna最適化・個別モデル学習結果",
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

                # サンプル予測テスト（DataFrameでsklearn警告回避）- Phase 40.6: 動的特徴量数対応
                n_features = len(self.expected_features)
                sample_features_array = np.random.random((5, n_features))
                sample_features = pd.DataFrame(
                    sample_features_array, columns=self.expected_features
                )
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

                    # predict_proba メソッド確認
                    if hasattr(model, "predict_proba"):
                        probabilities = model.predict_proba(sample_features)
                        if probabilities.shape == (5, 2):
                            self.logger.info("✅ predict_proba 確認成功")
                        else:
                            self.logger.error(f"❌ predict_proba 形状不正: {probabilities.shape}")
                            validation_passed = False

                    # get_model_info メソッド確認 - Phase 40.6: 動的特徴量数対応
                    if hasattr(model, "get_model_info"):
                        info = model.get_model_info()
                        expected_count = len(self.expected_features)
                        if info.get("n_features") == expected_count:
                            self.logger.info("✅ get_model_info 確認成功")
                        else:
                            self.logger.error(
                                f"❌ get_model_info 特徴量数不正: "
                                f"{info.get('n_features')} != {expected_count}"
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
        """既存モデルを自動アーカイブ（Phase 29: バージョン管理強化）."""
        try:
            production_model = self.production_dir / "production_ensemble.pkl"
            production_metadata = self.production_dir / "production_model_metadata.json"

            if production_model.exists():
                # アーカイブディレクトリ作成
                archive_dir = Path("models/archive")
                archive_dir.mkdir(exist_ok=True)

                # タイムスタンプ付きアーカイブ
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                archive_model = archive_dir / f"production_ensemble_{timestamp}.pkl"
                archive_metadata = archive_dir / f"production_model_metadata_{timestamp}.json"

                # ファイルコピー
                import shutil

                shutil.copy2(production_model, archive_model)
                if production_metadata.exists():
                    shutil.copy2(production_metadata, archive_metadata)

                self.logger.info(f"✅ 既存モデルアーカイブ完了: {archive_model}")
                return True
            else:
                self.logger.info("📂 既存モデルなし - アーカイブスキップ")
                return True

        except Exception as e:
            self.logger.error(f"❌ モデルアーカイブエラー: {e}")
            return False

    def run(self, dry_run: bool = False, days: int = 180) -> bool:
        """メイン実行処理."""
        try:
            self.logger.info("🚀 新システムMLモデル作成開始")

            # 0. 既存モデル自動アーカイブ（Phase 29: バージョン管理強化）
            if not dry_run:
                if not self._archive_existing_models():
                    self.logger.warning("⚠️ アーカイブ失敗 - 処理続行")

            # 1. 学習データ準備
            features, target = self.prepare_training_data(days)

            # 2. モデル学習
            training_results = self.train_models(features, target, dry_run)

            if dry_run:
                self.logger.info("🔍 ドライラン完了")
                return True

            # 3. モデル保存
            saved_files = self.save_models(training_results)

            # 4. 検証
            validation_passed = self.validate_models(saved_files)

            if validation_passed:
                self.logger.info("✅ MLモデル作成完了 - 実取引準備完了")
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

    args = parser.parse_args()

    # モデル作成実行（Phase 39.2-39.5対応）
    creator = NewSystemMLModelCreator(
        config_path=args.config,
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
