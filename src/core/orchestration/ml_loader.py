"""
MLサービス モデル読み込み機能 - Phase 18 分割

ProductionEnsemble読み込み・個別モデル再構築・モデル管理機能を提供。
ml_adapter.pyから分離したモデル読み込み専用モジュール。
"""

import pickle
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from ..config import get_threshold
from ..exceptions import FileIOError, ModelLoadError
from ..logger import CryptoBotLogger
from .ml_fallback import DummyModel


class MLModelLoader:
    """MLモデル読み込み管理クラス"""

    def __init__(self, logger: CryptoBotLogger):
        self.logger = logger
        self.model = None
        self.model_type = "Unknown"
        self.is_fitted = False

    def load_model_with_priority(self) -> Any:
        """
        優先順位付きモデル読み込み

        1. ProductionEnsemble（最優先）
        2. 個別モデルから再構築
        3. ダミーモデル（最終フォールバック）

        Returns:
            読み込まれたモデルインスタンス
        """
        self.logger.info("🤖 MLモデル読み込み開始")

        # 1. ProductionEnsemble読み込み試行
        if self._load_production_ensemble():
            return self.model

        # 2. 個別モデルから再構築試行
        if self._load_from_individual_models():
            return self.model

        # 3. 最終フォールバック: ダミーモデル
        self._load_dummy_model()
        return self.model

    def _load_production_ensemble(self) -> bool:
        """ProductionEnsemble読み込み（互換性レイヤー付き）"""
        import os

        # Cloud Run環境とローカル環境の両方に対応
        base_path = "/app" if os.path.exists("/app/models") else "."
        model_path = Path(base_path) / "models/production/production_ensemble.pkl"

        if not model_path.exists():
            self.logger.warning(f"ProductionEnsemble未発見: {model_path}")
            return False

        try:
            # Phase 18対応: 古いPickleファイル互換性レイヤー（完全版）
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
                self.model_type = "ProductionEnsemble"
                self.is_fitted = getattr(self.model, "is_fitted", True)
                self.logger.info("✅ ProductionEnsemble読み込み成功")
                return True
            else:
                self.logger.error("ProductionEnsembleに必須メソッドが不足")
                return False

        except Exception as e:
            self.logger.error(f"ProductionEnsemble読み込みエラー: {e}")
            return False

    def _load_from_individual_models(self) -> bool:
        """個別モデルからProductionEnsemble再構築"""
        import os

        base_path = "/app" if os.path.exists("/app/models") else "."
        training_path = Path(base_path) / "models/training"

        if not training_path.exists():
            self.logger.warning(f"個別モデルディレクトリ未発見: {training_path}")
            return False

        try:
            individual_models = {}
            model_files = {
                "lightgbm": "lightgbm_model.pkl",
                "xgboost": "xgboost_model.pkl",
                "random_forest": "random_forest_model.pkl",
            }

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
        """モデル情報取得"""
        return {
            "model_type": self.model_type,
            "is_fitted": self.is_fitted,
            "has_predict": hasattr(self.model, "predict") if self.model else False,
            "has_predict_proba": hasattr(self.model, "predict_proba") if self.model else False,
        }
