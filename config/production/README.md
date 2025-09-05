# config/production/ - 本番運用環境設定

**Phase 19完了**: 特徴量定義一元化・バージョン管理システム改良・MLOps基盤確立により、654テスト100%成功・59.24%カバレッジ達成・企業級品質保証を実現した継続的品質改善システムが完全稼働

## 🎯 役割・責任

本番運用（実取引）における安全で効率的な設定管理を担当します。1万円スタート→50万円段階拡大の個人開発向け設定と、特徴量統一管理・MLOps基盤と連携し、実際の資金を使用するbitbank信用取引環境での最適な設定値を提供し、12特徴量統一管理・週次自動学習・リスク管理と収益性の両立を実現します。

## 📂 ファイル構成

```
production/
├── README.md               # このファイル（Phase 19完成版）
└── production.yaml         # 本番運用設定（実取引用・Phase 19対応）
```

**✅ Phase 19最適化完了**:
- **特徴量統一管理対応**: 12特徴量一元化・feature_manager.py統合・整合性100%
- **654テスト品質保証**: 35テスト追加・100%成功・59.24%カバレッジ達成
- **MLOps基盤確立**: 週次自動学習・バージョン管理・ProductionEnsemble対応
- **本番運用最適化**: GCPクリーンアップ・コスト30%削減・企業級品質

## 🔧 主要機能・実装

### **production.yaml - 本番運用設定（Phase 19完成版）**

**bitbank信用取引専用設定**:
```yaml
# 本番モード（実取引・Phase 19対応）
mode: live  # 🚨 実際の資金での取引

# 取引所設定（bitbank信用取引専用）
exchange:
  name: bitbank
  symbol: "BTC/JPY"          # 信用取引専用通貨ペア
  leverage: 1.0              # 1倍（安全性最優先）
  rate_limit_ms: 35000       # 35秒間隔（本番安全マージン）
  timeout_ms: 120000         # 2分タイムアウト
  retries: 5                 # 信頼性確保

# 機械学習設定（Phase 19本番最適化・MLOps統合）
ml:
  confidence_threshold: 0.65    # 65%（収益性重視・高品質シグナル）
  ensemble_enabled: true
  models: ["lgbm", "xgb", "rf"]
  model_weights: [0.5, 0.3, 0.2]
```

### **個人開発制約最適化**

**1万円→50万円段階拡大対応（Phase 19特徴量統一管理）**:
```yaml
# Phase 19個人開発制約・特徴量統一管理対応
trading_constraints:
  exchange: "bitbank"
  trading_type: "margin"        # 信用取引専用
  leverage_max: 2.0             # 2倍レバレッジ上限（bitbank仕様）
  leverage_actual: 1.0          # 実際使用（安全性重視）
  currency_pair: "BTC/JPY"
  initial_capital: 10000        # 1万円スタート
  target_capital: 500000        # 最終目標50万円
  features_count: 12            # 特徴量統一管理（feature_manager.py）
  timeframes: ["15m", "4h"]     # マルチタイムフレーム
```

### **リスク管理強化（個人開発最適化）**

**Kelly基準・安全性重視**:
```yaml
risk:
  # Kelly基準ポジションサイジング（個人開発最適化）
  kelly_criterion:
    max_position_ratio: 0.03    # 最大3%（個人開発安全性重視）
    safety_factor: 0.7          # Kelly値の70%使用
    
  # Phase 19個人開発最適化設定
  risk_per_trade: 0.01          # 1取引あたり1%（安全・維持）
  kelly_max_fraction: 0.03      # Kelly基準最大3%（個人開発適正）
  max_drawdown: 0.20            # 最大ドローダウン20%
  consecutive_loss_limit: 5     # 連続5損失で24時間停止
```

### **モード設定一元化対応（Phase 19統合）**

**3層優先順位制御**:
1. **コマンドライン引数**（最優先）: `--mode live`
2. **環境変数**（中優先）: `MODE=live` 
3. **YAMLファイル**（デフォルト）: `mode: live`（production.yaml）

**安全性設計**:
- **デフォルト保護**: config/core/base.yamlは`mode: paper`で安全
- **明示的本番指定**: production.yamlのみ`mode: live`
- **環境変数制御**: Cloud Runで`MODE=live`自動設定

## 📝 使用方法・例

### **本番運用の開始（Phase 19対応）**
```bash
# 1. 環境変数での本番指定（推奨）
export MODE=live
python3 main.py --config config/core/base.yaml

# 2. コマンドラインでの本番指定
python3 main.py --config config/core/base.yaml --mode live

# 3. 直接production.yaml指定（非推奨・互換性維持）
python3 main.py --config config/production/production.yaml
```

### **CI/CDでの本番デプロイ（Phase 19対応）**
```bash
# GitHub Actions自動デプロイ（654テスト→設定検証→デプロイ・MLOps統合）
git push origin main  # 自動的にMODE=liveでデプロイ

# 手動デプロイ確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1
gcloud logging read "resource.type=cloud_run_revision" --limit=10
```

### **本番設定の確認（Phase 19対応）**
```python
from src.core.config import load_config

# 本番設定読み込み
config = load_config('config/production/production.yaml')

# 重要設定確認（Phase 19対応・特徴量統一管理）
assert config.mode == 'live', "本番モードが設定されていません"
print(f"信頼度閾値: {config.ml.confidence_threshold}")  # 0.65
print(f"リスク/取引: {config.risk.risk_per_trade}")      # 0.01 (1%)
print(f"Kelly基準: {config.risk.kelly_max_fraction}")    # 0.03 (3%)
# Phase 19特徴量統一管理確認
from src.core.config.feature_manager import FeatureManager
fm = FeatureManager()
print(f"特徴量数: {fm.get_feature_count()}")  # 12（feature_manager.py統一管理）
print(f"特徴量一覧: {fm.get_feature_names()}")  # 12特徴量統一定義
```

### **安全性チェック（Phase 19統合）**
```bash
# 本番前チェックリスト（654テスト・特徴量統一管理対応）
python3 scripts/management/dev_check.py validate
python3 scripts/testing/checks.sh

# Phase 19品質チェック（MLOps・特徴量統一管理対応）
python3 -m pytest tests/ --tb=short -v  # 654テスト実行・59.24%カバレッジ
```

## ⚠️ 注意事項・制約

### **bitbank信用取引制約（Phase 19対応）**
- **通貨ペア**: BTC/JPY専用（bitbank信用取引対応）
- **レバレッジ**: 最大2倍（bitbank仕様）・実際1倍（安全性重視）
- **資金管理**: 1万円→成功時50万円段階拡大（個人開発現実的）
- **取引時間**: 24時間・自動取引継続性確保

### **Phase 19対応事項**
- **654テスト**: 35テスト追加・100%成功・特徴量統一管理対応
- **59.24%カバレッジ**: 4.32%向上・企業級品質保証達成・継続監視
- **特徴量統一管理**: feature_manager.py・12特徴量・整合性100%
- **MLOps基盤**: 週次自動学習・ProductionEnsemble・バージョン管理

### **本番運用の重要事項**
- **実資金リスク**: production.yamlは実際の資金を使用
- **慎重な変更**: 設定変更は十分なテスト後に実施
- **監視必須**: Discord・Cloud Monitoring24時間監視体制
- **緊急停止**: 異常時即座停止できる体制維持

### **セキュリティ制約（GCP統合）**
- **API認証**: production.yamlにAPIキー記載禁止
- **GCP Secret Manager**: bitbank API・Discord Webhook管理
- **Workload Identity**: GitHub Actions自動認証
- **監査ログ**: 設定変更履歴の記録・管理

### **運用制約（個人開発最適化）**
- **取引時間**: Bitbank営業時間内での運用
- **API制限**: 35秒間隔遵守・過度なリクエスト防止
- **リソース制限**: Cloud Run 1Gi メモリ・1 CPU制約考慮
- **コスト管理**: 月額約2000円・GCP料金・取引手数料監視

## 🔗 関連ファイル・依存関係

### **重要な外部依存**
- **`config/core/base.yaml`**: 基本設定・デフォルト安全値
- **`config/core/feature_order.json`**: 12個厳選特徴量定義（Phase 19統一管理）
- **`src/core/config/feature_manager.py`**: 特徴量統一管理システム（Phase 19新規）
- **`src/core/config.py`**: モード設定一元化システム
- **`.github/workflows/ci.yml`**: CI/CDパイプライン
- **`.github/workflows/model-training.yml`**: 週次自動学習・MLOps統合（Phase 19新規）

### **GCP連携（Phase 16-B統合）**
- **Secret Manager**: `bitbank-api-key`, `bitbank-api-secret`, `discord-webhook-url`
- **Cloud Run**: `crypto-bot-service-prod`サービス
- **Artifact Registry**: Dockerイメージ管理・654テスト対応・GCPクリーンアップ最適化
- **Cloud Logging**: 本番運用ログ監視

### **監視・アラート（Phase 19強化）**
- **Discord Webhook**: リアルタイム通知・取引シグナル監視
- **Cloud Monitoring**: メトリクス・アラート・パフォーマンス監視
- **GitHub Actions**: デプロイ・品質監視・654テスト実行・週次ML学習
- **pytest**: 設定検証・620テスト統合・型安全性チェック

### **品質保証システム（Phase 19企業級基準）**
- **654テスト**: 35テスト追加・特徴量統一管理・MLOps品質保証対応
- **59.24%カバレッジ**: 4.32%向上・企業級品質保証継続・継続監視
- **特徴量品質**: feature_manager.py・12特徴量統一・整合性100%
- **MLOps統合**: 週次自動学習・ProductionEnsemble・バージョン管理・品質検証

---

---

**🎯 Phase 19完了・企業級品質達成**: 特徴量定義一元化・バージョン管理システム改良・MLOps基盤確立により、654テスト100%成功・59.24%カバレッジ達成・12特徴量統一管理・週次自動学習を実現した継続的品質改善システムが完全稼働**

## 🚀 Phase 19完了記録・本番運用品質達成

**完了日時**: 2025年9月4日（Phase 19企業級品質達成）  
**Phase 19本番運用品質達成**: 
- ✅ **654テスト100%成功** (35テスト追加・本番運用品質保証・回帰防止)
- ✅ **59.24%カバレッジ達成** (54.92%→59.24%・4.32%向上・企業級品質)
- ✅ **特徴量統一管理** (feature_manager.py・12特徴量・整合性100%・本番安全性)
- ✅ **MLOps本番統合** (週次自動学習・ProductionEnsemble・バージョン管理)
- ✅ **GCP最適化** (30%コスト削減・本番リソース効率化・運用コスト改善)

**継続本番運用体制**:
- 🎯 **企業級本番品質**: 59.24%カバレッジ・654テスト・本番品質劣化防止
- 🤖 **本番特徴量安全性**: 12特徴量統一管理・整合性監視・取引安全保証
- 📊 **本番MLOps統合**: 週次学習・バージョン管理・本番モデル品質保証
- 💰 **本番コスト最適化**: GCPクリーンアップ・30%削減・運用効率化
- 🔧 **本番継続改善**: 品質向上・テスト拡張・本番運用基盤強化

**重要**: Phase 19完了により、特徴量統一管理・MLOps基盤・企業級品質保証が確立されました。production.yamlは実資金を使用する本番運用設定であり、特徴量整合性・週次学習品質・システム監視体制での段階的検証運用を継続実施してください。