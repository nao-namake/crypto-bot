# src/data/ - データ層

**Phase 28完了・Phase 29セキュリティ強化版**: Bitbank信用取引API統合・保証金監視・マルチタイムフレームデータパイプライン・SSL証明書セキュリティ対応。

## 📂 ファイル構成

```
src/data/
├── __init__.py          # データ層エクスポート（35行）
├── bitbank_client.py    # Bitbank API接続クライアント（750行）
├── data_pipeline.py     # データ取得パイプライン（447行）
└── data_cache.py        # キャッシングシステム（469行）
```

## 🔧 主要コンポーネント

### **bitbank_client.py（750行）**

**目的**: Bitbank信用取引API専用クライアント

**主要機能**:
- ccxtライブラリ・SSL証明書セキュリティ対応
- 信用取引（レバレッジ1.0-2.0倍）対応
- 保証金維持率監視API統合（Phase 27）
- レート制限・エラーハンドリング・自動リトライ

**主要クラス・メソッド**:
```python
class BitbankClient:
    def __init__(self, leverage=1.0)         # 初期化
    def test_connection(self) -> bool        # 接続テスト
    def fetch_ohlcv(self) -> List[List]      # OHLCV取得
    def fetch_ticker(self) -> Dict           # ティッカー取得
    def fetch_balance(self) -> Dict          # 残高取得（認証）
    def create_order(self)                   # 注文発行
    def cancel_order(self)                   # 注文キャンセル
    def fetch_positions(self) -> List        # ポジション照会
    def set_leverage(self)                   # レバレッジ設定

    # Phase 27新機能: 保証金監視API
    def fetch_margin_status(self) -> Dict     # 信用取引口座状況取得（Phase 27新機能）
    def fetch_margin_positions(self) -> List  # 信用取引ポジション一覧取得（Phase 27新機能）

# グローバル関数
get_bitbank_client() -> BitbankClient        # グローバルクライアント取得
create_margin_client() -> BitbankClient      # 新規クライアント作成
```

**使用例**:
```python
from src.data.bitbank_client import get_bitbank_client

client = get_bitbank_client(leverage=1.5)
if client.test_connection():
    ohlcv = client.fetch_ohlcv("BTC/JPY", "1h", limit=100)
    ticker = client.fetch_ticker("BTC/JPY")

    # Phase 27: 保証金監視API
    margin_status = await client.fetch_margin_status()
    margin_ratio = margin_status.get('marginRatio', 0.0)
```

### **data_pipeline.py（447行）**

**目的**: マルチタイムフレーム対応データ取得パイプライン
**タイムフレーム**: 15分足・4時間足の2軸構成

**主要クラス**:
```python
class TimeFrame(Enum):
    M15 = "15m"    # 15分足
    H4 = "4h"      # 4時間足

@dataclass
class DataRequest:
    symbol: str = "BTC/JPY"
    timeframe: TimeFrame = TimeFrame.H4
    limit: int = 1000
    since: Optional[int] = None

class DataPipeline:
    def fetch_ohlcv(self) -> pd.DataFrame         # 単一タイムフレーム取得
    def fetch_multi_timeframe(self) -> Dict       # 全タイムフレーム取得
    def get_latest_prices(self) -> Dict           # 最新価格取得
    def clear_cache(self)                         # キャッシュクリア
    def get_cache_info(self) -> Dict              # キャッシュ情報

# 簡易インターフェース
fetch_market_data() -> pd.DataFrame               # 簡単データ取得
get_data_pipeline() -> DataPipeline              # グローバルパイプライン取得
```

**使用例**:
```python
from src.data.data_pipeline import DataPipeline, fetch_market_data

pipeline = DataPipeline()
multi_data = await pipeline.fetch_multi_timeframe("BTC/JPY", limit=100)
df = await fetch_market_data("BTC/JPY", "4h", 100)
```

### **data_cache.py（469行）**

**目的**: 高速データアクセス・階層化キャッシング
**戦略**: LRUメモリキャッシュ・3ヶ月ディスク保存・階層化アクセス

**主要クラス**:
```python
class DataCache:
    def __init__(self, max_size=1000)       # 初期化
    def get(self, key: str) -> Any          # データ取得
    def set(self, key: str, value: Any)     # データ保存
    def delete(self, key: str)              # データ削除
    def clear(self)                         # 全削除
    def get_stats(self) -> Dict             # 統計情報
    def cleanup_old_files(self)             # 古いファイル削除

class LRUCache:                             # LRU実装
class CacheMetadata:                        # キャッシュメタデータ

# グローバル関数
get_data_cache() -> DataCache               # グローバルキャッシュ取得
```

**使用例**:
```python
from src.data.data_cache import DataCache

cache = DataCache(max_size=500)
cache.set("btc_jpy_latest", {"price": 12345678})
data = cache.get("btc_jpy_latest")
stats = cache.get_stats()
```

## 🚀 使用例

```python
# 基本データ取得
from src.data import fetch_market_data, get_bitbank_client
df = await fetch_market_data("BTC/JPY", "4h", 100)
client = get_bitbank_client()
ticker = client.fetch_ticker("BTC/JPY")

# マルチタイムフレーム
from src.data.data_pipeline import DataPipeline
pipeline = DataPipeline()
multi_data = await pipeline.fetch_multi_timeframe("BTC/JPY", limit=200)

# キャッシュ活用
from src.data import get_data_cache
cache = get_data_cache()
cached_data = cache.get("market_data_btc_jpy_4h")
if cached_data is None:
    fresh_data = await fetch_market_data("BTC/JPY", "4h", 100)
    cache.set("market_data_btc_jpy_4h", fresh_data)
```

## 🔧 設定

**環境変数**: `BITBANK_API_KEY`, `BITBANK_API_SECRET`
**タイムフレーム**: 15m, 4h
**キャッシュ**: 5分間メモリ・3ヶ月ディスク保存

## ⚠️ 重要事項

### **特性・制約**
- **API制限**: 1000ms間隔・最大3回リトライ・30秒タイムアウト
- **パフォーマンス**: メモリ5分・ディスク3ヶ月・ヒット率80%以上
- **Phase 29最適化**: SSL証明書セキュリティ強化・信用取引特化設計
- **依存**: ccxt・pandas・aiohttp・src.core.*

---

**データ層（Phase 28完了・Phase 29セキュリティ強化）**: Bitbank信用取引特化・SSL証明書セキュリティ対応・保証金監視API統合・マルチタイムフレームデータパイプライン・階層化キャッシング機能。