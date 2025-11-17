# config/ - 設定管理ディレクトリ

**Phase 52.4**

**最終更新**: 2025年11月15日

## 🎯 役割・責任

システム全体の設定を一元管理します。取引所接続、機械学習、戦略、リスク管理、インフラなどの設定を階層的に管理し、開発環境から本番運用まで環境別に適切な設定を提供します。

## 📁 ディレクトリ構成

```
config/
├── README.md                   # このファイル
│
├── core/                       # システム基本設定
│   ├── README.md               # コア設定ガイド
│   ├── unified.yaml            # 統一設定ファイル（基本設定）
│   ├── thresholds.yaml         # 動的閾値設定（ML統合・リスク管理）
│   ├── features.yaml           # 機能オンオフ設定
│   ├── strategies.yaml         # 戦略定義（動的戦略管理）
│   └── feature_order.json      # 特徴量順序定義（Strategy-Aware ML）
│
├── infrastructure/             # GCPインフラ設定
│   ├── README.md               # GCP運用ガイド
│   ├── gcp_config.yaml         # GCP統合設定
│   └── iam_policy_backup.json  # IAM権限バックアップ
│
└── secrets/                    # 機密情報（.gitignore除外）
    ├── README.md               # 機密情報管理ガイド
    ├── .env.example            # 環境変数テンプレート
    └── .env                    # 環境変数（機密情報）
```

## 📋 各ディレクトリの役割

### **core/** - システム基本設定

システムのcore設定を統一管理します。

- `unified.yaml`: システム全体基本設定
- `thresholds.yaml`: 動的閾値設定（ML統合・リスク管理・Optuna最適化結果）
- `features.yaml`: 機能オンオフ設定
- `strategies.yaml`: 戦略定義（動的戦略管理）
- `feature_order.json`: 特徴量順序定義（Strategy-Aware ML）

**注**: 特徴量数・戦略数はそれぞれfeature_order.json・strategies.yamlを参照

### **infrastructure/** - GCPインフラ設定

GCP本番環境の設定を管理します。

- `gcp_config.yaml`: Cloud Run・Secret Manager・Workload Identity設定
- `iam_policy_backup.json`: IAM権限バックアップ（災害復旧用）
- 実践的GCP運用ガイド（gcloudコマンド集・トラブルシューティング）

### **secrets/** - 機密情報管理

機密情報を安全管理します（.gitignoreで完全除外）。

- ローカル開発: `.env`ファイル使用
- 本番環境: GCP Secret Manager使用（具体的バージョン指定必須）
- 環境変数設定テンプレート（`.env.example`）

## 📝 使用方法

### **品質チェック（開発必須）**
```bash
# 全テスト実行・品質基準確認
bash scripts/testing/checks.sh
```

### **設定ファイル編集**
```bash
# TP/SL設定変更
vim config/core/thresholds.yaml

# ML統合閾値調整
vim config/core/thresholds.yaml

# 特徴量確認
cat config/core/feature_order.json | jq '.total_features'

# 戦略確認
cat config/core/strategies.yaml | grep "enabled: true" -B 1
```

## ⚠️ 注意事項・制約

### **設定ファイル変更時の注意**
- **feature_order.json**: 特徴量順序変更は予測性能に重大影響
- **thresholds.yaml**: TP/SL・ML統合設定変更は取引頻度・リスク管理に直接影響
- **strategies.yaml**: 戦略有効化・重み変更は取引判断に直接影響
- **unified.yaml**: システム全体構造設定・影響範囲を十分確認

### **品質基準維持**
- **開発フロー**: 設定変更後は`bash scripts/testing/checks.sh`で品質確認必須
- **CI/CD**: GitHub Actions自動テスト通過必須

### **機密情報管理**
- **config/secrets/**: `.gitignore`完全除外・絶対にコミットしない
- **Secret Manager**: `:latest`禁止・具体的バージョン使用（例: `bitbank-api-key:3`）
- **環境変数**: `.env.example`をコピーして`.env`作成・値を設定

## 🔗 関連ファイル・依存関係

### **設定読み込みシステム**
- `src/core/config.py`: 設定ファイル統一読み込み
- `src/core/config/feature_manager.py`: 特徴量管理（feature_order.json参照）
- `src/core/config/threshold_manager.py`: 動的閾値管理（thresholds.yaml参照）

### **システム統合**
- `src/core/orchestration/orchestrator.py`: システム統合制御（TradingOrchestrator）
- `src/strategies/`: 戦略統合（strategies.yaml動的ロード）
- `src/ml/`: ProductionEnsemble（アンサンブルモデル・Strategy-Aware ML）
- `tax/`: 確定申告システム（移動平均法損益計算）

### **運用システム**
- `scripts/reports/weekly_report.py`: 週間レポート生成（Discord通知）
- `.github/workflows/`: CI/CD統合パイプライン（品質ゲート）
- `.gitignore`: 機密情報完全保護（config/secrets/完全除外）

---

**最終更新**: Phase 52.4完了（2025年11月15日）

