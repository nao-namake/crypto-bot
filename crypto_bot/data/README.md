# data/ - データ取得・前処理システム

## 📋 概要

**Data Acquisition & Preprocessing System**  
本フォルダは crypto-bot のデータ取得・前処理機能を提供し、各取引所からの市場データ取得、マルチタイムフレーム対応、キャッシュ管理、リアルタイムストリーミングを担当します。

## 🎯 主要機能

### **市場データ取得**
- 各取引所（Bitbank等）からのOHLCVデータ取得
- API認証・レート制限管理
- エラー処理・リトライ機能
- ページネーション対応

### **データ前処理**
- 重複データ除去
- 欠損値補完
- 外れ値検出・除去
- タイムスタンプ正規化

### **マルチタイムフレーム対応**
- 1時間足ベースデータから15分/4時間足生成
- 補間・集約アルゴリズム
- タイムフレーム間同期
- データ品質管理

### **キャッシュ・最適化**
- グローバルキャッシュ管理
- メモリ効率的なデータ保持
- 重複リクエスト防止
- 高速データアクセス

## 📁 ファイル構成

```
data/
├── __init__.py                    # パッケージ初期化
├── fetcher.py                     # 統合エクスポート（互換性レイヤー）
├── fetching/                      # Phase 16.3-C: fetcher.py分割システム
│   ├── __init__.py               # 分割モジュール統合
│   ├── market_client.py          # MarketDataFetcher - 市場データ取得
│   ├── data_processor.py         # DataProcessor/DataPreprocessor - 前処理
│   └── oi_fetcher.py             # OIDataFetcher - オープンインタレスト
├── multi_timeframe_fetcher.py     # マルチタイムフレーム対応
├── timeframe_synchronizer.py      # タイムフレーム間同期
├── global_cache_manager.py        # グローバルキャッシュ管理
├── scheduled_data_fetcher.py      # スケジュールベース取得
└── streamer.py                    # リアルタイムストリーミング
```

## 🔍 各ファイルの役割

### **fetcher.py（Phase 16.3-C互換性レイヤー）**
- 既存import文の完全下位互換保証
- `fetching/`分割モジュールからの統合エクスポート
- 26個既存依存関係の無変更動作
- レガシーコードとの完全互換性

### **fetching/market_client.py**
- `MarketDataFetcher`クラス - メインのデータ取得
- 取引所API統合（CCXT経由）
- 認証・レート制限管理
- エラーハンドリング・リトライ実装（588行）

### **fetching/data_processor.py** (Phase 18更新: 2025年8月9日)
- `DataProcessor`クラス - 基本データ処理
- `DataPreprocessor`クラス - 高度前処理
- 重複除去・欠損値補完・外れ値処理
- タイムスタンプ正規化（444行）
- **Phase 18改善**:
  - タイムスタンプ検証強化（未来・過去の異常値修正）
  - Bitbank API制限対応（72時間以内制限）
  - timeframe別の取得間隔調整（15m/1h/4h対応）

### **fetching/oi_fetcher.py**
- `OIDataFetcher`クラス - オープンインタレスト取得
- 専門的市場データ処理
- 取引所固有API対応（424行）

### **multi_timeframe_fetcher.py**
- `MultiTimeframeDataFetcher`クラス - マルチタイムフレーム管理
- 1時間足から15分足への補間（線形/スプライン）
- 1時間足から4時間足への集約
- データ同期・整合性確保
- Phase 2.1実装

### **timeframe_synchronizer.py**
- `TimeframeSynchronizer`クラス - タイムフレーム同期
- 異なるタイムフレーム間のタイムスタンプ調整
- データ欠損部分の検出・補完
- 同期品質メトリクス計算

### **global_cache_manager.py**
- `GlobalCacheManager`シングルトンクラス
- メモリ内データキャッシュ
- TTL（Time To Live）管理
- キャッシュヒット率最適化
- メモリ使用量監視

### **scheduled_data_fetcher.py**
- `ScheduledDataFetcher`クラス - 定期実行取得
- cronライクなスケジューリング
- バックグラウンドデータ更新
- エラー時の自動リカバリ

### **streamer.py**
- `DataStreamer`クラス - リアルタイムデータ
- WebSocketベースのストリーミング
- リアルタイム価格更新
- イベント駆動型処理

## 🚀 使用方法

### **基本的なデータ取得（Phase 16.3-C完全互換）**
```python
# 既存import文は完全に動作（互換性レイヤー）
from crypto_bot.data.fetcher import MarketDataFetcher

fetcher = MarketDataFetcher(
    exchange_name="bitbank",
    api_key=os.getenv("BITBANK_API_KEY"),
    api_secret=os.getenv("BITBANK_API_SECRET")
)

# OHLCVデータ取得（実装は fetching/market_client.py）
df = fetcher.fetch_ohlcv(
    symbol="BTC/JPY",
    timeframe="1h",
    limit=1000
)
```

### **新しい分割モジュール直接使用**
```python
# 直接的な分割モジュール使用（新機能用）
from crypto_bot.data.fetching import MarketDataFetcher, DataProcessor

# より明確な責任分離
fetcher = MarketDataFetcher(exchange_id="bitbank")
processor = DataProcessor()
```

### **マルチタイムフレームデータ取得**
```python
from crypto_bot.data.multi_timeframe_fetcher import MultiTimeframeDataFetcher

mtf_fetcher = MultiTimeframeDataFetcher()
multi_data = mtf_fetcher.fetch_multi_timeframe(
    symbol="BTC/JPY",
    timeframes=["15m", "1h", "4h"],
    limit=500
)
```

### **データ前処理**
```python
from crypto_bot.data.fetcher import DataPreprocessor

preprocessor = DataPreprocessor()
clean_df = preprocessor.preprocess(
    df,
    remove_duplicates=True,
    fill_missing=True,
    remove_outliers=True
)
```

## ⚠️ 課題・改善点

### **パフォーマンス最適化**
- 大量データ取得時のメモリ使用量
- API呼び出しの効率化
- より高度なキャッシュ戦略

### **Phase 16.3-C分割効果検証**
- **1,456行→3ファイル分割完了**: 保守性劇的向上
- **96%コード削減**: fetcher.py（1,456行→59行互換レイヤー）
- **責任分離実現**: 市場データ取得・前処理・OI取得の明確分離
- **既存互換性100%**: 26個既存依存関係の無影響動作

### **エラーハンドリング**
- より詳細なエラー分類
- 取引所固有エラーの適切な処理
- リトライ戦略の最適化

### **リアルタイム対応強化**
- WebSocketの安定性向上
- 遅延の最小化
- データ同期の改善

## 📝 今後の展開

### **Phase 16.3-C分割システム完成効果**
1. **モジュラーアーキテクチャ確立**
   - 責任明確化：市場データ・前処理・OI専門化
   - 保守性向上：ファイル分割による可読性向上
   - テスト容易性：単一責任による単体テスト簡素化

2. **データソース拡張基盤**
   - 複数取引所統合：market_client.py拡張
   - オルタナティブデータ：data_processor.py統合
   - 専門データ：oi_fetcher.py類似モジュール追加

3. **処理効率化最適化**
   - 並列データ取得：各クラス独立並列処理
   - 増分更新：専門化による最適化実装
   - データ圧縮：前処理専門化による高度最適化

4. **統合強化・次世代対応**
   - MLパイプライン密結合：preprocessor連携強化
   - リアルタイム特徴量：market_client.py即時処理
   - ストリーミング分析：専門モジュール追加対応