# scripts/analytics/ - 統合分析基盤・データ収集・可視化

**Phase 13対応**: 統合分析基盤・データ収集・パフォーマンス分析・ダッシュボード機能（2025年8月26日現在）

## 📂 ファイル構成

```
analytics/
├── base_analyzer.py         # 共通基盤クラス・Cloud Run統合
├── data_collector.py        # 実データ収集・統計分析
├── performance_analyzer.py  # システムパフォーマンス分析
├── dashboard.py             # HTMLダッシュボード・可視化
└── README.md                # このファイル
```

## 🎯 役割・責任

統合分析基盤として以下を提供：
- **データ収集**: Cloud Runログからの実取引データ抽出・統計分析
- **パフォーマンス分析**: システム全体の包括的評価・異常検知
- **可視化ダッシュボード**: HTML・Chart.js統合レポート
- **共通基盤**: base_analyzer.py基盤クラスによる統一インターフェース

## 📊 主要機能・実装

### **base_analyzer.py**: 共通基盤クラス
- Cloud Runログ取得統合・gcloudコマンド実行
- エラーログ分析・パターン検出・重要度判定
- サービスヘルス監視・URL応答確認
- ファイル出力・logs/reports/配下統一保存

### **data_collector.py**: 実データ収集
- 取引統計収集（勝率・収益・シグナル頻度・エラー率）
- CSV/JSON出力・Discord通知・異常検知
- 時間指定・期間指定収集

### **performance_analyzer.py**: システム分析
- システムヘルス（CPU・メモリ・ネットワーク）
- エラー分析・レスポンス分析・改善提案
- 期間指定・形式指定分析

### **dashboard.py**: 可視化ダッシュボード
- HTML可視化・Chart.jsインタラクティブグラフ
- 取引統計表示・システム監視・Discord連携
- 自動レポート配信・アラート通知

## 🔧 使用方法・例

### **日常分析フロー**
```bash
# データ収集（24時間）
python scripts/analytics/data_collector.py --hours 24

# システム分析（週次）
python scripts/analytics/performance_analyzer.py --period 7d

# ダッシュボード生成・Discord通知
python scripts/analytics/dashboard.py --discord
```

### **詳細分析**
```bash
# 長期データ収集（1週間・JSON出力）
python scripts/analytics/data_collector.py --hours 168 --format json

# 詳細パフォーマンス分析（30日・マークダウン出力）
python scripts/analytics/performance_analyzer.py --period 30d --format markdown

# 期間指定ダッシュボード（24時間）
python scripts/analytics/dashboard.py --hours 24 --discord
```

## ⚠️ 注意事項・制約

### **実行環境制約**
1. **GCP認証必須**: gcloud auth設定済み環境
2. **ネットワーク接続**: Cloud Run・Discord APIアクセス必要
3. **実行時間**: 大量データ処理時数分要する場合あり
4. **並列実行制限**: 同時実行非推奨（ログ取得競合防止）

### **推奨使用パターン**
- **日次監視**: data_collector.py + dashboard.py
- **週次分析**: performance_analyzer.py + 詳細ダッシュボード
- **問題調査**: performance_analyzer.py短期間詳細モード
- **月次レポート**: 全スクリプト実行 + 長期統計

## 🔗 関連ファイル・依存関係

### **システム統合**
- **scripts/management/**: dev_check.py連携・自動パフォーマンス分析
- **scripts/testing/**: 品質チェック後性能測定・結果可視化
- **scripts/deployment/**: デプロイ後性能検証・本番監視

### **出力・保存先**
- **logs/reports/analytics/**: 分析結果・統計データ・ダッシュボード
- **logs/reports/data_collection/**: CSV/JSON統計データ
- **logs/system/**: Cloud Runログ・システムログ

### **外部依存**
- **GCP Cloud Run**: ログデータソース・サービス監視
- **Discord API**: 通知・レポート配信・アラート送信
- **Chart.js**: ダッシュボード可視化ライブラリ

---

**🎯 Phase 13対応完了**: 統合分析基盤・base_analyzer.py共通クラス・重複コード削除により効率的な監視・分析・可視化環境を実現。