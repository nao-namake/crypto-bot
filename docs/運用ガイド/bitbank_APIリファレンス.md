# bitbank API クイックリファレンス

**最終更新**: 2025年12月14日

## このドキュメントの役割

| 項目 | 内容 |
|------|------|
| **目的** | bitbank API仕様のクイックリファレンス |
| **対象読者** | 運用者・開発者 |
| **記載内容** | エンドポイント、認証方式、エラーコード、注文タイプ |
| **使用頻度** | APIエラー発生時、仕様確認時 |

**ルール**:
- 公式ドキュメントのURL一覧を維持
- エラーコード・パラメータ仕様を最新に保つ
- 実装例やトラブルシューティングは記載しない（実装は`src/data/bitbank_client.py`参照）

---

## 目次

1. [公式ドキュメント](#1-公式ドキュメント)
2. [認証方式](#2-認証方式)
3. [主要エンドポイント](#3-主要エンドポイント)
4. [注文タイプ](#4-注文タイプ)
5. [エラーコード](#5-エラーコード)
6. [レート制限](#6-レート制限)

---

## 1. 公式ドキュメント

### 基本仕様
- [README（概要）](https://github.com/bitbankinc/bitbank-api-docs/blob/master/README_JP.md)
- [REST API仕様](https://github.com/bitbankinc/bitbank-api-docs/blob/master/rest-api_JP.md)
- [エラーコード一覧](https://github.com/bitbankinc/bitbank-api-docs/blob/master/errors_JP.md)

### API種別
- [Public API（認証不要）](https://github.com/bitbankinc/bitbank-api-docs/blob/master/public-api_JP.md)
- [Public Stream（WebSocket）](https://github.com/bitbankinc/bitbank-api-docs/blob/master/public-stream_JP.md)
- [Private Stream（認証付きWebSocket）](https://github.com/bitbankinc/bitbank-api-docs/blob/master/private-stream_JP.md)

---

## 2. 認証方式

### 認証ヘッダー構成
```
ACCESS-KEY: <API Key>
ACCESS-NONCE: <Unix timestamp (milliseconds)>
ACCESS-SIGNATURE: <HMAC-SHA256 signature>
```

### 署名生成ルール

| メソッド | 署名対象メッセージ | 例 |
|---------|------------------|-----|
| **GET** | `{nonce}/v1{endpoint}` | `1696723200000/v1/user/margin/status` |
| **POST** | `{nonce}{request_body}` | `1696723200000{"pair":"btc_jpy",...}` |

**署名アルゴリズム**: HMAC-SHA256（hexdigest）

**重要**:
- GET署名には `/v1` プレフィックスが必須
- GET/POST署名の違いを厳守（誤るとエラー20001/20003発生）

---

## 3. 主要エンドポイント

### 信用取引関連
| エンドポイント | メソッド | 説明 |
|--------------|---------|------|
| `/user/margin/status` | GET | 証拠金維持率・利用可能残高取得 |
| `/user/spot/order` | POST | 注文作成（現物・信用取引両対応） |

#### `/user/margin/status` レスポンス詳細

**メソッド**: GET
**認証**: 必須（ACCESS-KEY, ACCESS-NONCE, ACCESS-SIGNATURE）

**レスポンスフィールド**:
```json
{
  "success": 1,
  "data": {
    "maintenance_margin_ratio": 150.5,
    "available_margin": 50000.0,
    "collateral": 100000.0,
    "unrealized_pnl": 5000.0
  }
}
```

**リスク閾値**:
| 維持率 | ステータス | 説明 |
|--------|-----------|------|
| >= 80% | 安全 | 通常運用可能 |
| 50-79% | 警告 | 追加証拠金推奨 |
| < 50% | マージンコール | 追加証拠金必要・新規取引制限 |
| < 25% | 強制決済 | ロスカット実行 |

**実装参照**: `src/trading/balance/monitor.py`、`src/data/bitbank_client.py`

**Phase 53.4対応**: `maintenance_margin_ratio`がNullまたは型変換失敗時、デフォルト500.0%を使用（安全な取引継続）

### 注文管理
| エンドポイント | メソッド | 説明 |
|--------------|---------|------|
| `/user/spot/active_orders` | GET | アクティブ注文一覧 |
| `/user/spot/cancel_order` | POST | 注文キャンセル |
| `/user/spot/orders_info` | POST | 注文詳細取得 |
| `/user/spot/trade_history` | GET | 取引履歴 |

#### `/user/spot/active_orders` レスポンス詳細

**メソッド**: GET（CCXT経由: `fetch_open_orders`）
**認証**: 必須

**レスポンス形式**（CCXT統一形式）:
```json
[
  {
    "id": "12345678",
    "symbol": "BTC/JPY",
    "side": "buy",
    "type": "limit",
    "price": 15000000.0,
    "amount": 0.001,
    "status": "open"
  }
]
```

**注意**:
- CCXT形式ではリスト（配列）で返却
- 注文IDは`id`キー（bitbank独自形式の`order_id`ではない）
- **実装参照**: `src/data/bitbank_client.py:fetch_active_orders()`

### 資産情報
| エンドポイント | メソッド | 説明 |
|--------------|---------|------|
| `/user/assets` | GET | 資産残高 |
| `/user/withdrawal_account` | GET | 出金先一覧 |

---

## 4. 注文タイプ

### 基本注文タイプ
| タイプ | 説明 | 使用場面 |
|--------|------|----------|
| `limit` | 指値注文 | 指定価格で注文・約定確実性高 |
| `market` | 成行注文 | 現在価格で即時約定・スリッページリスク |

### 逆指値注文
| タイプ | 説明 | 使用場面 |
|--------|------|----------|
| `stop` | 逆指値成行注文 | ストップロス・トリガー価格到達で成行約定 |
| `stop_limit` | 逆指値指値注文 | トリガー価格到達後に指値注文 |

### 注文パラメータ
```python
{
    "pair": "btc_jpy",
    "amount": "0.0001",
    "side": "buy" | "sell",
    "type": "limit" | "market" | "stop" | "stop_limit",

    # limit/stop_limit 時のみ
    "price": "1000000",

    # stop/stop_limit 時のみ
    "trigger_price": "950000",

    # 信用取引パラメータ
    "post_only": True | False,
}
```

### 注意事項
- **stop注文**: `trigger_price`必須・価格到達で成行約定
- **stop_limit注文**: `trigger_price` + `price`両方必須
- **limit注文**: SL用途では誤認識リスク（新規ポジション開設と解釈される可能性）

### 注文タイプ選択ガイド

| 用途 | 推奨タイプ | 理由 |
|------|----------|------|
| エントリー | `limit`（指値） | 約定確実性高・Maker手数料還元 |
| テイクプロフィット | `limit`（指値） | 利益確保・手数料還元 |
| ストップロス | `stop`（逆指値成行） | 確実な損切り実行 |
| 緊急決済 | `market`（成行） | 即時約定優先 |

---

## 5. エラーコード

### 認証エラー
| コード | 説明 | 主な原因 |
|--------|------|---------|
| 20001 | API認証失敗 | 署名不正・/v1プレフィックス欠落（GET） |
| 20003 | ACCESS-KEY not found | GET/POST署名ロジック混同・API Key未設定 |
| 20005 | Invalid API key | API Key無効・期限切れ |
| 20014 | Invalid nonce | nonce値が過去または未来すぎる・システム時刻ズレ |

### 取引エラー
| コード | 説明 | 主な原因 |
|--------|------|---------|
| 30101 | トリガー価格を指定してください | `stop`注文で`trigger_price`未指定 |
| 50061 | 利用可能新規建玉可能額を超過 | 証拠金残高不足 |
| 50062 | 保有建玉数量を超過 | 決済注文数量 > 保有ポジション |
| 50063 | 注文価格が不正 | 価格範囲外・最小価格単位違反 |

---

## 6. レート制限

| API種別 | 制限値 | 制限超過時 |
|---------|-------|-----------|
| 取得系API | 10リクエスト/秒 | HTTP 429エラー |
| 更新系API | 6リクエスト/秒 | HTTP 429エラー |
