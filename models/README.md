# models/ - モデル管理・昇格システム

## 📋 概要

**Model Management & Promotion System**  
本フォルダは crypto-bot の機械学習モデル管理を担当し、開発→検証→本番への昇格ワークフローを提供します。

**🎊 Phase 16.12更新**: 2025年8月8日  
**最終更新**: 2025年8月10日 - アンサンブルモデル強化・CI/CDテスト対応  
**管理体制**: 97特徴量システム・TradingEnsembleClassifier・3モデル統合(LGBM+XGB+RF)

## 📁 ディレクトリ構造

```
models/                                 # Phase 16.12現在（24ファイル）
├── README.md                           # 本ドキュメント
│
├── ✅ production/ - 本番稼働モデル（5ファイル）
│   ├── model.pkl                       # TradingEnsembleClassifier本番モデル（3モデル統合）
│   ├── model_metadata.json            # 本番モデルメタデータ
│   ├── model.pkl.backup_*             # 各種バックアップ（自動生成）
│   └── create_production_model.py使用  # CI/CDでの自動生成対応
│
├── ✅ training/ - 訓練済み個別モデル（7ファイル）
│   ├── lgbm_97_features.pkl           # LightGBM 97特徴量モデル
│   ├── lgbm_97_features_metadata.json # LightGBMメタデータ
│   ├── xgb_97_features.pkl            # XGBoost 97特徴量モデル
│   ├── xgb_97_features_metadata.json  # XGBoostメタデータ  
│   ├── rf_97_features.pkl             # RandomForest 97特徴量モデル
│   ├── rf_97_features_metadata.json   # RandomForestメタデータ
│   ├── model_trading_ensemble.pkl     # TradingEnsemble統合モデル
│   └── ensemble_97_features_metadata.json # アンサンブルメタデータ
│
├── ✅ validation/ - 検証・バックテストモデル（15ファイル）  
│   ├── lgbm_97_features.pkl           # LightGBM検証用
│   ├── xgb_97_features.pkl            # XGBoost検証用
│   ├── rf_97_features.pkl             # RandomForest検証用
│   ├── ensemble_97_features.pkl       # アンサンブル検証用
│   ├── *_metadata.json                # 各種性能メタデータ
│   ├── feature_names.json             # 97特徴量定義
│   ├── optimal_features.json          # 最適特徴量セット
│   └── optimal_model_performance.json # 最適性能記録
│
└── development/ - 開発用（空・将来拡張用）
```

## 🔍 各ディレクトリの役割

### **production/ - 本番稼働モデル**
- **model.pkl**: TradingEnsembleClassifier（LGBM + XGBoost + RandomForest統合）
- **model_metadata.json**: 97特徴量対応・性能指標・設定情報
- **Docker内パス**: `/app/models/production/model.pkl`
- **現在の状況**: Phase 16本番稼働中・Bitbank BTC/JPY取引実行

### **training/ - 訓練済み個別モデル**
- **個別モデル**: lgbm/xgb/rf の97特徴量対応モデル
- **アンサンブルモデル**: TradingEnsembleClassifier統合版
- **メタデータ**: 各モデルの訓練詳細・性能指標・パラメータ
- **用途**: 新モデル訓練・性能比較・アンサンブル構成要素

### **validation/ - 検証・実験モデル**
- **検証モデル**: 各種バックテスト・性能検証用モデル
- **特徴量定義**: feature_names.json（97特徴量完全定義）
- **最適化結果**: optimal_features.json・optimal_model_performance.json
- **メタデータ**: 詳細な性能分析・設定バリエーション
- **用途**: モデル昇格前検証・A/Bテスト・性能ベンチマーク

### **development/ - 開発実験用**
- **現在**: 空フォルダ（将来の開発実験用として予約）
- **用途**: ローカル実験・プロトタイプ・一時的なテストモデル

## 🚀 使用方法

### **本番デプロイ**
```bash
# Phase 16.12対応本番環境
python -m crypto_bot.main live-bitbank \
    --config config/production/production.yml
    # 自動的に models/production/model.pkl を読み込み
```

### **個別モデル検証**
```bash  
# LightGBMモデル個別テスト
python -m crypto_bot.main backtest \
    --config config/validation/lgbm_97_features_test.yml \
    --model models/training/lgbm_97_features.pkl
```

### **アンサンブルモデル検証**
```bash
# TradingEnsembleClassifier統合テスト
python -m crypto_bot.main backtest \
    --config config/validation/ensemble_97_features_test.yml \
    --model models/validation/ensemble_97_features.pkl
```

## 📋 モデル昇格ワークフロー（Phase 16.12対応）

### **Stage 1: 個別モデル訓練**
```bash
# 97特徴量システムで個別モデル訓練
python scripts/retrain_97_features_model.py
# 出力: models/training/lgbm_97_features.pkl
#       models/training/xgb_97_features.pkl  
#       models/training/rf_97_features.pkl
```

### **Stage 2: アンサンブル統合**
```bash
# TradingEnsembleClassifierによる統合（3モデル統合）
python scripts/create_proper_ensemble_model.py
# 出力: models/production/model.pkl
# 内容: LGBM + XGBoost + RandomForest の trading_stacking 統合

# CI/CD環境用モデル作成
python scripts/create_production_model.py
# DataFrame対応・confidence_threshold=0.35
# フォールバック対応（simple_fallback）
```

### **Stage 3: 検証・バックテスト**
```bash
# validation/で性能検証・バックテスト実行
python -m crypto_bot.main backtest \
    --config config/validation/ensemble_97_features_test.yml \
    --model models/training/model_trading_ensemble.pkl

# 優秀な結果が出た場合、validation/にコピー
cp models/training/model_trading_ensemble.pkl models/validation/ensemble_97_features.pkl
```

### **Stage 4: 本番昇格（慎重実行）**
```bash
# 現在の本番モデルをバックアップ
cp models/production/model.pkl models/production/model_backup_$(date +%Y%m%d).pkl

# 検証済みモデルを本番に昇格  
cp models/validation/ensemble_97_features.pkl models/production/model.pkl

# メタデータも更新
cp models/validation/ensemble_97_features_metadata.json models/production/model_metadata.json
```

### **Stage 5: 本番デプロイ**
```bash
# Phase 16対応本番デプロイ
gcloud run deploy crypto-bot-service-prod \
    --source . --region=asia-northeast1
    
# 動作確認
curl https://crypto-bot-service-prod-11445303925.asia-northeast1.run.app/health
```

## ⚠️ 重要な管理原則

### **固定ファイル名原則**
- **本番モデル**: 常に`models/production/model.pkl`（固定名）
- **Docker環境**: `/app/models/production/model.pkl`で参照
- **複数バージョン管理禁止**: 混乱防止のため本番は単一ファイル

### **バックアップ管理**
- **更新前必須**: 本番モデル更新前に必ずバックアップ作成
- **命名規則**: `model_backup_YYYYMMDD.pkl`
- **保管場所**: `models/production/`内にバックアップ保管

### **Phase 16.12品質保証**
- **97特徴量対応**: 全モデルが97特徴量システム対応済み
- **TradingEnsembleClassifier**: 統合学習方式で予測精度向上
- **本番稼働確認**: Bitbank BTC/JPY で実際に取引実行中

### **Cloud Storage統合**
```bash
# 必要時にCloud Storageから本番モデルダウンロード
gsutil cp gs://my-crypto-bot-models/model.pkl models/production/model.pkl

# Cloud Storageへのバックアップアップロード
gsutil cp models/production/model_backup_$(date +%Y%m%d).pkl gs://my-crypto-bot-models/backups/
```

## 📊 現在のモデル体制（Phase 16.12）

### **本番稼働モデル（2025年8月10日更新）**
- **TradingEnsembleClassifier**: LGBM + XGBoost + RandomForest 3モデル統合
- **統合方式**: trading_stacking メソッド（高度な予測統合）
- **97特徴量完全対応**: 100%実装率・フォールバック削減
- **confidence_threshold**: 0.35（production.yml準拠）
- **CI/CD対応**: create_production_model.py でのフォールバック生成対応
- **稼働状況**: Phase 18本番環境・Bitbank BTC/JPY実取引中

### **訓練済みモデル群**
- **個別モデル性能**: LGBM(47.02%) / XGBoost(48.20%) / RandomForest(47.84%)
- **アンサンブル効果**: trading_stacking方式による精度向上
- **完全メタデータ**: 訓練詳細・性能指標・パラメータ完備

### **継続改善体制**
- **定期再訓練**: 週次・月次でのモデル性能評価
- **A/Bテスト**: validation/での新モデル検証
- **段階的昇格**: 安全な本番モデル更新プロセス

---

**Phase 16.12完了**: 97特徴量システム・TradingEnsembleClassifier・本番稼働体制が完全に整備されたモデル管理システムが確立されました。🎊