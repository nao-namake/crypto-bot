# bitbank API クイックリファレンス

**Phase 52.4**

## 📋 このファイルの目的

**使用場面**:
- APIエラー発生時のエラーコード確認
- API仕様（エンドポイント・パラメータ）の調査
- 注文タイプ・認証方式の確認

**ルール**:
- 公式ドキュメントのURL一覧を維持
- エラーコード・パラメータ仕様を最新に保つ
- 実装例やトラブルシューティングは記載しない（実装は`src/data/bitbank_client.py`、履歴は開発履歴ドキュメント参照）

---

## 📚 公式ドキュメント

### 基本仕様
- [README（概要）](https://github.com/bitbankinc/bitbank-api-docs/blob/master/README_JP.md)
- [REST API仕様](https://github.com/bitbankinc/bitbank-api-docs/blob/master/rest-api_JP.md)
- [エラーコード一覧](https://github.com/bitbankinc/bitbank-api-docs/blob/master/errors_JP.md)

### API種別
- [Public API（認証不要）](https://github.com/bitbankinc/bitbank-api-docs/blob/master/public-api_JP.md)
- [Public Stream（WebSocket）](https://github.com/bitbankinc/bitbank-api-docs/blob/master/public-stream_JP.md)
- [Private Stream（認証付きWebSocket）](https://github.com/bitbankinc/bitbank-api-docs/blob/master/private-stream_JP.md)

---

## 🔐 認証方式（Private API）

### 認証ヘッダー構成
```
ACCESS-KEY: <API Key>
ACCESS-NONCE: <Unix timestamp (milliseconds)>
ACCESS-SIGNATURE: <HMAC-SHA256 signature>
```

### 署名生成ルール

| メソッド | 署名対象メッセージ | 例 |
|---------|------------------|-----|
| **GET** | `{nonce}{endpoint}` | `1696723200000/user/margin/status` |
| **POST** | `{nonce}{request_body}` | `1696723200000{"pair":"btc_jpy",...}` |

**署名アルゴリズム**: HMAC-SHA256（hexdigest）

**⚠️ 重要**: GET/POST署名の違いを厳守（誤るとエラー20003発生）

---

## 📡 主要Private APIエンドポイント

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
    "maintenance_margin_ratio": 150.5,  // 証拠金維持率（%）
    "available_margin": 50000.0,        // 利用可能証拠金（JPY）
    "collateral": 100000.0,             // 委託保証金額（JPY）
    "unrealized_pnl": 5000.0,           // 未実現損益（JPY）
    // ... その他のフィールド
  }
}
```

**証拠金維持率計算式**:
```
証拠金維持率（%）= 委託保証金額 ÷ 建玉評価額 × 100
```

**リスク閾値**:
| 維持率 | ステータス | 説明 |
|--------|-----------|------|
| ≥ 80% | 安全 | 通常運用可能 |
| 50-79% | 警告 | 追加証拠金推奨 |
| < 50% | マージンコール | 追加証拠金必要・新規取引制限 |
| < 25% | 強制決済 | ロスカット実行 |

**実装参照**: `src/trading/balance/monitor.py`（証拠金監視）・`src/data/bitbank_client.py`（fetch_margin_status()）

### 注文管理
| エンドポイント | メソッド | 説明 |
|--------------|---------|------|
| `/user/spot/active_orders` | GET | アクティブ注文一覧 |
| `/user/spot/cancel_order` | POST | 注文キャンセル |
| `/user/spot/orders_info` | POST | 注文詳細取得 |
| `/user/spot/trade_history` | GET | 取引履歴 |

### 資産情報
| エンドポイント | メソッド | 説明 |
|--------------|---------|------|
| `/user/assets` | GET | 資産残高 |
| `/user/withdrawal_account` | GET | 出金先一覧 |

---

## 📝 注文タイプ（Order Types）

### 基本注文タイプ
| タイプ | 説明 | 使用場面 |
|--------|------|----------|
| `limit` | 指値注文 | 指定価格で注文・約定確実性↑ |
| `market` | 成行注文 | 現在価格で即時約定・スリッページリスク |

### 逆指値注文
| タイプ | 説明 | 使用場面 |
|--------|------|----------|
| `stop` | 逆指値成行注文 | ストップロス実装・トリガー価格到達で成行約定 |
| `stop_limit` | 逆指値指値注文 | ストップロス（価格指定）・トリガー価格到達後に指値注文 |

### 注文パラメータ
```python
{
    "pair": "btc_jpy",
    "amount": "0.0001",           # 注文数量
    "side": "buy" | "sell",       # 売買方向
    "type": "limit" | "market" | "stop" | "stop_limit",

    # limit/stop_limit 時のみ
    "price": "1000000",           # 注文価格

    # stop/stop_limit 時のみ
    "trigger_price": "950000",    # トリガー価格

    # 信用取引パラメータ
    "post_only": True | False,    # PostOnlyフラグ
}
```

### ⚠️ 注意事項
- **stop注文**: `trigger_price`必須・価格到達で成行約定
- **stop_limit注文**: `trigger_price` + `price`両方必須
- **limit注文**: SL用途では誤認識リスク（新規ポジション開設と解釈される可能性）

---

## ⚠️ エラーコード一覧

### 認証エラー
| コード | 説明 | 主な原因 |
|--------|------|---------|
| 20003 | ACCESS-KEY not found | GET/POST署名ロジック混同・API Key未設定 |
| 20005 | Invalid API key | API Key無効・期限切れ |
| 20014 | Invalid nonce | nonce値が過去または未来すぎる・システム時刻ズレ |

### 取引エラー
| コード | 説明 | 主な原因 |
|--------|------|---------|
| 30101 | トリガー価格を指定してください | `stop`注文で`trigger_price`未指定 |
| 50061 | 利用可能新規建玉可能額を超過 | 証拠金残高不足 |
| 50062 | 保有建玉数量を超過 | 決済注文数量 > 保有ポジション・`limit`注文で決済時 |
| 50063 | 注文価格が不正 | 価格範囲外・最小価格単位違反 |

---

## 🚦 レート制限

| API種別 | 制限値 | 制限超過時 |
|---------|-------|-----------|
| 取得系API | 10リクエスト/秒 | HTTP 429エラー |
| 更新系API | 6リクエスト/秒 | HTTP 429エラー |

---

## 🎯 注文タイプ選択ガイド

| 用途 | 推奨タイプ | 理由 |
|------|----------|------|
| エントリー | `limit`（指値） | 約定確実性↑・Maker手数料還元 |
| テイクプロフィット | `limit`（指値） | 利益確保・手数料還元 |
| ストップロス | `stop`（逆指値成行） | 確実な損切り実行 |
| 緊急決済 | `market`（成行） | 即時約定優先 |

---

**📅 最終更新**: 2025年11月15日 - API仕様参照ファイル（実装詳細は開発履歴参照）
