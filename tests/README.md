# tests/ - Phase 19 MLOps統合テスト・品質保証システム

**Phase 19対応**: 654テスト・59.24%カバレッジ・MLOps統合・週次学習・Cloud Run 24時間稼働（2025年9月4日現在）

## 🎯 役割・責任

Phase 19 MLOps統合テスト・品質保証システムとして以下を提供：
- **MLOps統合テスト**: 654テスト・feature_manager 12特徴量・ProductionEnsemble 3モデル統合
- **週次学習テスト**: GitHub Actions統合・自動モデルテスト・Cloud Runデプロイ検証
- **品質保証**: 59.24%カバレッジ・MLOps品質管理・CI/CD統合・段階的デプロイ
- **回帰防止**: 24時間稼働監視・Discord 3階層通知・MLOps自動テスト

## 📂 ファイル構成

```
tests/
├── manual/              # Phase 19手動テスト・MLOps統合検証
│   ├── test_phase2_components.py    # Phase 19コンポーネント検証（7テスト・MLOps対応）
│   ├── manual_bitbank_client.py     # Bitbank APIマニュアルテスト
│   └── README.md                    # Phase 19手動テスト詳細
├── unit/                # Phase 19単体テスト（654テスト・59.24%カバレッジ）
│   ├── strategies/      # 4戦略統合テスト（feature_manager連携）
│   ├── ml/              # ProductionEnsembleテスト（3モデル統合・週次学習）
│   ├── features/        # feature_managerテスト（12特徴量統一）
│   ├── trading/         # 統合リスク管理テスト（実取引対応）
│   ├── backtest/        # 統一バックテストエンジンテスト
│   ├── data/            # Bitbank API・パイプラインテスト
│   ├── monitoring/      # Discord 3階層監視・Cloud Run統合テスト
│   └── README.md        # Phase 19単体テスト詳細
└── README.md            # このファイル（Phase 19対応）
```

## 🧪 主要機能・実装

### **Phase 19手動テスト**: MLOps統合検証・7テスト・100%合格
- feature_manager 12特徴量統合テスト・ProductionEnsemble 3モデル統合テスト
- Cloud Run 24時間稼働テスト・Bitbank API + MLOps連携テスト
- DataPipeline + feature_manager統合テスト・DataCache + MLOpsデータ管理テスト
- 654テスト統合テスト・公開API活用・開発支援

### **Phase 19単体テスト**: 654テスト・59.24%カバレッジ・MLOps統合
- feature_manager 12特徴量テスト・ProductionEnsemble 3モデルテスト・週次学習テスト
- 4戦略統合テスト・統合リスク管理テスト・Cloud Run統合テスト
- pytest + MLOpsモック・30秒高速実行・GitHub Actions統合・CI/CD品質ゲート

## 🔧 使用方法・例

### **Phase 19統合テスト実行（654テスト・MLOps統合）**
```bash
# Phase 19全テスト実行（654テスト・59.24%カバレッジ）
python -m pytest tests/unit/ -v --tb=short

# Phase 19手動テスト実行（MLOps統合検証）
python tests/manual/test_phase2_components.py

# Phase 19カバレッジ付きテスト（MLOps対応）
python -m pytest tests/unit/ --cov=src --cov-report=html --cov-report=term-missing

# Phase 19モジュール別テスト（MLOps統合）
python -m pytest tests/unit/features/ -v    # feature_manager 12特徴量テスト
python -m pytest tests/unit/ml/ -v          # ProductionEnsembleテスト
python -m pytest tests/unit/strategies/ -v  # 4戦略統合テスト
python -m pytest tests/unit/trading/ -v     # 統合リスク管理テスト
```

### **Phase 19開発時品質チェック（MLOps統合）**
```bash
# Phase 19統合品質チェック（30秒実行・654テスト）
bash scripts/testing/checks.sh

# MLOps統合管理CLI経由（feature_manager・ProductionEnsemble）
python scripts/testing/dev_check.py validate

# 週次学習テスト（GitHub Actions統合）
python scripts/ml/weekly_training.py --test-mode

# Cloud Run統合テスト（デプロイ検証）
python scripts/deployment/deploy_staging.py --validate
```

### **Phase 19期待結果（MLOps統合）**
```
🚀 Phase 19 MLOps統合テスト結果
collected 654 items
tests/unit/features ✅ feature_manager 12特徴量テスト passed
tests/unit/ml ✅ ProductionEnsemble 3モデル統合テスト passed  
tests/unit/strategies ✅ 4戦略統合テスト passed
tests/unit/trading ✅ 統合リスク管理テスト passed
tests/unit/monitoring ✅ Discord 3階層監視テスト passed
tests/manual ✅ 7/7 (100.0%) MLOps統合検証 passed
========================= 654 passed in 30.12s =========================
Coverage: 59.24% (Phase 19 target achieved)
🎉 MLOps統合品質保証完了！
```

## ⚠️ 注意事項・制約

### **Phase 19実行環境制約（MLOps対応）**
1. **プロジェクトルート**: 必ず`/Users/nao/Desktop/bot`から実行
2. **Phase 19環境**: pytest・pytest-cov・pytest-mock・lightgbm・xgboost・scikit-learn必須
3. **MLOps依存関係**: feature_manager・ProductionEnsemble・週次学習モデル・Cloud Run設定
4. **実行時間**: 全テスト約30秒・Phase 19 MLOps統合テスト含む

### **Phase 19テスト品質基準（MLOps統合）**
- **成功率**: 654テスト100%合格必須・MLOps回帰エラー0件
- **カバレッジ**: 59.24%以上・feature_manager・ProductionEnsemble・週次学習カバー
- **実行速度**: 全テスト30秒以内・MLOps統合テスト含む
- **MLOps品質**: 12特徴量テスト・3モデルアンサンブル・Cloud Run統合・Discord監視

### **Phase 19モック・スタブ戦略（MLOps対応）**
- **外部API**: BitbankAPI・Discord Webhook・Cloud Run API完全モック化
- **MLOpsモデル**: ProductionEnsemble軽量版・feature_manager予測可能データ
- **週次学習**: GitHub Actions Mock・学習プロセステストデータ
- **MLOps統合**: 12特徴量テストデータ・3モデル予測データ・固定datetime管理

## 🔗 関連ファイル・依存関係

### **Phase 19システム統合（MLOps対応）**
- **src/features/feature_generator.py**: 12特徴量統一管理・テスト対象・品質確認
- **src/ml/**: ProductionEnsemble・週次学習・3モデルアンサンブルテスト対象
- **scripts/testing/checks.sh**: 654テスト統合品質チェック・GitHub Actions統合
- **scripts/management/**: MLOps統合管理・feature_manager・ProductionEnsembleテスト

### **Phase 19設定・環境（MLOps対応）**
- **config/**: Phase 19設定・MLOpsテスト用設定・feature_manager設定
- **models/**: ProductionEnsembleモデル・週次学習モデル・テスト用軽量モデル
- **coverage-reports/**: Phase 19カバレッジ59.24%・MLOps品質指標・HTML出力

### **Phase 19外部依存（MLOps統合）**
- **pytest**: Phase 19テストフレームワーク・654テストランナー・MLOpsアサーション
- **lightgbm・xgboost**: ProductionEnsemble実テスト・3モデル統合検証
- **pytest-mock**: MLOpsモック・feature_manager・ProductionEnsembleパッチ
- **GitHub Actions**: 週次学習CI/CD・自動モデルテスト・MLOps品質ゲート・段階的デプロイ

---

**🎯 Phase 19 MLOps対応完了**: 654テスト・59.24%カバレッジ・feature_manager 12特徴量統一管理・ProductionEnsemble 3モデル統合・週次自動学習・Cloud Run 24時間稼働・Discord 3階層監視・GitHub Actions統合・CI/CD品質ゲート・段階的デプロイにより、包括的なMLOps品質保証システムを実現。