# src/core/persistence/ - 状態永続化

Phase 87 H4/H5 で導入された Firestore ベース状態永続化。Cloud Run の ephemeral FS による状態消失を解消。

## ファイル構成

| ファイル | 行数 | 役割 |
|---|---|---|
| `__init__.py` | 10 | エクスポート |
| `firestore_state.py` | 233 | Firestore Native モード読み書き + ローカル fallback |

## 主要 API

```python
from src.core.persistence import FirestoreStateClient

client = FirestoreStateClient()
client.save("sl_state", "buy", {"sl_order_id": "...", "sl_price": 13900000})
state = client.load("sl_state", "buy")  # -> dict or None
client.delete("sl_state", "buy")
```

## 環境別の挙動

| 環境 | 永続化先 |
|---|---|
| 本番（GCP Cloud Run）| **Firestore Native**（`bot_state/default/{collection}/{key}`）|
| ローカル開発・ペーパー | `data/{collection}.json`（fallback）|
| テスト | 同上 + `BOT_FORCE_LOCAL_PERSISTENCE=1` で強制ローカル化（Phase 90α 補強）|

## 利用箇所

- `src/trading/execution/sl_state_persistence.py` — SL 注文 ID 永続化（Phase 87 H4）
- `src/trading/risk/drawdown.py` — ドローダウン状態（Phase 87 H5）
- `src/core/orchestration/ml_health_monitor.py` — ML 健全性 + Drift 検出履歴

## 関連リンク

- 親 README: [../README.md](../README.md)
- データ層: [../../../data/README.md](../../../data/README.md)（ローカル fallback ファイル説明）
- Phase 87 経緯: [../../../docs/開発履歴/Phase_87.md](../../../docs/開発履歴/Phase_87.md)

---

**最終更新**: 2026年5月20日（Phase 90α: 新規作成）
