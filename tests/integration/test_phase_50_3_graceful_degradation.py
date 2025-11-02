"""
Phase 51.5-A 統合テスト: 2段階Graceful Degradation

MLモデルの2段階Graceful Degradation (full 60 → basic 57 → Dummy) を検証。
Phase 51.5-A: 5戦略→3戦略削減により60特徴量に更新。
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.logger import get_logger
from src.core.orchestration.ml_loader import MLModelLoader


@pytest.fixture
def logger():
    """ロガーインスタンス"""
    return get_logger()


class TestMLLoader2StageGracefulDegradation:
    """MLLoader 2段階Graceful Degradationテスト（Phase 51.5-A: 60→57→Dummy）"""

    def test_determine_feature_level_60_features(self, logger):
        """特徴量レベル判定テスト（60特徴量 → full - Phase 51.5-A）"""
        loader = MLModelLoader(logger=logger)

        level = loader._determine_feature_level(feature_count=60)
        assert level == "full"

    def test_determine_feature_level_57_features(self, logger):
        """特徴量レベル判定テスト（57特徴量 → basic - Phase 51.5-A）"""
        loader = MLModelLoader(logger=logger)

        level = loader._determine_feature_level(feature_count=57)
        assert level == "basic"

    def test_determine_feature_level_unknown_features(self, logger):
        """特徴量レベル判定テスト（想定外の特徴量数 → fullフォールバック）"""
        loader = MLModelLoader(logger=logger)

        level = loader._determine_feature_level(feature_count=99)
        assert level == "full"  # Phase 51.5-A: fullにフォールバック

    def test_determine_feature_level_none(self, logger):
        """特徴量レベル判定テスト（特徴量数未指定 → fullデフォルト）"""
        loader = MLModelLoader(logger=logger)

        level = loader._determine_feature_level(feature_count=None)
        assert level == "full"  # Phase 51.5-A: fullがデフォルト

    def test_load_production_ensemble_level_full(self, logger):
        """ProductionEnsemble読み込みテスト（full: 60特徴量 - Phase 51.5-A）"""
        loader = MLModelLoader(logger=logger)

        # Phase 51.5-A: ensemble_full.pkl（60特徴量）
        model_path = Path("models/production/ensemble_full.pkl")
        if not model_path.exists():
            pytest.skip("ensemble_full.pkl not found")

        success = loader._load_production_ensemble(level="full")

        if success:
            assert loader.feature_level == "full"
            assert "full" in loader.model_type.lower()

    def test_load_production_ensemble_level_basic(self, logger):
        """ProductionEnsemble読み込みテスト（basic: 57特徴量 - Phase 51.5-A）"""
        loader = MLModelLoader(logger=logger)

        # Phase 51.5-A: ensemble_basic.pkl（57特徴量）
        model_path = Path("models/production/ensemble_basic.pkl")
        if not model_path.exists():
            pytest.skip("ensemble_basic.pkl not found")

        success = loader._load_production_ensemble(level="basic")

        if success:
            assert loader.feature_level == "basic"
            assert "basic" in loader.model_type.lower()

    def test_load_model_with_priority_dummy_fallback(self, logger):
        """load_model_with_priority ダミーモデルフォールバックテスト"""
        loader = MLModelLoader(logger=logger)

        # 全てのモデルファイルが存在しないことをシミュレート
        with patch.object(loader, "_load_production_ensemble", return_value=False):
            with patch.object(loader, "_load_from_individual_models", return_value=False):
                model = loader.load_model_with_priority(feature_count=60)

        # ダミーモデルにフォールバック
        assert model is not None
        assert loader.model_type == "DummyModel"

    def test_get_model_info_with_feature_level(self, logger):
        """get_model_info特徴量レベル情報テスト"""
        loader = MLModelLoader(logger=logger)
        loader.load_model_with_priority()

        model_info = loader.get_model_info()

        assert "feature_level" in model_info
        # Phase 50.9: full, basic, unknownのいずれか（full_with_external削除）
        assert model_info["feature_level"] in [
            "full",
            "basic",
            "unknown",
        ]
