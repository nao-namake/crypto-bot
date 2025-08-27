# config/production/ - 本番運用環境設定

**Phase 13完了**: フォルダ構造最適化・モード設定一元化・セキュリティ強化により、シンプルで安全な本番運用設定システムが確立

## 🎯 役割・責任

本番運用（実取引）における安全で効率的な設定管理を担当します。モード設定一元化システムと連携し、実際の資金を使用する取引環境での最適な設定値を提供し、リスク管理と収益性の両立を実現します。

## 📂 ファイル構成

```
production/
├── README.md               # このファイル（Phase 13完了版）
└── production.yaml         # 本番運用設定（実取引用・Phase 13対応）
```

**✅ 削除完了（Phase 13最適化）**:
- `stage_10.yaml`, `stage_50.yaml` - Phase 9段階的デプロイの遺物（削除済み）
- `testing.yaml`, `validation.yaml` - 最小単位テスト・1万円検証（削除済み）

## 🔧 主要機能・実装

### **production.yaml - 本番運用設定（Phase 13完成版）**

**本番最適化設定**:
```yaml
# 本番モード（実取引）
mode: live  # 🚨 実際の資金での取引

# 取引所設定（本番用厳格設定）
exchange:
  name: bitbank
  symbol: "BTC/JPY"
  rate_limit_ms: 35000      # 35秒間隔（安全マージン）
  timeout_ms: 120000        # 2分タイムアウト
  retries: 5                # 信頼性確保

# 機械学習設定（本番最適化）
ml:
  confidence_threshold: 0.65   # 65%（収益性重視）
  ensemble_enabled: true
  models: ["lgbm", "xgb", "rf"]
  model_weights: [0.5, 0.3, 0.2]
```

### **モード設定一元化対応**

**3層優先順位制御**:
1. **コマンドライン引数**（最優先）: `--mode live`
2. **環境変数**（中優先）: `MODE=live` 
3. **YAMLファイル**（デフォルト）: `mode: live`（production.yaml）

**安全性設計**:
- **デフォルト保護**: config/core/base.yamlは`mode: paper`で安全
- **明示的本番指定**: production.yamlのみ`mode: live`
- **環境変数制御**: Cloud Runで`MODE=live`自動設定

### **本番運用最適化機能**

**リスク管理強化**:
```yaml
risk:
  risk_per_trade: 0.008       # 0.8%（保守的）
  kelly_max_fraction: 0.025   # 2.5%（安全運用）  
  max_drawdown: 0.15          # 15%制限
  stop_loss_atr_multiplier: 1.8  # 損切り強化
  consecutive_loss_limit: 3   # 連続損失制限
```

**監視・通知システム**:
```yaml
monitoring:
  health_check:
    enabled: true
    interval_seconds: 30
  performance:
    enabled: true
    metrics_interval: 60
  discord_notifications:
    enabled: true
    levels: ["error", "warning", "trade"]
```

## 📝 使用方法・例

### **本番運用の開始**
```bash
# 1. 環境変数での本番指定（推奨）
export MODE=live
python3 main.py --config config/core/base.yaml

# 2. コマンドラインでの本番指定
python3 main.py --config config/core/base.yaml --mode live

# 3. 直接production.yaml指定（非推奨）
python3 main.py --config config/production/production.yaml
```

### **CI/CDでの本番デプロイ**
```bash
# GitHub Actions自動デプロイ
git push origin main  # 自動的にMODE=liveでデプロイ

# 手動デプロイ確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1
gcloud logging read "resource.type=cloud_run_revision" --limit=10
```

### **本番設定の確認**
```python
from src.core.config import load_config

# 本番設定読み込み
config = load_config('config/production/production.yaml')

# 重要設定確認
assert config.mode == 'live', "本番モードが設定されていません"
print(f"信頼度閾値: {config.ml.confidence_threshold}")  # 0.65
print(f"リスク/取引: {config.risk.risk_per_trade}")      # 0.008 (0.8%)
```

### **安全性チェック**
```bash
# 本番前チェックリスト
python3 scripts/management/dev_check.py validate --mode live
python3 scripts/deployment/verify_production_config.py
```

## ⚠️ 注意事項・制約

### **本番運用の重要事項**
- **実資金リスク**: production.yamlは実際の資金を使用
- **慎重な変更**: 設定変更は十分なテスト後に実施
- **監視必須**: 24時間監視体制での運用推奨
- **緊急停止**: 異常時即座停止できる体制維持

### **セキュリティ制約**
- **API認証**: production.yamlにAPIキー記載禁止
- **環境変数使用**: 機密情報はGCP Secret Manager管理
- **アクセス制限**: 本番設定ファイルへの適切なアクセス制御
- **監査ログ**: 設定変更履歴の記録・管理

### **運用制約**
- **取引時間**: Bitbank営業時間内での運用
- **API制限**: 35秒間隔遵守・過度なリクエスト防止
- **リソース制限**: Cloud Runメモリ・CPU制約考慮
- **コスト管理**: GCP料金・取引手数料の監視

### **Phase 13での変更点**
- **段階的デプロイ廃止**: stage_*.yaml, testing.yaml, validation.yaml不要化
- **モード一元化**: 環境変数とコマンドライン優先の単純化
- **設定統合**: production.yamlへの機能集約・保守性向上

## 🔗 関連ファイル・依存関係

### **重要な外部依存**
- **`config/core/base.yaml`**: 基本設定・デフォルト安全値
- **`src/core/config.py`**: モード設定一元化システム
- **`.github/workflows/ci.yml`**: 自動デプロイ・環境変数設定
- **`scripts/management/dev_check.py`**: 本番前品質チェック

### **GCP連携**
- **Secret Manager**: `bitbank-api-key`, `bitbank-api-secret`
- **Cloud Run**: `crypto-bot-service-prod`サービス
- **Artifact Registry**: Dockerイメージ管理
- **Cloud Logging**: 本番運用ログ監視

### **監視・アラート**
- **Discord Webhook**: リアルタイム通知
- **Cloud Monitoring**: メトリクス・アラート
- **GitHub Actions**: デプロイ・品質監視
- **pytest**: 設定検証（306テスト対応）

---

**重要**: Phase 13完了により、段階的デプロイメントからモード設定一元化への移行が完了しました。production.yamlのみで本番運用を行い、不要な段階的設定ファイルの削除を推奨します。本番運用時は十分な監視体制での運用を実施してください。