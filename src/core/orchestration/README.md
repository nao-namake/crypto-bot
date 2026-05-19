# src/core/orchestration/ - システム統合制御

全サービスの統合 orchestrator・ML サービス層・gating / 品質フィルタ・Phase 88 I3 trigger server。Phase 89-α/β/γ/δ + Phase 90α の中核制御層。

## ファイル構成

| ファイル | 行数 | 役割 | Phase |
|---|---|---|---|
| `__init__.py` | 6 | エクスポート | - |
| `orchestrator.py` | 619 | アプリケーションサービス層（`TradingOrchestrator`）| Phase 49 |
| `protocols.py` | 71 | 5 サービスプロトコル定義（DI 用） | Phase 49 |
| `ml_adapter.py` | 218 | ProductionEnsemble 統一インターフェース | Phase 64.6 |
| `ml_loader.py` | 297 | ML モデル読み込み・3 段階 Graceful Degradation | Phase 64.6 |
| `ml_fallback.py` | 60 | DummyModel 安全装置（hold 信頼度 0.5）| Phase 49 |
| `ml_confidence.py` | 47 | ML 信頼度計算ヘルパー（`predicted_class_proba` 統一）| Phase 87 C2 |
| `ml_health_monitor.py` | 494 | ML 健全性監視・サーキットブレーカー（3 回連続失敗で EMERGENCY_STOP）| Phase 87 C4 |
| `quality_filter.py` | 261 | レジーム別品質フィルタ（accept_threshold / reject_threshold）| Phase 87 H6/H10 |
| `trade_gating.py` | 157 | Phase 89-α 取引判断 gating（15 分足境界判定・monitor_only スキップ）| Phase 89-α |
| `trigger_server.py` | 270 | Cloud Scheduler 駆動 FastAPI（`/trigger` endpoint）| Phase 88 I3 |

## 主要エントリポイント

### TradingOrchestrator

```python
from src.core.orchestration import TradingOrchestrator

orch = TradingOrchestrator()
await orch.initialize()       # 全サービス DI 初期化
await orch.run()              # 無限ループ実行
await orch.run_trading_cycle() # 1 サイクル
await orch.run_monitor_only()  # gating で monitor_only スキップ
```

### MLServiceAdapter（4 モデルアンサンブル統一 API）

```python
from src.core.orchestration.ml_adapter import MLServiceAdapter

adapter = MLServiceAdapter(logger)
prediction = await adapter.predict(features)
# 失敗時自動: ml_health_monitor.record_failure → 3 回で circuit break
```

### 3 段階 Graceful Degradation

```
Level 1: ensemble_full.pkl (55 特徴量・4 モデル)
    ↓ 読み込み失敗
Level 2: ensemble_basic.pkl (55 特徴量・3 モデル fallback)
    ↓ 読み込み失敗
Level 3: DummyModel (常に hold・ml_fallback.py)
```

## Phase 89-α 取引判断 gating

`trade_gating.py` が **15 分足完成境界（00/15/30/45 ±2 分）外** or **両方向ポジション既存時**は TP/SL 監視のみで早期 return。**98% の余剰サイクル発火を 1/30 に削減**。

## Phase 88 I3 trigger_server

`MODE=trigger` 時に `uvicorn` 経由で起動し、Cloud Scheduler から `/trigger` を受けて 1 サイクル実行。`min_instances=0` 化（月 ¥2,400 削減目標）の鍵。

## 関連リンク

- 親 README: [../README.md](../README.md)
- 取引サイクル: [../services/README.md](../services/README.md)
- ML 統合: [../../ml/README.md](../../ml/README.md)

---

**最終更新**: 2026年5月20日（Phase 90α: 新規作成・11 ファイル全部記載）
