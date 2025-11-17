# 📊 データ層

**最終更新**: 2025/11/16 (Phase 52.4-B)

## 🎯 概要

AI自動取引システムのデータ層。Bitbank API統合・高速キャッシング・データ品質保証を提供します。

### 現状（Phase 52.4-B）
- ✅ **Bitbank API統合**: 信用取引・証拠金維持率監視・SSL証明書対応
- ✅ **マルチタイムフレーム**: 15分足（エントリー）・4時間足（トレンド）2軸構成
- ✅ **高速キャッシング**: LRUキャッシュ・長期保存（3ヶ月）・スレッドセーフ
- ✅ **データ品質保証**: 欠損値・異常値検出・自動リトライ機構
- ✅ **バックテスト対応**: CSV読み込み・本番同一ロジック

### 開発履歴

**Phase 52.4-B（2025/11/16）**: コード整理・ドキュメント統一完了

**Phase 49（2025/10/22）**: バックテストモード対応・証拠金維持率80%遵守

**Phase 35（2025/10/15）**: stop_limit注文・GET/POST API対応

**Phase 34（2025/10/14）**: 高速キャッシング実装・15分足データ収集80倍改善

---

## 📂 ディレクトリ構成

```
src/data/
├── __init__.py                 # モジュールエクスポート（36行）
├── bitbank_client.py           # Bitbank API クライアント（1,688行）
├── data_pipeline.py            # データ取得パイプライン（566行）
├── data_cache.py               # キャッシングシステム（469行）
└── README.md                   # 本ドキュメント（221行）
```

**総行数**: 2,759行（Python）+ 221行（ドキュメント） = 2,980行

## 🔧 主要コンポーネント

### 1. BitbankClient（`bitbank_client.py`）

**責務**: Bitbank API接続・信用取引注文・証拠金維持率監視

**主要メソッド**:
```python
# API クライアント取得
client = get_bitbank_client()

# 信用取引注文（指値）
order = await client.create_margin_order(
    side="buy",
    amount=0.001,
    price=14000000,
    order_type="limit"
)

# 証拠金維持率取得
margin_rate = await client.fetch_margin_status()
# → {"margin_maintenance_rate": 250.5, "status": "ok"}

# OHLCVデータ取得
ohlcv = await client.fetch_ohlcv("BTC/JPY", "15m", limit=100)
# → [[timestamp, open, high, low, close, volume], ...]
```

**特徴**:
- ccxtライブラリ使用（シンプル実装）
- 証拠金維持率80%遵守（critical_margin_rate設定）
- SSL証明書対応・エラーハンドリング
- GET/POST API両対応

**設定**: `config/core/unified.yaml`
```yaml
bitbank:
  leverage: 1.0
  critical_margin_rate: 80.0
  api_rate_limit: 5
```

---

### 2. DataPipeline（`data_pipeline.py`）

**責務**: マルチタイムフレームデータ取得・キャッシング・データ品質保証

**主要メソッド**:
```python
# パイプライン取得
pipeline = get_data_pipeline()

# 15分足データ取得（キャッシュ優先）
df_15m = await pipeline.fetch_ohlcv(
    symbol="BTC/JPY",
    timeframe="15m",
    limit=100,
    use_cache=True
)

# 4時間足データ取得
df_4h = await pipeline.fetch_ohlcv(
    symbol="BTC/JPY",
    timeframe="4h",
    limit=200,
    use_cache=True
)

# データ品質チェック
is_valid = pipeline.validate_data(df_15m)
# → True/False（欠損値・異常値チェック）
```

**特徴**:
- マルチタイムフレーム対応（15m, 4h）
- 自動キャッシング（LRUCache統合）
- 自動リトライ（指数バックオフ）
- データ品質チェック（欠損値・異常値検出）
- バックテストモード対応（CSV読み込み）

**設定**: `config/core/unified.yaml`
```yaml
data_pipeline:
  max_retries: 3
  retry_delay: 1.0
  cache_ttl: 300
  backtest_mode: false
```

---

### 3. DataCache（`data_cache.py`）

**責務**: 高速キャッシング・LRU自動削除・長期保存

**主要メソッド**:
```python
# キャッシュ取得
cache = get_data_cache()

# データ保存
cache.set(
    key="BTC_JPY_15m_20251116",
    value=df,
    timeframe="15m",
    symbol="BTC/JPY"
)

# データ取得
df = cache.get("BTC_JPY_15m_20251116")

# キャッシュクリア
cache.clear()

# 統計情報
stats = cache.get_stats()
# → {"hit_rate": 0.85, "size": 50, "max_size": 1000}
```

**特徴**:
- LRUキャッシュ（自動削除・最大1000エントリー）
- 長期保存対応（3ヶ月間・gzip圧縮）
- スレッドセーフ実装（threading.Lock）
- メタデータ管理（作成日時・最終アクセス・サイズ）

**設定**: `config/core/unified.yaml`
```yaml
data_cache:
  max_size: 1000
  cache_dir: "src/data/cache"
  long_term_ttl: 7776000  # 3ヶ月（秒）
```

---

## 🔄 データフロー

```
┌─────────────────────────┐
│  TradingOrchestrator    │
│  （取引制御）           │
└────────┬────────────────┘
         │
         │ 1. データ取得リクエスト
         ▼
┌─────────────────────────┐
│  DataPipeline           │
│  （データパイプライン） │
└────────┬────────────────┘
         │
         │ 2. キャッシュ確認
         ▼
┌─────────────────────────┐
│  DataCache              │
│  （LRUキャッシュ）      │
└────────┬────────────────┘
         │
         │ 3. キャッシュヒット？
         ├─ YES → データ返却（高速）
         └─ NO ↓
                │
                │ 4. API呼び出し
                ▼
         ┌─────────────────────────┐
         │  BitbankClient          │
         │  （Bitbank API）        │
         └────────┬────────────────┘
                  │
                  │ 5. OHLCVデータ取得
                  ▼
         ┌─────────────────────────┐
         │  Bitbank API            │
         │  （外部サービス）       │
         └────────┬────────────────┘
                  │
                  │ 6. データ返却
                  ▼
         ┌─────────────────────────┐
         │  DataPipeline           │
         │  - データ品質チェック   │
         │  - キャッシュ保存       │
         └────────┬────────────────┘
                  │
                  │ 7. 正規化データ返却
                  ▼
         ┌─────────────────────────┐
         │  FeatureGenerator       │
         │  （特徴量生成）         │
         └─────────────────────────┘
```

---

## 🧪 テスト

### テストファイル構成

```
tests/unit/data/
├── test_bitbank_client.py           # BitbankClient テスト
├── test_data_pipeline.py            # DataPipeline テスト
└── test_data_cache.py               # DataCache テスト
```

### テスト実行

```bash
# 全データ層テスト実行
pytest tests/unit/data/ -v

# カバレッジ付き実行
pytest tests/unit/data/ --cov=src/data --cov-report=html
```

---

## 📈 パフォーマンス指標

### キャッシュ効率（本番環境実績）

- **ヒット率**: 85-90%（15分足データ）
- **レイテンシ**:
  - キャッシュヒット: 1-5ms
  - キャッシュミス: 200-500ms（API呼び出し含む）
- **メモリ使用量**: 50-100MB（1000エントリー時）

### API呼び出し削減効果

- **15分足データ取得**: 80倍高速化（Phase 34達成）
- **月間API呼び出し**: 300,000回 → 30,000回（90%削減）
- **コスト削減**: 月額¥700-900達成（Phase 48目標達成）

---

## 🔗 関連ドキュメント

- **設定管理**: `config/core/unified.yaml`
- **統合ガイド**: `docs/運用手順/統合運用ガイド.md`
- **バックテストシステム**: `src/backtest/README.md`
- **開発ガイド**: `CLAUDE.md`

---

**作成日**: 2025/11/16
**最終更新**: 2025/11/16 (Phase 52.4-B)
**メンテナー**: Claude Code