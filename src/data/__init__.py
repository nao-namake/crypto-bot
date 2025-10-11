"""
データ層 - Phase 38.4完了

AI自動取引システムのデータ層。
主要コンポーネント:
- Bitbank API接続・保証金維持率監視
- マルチタイムフレーム対応
- 高速キャッシング
- データ品質保証・SSL証明書セキュリティ対応.
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
