# config/core/ - システム基本設定

## 役割・責任

システム全体で使用する基本設定を管理する中核フォルダです。2つのファイルにより、全設定・特徴量定義を管理します。

**Phase 65.12（2026年2月24日）**:
- 37特徴量（SHAP最適化）
- 6戦略統合・3モデルアンサンブル
- 1ファイル体系（thresholds.yaml）

---

## ファイル構成

### 1. **thresholds.yaml** - システム統合設定

**役割**: 環境設定 + 全パラメータ + 機能トグル + 戦略定義の一元管理

**主要セクション**:
```yaml
# 環境・構造設定
mode:               # 実行モード（paper/live/backtest）
mode_balances:      # モード別初期残高（50万円）
exchange:           # 取引所接続設定（bitbank）
data:               # タイムフレーム定義（15m/4h）
cloud_run:          # GCPリソース設定（1Gi/1CPU）
security:           # Secret Manager設定
trading_constraints: # 通貨ペア・取引制約

# パラメータ・閾値
ml:                    # ML統合設定（アンサンブル重み・信頼度閾値）
dynamic_confidence:    # 動的信頼度計算（6戦略の信頼度範囲）
strategies:            # 戦略定義+パラメータ（6戦略・定義/閾値/重み統合）
trading:               # 取引設定（手数料・Kelly基準・信頼度レベル）
position_management:   # ポジション管理（TP/SL・クールダウン）
margin:                # 証拠金管理（維持率閾値80%）
order_execution:       # 注文実行（完全指値オンリー・Maker戦略）
models:                # MLモデルハイパーパラメータ
feature_flags:         # 機能トグル（旧features.yaml）
```

**使い方**:
- モード制御: CLI引数 > 環境変数MODE > YAML内mode
- コードから参照: `get_threshold("パラメータ名")`
- 機能トグル: `get_features_config()` → `feature_flags` セクション

---

### 2. **feature_order.json** - 特徴量定義（単一真実源）

**役割**: 全システムで使用する37特徴量の順序・定義を一元管理

**構造**:
```json
{
  "total_features": 37,
  "feature_levels": {
    "full": { "count": 37, "model_file": "ensemble_full.pkl" },
    "basic": { "count": 37, "model_file": "ensemble_basic.pkl" }
  },
  "feature_categories": {
    "basic": ["close", "volume"],
    "momentum": ["rsi_14", "macd", ...],
    "strategy_signals": ["strategy_signal_ATRBased", ...]
  }
}
```

**使い方**:
- 参照元: `src/core/config/feature_manager.py`、`src/core/orchestration/ml_loader.py`
- 特徴量追加時: このファイルを更新すれば全システムに自動反映
- 順序変更時: 既存モデル再訓練必須

---

## 設定変更ガイド

### よくある操作

```bash
# パラメータ調整（TP/SL・信頼度・戦略閾値等）
vim config/core/thresholds.yaml

# 機能の有効/無効化
vim config/core/thresholds.yaml  # feature_flags セクション

# 環境設定変更（取引間隔・GCP設定等）
vim config/core/thresholds.yaml  # production/cloud_run セクション

# 接続設定変更
vim config/core/thresholds.yaml  # exchange セクション

# 特徴量追加
vim config/core/feature_order.json

# 設定検証
bash scripts/testing/checks.sh

# 設定確認（Pythonから）
python3 -c "
from src.core.config.threshold_manager import get_threshold
print(get_threshold('position_management.take_profit.min_profit_ratio'))
"
```

---

## レバレッジ変更ガイド

### 実効レバレッジ変更時の修正箇所一覧

実効レバレッジを変更する際は、以下の14箇所を一括で修正する必要があります。すべて `thresholds.yaml` 内にあります。

| # | パラメータ | 説明 | 0.15倍 | 0.5倍 | 1.0倍 |
|---|-----------|------|--------|-------|-------|
| 1 | `production.max_order_size` | 最大注文サイズ(BTC) | 0.05 | 0.15 | 0.30 |
| 2 | `kelly_criterion.max_position_ratio` | Kelly最大ポジション比率 | 0.35 | 1.00 | 2.00 |
| 3 | `initial_position_size` | 初期ポジションサイズ(BTC) | 0.005 | 0.015 | 0.030 |
| 4 | `position_sizing.max_position_ratio` | ポジションサイジング上限 | 0.35 | 1.00 | 2.00 |
| 5 | `risk.max_capital_usage` | 資金利用率上限 | 0.5 | 1.5 | 3.0 |
| 6-8 | `max_position_ratio_per_trade.*` | 信頼度別上限 | 0.25-0.50 | 0.80-1.50 | 1.60-3.00 |
| 9-14 | `dynamic_position_sizing.*` | 動的サイジング | 0.10-0.35 | 0.30-1.05 | 0.60-2.10 |

### スケーリング計算式

```
新値 = 現在値 × (目標レバレッジ / 現在レバレッジ)
```

---

## 注意事項

### feature_order.json変更時の影響

- 既存MLモデルは使用不可（再訓練必須）
- バックテストデータの互換性喪失
- 全テスト再実行必須

---

**最終更新**: Phase 65.12（2026年2月24日）
