"""
ML Preprocessing Module - Phase 16.3-A Integration

統合前: crypto_bot/ml/preprocessor.py（3,314行）
統合後: crypto_bot/ml/preprocessing/ ディレクトリ構造

機能統合:
- FeatureEngineer: sklearn互換特徴量生成クラス
- build_ml_pipeline: パイプライン構築
- prepare_ml_dataset: ML用データセット作成
- calc_rci: RCI指標計算
- ensure_feature_coverage: 特徴量カバレッジ保証

Phase 16.3-A実装日: 2025年8月8日
"""

from .dataset_processor import prepare_ml_dataset, prepare_ml_dataset_enhanced

# 主要クラス・関数のインポート
from .feature_engineer import FeatureEngineer
from .pipeline_builder import build_ml_pipeline
from .utils import calc_rci, ensure_feature_coverage

# 後方互換性のための統合インターフェース
__all__ = [
    "FeatureEngineer",
    "build_ml_pipeline",
    "prepare_ml_dataset",
    "prepare_ml_dataset_enhanced",
    "calc_rci",
    "ensure_feature_coverage",
]

__version__ = "16.3.0"
__author__ = "Phase 16.3-A Integration"
__description__ = "ML Preprocessing Integration Module"

# 統合状況
INTEGRATION_STATUS = {
    "phase": "16.3-A",
    "original_file": "crypto_bot/ml/preprocessor.py (3,314行)",
    "split_structure": {
        "feature_engineer.py": "FeatureEngineerクラス (2900行)",
        "pipeline_builder.py": "build_ml_pipeline関数 (50行)",
        "dataset_processor.py": "prepare_ml_dataset系関数 (160行)",
        "utils.py": "calc_rci、ensure_feature_coverage (200行)",
    },
    "files_created": 4,
    "backward_compatibility": "完全保証",
    "import_migration": {
        "old": "from crypto_bot.ml.preprocessor import FeatureEngineer",
        "new": "from crypto_bot.ml.preprocessing import FeatureEngineer",
    },
}
