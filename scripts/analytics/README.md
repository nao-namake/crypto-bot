# scripts/analytics/ - Phase 19統合分析基盤・データ収集・MLOps可視化システム

**Phase 19完了**: 特徴量統一管理・週次自動再学習・MLOps基盤完成・654テスト100%・59.24%カバレッジ達成に対応した統合分析基盤・データ収集・パフォーマンス監視・可視化システム（2025年9月4日現在）

## 📂 ファイル構成

```
analytics/
├── base_analyzer.py         # Phase 19共通基盤クラス・Cloud Run・Discord統合
├── data_collector.py        # MLOps実データ収集・feature_manager統計分析
├── performance_analyzer.py  # ProductionEnsemble・週次学習パフォーマンス分析
├── dashboard.py             # HTMLダッシュボード・Phase 19統合可視化
└── README.md                # このファイル
```

## 🎯 役割・責任

**Phase 19 MLOps基盤**における統合分析・データ収集・パフォーマンス監視の核心システムを担当。feature_manager.py統一管理・ProductionEnsemble・週次自動再学習・654テスト品質保証を統合した包括的な分析・可視化・監視システムを提供します。

**主要機能**:
- **MLOps統合データ収集**: feature_manager.py・ProductionEnsemble・週次学習統計分析
- **654テスト品質監視**: テスト結果・59.24%カバレッジ・CI/CD品質ゲート分析
- **リアルタイム分析**: Cloud Run 24時間監視・Discord通知・自動アラート
- **統合可視化**: Phase 19対応HTMLダッシュボード・Chart.js・週次学習可視化

## 🔧 主要機能・実装（Phase 19統合）

### **base_analyzer.py - Phase 19共通基盤クラス（核心機能）**

**MLOps統合機能**:
- **Cloud Run統合**: gcloudログ取得・サービス監視・エンドポイント確認
- **feature_manager統合**: 12特徴量生成ログ・統計分析・異常検知
- **ProductionEnsemble監視**: 3モデル統合・予測精度・性能評価
- **654テスト統合**: テスト結果分析・カバレッジ監視・品質ゲート確認

### **data_collector.py - MLOps実データ収集（Phase 19対応）**

**週次自動再学習統合**:
- **取引統計収集**: 勝率・収益・シグナル頻度・feature_manager連携統計
- **MLOps統計**: ProductionEnsemble性能・週次学習効果・モデル精度
- **654テスト統計**: テスト成功率・カバレッジ推移・品質メトリクス
- **CSV/JSON出力**: Discord通知・異常検知・時系列分析

### **performance_analyzer.py - システム・MLOps性能分析**

**Phase 19統合分析**:
- **システムヘルス**: Cloud Run性能・CPU・メモリ・レスポンス時間
- **MLOps性能**: feature_manager処理時間・ProductionEnsemble予測レイテンシ
- **週次学習監視**: 学習時間・モデル更新・デプロイ成功率
- **エラー分析**: パターン検出・改善提案・自動復旧監視

### **dashboard.py - Phase 19統合可視化ダッシュボード**

**MLOps統合可視化**:
- **HTMLダッシュボード**: Chart.js・Phase 19対応・週次学習可視化
- **取引統計表示**: feature_manager連携・ProductionEnsemble精度グラフ
- **654テスト可視化**: テスト結果・カバレッジ推移・品質トレンド
- **Discord連携**: 自動レポート・アラート通知・監視統合

## 📝 使用方法・例（Phase 19推奨ワークフロー）

### **日常MLOps監視フロー（Phase 19必須）**

```bash
# Phase 19統合データ収集（24時間・MLOps統計含む）
python3 scripts/analytics/data_collector.py --hours 24 --mlops

# 期待結果: 
# ✅ feature_manager 12特徴量統計・ProductionEnsemble性能・654テスト状況

# 週次学習パフォーマンス分析（Phase 19対応）
python3 scripts/analytics/performance_analyzer.py --period 7d --include-mlops

# 期待結果:
# ✅ 週次学習効果・モデル精度推移・システム性能・エラー分析

# Phase 19統合ダッシュボード（Discord通知）
python3 scripts/analytics/dashboard.py --discord --phase19

# 期待結果:
# ✅ MLOps可視化・654テスト状況・週次学習監視・統合レポート
```

### **詳細MLOps分析（Phase 19対応）**

```python
# Phase 19統合分析実行
from scripts.analytics.base_analyzer import CloudRunAnalyzer
from scripts.analytics.data_collector import TradingDataCollector

# MLOps統合分析
analyzer = CloudRunAnalyzer()
collector = TradingDataCollector()

# feature_manager・ProductionEnsemble統合分析
mlops_data = collector.collect_mlops_statistics(hours=168)      # 1週間
system_analysis = analyzer.run_analysis(hours=168, include_health_check=True)

# 654テスト品質分析
quality_metrics = analyzer.analyze_test_quality_trends()

print(f"MLOps統計: {len(mlops_data['predictions'])}件予測")
print(f"週次学習: {mlops_data['weekly_training']['last_success']}")
print(f"654テスト: {quality_metrics['current_success_rate']}%成功率")
```

### **長期トレンド分析（Phase 19統合）**

```bash
# 30日間MLOps・品質統合分析
python3 scripts/analytics/performance_analyzer.py --period 30d --format json --output-mlops

# Phase 19統合ダッシュボード（月次レポート）
python3 scripts/analytics/dashboard.py --hours 720 --discord --monthly-report

# 期待結果:
# ✅ 30日間MLOps性能・654テスト品質推移・週次学習効果・改善提案
```

## ⚠️ 注意事項・制約（Phase 19対応）

### **Phase 19統合制約**

1. **MLOps整合性**: feature_manager.py・ProductionEnsemble・週次学習との統合必須
2. **654テスト品質**: 分析実行前後でテスト成功・カバレッジ維持必須
3. **CI/CD統合**: GitHub Actions・品質ゲート・段階的デプロイとの連携
4. **24時間監視**: Cloud Run・Discord通知・自動復旧機能への依存

### **実行環境・権限要件**

1. **Python環境**: Python 3.13・依存関係完全・プロジェクトルートから実行
2. **GCP統合**: Workload Identity・Cloud Run・ログ取得権限設定済み
3. **GitHub統合**: Actions権限・週次学習ワークフロー監視権限
4. **Discord統合**: Webhook URL・通知権限・アラート設定

### **推奨使用パターン（Phase 19対応）**

- **日次MLOps監視**: data_collector.py + dashboard.py（feature_manager統計含む）
- **週次学習分析**: performance_analyzer.py週次モード（学習効果評価）
- **品質問題調査**: 654テスト詳細分析・カバレッジ低下要因分析
- **月次統合レポート**: 全スクリプト実行・MLOps・品質・性能統合分析

### **データ保存・管理**

1. **自動保存**: logs/reports/analytics/・タイムスタンプ・構造化保存
2. **保存期間**: 30日間・重要レポート手動保護・定期クリーンアップ
3. **形式統一**: JSON・CSV・HTML・Discord連携・AI解析最適化
4. **履歴管理**: トレンド分析・比較・パフォーマンス推移追跡

## 🔗 関連ファイル・依存関係（Phase 19統合）

### **Phase 19 MLOps基盤統合**
- **`src/features/feature_manager.py`**: 特徴量統一管理・12特徴量・分析統計統合
- **`src/ml/ensemble.py`**: ProductionEnsemble・モデル管理・性能分析統合
- **`.github/workflows/`**: 週次自動再学習・CI/CD・品質ゲート・分析連携
- **`scripts/management/dev_check.py`**: 統合品質チェック・MLOps診断・分析連携

### **品質保証・監視システム**
- **`scripts/testing/checks.sh`**: 654テスト・カバレッジ・品質分析データソース
- **`tests/unit/`**: 654テスト・品質保証・分析スクリプト動作検証
- **`logs/reports/ci_checks/`**: 品質チェック結果・分析データ・履歴管理

### **出力・保存先・統合**
- **`logs/reports/analytics/`**: Phase 19分析結果・MLOps統計・ダッシュボード
- **`logs/reports/data_collection/`**: feature_manager統計・ProductionEnsemble性能
- **`logs/system/`**: Cloud Runログ・週次学習ログ・システムログ統合

### **外部依存・統合システム**
- **GCP Cloud Run**: 本番ログデータソース・24時間サービス監視・週次学習環境
- **Discord API**: 通知・レポート配信・アラート送信・MLOps監視統合
- **Chart.js**: HTMLダッシュボード・Phase 19対応可視化ライブラリ
- **GitHub Actions**: 週次学習監視・CI/CD統合・品質ゲート連携

---

**🎯 Phase 19完了**: 特徴量統一管理・週次自動再学習・MLOps基盤・654テスト100%・59.24%カバレッジ統合による包括的分析・データ収集・パフォーマンス監視・可視化システムを実現