# src/core/config - 統合設定管理システム 📋 Phase 52.4

3層設定体系（features.yaml・unified.yaml・thresholds.yaml）統合管理。
環境変数とYAMLファイルの統一制御により、モード設定・閾値管理・特徴量定義を一元化。

---

## 📂 ファイル構成

### 主要ファイル
- **`__init__.py`** (416行): メインエントリーポイント・Config/ConfigManager
- **`config_classes.py`** (150行): 5設定dataclass（Exchange/ML/Risk/Data/Logging）
- **`threshold_manager.py`** (277行): thresholds.yaml統合管理・8専用アクセス関数
- **`feature_manager.py`** (339行): 特徴量定義管理（feature_order.json準拠）
- **`runtime_flags.py`** (125行): ランタイムフラグ（backtest/paper mode）

---

## 🎯 3層設定体系

### 1. features.yaml - 機能トグル設定
```yaml
trading:
  cooldown:
    enabled: true
    flexible_mode: false
  ml_integration:
    enabled: true
```

### 2. unified.yaml - 基本設定
```yaml
mode_balances:
  paper:
    initial_balance: 10000
  live:
    initial_balance: 100000
```

### 3. thresholds.yaml - 動的値（ML閾値・リスク設定）
```yaml
position_management:
  confidence_thresholds:
    low_to_medium: 0.60
    medium_to_high: 0.75
```

---

## 🚀 使用例

### 設定読み込み
```python
from src.core.config import load_config

# unified.yaml読み込み（コマンドラインモード優先）
config = load_config("config/core/unified.yaml", cmdline_mode="paper")
```

### 閾値取得（推奨パターン）
```python
from src.core.config import get_threshold

# 階層キーでアクセス
sl_rate = get_threshold("risk.sl_min_distance_ratio", 0.02)
ml_confidence = get_threshold("ml.default_confidence", 0.5)

# 専用アクセス関数（8種類）
from src.core.config import get_trading_thresholds, get_monitoring_config

trading_thresholds = get_trading_thresholds()
monitoring_config = get_monitoring_config()
```

### 特徴量管理
```python
from src.core.config import get_feature_names, get_feature_count

# 特徴量名リスト取得
features = get_feature_names()  # ["close", "volume", ...]

# 特徴量数取得
count = get_feature_count()  # 55

# Graceful Degradation対応
from src.core.config import get_feature_levels

levels = get_feature_levels()
# {"full": {"count": 55, "model_file": "ensemble_full.pkl"}, ...}
```

### ランタイムフラグ
```python
from src.core.config import set_backtest_mode, is_backtest_mode

# バックテストモード設定
set_backtest_mode(True)

if is_backtest_mode():
    # バックテスト専用処理（API呼び出しモック化等）
    pass
```

---

## 🔧 設計原則

### ハードコード禁止 ⛔
全ての設定値は設定ファイル・環境変数で管理。

**❌ 避けるべき**:
```python
sl_rate = 0.02  # ハードコード
```

**✅ 推奨**:
```python
from src.core.config import get_threshold
sl_rate = get_threshold("risk.sl_min_distance_ratio", 0.02)
```

### モード設定優先順位
```
コマンドライン引数 > 環境変数 > unified.yaml
```

### Graceful Degradation
特徴量レベル（full/basic）によるモデルファイル自動選択。

```python
# 55特徴量 → ensemble_full.pkl
# 49特徴量 → ensemble_basic.pkl（フォールバック）
# エラー → DummyModel（最終フォールバック）
```

---

## 📊 8専用アクセス関数（threshold_manager.py）

高頻度アクセス設定用の専用関数:

| 関数名 | 取得内容 |
|--------|----------|
| `get_trading_thresholds()` | 取引設定（SL/TP/Kelly基準） |
| `get_monitoring_config()` | 監視設定（証拠金維持率閾値） |
| `get_anomaly_config()` | 異常検知設定（スプレッド・API遅延） |
| `get_position_config()` | ポジション管理設定（上限・クールダウン） |
| `get_backtest_config()` | バックテスト設定（初期残高・手数料） |
| `get_data_config()` | データ設定（時間足・履歴期間） |
| `get_file_config()` | ファイルパス設定（モデル・ログ） |
| `get_system_thresholds()` | システム設定（パフォーマンス・リトライ） |

---

## ⚠️ 注意事項

### 循環参照リスク
- `__init__.py` ↔ `threshold_manager.py` の循環参照に注意
- 新規import追加時は依存関係確認必須

### 設定ファイル依存
- `features.yaml`, `unified.yaml`, `thresholds.yaml`, `feature_order.json` 必須
- ファイル不在時のフォールバック処理実装済み

### グローバル状態管理
- `_thresholds_cache`, `_features_config_cache` のグローバルキャッシュ
- `runtime_flags`はスレッドセーフ設計（threading.Lock使用）

---

## 🔗 関連ファイル

### 設定ファイル
- `config/core/features.yaml`: 機能トグル設定
- `config/core/unified.yaml`: 統合設定ファイル
- `config/core/thresholds.yaml`: 閾値設定
- `config/core/feature_order.json`: 特徴量定義（真の情報源）

### 参照元システム
- `src/core/orchestration/`: 設定読み込み・モード判定
- `src/ml/`: 特徴量管理・モデル選択
- `src/trading/`: 閾値参照・リスク管理

---

**🎯 Phase 52.4完了**: 設定管理完全統一・3層設定体系確立・ハードコード禁止原則徹底により、保守性・拡張性が大幅に向上しています。
