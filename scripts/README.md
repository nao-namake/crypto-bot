# scripts/ - 運用スクリプト・ツール管理ディレクトリ

**Phase 13対応**: 機能別フォルダ構成・統合管理・開発支援・分析・デプロイメント自動化ツール集（2025年8月26日現在）

## 📂 ディレクトリ構成

```
scripts/
├── analytics/      # 統合分析・データ収集・ダッシュボード [詳細: README.md]
│   ├── base_analyzer.py             # 共通基盤クラス・Cloud Run統合
│   ├── data_collector.py            # 実データ収集・統計分析
│   ├── performance_analyzer.py      # システムパフォーマンス分析
│   └── dashboard.py                 # HTMLダッシュボード・可視化
├── management/     # 統合管理・開発支援・監視 [詳細: README.md]
│   ├── dev_check.py                 # 統合開発管理CLI（多機能）
│   └── ops_monitor.py               # 運用監視・ヘルスチェック
├── ml/            # 機械学習・モデル管理 [詳細: README.md]
│   └── create_ml_models.py          # MLモデル作成・アンサンブル構築
├── deployment/    # デプロイメント・インフラ [詳細: README.md]
│   ├── deploy_production.sh         # GCP Cloud Run本番デプロイ
│   ├── docker-entrypoint.sh         # Dockerエントリポイント
│   ├── setup_ci_prerequisites.sh    # CI/CD前提条件セットアップ
│   ├── setup_gcp_secrets.sh         # GCP Secret Manager設定
│   └── verify_gcp_setup.sh          # GCP環境検証
└── testing/       # テスト・品質保証 [詳細: README.md]
    ├── checks.sh                    # 統合品質チェック
    └── test_live_trading.py          # ライブトレード統合テスト
```

## 🎯 役割・責任

システム開発・運用・監視・デプロイメントに必要なスクリプト・ツールを機能別に整理・管理するディレクトリです。開発から本番運用まで一貫した自動化・品質保証・効率化を提供します。

**主要機能**:
- 統合開発管理・品質チェック自動化
- データ分析・パフォーマンス監視・可視化
- 機械学習モデル管理・自動学習
- GCPデプロイメント・インフラ管理
- テスト・品質保証・CI/CD統合

## 📝 使用方法・例

### **日常開発フロー**
```bash
# 開発状況確認
python scripts/management/dev_check.py full-check

# 品質チェック
python scripts/management/dev_check.py validate

# MLモデル作成・更新
python scripts/management/dev_check.py ml-models
```

### **分析・監視フロー**
```bash
# データ収集・分析
python scripts/analytics/data_collector.py --hours 24

# パフォーマンス分析
python scripts/analytics/performance_analyzer.py

# ダッシュボード生成
python scripts/analytics/dashboard.py --discord
```

### **デプロイメントフロー**
```bash
# デプロイ前チェック
bash scripts/testing/checks.sh

# 本番デプロイ
bash scripts/deployment/deploy_production.sh

# デプロイ後確認
python scripts/management/ops_monitor.py
```

## ⚠️ 注意事項・制約

### **実行環境の制約**
1. **プロジェクトルート**: 必ず`/Users/nao/Desktop/bot`から実行
2. **Python環境**: Python 3.8以上・必要なライブラリインストール済み
3. **GCP認証**: 一部スクリプトでgcloud auth設定が必要

### **権限・セキュリティ**
1. **実行権限**: シェルスクリプトは実行権限必須（chmod +x）
2. **API認証**: Bitbank API・Discord Webhook等の環境変数設定
3. **GCP権限**: Cloud Run・Secret Manager・Artifact Registry権限

### **リソース使用上の注意**
1. **メモリ使用量**: 機械学習系スクリプトは200MB-2GB使用
2. **実行時間**: 分析・MLモデル作成は数分～数十分要する場合あり
3. **並列実行**: 同時実行は推奨されません（リソース競合防止）

## 🔗 関連ファイル・依存関係

### **システム統合**
- **`src/`**: 新システム実装・スクリプトから利用
- **`config/`**: 設定ファイル・環境別設定
- **`models/`**: 機械学習モデル・メタデータ管理

### **出力・レポート**
- **`logs/reports/`**: スクリプト実行結果・分析レポート
- **`coverage-reports/`**: テストカバレッジ結果
- **`logs/deployment/`**: デプロイ関連ログ

### **外部依存**
- **GCP Cloud Run・Artifact Registry**: デプロイメント基盤
- **Discord API**: 通知・レポート配信
- **GitHub Actions**: CI/CD統合・自動実行

### **🗑️ 不要スクリプト特定・削除提案**

現在のscripts/構成を分析した結果、以下の最適化提案があります：

#### **重複機能・統合候補**
1. **ops_monitor.py（91KB）**: dev_check.pyと機能重複の可能性
   - 両方とも監視・ヘルスチェック機能を持つ
   - **提案**: 機能統合またはops_monitor.pyの軽量化

#### **使用頻度・保守性の検討**
1. **deployment/スクリプト群**: 5個のシェルスクリプト
   - setup_ci_prerequisites.sh（25KB）
   - verify_gcp_setup.sh（26KB）  
   - setup_gcp_secrets.sh（13KB）
   - **提案**: 実際の使用頻度確認・統合検討

#### **現状維持推奨**
- すべてのスクリプトが最近更新されており活発に使用
- 機能別分類が明確で保守性が高い
- 削除よりも統合・最適化が適切

---

**🎯 Phase 13対応完了**: 機能別フォルダ構成・統合管理・開発支援・分析・デプロイメント自動化による効率的なスクリプト管理環境を確立。開発から本番運用まで一貫した品質保証・自動化ツール集を実現。