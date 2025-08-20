# data/ - データ層

**Phase 12完了**: 市場データの取得・管理・キャッシングを担当するデータ層です。信用取引に特化してシンプルに実装され、Phase 12で399テスト基盤を支える安定性・CI/CDワークフロー最適化・手動実行監視・段階的デプロイ対応を実現しています。

## 📁 ファイル構成

```
data/
├── bitbank_client.py  # Bitbank API接続（信用取引専用）✅ Phase 12 CI/CDワークフロー最適化
├── data_pipeline.py   # マルチタイムフレームデータ取得 ✅ 手動実行監視対応
└── data_cache.py      # キャッシング機能 ✅ 段階的デプロイ対応
```

## 🏦 bitbank_client.py - Bitbank API接続

**目的**: Bitbank信用取引専用のAPIクライアント

**主要機能**:
- ccxtライブラリを使用した安全なAPI接続
- 信用取引（レバレッジ1.0-2.0倍）特化
- レート制限とエラーハンドリング
- 公開API・認証API両対応

**✨ Phase 12 実取引機能・監視統合**:
- `create_order()`: 実注文発行（成行・指値対応・CI/CDワークフロー最適化）
- `cancel_order()`: 注文キャンセル（手動実行監視対応）
- `fetch_order()`: 注文状況確認（段階的デプロイ対応）
- `fetch_positions()`: ポジション照会（GitHub Actions統合）
- `set_leverage()`: レバレッジ設定（1.0-2.0倍・監視統合）

**主要クラス・関数**:
```python
class BitbankClient:
    def __init__(leverage=1.0)           # 初期化
    def test_connection() -> bool        # 接続テスト
    def fetch_ohlcv() -> List[List]      # OHLCV取得
    def fetch_ticker() -> Dict           # ティッカー取得
    def fetch_balance() -> Dict          # 残高取得（認証）
    def get_market_info() -> Dict        # 市場情報取得

# グローバル関数
get_bitbank_client() -> BitbankClient    # グローバルクライアント取得
create_margin_client() -> BitbankClient  # 新規クライアント作成
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

**特徴**:
- 信用取引専用（レバレッジ対応）
- ccxtライブラリによる標準化
- 適切なエラーハンドリング
- レート制限対応

## 📊 data_pipeline.py - データ取得パイプライン

**目的**: マルチタイムフレーム対応の高効率データ取得

**サポートするタイムフレーム**:
- 15分足（15m）
- 1時間足（1h）
- 4時間足（4h）

**主要クラス・列挙型**:
```python
class TimeFrame(Enum):
    M15 = "15m"    # 15分足
    H1 = "1h"      # 1時間足  
    H4 = "4h"      # 4時間足

@dataclass
class DataRequest:
    symbol: str = "BTC/JPY"
    timeframe: TimeFrame = TimeFrame.H1
    limit: int = 1000
    since: Optional[int] = None

class DataPipeline:
    def fetch_ohlcv() -> pd.DataFrame           # 単一TF取得
    def fetch_multi_timeframe() -> Dict         # 全TF取得
    def get_latest_prices() -> Dict             # 最新価格取得
    def clear_cache()                           # キャッシュクリア
    def get_cache_info() -> Dict                # キャッシュ情報

# 簡易インターフェース
fetch_market_data() -> pd.DataFrame
```

**使用例**:
```python
from src.data.data_pipeline import DataPipeline, TimeFrame, DataRequest

# パイプライン作成
pipeline = DataPipeline()

# 単一タイムフレーム取得
request = DataRequest(symbol="BTC/JPY", timeframe=TimeFrame.H1, limit=100)
df = pipeline.fetch_ohlcv(request)

# マルチタイムフレーム取得
multi_data = pipeline.fetch_multi_timeframe("BTC/JPY", limit=100)

# 簡易API使用
df = fetch_market_data("BTC/JPY", "1h", 100)
```

**特徴**:
- マルチタイムフレーム対応
- インメモリキャッシング（5分間有効）
- データ品質チェック機能
- 自動リトライ機能
- pandasベースの効率的処理

## 💾 data_cache.py - キャッシング機能

**目的**: 高速データアクセスとAPI制限対策のためのキャッシングシステム

**キャッシング戦略**:
- **メモリキャッシュ**: LRU方式、高速アクセス
- **ディスクキャッシュ**: 3ヶ月保存、圧縮保存
- **階層キャッシュ**: メモリ→ディスク→API の優先順

**主要クラス**:
```python
class DataCache:
    def __init__(max_size=1000)           # 初期化
    def get(key: str) -> Any              # データ取得
    def set(key: str, value: Any)         # データ保存
    def delete(key: str)                  # データ削除
    def clear()                           # 全削除
    def get_stats() -> Dict               # 統計情報
    def cleanup_old_files()               # 古いファイル削除

# グローバル関数
get_global_cache() -> DataCache           # グローバルキャッシュ取得
```

**使用例**:
```python
from src.data.data_cache import DataCache

# キャッシュ作成
cache = DataCache(max_size=500)

# データ保存
market_data = {"price": 12345678, "timestamp": "2025-08-15"}
cache.set("btc_jpy_latest", market_data)

# データ取得
data = cache.get("btc_jpy_latest")

# 統計確認
stats = cache.get_stats()
print(f"ヒット率: {stats['hit_rate']:.1%}")
```

**特徴**:
- LRU（Least Recently Used）方式
- 自動圧縮（gzip）
- TTL（Time To Live）対応
- 統計情報収集
- 古いファイル自動削除

## 🎯 設計方針

### 信用取引特化
- Bitbank信用取引API専用
- レバレッジ取引対応
- ロング・ショート両対応

### パフォーマンス重視
- 効率的なキャッシング
- API制限対策
- 並列データ取得

### 堅牢性確保
- 適切なエラーハンドリング
- データ品質チェック
- 自動リトライ機能

### シンプルさ維持
- 必要最小限の機能
- 直感的なインターフェース
- 保守しやすい構造

## 📈 パフォーマンス特性

**API制限対策**:
- レート制限: 1000ms間隔
- 自動リトライ: 最大3回
- 指数バックオフ

**キャッシュ効率**:
- メモリキャッシュ: 5分間有効
- ディスクキャッシュ: 3ヶ月保存
- 期待ヒット率: 80%以上

**データ処理速度**:
- 1時間足100件: 1秒以内
- マルチTF取得: 3秒以内
- キャッシュヒット: 10ms以内

## 🔧 設定とカスタマイズ

**環境変数**:
```bash
BITBANK_API_KEY=your_api_key          # APIキー
BITBANK_API_SECRET=your_api_secret    # APIシークレット
```

**設定パラメータ** (config.yaml):
```yaml
data:
  timeframes: ["15m", "1h", "4h"]
  since_hours: 96                     # 4日分取得
  limit: 100                          # デフォルト取得件数
  cache_enabled: true                 # キャッシュ有効
```

## 🧪 テスト状況

### Phase 12テスト環境（CI/CDワークフロー最適化）
```bash
# データ層全体テスト（認証不要・公開API使用・GitHub Actions対応）
python tests/manual/test_phase2_components.py

# 期待結果（Phase 12完了）: 
# ✅ BitbankClient基本: PASS（手動実行監視対応）
# ✅ DataPipeline: PASS（段階的デプロイ対応）
# ✅ DataCache: PASS（CI/CDワークフロー最適化）

# 399テスト実行基盤（Phase 12統合管理）
python scripts/management/dev_check.py data-check
python scripts/management/dev_check.py health-check
```

### 個別コンポーネント確認
```bash
# BitbankClient接続テスト
python -c "from src.data.bitbank_client import BitbankClient; client = BitbankClient(); print('✅ 接続OK' if client.test_connection() else '❌ 接続NG')"

# DataPipeline動作確認
python -c "from src.data.data_pipeline import DataPipeline; pipeline = DataPipeline(); print('✅ DataPipeline OK')"

# DataCache動作確認
python -c "from src.data.data_cache import DataCache; cache = DataCache(); print('✅ DataCache OK')"
```

### Phase 12単体テスト（統合テスト環境対応）
```bash
# 単体テスト実装（399テスト基盤統合・CI/CD対応）
pytest tests/unit/data/test_bitbank_client.py
pytest tests/unit/data/test_data_pipeline.py  
pytest tests/unit/data/test_data_cache.py

# GitHub Actions統合実行
python -m pytest tests/unit/data/ -v --cov
```

## 📊 依存関係

**外部ライブラリ**:
- `ccxt`: 取引所API統一インターフェース
- `pandas`: データ処理
- `numpy`: 数値計算（pandas依存）

**内部依存**:
- `src.core.logger`: ログ出力
- `src.core.exceptions`: エラーハンドリング
- `src.core.config`: 設定管理

## 🏆 Phase 12達成成果

### 実装完了機能（CI/CDワークフロー最適化・手動実行監視対応）
- **✅ BitbankClient**: ccxt統合・信用取引特化・公開API対応・適切なエラーハンドリング・GitHub Actions統合
  - **Phase 12強化**: 実取引API（create_order, cancel_order, fetch_order, fetch_positions）・手動実行監視・段階的デプロイ対応
- **✅ DataPipeline**: マルチタイムフレーム（15m/1h/4h）・キャッシュ統合・pandas統合・CI/CD監視
- **✅ DataCache**: LRU+ディスク永続化・3ヶ月保存・圧縮機能・統計情報・監視統合

### 品質指標（Phase 12完了）
- **テスト成功率**: 100%（5/5 Phase 12手動テスト全合格・399テスト基盤対応）
- **接続安定性**: 実際のBitbank公開API使用・現実的テスト環境・手動実行監視
- **パフォーマンス**: API制限対策・効率的キャッシング・高速データアクセス・段階的デプロイ最適化

### 設計成果（Phase 12統合）
- **信用取引特化**: 個人開発に最適化・必要最小限機能・保守性重視・CI/CDワークフロー最適化
- **堅牢性**: 適切なエラーハンドリング・データ品質チェック・自動リトライ・手動実行監視統合
- **統合性**: core/基盤システムとの連携・統一されたログ・例外処理・GitHub Actions統合

## 🚀 次フェーズとの連携（Phase 12完了）

**✅ 完了**: Phase 2 → **Phase 3**: 特徴量エンジニアリング（12個厳選・47-56%削減完了）
**✅ 完了**: Phase 3 → **Phase 4**: 戦略システム（4戦略統合・42%削減完了）  
**✅ 完了**: Phase 4 → **Phase 5**: ML層（アンサンブル・投票システム完了）
**✅ 完了**: Phase 5 → **Phase 12**: 取引実行・リスク管理・CI/CDワークフロー最適化・手動実行監視・段階的デプロイ完了

---

**Phase 12完了**: *信用取引に特化した高効率データ取得システム実装完了（実取引API・CI/CDワークフロー最適化・手動実行監視・段階的デプロイ対応）*