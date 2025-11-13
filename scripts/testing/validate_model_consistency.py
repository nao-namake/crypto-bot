#!/usr/bin/env python3
"""
Phase 51.5-A: MLモデル特徴量整合性検証スクリプト

目的:
- モデルメタデータと実装の特徴量数の一致を検証
- デプロイ前にローカルで不一致を検出
- Phase 51.5-A問題（60≠62）の再発防止

検証項目:
1. feature_order.jsonの特徴量数
2. production_model_metadata.jsonの特徴量数
3. 有効な戦略数と戦略信号特徴量数の一致
4. モデルファイルの存在確認

使用方法:
    python scripts/testing/validate_model_consistency.py

    または checks.sh から自動実行
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class ModelConsistencyValidator:
    """モデル整合性検証クラス"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate(self) -> bool:
        """全検証を実行"""
        print("🔍 Phase 51.5-A: MLモデル整合性検証開始\n")

        # 1. feature_order.json読み込み
        feature_order_data = self._load_feature_order()
        if not feature_order_data:
            return False

        # 2. production_model_metadata.json読み込み
        model_metadata = self._load_model_metadata()
        if not model_metadata:
            self.warnings.append("⚠️  production_model_metadata.json not found - モデル未訓練の可能性")

        # 3. 有効戦略数カウント
        active_strategies = self._count_active_strategies()

        # 4. 検証実行
        self._validate_feature_counts(feature_order_data, model_metadata)
        self._validate_strategy_signals(feature_order_data, active_strategies)
        self._validate_model_files(feature_order_data)

        # 5. 結果出力
        return self._print_results()

    def _load_feature_order(self) -> Optional[Dict]:
        """feature_order.json読み込み"""
        path = self.project_root / "config/core/feature_order.json"
        if not path.exists():
            self.errors.append(f"❌ {path} not found")
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            print("✅ feature_order.json読み込み成功")
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
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            print("\n✅ production_model_metadata.json読み込み成功")
            print(f"   Phase: {data.get('phase', 'unknown')}")
            print(f"   Feature count: {data.get('training_info', {}).get('feature_count', 'unknown')}")
            print(f"   Feature names count: {len(data.get('feature_names', []))}")
            return data
        except Exception as e:
            self.warnings.append(f"⚠️  production_model_metadata.json読み込みエラー: {e}")
            return None

    def _count_active_strategies(self) -> int:
        """strategies.yamlから有効戦略数をカウント"""
        path = self.project_root / "config/strategies/strategies.yaml"
        if not path.exists():
            self.warnings.append(f"⚠️  {path} not found - 戦略数検証スキップ")
            return 0

        try:
            import yaml

            with open(path, "r", encoding="utf-8") as f:
                strategies_config = yaml.safe_load(f)

            # enabled戦略のみカウント
            active = [s for s in strategies_config.get("strategies", []) if s.get("enabled", False)]
            count = len(active)
            print("\n✅ strategies.yaml読み込み成功")
            print(f"   有効戦略数: {count}")
            for strategy in active:
                print(f"     - {strategy.get('name', 'unknown')}")
            return count
        except Exception as e:
            self.warnings.append(f"⚠️  strategies.yaml読み込みエラー: {e}")
            return 0

    def _validate_feature_counts(self, feature_order_data: Dict, model_metadata: Optional[Dict]) -> None:
        """特徴量数の整合性検証"""
        print("\n" + "=" * 60)
        print("📊 特徴量数整合性検証")
        print("=" * 60)

        # feature_order.jsonの特徴量数
        expected_full = feature_order_data.get("feature_levels", {}).get("full", {}).get("count")
        expected_basic = feature_order_data.get("feature_levels", {}).get("basic", {}).get("count")

        print("\n🎯 期待値 (feature_order.json):")
        print(f"   Full model: {expected_full} features")
        print(f"   Basic model: {expected_basic} features")

        if not model_metadata:
            self.warnings.append("⚠️  モデルメタデータなし - モデル訓練が必要です")
            return

        # モデルメタデータの特徴量数
        actual_feature_count = model_metadata.get("training_info", {}).get("feature_count")
        actual_feature_names_count = len(model_metadata.get("feature_names", []))

        print("\n📦 実際のモデル (production_model_metadata.json):")
        print(f"   training_info.feature_count: {actual_feature_count}")
        print(f"   len(feature_names): {actual_feature_names_count}")

        # 検証
        if actual_feature_count != expected_full:
            self.errors.append(f"❌ 特徴量数不一致: モデル={actual_feature_count}, 期待値={expected_full}")
            self.errors.append(
                "   → モデル再訓練が必要: python3 scripts/ml/create_ml_models.py --model both --n-classes 3 --threshold 0.005 --optimize --n-trials 50"
            )
        else:
            print(f"\n✅ 特徴量数一致: {actual_feature_count} == {expected_full}")

        if actual_feature_names_count != expected_full:
            self.errors.append(f"❌ feature_names数不一致: {actual_feature_names_count} != {expected_full}")

    def _validate_strategy_signals(self, feature_order_data: Dict, active_strategies: int) -> None:
        """戦略信号特徴量の整合性検証"""
        print("\n" + "=" * 60)
        print("🎯 戦略信号特徴量整合性検証")
        print("=" * 60)

        # feature_order.jsonの戦略信号特徴量
        strategy_signals = feature_order_data.get("feature_categories", {}).get("strategy_signals", {})
        expected_signals = len(strategy_signals.get("features", []))

        print("\n🎯 期待値:")
        print(f"   有効戦略数: {active_strategies}")
        print(f"   戦略信号特徴量数: {expected_signals}")

        if active_strategies > 0 and active_strategies != expected_signals:
            self.errors.append(f"❌ 戦略信号数不一致: 有効戦略={active_strategies}, 戦略信号特徴量={expected_signals}")
            self.errors.append("   → feature_order.jsonのstrategy_signalsを更新してください")
        else:
            print(f"\n✅ 戦略信号数一致: {active_strategies} == {expected_signals}")

    def _validate_model_files(self, feature_order_data: Dict) -> None:
        """モデルファイルの存在確認"""
        print("\n" + "=" * 60)
        print("📁 モデルファイル存在確認")
        print("=" * 60)

        # 期待されるモデルファイル
        full_model_file = feature_order_data.get("feature_levels", {}).get("full", {}).get("model_file")
        basic_model_file = feature_order_data.get("feature_levels", {}).get("basic", {}).get("model_file")

        print("\n🎯 期待されるモデルファイル:")
        print(f"   Full: {full_model_file}")
        print(f"   Basic: {basic_model_file}")

        # ファイル存在確認
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
    # プロジェクトルート取得
    project_root = Path(__file__).resolve().parents[2]

    # 検証実行
    validator = ModelConsistencyValidator(project_root)
    success = validator.validate()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
