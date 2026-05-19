# src/data/ - データ層

Bitbank 信用取引 API 統合・マルチタイムフレームデータパイプライン・階層化キャッシング・WebSocket ストリーム・外部 API クライアント。

## ファイル構成（Phase 90α・2026-05-19 時点）

```
src/data/
├── __init__.py                    # エクスポート（30 行）
├── bitbank_client.py              # Bitbank API 接続クライアント（2,019 行）
├── bitbank_websocket_client.py    # Phase 89-δ: bitbank Public WebSocket（248 行）
├── data_pipeline.py               # データ取得パイプライン（572 行）
├── data_cache.py                  # キャッシングシステム（462 行）
└── external_api_client.py         # Phase 89-β: 外部 API クライアント（285 行）
```

## 主要コンポーネント

### bitbank_client.py（2,019 行）

Bitbank 信用取引 API 専用クライアント。ccxt ライブラリ + 直接 API 実装の混在。Phase コメント 54 件（数式根拠・修正履歴の重要記録）。

**主要メソッド**:

| メソッド | 種別 | 説明 |
|---|---|---|
| `test_connection()` | sync | 接続テスト |
| `fetch_ohlcv()` | async | OHLCV 取得（ccxt 経由）|
| `fetch_ohlcv_4h_direct()` | async | 4 時間足直接 API 取得 |
| `fetch_ohlcv_15m_direct()` | async | 15 分足直接 API 取得 |
| `fetch_ticker()` | sync | ティッカー取得 |
| `fetch_order_book()` | sync | 板情報取得 |
| `fetch_balance()` | sync | 残高取得 |
| `create_order()` | sync | 注文発行（Maker/Taker 対応）|
| `create_take_profit_order()` | sync | TP 指値注文作成 |
| `create_stop_loss_order()` | sync | SL 逆指値注文作成（stop 型・Phase 80）|
| `cancel_order()` | sync | 注文キャンセル |
| `fetch_order()` | sync | 注文状態照会（INACTIVE 含む全状態）|
| `fetch_active_orders()` | sync | アクティブ注文一覧 |
| `fetch_margin_status()` | async | 信用取引口座状況（維持率等）|
| `fetch_margin_positions()` | async | 信用取引ポジション一覧 |
| `has_open_positions()` | async | ポジション有無確認 |
| `get_market_info()` | sync | 市場情報（最小注文単位等）|
| `get_websocket_client()` | sync | WebSocket クライアント取得（Phase 89-δ）|
| `get_stats()` | sync | API 統計情報 |

**内部メソッド**:
- `_fetch_candlestick_direct()` — 直接 API 共通実装（リトライ・OHLCV 変換）
- `_create_order_direct()` — Private API 直接注文
- `_call_private_api()` — Private API 認証呼び出し

### bitbank_websocket_client.py（248 行・Phase 89-δ）

bitbank Public WebSocket API クライアント。ticker / depth / transactions のリアルタイムストリーム。Cloud Run 内で常駐接続維持。

**主要クラス**: `BitbankWebSocketClient`

### data_pipeline.py（572 行）

マルチタイムフレーム対応データ取得パイプライン。15 分足（メイン）・4 時間足（環境認識）の 2 軸構成。

**主要クラス**: `DataPipeline`, `TimeFrame`, `DataRequest`

### data_cache.py（462 行）

LRU メモリキャッシュ + ディスク永続化の階層化キャッシング。Phase 89-α でキャンドル ID ベースキャッシュキー改善検討中。

**主要クラス**: `DataCache`, `LRUCache`, `CacheMetadata`

### external_api_client.py（285 行・Phase 89-β）

Fear & Greed Index（alternative.me）等の無料外部 API クライアント。Phase 50.9 で削除した外部 API（yfinance 等）の後継として、必要最小限の機能のみ実装。

**主要クラス**: `ExternalAPIClient`

## 設定

- **環境変数**: `BITBANK_API_KEY`, `BITBANK_API_SECRET`
- **API 制限**: 1000ms 間隔・最大 3 回リトライ・30 秒タイムアウト
- **キャッシュ**: メモリ 5 分・ディスク 3 ヶ月保存
- **WebSocket**: bitbank Public エンドポイント・再接続自動化

## 関連リンク

- 親 README: [../README.md](../README.md)
- bitbank API 仕様: [../../docs/運用ガイド/bitbank_APIリファレンス.md](../../docs/運用ガイド/bitbank_APIリファレンス.md)
- 特徴量生成: [../features/](../features/)（このデータを消費）

---

**最終更新**: 2026年5月19日（Phase 90α: 5 ファイル構成反映・bitbank_websocket_client / external_api_client 追加）
