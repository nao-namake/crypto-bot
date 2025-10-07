# bitbank API 仕様リファレンス

**目的**: bitbank API仕様の理解・エラー対処のためのクイックリファレンス

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

### 認証ヘッダー
```http
ACCESS-KEY: <API Key>
ACCESS-NONCE: <Unix timestamp in milliseconds>
ACCESS-SIGNATURE: <HMAC-SHA256 signature>
```

### 署名生成ロジック

#### **GETリクエスト**
```python
message = f"{nonce}{endpoint}"
# 例: "1696723200000/user/margin/status"

signature = hmac.new(
    api_secret.encode("utf-8"),
    message.encode("utf-8"),
    hashlib.sha256
).hexdigest()
```

#### **POSTリクエスト**
```python
body = json.dumps(params, separators=(",", ":"))
message = f"{nonce}{body}"
# 例: '1696723200000{"pair":"btc_jpy","amount":"0.0001","price":"1000000","side":"buy","type":"limit"}'

signature = hmac.new(
    api_secret.encode("utf-8"),
    message.encode("utf-8"),
    hashlib.sha256
).hexdigest()
```

### ⚠️ 重要な違い
- **GET**: `nonce + endpoint` で署名生成
- **POST**: `nonce + request_body` で署名生成
- **誤った署名**: エラー20003（ACCESS-KEY not found）が発生

---

## 📡 主要Private APIエンドポイント

### 信用取引関連

#### `/user/margin/status`
- **メソッド**: GET
- **説明**: 証拠金維持率・利用可能残高取得
- **レスポンス例**:
```json
{
  "success": 1,
  "data": {
    "maintenance_margin_ratio": 55.0,
    "available_margin": 12000.0,
    "used_margin": 8000.0,
    "unrealized_pnl": -1500.0,
    "margin_call_status": "normal"
  }
}
```

#### `/user/spot/order`
- **メソッド**: POST
- **説明**: 注文作成（現物・信用取引両対応）

### 注文管理
- `/user/spot/active_orders`: アクティブ注文一覧（GET）
- `/user/spot/cancel_order`: 注文キャンセル（POST）
- `/user/spot/orders_info`: 注文詳細取得（POST）
- `/user/spot/trade_history`: 取引履歴（GET）

### 資産情報
- `/user/assets`: 資産残高（GET）
- `/user/withdrawal_account`: 出金先一覧（GET）

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
| コード | 説明 | 原因 | 対処法 |
|--------|------|------|--------|
| 20003 | ACCESS-KEY not found | API Key未設定・署名不正（GET/POST混同） | GET/POST署名ロジック確認 |
| 20005 | Invalid API key | API Key無効 | Secret Manager確認・再発行 |
| 20014 | Invalid nonce | nonce値が過去または未来すぎる | システム時刻確認 |

### 取引エラー
| コード | 説明 | 原因 | 対処法 |
|--------|------|------|--------|
| 50061 | 利用可能新規建玉可能額を超過 | 証拠金残高不足 | 事前残高チェック実装 |
| 50062 | 保有建玉数量を超過 | 決済注文数量 > 保有ポジション | 注文タイプ確認（`stop`使用推奨） |
| 50063 | 注文価格が不正 | 価格範囲外 | 価格検証ロジック追加 |

### よくある問題と対処法

#### エラー20003（ACCESS-KEY not found）
- **原因**: GETエンドポイントにPOST署名ロジック使用
- **対処**: `message = f"{nonce}{endpoint}"` で署名生成

#### エラー50062（保有建玉数量を超過）
- **原因**: SL注文を`limit`タイプで作成 → 新規ショートポジション開設と誤認識
- **対処**: `stop`タイプ + `trigger_price`パラメータ使用

#### エラー50061（証拠金不足）
- **原因**: 利用可能証拠金 < 注文に必要な証拠金
- **対処**: `/user/margin/status`で事前残高チェック実装

---

## 🚦 レート制限

### 制限値
- **取得系API**: 10リクエスト/秒
- **更新系API**: 6リクエスト/秒
- **制限超過時**: HTTP 429エラー

### 対策
- リクエスト間隔を適切に設定（3分間隔推奨）
- キャッシュ活用によるAPI呼び出し削減
- エラーハンドリング実装（429エラー時のリトライ）

---

## 📊 実装例

### GET認証（証拠金状況取得）
```python
async def _call_private_api(
    self, endpoint: str, params: Optional[Dict] = None, method: str = "POST"
) -> Dict[str, Any]:
    """bitbank private API呼び出し"""

    # GET/POST署名分岐
    if method.upper() == "GET":
        message = f"{nonce}{endpoint}"
        body = None
    else:
        body = json.dumps(params, separators=(",", ":"))
        message = f"{nonce}{body}"

    # 署名生成
    signature = hmac.new(
        self.api_secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    # ヘッダー作成
    headers = {
        "ACCESS-KEY": self.api_key,
        "ACCESS-NONCE": nonce,
        "ACCESS-SIGNATURE": signature,
    }
    if method.upper() == "POST":
        headers["Content-Type"] = "application/json"

    # HTTP リクエスト実行
    if method.upper() == "GET":
        async with session.get(url, headers=headers, timeout=timeout) as response:
            result = await response.json()
    else:
        async with session.post(url, headers=headers, data=body, timeout=timeout) as response:
            result = await response.json()


async def fetch_margin_status(self) -> Dict[str, Any]:
    """証拠金状況取得（GETメソッド）"""
    response = await self._call_private_api("/user/margin/status", method="GET")
    return response
```

### POST認証（注文作成）
```python
async def create_stop_loss_order(
    self, entry_side: str, amount: float, stop_loss_price: float
) -> Dict[str, Any]:
    """ストップロス注文作成（stop注文タイプ）"""
    return self.create_order(
        symbol="BTC/JPY",
        side="sell" if entry_side == "buy" else "buy",
        order_type="stop",              # 逆指値成行注文
        amount=amount,
        trigger_price=stop_loss_price,  # トリガー価格
        is_closing_order=True,
    )
```

---

## 🎯 参考情報

### 注文タイプ選択ガイド
- **エントリー注文**: `limit`（指値）推奨 - 約定確実性↑・手数料削減
- **テイクプロフィット**: `limit`（指値）推奨 - 利益確保
- **ストップロス**: `stop`（逆指値成行）推奨 - 確実な損切り実行
- **緊急決済**: `market`（成行）使用 - 即時約定優先

### セキュリティ推奨事項
- API KeyはSecret Manager等で安全に管理
- nonce値はタイムスタンプ（ミリ秒）使用
- システム時刻のNTP同期確認
- 署名生成ロジックのGET/POST分岐を厳密に実装
