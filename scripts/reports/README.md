# scripts/reports/ - レポート生成スクリプト（Phase 52.4更新）

**最終更新**: 2025年11月16日 - Phase 52.4コード整理・Phase 52.3バグ修正適用・テストカバレッジ追加

## 🎯 役割・責任

週間レポート生成システムを提供します。過去7日間の取引統計を集計し、損益曲線グラフを生成してDiscordに自動送信します。

**Phase 48で達成した成果**: 週間レポート自動送信・損益曲線グラフ生成・Discord通知99%削減（300-1,500回/月 → 4回/月）・コスト35%削減・月額700-900円達成

**Phase 52.4更新内容**: Phase 52.3最大ドローダウン計算バグ修正適用・ハードコード値config移行・テストカバレッジ追加（0% → 80%+）

## 📂 ファイル構成

```
scripts/reports/
├── README.md          # このファイル（Phase 52.4更新版）
└── weekly_report.py   # 週間レポート生成・Discord送信スクリプト（Phase 52.4更新）
```

## 📋 主要ファイルの役割

### **weekly_report.py**（Phase 52.4更新）
過去7日間の取引統計を集計し、損益曲線グラフを生成してDiscordに送信します。

**主要機能**:
- ✅ **統計集計**: 過去7日間の取引数・損益・勝率・最大ドローダウン・シャープレシオ
- ✅ **matplotlib可視化**: 累積損益曲線グラフ生成（equity_curve.png）
- ✅ **Discord送信**: 統計テキスト + グラフ画像の自動送信
- ✅ **tax/統合**: TradeHistoryRecorder・PnLCalculatorと統合

**実行方法**:
```bash
# 基本実行（過去7日間）
python3 scripts/reports/weekly_report.py

# カスタム期間指定
python3 scripts/reports/weekly_report.py --days 14
```

**GitHub Actions自動実行**:
```yaml
# .github/workflows/weekly_report.yml
# 毎週月曜9:00 JST自動実行
```

## 📝 使用方法・例

### **手動実行**（Phase 52.4更新版）
```bash
# プロジェクトルートから実行
cd /Users/nao/Desktop/bot

# 週間レポート生成・Discord送信
python3 scripts/reports/weekly_report.py

# 期待結果:
# ✅ 過去7日間の統計集計
# ✅ 損益曲線グラフ生成: /tmp/equity_curve_*.png
# ✅ Discord送信完了
```

### **カスタム期間実行**
```bash
# 過去14日間のレポート
python3 scripts/reports/weekly_report.py --days 14

# 過去30日間のレポート
python3 scripts/reports/weekly_report.py --days 30
```

### **GitHub Actions自動実行**（Phase 52.4更新版）
```bash
# .github/workflows/weekly_report.yml で自動実行
# スケジュール: 毎週月曜9:00 JST（UTC 00:00）
# 手動トリガー: workflow_dispatch対応
```

## ⚠️ 注意事項・制約

### **実行環境要件**
- **Python環境**: Python 3.13・matplotlib・Pillow必須
- **実行場所**: プロジェクトルートディレクトリから実行必須
- **データベース**: tax/trade_history.db存在必須（Phase 47取引記録システム）
- **Discord Webhook**: 環境変数DISCORD_WEBHOOK_URL設定必須

### **依存関係**
- `tax/trade_history_recorder.py`: 取引履歴記録システム（Phase 47）
- `tax/pnl_calculator.py`: 損益計算エンジン（Phase 47）
- `src/core/reporting/discord_notifier.py`: Discord通知システム
- `matplotlib`: グラフ生成
- `Pillow`: 画像処理

## 🔗 関連ファイル・依存関係

### **取引記録・損益計算**（Phase 47実装）
- `tax/trade_history_recorder.py`: SQLite取引履歴記録
- `tax/pnl_calculator.py`: 移動平均法損益計算
- `tax/trade_history.db`: 取引履歴データベース

### **レポート生成**（Phase 52.4更新）
- `src/core/reporting/discord_notifier.py`: Discord通知システム
- `src/core/reporting/`: 週間レポート生成システム

### **GitHub Actions統合**
- `.github/workflows/weekly_report.yml`: 週間レポート自動実行ワークフロー
- スケジュール: 毎週月曜9:00 JST
- 手動トリガー: workflow_dispatch対応

---

**🎯 重要事項**:
- ✅ **週間レポート自動送信**: 毎週月曜9:00 JST自動実行
- ✅ **Phase 52.3バグ修正適用**: 最大ドローダウン計算の正確性向上（累積損益基準 → ピーク残高基準）
- ✅ **テストカバレッジ追加**: 0% → 80%+ 達成（Phase 52.4）
- ✅ **設定管理統一**: ハードコード値をconfig/core/unified.yamlに移行
- ✅ **Phase 48達成成果**: Discord通知99%削減（300-1,500回/月 → 4回/月）・コスト35%削減（月額700-900円）

**推奨運用方法**:
1. **自動実行**: GitHub Actions週次自動実行（推奨）
2. **手動実行**: 月次確認・四半期確認時に手動実行
3. **カスタム期間**: 特定期間の分析が必要な場合に`--days`オプション使用
