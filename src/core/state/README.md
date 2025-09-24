# src/core/state/ - システム状態管理ディレクトリ

**最終更新**: 2025年9月24日 - Phase 23モード別状態管理完了

## 🎯 役割

トレーディングシステムの実行状態を永続化・管理するディレクトリです。**Phase 23完了**により、各モード（paper/live/backtest）の状態を完全分離し、本番環境への影響を防止します。

## 📂 ディレクトリ構造

```
src/core/state/
├── README.md                   # このファイル
├── drawdown_persistence.py     # 状態管理ロジック（読み書き・復元）
├── paper/                      # ペーパーモード専用状態
│   └── drawdown_state.json
├── live/                       # ライブモード専用状態
│   └── drawdown_state.json
└── backtest/                   # バックテストモード専用状態
    └── (必要時に自動生成)
```

## 📋 各ファイルの役割

### **drawdown_persistence.py**
状態ファイルの読み書きを管理する中核ロジックです。

**主要機能**:
- `load_drawdown_state(mode)`: モード別状態ファイル読み込み
- `save_drawdown_state(state, mode)`: モード別状態ファイル保存
- `reset_drawdown_state(mode)`: 状態リセット（ペーパーモード自動実行）
- GCPシークレット対応・ローカル/本番環境自動判定

**使用例**:
```python
from src.core.state.drawdown_persistence import load_drawdown_state, save_drawdown_state

# ペーパーモードの状態読み込み
state = load_drawdown_state(mode="paper")

# 状態更新後の保存
save_drawdown_state(state, mode="paper")
```

### **drawdown_state.json（各モードディレクトリ内）**
ドローダウン管理システムの状態を記録するJSONファイルです。

**構造**:
```json
{
  "current_balance": 10000.0,        // 現在残高
  "peak_balance": 10000.0,           // ピーク残高
  "consecutive_losses": 0,           // 連続損失回数
  "last_loss_time": null,            // 最終損失時刻
  "trading_status": "active",        // 取引状態
  "pause_until": null,               // 一時停止期限
  "current_session": null,           // 現在セッション
  "last_updated": "2025-09-24T05:00:00"  // 最終更新時刻
}
```

**trading_status値**:
- `active`: 通常取引中
- `paused_drawdown`: ドローダウン制限により一時停止（20%超過）
- `paused_consecutive_loss`: 連続損失により一時停止（5回連続）

## 🔒 重要ルール

### **1. モード別完全分離（Phase 23）**
- ✅ **各モード独立**: paper/live/backtest は**完全に独立した状態ファイル**を持つ
- ✅ **相互影響防止**: ペーパーモードの実験が本番環境（live）に影響しない
- ✅ **本番保護**: ライブモードの状態はペーパーモードから完全隔離

### **2. ファイル配置規則**
```python
# ✅ 正しいパス（Phase 23）
f"src/core/state/{mode}/drawdown_state.json"
# paper → src/core/state/paper/drawdown_state.json
# live  → src/core/state/live/drawdown_state.json

# ❌ 古いパス（Phase 22以前・使用禁止）
"src/core/state/drawdown_state.json"  # 共有ファイル（削除済み）
```

### **3. 初期化・リセット規則**
- **ペーパーモード**: 実行開始時に**自動リセット**（`run_safe.sh`が自動削除）
- **ライブモード**: 状態を**永続化**（リセット禁止）
- **バックテストモード**: テスト終了後に自動クリーンアップ

### **4. 残高管理規則（Phase 23連携）**
初期残高は`config/core/unified.yaml`の`mode_balances`で一元管理:

```yaml
# config/core/unified.yaml
mode_balances:
  paper:
    initial_balance: 10000.0    # ペーパーモード初期残高
  live:
    initial_balance: 10000.0    # ライブモード初期残高
  backtest:
    initial_balance: 10000.0    # バックテスト初期残高
```

状態ファイルの`current_balance`は実行中の残高変動を記録。

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
# run_safe.sh が自動実行（手動不要）
bash scripts/management/run_safe.sh local paper
# → 起動時に src/core/state/paper/drawdown_state.json を自動削除
```

### **手動リセット（緊急時のみ）**
```bash
# ペーパーモード手動リセット
rm src/core/state/paper/drawdown_state.json

# ⚠️ ライブモードは手動リセット禁止（本番データ消失防止）
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

## 📊 状態遷移図

```
初期状態
   ↓
[active] ← 通常取引中
   ↓
   ├─ ドローダウン20%超過 → [paused_drawdown]
   │                              ↓
   │                          24時間一時停止
   │                              ↓
   │                          [active] 復帰
   │
   └─ 連続損失5回 → [paused_consecutive_loss]
                          ↓
                      1時間一時停止
                          ↓
                      [active] 復帰
```

## 🔗 関連ファイル・システム

### **設定ファイル連携**
- `config/core/unified.yaml`: モード別初期残高設定（mode_balances）
- `config/core/thresholds.yaml`: ドローダウン閾値・リスク設定

### **実行スクリプト連携**
- `scripts/management/run_safe.sh`: ペーパーモード自動リセット実行
- `scripts/management/bot_manager.sh`: 状態確認・プロセス管理

### **コア機能連携**
- `src/trading/risk_manager.py`: 状態読み込み・ドローダウン判定
- `src/core/orchestration/orchestrator.py`: 状態管理システム統合

## 📝 変更履歴

### **Phase 23（2025/09/24）**
- ✅ モード別ディレクトリ分離（paper/live/backtest）
- ✅ 古い共有ファイル削除（drawdown_state.json）
- ✅ run_safe.shペーパーモード自動リセット実装
- ✅ 本番環境保護強化

### **Phase 22以前**
- 共有状態ファイル方式（全モードで1ファイル共有）
- モード間の状態汚染問題あり

---

**🎯 重要**: このディレクトリはシステムの状態永続化を担う重要な役割を持ちます。Phase 23のモード別分離により、ペーパーモードの実験が本番環境に影響しない安全な構造を実現しました。状態ファイルの直接編集は避け、システムの自動管理に任せてください。