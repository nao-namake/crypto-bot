"""
データ層

最終更新: 2025/11/16 (Phase 52.4-B)

AI自動取引システムのデータ層。
Bitbank API統合・高速キャッシング・データ品質保証を提供。

主要コンポーネント:
- BitbankClient: Bitbank API接続・証拠金維持率監視・SSL証明書対応
- DataPipeline: マルチタイムフレーム対応・エラーハンドリング・リトライ機構
- DataCache: LRUキャッシング・高速データアクセス・メモリ効率化

開発履歴:
- Phase 52.4-B: コード整理・ドキュメント統一
- Phase 49: バックテスト対応・データ品質保証強化
"""

from .bitbank_client import BitbankClient, create_margin_client, get_bitbank_client
from .data_cache import CacheMetadata, DataCache, LRUCache, get_data_cache
from .data_pipeline import (
    DataPipeline,
    DataRequest,
    TimeFrame,
    fetch_market_data,
    get_data_pipeline,
)

__all__ = [
    "BitbankClient",
    "get_bitbank_client",
    "create_margin_client",
    "DataPipeline",
    "TimeFrame",
    "DataRequest",
    "get_data_pipeline",
    "fetch_market_data",
    "DataCache",
    "LRUCache",
    "CacheMetadata",
    "get_data_cache",
]
