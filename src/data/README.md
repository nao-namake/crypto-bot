# src/data/ - データ層

Bitbank信用取引API統合・マルチタイムフレームデータパイプライン・階層化キャッシング。

## ファイル構成

```
src/data/
├── __init__.py          # エクスポート（35行）
├── bitbank_client.py    # Bitbank API接続クライアント（1,861行）
├── data_pipeline.py     # データ取得パイプライン（559行）
└── data_cache.py        # キャッシングシステム（469行）
```

## 主要コンポーネント

### bitbank_client.py（1,861行）

Bitbank信用取引API専用クライアント。ccxtライブラリ + 直接API実装。

**主要メソッド**:

| メソッド | 種別 | 説明 |
|---------|------|------|
| `test_connection()` | sync | 接続テスト |
| `fetch_ohlcv()` | async | OHLCV取得（ccxt経由） |
| `fetch_ohlcv_4h_direct()` | async | 4時間足直接API取得 |
| `fetch_ohlcv_15m_direct()` | async | 15分足直接API取得 |
| `fetch_ticker()` | sync | ティッカー取得 |
| `fetch_order_book()` | sync | 板情報取得 |
| `fetch_balance()` | sync | 残高取得 |
| `create_order()` | sync | 注文発行（Maker/Taker対応） |
| `create_take_profit_order()` | sync | TP指値注文作成 |
| `create_stop_loss_order()` | sync | SL逆指値注文作成 |
| `cancel_order()` | sync | 注文キャンセル |
| `fetch_order()` | sync | 注文状態照会 |
| `fetch_active_orders()` | sync | アクティブ注文一覧 |
| `fetch_margin_status()` | async | 信用取引口座状況（維持率等） |
| `fetch_margin_positions()` | async | 信用取引ポジション一覧 |
| `has_open_positions()` | async | ポジション有無確認 |
| `get_market_info()` | sync | 市場情報（最小注文単位等） |
| `get_stats()` | sync | API統計情報 |

**内部メソッド**:
- `_fetch_candlestick_direct()` — 直接API共通実装（リトライ・OHLCV変換）
- `_create_order_direct()` — Private API直接注文
- `_call_private_api()` — Private API認証呼び出し

### data_pipeline.py（559行）

マルチタイムフレーム対応データ取得パイプライン。15分足（メイン）・4時間足（環境認識）の2軸構成。

**主要クラス**: `DataPipeline`, `TimeFrame`, `DataRequest`

### data_cache.py（469行）

LRUメモリキャッシュ + ディスク永続化の階層化キャッシング。

**主要クラス**: `DataCache`, `LRUCache`, `CacheMetadata`

## 設定

- **環境変数**: `BITBANK_API_KEY`, `BITBANK_API_SECRET`
- **API制限**: 1000ms間隔・最大3回リトライ・30秒タイムアウト
- **キャッシュ**: メモリ5分・ディスク3ヶ月保存

---

**最終更新**: Phase 64.8 — デッドメソッド削除・直接APIメソッド統合
