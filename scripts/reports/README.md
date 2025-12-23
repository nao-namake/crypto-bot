# scripts/reports/ - 週間レポート生成システム（Phase 55.8修正版）

**最終更新**: 2025年12月23日 - Phase 55.8修正・PnLCalculator引数エラー解決

## 役割・責任

週間レポート生成システムを提供します。過去7日間の取引統計を集計し、損益曲線グラフを生成してDiscordに自動送信します。

**ワークフロー状態**: 毎週月曜 9:00 JST 自動実行（GitHub Actions）

## ファイル構成

```
scripts/reports/
├── README.md          # このファイル
└── weekly_report.py   # 週間レポート生成・Discord送信スクリプト
```

## weekly_report.py

過去7日間の取引統計を集計し、損益曲線グラフを生成してDiscordに送信。

**主要機能**:
| 機能 | 説明 |
|------|------|
| 統計集計 | 取引数・損益・勝率・最大ドローダウン計算 |
| グラフ生成 | matplotlib による損益曲線グラフ |
| Discord送信 | 統計テキスト + グラフ画像の自動送信 |
| tax統合 | TradeHistoryRecorder・PnLCalculatorと連携 |

**実行方法**:
```bash
# 手動実行（過去7日間）
python3 scripts/reports/weekly_report.py

# カスタムDBパス指定
python3 scripts/reports/weekly_report.py --db-path tax/trade_history.db
```

## GitHub Actions自動実行

`.github/workflows/weekly_report.yml`で自動実行。

| 項目 | 値 |
|------|-----|
| スケジュール | 毎週月曜 9:00 JST（UTC 00:00） |
| 手動実行 | workflow_dispatch対応 |
| データソース | Cloud Storage（gs://crypto-bot-trade-data/tax/trade_history.db） |
| 通知先 | Discord Webhook（Secret Managerから取得） |

## 依存関係

### 必須モジュール
- `tax/trade_history_recorder.py`: 取引履歴記録
- `tax/pnl_calculator.py`: 損益計算エンジン
- `src/core/reporting/discord_notifier.py`: Discord通知

### 必須ライブラリ
- matplotlib: グラフ生成
- Pillow: 画像処理

## トラブルシューティング

```bash
# 手動実行テスト
python3 scripts/reports/weekly_report.py

# import確認
python3 -c "from scripts.reports.weekly_report import WeeklyReportGenerator; print('OK')"

# 直近のワークフロー実行確認
gh run list --workflow=weekly_report.yml --limit=5
```

## 変更履歴

| Phase | 変更内容 |
|-------|---------|
| 48.2 | 初期実装・Discord送信・matplotlib可視化 |
| 52.2 | Cloud Storage統合・環境変数化 |
| 55.8 | PnLCalculator引数修正（db_path → trade_recorder） |

---

**推奨運用**:
1. **自動実行**: GitHub Actions週次自動実行（推奨）
2. **手動確認**: ワークフロー失敗時は `gh run list` で確認
