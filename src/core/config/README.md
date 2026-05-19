# src/core/config/ - 設定管理

`config/core/thresholds.yaml`（1 ファイル化された全設定）の読み書き・型安全アクセス・動的オーバーライドを担う。

## ファイル構成

| ファイル | 行数 | 役割 |
|---|---|---|
| `__init__.py` | 321 | 設定ローダー・公開 API（`get_threshold` / `get_config` / `get_features_config`）|
| `config_classes.py` | 139 | 5 設定 dataclass 定義（`ExchangeConfig` / `MLConfig` 等）|
| `feature_manager.py` | 255 | 55 特徴量統一管理（Phase 89-β/γ/δ 拡張・`config/core/feature_order.json` 連携）|
| `threshold_manager.py` | 222 | 閾値ドット記法アクセス・実行時オーバーライド（Phase 40.1）|
| `runtime_flags.py` | 77 | グローバルランタイムフラグ（Phase 64.13・`ML_TRAINING_MODE` 等）|

## 主要 API

```python
from src.core.config import get_threshold, get_config, get_features_config

# ドット記法でアクセス
sl_rate = get_threshold("risk.sl_min_distance_ratio", 0.02)

# Dataclass で取得
config = get_config()
exchange = config.exchange  # ExchangeConfig dataclass

# Feature toggle
features = get_features_config()
cooldown_enabled = features.get("trading", {}).get("cooldown", {}).get("enabled", True)
```

## 設計原則

- **1 ファイル設定**: 全設定は `config/core/thresholds.yaml` に集約（Phase 65.12）
- **ハードコード禁止**: 必ず `get_threshold()` 経由で取得
- **デフォルト値必須**: `get_threshold(key, default)` の形で defensive

## 関連リンク

- 親 README: [../README.md](../README.md)
- 設定ファイル本体: `../../../config/core/thresholds.yaml`
- 特徴量定義: `../../../config/core/feature_order.json`

---

**最終更新**: 2026年5月20日（Phase 90α: 新規作成）
