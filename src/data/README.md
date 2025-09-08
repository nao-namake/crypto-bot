# src/data/ - データ層

## 🎯 役割・責任

AI自動取引システムのデータ層。Bitbank API接続、マーケットデータ取得、マルチタイムフレーム対応データパイプライン、高速キャッシング機能を提供。信用取引に特化したデータ管理システム。

## 📂 ファイル構成

```
src/data/
├── __init__.py          # データ層エクスポート（33行）
├── bitbank_client.py    # Bitbank API接続クライアント（743行）
├── data_pipeline.py     # データ取得パイプライン（726行）
├── data_cache.py        # キャッシングシステム（469行）
└── historical/          # バックテスト用履歴データ保存ディレクトリ
```

## 🔧 主要コンポーネント

### **bitbank_client.py（743行）**

**目的**: Bitbank信用取引API専用クライアント

**主要機能**:
- ccxtライブラリによるAPI接続
- 信用取引（レバレッジ1.0-2.0倍）対応
- レート制限とエラーハンドリング
- 公開API・認証API両対応

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

# グローバル関数
get_bitbank_client() -> BitbankClient        # グローバルクライアント取得
create_margin_client() -> BitbankClient      # 新規クライアント作成
```

**使用例**:
```python
from src.data.bitbank_client import get_bitbank_client

# クライアント取得
client = get_bitbank_client(leverage=1.5)

# 接続テスト
if client.test_connection():
    print("接続OK")

# OHLCV取得
ohlcv = client.fetch_ohlcv("BTC/JPY", "1h", limit=100)

# 最新価格取得
ticker = client.fetch_ticker("BTC/JPY")
price = ticker['last']
```

### **data_pipeline.py（726行）**

**目的**: マルチタイムフレーム対応データ取得パイプライン

**サポートタイムフレーム**:
- 15分足（15m）
- 4時間足（4h）

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

class BacktestDataLoader:
    async def load_historical_data(self) -> Dict  # バックテスト用長期データ取得
    async def fetch_historical_data(self)         # 履歴データ取得

# 簡易インターフェース
fetch_market_data() -> pd.DataFrame               # 簡単データ取得
get_backtest_data_loader() -> BacktestDataLoader  # バックテストローダー取得
```

**使用例**:
```python
from src.data.data_pipeline import DataPipeline, TimeFrame, DataRequest

# パイプライン作成
pipeline = DataPipeline()

# 単一タイムフレーム取得
request = DataRequest(symbol="BTC/JPY", timeframe=TimeFrame.H4, limit=100)
df = await pipeline.fetch_ohlcv(request)

# マルチタイムフレーム取得
multi_data = await pipeline.fetch_multi_timeframe("BTC/JPY", limit=100)

# 簡易API使用
df = await fetch_market_data("BTC/JPY", "4h", 100)
```

### **data_cache.py（469行）**

**目的**: 高速データアクセス・階層化キャッシングシステム

**キャッシング戦略**:
- **メモリキャッシュ**: LRU方式、高速アクセス
- **ディスクキャッシュ**: 3ヶ月保存、圧縮保存
- **階層キャッシュ**: メモリ→ディスク→API の優先順

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

# グローバル関数
get_global_cache() -> DataCache             # グローバルキャッシュ取得
```

**使用例**:
```python
from src.data.data_cache import DataCache

# キャッシュ作成
cache = DataCache(max_size=500)

# データ保存
market_data = {"price": 12345678, "timestamp": "2025-09-07"}
cache.set("btc_jpy_latest", market_data)

# データ取得
data = cache.get("btc_jpy_latest")

# 統計確認
stats = cache.get_stats()
print(f"ヒット率: {stats['hit_rate']:.1%}")
```

### **historical/ディレクトリ**

**目的**: バックテスト用履歴データの永続化保存

**特徴**:
- バックテスト用長期データ（6ヶ月程度）保存
- data_pipeline.pyから自動作成・管理
- 1週間キャッシュによる高速バックテスト実行
- 圧縮保存による効率的ディスク使用

## 🚀 使用例

### **基本的なデータ取得**
```python
from src.data import fetch_market_data, get_bitbank_client

# 簡単なデータ取得
df = await fetch_market_data("BTC/JPY", "4h", 100)

# クライアント直接使用
client = get_bitbank_client()
ticker = client.fetch_ticker("BTC/JPY")
current_price = ticker['last']
```

### **マルチタイムフレーム取得**
```python
from src.data.data_pipeline import DataPipeline

pipeline = DataPipeline()

# 複数タイムフレーム同時取得
multi_data = await pipeline.fetch_multi_timeframe("BTC/JPY", limit=200)
print(f"15分足: {len(multi_data['15m'])}件")
print(f"4時間足: {len(multi_data['4h'])}件")
```

### **バックテスト用データ取得**
```python
from src.data.data_pipeline import get_backtest_data_loader

# バックテスト用長期データ
loader = get_backtest_data_loader()
historical_data = await loader.load_historical_data(
    symbol="BTC/JPY",
    months=6,
    timeframes=["15m", "4h"]
)

for tf, df in historical_data.items():
    print(f"{tf}: {len(df)}件の履歴データ")
```

## 🔧 設定

### **環境変数**
```bash
BITBANK_API_KEY=your_api_key          # APIキー
BITBANK_API_SECRET=your_api_secret    # APIシークレット
```

### **設定パラメータ**
```yaml
data:
  timeframes: ["15m", "4h"]
  limit: 1000                         # デフォルト取得件数
  cache_enabled: true                 # キャッシュ有効
  cache_duration_minutes: 5           # メモリキャッシュ有効期間
```

## ⚠️ 重要事項

### **API制限対策**
- レート制限: 35秒間隔（Bitbank制限考慮）
- 自動リトライ: 最大3回
- 指数バックオフ
- タイムアウト設定: 30秒

### **パフォーマンス特性**
- メモリキャッシュ: 5分間有効
- ディスクキャッシュ: 3ヶ月保存
- 期待ヒット率: 80%以上
- 4時間足100件: 1秒以内
- マルチタイムフレーム取得: 3秒以内

### **設計原則**
- **信用取引特化**: Bitbank信用取引API専用設計
- **パフォーマンス重視**: 効率的キャッシング・API制限対策
- **堅牢性確保**: エラーハンドリング・データ品質チェック
- **シンプル性維持**: 必要最小限機能・直感的インターフェース

### **依存関係**
- **外部ライブラリ**: ccxt（取引所API）、pandas（データ処理）
- **内部依存**: src.core.logger、src.core.exceptions、src.core.config

---

**データ層**: Bitbank信用取引に特化した高効率データ取得・管理システム。マルチタイムフレーム対応、階層化キャッシング、バックテスト支援機能を提供。