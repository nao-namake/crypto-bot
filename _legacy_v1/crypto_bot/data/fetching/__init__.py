"""
Fetching Integration - Phase 16.3-C Split
統合前: crypto_bot/data/fetcher.py（1,456行）
分割後: crypto_bot/data/fetching/ ディレクトリ

機能:
- 3ファイル分割システムの統合エクスポート
- MarketDataFetcher: API接続・認証・基本データ取得
- DataProcessor: 複雑データ処理・タイムスタンプ検証・ページネーション
- OIDataFetcher: OI（未決済建玉）データ処理
- DataPreprocessor: データ前処理（重複除去・欠損補完・外れ値除去）

Phase 16.3-C実装日: 2025年8月8日
"""

from .data_processor import DataPreprocessor, DataProcessor
from .market_client import MarketDataFetcher
from .oi_fetcher import OIDataFetcher

__all__ = ["MarketDataFetcher", "DataProcessor", "DataPreprocessor", "OIDataFetcher"]
