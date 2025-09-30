# config/ - 設定管理ディレクトリ（Phase 28完了・Phase 29最適化版）

**最終更新**: 2025年9月28日 - Phase 28完了・Phase 29最適化版
**テスト品質**: 625テスト・64.74%カバレッジ

## 🎯 役割・責任

システム全体の設定を一元管理し、開発環境から本番運用まで環境別に適切な設定を提供します。取引所接続、機械学習、戦略、リスク管理、インフラなどの設定を階層的に管理し、システム全体の一貫性を保証します。

## 📁 ディレクトリ構成

```
config/
├── README.md                   # このファイル（Phase 29最適化版）
│
├── core/                      # システム基本設定（Phase 29最適化完了）
│   ├── README.md              # コア設定ガイド（設定重複解消詳細）
│   ├── unified.yaml           # 統一設定ファイル（システム全体・重複削除済み）
│   ├── thresholds.yaml        # 動的閾値設定（ML信頼度・Kelly基準統合）
│   └── feature_order.json     # 15特徴量順序定義（v2.3.0・Phase 29対応）
│
├── infrastructure/            # インフラ設定（統一設定管理体系対応）
│   ├── README.md              # インフラガイド（v23.0.0・CI/CD統一版）
│   └── gcp_config.yaml        # GCP統合設定（v29.0.0・Secret Manager具体バージョン）
│
└── secrets/                   # 機密情報（.gitignoreで除外・Phase 29対応）
    ├── README.md              # 機密設定ガイド（Phase 29マーカー追加）
    ├── .env.example           # 環境変数テンプレート（Phase 29最適化版）
    ├── discord_webhook.txt    # Discord Webhook URL
    └── .env                   # 環境変数（機密情報）
```

## 📋 各ディレクトリの役割（Phase 29最適化版）

### **core/**（Phase 29設定重複解消完了）
システムの基本設定を統一管理します。
- `unified.yaml`: システム全体設定（アンサンブル重み・基本動作・重複削除済み）
- `thresholds.yaml`: 動的閾値設定（ML信頼度0.3・Kelly基準・TP/SL設定統合）
- `feature_order.json`: 15特徴量順序定義（v2.3.0・ATR/MochiPoy/MTF/Donchian/ADX対応）

### **infrastructure/**（統一設定管理体系確立）
GCP統合インフラ設定を管理します。
- `gcp_config.yaml`: GCP統合設定（v29.0.0・Secret Manager具体バージョン・GitHub Actions統一）
- Cloud Run、Artifact Registry、Secret Manager統合管理
- CI/CD統一設定（GitHub Actions完全統一・Cloud Build廃止）

### **secrets/**（機密情報Phase 29対応）
機密情報を安全管理します（.gitignoreで完全除外）。
- Discord Webhook URL、Bitbank APIキー統合管理
- 環境変数設定（Phase 29最適化テンプレート）
- ローカル優先・GCP Secret Manager連携

## 🚀 Phase 29最適化成果

### **設定重複完全解消**
- **unified.yaml と thresholds.yaml の責任分離**：ML信頼度・Kelly基準・アンサンブル重み設定の重複を完全解消
- **視覚的理解向上**：日本語セクションヘッダーによる構造化・理解しやすい設定構成
- **統一設定管理体系**：全設定ファイルPhase 29マーカー統一・一貫性確保

### **テスト品質向上**
- **625テスト100%成功**：58.64% → 64.74%カバレッジ向上・品質基準強化
- **15特徴量統一システム**：ATR・MochiPoy・MultiTimeframe・DonchianChannel・ADX戦略統合
- **ProductionEnsemble**：LightGBM 50%・XGBoost 30%・RandomForest 20%重み最適化

## 📝 使用方法・例（Phase 29最適化版）

### **基本システム実行**
```bash
# 品質チェック（開発必須）
bash scripts/testing/checks.sh                    # 625テスト・64.74%カバレッジ確認

# システム実行（Phase 29最適化設定）
python3 main.py --mode paper    # ペーパートレード（デフォルト）
python3 main.py --mode live     # ライブトレード（本番運用）
```

### **Phase 29最適化設定の活用**
```python
from src.core.config import get_threshold, get_ml_config, get_trading_config

# Phase 29最適化設定値取得
confidence = get_threshold("ml.confidence_threshold", 0.3)  # thresholds.yaml統合
kelly_min_trades = get_threshold("trading.kelly_criterion.min_trades", 5)  # 実用性向上

# 15特徴量統一システム
from src.core.config.feature_manager import FeatureManager
fm = FeatureManager()
feature_names = fm.get_feature_names()  # 15特徴量一覧（ATR/MochiPoy/MTF/Donchian/ADX）
feature_count = fm.get_feature_count()  # 15

# アンサンブル重み（unified.yaml統一）
weights = get_ml_config("ensemble.weights")  # LightGBM 50%, XGBoost 30%, RandomForest 20%
```

### **機密情報設定**
```bash
# secretsディレクトリ作成
mkdir -p config/secrets

# Discord Webhook URL設定
echo "https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN" > config/secrets/discord_webhook.txt
```

## ⚠️ 注意事項・制約（Phase 29最適化版）

### **Phase 29最適化設定の制約**
- **unified.yaml**: システム全体設定・重複削除により変更時は慎重に
- **thresholds.yaml**: ML信頼度・Kelly基準統合設定・取引頻度に直接影響
- **feature_order.json**: 15特徴量順序変更は予測性能に重大影響
- **設定分離原則**: 各ファイルの責任範囲を維持・重複を避ける

### **統一設定管理体系の制約**
- **Phase 29マーカー**: 全設定ファイルでバージョン統一必須
- **テスト品質基準**: 625テスト100%成功・64.74%カバレッジ維持必須
- **CI/CD統合**: GitHub Actions統一・設定変更時は自動テスト通過必須

### **機密情報管理（Phase 29対応）**
- **config/secrets/**：`.gitignore`完全除外・Phase 29テンプレート使用
- **Secret Manager具体バージョン**: `:latest`禁止・具体的バージョン（:3,:5）使用
- **ローカル優先設定**: GCP Secret Manager依存解消・開発効率向上

## 🔗 関連ファイル・依存関係（Phase 29最適化版）

### **Phase 29統一設定管理システム**
- `src/core/config.py`: 設定ファイル統一読み込み・重複解消対応
- `src/core/config/feature_manager.py`: 15特徴量統一管理（v2.3.0対応）
- `src/core/config/threshold_manager.py`: 動的閾値管理（ML信頼度・Kelly基準統合）

### **Phase 29対応システム統合**
- `src/core/orchestration/orchestrator.py`: システム統合制御（ExecutionService統合・Silent Failure解決）
- `main.py`: エントリーポイント（625テスト品質ゲート・Phase 29設定）
- `src/strategies/`: 5戦略統合（ATR・MochiPoy・MTF・Donchian・ADX）
- `src/ml/`: ProductionEnsemble（LightGBM・XGBoost・RandomForest重み最適化）

### **統一設定管理体系インフラ**
- `.github/workflows/`: CI/CD統一パイプライン（GitHub Actions完全統一・Cloud Build廃止）
- `config/infrastructure/gcp_config.yaml`: GCP統合設定（v29.0.0・Secret Manager具体バージョン）
- `.gitignore`: 機密情報完全保護・Phase 29テンプレート対応

## 🎯 Phase 29最適化まとめ

**設定重複完全解消・視覚的理解向上・統一設定管理体系確立により、AI自動取引システムの設定管理が企業級品質に到達しました。625テスト100%成功・64.74%カバレッジ・15特徴量統一システム・5戦略統合・ProductionEnsemble最適化により、24時間安定稼働の基盤が完成しています。** 🚀

