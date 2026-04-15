#!/usr/bin/env python3
"""
Phase 61: ML検証統合スクリプト

統合元:
- Phase 54.7: validate_model_performance.py
- Phase 54.8: validate_ml_prediction_distribution.py
- Phase 51.5-A/55.7: validate_model_consistency.py
検証項目:
1. モデルファイル整合性
2. 特徴量数整合性
3. full/basicモデル差異（MD5比較）
4. 3クラス分類確認
5. 予測分布検証
6. 信頼度統計
7. 個別モデル性能

使用方法:
    # 全検証
    python scripts/testing/validate_ml_models.py

    # 特定検証のみ
    python scripts/testing/validate_ml_models.py --check consistency
    python scripts/testing/validate_ml_models.py --check distribution
    python scripts/testing/validate_ml_models.py --check performance

    # 軽量モード（実データ読み込みなし・高速）
    python scripts/testing/validate_ml_models.py --quick
"""

import argparse
import hashlib
import json
import pickle
import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))


class MLModelValidator:
    """MLモデル統合検証クラス"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.model = None
        self.metadata = None
        self.feature_order_data = None

    # ========================================
    # 整合性検証（consistency）
    # ========================================

    def _load_feature_order(self) -> Optional[Dict]:
        """feature_order.json読み込み"""
        path = self.project_root / "config/core/feature_order.json"
        if not path.exists():
            self.errors.append(f"❌ {path} not found")
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"✅ feature_order.json読み込み成功")
            print(f"   Phase: {data.get('phase', 'unknown')}")
            print(f"   Total features: {data.get('total_features', 'unknown')}")
            return data
        except Exception as e:
            self.errors.append(f"❌ feature_order.json読み込みエラー: {e}")
            return None

    def _load_model_metadata(self) -> Optional[Dict]:
        """production_model_metadata.json読み込み"""
        path = self.project_root / "models/production/production_model_metadata.json"
        if not path.exists():
            self.warnings.append(
                "⚠️  production_model_metadata.json not found - モデル未訓練の可能性"
            )
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"\n✅ production_model_metadata.json読み込み成功")
            print(f"   Phase: {data.get('phase', 'unknown')}")
            print(
                f"   Feature count: {data.get('training_info', {}).get('feature_count', 'unknown')}"
            )
            return data
        except Exception as e:
            self.warnings.append(f"⚠️  production_model_metadata.json読み込みエラー: {e}")
            return None

    def _count_active_strategies(self) -> int:
        """thresholds.yamlから有効戦略数をカウント"""
        path = self.project_root / "config/core/thresholds.yaml"
        if not path.exists():
            self.warnings.append(f"⚠️  {path} not found - 戦略数検証スキップ")
            return 0

        try:
            import yaml

            with open(path, "r", encoding="utf-8") as f:
                thresholds_config = yaml.safe_load(f)

            strategies = thresholds_config.get("strategies", {})
            if isinstance(strategies, dict):
                active = [
                    (name, cfg) for name, cfg in strategies.items() if cfg.get("enabled", False)
                ]
                count = len(active)
                print(f"\n✅ config/core/thresholds.yaml 戦略読み込み成功")
                print(f"   有効戦略数: {count}")
                for name, _ in active:
                    print(f"     - {name}")
            else:
                active = [s for s in strategies if s.get("enabled", False)]
                count = len(active)
            return count
        except Exception as e:
            self.warnings.append(f"⚠️  config/core/thresholds.yaml 戦略読み込みエラー: {e}")
            return 0

    def validate_feature_counts(self) -> None:
        """特徴量数の整合性検証"""
        print("\n" + "=" * 60)
        print("📊 特徴量数整合性検証")
        print("=" * 60)

        if not self.feature_order_data:
            return

        expected_full = (
            self.feature_order_data.get("feature_levels", {}).get("full", {}).get("count")
        )
        expected_basic = (
            self.feature_order_data.get("feature_levels", {}).get("basic", {}).get("count")
        )

        print(f"\n🎯 期待値 (feature_order.json):")
        print(f"   Full model: {expected_full} features")
        print(f"   Basic model: {expected_basic} features")

        if not self.metadata:
            self.warnings.append("⚠️  モデルメタデータなし - モデル訓練が必要です")
            return

        actual_feature_count = self.metadata.get("training_info", {}).get("feature_count")
        actual_feature_names_count = len(self.metadata.get("feature_names", []))

        print(f"\n📦 実際のモデル:")
        print(f"   training_info.feature_count: {actual_feature_count}")
        print(f"   len(feature_names): {actual_feature_names_count}")

        if actual_feature_count != expected_full:
            self.errors.append(
                f"❌ 特徴量数不一致: モデル={actual_feature_count}, 期待値={expected_full}"
            )
        else:
            print(f"\n✅ 特徴量数一致: {actual_feature_count} == {expected_full}")

    def validate_strategy_signals(self) -> None:
        """戦略信号特徴量の整合性検証（Phase 77以降は戦略シグナル削除済み）"""
        print("\n" + "=" * 60)
        print("🎯 戦略信号特徴量整合性検証")
        print("=" * 60)

        if not self.feature_order_data:
            return

        active_strategies = self._count_active_strategies()
        strategy_signals = self.feature_order_data.get("feature_categories", {}).get(
            "strategy_signals", {}
        )
        expected_signals = len(strategy_signals.get("features", []))

        print(f"\n🎯 現状:")
        print(f"   有効戦略数: {active_strategies}")
        print(f"   戦略信号特徴量数: {expected_signals}")

        # Phase 77: SHAP importance=0 の戦略シグナル6個を削除。
        # strategy_signals特徴量が0個でも正常（戦略自体は6個でMLと独立動作）。
        if expected_signals == 0:
            print(
                f"\n✅ Phase 77設計準拠: 戦略シグナル特徴量は削除済み"
                f"（戦略{active_strategies}個は独立動作）"
            )
        elif active_strategies != expected_signals:
            self.warnings.append(
                f"⚠️  戦略信号数不一致（通常はPhase 77で0）: "
                f"有効戦略={active_strategies}, 戦略信号特徴量={expected_signals}"
            )
        else:
            print(f"\n✅ 戦略信号数一致: {active_strategies} == {expected_signals}")

    def validate_model_files(self) -> None:
        """モデルファイルの存在確認"""
        print("\n" + "=" * 60)
        print("📁 モデルファイル存在確認")
        print("=" * 60)

        if not self.feature_order_data:
            return

        full_model_file = (
            self.feature_order_data.get("feature_levels", {}).get("full", {}).get("model_file")
        )
        basic_model_file = (
            self.feature_order_data.get("feature_levels", {}).get("basic", {}).get("model_file")
        )

        print(f"\n🎯 期待されるモデルファイル:")
        print(f"   Full: {full_model_file}")
        print(f"   Basic: {basic_model_file}")

        full_path = self.project_root / f"models/production/{full_model_file}"
        basic_path = self.project_root / f"models/production/{basic_model_file}"

        if full_path.exists():
            print(f"\n✅ {full_model_file} 存在確認")
            print(f"   サイズ: {full_path.stat().st_size / 1024 / 1024:.2f} MB")
        else:
            self.warnings.append(f"⚠️  {full_model_file} not found")

        if basic_path.exists():
            print(f"✅ {basic_model_file} 存在確認")
            print(f"   サイズ: {basic_path.stat().st_size / 1024 / 1024:.2f} MB")
        else:
            self.warnings.append(f"⚠️  {basic_model_file} not found")

    def validate_model_difference(self) -> None:
        """Phase 55.7: full/basicモデルが異なるか検証（MD5比較）"""
        print("\n" + "=" * 60)
        print("🔬 full/basicモデル差異検証")
        print("=" * 60)

        if not self.feature_order_data:
            return

        full_model_file = (
            self.feature_order_data.get("feature_levels", {}).get("full", {}).get("model_file")
        )
        basic_model_file = (
            self.feature_order_data.get("feature_levels", {}).get("basic", {}).get("model_file")
        )

        full_path = self.project_root / f"models/production/{full_model_file}"
        basic_path = self.project_root / f"models/production/{basic_model_file}"

        if not full_path.exists() or not basic_path.exists():
            self.warnings.append("⚠️  モデルファイルが不足 - MD5比較スキップ")
            return

        def get_md5(path: Path) -> str:
            hash_md5 = hashlib.md5()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()

        full_md5 = get_md5(full_path)
        basic_md5 = get_md5(basic_path)

        print(f"\n🎯 MD5ハッシュ:")
        print(f"   Full:  {full_md5}")
        print(f"   Basic: {basic_md5}")

        # Phase 77: Full=Basic=37特徴量の統一モデル構成。MD5一致は設計通り（正常）。
        if full_md5 == basic_md5:
            print(f"\n✅ Phase 77設計準拠: Full=Basic=37特徴量の統一モデル（MD5一致は正常）")
        else:
            print(f"\nℹ️  full/basicモデルは異なる（MD5不一致）")

        full_size = full_path.stat().st_size
        basic_size = basic_path.stat().st_size
        print(f"\n🎯 ファイルサイズ:")
        print(f"   Full:  {full_size / 1024 / 1024:.2f} MB")
        print(f"   Basic: {basic_size / 1024 / 1024:.2f} MB")

        # Phase 77: Full=Basic統一のためサイズ一致が正常。警告は不要。
        if full_md5 != basic_md5 and full_size <= basic_size:
            self.warnings.append(f"⚠️  fullモデル <= basicモデル - 通常はfull > basic")

    def validate_n_classes(self) -> None:
        """Phase 73-B: モデルのクラス数検証（2クラスまたは3クラス）"""
        print("\n" + "=" * 60)
        print("🔬 分類クラス数検証")
        print("=" * 60)

        n_classes = None

        if self.metadata:
            n_classes = self.metadata.get("training_info", {}).get("n_classes")

        if n_classes is None and self.model:
            if hasattr(self.model, "n_classes"):
                n_classes = self.model.n_classes
            elif hasattr(self.model, "models"):
                for m in self.model.models.values():
                    if hasattr(m, "classes_"):
                        n_classes = len(m.classes_)
                        break

        if n_classes is None:
            full_path = self.project_root / "models/production/ensemble_full.pkl"
            if full_path.exists():
                try:
                    with open(full_path, "rb") as f:
                        model = pickle.load(f)
                    if hasattr(model, "n_classes"):
                        n_classes = model.n_classes
                    elif hasattr(model, "models"):
                        for m in model.models.values():
                            if hasattr(m, "classes_"):
                                n_classes = len(m.classes_)
                                break
                except Exception as e:
                    self.warnings.append(f"⚠️  モデル読み込みエラー: {e}")
                    return

        print(f"\n🎯 検出されたクラス数: {n_classes}")

        if n_classes is None:
            self.warnings.append("⚠️  クラス数を特定できませんでした")
        elif n_classes == 2:
            print(f"\n✅ 2クラス分類（DOWN/UP）確認（Phase 73-B: バイナリ分類）")
        elif n_classes == 3:
            print(f"\n✅ 3クラス分類（BUY/HOLD/SELL）確認")
        else:
            self.warnings.append(f"⚠️  予期しないクラス数: {n_classes}")

    # ========================================
    # 予測分布検証（distribution）
    # ========================================

    def _load_real_data(self, n_samples: int = 300) -> Optional[pd.DataFrame]:
        """実データを読み込む（全期間から均等サンプリング）"""
        data_path = self.project_root / "src/backtest/data/historical/BTC_JPY_15m.csv"
        if not data_path.exists():
            self.errors.append(f"❌ データファイルが見つかりません: {data_path}")
            return None

        try:
            df = pd.read_csv(data_path)
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                df = df.set_index("timestamp")
                df.index = pd.DatetimeIndex(df.index)
            # 全期間から均等サンプリング（市場レジームの偏りを排除）
            if len(df) > n_samples:
                step = len(df) // n_samples
                df = df.iloc[::step].tail(n_samples)
            return df
        except Exception as e:
            self.errors.append(f"❌ データ読み込み失敗: {e}")
            return None

    def _generate_features(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """特徴量を生成"""
        try:
            from src.features.feature_generator import FeatureGenerator

            generator = FeatureGenerator()
            return generator.generate_features_sync(df)
        except Exception as e:
            self.errors.append(f"❌ 特徴量生成失敗: {e}")
            return None

    def _load_model(self) -> bool:
        """モデル読み込み"""
        model_path = self.project_root / "models/production/ensemble_full.pkl"

        if not model_path.exists():
            self.warnings.append(f"⚠️  モデルファイルが見つかりません: {model_path}")
            return False

        try:
            with open(model_path, "rb") as f:
                self.model = pickle.load(f)
            return True
        except Exception as e:
            self.errors.append(f"❌ モデル読み込みエラー: {e}")
            return False

    def validate_prediction_distribution(self) -> None:
        """予測分布検証（Phase 64: メタデータベース方式）"""
        print("\n" + "=" * 60)
        print("📊 予測分布検証（メタデータベース）")
        print("=" * 60)

        # メタデータからクラス分布を読み取り
        metadata_path = self.project_root / "models/production/production_model_metadata.json"
        if not metadata_path.exists():
            self.errors.append(f"❌ メタデータが見つかりません: {metadata_path}")
            return

        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except Exception as e:
            self.errors.append(f"❌ メタデータ読み込みエラー: {e}")
            return

        training_info = metadata.get("training_info", {})
        class_dist = training_info.get("class_distribution", {})

        # Phase 73-B: バイナリ分類ではclass_distributionが空の場合がある
        if not class_dist:
            # モデルのクラス数を確認
            n_classes = training_info.get("n_classes", None)
            if n_classes == 2:
                print("\n✅ バイナリ分類モデル - class_distribution検証スキップ")
                return
            # 3クラスモデルで空は問題
            self.warnings.append("⚠️  メタデータにclass_distributionがありません")
            return

        sell_pct = class_dist.get("sell", class_dist.get("0", 0))
        if isinstance(sell_pct, float) and sell_pct <= 1:
            sell_pct *= 100
        hold_pct = class_dist.get("hold", class_dist.get("1", 0))
        if isinstance(hold_pct, float) and hold_pct <= 1:
            hold_pct *= 100
        buy_pct = class_dist.get("buy", class_dist.get("2", 0))
        if isinstance(buy_pct, float) and buy_pct <= 1:
            buy_pct *= 100

        print(f"\n🎯 訓練時クラス分布（メタデータ）:")
        print(f"   SELL: {sell_pct:.1f}%")
        print(f"   HOLD: {hold_pct:.1f}%")
        print(f"   BUY:  {buy_pct:.1f}%")

        max_pct = max(sell_pct, hold_pct, buy_pct)
        print(f"   最大クラス比率: {max_pct:.1f}%")

        MAX_CLASS_THRESHOLD = 80.0
        MIN_CLASS_THRESHOLD = 5.0

        if max_pct >= MAX_CLASS_THRESHOLD:
            self.errors.append(
                f"❌ 極端なクラスバイアス（最大クラス: {max_pct:.1f}% >= {MAX_CLASS_THRESHOLD}%）"
            )
        else:
            print(f"\n✅ クラスバランス良好（最大クラス: {max_pct:.1f}% < {MAX_CLASS_THRESHOLD}%）")

        if min(sell_pct, buy_pct) < MIN_CLASS_THRESHOLD:
            self.warnings.append(
                f"⚠️  BUY/SELLの一方が{MIN_CLASS_THRESHOLD}%未満"
                f"（SELL:{sell_pct:.1f}%, BUY:{buy_pct:.1f}%）"
            )

    # ========================================
    # 性能検証（performance）
    # ========================================

    def validate_confidence_stats(self) -> None:
        """信頼度統計検証（実データが必要・不在時はスキップ）"""
        print("\n" + "=" * 60)
        print("📊 信頼度統計検証")
        print("=" * 60)

        if self.model is None:
            if not self._load_model():
                return

        df = self._load_real_data(n_samples=100)
        if df is None:
            # Phase 64: データ不在時はスキップ（CI環境ではデータなし）
            print("\nℹ️  実データなし - 信頼度統計検証スキップ")
            # エラーリストから _load_real_data が追加したエラーを除去
            self.errors = [e for e in self.errors if "データファイルが見つかりません" not in e]
            return

        features_df = self._generate_features(df)
        if features_df is None:
            return

        try:
            expected_features = (
                self.model.feature_names if hasattr(self.model, "feature_names") else []
            )

            test_df = features_df.copy()
            for f in expected_features:
                if f not in test_df.columns:
                    test_df[f] = 0.0

            X_test = test_df[expected_features].values
            X_test = np.nan_to_num(X_test, nan=0.0)

            probabilities = self.model.predict_proba(X_test)
            max_probs = np.max(probabilities, axis=1)

            print(f"\n🎯 信頼度統計:")
            print(f"   平均: {np.mean(max_probs):.3f}")
            print(f"   最小: {np.min(max_probs):.3f}")
            print(f"   最大: {np.max(max_probs):.3f}")
            print(f"   標準偏差: {np.std(max_probs):.3f}")

            high_conf = np.sum(max_probs > 0.6) / len(max_probs) * 100
            print(f"   高信頼度(>60%): {high_conf:.1f}%")

            if high_conf < 5:
                self.warnings.append(f"⚠️  高信頼度予測が少ない（{high_conf:.1f}%）")
            else:
                print(f"\n✅ 信頼度統計正常")

        except Exception as e:
            self.errors.append(f"❌ 信頼度統計計算失敗: {e}")

    def validate_individual_models(self) -> None:
        """個別モデルの検証"""
        print("\n" + "=" * 60)
        print("🔍 個別モデル検証")
        print("=" * 60)

        if self.model is None:
            if not self._load_model():
                return

        if not hasattr(self.model, "models"):
            print("⚠️ 個別モデルへのアクセス不可")
            return

        for name, model in self.model.models.items():
            print(f"\n📊 {name}:")
            print(f"   タイプ: {type(model).__name__}")

            if hasattr(model, "n_estimators"):
                print(f"   n_estimators: {model.n_estimators}")
            if hasattr(model, "n_features_in_"):
                print(f"   n_features_in_: {model.n_features_in_}")
            if hasattr(model, "classes_"):
                print(f"   classes_: {model.classes_}")

            if self.metadata:
                perf = self.metadata.get("performance_metrics", {}).get(name, {})
                if perf:
                    print(f"   訓練時性能:")
                    if "accuracy" in perf:
                        print(f"     Accuracy: {perf['accuracy']:.3f}")
                    if "f1_score" in perf:
                        print(f"     F1 Score: {perf['f1_score']:.3f}")
                    if "cv_f1_mean" in perf:
                        print(f"     CV F1 Mean: {perf['cv_f1_mean']:.3f}")

        print(f"\n✅ 個別モデル検証完了")

    # ========================================
    # 統合実行
    # ========================================

    def run_consistency(self) -> None:
        """整合性検証を実行"""
        print("\n" + "=" * 60)
        print("🔍 整合性検証開始")
        print("=" * 60)

        self.feature_order_data = self._load_feature_order()
        self.metadata = self._load_model_metadata()

        self.validate_feature_counts()
        self.validate_strategy_signals()
        self.validate_model_files()
        self.validate_model_difference()
        self.validate_n_classes()

    def run_distribution(self) -> None:
        """予測分布検証を実行"""
        self.validate_prediction_distribution()

    def run_performance(self) -> None:
        """性能検証を実行"""
        self.validate_confidence_stats()
        self.validate_individual_models()

    def run_all(self, quick: bool = False) -> bool:
        """全検証を実行"""
        print("\n" + "=" * 60)
        print("🚀 Phase 61: ML検証統合スクリプト開始")
        print("=" * 60)

        # 整合性検証（常に実行）
        self.run_consistency()

        # 実データ検証（quickモードでスキップ）
        if not quick:
            self.run_distribution()
            self.run_performance()
        else:
            print("\n⏭️  --quick モード: 実データ検証スキップ")

        return self._print_results()

    def _print_results(self) -> bool:
        """検証結果を出力"""
        print("\n" + "=" * 60)
        print("📋 検証結果サマリー")
        print("=" * 60)

        if self.errors:
            print(f"\n❌ エラー: {len(self.errors)}件")
            for error in self.errors:
                print(f"   {error}")

        if self.warnings:
            print(f"\n⚠️  警告: {len(self.warnings)}件")
            for warning in self.warnings:
                print(f"   {warning}")

        if not self.errors and not self.warnings:
            print("\n✅ すべての検証に合格しました！")
            return True
        elif not self.errors:
            print("\n✅ エラーなし（警告のみ）")
            return True
        else:
            print("\n❌ 検証失敗 - 上記エラーを修正してください")
            return False


def main() -> int:
    """メイン処理"""
    parser = argparse.ArgumentParser(description="Phase 61: ML検証統合スクリプト")
    parser.add_argument(
        "--check",
        choices=["all", "consistency", "distribution", "performance"],
        default="all",
        help="検証タイプを指定（デフォルト: all）",
    )
    parser.add_argument(
        "--quick", action="store_true", help="軽量モード（実データ読み込みなし・高速）"
    )

    args = parser.parse_args()

    validator = MLModelValidator(PROJECT_ROOT)

    if args.check == "all":
        success = validator.run_all(quick=args.quick)
    elif args.check == "consistency":
        validator.feature_order_data = validator._load_feature_order()
        validator.metadata = validator._load_model_metadata()
        validator.run_consistency()
        success = validator._print_results()
    elif args.check == "distribution":
        validator.run_distribution()
        success = validator._print_results()
    elif args.check == "performance":
        validator.metadata = validator._load_model_metadata()
        validator.run_performance()
        success = validator._print_results()
    else:
        success = False

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
