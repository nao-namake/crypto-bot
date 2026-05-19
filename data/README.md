# data/

ローカル実行時の状態永続化 fallback ディレクトリ。本番（GCP Cloud Run）は Firestore に永続化（Phase 87 H4/H5）、本フォルダは**ローカル開発・テスト・Firestore 接続失敗時の fallback** として使用される。

## 役割

| 環境 | 永続化先 | data/ の使われ方 |
|---|---|---|
| 本番（GCP Cloud Run） | **Firestore**（`bot_state/default/{collection}/{key}`） | 通常未使用（接続断時のみ書き込み） |
| ローカル開発・ペーパー | `data/{collection}.json` | **主たる永続化先** |
| テスト | `data/{collection}.json`（`BOT_FORCE_LOCAL_PERSISTENCE=1`）| 強制的にローカル使用 |

`src/core/persistence/firestore_state.py` の `FirestoreStateClient` が両方を抽象化。ローカル形式は `data/{collection}.json` で Firestore のドキュメント階層と互換。

## 主要ファイル / サブフォルダ

| パス | 役割 | 書き込み元 | 生成タイミング |
|---|---|---|---|
| `sl_state.json` | SL 注文 ID 永続化（INACTIVE SL 対策） | `src/trading/execution/sl_state_persistence.py:25` | SL 配置時 |
| `ml_health.json` | ML 健全性状態（連続失敗数 / drift 検知） | `src/core/orchestration/ml_health_monitor.py` | ML 実行時 |
| `drawdown_state.json` | ドローダウン状態 | `src/trading/risk/drawdown.py:107` | 取引判断時 |
| `runtime_state/cross_asset_history.pkl` | BTC-ETH 相関履歴（Phase 89-δ） | `src/features/feature_generator.py:52` | 特徴量生成時 |
| `orderbook/` | オーダーブック蓄積（Phase 77・OFI 用） | `src/core/services/trading_cycle_manager.py:1207` | 取引サイクル時 |

## 整理方針

- **`*.json` ファイル**: ローカル実行時に自動生成・再生成可能 → 削除しても次回実行で復元される
- **`orderbook/`**: `.gitkeep` で空フォルダ保持（Phase 89-β で OFI 特徴量実装時に蓄積開始予定）
- **gitignore**: `data/` 全体が `.gitignore:173` で除外。例外は `data/README.md`（本ファイル）と `data/orderbook/.gitkeep`

## 関連リンク

- 親 README: [../README.md](../README.md)
- 永続化実装: `../src/core/persistence/firestore_state.py`
- Phase 87 H4/H5 経緯: [../docs/開発履歴/Phase_87.md](../docs/開発履歴/Phase_87.md)
