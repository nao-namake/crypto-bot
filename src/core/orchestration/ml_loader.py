"""
MLサービス モデル読み込み機能 - Phase 50.8完了

ProductionEnsemble読み込み・個別モデル再構築・モデル管理機能を提供。
ml_adapter.pyから分離したモデル読み込み専用モジュール。

Phase 50.8完了:
- 旧モデルパス後方互換性削除（Phase 50.7完全移行）

Phase 50.7完了:
- 3段階MLモデルシステム実装（Phase 50.7モデル名固定化）
  - Level 1（完全+外部API）: 70特徴量モデル（ensemble_level1.pkl）
  - Level 2（完全）: 62特徴量モデル（ensemble_level2.pkl）
  - Level 3（基本）: 57特徴量モデル（ensemble_level3.pkl）
  - Level 4（ダミー）: DummyModel（最終フォールバック）
- 外部API障害時自動Level 2フォールバック
- レガシーシステム教訓反映: 外部API失敗でもシステム継続動作保証

Phase 50.3完了:
- 4段階Graceful Degradation実装（外部API統合対応）

Phase 50.1完了:
- 3段階Graceful Degradation実装（設定駆動型）
- feature_order.json設定駆動型モデル選択
- 特徴量数自動判定システム
- 動的モデルフォールバック機能

Phase 49完了:
- ProductionEnsemble読み込み
- 個別モデル再構築（LightGBM・XGBoost・RandomForest）
- pickle.UnpicklingError対応（モデルクラス再定義）
- DummyModelフォールバック（読み込み失敗時）

Phase 28-29: MLモデル読み込み専門モジュール分離・互換性レイヤー実装
"""

import pickle
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from ..config import get_threshold
from ..logger import CryptoBotLogger
from .ml_fallback import DummyModel


class MLModelLoader:
    """
    MLモデル読み込み管理クラス - Phase 50.3: 4段階Graceful Degradation対応

    設定駆動型モデル選択により、特徴量レベルに応じた最適なモデルを自動選択。
    外部API障害時は自動的にLevel 2（62特徴量）にフォールバックし、システム継続性を保証。
    """

    def __init__(self, logger: CryptoBotLogger):
        self.logger = logger
        self.model = None
        self.model_type = "Unknown"
        self.is_fitted = False
        self.feature_level = "unknown"  # Phase 50.1: 使用中の特徴量レベル

    def load_model_with_priority(self, feature_count: Optional[int] = None) -> Any:
        """
        Phase 50.7: 3段階MLモデルシステム優先順位読み込み

        Level 1（完全+外部API）: 70特徴量モデル → ensemble_level1.pkl
        Level 2（完全）: 62特徴量モデル → ensemble_level2.pkl
        Level 3（基本）: 57特徴量モデル → ensemble_level3.pkl
        Level 4（ダミー）: DummyModel → 最終フォールバック

        Args:
            feature_count: 生成された特徴量数（Noneの場合は設定から判定）

        Returns:
            読み込まれたモデルインスタンス
        """
        self.logger.info("🤖 MLモデル読み込み開始 - Phase 50.3: 4段階Graceful Degradation")

        # Phase 50.3: 特徴量レベル判定
        target_level = self._determine_feature_level(feature_count)
        self.logger.info(f"特徴量レベル判定: {target_level} ({feature_count}特徴量)")

        # Level 1: 外部API付き完全特徴量モデル読み込み試行（70特徴量）
        if target_level == "full_with_external" and self._load_production_ensemble(
            level="full_with_external"
        ):
            return self.model

        # Level 2: 外部APIなし完全特徴量モデル読み込み試行（62特徴量）
        if target_level in ["full_with_external", "full"] and self._load_production_ensemble(
            level="full"
        ):
            if target_level == "full_with_external":
                self.logger.info("Level 2（外部APIなし）モデルにフォールバック")
            return self.model

        # Level 3: 基本特徴量モデル読み込み試行（57特徴量）
        if target_level in [
            "full_with_external",
            "full",
            "basic",
        ] and self._load_production_ensemble(level="basic"):
            self.logger.info("Level 3（基本）モデルにフォールバック")
            return self.model

        # Level 3.5: 個別モデルから再構築試行（後方互換性）
        if self._load_from_individual_models():
            self.logger.info("Level 3.5（再構築）モデルにフォールバック")
            return self.model

        # Level 4: 最終フォールバック - ダミーモデル
        self._load_dummy_model()
        return self.model

    def _determine_feature_level(self, feature_count: Optional[int] = None) -> str:
        """
        Phase 50.3: 特徴量レベル判定（設定駆動型・外部API対応）

        Args:
            feature_count: 生成された特徴量数

        Returns:
            特徴量レベル文字列（"full_with_external", "full", or "basic"）
        """
        # feature_order.jsonから特徴量レベル情報を取得
        from ..config.feature_manager import _feature_manager

        level_counts = _feature_manager.get_feature_level_counts()

        # feature_countが指定されていない場合は、デフォルトでfull_with_externalを試行
        if feature_count is None:
            self.logger.debug("特徴量数未指定 → Level 1（完全+外部API）を試行")
            return "full_with_external"

        # 70特徴量の場合（外部API含む）- Phase 50.3
        if feature_count == level_counts.get("full_with_external", 70):
            return "full_with_external"

        # 62特徴量の場合（外部APIなし）
        if feature_count == level_counts.get("full", 62):
            return "full"

        # 57特徴量の場合（基本特徴量のみ）
        if feature_count == level_counts.get("basic", 57):
            return "basic"

        # その他の場合はfull_with_externalを試行（フォールバック）
        self.logger.warning(f"想定外の特徴量数: {feature_count} → Level 1（完全+外部API）を試行")
        return "full_with_external"

    def _load_production_ensemble(self, level: str = "full") -> bool:
        """
        Phase 50.3: ProductionEnsemble読み込み（設定駆動型・互換性レイヤー付き・外部API対応）

        Args:
            level: 特徴量レベル（"full_with_external", "full", or "basic"）

        Returns:
            読み込み成功の可否
        """
        import os

        # Cloud Run環境とローカル環境の両方に対応
        cloud_base_path = get_threshold("ml.model_paths.base_path", "/app")
        local_base_path = get_threshold("ml.model_paths.local_path", ".")
        base_path = (
            cloud_base_path if os.path.exists(f"{cloud_base_path}/models") else local_base_path
        )

        # Phase 50.1: feature_order.jsonから設定駆動型でモデルファイル名取得
        from ..config.feature_manager import _feature_manager

        level_info = _feature_manager.get_feature_level_info()

        if level not in level_info:
            self.logger.warning(f"想定外の特徴量レベル: {level} → 読み込みスキップ")
            return False

        model_filename = level_info[level].get("model_file", "ensemble_level2.pkl")
        model_path = Path(base_path) / "models" / "production" / model_filename

        # Phase 50.8.1: 旧モデル後方互換性削除（Phase 50.7完全移行）

        if not model_path.exists():
            self.logger.warning(f"ProductionEnsemble未発見 (Level {level.upper()}): {model_path}")
            return False

        try:
            # Phase 28-29最適化: 古いPickleファイル互換性レイヤー（完全版）
            class EnsembleModule:
                """ensemble サブモジュールのエミュレート"""

                def __init__(self):
                    from src.ml.ensemble import ProductionEnsemble

                    self.ProductionEnsemble = ProductionEnsemble

            class ProductionModule:
                """src.ml.production モジュールのエミュレート"""

                def __init__(self):
                    self.ensemble = EnsembleModule()

            # 階層的モジュールリダイレクト設定
            old_production = sys.modules.get("src.ml.production")
            old_ensemble = sys.modules.get("src.ml.production.ensemble")

            sys.modules["src.ml.production"] = ProductionModule()
            sys.modules["src.ml.production.ensemble"] = EnsembleModule()

            try:
                with open(model_path, "rb") as f:
                    self.model = pickle.load(f)
            finally:
                # リダイレクト後片付け（階層的）
                if old_production is None:
                    sys.modules.pop("src.ml.production", None)
                else:
                    sys.modules["src.ml.production"] = old_production

                if old_ensemble is None:
                    sys.modules.pop("src.ml.production.ensemble", None)
                else:
                    sys.modules["src.ml.production.ensemble"] = old_ensemble

            # モデルの妥当性チェック
            if hasattr(self.model, "predict") and hasattr(self.model, "predict_proba"):
                self.model_type = f"ProductionEnsemble_{level.upper()}"
                self.is_fitted = getattr(self.model, "is_fitted", True)
                self.feature_level = level
                feature_count = level_info[level].get("count", "unknown")
                self.logger.info(
                    f"✅ ProductionEnsemble読み込み成功 (Level {level.upper()}, {feature_count}特徴量)"
                )
                return True
            else:
                self.logger.error("ProductionEnsembleに必須メソッドが不足")
                return False

        except Exception as e:
            self.logger.error(f"ProductionEnsemble読み込みエラー (Level {level.upper()}): {e}")
            return False

    def _load_from_individual_models(self) -> bool:
        """個別モデルからProductionEnsemble再構築"""
        import os

        cloud_base_path = get_threshold("ml.model_paths.base_path", "/app")
        local_base_path = get_threshold("ml.model_paths.local_path", ".")
        base_path = (
            cloud_base_path if os.path.exists(f"{cloud_base_path}/models") else local_base_path
        )

        training_path_str = get_threshold("ml.model_paths.training_path", "models/training")
        training_path = Path(base_path) / training_path_str

        if not training_path.exists():
            self.logger.warning(f"個別モデルディレクトリ未発見: {training_path}")
            return False

        try:
            individual_models = {}
            model_files = get_threshold(
                "ml.model_files",
                {
                    "lightgbm": "lightgbm_model.pkl",
                    "xgboost": "xgboost_model.pkl",
                    "random_forest": "random_forest_model.pkl",
                },
            )

            for model_name, filename in model_files.items():
                model_file = training_path / filename
                if model_file.exists():
                    with open(model_file, "rb") as f:
                        individual_models[model_name] = pickle.load(f)
                    self.logger.info(f"個別モデル読み込み: {model_name}")

            if len(individual_models) > 0:
                # ProductionEnsembleを再構築
                from src.ml.ensemble import ProductionEnsemble

                self.model = ProductionEnsemble(individual_models)
                self.model_type = "ReconstructedEnsemble"
                self.is_fitted = True
                self.logger.info(
                    f"✅ 個別モデルからEnsemble再構築成功 ({len(individual_models)}モデル)"
                )
                return True
            else:
                self.logger.error("有効な個別モデルが見つかりません")
                return False

        except Exception as e:
            self.logger.error(f"個別モデル再構築エラー: {e}")
            return False

    def _load_dummy_model(self) -> None:
        """ダミーモデル読み込み（最終フォールバック）"""
        self.model = DummyModel()
        self.model_type = "DummyModel"
        self.is_fitted = True
        self.logger.warning("⚠️ ダミーモデル使用 - 全てholdシグナルで稼働継続")

    def reload_model(self) -> bool:
        """モデル再読み込み"""
        try:
            old_model_type = self.model_type
            new_model = self.load_model_with_priority()

            if new_model and self.model_type != old_model_type:
                self.logger.info(f"モデル切り替え: {old_model_type} → {self.model_type}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"モデル再読み込みエラー: {e}")
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """
        Phase 50.1: モデル情報取得（特徴量レベル含む）

        Returns:
            モデル情報辞書
        """
        return {
            "model_type": self.model_type,
            "is_fitted": self.is_fitted,
            "feature_level": self.feature_level,  # Phase 50.1追加
            "has_predict": hasattr(self.model, "predict") if self.model else False,
            "has_predict_proba": (hasattr(self.model, "predict_proba") if self.model else False),
        }
