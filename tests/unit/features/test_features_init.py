"""
features/__init__.py の遅延インポートテスト
"""

import pytest


class TestFeaturesLazyImport:
    """features パッケージの __getattr__ 遅延インポートテスト"""

    def test_import_feature_generator(self):
        """FeatureGeneratorの遅延インポート"""
        from src.features import FeatureGenerator

        assert FeatureGenerator is not None

    def test_import_feature_categories(self):
        """FEATURE_CATEGORIESの遅延インポート"""
        from src.features import FEATURE_CATEGORIES

        assert isinstance(FEATURE_CATEGORIES, dict)

    def test_import_optimized_features(self):
        """OPTIMIZED_FEATURESの遅延インポート"""
        from src.features import OPTIMIZED_FEATURES

        assert isinstance(OPTIMIZED_FEATURES, list)

    def test_import_invalid_attribute(self):
        """存在しない属性でAttributeError"""
        with pytest.raises(AttributeError, match="has no attribute"):
            from src import features

            features.__getattr__("NonExistentClass")
