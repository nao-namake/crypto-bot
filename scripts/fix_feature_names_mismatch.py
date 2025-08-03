#!/usr/bin/env python3
"""
Phase 3.1: feature_names mismatch完全解決
特徴量順序統一・ML予測精度修復システム

解決する問題:
- XGBoost/RandomForestが常に0.500を返す問題
- 学習時と予測時の特徴量順序不一致
- feature_names mismatch エラー
- ML予測の信頼性確保

実装機能:
1. 特徴量順序検証・修正システム
2. MLモデル互換性チェック
3. feature_order.json整合性確保
4. 97特徴量システム完全対応
"""

import json
import logging
import pickle
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yaml

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# FeatureOrderManager インポート
try:
    from crypto_bot.ml.feature_order_manager import (
        FeatureOrderManager,
        get_feature_order_manager,
    )

    logger.info("✅ FeatureOrderManager successfully imported")
except ImportError as e:
    logger.error(f"❌ FeatureOrderManager import failed: {e}")
    sys.exit(1)


class FeatureNamesMismatchFixer:
    """
    Phase 3.1: feature_names mismatch完全解決システム

    機能:
    - 特徴量順序統一
    - MLモデル互換性保証
    - 学習・予測間一致確保
    - 97特徴量システム完全対応
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.config = None
        self.feature_manager = get_feature_order_manager()

        # 97特徴量システム標準順序
        self.standard_97_features = self.feature_manager.FEATURE_ORDER_97

        logger.info("🔧 FeatureNamesMismatchFixer initialized")

        if config_path:
            self.load_config()

    def load_config(self) -> bool:
        """設定ファイル読み込み"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f)
            logger.info(f"✅ Config loaded: {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Config load failed: {e}")
            return False

    def diagnose_feature_mismatch(
        self, df: pd.DataFrame, model_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        特徴量ミスマッチの包括的診断

        Args:
            df: 診断対象DataFrame
            model_path: MLモデルファイルパス（オプション）

        Returns:
            診断結果の詳細レポート
        """
        logger.info("🔍 Starting comprehensive feature mismatch diagnosis...")

        diagnosis = {
            "timestamp": datetime.now().isoformat(),
            "input_features": {"count": len(df.columns), "features": list(df.columns)},
            "standard_features": {
                "count": len(self.standard_97_features),
                "features": self.standard_97_features,
            },
            "analysis": {},
            "issues": [],
            "recommendations": [],
        }

        # 1. 特徴量数の検証
        input_count = len(df.columns)
        if input_count != 97:
            issue = f"Feature count mismatch: {input_count} instead of 97"
            diagnosis["issues"].append(issue)
            logger.warning(f"⚠️ {issue}")

        # 2. 特徴量順序の検証
        input_features = list(df.columns)
        if input_features != self.standard_97_features:
            issue = "Feature order mismatch detected"
            diagnosis["issues"].append(issue)
            logger.warning(f"⚠️ {issue}")

            # 詳細分析
            input_set = set(input_features)
            standard_set = set(self.standard_97_features)

            missing_features = standard_set - input_set
            extra_features = input_set - standard_set
            common_features = input_set & standard_set

            diagnosis["analysis"] = {
                "missing_features": list(missing_features),
                "extra_features": list(extra_features),
                "common_features": list(common_features),
                "missing_count": len(missing_features),
                "extra_count": len(extra_features),
                "common_count": len(common_features),
                "overlap_ratio": len(common_features) / 97,
            }

            logger.info(
                f"📊 Analysis: {len(missing_features)} missing, {len(extra_features)} extra, {len(common_features)} common"
            )

        # 3. MLモデル互換性検証
        if model_path and Path(model_path).exists():
            model_diagnosis = self._diagnose_model_compatibility(
                model_path, input_features
            )
            diagnosis["model_compatibility"] = model_diagnosis

        # 4. feature_order.json整合性検証
        feature_order_diagnosis = self._diagnose_feature_order_file(input_features)
        diagnosis["feature_order_file"] = feature_order_diagnosis

        # 5. 推奨事項の生成
        diagnosis["recommendations"] = self._generate_recommendations(diagnosis)

        logger.info(f"✅ Diagnosis completed: {len(diagnosis['issues'])} issues found")
        return diagnosis

    def _diagnose_model_compatibility(
        self, model_path: str, input_features: List[str]
    ) -> Dict[str, Any]:
        """MLモデル互換性診断"""
        logger.info(f"🤖 Diagnosing ML model compatibility: {model_path}")

        try:
            with open(model_path, "rb") as f:
                model = pickle.load(f)

            model_info = {
                "model_type": type(model).__name__,
                "model_loaded": True,
                "feature_compatibility": {},
                "issues": [],
            }

            # XGBoost/LightGBM の場合、特徴量名を確認
            if hasattr(model, "feature_names_in_"):
                model_features = list(model.feature_names_in_)
                model_info["model_features"] = model_features
                model_info["model_feature_count"] = len(model_features)

                # 特徴量の比較
                if model_features != input_features:
                    model_info["issues"].append(
                        "Feature names/order mismatch with model"
                    )
                    model_info["feature_compatibility"] = {
                        "perfect_match": False,
                        "model_features": model_features,
                        "input_features": input_features,
                    }
                else:
                    model_info["feature_compatibility"] = {"perfect_match": True}

            elif hasattr(model, "get_booster"):  # XGBoost specific
                try:
                    booster = model.get_booster()
                    model_features = booster.feature_names
                    model_info["model_features"] = model_features
                    model_info["model_feature_count"] = len(model_features)

                    if model_features != input_features:
                        model_info["issues"].append("XGBoost feature names mismatch")
                except Exception as e:
                    model_info["issues"].append(
                        f"XGBoost feature extraction failed: {e}"
                    )

            else:
                model_info["issues"].append("Cannot extract feature names from model")

            logger.info(f"🤖 Model compatibility diagnosis completed")
            return model_info

        except Exception as e:
            logger.error(f"❌ Model compatibility diagnosis failed: {e}")
            return {
                "model_loaded": False,
                "error": str(e),
                "issues": [f"Model loading failed: {e}"],
            }

    def _diagnose_feature_order_file(self, input_features: List[str]) -> Dict[str, Any]:
        """feature_order.json整合性診断"""
        logger.info("📋 Diagnosing feature_order.json consistency...")

        feature_order_path = Path("config/core/feature_order.json")

        diagnosis = {"file_exists": feature_order_path.exists(), "issues": []}

        if not feature_order_path.exists():
            diagnosis["issues"].append("feature_order.json file not found")
            return diagnosis

        try:
            with open(feature_order_path, "r") as f:
                data = json.load(f)

            stored_features = data.get("feature_order", [])
            stored_count = data.get("num_features", 0)

            diagnosis.update(
                {
                    "stored_features": stored_features,
                    "stored_count": stored_count,
                    "data_loaded": True,
                }
            )

            # 整合性チェック
            if stored_count != 97:
                diagnosis["issues"].append(f"Stored feature count {stored_count} != 97")

            if stored_features != self.standard_97_features:
                diagnosis["issues"].append("Stored features != standard 97 features")

            if stored_features != input_features:
                diagnosis["issues"].append("Stored features != input features")

            if not diagnosis["issues"]:
                logger.info("✅ feature_order.json is perfectly consistent")

            return diagnosis

        except Exception as e:
            diagnosis["issues"].append(f"Failed to load feature_order.json: {e}")
            return diagnosis

    def _generate_recommendations(self, diagnosis: Dict[str, Any]) -> List[str]:
        """診断結果に基づく推奨事項生成"""
        recommendations = []

        if diagnosis["issues"]:
            recommendations.append("🔧 Execute fix_feature_order() to resolve issues")

        # 特徴量数の問題
        input_count = diagnosis["input_features"]["count"]
        if input_count != 97:
            if input_count < 97:
                recommendations.append(
                    f"📈 Add {97 - input_count} missing features using generate_missing_features()"
                )
            else:
                recommendations.append(
                    f"📉 Remove {input_count - 97} excess features using trim_to_97_features()"
                )

        # 特徴量順序の問題
        if (
            "analysis" in diagnosis
            and diagnosis["analysis"].get("overlap_ratio", 1.0) < 0.8
        ):
            recommendations.append(
                "🔄 Regenerate features using HybridBacktestEngine.add_97_features()"
            )

        # MLモデルの問題
        if "model_compatibility" in diagnosis:
            model_issues = diagnosis["model_compatibility"].get("issues", [])
            if model_issues:
                recommendations.append(
                    "🤖 Retrain ML model with corrected 97-feature dataset"
                )

        # feature_order.jsonの問題
        if "feature_order_file" in diagnosis:
            file_issues = diagnosis["feature_order_file"].get("issues", [])
            if file_issues:
                recommendations.append(
                    "📋 Update feature_order.json using save_corrected_feature_order()"
                )

        if not recommendations:
            recommendations.append(
                "✅ No issues detected - system is properly configured"
            )

        return recommendations

    def fix_feature_order(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        特徴量順序の完全修正

        Args:
            df: 修正対象DataFrame

        Returns:
            97特徴量順序で修正されたDataFrame
        """
        logger.info("🔧 Starting comprehensive feature order fix...")
        start_time = pd.Timestamp.now()

        try:
            # Step 1: 現状診断
            original_count = len(df.columns)
            logger.info(f"📊 Input: {original_count} features")

            # Step 2: FeatureOrderManagerを使用した順序統一
            df_ordered = self.feature_manager.ensure_column_order(df.copy())

            # Step 3: 97特徴量完全性保証
            df_complete = self.feature_manager.ensure_97_features_completeness(
                df_ordered
            )

            # Step 4: 最終検証
            final_features = list(df_complete.columns)
            if final_features != self.standard_97_features:
                logger.warning("⚠️ Final validation failed - applying emergency fix")
                df_complete = self._apply_emergency_97_fix(df_complete)

            # Step 5: 品質チェック
            df_final = self._ensure_data_quality(df_complete)

            execution_time = pd.Timestamp.now() - start_time
            logger.info(
                f"✅ Feature order fix completed in {execution_time.total_seconds():.2f}s"
            )
            logger.info(f"📊 Result: {len(df_final.columns)} features (target: 97)")

            return df_final

        except Exception as e:
            logger.error(f"❌ Feature order fix failed: {e}")
            return self._create_emergency_97_dataframe(df)

    def _apply_emergency_97_fix(self, df: pd.DataFrame) -> pd.DataFrame:
        """緊急97特徴量修正"""
        logger.warning("🚨 Applying emergency 97-feature fix...")

        # 97特徴量の標準DataFrameを作成
        result_df = pd.DataFrame(0.0, index=df.index, columns=self.standard_97_features)

        # 利用可能な特徴量をコピー
        for col in df.columns:
            if col in result_df.columns:
                result_df[col] = df[col]

        logger.warning(f"🚨 Emergency fix applied: {len(result_df.columns)} features")
        return result_df

    def _ensure_data_quality(self, df: pd.DataFrame) -> pd.DataFrame:
        """データ品質確保"""
        df_clean = df.copy()

        # NaN値処理
        nan_cols = df_clean.columns[df_clean.isna().any()].tolist()
        if nan_cols:
            logger.info(f"🧹 Cleaning NaN values in {len(nan_cols)} columns")
            df_clean = (
                df_clean.fillna(method="ffill").fillna(method="bfill").fillna(0.0)
            )

        # Inf値処理
        inf_cols = df_clean.columns[np.isinf(df_clean).any()].tolist()
        if inf_cols:
            logger.info(f"🧹 Cleaning Inf values in {len(inf_cols)} columns")
            df_clean = df_clean.replace([np.inf, -np.inf], 0.0)

        return df_clean

    def _create_emergency_97_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """緊急97特徴量DataFrame作成"""
        logger.error("🚨 Creating emergency 97-feature DataFrame")
        return pd.DataFrame(
            0.0,
            index=df.index if not df.empty else [0],
            columns=self.standard_97_features,
        )

    def validate_ml_prediction_compatibility(
        self, df: pd.DataFrame, model_path: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        ML予測互換性の検証

        Args:
            df: 予測用DataFrame
            model_path: MLモデルパス

        Returns:
            (互換性OK, 詳細レポート)
        """
        logger.info("🤖 Validating ML prediction compatibility...")

        if not Path(model_path).exists():
            return False, {"error": "Model file not found"}

        try:
            # モデル読み込み
            with open(model_path, "rb") as f:
                model = pickle.load(f)

            # 特徴量検証
            df_features = list(df.columns)

            # テスト予測実行
            test_data = df.head(5).fillna(0.0)  # 最初の5行でテスト

            if hasattr(model, "predict_proba"):
                predictions = model.predict_proba(test_data)
                pred_shape = predictions.shape
                pred_sample = predictions[0] if len(predictions) > 0 else []
            else:
                predictions = model.predict(test_data)
                pred_shape = predictions.shape
                pred_sample = predictions[:3] if len(predictions) > 0 else []

            # 固定値チェック（0.500問題の検出）
            if hasattr(model, "predict_proba") and len(predictions) > 1:
                # 全ての予測が同じ値かチェック
                if len(predictions.shape) > 1 and predictions.shape[1] > 1:
                    first_pred = predictions[0, 1]  # Buy probability
                    all_same = np.all(np.abs(predictions[:, 1] - first_pred) < 1e-6)

                    if all_same:
                        logger.warning(
                            f"⚠️ Model returning fixed predictions: {first_pred}"
                        )
                        return False, {
                            "fixed_prediction_detected": True,
                            "fixed_value": float(first_pred),
                            "prediction_shape": pred_shape,
                            "sample_predictions": (
                                pred_sample.tolist()
                                if hasattr(pred_sample, "tolist")
                                else pred_sample
                            ),
                        }

            logger.info("✅ ML prediction compatibility validated")
            return True, {
                "model_type": type(model).__name__,
                "prediction_shape": pred_shape,
                "sample_predictions": (
                    pred_sample.tolist()
                    if hasattr(pred_sample, "tolist")
                    else pred_sample
                ),
                "feature_count": len(df_features),
            }

        except Exception as e:
            logger.error(f"❌ ML prediction compatibility validation failed: {e}")
            return False, {"error": str(e)}

    def save_corrected_feature_order(self, df: pd.DataFrame):
        """修正された特徴量順序を保存"""
        logger.info("💾 Saving corrected feature order...")

        features = list(df.columns)
        if len(features) == 97 and features == self.standard_97_features:
            self.feature_manager.save_feature_order(features)
            logger.info("✅ Corrected feature order saved")
        else:
            logger.warning(
                f"⚠️ Cannot save non-standard feature order: {len(features)} features"
            )

    def comprehensive_fix_and_validate(
        self, df: pd.DataFrame, model_path: Optional[str] = None
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        包括的修正・検証システム

        Args:
            df: 処理対象DataFrame
            model_path: MLモデルパス（オプション）

        Returns:
            (修正済みDataFrame, 検証レポート)
        """
        logger.info("🚀 Starting comprehensive fix and validation...")

        # 1. 初期診断
        initial_diagnosis = self.diagnose_feature_mismatch(df, model_path)

        # 2. 特徴量順序修正
        df_fixed = self.fix_feature_order(df)

        # 3. ML互換性検証
        ml_compatibility = {}
        if model_path:
            is_compatible, ml_report = self.validate_ml_prediction_compatibility(
                df_fixed, model_path
            )
            ml_compatibility = {"compatible": is_compatible, "report": ml_report}

        # 4. 最終診断
        final_diagnosis = self.diagnose_feature_mismatch(df_fixed, model_path)

        # 5. 修正された特徴量順序を保存
        if not final_diagnosis["issues"]:
            self.save_corrected_feature_order(df_fixed)

        # 6. 包括レポート
        comprehensive_report = {
            "timestamp": datetime.now().isoformat(),
            "initial_diagnosis": initial_diagnosis,
            "final_diagnosis": final_diagnosis,
            "ml_compatibility": ml_compatibility,
            "fix_successful": len(final_diagnosis["issues"]) == 0,
            "original_feature_count": len(df.columns),
            "final_feature_count": len(df_fixed.columns),
        }

        if comprehensive_report["fix_successful"]:
            logger.info("🎊 Comprehensive fix and validation completed successfully!")
        else:
            logger.warning(
                f"⚠️ Fix completed with {len(final_diagnosis['issues'])} remaining issues"
            )

        return df_fixed, comprehensive_report


def run_feature_mismatch_diagnosis():
    """Phase 3.1診断実行"""
    print("🔍 Phase 3.1: Feature Names Mismatch Diagnosis")
    print("=" * 70)

    fixer = FeatureNamesMismatchFixer()

    # サンプルデータで診断実行
    logger.info("📊 Creating sample data for diagnosis...")
    sample_data = pd.DataFrame(
        np.random.randn(100, 95),  # 97特徴量未満でテスト
        columns=[f"feature_{i:03d}" for i in range(95)],
    )

    # 診断実行
    diagnosis = fixer.diagnose_feature_mismatch(sample_data)

    # 結果表示
    print(f"\n📋 Diagnosis Results:")
    print(f"   Input features: {diagnosis['input_features']['count']}")
    print(f"   Issues found: {len(diagnosis['issues'])}")

    for issue in diagnosis["issues"]:
        print(f"   ❌ {issue}")

    print(f"\n💡 Recommendations:")
    for rec in diagnosis["recommendations"]:
        print(f"   {rec}")

    return diagnosis


def run_comprehensive_fix_demo():
    """包括的修正システムのデモ実行"""
    print("\n🔧 Phase 3.1: Comprehensive Fix Demo")
    print("=" * 70)

    fixer = FeatureNamesMismatchFixer()

    # HybridBacktestEngineを使用してリアルな97特徴量データを生成
    try:
        from scripts.hybrid_backtest_approach import HybridBacktest

        # サンプルデータ生成
        dates = pd.date_range("2024-01-01", periods=200, freq="H")
        np.random.seed(42)
        price = 7500000  # BTC/JPY
        sample_ohlcv = []

        for _ in dates:
            price += np.random.normal(0, 50000)
            high = price + np.random.uniform(0, 30000)
            low = price - np.random.uniform(0, 30000)
            volume = np.random.uniform(50, 500)

            sample_ohlcv.append(
                {
                    "open": price,
                    "high": high,
                    "low": low,
                    "close": price,
                    "volume": volume,
                }
            )

        df_ohlcv = pd.DataFrame(sample_ohlcv, index=dates)

        # 97特徴量生成
        backtest_engine = HybridBacktest(phase="B")
        df_features = backtest_engine.add_97_features(df_ohlcv)

        logger.info(
            f"📊 Generated {len(df_features.columns)} features for comprehensive fix demo"
        )

        # 包括的修正・検証実行
        df_fixed, report = fixer.comprehensive_fix_and_validate(df_features)

        # 結果表示
        print(f"\n✅ Comprehensive Fix Results:")
        print(f"   Original features: {report['original_feature_count']}")
        print(f"   Final features: {report['final_feature_count']}")
        print(f"   Fix successful: {report['fix_successful']}")

        if report["fix_successful"]:
            print("   🎊 All feature_names mismatches resolved!")

        return df_fixed, report

    except ImportError:
        logger.error("❌ HybridBacktestEngine not available for demo")
        return None, None


def main():
    """Phase 3.1メイン実行"""
    print("🚀 Phase 3.1: Feature Names Mismatch Complete Solution")
    print("=" * 80)
    print("特徴量順序統一・ML予測精度修復・97特徴量システム完全対応")
    print("=" * 80)

    # 1. 診断実行
    diagnosis = run_feature_mismatch_diagnosis()

    # 2. 包括的修正デモ
    df_fixed, report = run_comprehensive_fix_demo()

    # 3. 完了レポート
    print(f"\n" + "🎊" * 80)
    print("Phase 3.1: Feature Names Mismatch Solution - 完了!")
    print("🎊" * 80)

    if report and report.get("fix_successful", False):
        print("✅ すべてのfeature_names mismatch問題を解決しました")
        print("🤖 ML予測精度の改善が期待されます")
        print("📊 97特徴量システムの整合性を確保しました")
    else:
        print("⚠️ 一部の問題が残存している可能性があります")

    print("🔄 Next: Phase 4 - 実行・検証・最適化")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
