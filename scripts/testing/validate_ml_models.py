#!/usr/bin/env python3
"""
Phase 61: ML検証統合スクリプト

統合元:
- Phase 54.7: validate_model_performance.py
- Phase 54.8: validate_ml_prediction_distribution.py
- Phase 51.5-A/55.7: validate_model_consistency.py
- Phase 59.8: Stacking検証追加

検証項目:
1. モデルファイル整合性
2. 特徴量数整合性
3. full/basicモデル差異（MD5比較）
4. 3クラス分類確認
5. 予測分布検証
6. 信頼度統計
7. 個別モデル性能
8. Stackingモデル検証（Phase 59.8追加）

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
        """strategies.yamlから有効戦略数をカウント"""
        path = self.project_root / "config/strategies.yaml"
        if not path.exists():
            self.warnings.append(f"⚠️  {path} not found - 戦略数検証スキップ")
            return 0

        try:
            import yaml

            with open(path, "r", encoding="utf-8") as f:
                strategies_config = yaml.safe_load(f)

            strategies = strategies_config.get("strategies", {})
            if isinstance(strategies, dict):
                active = [
                    (name, cfg) for name, cfg in strategies.items() if cfg.get("enabled", False)
                ]
                count = len(active)
                print(f"\n✅ strategies.yaml読み込み成功")
                print(f"   有効戦略数: {count}")
                for name, _ in active:
                    print(f"     - {name}")
            else:
                active = [s for s in strategies if s.get("enabled", False)]
                count = len(active)
            return count
        except Exception as e:
            self.warnings.append(f"⚠️  strategies.yaml読み込みエラー: {e}")
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
        """戦略信号特徴量の整合性検証"""
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

        print(f"\n🎯 期待値:")
        print(f"   有効戦略数: {active_strategies}")
        print(f"   戦略信号特徴量数: {expected_signals}")

        if active_strategies > 0 and active_strategies != expected_signals:
            self.errors.append(
                f"❌ 戦略信号数不一致: 有効戦略={active_strategies}, 戦略信号特徴量={expected_signals}"
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

        if full_md5 == basic_md5:
            self.errors.append(
                "❌ full/basicモデルが同一（MD5一致）- create_ml_models.pyのバグの可能性"
            )
        else:
            print(f"\n✅ full/basicモデルは異なる（MD5不一致）")

        full_size = full_path.stat().st_size
        basic_size = basic_path.stat().st_size
        print(f"\n🎯 ファイルサイズ:")
        print(f"   Full:  {full_size / 1024 / 1024:.2f} MB")
        print(f"   Basic: {basic_size / 1024 / 1024:.2f} MB")

        if full_size <= basic_size:
            self.warnings.append(f"⚠️  fullモデル <= basicモデル - 通常はfull > basic")

    def validate_n_classes(self) -> None:
        """Phase 55.7: モデルが3クラス分類か検証"""
        print("\n" + "=" * 60)
        print("🔬 3クラス分類検証")
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
            self.errors.append("❌ モデルが2クラス分類 - 3クラス分類（BUY/HOLD/SELL）が必要")
        elif n_classes == 3:
            print(f"\n✅ 3クラス分類（BUY/HOLD/SELL）確認")
        else:
            self.warnings.append(f"⚠️  予期しないクラス数: {n_classes}")

    def validate_stacking_model(self) -> None:
        """Phase 59.8: Stackingモデル検証"""
        print("\n" + "=" * 60)
        print("🔬 Phase 59.8: Stackingモデル検証")
        print("=" * 60)

        if not self.feature_order_data:
            return

        # feature_order.jsonからStacking定義確認
        stacking_info = self.feature_order_data.get("feature_levels", {}).get("stacking", {})

        if not stacking_info:
            print("\nℹ️  Stackingレベル定義がfeature_order.jsonにありません")
            print("   → stacking_enabled=false時は正常")
            return

        print(f"\n🎯 Stacking定義 (feature_order.json):")
        print(f"   特徴量数: {stacking_info.get('count', 'unknown')}")
        print(f"   モデルファイル: {stacking_info.get('model_file', 'unknown')}")
        print(f"   Meta-Learnerファイル: {stacking_info.get('meta_learner_file', 'unknown')}")
        print(f"   Phase: {stacking_info.get('phase', 'unknown')}")

        # モデルファイル存在確認
        stacking_file = stacking_info.get("model_file", "stacking_ensemble.pkl")
        meta_file = stacking_info.get("meta_learner_file", "meta_learner.pkl")

        stacking_path = self.project_root / f"models/production/{stacking_file}"
        meta_path = self.project_root / f"models/production/{meta_file}"

        if stacking_path.exists():
            print(f"\n✅ {stacking_file} 存在確認")
            print(f"   サイズ: {stacking_path.stat().st_size / 1024 / 1024:.2f} MB")

            # Stackingモデルのロードテスト
            try:
                with open(stacking_path, "rb") as f:
                    stacking_model = pickle.load(f)

                if hasattr(stacking_model, "predict") and hasattr(stacking_model, "predict_proba"):
                    print(f"   predict/predict_proba: ✅ 存在")
                else:
                    self.errors.append("❌ Stackingモデルに必須メソッドが不足")

                if hasattr(stacking_model, "meta_model"):
                    print(f"   meta_model: ✅ 存在")
                else:
                    print(f"   meta_model: ⚠️  内蔵Meta-Learner不存在（外部ファイル使用）")

                if hasattr(stacking_model, "stacking_enabled"):
                    print(f"   stacking_enabled: {stacking_model.stacking_enabled}")

                # Phase 59.8: 特徴量数整合性チェック（重要）
                stacking_n_features = None
                # StackingEnsembleはn_features_属性を直接持つ
                if hasattr(stacking_model, "n_features_"):
                    stacking_n_features = stacking_model.n_features_
                elif hasattr(stacking_model, "models"):
                    # フォールバック: ベースモデルから取得
                    for model_name, base_model in stacking_model.models.items():
                        if hasattr(base_model, "n_features_in_"):
                            stacking_n_features = base_model.n_features_in_
                            break

                if stacking_n_features:
                    print(f"   n_features_in_: {stacking_n_features}")
                    expected_features = stacking_info.get("count", 55)

                    # ensemble_full.pklとの比較
                    full_path = self.project_root / "models/production/ensemble_full.pkl"
                    if full_path.exists():
                        with open(full_path, "rb") as f:
                            full_model = pickle.load(f)
                        full_n_features = None
                        if hasattr(full_model, "models"):
                            for _, base_model in full_model.models.items():
                                if hasattr(base_model, "n_features_in_"):
                                    full_n_features = base_model.n_features_in_
                                    break

                        if full_n_features and stacking_n_features != full_n_features:
                            self.errors.append(
                                f"❌ 特徴量数不一致: Stacking({stacking_n_features}) != Full({full_n_features}) "
                                f"→ Stackingモデル再訓練が必要"
                            )
                            print(f"   ⛔ 特徴量不一致: {stacking_n_features} != {full_n_features}")
                        elif full_n_features:
                            print(
                                f"   ✅ 特徴量一致: Stacking={stacking_n_features}, Full={full_n_features}"
                            )

                    if stacking_n_features != expected_features:
                        self.warnings.append(
                            f"⚠️  Stacking特徴量数が設定と不一致: 実際={stacking_n_features}, 期待={expected_features}"
                        )
                else:
                    self.warnings.append("⚠️  Stackingモデルの特徴量数を取得できませんでした")

            except Exception as e:
                self.errors.append(f"❌ Stackingモデルロードエラー: {e}")
        else:
            print(f"\nℹ️  {stacking_file} 未検出")
            print("   → Stackingモデル未訓練（stacking_enabled=false時は正常）")

        if meta_path.exists():
            print(f"\n✅ {meta_file} 存在確認")
            print(f"   サイズ: {meta_path.stat().st_size / 1024:.2f} KB")
        else:
            print(f"\nℹ️  {meta_file} 未検出")

        # thresholds.yamlからstacking_enabled確認
        try:
            import yaml

            thresholds_path = self.project_root / "config/core/thresholds.yaml"
            if thresholds_path.exists():
                with open(thresholds_path, "r", encoding="utf-8") as f:
                    thresholds = yaml.safe_load(f)

                stacking_enabled = thresholds.get("ensemble", {}).get("stacking_enabled", False)
                print(f"\n🎯 thresholds.yaml設定:")
                print(f"   ensemble.stacking_enabled: {stacking_enabled}")

                if stacking_enabled and not stacking_path.exists():
                    self.errors.append("❌ stacking_enabled=trueだがStackingモデルが存在しません")
        except Exception as e:
            self.warnings.append(f"⚠️  thresholds.yaml読み込みエラー: {e}")

        print(f"\n✅ Stackingモデル検証完了")

    # ========================================
    # 予測分布検証（distribution）
    # ========================================

    def _load_real_data(self, n_samples: int = 200) -> Optional[pd.DataFrame]:
        """実データを読み込む"""
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
            return df.tail(n_samples)
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
        """予測分布検証"""
        print("\n" + "=" * 60)
        print("📊 予測分布検証")
        print("=" * 60)

        print("\n  実データ読み込み中...")
        df = self._load_real_data(n_samples=300)
        if df is None:
            return
        print(f"  データ読み込み完了: {len(df)}行")

        print("  特徴量生成中...")
        features_df = self._generate_features(df)
        if features_df is None:
            return
        print(f"  特徴量生成完了: {len(features_df)}行 x {len(features_df.columns)}列")

        if not self._load_model():
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

            predictions = self.model.predict(X_test)

            unique, counts = np.unique(predictions, return_counts=True)
            distribution = dict(zip(unique, counts))

            total = len(predictions)
            sell_pct = distribution.get(0, 0) / total * 100
            hold_pct = distribution.get(1, 0) / total * 100
            buy_pct = distribution.get(2, 0) / total * 100

            print(f"\n🎯 予測分布:")
            print(f"   SELL: {distribution.get(0, 0)}回 ({sell_pct:.1f}%)")
            print(f"   HOLD: {distribution.get(1, 0)}回 ({hold_pct:.1f}%)")
            print(f"   BUY:  {distribution.get(2, 0)}回 ({buy_pct:.1f}%)")

            max_ratio = max(counts) / total
            print(f"   最大クラス比率: {max_ratio * 100:.1f}%")

            MAX_CLASS_THRESHOLD = 0.90
            WARN_THRESHOLD = 0.80

            if max_ratio >= MAX_CLASS_THRESHOLD:
                self.errors.append(
                    f"❌ 極端なクラスバイアス（最大クラス: {max_ratio * 100:.1f}% >= 90%）"
                )
            elif max_ratio >= WARN_THRESHOLD:
                self.warnings.append(
                    f"⚠️  クラスバランスがやや偏り（最大クラス: {max_ratio * 100:.1f}%）"
                )
            else:
                print(f"\n✅ クラスバランス良好（最大クラス: {max_ratio * 100:.1f}% < 80%）")

            if min(sell_pct, buy_pct) < 5:
                self.warnings.append(
                    f"⚠️  BUY/SELLの一方が5%未満（SELL:{sell_pct:.1f}%, BUY:{buy_pct:.1f}%）"
                )

        except Exception as e:
            self.errors.append(f"❌ 予測分布チェック失敗: {e}")

    # ========================================
    # 性能検証（performance）
    # ========================================

    def validate_confidence_stats(self) -> None:
        """信頼度統計検証"""
        print("\n" + "=" * 60)
        print("📊 信頼度統計検証")
        print("=" * 60)

        if self.model is None:
            if not self._load_model():
                return

        df = self._load_real_data(n_samples=100)
        if df is None:
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
        self.validate_stacking_model()  # Phase 59.8追加

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
