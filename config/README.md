# config/ - 設定管理ディレクトリ

**Phase 13完了**: モード設定一元化・セキュリティ強化・CI/CD完全自動化により、包括的設定管理システムが確立。ペーパートレード安全性から本番運用まで、3層優先制御による統合設定管理を実現。

## 🎯 役割・責任

システム全体の設定を一元管理し、開発環境から本番運用まで、安全性・保守性・運用効率性を重視した設定管理を担当します。Phase 13で確立されたモード設定一元化システムにより、シンプルで安全な環境制御を提供します。

## 📁 ディレクトリ構成（Phase 13最終版）

```
config/
├── README.md                          # このファイル（Phase 13完了版）
├── .env.example                      # 環境変数テンプレート（セキュア）
│
├── core/                             # 🏗️ コア設定（基盤システム）
│   ├── README.md                     # コア設定ガイド（Phase 13完了版）
│   ├── base.yaml                     # 基本設定・モード一元化対応
│   └── feature_order.json            # 特徴量定義（12個厳選版）
│
├── production/                       # 🎯 本番運用設定（統合最適化）
│   ├── README.md                    # 本番運用ガイド（Phase 13完了版）
│   └── production.yaml              # 本番運用設定
│
└── infrastructure/                   # 🔧 インフラストラクチャ
    ├── README.md                     # インフラガイド（Phase 13完了版）
    ├── gcp_config.yaml               # GCP統合設定（更新推奨）
    └── cloudbuild.yaml               # Cloud Build設定
```

**✅ 最適化完了（Phase 13統合）**:
- `environments/` フォルダ廃止 → `production/` に統合（フォルダ階層最適化）
- `paper/` 削除 → `base.yaml` のモード一元化で代替
- `stage_*.yaml`, `testing.yaml`, `validation.yaml` 削除 → Phase 9レガシー除去

## 🔧 主要機能・実装

### **モード設定一元化システム（Phase 13完成版）**

**3層優先順位制御**:
1. **コマンドライン引数**（最優先）: `--mode live`
2. **環境変数**（中優先）: `MODE=live`
3. **YAMLファイル**（デフォルト）: `mode: paper`（安全デフォルト）

**デフォルト安全設計**:
- **config/core/base.yaml**: `mode: paper`で安全デフォルト
- **config/production/production.yaml**: 明示的`mode: live`
- **環境変数制御**: Cloud Runで自動`MODE=live`設定

### **セキュリティ強化システム**

**API認証情報管理**:
- **config/.env.example**: プレースホルダー形式（YOUR_BITBANK_API_KEY_HERE）
- **環境変数**: `BITBANK_API_KEY`, `BITBANK_API_SECRET`
- **GCP Secret Manager**: 本番運用での機密情報安全管理

**設定ファイル保護**:
- **YAMLファイル**: API認証情報記載禁止
- **環境変数優先**: 機密情報の設定ファイル除外
- **テンプレート提供**: 安全な開発環境セットアップ支援

## 📝 使用方法・例

### **基本的な設定利用**

**ペーパートレード（開発・テスト）**:
```bash
# デフォルト（自動的にpaper）
python3 main.py

# 明示的にpaper指定
python3 main.py --mode paper

# 環境変数での指定
export MODE=paper && python3 main.py
```

**本番運用**:
```bash
# 環境変数での本番指定（推奨）
export MODE=live
python3 main.py

# コマンドラインでの本番指定
python3 main.py --mode live

# 本番設定ファイル直接指定
python3 main.py --config config/production/production.yaml
```

### **CI/CDでの自動デプロイ**
```bash
# GitHub Actions自動デプロイ
git push origin main  # 自動的にMODE=liveでデプロイ

# デプロイ状況確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1
```

### **設定の確認・検証**
```python
from src.core.config import load_config

# 設定読み込み・確認
config = load_config('config/core/base.yaml')
print(f"モード: {config.mode}")  # paper（デフォルト）
print(f"信頼度閾値: {config.ml.confidence_threshold}")  # 0.35
```

## ⚠️ 注意事項・制約

### **モード設定の重要事項**
- **デフォルト安全**: 未指定時は自動的に`mode: paper`（仮想取引）
- **本番運用注意**: `MODE=live`または`--mode live`指定時のみ実取引
- **設定優先順位**: コマンドライン > 環境変数 > YAMLファイル
- **確認必須**: 本番運用前の設定モード確認

### **セキュリティ制約**
- **API認証情報**: YAMLファイルへの記載禁止
- **環境変数使用**: 機密情報は環境変数またはGCP Secret Manager管理
- **config/.env.example**: プレースホルダー形式での安全なテンプレート提供
- **設定分離**: 開発環境と本番環境の完全分離

### **運用制約**
- **取引時間**: Bitbank営業時間内での運用
- **API制限**: 適切なレート制限遵守
- **リソース制限**: Cloud Runメモリ・CPU制約考慮
- **コスト管理**: GCP料金・取引手数料の監視

### **Phase 13での変更点**
- **段階的デプロイ廃止**: stage_*.yaml, testing.yaml, validation.yaml不要化
- **モード一元化**: 3層優先制御による単純化
- **セキュリティ強化**: API認証情報の設定ファイル除外
- **設定統合**: production.yamlへの機能集約・保守性向上

## 🔗 関連ファイル・依存関係

### **重要な外部依存**
- **`src/core/config.py`**: モード設定一元化システム・設定読み込み
- **`main.py`**: エントリーポイント・モード制御・コマンドライン処理
- **`.github/workflows/ci.yml`**: CI/CD自動デプロイ・環境変数設定
- **`scripts/management/dev_check.py`**: 設定検証・品質チェック

### **GCP連携**
- **Secret Manager**: `bitbank-api-key`, `bitbank-api-secret`, `discord-webhook-url`
- **Cloud Run**: `crypto-bot-service-prod`本番サービス
- **Workload Identity**: GitHub Actions自動認証
- **Cloud Logging**: 設定・デプロイログ監視

### **設定システム統合**
- **config/core/base.yaml**: 全環境共通基本設定・デフォルト値
- **config/production/**: 本番運用設定
- **config/infrastructure/**: GCPインフラ・CI/CD設定
- **config/.env.example**: 環境変数テンプレート

---

**重要**: Phase 13完了により、段階的デプロイメントからモード設定一元化への移行が完了しました。3層優先制御（CLI > 環境変数 > YAML）による安全で効率的な設定管理システムを提供し、ペーパートレードから本番運用まで一貫した設定体験を実現しています。