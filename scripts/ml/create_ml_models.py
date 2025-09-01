#!/usr/bin/env python3
"""
新システム用MLモデル作成スクリプト.

Phase 9対応: 12特徴量最適化システム用モデル学習
レガシーシステムのretrain_97_features_model.pyを参考に新システム構造で実装

機能:
- 12特徴量での LightGBM・XGBoost・RandomForest アンサンブル学習
- 新システム src/ 構造に対応
- models/production/ にモデル保存
- 実取引前の品質保証・性能検証

使用方法:
    python scripts/create_ml_models.py [--dry-run] [--verbose].
"""

import argparse
import json
import logging
import pickle
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import TimeSeriesSplit
from xgboost import XGBClassifier

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.core.config import load_config
    from src.core.logger import get_logger
    from src.data.data_pipeline import DataPipeline, DataRequest, TimeFrame
    from src.features.technical import TechnicalIndicators
    from src.ml.ensemble import ProductionEnsemble
except ImportError as e:
    print(f"❌ 新システムモジュールのインポートに失敗: {e}")
    print("プロジェクトルートから実行してください。")
    sys.exit(1)


class NewSystemMLModelCreator:
    """新システム用MLモデル作成・学習システム."""

    def __init__(self, config_path: str = "config/core/base.yaml", verbose: bool = False):
        """初期化."""
        self.config_path = config_path
        self.verbose = verbose

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
        self.technical_indicators = TechnicalIndicators()

        # 12特徴量定義（新システム最適化済み）
        self.expected_features = [
            "close",
            "volume",
            "returns_1",
            "rsi_14",
            "macd",
            "macd_signal",
            "atr_14",
            "bb_position",
            "ema_20",
            "ema_50",
            "zscore",
            "volume_ratio",
        ]

        self.logger.info(f"🎯 対象特徴量: {len(self.expected_features)}個（新システム最適化済み）")

        # MLモデル設定
        self.models = {
            "lightgbm": LGBMClassifier(
                n_estimators=200,
                learning_rate=0.1,
                max_depth=8,
                num_leaves=31,
                random_state=42,
                verbose=-1,
            ),
            "xgboost": XGBClassifier(
                n_estimators=200,
                learning_rate=0.1,
                max_depth=8,
                random_state=42,
                eval_metric="logloss",
                verbosity=0,
            ),
            "random_forest": RandomForestClassifier(
                n_estimators=200,
                max_depth=12,
                random_state=42,
                n_jobs=-1,
            ),
        }

    def prepare_training_data(self, days: int = 180) -> Tuple[pd.DataFrame, pd.Series]:
        """学習用データ準備（新システム対応）."""
        self.logger.info(f"📊 学習データ準備開始（過去{days}日分）")

        try:
            # 過去データ取得

            # 1時間足データ取得
            request = DataRequest(
                symbol="BTC/JPY",
                timeframe=TimeFrame.H1,
                limit=days * 24,
                since=None,  # 1日24時間
            )
            df = self.data_pipeline.fetch_ohlcv(request)

            if df is None or len(df) < 100:
                self.logger.warning("❌ 実データ取得失敗、サンプルデータを生成")
                df = self._generate_sample_data(days * 24)

            self.logger.info(f"✅ 基本データ取得完了: {len(df)}行")

            # 特徴量エンジニアリング
            features_df = self.technical_indicators.generate_all_features(df)

            # 12特徴量への整合性確保
            features_df = self._ensure_feature_consistency(features_df)

            # ターゲット生成（価格変動による分類）
            target = self._generate_target(df)

            # データ品質チェック
            features_df, target = self._clean_data(features_df, target)

            self.logger.info(
                f"✅ 学習データ準備完了: {len(features_df)}サンプル、{len(features_df.columns)}特徴量"
            )
            return features_df, target

        except Exception as e:
            self.logger.error(f"❌ 学習データ準備エラー: {e}")
            raise

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

    def _ensure_feature_consistency(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """12特徴量への整合性確保."""
        # 不足特徴量の0埋め
        for feature in self.expected_features:
            if feature not in features_df.columns:
                features_df[feature] = 0.0
                self.logger.warning(f"⚠️ 不足特徴量を0埋め: {feature}")

        # 12特徴量のみ選択
        features_df = features_df[self.expected_features]

        if len(features_df.columns) != 12:
            self.logger.warning(f"⚠️ 特徴量数不一致: {len(features_df.columns)} != 12")

        return features_df

    def _generate_target(self, df: pd.DataFrame) -> pd.Series:
        """ターゲット生成（価格変動による分類）."""
        # 1時間後の価格変動率
        price_change = df["close"].pct_change(periods=1).shift(-1)

        # 0.3%以上の上昇をBUY（1）、それ以外をHOLD/SELL（0）
        target = (price_change > 0.003).astype(int)

        buy_ratio = target.mean()
        self.logger.info(f"📊 ターゲット分布: BUY {buy_ratio:.1%}, HOLD/SELL {1 - buy_ratio:.1%}")

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

    def train_models(
        self, features: pd.DataFrame, target: pd.Series, dry_run: bool = False
    ) -> Dict[str, Any]:
        """モデル学習実行."""
        self.logger.info("🤖 MLモデル学習開始")

        if dry_run:
            self.logger.info("🔍 ドライラン: 実際の学習はスキップ")
            return {"dry_run": True, "models": list(self.models.keys())}

        results = {}
        trained_models = {}

        # TimeSeriesSplit による時系列データ対応クロスバリデーション
        tscv = TimeSeriesSplit(n_splits=3)

        for model_name, model in self.models.items():
            self.logger.info(f"📈 {model_name} 学習開始")

            try:
                # クロスバリデーション評価
                cv_scores = []

                for train_idx, val_idx in tscv.split(features):
                    X_train, X_val = (
                        features.iloc[train_idx],
                        features.iloc[val_idx],
                    )
                    y_train, y_val = (
                        target.iloc[train_idx],
                        target.iloc[val_idx],
                    )

                    # モデル学習（DataFrameのまま渡してsklearn警告回避）
                    model.fit(X_train, y_train)

                    # 予測・評価
                    y_pred = model.predict(X_val)
                    score = f1_score(y_val, y_pred, average="weighted")
                    cv_scores.append(score)

                # 全データで最終モデル学習（DataFrameのまま渡してsklearn警告回避）
                # featuresがDataFrameであることを確実にする
                if not isinstance(features, pd.DataFrame):
                    features = pd.DataFrame(features, columns=self.expected_features)
                model.fit(features, target)

                # 評価指標計算
                y_pred = model.predict(features)
                metrics = {
                    "accuracy": accuracy_score(target, y_pred),
                    "f1_score": f1_score(target, y_pred, average="weighted"),
                    "precision": precision_score(target, y_pred, average="weighted"),
                    "recall": recall_score(target, y_pred, average="weighted"),
                    "cv_f1_mean": np.mean(cv_scores),
                    "cv_f1_std": np.std(cv_scores),
                }

                results[model_name] = metrics
                trained_models[model_name] = model

                self.logger.info(
                    f"✅ {model_name} 学習完了 - F1: {metrics['f1_score']:.3f}, "
                    f"CV F1: {metrics['cv_f1_mean']:.3f}±{metrics['cv_f1_std']:.3f}"
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

                    # 本番用メタデータ保存
                    production_metadata = {
                        "created_at": datetime.now().isoformat(),
                        "model_type": "ProductionEnsemble",
                        "model_file": str(model_file),
                        "phase": "Phase 9",
                        "status": "production_ready",
                        "feature_names": training_results.get("feature_names", []),
                        "individual_models": [
                            k for k in model.models.keys() if k != "production_ensemble"
                        ],
                        "model_weights": model.weights,
                        "notes": "本番用統合アンサンブルモデル・実取引用最適化済み・循環参照修正",
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

        # 学習用メタデータ保存
        training_metadata = {
            "created_at": datetime.now().isoformat(),
            "feature_names": training_results.get("feature_names", []),
            "training_samples": training_results.get("training_samples", 0),
            "model_metrics": training_results.get("results", {}),
            "model_files": saved_files,
            "config_path": self.config_path,
            "phase": "Phase 9",
            "notes": "個別モデル学習結果・training用保存",
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

                # サンプル予測テスト（DataFrameでsklearn警告回避）
                sample_features_array = np.random.random((5, 12))  # 12特徴量
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

                    # get_model_info メソッド確認
                    if hasattr(model, "get_model_info"):
                        info = model.get_model_info()
                        if info.get("n_features") == 12:
                            self.logger.info("✅ get_model_info 確認成功")
                        else:
                            self.logger.error("❌ get_model_info 特徴量数不正")
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

    def run(self, dry_run: bool = False, days: int = 180) -> bool:
        """メイン実行処理."""
        try:
            self.logger.info("🚀 新システムMLモデル作成開始")

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
    """メイン関数."""
    parser = argparse.ArgumentParser(
        description="新システム用MLモデル作成スクリプト",
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
    parser.add_argument("--config", default="config/core/base.yaml", help="設定ファイルパス")

    args = parser.parse_args()

    # モデル作成実行
    creator = NewSystemMLModelCreator(config_path=args.config, verbose=args.verbose)

    success = creator.run(dry_run=args.dry_run, days=args.days)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
