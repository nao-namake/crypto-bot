# src/core/state/ - システム状態管理

**Phase 28完了・Phase 29最適化版**のドローダウン状態永続化システム。

## 🎯 役割

AI自動取引システムの実行状態を永続化・管理。各モード（paper/live/backtest）の状態を完全分離し、本番環境への影響を防止。

## 📂 ディレクトリ構造

```
src/core/state/
├── __init__.py                 # パッケージエクスポート
├── drawdown_persistence.py     # 状態管理ロジック（275行）
├── README.md                   # このファイル
├── paper/                      # ペーパーモード専用状態
│   └── drawdown_state.json
├── live/                       # ライブモード専用状態
│   └── drawdown_state.json
└── backtest/                   # バックテストモード専用状態
    └── (必要時に自動生成)
```

## 🔧 主要機能

### **drawdown_persistence.py**
状態ファイルの読み書きを管理する中核ロジック。

**主要クラス**:
- `DrawdownPersistence`: 基底抽象クラス
- `LocalFilePersistence`: ローカルファイル実装
- `CloudStoragePersistence`: GCP Cloud Storage実装
- `create_persistence()`: 環境自動判定ファクトリ関数

**使用例**:
```python
from src.core.state import create_persistence

# モード別状態管理
persistence = create_persistence(mode="paper")
state = await persistence.load_state()
await persistence.save_state(updated_state)
```

### **drawdown_state.json（各モードディレクトリ内）**
ドローダウン管理システムの状態を記録するJSONファイル。

**実際の構造**:
```json
{
  "current_balance": 10432.21,
  "peak_balance": 10432.21,
  "consecutive_losses": 0,
  "last_loss_time": null,
  "trading_status": "active",
  "pause_until": null,
  "current_session": {
    "start_time": "2025-09-25 20:27:54.636613",
    "end_time": null,
    "reason": "セッション開始",
    "initial_balance": 10000.0,
    "final_balance": null,
    "total_trades": 0,
    "profitable_trades": 0
  },
  "last_updated": "2025-09-27T04:54:13.574812"
}
```

**trading_status値**:
- `active`: 通常取引中
- `paused_drawdown`: ドローダウン制限により一時停止
- `paused_consecutive_loss`: 連続損失により一時停止

## 🔒 重要ルール

### **1. モード別完全分離**
- ✅ **各モード独立**: paper/live/backtest は完全に独立した状態ファイルを持つ
- ✅ **相互影響防止**: ペーパーモードの実験が本番環境（live）に影響しない
- ✅ **本番保護**: ライブモードの状態はペーパーモードから完全隔離

### **2. ファイル配置規則**
```python
# ✅ 正しいパス
f"src/core/state/{mode}/drawdown_state.json"
# paper → src/core/state/paper/drawdown_state.json
# live  → src/core/state/live/drawdown_state.json
```

### **3. 初期化・リセット規則**
- **ペーパーモード**: 実行開始時に自動リセット（`run_safe.sh`が自動削除）
- **ライブモード**: 状態を永続化（リセット禁止）
- **バックテストモード**: テスト終了後に自動クリーンアップ

## 🔧 操作方法

### **状態確認**
```bash
# ペーパーモード状態確認
cat src/core/state/paper/drawdown_state.json

# ライブモード状態確認
cat src/core/state/live/drawdown_state.json
```

### **ペーパーモードリセット（自動実行）**
```bash
bash scripts/management/run_safe.sh local paper
# → 起動時に src/core/state/paper/drawdown_state.json を自動削除
```

## 🚨 注意事項

### **絶対禁止事項**
- ❌ **ライブモード状態の手動削除**: 本番取引データが消失
- ❌ **モード間の状態ファイルコピー**: 環境間の汚染原因
- ❌ **drawdown_state.jsonの直接編集**: システム整合性破壊

### **推奨事項**
- ✅ **状態確認は読み取り専用**: `cat`コマンドで確認
- ✅ **リセットはスクリプト経由**: `run_safe.sh`に任せる
- ✅ **バックアップは自動**: システムが必要時に自動実行

## 🔗 関連システム

**設定ファイル連携**:
- `config/core/unified.yaml`: モード別初期残高設定（mode_balances）
- `config/core/thresholds.yaml`: ドローダウン閾値・リスク設定

**実行スクリプト連携**:
- `scripts/management/run_safe.sh`: ペーパーモード自動リセット実行
- `scripts/management/bot_manager.sh`: 状態確認・プロセス管理

**コア機能連携**:
- `src/trading/risk_monitor.py`: 状態読み込み・ドローダウン判定
- `src/core/orchestration/orchestrator.py`: 状態管理システム統合

---

**状態永続化システム（Phase 28完了・Phase 29最適化版）**: モード別状態分離により、ペーパーモードの実験が本番環境に影響しない安全な構造を実現。ローカル・Cloud Storage両対応で運用環境に最適化。