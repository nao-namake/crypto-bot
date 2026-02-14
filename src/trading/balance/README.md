# src/trading/balance/ - 残高監視層

## 役割

証拠金残高監視・不足検知を担当。Phase 38でtradingレイヤードアーキテクチャの一部として分離。

## ファイル構成

```
balance/
├── monitor.py       # BalanceMonitor（465行）
├── __init__.py      # モジュール初期化
└── README.md        # このファイル
```

## 公開メソッド（外部呼び出し元あり）

| メソッド | 呼び出し元 | 役割 |
|---------|-----------|------|
| `validate_margin_balance()` | executor.py | ライブ取引前の証拠金残高チェック |
| `predict_future_margin()` | risk/manager.py | 新規ポジション追加後の維持率予測 |
| `should_warn_user()` | risk/manager.py | 維持率低下の警告判定 |

## 内部メソッド

| メソッド | 役割 |
|---------|------|
| `calculate_margin_ratio()` | 保証金維持率計算（API優先・フォールバック） |
| `_calculate_margin_ratio_direct()` | 保証金維持率の直接計算 |
| `_fetch_margin_ratio_from_api()` | bitbank APIから維持率取得 |
| `get_margin_status()` | 維持率に基づく状態判定（SAFE/CAUTION/WARNING/CRITICAL） |
| `_get_recommendation()` | 維持率に基づく推奨アクション |

## 設定ファイル連携

- `config/core/thresholds.yaml`: `balance_alert.min_required_margin`（14,000円）、`margin.thresholds.*`
