# config/ - 設定管理ディレクトリ

## 🎯 役割・責任

システム全体の設定を一元管理し、開発環境から本番運用まで環境別に適切な設定を提供します。取引所接続、機械学習、戦略、リスク管理、インフラなどの設定を階層的に管理し、システム全体の一貫性を保証します。

## 📁 ディレクトリ構成

```
config/
├── README.md                          # このファイル
│
├── core/                              # システム基本設定
│   ├── README.md                      # コア設定ガイド
│   ├── base.yaml                      # 基本設定（モード、取引所、ML、リスク管理など）
│   ├── feature_order.json             # 特徴量定義（12特徴量統一管理）
│   └── thresholds.yaml                # 動的閾値設定
│
├── production/                        # 本番運用設定
│   ├── README.md                      # 本番運用ガイド
│   └── production.yaml                # 本番環境固有設定
│
├── infrastructure/                    # インフラ設定
│   ├── README.md                      # インフラガイド
│   ├── gcp_config.yaml                # GCP関連設定
│   └── cloudbuild.yaml                # Cloud Build設定
│
├── backtest/                          # バックテスト設定
│   ├── README.md                      # バックテストガイド
│   ├── base.yaml                      # バックテスト用基本設定
│   ├── feature_order.json             # バックテスト用特徴量定義
│   └── thresholds.yaml                # バックテスト用閾値設定
│
└── secrets/                           # 機密情報（.gitignoreで除外）
    ├── README.md                      # 機密設定ガイド
    ├── discord_webhook.txt            # Discord Webhook URL
    ├── .env                           # 環境変数（機密情報）
    └── .env.example                   # 環境変数テンプレート
```

## 📋 各ディレクトリの役割

### **core/**
システムの基本設定を管理します。
- `base.yaml`: 動作モード、取引所設定、ML設定、リスク管理設定など
- `feature_order.json`: 特徴量定義（12特徴量統一管理）
- `thresholds.yaml`: 動的閾値設定（信頼度レベル、戦略設定など）

### **production/**
本番環境固有の設定を管理します。
- 本番運用時のオーバーライド設定
- 実際の資金での取引に関する設定

### **infrastructure/**
GCPなどのインフラ関連設定を管理します。
- Cloud Run、Cloud Build、Secret Manager設定
- CI/CDパイプライン設定

### **backtest/**
バックテスト実行時に本番設定を変更せずに独立した環境を提供します。
- core/設定のコピーをベースにしたバックテスト専用設定

### **secrets/**
機密情報を管理します（.gitignoreで除外）。
- Discord Webhook URL、API キーなど
- 環境変数設定

## 📝 使用方法・例

### **基本設定の変更**
```bash
# ペーパートレード（デフォルト）
python3 main.py --mode paper

# ライブトレード
python3 main.py --mode live
```

### **設定値の取得**
```python
from src.core.config import get_threshold, get_ml_config, get_trading_config

# 基本的な設定値取得
confidence = get_threshold("ml.confidence_threshold", 0.65)
balance = get_trading_config("default_balance_jpy", 10000.0)

# 特徴量管理
from src.core.config.feature_manager import FeatureManager
fm = FeatureManager()
feature_names = fm.get_feature_names()  # 12特徴量一覧
feature_count = fm.get_feature_count()  # 12
```

### **機密情報設定**
```bash
# secretsディレクトリ作成
mkdir -p config/secrets

# Discord Webhook URL設定
echo "https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN" > config/secrets/discord_webhook.txt
```

## ⚠️ 注意事項・制約

### **設定変更時の注意**
- **core/base.yaml**: システムの基本動作に影響するため慎重に変更
- **feature_order.json**: 特徴量の順序変更は予測性能に影響
- **thresholds.yaml**: 閾値変更は取引頻度・リスクに大きく影響

### **環境分離**
- production/設定は本番環境でのみ使用
- backtest/設定は本番設定を変更せずにテスト実行
- 設定ファイル間の整合性を保つ

### **機密情報管理**
- `config/secrets/`は`.gitignore`で除外済み
- API キーやWebhook URLは絶対にコミットしない
- 環境変数も適切に管理する

## 🔗 関連ファイル・依存関係

### **設定読み込みシステム**
- `src/core/config.py`: 設定ファイル読み込みとアクセス機能
- `src/core/config/feature_manager.py`: 特徴量管理
- `src/core/config/threshold_manager.py`: 閾値管理

### **設定利用システム**
- `src/core/orchestration/orchestrator.py`: システム統合制御
- `main.py`: エントリーポイント、コマンドライン引数処理
- `src/strategies/`: 各取引戦略
- `src/ml/`: 機械学習システム

### **インフラ連携**
- `.github/workflows/`: CI/CDパイプライン
- `.gitignore`: 機密情報保護設定

