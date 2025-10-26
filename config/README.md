# config/ - 設定管理ディレクトリ（Phase 49完了時点）

**最終更新**: 2025年10月22日 - Phase 49完了
**テスト品質**: 1,117テスト・68.32%カバレッジ・55特徴量

## 🎯 役割・責任

システム全体の設定を一元管理し、開発環境から本番運用まで環境別に適切な設定を提供します。取引所接続、機械学習、戦略、リスク管理、インフラなどの設定を階層的に管理し、システム全体の一貫性を保証します。

## 📁 ディレクトリ構成

```
config/
├── README.md                   # このファイル（Phase 49完了版）
│
├── core/                      # システム基本設定（Phase 49完了）
│   ├── README.md              # コア設定ガイド（実践的実装ガイド）
│   ├── unified.yaml           # 統一設定ファイル（システム全体・55特徴量対応）
│   ├── thresholds.yaml        # 動的閾値設定（TP/SL・ML統合・79パラメータ）
│   └── feature_order.json     # 55特徴量順序定義（v2.5.0・Strategy-Aware ML対応）
│
├── infrastructure/            # GCPインフラ設定（Cloud Run・Secret Manager）
│   ├── README.md              # 実践的GCP運用ガイド（gcloudコマンド集）
│   └── gcp_config.yaml        # GCP統合設定（Workload Identity・Secret Manager）
│
├── secrets/                   # 機密情報（.gitignoreで完全除外）
│   ├── README.md              # 機密情報管理ガイド
│   ├── .env.example           # 環境変数テンプレート
│   ├── discord_webhook.txt    # Discord Webhook URL
│   └── .env                   # 環境変数（機密情報）
│
└── optimization/              # Optuna最適化結果管理（Phase 40実装）
    ├── README.md              # 最適化結果使用ガイド（79パラメータ）
    ├── results/               # Phase 40最適化結果（JSON形式）
    ├── checkpoints/           # 最適化チェックポイント（.gitignore対象）
    └── .checkpoint.json       # 実行状態管理
```

## 📋 各ディレクトリの役割（Phase 49完了版）

### **core/**（システム基本設定）
システムの基本設定を統一管理します。
- `unified.yaml`: システム全体設定（55特徴量・5戦略・3モデルアンサンブル）
- `thresholds.yaml`: 動的閾値設定（TP/SL・ML統合・79パラメータ最適化対応）
- `feature_order.json`: 55特徴量順序定義（50基本+5戦略信号・Strategy-Aware ML対応）

### **infrastructure/**（GCPインフラ設定）
GCP本番環境の設定を管理します。
- `gcp_config.yaml`: Cloud Run・Secret Manager・Workload Identity設定
- 実践的GCP運用ガイド（gcloudコマンド集・トラブルシューティング）

### **secrets/**（機密情報管理）
機密情報を安全管理します（.gitignoreで完全除外）。
- Discord Webhook URL・Bitbank APIキー管理
- 環境変数設定テンプレート
- ローカル開発優先・GCP Secret Manager連携

### **optimization/**（Optuna最適化結果）
Phase 40で実装された79パラメータ最適化結果を管理します。
- 4フェーズ最適化結果（リスク12・戦略30・ML統合7・MLハイパー30）
- チェックポイント管理（中断・再開対応）
- thresholds.yaml統合デプロイ機能

## 📝 使用方法（Phase 49完了版）

### **品質チェック（開発必須）**
```bash
# Phase 49品質基準: 1,117テスト・68.32%カバレッジ
bash scripts/testing/checks.sh
```

### **設定ファイル編集**
```bash
# TP/SL設定変更（デイトレード特化: SL 1.5% / TP 2%）
vim config/core/thresholds.yaml

# ML統合閾値調整（3段階統合ロジック: 0.45/0.60）
vim config/core/thresholds.yaml

# 特徴量確認（55特徴量: 50基本+5戦略信号）
cat config/core/feature_order.json | jq '.total_features'
```

### **Optuna最適化実行**
```bash
# 79パラメータ最適化実行（Phase 40実装）
python3 scripts/optimization/run_phase40_optimization.py

# 最適化結果確認
cat config/optimization/results/phase40_1_risk_management.json | jq '.best_value'

# thresholds.yaml統合デプロイ
python3 scripts/optimization/integrate_and_deploy.py --dry-run
```

## ⚠️ 注意事項・制約（Phase 49完了版）

### **設定ファイル変更時の注意**
- **feature_order.json**: 55特徴量順序変更は予測性能に重大影響・慎重に変更
- **thresholds.yaml**: TP/SL・ML統合設定変更は取引頻度・リスク管理に直接影響
- **unified.yaml**: システム全体構造設定・変更時は影響範囲を十分確認

### **品質基準維持**
- **テスト品質**: 1,117テスト100%成功・68.32%カバレッジ維持必須
- **開発フロー**: 設定変更後は`bash scripts/testing/checks.sh`で品質確認
- **CI/CD**: GitHub Actions自動テスト通過必須

### **機密情報管理**
- **config/secrets/**: `.gitignore`完全除外・絶対にコミットしない
- **Secret Manager**: `:latest`禁止・具体的バージョン（:3, :5）使用
- **環境変数**: `.env.example`をコピーして`.env`作成・値を設定

## 🔗 関連ファイル・依存関係（Phase 49完了版）

### **設定読み込みシステム**
- `src/core/config.py`: 設定ファイル統一読み込み（unified.yaml・thresholds.yaml統合）
- `src/core/config/feature_manager.py`: 55特徴量管理（feature_order.json単一参照）
- `src/core/config/threshold_manager.py`: 動的閾値管理（TP/SL・ML統合・79パラメータ）

### **システム統合**
- `src/core/orchestration/orchestrator.py`: システム統合制御（TradingOrchestrator）
- `src/strategies/`: 5戦略統合（ATR・MochiPoy・MultiTimeframe・Donchian・ADX）
- `src/ml/`: ProductionEnsemble（3モデルアンサンブル・55特徴量Strategy-Aware ML）
- `tax/`: 確定申告システム（Phase 47実装・移動平均法損益計算）

### **最適化・運用システム**
- `scripts/optimization/`: Optuna最適化スクリプト（Phase 40実装・79パラメータ）
- `scripts/reports/weekly_report.py`: 週間レポート生成（Phase 48実装・Discord通知）
- `.github/workflows/`: CI/CD統合パイプライン（品質ゲート・週次レポート）
- `.gitignore`: 機密情報完全保護（config/secrets/完全除外）

## 🎯 Phase 49完了まとめ

**Phase 49完了時点の設定管理システム**: 1,117テスト100%成功・68.32%カバレッジ・55特徴量Strategy-Aware ML・79パラメータOptuna最適化・TP/SL設定最適化（SL 1.5%/TP 2%）・統合TP/SL実装（注文数91.7%削減）・トレーリングストップ・確定申告対応・週間レポート自動化により、企業級品質のAI自動取引システムが24時間安定稼働中 🚀

