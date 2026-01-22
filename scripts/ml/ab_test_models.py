#!/usr/bin/env python3
"""
Phase 60.6 A/Bテスト用モデル学習スクリプト

Phase 60.5でのMLモデル性能低下の原因を特定するため、
各パターンのモデルを学習し、信頼度分布を比較する。

パターン:
- A: 重み固定 40/40/20（動的計算無効化）
- B: シード統一 42/42/42
- C: A+B両方適用
- D: Optuna無効 + 60.4パラメータ流用

使用方法:
    # パターンA: 重み固定
    python scripts/ml/ab_test_models.py --pattern A --days 180

    # パターンB: シード統一
    python scripts/ml/ab_test_models.py --pattern B --days 180

    # パターンC: 両方
    python scripts/ml/ab_test_models.py --pattern C --days 180

    # パターンD: Optuna無効
    python scripts/ml/ab_test_models.py --pattern D --days 180

    # 全パターン評価
    python scripts/ml/ab_test_models.py --evaluate-all

    # 特定モデルの信頼度評価
    python scripts/ml/ab_test_models.py --evaluate models/ab_test/pattern_A/ensemble_full.pkl
"""

import argparse
import asyncio
import json
import logging
import pickle
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score
from sklearn.model_selection import TimeSeriesSplit
from xgboost import XGBClassifier

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.backtest.scripts.collect_historical_csv import HistoricalDataCollector
    from src.core.config import load_config
    from src.core.config.feature_manager import _feature_manager, get_feature_names
    from src.core.logger import get_logger
    from src.data.data_pipeline import DataPipeline
    from src.features.feature_generator import FeatureGenerator
    from src.ml.ensemble import ProductionEnsemble
    from src.strategies.base.strategy_manager import StrategyManager
    from src.strategies.strategy_loader import StrategyLoader
except ImportError as e:
    print(f"Import error: {e}")
    print("Run from project root.")
    sys.exit(1)


# Phase 60.4のハイパーパラメータ（アーカイブから取得）
PHASE_60_4_PARAMS = {
    "lightgbm": {
        "n_estimators": 200,
        "learning_rate": 0.1,
        "max_depth": 8,
        "num_leaves": 31,
        "feature_fraction": 0.9,  # 60.4: 0.9
        "bagging_fraction": 0.8,
        "bagging_freq": 5,
    },
    "xgboost": {
        "n_estimators": 200,
        "learning_rate": 0.1,
        "max_depth": 8,
        "subsample": 0.8,
        "colsample_bytree": 0.8,  # 60.4: 0.8
    },
    "random_forest": {
        "n_estimators": 200,
        "max_depth": 12,
        "max_features": "sqrt",
    },
}


class ABTestModelCreator:
    """A/Bテスト用モデル作成クラス"""

    def __init__(
        self,
        pattern: str,
        verbose: bool = False,
        days: int = 180,
        n_trials: int = 50,
    ):
        """
        初期化

        Args:
            pattern: テストパターン (A/B/C/D)
            verbose: 詳細ログ出力
            days: 学習データ日数
            n_trials: Optuna試行回数（パターンDでは無視）
        """
        self.pattern = pattern.upper()
        self.verbose = verbose
        self.days = days
        self.n_trials = n_trials
        self.n_classes = 3
        self.target_threshold = 0.0005

        # ログ設定
        self.logger = get_logger()
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)

        # ログファイル
        log_dir = Path("logs/ml")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"ab_test_{pattern}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logging.getLogger().addHandler(file_handler)
        self.logger.info(f"Log file: {log_file}")

        # 設定
        self.config = load_config("config/core/unified.yaml")

        # 出力ディレクトリ
        self.output_dir = Path(f"models/ab_test/pattern_{pattern}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # データパイプライン
        self.data_pipeline = DataPipeline()
        self.feature_generator = FeatureGenerator()
        self.expected_features = get_feature_names()

        self.logger.info(f"Pattern {pattern} initialized")
        self._log_pattern_config()

    def _log_pattern_config(self):
        """パターン設定をログ出力"""
        config = self._get_pattern_config()
        self.logger.info("=" * 60)
        self.logger.info(f"Pattern {self.pattern} Configuration:")
        self.logger.info(f"  - Fixed weights: {config['fixed_weights']}")
        self.logger.info(f"  - Unified seeds: {config['unified_seeds']}")
        self.logger.info(f"  - Use Optuna: {config['use_optuna']}")
        self.logger.info(
            f"  - Seeds: LGB={config['seeds']['lgb']}, XGB={config['seeds']['xgb']}, RF={config['seeds']['rf']}"
        )
        if config["fixed_weights"]:
            self.logger.info(f"  - Weights: {config['weights']}")
        self.logger.info("=" * 60)

    def _get_pattern_config(self) -> Dict[str, Any]:
        """パターン別設定を取得"""
        if self.pattern == "A":
            # パターンA: 重み固定 40/40/20
            return {
                "fixed_weights": True,
                "unified_seeds": False,
                "use_optuna": True,
                "seeds": {"lgb": 42, "xgb": 123, "rf": 456},  # 60.5のまま
                "weights": {"lightgbm": 0.4, "xgboost": 0.4, "random_forest": 0.2},
                "feature_fraction": 0.7,  # 60.5
                "colsample_bytree": 0.7,  # 60.5
            }
        elif self.pattern == "B":
            # パターンB: シード統一 42/42/42
            return {
                "fixed_weights": False,
                "unified_seeds": True,
                "use_optuna": True,
                "seeds": {"lgb": 42, "xgb": 42, "rf": 42},  # 統一
                "weights": None,  # 動的計算
                "feature_fraction": 0.7,  # 60.5
                "colsample_bytree": 0.7,  # 60.5
            }
        elif self.pattern == "C":
            # パターンC: A+B両方
            return {
                "fixed_weights": True,
                "unified_seeds": True,
                "use_optuna": True,
                "seeds": {"lgb": 42, "xgb": 42, "rf": 42},  # 統一
                "weights": {"lightgbm": 0.4, "xgboost": 0.4, "random_forest": 0.2},
                "feature_fraction": 0.7,  # 60.5
                "colsample_bytree": 0.7,  # 60.5
            }
        elif self.pattern == "D":
            # パターンD: Optuna無効 + 60.4パラメータ
            return {
                "fixed_weights": True,
                "unified_seeds": True,
                "use_optuna": False,  # Optuna無効
                "seeds": {"lgb": 42, "xgb": 42, "rf": 42},  # 統一
                "weights": {"lightgbm": 0.4, "xgboost": 0.4, "random_forest": 0.2},
                "feature_fraction": 0.9,  # 60.4
                "colsample_bytree": 0.8,  # 60.4
            }
        else:
            raise ValueError(f"Unknown pattern: {self.pattern}")

    def _create_models(self) -> Dict[str, Any]:
        """パターン別モデルインスタンス作成"""
        config = self._get_pattern_config()

        # LightGBM
        lgb_params = {
            "n_estimators": 200,
            "learning_rate": 0.1,
            "max_depth": 8,
            "num_leaves": 31,
            "random_state": config["seeds"]["lgb"],
            "verbose": -1,
            "class_weight": "balanced",
            "feature_fraction": config["feature_fraction"],
            "bagging_fraction": 0.8,
            "bagging_freq": 5,
            "objective": "multiclass",
            "num_class": 3,
        }

        # XGBoost
        xgb_params = {
            "n_estimators": 200,
            "learning_rate": 0.1,
            "max_depth": 8,
            "random_state": config["seeds"]["xgb"],
            "verbosity": 0,
            "subsample": 0.8,
            "colsample_bytree": config["colsample_bytree"],
            "objective": "multi:softprob",
            "num_class": 3,
            "eval_metric": "mlogloss",
        }

        # RandomForest
        rf_params = {
            "n_estimators": 200,
            "max_depth": 12,
            "random_state": config["seeds"]["rf"],
            "n_jobs": 1,
            "class_weight": "balanced",
            "max_features": "sqrt",
        }

        return {
            "lightgbm": LGBMClassifier(**lgb_params),
            "xgboost": XGBClassifier(**xgb_params),
            "random_forest": RandomForestClassifier(**rf_params),
        }

    async def _load_data(self) -> pd.DataFrame:
        """データ読み込み"""
        self.logger.info(f"Loading data ({self.days} days)")

        csv_path = Path("src/backtest/data/historical/BTC_JPY_15m.csv")

        if not csv_path.exists():
            self.logger.info("Collecting historical data...")
            collector = HistoricalDataCollector()
            await collector.collect_data(symbol="BTC/JPY", days=self.days, timeframes=["15m"])

        df = pd.read_csv(csv_path)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)

        from datetime import timedelta

        cutoff_date = datetime.now() - timedelta(days=self.days)
        df = df[df.index >= cutoff_date]

        if df.isnull().any().any():
            df = df.dropna()

        self.logger.info(f"Loaded {len(df)} samples")
        return df[["open", "high", "low", "close", "volume"]].copy()

    async def _generate_strategy_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """戦略シグナル生成"""
        strategy_loader = StrategyLoader("config/strategies.yaml")
        loaded_strategies = strategy_loader.load_strategies()
        strategy_names = [s["metadata"]["name"] for s in loaded_strategies]

        self.logger.info(f"Generating strategy signals for {len(strategy_names)} strategies")

        strategy_signals = pd.DataFrame(index=df.index)
        strategy_manager = StrategyManager()

        for strategy_data in loaded_strategies:
            strategy_manager.register_strategy(
                strategy_data["instance"], weight=strategy_data["weight"]
            )

        self.data_pipeline.set_backtest_data({"15m": df.copy()})

        total_points = len(df)
        for i in range(len(df)):
            current_data = df.iloc[: i + 1]

            if len(current_data) < 50:
                for strategy_name in strategy_names:
                    strategy_signals.loc[
                        current_data.index[-1], f"strategy_signal_{strategy_name}"
                    ] = 0.5
                continue

            try:
                self.data_pipeline.set_backtest_data({"15m": current_data.copy()})
                signals = strategy_manager.get_individual_strategy_signals(current_data)

                current_timestamp = current_data.index[-1]
                for strategy_name in strategy_names:
                    if strategy_name in signals:
                        action = signals[strategy_name]["action"]
                        confidence = signals[strategy_name]["confidence"]

                        if action == "buy":
                            signal_value = 0.5 + (confidence * 0.5)
                        elif action == "sell":
                            signal_value = 0.5 - (confidence * 0.5)
                        else:
                            signal_value = 0.5

                        strategy_signals.loc[
                            current_timestamp, f"strategy_signal_{strategy_name}"
                        ] = signal_value
                    else:
                        strategy_signals.loc[
                            current_timestamp, f"strategy_signal_{strategy_name}"
                        ] = 0.5

            except Exception:
                for strategy_name in strategy_names:
                    strategy_signals.loc[
                        current_data.index[-1], f"strategy_signal_{strategy_name}"
                    ] = 0.5

            if (i + 1) % max(1, total_points // 10) == 0:
                progress = ((i + 1) / total_points) * 100
                self.logger.info(
                    f"Strategy signal progress: {i + 1}/{total_points} ({progress:.1f}%)"
                )

        strategy_signals.fillna(0.5, inplace=True)
        return strategy_signals

    async def prepare_training_data(self) -> Tuple[pd.DataFrame, pd.Series]:
        """学習データ準備"""
        df = await self._load_data()

        # 特徴量生成
        features_df = await self.feature_generator.generate_features(df)

        # 戦略シグナル削除
        strategy_signal_cols = [
            col for col in features_df.columns if col.startswith("strategy_signal_")
        ]
        if strategy_signal_cols:
            features_df = features_df.drop(columns=strategy_signal_cols)

        # 実戦略シグナル生成
        strategy_signals_df = await self._generate_strategy_signals(features_df)
        features_df = pd.concat([features_df, strategy_signals_df], axis=1)

        # 特徴量整合性
        for feature in self.expected_features:
            if feature not in features_df.columns:
                features_df[feature] = 0.0

        features_df = features_df[self.expected_features]

        # ターゲット生成
        price_change = df["close"].pct_change(periods=1).shift(-1)
        target = pd.Series(1, index=df.index, dtype=int)
        target[price_change > self.target_threshold] = 2
        target[price_change < -self.target_threshold] = 0

        # クリーニング
        valid_mask = ~(features_df.isna().any(axis=1) | target.isna())
        features_df = features_df[valid_mask].copy()
        target = target[valid_mask].copy()

        features_df.replace([np.inf, -np.inf], np.nan, inplace=True)
        features_df.fillna(0, inplace=True)

        self.logger.info(
            f"Prepared {len(features_df)} samples, {len(features_df.columns)} features"
        )
        return features_df, target

    def train_models(self, features: pd.DataFrame, target: pd.Series) -> Dict[str, Any]:
        """モデル学習"""
        config = self._get_pattern_config()
        models = self._create_models()

        self.logger.info(f"Training models (Pattern {self.pattern})")

        results = {}
        trained_models = {}

        # Split
        n_samples = len(features)
        train_size = int(n_samples * 0.70)
        val_size = int(n_samples * 0.15)

        X_train = features.iloc[:train_size]
        y_train = target.iloc[:train_size]
        X_val = features.iloc[train_size : train_size + val_size]
        y_val = target.iloc[train_size : train_size + val_size]
        X_test = features.iloc[train_size + val_size :]
        y_test = target.iloc[train_size + val_size :]

        self.logger.info(f"Split: Train={len(X_train)}, Val={len(X_val)}, Test={len(X_test)}")

        # Optuna最適化（パターンDでは無効）
        if config["use_optuna"]:
            self.logger.info(f"Running Optuna optimization ({self.n_trials} trials)")
            optimal_params = self._optimize_hyperparameters(
                pd.concat([X_train, X_val]),
                pd.concat([y_train, y_val]),
                config,
            )
            for model_name in models.keys():
                if model_name in optimal_params:
                    models[model_name].set_params(**optimal_params[model_name])
        else:
            self.logger.info("Optuna disabled (using 60.4 parameters)")

        # 学習
        tscv = TimeSeriesSplit(n_splits=5)

        for model_name, model in models.items():
            self.logger.info(f"Training {model_name}")

            try:
                cv_scores = []
                for train_idx, val_idx in tscv.split(X_train):
                    X_cv_train = X_train.iloc[train_idx]
                    y_cv_train = y_train.iloc[train_idx]
                    X_cv_val = X_train.iloc[val_idx]
                    y_cv_val = y_train.iloc[val_idx]

                    # SMOTE
                    try:
                        smote = SMOTE(sampling_strategy="auto", k_neighbors=5, random_state=42)
                        X_cv_train_resampled, y_cv_train_resampled = smote.fit_resample(
                            X_cv_train, y_cv_train
                        )
                        X_cv_train = pd.DataFrame(X_cv_train_resampled, columns=X_cv_train.columns)
                        y_cv_train = pd.Series(y_cv_train_resampled)
                    except Exception:
                        pass

                    # Fit
                    if model_name == "lightgbm":
                        try:
                            import lightgbm

                            model.fit(
                                X_cv_train,
                                y_cv_train,
                                eval_set=[(X_cv_val, y_cv_val)],
                                callbacks=[
                                    lightgbm.early_stopping(stopping_rounds=20, verbose=False)
                                ],
                            )
                        except ValueError:
                            model.fit(X_cv_train, y_cv_train)
                    elif model_name == "xgboost":
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
                            model.fit(X_cv_train, y_cv_train)
                    else:
                        model.fit(X_cv_train, y_cv_train)

                    y_pred = model.predict(X_cv_val)
                    score = f1_score(y_cv_val, y_pred, average="weighted")
                    cv_scores.append(score)

                # Final training
                X_train_val = pd.concat([X_train, X_val])
                y_train_val = pd.concat([y_train, y_val])

                try:
                    smote = SMOTE(sampling_strategy="auto", k_neighbors=5, random_state=42)
                    X_resampled, y_resampled = smote.fit_resample(X_train_val, y_train_val)
                    X_train_val = pd.DataFrame(X_resampled, columns=X_train_val.columns)
                    y_train_val = pd.Series(y_resampled)
                except Exception:
                    pass

                if model_name == "lightgbm":
                    import lightgbm

                    model.fit(
                        X_train_val,
                        y_train_val,
                        eval_set=[(X_test, y_test)],
                        callbacks=[lightgbm.early_stopping(stopping_rounds=20, verbose=False)],
                    )
                elif model_name == "xgboost":
                    try:
                        from xgboost import callback as xgb_callback

                        model.fit(
                            X_train_val,
                            y_train_val,
                            eval_set=[(X_test, y_test)],
                            callbacks=[xgb_callback.EarlyStopping(rounds=20)],
                            verbose=False,
                        )
                    except Exception:
                        model.fit(X_train_val, y_train_val)
                else:
                    model.fit(X_train_val, y_train_val)

                # Evaluation
                y_test_pred = model.predict(X_test)
                test_f1 = f1_score(y_test, y_test_pred, average="weighted")

                results[model_name] = {
                    "f1_score": test_f1,
                    "cv_f1_mean": np.mean(cv_scores),
                    "cv_f1_std": np.std(cv_scores),
                }
                trained_models[model_name] = model

                self.logger.info(
                    f"{model_name}: Test F1={test_f1:.3f}, CV F1={np.mean(cv_scores):.3f}"
                )

            except Exception as e:
                self.logger.error(f"{model_name} training error: {e}")
                results[model_name] = {"error": str(e)}

        # Ensemble
        if len(trained_models) >= 2:
            # 重み設定
            if config["fixed_weights"]:
                weights = config["weights"]
            else:
                weights = self._calculate_optimal_weights(results)

            # 個別モデルのみでEnsemble作成（循環参照防止のためコピーを使用）
            individual_models = {k: v for k, v in trained_models.items()}
            ensemble_model = ProductionEnsemble(individual_models)
            ensemble_model.weights = weights
            trained_models["production_ensemble"] = ensemble_model

            self.logger.info(f"Ensemble created with weights: {weights}")

        return {
            "results": results,
            "models": trained_models,
            "feature_names": list(features.columns),
            "training_samples": len(features),
            "config": config,
        }

    def _optimize_hyperparameters(
        self,
        features: pd.DataFrame,
        target: pd.Series,
        config: Dict,
    ) -> Dict[str, Dict]:
        """Optuna最適化"""
        import optuna
        from optuna.samplers import TPESampler

        optuna.logging.set_verbosity(optuna.logging.WARNING)
        optimal_params = {}

        for model_name in ["lightgbm", "xgboost", "random_forest"]:
            self.logger.info(f"Optimizing {model_name}")

            def objective(trial):
                if model_name == "lightgbm":
                    params = {
                        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
                        "max_depth": trial.suggest_int("max_depth", 3, 15),
                        "n_estimators": trial.suggest_int("n_estimators", 50, 300),
                        "num_leaves": trial.suggest_int("num_leaves", 20, 100),
                        "random_state": config["seeds"]["lgb"],
                        "verbose": -1,
                        "class_weight": "balanced",
                        "feature_fraction": config["feature_fraction"],
                        "objective": "multiclass",
                        "num_class": 3,
                    }
                    model = LGBMClassifier(**params)
                elif model_name == "xgboost":
                    params = {
                        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
                        "max_depth": trial.suggest_int("max_depth", 3, 15),
                        "n_estimators": trial.suggest_int("n_estimators", 50, 300),
                        "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
                        "random_state": config["seeds"]["xgb"],
                        "verbosity": 0,
                        "colsample_bytree": config["colsample_bytree"],
                        "objective": "multi:softprob",
                        "num_class": 3,
                    }
                    model = XGBClassifier(**params)
                else:
                    params = {
                        "n_estimators": trial.suggest_int("n_estimators", 50, 300),
                        "max_depth": trial.suggest_int("max_depth", 5, 20),
                        "min_samples_split": trial.suggest_int("min_samples_split", 2, 20),
                        "random_state": config["seeds"]["rf"],
                        "n_jobs": 1,
                        "class_weight": "balanced",
                    }
                    model = RandomForestClassifier(**params)

                tscv = TimeSeriesSplit(n_splits=3)
                scores = []
                for train_idx, val_idx in tscv.split(features):
                    X_train = features.iloc[train_idx]
                    y_train = target.iloc[train_idx]
                    X_val = features.iloc[val_idx]
                    y_val = target.iloc[val_idx]

                    model.fit(X_train, y_train)
                    y_pred = model.predict(X_val)
                    scores.append(f1_score(y_val, y_pred, average="weighted"))

                return np.mean(scores)

            study = optuna.create_study(direction="maximize", sampler=TPESampler(seed=42))
            study.optimize(objective, n_trials=self.n_trials, show_progress_bar=False)

            optimal_params[model_name] = study.best_params
            self.logger.info(f"{model_name}: Best F1={study.best_value:.4f}")

        return optimal_params

    def _calculate_optimal_weights(self, results: Dict) -> Dict[str, float]:
        """動的重み計算"""
        model_scores = {}
        for model_name in ["lightgbm", "xgboost", "random_forest"]:
            if model_name in results and "f1_score" in results[model_name]:
                model_scores[model_name] = results[model_name]["f1_score"]
            else:
                model_scores[model_name] = 0.33

        total_score = sum(model_scores.values())
        if total_score <= 0:
            return {"lightgbm": 0.33, "xgboost": 0.33, "random_forest": 0.34}

        weights = {name: score / total_score for name, score in model_scores.items()}

        # 最小重み確保
        for name in weights:
            if weights[name] < 0.1:
                weights[name] = 0.1

        # 再正規化
        total = sum(weights.values())
        weights = {name: round(w / total, 3) for name, w in weights.items()}

        # 合計調整
        weight_sum = sum(weights.values())
        if weight_sum != 1.0:
            max_model = max(weights, key=weights.get)
            weights[max_model] = round(weights[max_model] + (1.0 - weight_sum), 3)

        return weights

    def save_models(self, training_results: Dict) -> str:
        """モデル保存"""
        models = training_results.get("models", {})

        # Ensemble保存
        if "production_ensemble" in models:
            model_file = self.output_dir / "ensemble_full.pkl"
            with open(model_file, "wb") as f:
                pickle.dump(models["production_ensemble"], f)
            self.logger.info(f"Saved: {model_file}")

        # メタデータ保存
        metadata = {
            "created_at": datetime.now().isoformat(),
            "pattern": self.pattern,
            "config": training_results.get("config", {}),
            "results": training_results.get("results", {}),
            "feature_names": training_results.get("feature_names", []),
            "training_samples": training_results.get("training_samples", 0),
        }

        metadata_file = self.output_dir / "metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)

        self.logger.info(f"Saved metadata: {metadata_file}")
        return str(self.output_dir / "ensemble_full.pkl")

    async def run(self) -> bool:
        """メイン実行"""
        try:
            self.logger.info(f"Starting A/B test - Pattern {self.pattern}")

            # データ準備
            features, target = await self.prepare_training_data()

            # モデル学習
            training_results = self.train_models(features, target)

            # 保存
            model_path = self.save_models(training_results)

            # 信頼度評価
            self.logger.info("Evaluating confidence distribution...")
            evaluate_model_confidence(model_path, features)

            self.logger.info(f"Pattern {self.pattern} completed!")
            return True

        except Exception as e:
            self.logger.error(f"Error: {e}")
            import traceback

            traceback.print_exc()
            return False


def evaluate_model_confidence(model_path: str, features: Optional[pd.DataFrame] = None):
    """
    モデルの信頼度分布を評価

    Args:
        model_path: モデルファイルパス
        features: 評価用特徴量（Noneの場合は内部で生成）
    """
    logger = get_logger()

    # モデル読み込み
    with open(model_path, "rb") as f:
        model = pickle.load(f)

    if features is None:
        # 簡易評価: ランダムデータで信頼度分布を確認
        logger.info("Generating random test data for confidence evaluation...")
        expected_features = get_feature_names()
        n_samples = 1000
        # ランダムな特徴量データ（信頼度分布の確認用）
        np.random.seed(42)
        features_array = np.random.randn(n_samples, len(expected_features))
    else:
        # 渡された特徴量を使用
        features_array = features.values if hasattr(features, "values") else features
    predictions = model.predict(features_array)
    probabilities = model.predict_proba(features_array)

    # 信頼度計算
    confidences = np.max(probabilities, axis=1)

    # 統計
    high_conf_rate = (confidences > 0.5).mean() * 100
    mean_conf = confidences.mean()

    # 予測分布
    pred_counts = pd.Series(predictions).value_counts(normalize=True)

    # 結果表示
    n_samples = len(features_array)
    print("\n" + "=" * 60)
    print(f"Model: {model_path}")
    print("=" * 60)
    print(f"Samples: {n_samples}")
    print("\nConfidence Distribution:")
    print(f"  - High confidence (>50%): {high_conf_rate:.1f}%")
    print(f"  - Mean confidence: {mean_conf:.3f}")
    print(f"  - Min confidence: {confidences.min():.3f}")
    print(f"  - Max confidence: {confidences.max():.3f}")
    print("\nPrediction Distribution:")
    for cls, pct in pred_counts.items():
        label = {0: "SELL", 1: "HOLD", 2: "BUY"}.get(cls, str(cls))
        print(f"  - {label}: {pct:.1%}")
    print("=" * 60)

    # 判定
    if high_conf_rate >= 25:
        print("Status: PROMISING (high confidence rate >= 25%)")
    elif high_conf_rate >= 10:
        print("Status: ACCEPTABLE (high confidence rate >= 10%)")
    else:
        print("Status: POOR (high confidence rate < 10%)")

    return {
        "high_conf_rate": high_conf_rate,
        "mean_conf": mean_conf,
        "prediction_dist": pred_counts.to_dict(),
    }


def evaluate_all_patterns():
    """全パターンの評価"""
    print("\n" + "=" * 80)
    print("A/B Test Results Summary")
    print("=" * 80)

    results = {}
    base_dir = Path("models/ab_test")

    # 60.4基準
    ref_path = Path("models/archive/phase60.4_20260120_051942/ensemble_full.pkl")
    if ref_path.exists():
        print("\n[Reference] Phase 60.4:")
        try:
            results["60.4"] = evaluate_model_confidence(str(ref_path))
        except Exception as e:
            print(f"Error: {e}")

    # 60.5現行
    current_path = Path("models/production/ensemble_full.pkl")
    if current_path.exists():
        print("\n[Current] Phase 60.5:")
        try:
            results["60.5"] = evaluate_model_confidence(str(current_path))
        except Exception as e:
            print(f"Error: {e}")

    # A/Bテストパターン
    for pattern in ["A", "B", "C", "D"]:
        pattern_path = base_dir / f"pattern_{pattern}" / "ensemble_full.pkl"
        if pattern_path.exists():
            print(f"\n[Pattern {pattern}]:")
            try:
                results[f"Pattern_{pattern}"] = evaluate_model_confidence(str(pattern_path))
            except Exception as e:
                print(f"Error: {e}")

    # サマリーテーブル
    if results:
        print("\n" + "=" * 80)
        print("Summary Table")
        print("=" * 80)
        print(f"{'Model':<15} {'High Conf Rate':<20} {'Mean Conf':<15} {'Status'}")
        print("-" * 80)
        for name, data in results.items():
            rate = data.get("high_conf_rate", 0)
            mean = data.get("mean_conf", 0)
            if rate >= 25:
                status = "PROMISING"
            elif rate >= 10:
                status = "ACCEPTABLE"
            else:
                status = "POOR"
            print(f"{name:<15} {rate:>6.1f}%              {mean:>6.3f}          {status}")


def main():
    parser = argparse.ArgumentParser(description="Phase 60.6 A/B Test Models")

    parser.add_argument(
        "--pattern",
        type=str,
        choices=["A", "B", "C", "D"],
        help="Test pattern (A/B/C/D)",
    )
    parser.add_argument("--days", type=int, default=180, help="Training data days")
    parser.add_argument("--n-trials", type=int, default=50, help="Optuna trials")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--evaluate", type=str, help="Evaluate specific model path")
    parser.add_argument("--evaluate-all", action="store_true", help="Evaluate all patterns")

    args = parser.parse_args()

    if args.evaluate:
        evaluate_model_confidence(args.evaluate)
    elif args.evaluate_all:
        evaluate_all_patterns()
    elif args.pattern:
        creator = ABTestModelCreator(
            pattern=args.pattern,
            verbose=args.verbose,
            days=args.days,
            n_trials=args.n_trials,
        )
        success = asyncio.run(creator.run())
        sys.exit(0 if success else 1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
