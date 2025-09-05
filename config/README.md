# config/ - 設定管理ディレクトリ

**Phase 19完了**: 特徴量定義一元化・バージョン管理システム改良・MLOps基盤確立により、654テスト100%成功・59.24%カバレッジ達成・12特徴量統一管理・週次自動学習を実現。feature_manager.py追加でシステム保守性大幅向上・企業級品質保証された継続的品質改善システムを完成。

## 🎯 役割・責任

システム全体の設定を一元管理し、開発環境から本番運用まで、bitbank信用取引・1万円→50万円段階拡大・特徴量統一管理・MLOps基盤・安全性・保守性・運用効率性を重視した設定管理を担当します。Phase 19で完成した12特徴量統一管理・MLOps基盤・継続的品質改善システムにより、シンプルで安全・効率的・企業級品質の環境制御を提供します。

## 📁 ディレクトリ構成（Phase 16-B完了版）

```
config/
├── README.md                          # このファイル（Phase 19完了版）
├── .env.example                      # 環境変数テンプレート（セキュア）
│
├── core/                             # 🏗️ コア設定（基盤システム・Phase 19完了）
│   ├── README.md                     # コア設定ガイド（Phase 19完了版）
│   ├── base.yaml                     # 基本設定・動的設定統合対応
│   ├── feature_order.json            # 12個厳選特徴量定義（feature_manager.py統一管理）
│   └── thresholds.yaml               # 動的閾値設定（160個ハードコード値統合）
│
├── production/                       # 🎯 本番運用設定（Phase 19個人運用最適化）
│   ├── README.md                    # 本番運用ガイド（Phase 19完了版）
│   └── production.yaml              # 本番運用設定（1万円運用・MLOps統合・特徴量統一管理）
│
└── infrastructure/                   # 🔧 インフラストラクチャ（Phase 19統合最適化）
    ├── README.md                     # インフラガイド（Phase 19完了版）
    ├── gcp_config.yaml               # GCP統合設定（654テスト対応・MLOpsクリーンアップ対応）
    └── cloudbuild.yaml               # Cloud Build設定（654テスト・週次ML学習対応）
```

**✅ Phase 19設定一元化完了**:
- **特徴量統一管理完成**: feature_manager.py・12特徴量一元化・整合性100%保証
- **MLOps基盤確立**: 週次自動学習・バージョン管理・ProductionEnsemble対応
- **654テスト品質向上**: 35テスト追加・100%成功・59.24%カバレッジ達成
- **企業級品質保証**: 継続的品質改善・GCPクリーンアップ・30%コスト削減

## 🔧 主要機能・実装

### **モード設定一元化システム（Phase 16-A完成版）**

**3層優先順位制御**:
1. **コマンドライン引数**（最優先）: `--mode live`
2. **環境変数**（中優先）: `MODE=live`
3. **YAMLファイル**（デフォルト）: `mode: paper`（安全デフォルト）

**デフォルト安全設計**:
- **config/core/base.yaml**: `mode: paper`で安全デフォルト
- **config/production/production.yaml**: 明示的`mode: live`
- **環境変数制御**: Cloud Runで自動`MODE=live`設定

### **thresholds.yaml動的設定システム（Phase 16-B完成版）**

**160個ハードコード値完全統合**:
```yaml
# ML関連動的閾値（Phase 16-B拡張）
ml:
  default_confidence: 0.5           # ダミーモデル時信頼度
  emergency_stop_on_dummy: true     # ダミーモデル緊急停止
  max_model_failures: 3            # モデル失敗上限
  prediction_fallback_confidence: 0.0  # 予測失敗時フォールバック

# 取引関連動的設定（BTC価格1600万円対応）
trading:
  initial_balance_jpy: 10000.0      # 初期残高（1万円・個人運用統一）
  fallback_btc_jpy: 16000000.0      # フォールバック価格（現在相場対応）
  bid_spread_ratio: 0.999           # 0.1%スプレッド
  ask_spread_ratio: 1.001           # 0.1%スプレッド（上）
  
# 実行間隔制御（保守性向上）
execution:
  paper_mode_interval_seconds: 60   # ペーパートレード間隔
  live_mode_interval_seconds: 180   # ライブトレード間隔（収益性重視）

# 新規追加：監視・リスク管理・データ取得・ポジション管理（160項目統合）
monitoring:
  discord:
    timeout: 10                     # Discord通知タイムアウト
    confidence_thresholds:
      high: 0.8                     # 高信頼度閾値（緑色）
      medium: 0.6                   # 中信頼度閾値（黄色）
position_management:
  kelly_criterion:
    max_position_ratio: 0.03        # 最大ポジション比率3%
    safety_factor: 0.5              # 安全係数50%
  drawdown:
    default_balance: 10000.0        # デフォルト残高（1万円統一）
```

**8個ヘルパー関数で効率的アクセス**:
```python
from src.core.config import (
    get_threshold,           # 汎用閾値取得
    get_monitoring_config,   # 監視設定専用
    get_position_config,     # ポジション管理専用
    get_backtest_config,     # バックテスト設定専用
    get_data_config,         # データ関連設定専用
    get_execution_config,    # 実行設定専用
    get_ml_config,           # ML設定専用
    get_trading_config       # 取引設定専用
)

# ドット記法でのネストアクセス
confidence = get_monitoring_config("discord.confidence_thresholds.high", 0.8)
balance = get_position_config("drawdown.default_balance", 10000.0)
btc_price = get_trading_config("fallback_btc_jpy", 16000000.0)
```

### **12個厳選特徴量システム（Phase 19統一管理完成）**

**feature_manager.py統一管理**:
```python
# Phase 19特徴量統一管理システム
from src.core.config.feature_manager import FeatureManager

fm = FeatureManager()
print(f"特徴量数: {fm.get_feature_count()}")  # 12（統一管理）
print(f"特徴量一覧: {fm.get_feature_names()}")  # 12特徴量統一定義

# 整合性検証（Phase 19品質保証）
features = ["close", "volume", "returns_1", "rsi_14", "macd", 
           "macd_signal", "atr_14", "bb_position", "ema_20", 
           "ema_50", "zscore", "volume_ratio"]
assert fm.validate_features(features), "特徴量整合性エラー"
```

**feature_order.json（12特徴量統一定義）**:
```json
{
  "total_features": 12,
  "feature_categories": {
    "basic": ["close", "volume", "returns_1"],           // 3個
    "technical": ["rsi_14", "macd", "macd_signal", "atr_14", "bb_position", "ema_20", "ema_50"],  // 7個
    "anomaly": ["zscore", "volume_ratio"]  // 2個（market_stress削除）
  },
  "phase19_improvements": {
    "feature_manager_integration": true,
    "consistency_validation": true,
    "ml_model_alignment": true
  }
}
```

### **bitbank信用取引制約システム**

**個人開発最適化設定**:
```yaml
# bitbank信用取引制約（全設定ファイル統一）
exchange:
  name: bitbank
  symbol: "BTC/JPY"          # 信用取引専用通貨ペア
  leverage: 1.0              # 1倍（安全性最優先）
  
trading_constraints:
  trading_type: "margin"     # 信用取引専用
  leverage_max: 2.0          # 2倍レバレッジ上限（bitbank仕様）
  initial_capital: 10000     # 1万円スタート
  target_capital: 500000     # 最終目標50万円
```

## 📝 使用方法・例

### **基本的な設定利用（Phase 16-A対応）**

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

### **動的閾値の使用（Phase 16-B完成版）**
```python
from src.core.config import (
    get_threshold, get_monitoring_config, get_position_config, 
    get_trading_config, get_ml_config
)

# 基本的な閾値取得（160個統合対応）
confidence = get_threshold("ml.default_confidence", 0.5)
interval = get_threshold("execution.paper_mode_interval_seconds", 60)
balance = get_threshold("trading.initial_balance_jpy", 10000.0)

# ヘルパー関数による効率的アクセス（Phase 16-B新機能）
btc_price = get_trading_config("fallback_btc_jpy", 16000000.0)
discord_timeout = get_monitoring_config("discord.timeout", 10)
kelly_ratio = get_position_config("kelly_criterion.max_position_ratio", 0.03)
default_balance = get_position_config("drawdown.default_balance", 10000.0)

# ネストアクセス（ドット記法）
high_confidence = get_monitoring_config("discord.confidence_thresholds.high", 0.8)
safety_factor = get_position_config("kelly_criterion.safety_factor", 0.5)

# フォールバック制御（エラーハンドリング強化）
emergency_stop = get_ml_config("emergency_stop_on_dummy", True)
max_failures = get_ml_config("max_model_failures", 3)
if emergency_stop and model_type == "DummyModel":
    logger.critical("🚨 ダミーモデル検出により緊急停止")
    sys.exit(1)

# 1万円運用最適化設定（Phase 16-B現在相場対応）
initial_balance = get_trading_config("initial_balance_jpy", 10000.0)
current_btc_price = get_trading_config("fallback_btc_jpy", 16000000.0)  # 1600万円
logger.info(f"初期残高: ¥{initial_balance:,}, BTC現在価格: ¥{current_btc_price:,}")
```

### **CI/CDでの自動デプロイ（654テスト・MLOps完全対応）**
```bash
# GitHub Actions自動デプロイ（Phase 19品質保証・週次ML学習統合）
git push origin main  # 自動的に654テスト→品質ゲート→MODE=liveでデプロイ→週次学習

# デプロイ状況確認（設定一元化対応）
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1

# 設定統合確認（特徴量統一管理・MLOps品質確認）
python3 scripts/management/dev_check.py validate  # 654テスト・特徴量整合性・MLOps品質確認
```

### **設定の確認・検証（Phase 16-A対応）**
```python
from src.core.config import load_config

# 設定読み込み・確認
config = load_config('config/core/base.yaml')
print(f"モード: {config.mode}")  # paper（デフォルト）
print(f"信頼度閾値: {config.ml.confidence_threshold}")  # 0.65
# Phase 19特徴量統一管理確認
from src.core.config.feature_manager import FeatureManager
fm = FeatureManager()
print(f"特徴量数: {fm.get_feature_count()}")  # 12（feature_manager.py統一管理）
print(f"特徴量一覧: {fm.get_feature_names()}")  # 12特徴量統一定義
```

## ⚠️ 注意事項・制約

### **bitbank信用取引制約（Phase 16-A対応）**
- **通貨ペア**: BTC/JPY専用（bitbank信用取引対応）
- **レバレッジ**: 最大2倍（bitbank仕様）・実際1倍（安全性最優先）
- **資金管理**: 1万円→成功時50万円段階拡大（個人開発現実的）
- **取引時間**: 24時間・自動取引継続性確保

### **Phase 19対応事項**
- **654テスト**: 35テスト追加・100%成功・特徴量統一管理テスト対応・品質保証強化
- **59.24%カバレッジ**: 4.32%向上・企業級品質保証達成・継続監視・安定品質確保
- **特徴量統一管理**: feature_manager.py・12特徴量・整合性100%・ML互換性保証
- **MLOps基盤確立**: 週次自動学習・ProductionEnsemble・バージョン管理・品質検証

### **モード設定の重要事項**
- **デフォルト安全**: 未指定時は自動的に`mode: paper`（仮想取引）
- **本番運用注意**: `MODE=live`または`--mode live`指定時のみ実取引
- **設定優先順位**: コマンドライン > 環境変数 > YAMLファイル
- **確認必須**: 本番運用前の設定モード確認

### **セキュリティ制約（GCP統合）**
- **API認証情報**: YAMLファイルへの記載禁止
- **GCP Secret Manager**: bitbank API・Discord Webhook管理
- **Workload Identity**: GitHub Actions自動認証
- **設定分離**: 開発環境と本番環境の完全分離

### **運用制約（個人開発最適化）**
- **取引時間**: Bitbank営業時間内での運用
- **API制限**: 35秒間隔遵守・過度なリクエスト防止
- **リソース制限**: Cloud Run 1Gi メモリ・1 CPU制約考慮
- **コスト管理**: 月額約2000円・GCP料金・取引手数料監視

## 🔗 関連ファイル・依存関係

### **重要な外部依存**
- **`src/core/config.py`**: モード設定一元化システム・設定読み込み・thresholds.yaml対応
- **`main.py`**: エントリーポイント・モード制御・コマンドライン処理
- **`.github/workflows/ci.yml`**: CI/CDパイプライン・654テスト実行・品質ゲート統合
- **`.github/workflows/model-training.yml`**: 週次自動学習・MLOps統合・バージョン管理（Phase 19新規）
- **`scripts/management/dev_check.py`**: 設定検証・品質チェック

### **GCP連携（Phase 16-A統合）**
- **Secret Manager**: `bitbank-api-key`, `bitbank-api-secret`, `discord-webhook-url`
- **Cloud Run**: `crypto-bot-service-prod`本番サービス
- **Workload Identity**: GitHub Actions自動認証・最小権限
- **Cloud Logging**: 設定・デプロイログ監視

### **設定システム統合（Phase 16-A完成）**
- **config/core/base.yaml**: 全環境共通基本設定・デフォルト値
- **config/core/thresholds.yaml**: 動的閾値・運用時調整可能設定
- **config/production/**: bitbank信用取引本番運用設定
- **config/infrastructure/**: GCPインフラ・CI/CD設定

### **品質保証システム（Phase 19企業級基準）**
- **654テスト**: 35テスト追加・統合テスト強化・特徴量統一管理・MLOps品質保証対応
- **59.24%カバレッジ**: 4.32%向上・企業級品質保証継続・継続監視・安定品質確保
- **特徴量品質**: feature_manager.py・12特徴量統一・整合性100%・ML互換性保証
- **MLOps品質統合**: 週次自動学習・ProductionEnsemble・バージョン管理・品質検証

## 📊 Phase 19設定一元化・品質保証完了成果

### **特徴量統一管理・MLOps達成結果**
- **特徴量統一管理完成**: feature_manager.py・12特徴量一元化・整合性100%保証
- **MLOps基盤確立**: 週次自動学習・ProductionEnsemble・バージョン管理・品質検証
- **654テスト品質向上**: 35テスト追加・100%成功・59.24%カバレッジ達成
- **GCPクリーンアップ**: 30%コスト削減・リソース最適化・運用効率化・企業級品質

### **個人運用最適化完成**
- **1万円運用統一**: 初期残高・デフォルト残高・段階拡大設定統合
- **bitbank制約準拠**: 信用取引・BTC/JPY専用・現在相場1600万円対応
- **コスト効率**: 月額約2000円・1Gi メモリ・1 CPU・効率運用
- **安全性重視**: paper デフォルト・live 慎重移行・リスク管理統合

### **企業級品質保証完成（Phase 19達成）**
- **654テスト**: 35テスト追加・100%合格維持・特徴量統一管理・MLOps品質保証達成
- **59.24%カバレッジ**: 4.32%向上・企業級品質保証達成・継続監視・安定品質確保
- **MLOps統合**: 週次自動学習・ProductionEnsemble・バージョン管理・品質検証統合
- **継続的品質改善**: 特徴量品質監視・モデル品質保証・運用効率化・企業級基準達成

---

---

**🎯 Phase 19完了・企業級品質達成**: 特徴量定義一元化・バージョン管理システム改良・MLOps基盤確立により、654テスト100%成功・59.24%カバレッジ達成・12特徴量統一管理・週次自動学習を実現した継続的品質改善システムが完全稼働**

## 🚀 Phase 19完了記録・設定管理品質達成

**完了日時**: 2025年9月4日（Phase 19企業級品質達成）  
**Phase 19設定管理品質達成**: 
- ✅ **654テスト100%成功** (35テスト追加・設定管理品質保証・回帰防止完備)
- ✅ **59.24%カバレッジ達成** (54.92%→59.24%・4.32%向上・企業級品質)
- ✅ **特徴量統一管理** (feature_manager.py・12特徴量・整合性100%・設定連携)
- ✅ **MLOps設定統合** (週次自動学習・ProductionEnsemble・バージョン管理統合)
- ✅ **GCP設定最適化** (30%コスト削減・クリーンアップ・リソース効率化)

**継続設定管理体制**:
- 🎯 **企業級設定品質**: 59.24%カバレッジ・654テスト・設定品質劣化防止
- 🤖 **特徴量設定統合**: 12特徴量統一管理・整合性監視・設定安全保証
- 📊 **MLOps設定統合**: 週次学習設定・バージョン管理・設定品質検証
- 🔧 **継続設定改善**: カバレッジ向上・テスト拡張・設定管理基盤強化

**重要**: Phase 19完了により、特徴量統一管理・MLOps基盤・企業級品質保証が確立されました。設定管理システムは12特徴量統一管理・週次自動学習・継続的品質改善により、シンプルで安全・効率的・企業級品質の環境制御を提供し、ペーパートレードから本番運用まで一貫した高品質設定体験を実現しています。