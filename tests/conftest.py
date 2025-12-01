"""
pytest設定ファイル

テスト実行環境の共通設定。
Phase 57.5: プリセットシステム導入に伴い、
テスト環境ではプリセットを無効化して実行。
"""

import pytest


@pytest.fixture(autouse=True)
def clear_preset_cache():
    """
    各テスト前にプリセットキャッシュをクリア

    Phase 57.5: プリセットシステム導入により、
    テスト環境ではthresholds.yamlの値を直接使用するようにする。
    これにより、テストの期待値が安定する。
    """
    from src.core.config import threshold_manager

    # プリセットキャッシュをクリア（プリセットを無効化）
    threshold_manager._preset_cache = {}
    threshold_manager._active_preset_name = None

    yield

    # テスト後もキャッシュをクリア（次のテストに影響しないように）
    threshold_manager._preset_cache = {}
    threshold_manager._active_preset_name = None
    threshold_manager._thresholds_cache = None
