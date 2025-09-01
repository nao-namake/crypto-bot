# config/production/ - 本番運用環境設定

**Phase 16-B完了**: 設定一元化・保守性向上完成により、160個ハードコード値統合・8個ヘルパー関数・620テスト100%成功・50%+カバレッジで、個人開発最適化された本番運用設定システムが完成

## 🎯 役割・責任

本番運用（実取引）における安全で効率的な設定管理を担当します。1万円スタート→50万円段階拡大の個人開発向け設定と、モード設定一元化システムと連携し、実際の資金を使用するbitbank信用取引環境での最適な設定値を提供し、リスク管理と収益性の両立を実現します。

## 📂 ファイル構成

```
production/
├── README.md               # このファイル（Phase 16-B完成版）
└── production.yaml         # 本番運用設定（実取引用・Phase 16-B対応）
```

**✅ Phase 16-B最適化完了**:
- **個人開発制約対応**: 1万円→50万円段階拡大・bitbank信用取引専用
- **620テスト品質保証**: 設定一元化全テスト合格維持・50%+カバレッジ
- **レガシー設定削除**: 古いstage設定・過剰パラメータ削除
- **現実準拠設定**: プロジェクト実際構成に完全準拠

## 🔧 主要機能・実装

### **production.yaml - 本番運用設定（Phase 16-B完成版）**

**bitbank信用取引専用設定**:
```yaml
# 本番モード（実取引・Phase 16-B対応）
mode: live  # 🚨 実際の資金での取引

# 取引所設定（bitbank信用取引専用）
exchange:
  name: bitbank
  symbol: "BTC/JPY"          # 信用取引専用通貨ペア
  leverage: 1.0              # 1倍（安全性最優先）
  rate_limit_ms: 35000       # 35秒間隔（本番安全マージン）
  timeout_ms: 120000         # 2分タイムアウト
  retries: 5                 # 信頼性確保

# 機械学習設定（Phase 16-B本番最適化）
ml:
  confidence_threshold: 0.65    # 65%（収益性重視・高品質シグナル）
  ensemble_enabled: true
  models: ["lgbm", "xgb", "rf"]
  model_weights: [0.5, 0.3, 0.2]
```

### **個人開発制約最適化**

**1万円→50万円段階拡大対応**:
```yaml
# Phase 16-B個人開発制約
trading_constraints:
  exchange: "bitbank"
  trading_type: "margin"        # 信用取引専用
  leverage_max: 2.0             # 2倍レバレッジ上限（bitbank仕様）
  leverage_actual: 1.0          # 実際使用（安全性重視）
  currency_pair: "BTC/JPY"
  initial_capital: 10000        # 1万円スタート
  target_capital: 500000        # 最終目標50万円
  features_count: 12            # 厳選特徴量数
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
    
  # Phase 16-B個人開発最適化設定
  risk_per_trade: 0.01          # 1取引あたり1%（安全・維持）
  kelly_max_fraction: 0.03      # Kelly基準最大3%（個人開発適正）
  max_drawdown: 0.20            # 最大ドローダウン20%
  consecutive_loss_limit: 5     # 連続5損失で24時間停止
```

### **モード設定一元化対応（Phase 16-B）**

**3層優先順位制御**:
1. **コマンドライン引数**（最優先）: `--mode live`
2. **環境変数**（中優先）: `MODE=live` 
3. **YAMLファイル**（デフォルト）: `mode: live`（production.yaml）

**安全性設計**:
- **デフォルト保護**: config/core/base.yamlは`mode: paper`で安全
- **明示的本番指定**: production.yamlのみ`mode: live`
- **環境変数制御**: Cloud Runで`MODE=live`自動設定

## 📝 使用方法・例

### **本番運用の開始（Phase 16-B対応）**
```bash
# 1. 環境変数での本番指定（推奨）
export MODE=live
python3 main.py --config config/core/base.yaml

# 2. コマンドラインでの本番指定
python3 main.py --config config/core/base.yaml --mode live

# 3. 直接production.yaml指定（非推奨・互換性維持）
python3 main.py --config config/production/production.yaml
```

### **CI/CDでの本番デプロイ（Phase 16-B対応）**
```bash
# GitHub Actions自動デプロイ（620テスト→設定検証→デプロイ）
git push origin main  # 自動的にMODE=liveでデプロイ

# 手動デプロイ確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1
gcloud logging read "resource.type=cloud_run_revision" --limit=10
```

### **本番設定の確認（Phase 16-B対応）**
```python
from src.core.config import load_config

# 本番設定読み込み
config = load_config('config/production/production.yaml')

# 重要設定確認（Phase 16-B対応）
assert config.mode == 'live', "本番モードが設定されていません"
print(f"信頼度閾値: {config.ml.confidence_threshold}")  # 0.65
print(f"リスク/取引: {config.risk.risk_per_trade}")      # 0.01 (1%)
print(f"Kelly基準: {config.risk.kelly_max_fraction}")    # 0.03 (3%)
print(f"特徴量数: {len(config.features.basic + config.features.technical + config.features.anomaly)}")  # 12
```

### **安全性チェック（Phase 16-B統合）**
```bash
# 本番前チェックリスト（620テスト対応）
python3 scripts/management/dev_check.py validate
python3 scripts/testing/checks.sh

# Phase 16-B品質チェック
python3 -m pytest tests/ --tb=short -v  # 620テスト実行
```

## ⚠️ 注意事項・制約

### **bitbank信用取引制約（Phase 16-B対応）**
- **通貨ペア**: BTC/JPY専用（bitbank信用取引対応）
- **レバレッジ**: 最大2倍（bitbank仕様）・実際1倍（安全性重視）
- **資金管理**: 1万円→成功時50万円段階拡大（個人開発現実的）
- **取引時間**: 24時間・自動取引継続性確保

### **Phase 16-B対応事項**
- **620テスト**: 設定一元化全テスト100%合格維持・品質保証継続
- **50%+カバレッジ**: 目標を上回る企業級品質保証達成・継続監視
- **型安全性**: MyPy統合・段階的型エラー解消継続
- **12個厳選特徴量**: feature_order.json準拠・順序重要性維持

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
- **`config/core/feature_order.json`**: 12個厳選特徴量定義
- **`src/core/config.py`**: モード設定一元化システム
- **`.github/workflows/ci.yml`**: Phase 16-A対応CI/CDパイプライン

### **GCP連携（Phase 16-B統合）**
- **Secret Manager**: `bitbank-api-key`, `bitbank-api-secret`, `discord-webhook-url`
- **Cloud Run**: `crypto-bot-service-prod`サービス
- **Artifact Registry**: Dockerイメージ管理・620テスト対応
- **Cloud Logging**: 本番運用ログ監視

### **監視・アラート（Phase 16-B強化）**
- **Discord Webhook**: リアルタイム通知・取引シグナル監視
- **Cloud Monitoring**: メトリクス・アラート・パフォーマンス監視
- **GitHub Actions**: デプロイ・品質監視・620テスト実行
- **pytest**: 設定検証・620テスト統合・型安全性チェック

### **品質保証システム**
- **620テスト**: 設定一元化品質保証・統合テスト強化対応
- **50%+カバレッジ**: 目標を上回る企業級品質保証継続
- **MyPy統合**: 型安全性・段階的型エラー解消
- **CI/CD品質ゲート**: 自動品質チェック・デプロイ制御

---

**重要**: Phase 16-B完了により、bitbank信用取引専用・160個ハードコード値統合・8個ヘルパー関数による動的設定管理・620テスト品質保証・個人開発最適化（1万円→50万円段階拡大）が完成しました。production.yamlは実資金を使用する本番運用設定であり、thresholds.yaml設定変更時は十分な監視体制・段階的検証での運用を実施してください。