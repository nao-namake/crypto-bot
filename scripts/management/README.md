# scripts/management/ - 統合管理・開発支援・監視

**Phase 13対応**: 統合管理CLI・開発支援・運用監視・品質保証（2025年8月26日現在）

## 📂 ファイル構成

```
management/
├── dev_check.py           # 統合開発管理CLI（多機能）
├── ops_monitor.py         # 運用監視・ヘルスチェック
├── status_config.json     # システム状態設定
└── README.md              # このファイル
```

## 🎯 役割・責任

統合管理・開発支援システムとして以下を提供：
- **開発管理**: 品質チェック・テスト実行・Phase実装確認
- **運用監視**: 本番環境監視・システム診断・ヘルスチェック
- **デプロイ支援**: CI/CD統合・品質ゲート・環境確認
- **診断機能**: システム状態分析・問題検出・改善提案

## 🔧 主要機能・実装

### **dev_check.py**: 統合開発管理CLI（多機能）
- 6段階統合チェック・Phase実装確認・品質保証
- MLモデル作成・検証・テスト実行・CI/CD統合
- システム状態分析・デプロイ前確認・統合診断

### **ops_monitor.py**: 運用監視・ヘルスチェック
- 本番環境監視・システム診断・障害検知
- Cloud Run稼働状況・パフォーマンス分析・Discord通知
- リアルタイム監視・アラート・問題早期発見

### **status_config.json**: システム状態設定
- 監視対象設定・閾値管理・アラートルール
- システム状態基準・品質指標・運用ポリシー

## 🔧 使用方法・例

### **統合開発管理（dev_check.py）**
```bash
# 6段階統合チェック（推奨）
python scripts/management/dev_check.py full-check

# Phase実装状況確認
python scripts/management/dev_check.py phase-check

# 品質チェック
python scripts/management/dev_check.py validate

# MLモデル作成・検証
python scripts/management/dev_check.py ml-models

# システム状態確認
python scripts/management/dev_check.py status
```

### **運用監視（ops_monitor.py）**
```bash
# 運用監視・診断
python scripts/management/ops_monitor.py

# 詳細監視
python scripts/management/ops_monitor.py --verbose

# Discord通知付き監視
python scripts/management/ops_monitor.py --discord
```

## ⚠️ 注意事項・制約

### **実行環境制約**
1. **プロジェクトルート**: 必ず`/Users/nao/Desktop/bot`から実行
2. **Python環境**: Python 3.8以上・必要ライブラリインストール済み
3. **GCP認証**: ops_monitor.pyでgcloud auth設定必要
4. **権限設定**: Cloud Run・Secret Manager・Artifact Registry権限

### **パフォーマンス制約**
- **実行時間**: dev_check.py full-check約5-10分要する場合あり
- **メモリ使用**: MLモデル作成時200MB-1GB使用
- **並列実行制限**: 同時実行非推奨（リソース競合防止）
- **タイムアウト**: 各チェック最大300秒制限

### **データ・状態管理**
- **レポート出力**: logs/reports/management/自動保存
- **状態設定**: status_config.json設定ファイル依存
- **ログ管理**: システムログ・監視ログ一元管理

## 🔗 関連ファイル・依存関係

### **システム統合**
- **scripts/testing/**: checks.sh品質チェック・テスト実行統合
- **scripts/analytics/**: BaseAnalyzer共通基盤・データ分析統合
- **scripts/deployment/**: デプロイ前確認・GCP環境検証統合
- **scripts/ml/**: MLモデル作成・検証・メタデータ管理

### **設定・データ**
- **src/**: 新システム実装・コンポーネント確認・インポート検証
- **config/**: 設定ファイル・環境別設定・validation確認
- **models/**: MLモデル・メタデータ・性能指標確認
- **logs/**: システムログ・レポート保存・状態管理

### **外部依存**
- **GCP Cloud Run**: 本番環境監視・稼働状況確認・パフォーマンス分析
- **Discord API**: 通知・アラート・レポート配信・重要イベント通知
- **GitHub Actions**: CI/CD統合・自動品質チェック・デプロイ連携

---

**🎯 Phase 13対応完了**: 統合管理CLI・運用監視・品質保証により開発から本番運用まで一貫した管理システムを実現。