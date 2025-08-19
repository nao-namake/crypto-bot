"""
ML Preprocessor - Phase 16.3-A Integration Compatibility Layer

統合前: crypto_bot/ml/preprocessor.py（3,314行 - 単一ファイル）
統合後: crypto_bot/ml/preprocessing/ ディレクトリ構造

この統合ファイルは既存のimport文の後方互換性を保証します。

# 既存のimport（継続動作）
from crypto_bot.ml.preprocessor import FeatureEngineer
from crypto_bot.ml.preprocessor import build_ml_pipeline
from crypto_bot.ml.preprocessor import prepare_ml_dataset

# 新しいimport（推奨）
from crypto_bot.ml.preprocessing import FeatureEngineer
from crypto_bot.ml.preprocessing import build_ml_pipeline
from crypto_bot.ml.preprocessing import prepare_ml_dataset

Phase 16.3-A実装日: 2025年8月8日
巨大ファイル分割完了: 3,314行 → 4ファイル（平均800行）
"""

# Phase 16.15: 未使用import削除（compatibility layerでは不要）
# 個別モジュールで必要な箇所でのみimport

# 統合preprocessingディレクトリからのimport（後方互換性保証）
from crypto_bot.ml.preprocessing import (
    FeatureEngineer,
    build_ml_pipeline,
    calc_rci,
    ensure_feature_coverage,
    prepare_ml_dataset,
    prepare_ml_dataset_enhanced,
)

# __all__定義（既存コードとの互換性）
__all__ = [
    "FeatureEngineer",
    "build_ml_pipeline",
    "prepare_ml_dataset",
    "prepare_ml_dataset_enhanced",
    "calc_rci",
    "ensure_feature_coverage",
]

# Phase 16.3-A統合メタデータ
__split_info__ = {
    "original_size": "3,314行",
    "split_files": 4,
    "split_directory": "crypto_bot/ml/preprocessing/",
    "backward_compatibility": "✅ 完全保証",
    "migration_path": {
        "from": "from crypto_bot.ml.preprocessor import FeatureEngineer",
        "to": "from crypto_bot.ml.preprocessing import FeatureEngineer",
        "status": "両方のimportが動作継続",
    },
}
