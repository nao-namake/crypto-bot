# src/analysis/ - 分析共通ライブラリ

ライブ運用・バックテストの分析スクリプト（`scripts/live/standard_analysis.py` 等）から呼ばれる共通分析ユーティリティ。Phase 87 Stage 3 で `scripts/` 配下から `src/analysis/common/` に移動して再利用性確保。

## 構成

```
src/analysis/
├── __init__.py
└── common/         # 分析共通モジュール（詳細: common/README.md）
    ├── canceled_unfilled_detector.py  # SL CANCELED_UNFILLED 検出（Phase 87 C1）
    ├── gcp_metrics.py                  # Cloud Monitoring/Logging メトリクス取得
    ├── sl_validators.py                # SL 状態の妥当性検証
    └── tp_sl_helpers.py                # TP/SL 距離計算ヘルパー
```

## 目的

- **再利用性**: ライブ分析 / バックテスト分析 / テスト の 3 経路から共通利用
- **検証ロジックの一元化**: SL 健全性チェック・gcloud メトリクス取得などを 1 箇所に集約
- **Phase 87 H10 設計**: 「分析共通 lib」として scripts/ から src/ に移動

## 主要呼び出し元

- `scripts/live/standard_analysis.py`（ライブ運用統合診断）
- `scripts/backtest/standard_analysis.py`（バックテスト分析）
- `tests/unit/analysis/`（ユニットテスト）

## 関連リンク

- 親 README: [../README.md](../README.md)
- 共通モジュール詳細: [common/README.md](common/README.md)
- 分析スクリプト本体: [../../scripts/live/standard_analysis.py](../../scripts/live/standard_analysis.py)

---

**最終更新**: 2026年5月19日（Phase 90α: 新規作成）
