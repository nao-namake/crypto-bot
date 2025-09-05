# tests/unit/ - Phase 19単体テストシステム

**Phase 19対応**: 654テスト・59.24%カバレッジ・MLOps統合・feature_manager・ProductionEnsemble品質保証（2025年9月4日現在）

## 🎯 役割・責任

Phase 19 MLOps統合単体テストシステムとして以下を提供：
- **MLOps統合テスト**: feature_manager・ProductionEnsemble・週次学習・統合システム
- **品質保証**: 654テスト・59.24%カバレッジ・正常系・異常系・境界値・MLOps連携
- **CI/CD統合**: GitHub Actions・自動品質ゲート・週次学習テスト・段階的デプロイ
- **MLOps品質管理**: 12特徴量テスト・3モデルアンサンブル・Cloud Run統合・Discord監視

## 📂 ファイル構成

```
unit/
├── strategies/          # 戦略システムテスト（Phase 19統合・4戦略・100%合格）
│   ├── implementations/ # 戦略実装テスト（ATR・もちぽよ・MTF・フィボナッチ）
│   ├── base/           # 戦略基盤テスト（戦略マネージャー・統合制御）
│   ├── utils/          # 共通ユーティリティテスト（シグナル統合・多数決）
│   ├── test_strategy_manager.py  # 戦略管理テスト
│   └── README.md       # 戦略テスト詳細
├── ml/                  # Phase 19 MLOpsテスト（ProductionEnsemble・週次学習）
│   ├── models/         # 個別モデルテスト（LightGBM・XGBoost・RF）
│   ├── production/     # ProductionEnsembleテスト（3モデル統合）
│   ├── test_ensemble_model.py    # アンサンブル統合テスト
│   ├── test_ml_integration.py    # MLOps統合テスト
│   ├── test_model_manager.py     # モデル管理・週次学習テスト
│   ├── test_voting_system.py     # 重み付け投票テスト
│   └── README.md       # MLOpsテスト詳細
├── trading/             # 取引実行・統合リスク管理テスト（Phase 19対応）
│   ├── test_executor.py           # 実取引・ペーパートレードテスト
│   ├── test_integrated_risk_manager.py  # 統合リスク管理テスト
│   ├── test_kelly_criterion.py   # Kelly基準・ポジションサイジングテスト
│   ├── test_anomaly_detector.py  # 異常検知・アラートテスト
│   ├── test_drawdown_manager.py  # ドローダウン管理テスト
│   └── README.md       # 取引テスト詳細
├── features/            # Phase 19特徴量システムテスト（feature_manager統合）
│   ├── test_feature_generator.py # 12特徴量統一生成テスト
│   ├── test_technical.py         # テクニカル指標テスト
│   └── test_anomaly.py           # 異常検知特徴量テスト
├── backtest/            # バックテストエンジンテスト（統一レポーター）
│   ├── test_engine.py  # バックテストエンジンテスト
│   └── README.md       # バックテストテスト詳細
├── data/                # データ層テスト（Bitbank API・パイプライン）
│   ├── test_bitbank_client.py    # BitbankAPIテスト
│   └── test_data_cache.py        # データキャッシュテスト
├── monitoring/          # Phase 19監視テスト（Discord・Cloud Run統合）
│   └── test_discord.py           # Discord通知・MLOps監視テスト
└── README.md            # このファイル（Phase 19対応）
```

## ✅ 主要機能・実装

### **Phase 19統合戦略テスト**: 4戦略・feature_manager連携・高速実行
- ATRベース・フィボナッチ・もちぽよアラート・マルチタイムフレーム戦略統合
- feature_manager 12特徴量統一管理・DataFrame出力・戦略シームレス連携
- 戦略基盤・戦略管理・シグナル統合・多数決システム・リスク管理統合

### **Phase 19 MLOpsテスト**: ProductionEnsemble・週次学習・3モデル統合
- ProductionEnsemble（LightGBM 40%・XGBoost 40%・RandomForest 20%）
- 週次自動学習・GitHub Actions統合・モデルバージョン管理・デプロイ自動化
- 重み付け投票・信頼度閾値・予測精度評価・MLOps品質管理・Cloud Run統合

### **統合取引・リスク管理テスト**: Phase 19実取引対応・MLOps連携
- 統合リスク管理・Kelly基準・実取引・ペーパートレード・ポジションサイジング
- レイテンシー監視・Discord 3階層通知・安全係数・Cloud Run統合・MLOps連携
- 異常検知・ドローダウン管理・3段階リスク判定・feature_manager統合評価

### **Phase 19特徴量システムテスト**: feature_manager統合・12特徴量・DataFrame統一
- feature_manager 12特徴量統一生成・テクニカル指標・異常検知特徴量
- マルチタイムフレーム（4h/15m）統合・DataFrame標準出力・戦略シームレス連携
- Phase 19互換性・テスト完全カバー・品質保証・パフォーマンス最適化

### **Phase 19バックテスト・監視統合**: 統一レポーター・Discord監視・Cloud Run
- 統一バックテストエンジン・性能評価・CSV/JSON出力・Phase 19互換性
- Discord 3階層監視・Cloud Run統合・MLOps監視・週次学習監視・品質管理

## 🔧 使用方法・例

### **Phase 19全テスト実行（654テスト・59.24%カバレッジ）**
```bash
# Phase 19統合テスト実行（654テスト・MLOps対応）
python -m pytest tests/unit/ -v --tb=short

# Phase 19カバレッジ付き実行（59.24%目標）
python -m pytest tests/unit/ --cov=src --cov-report=html --cov-report=term-missing

# Phase 19高速並列実行（MLOps統合テスト）
python -m pytest tests/unit/ -n auto --maxfail=5

# 品質保証統合チェック（30秒実行）
bash scripts/testing/checks.sh
```

### **Phase 19モジュール別テスト（MLOps統合）**
```bash
# Phase 19戦略統合テスト（feature_manager連携）
python -m pytest tests/unit/strategies/ -v --tb=short

# Phase 19 MLOpsテスト（ProductionEnsemble・週次学習）
python -m pytest tests/unit/ml/ -v --tb=short

# Phase 19特徴量システムテスト（12特徴量統合）
python -m pytest tests/unit/features/ -v --tb=short

# Phase 19統合取引テスト（実取引対応）
python -m pytest tests/unit/trading/ -v --tb=short

# Phase 19バックテスト・監視統合テスト
python -m pytest tests/unit/backtest/ tests/unit/monitoring/ -v
```

### **Phase 19詳細MLOpsテスト**
```bash
# ProductionEnsembleテスト（3モデル統合）
python -m pytest tests/unit/ml/production/test_production_ensemble.py::TestProductionEnsemble -v

# feature_manager統合テスト（12特徴量）
python -m pytest tests/unit/features/test_feature_generator.py::TestFeatureGenerator::test_generate_features -v

# Phase 19戦略統合テスト（feature_manager連携）
python -m pytest tests/unit/strategies/implementations/test_atr_based.py::TestATRBasedStrategy::test_phase19_integration -v

# MLOps統合失敗時詳細表示
python -m pytest tests/unit/ -v --tb=short --maxfail=3 -x
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
- **実行速度**: 全テスト30秒以内・MLOps統合テスト含む・個別モジュール5秒以内
- **MLOps品質**: 12特徴量テスト・3モデルアンサンブル・Cloud Run統合・Discord監視

### **Phase 19モック・テストデータ戦略（MLOps対応）**
- **外部API**: BitbankAPI・Discord Webhook・Cloud Run API完全モック化
- **MLOpsモデル**: ProductionEnsemble軽量版・feature_manager予測可能データ
- **週次学習**: GitHub Actions Mock・学習プロセステストデータ
- **MLOps統合**: 12特徴量テストデータ・3モデル予測データ・固定datetime管理

## 🔗 関連ファイル・依存関係

### **Phase 19テスト対象システム（MLOps統合）**
- **src/features/feature_generator.py**: 12特徴量統一管理・DataFrame出力・戦略連携
- **src/ml/**: ProductionEnsemble・週次学習・3モデルアンサンブル・MLOps統合
- **src/strategies/**: 4戦略・feature_manager連携・統合シグナル生成
- **src/trading/**: 統合リスク管理・実取引・Cloud Run統合・Discord監視

### **Phase 19テスト基盤・環境（MLOps対応）**
- **pytest.ini**: Phase 19 pytest設定・MLOpsテストパス・カバレッジ59.24%設定
- **conftest.py**: Phase 19フィクスチャ・feature_manager・ProductionEnsemble設定
- **scripts/testing/checks.sh**: 654テスト統合実行・品質保証・30秒チェック
- **coverage-reports/**: Phase 19カバレッジ・MLOps品質指標・HTML出力

### **Phase 19外部依存（MLOps統合）**
- **pytest**: Phase 19テストフレームワーク・654テストランナー・アサーション
- **pytest-mock**: MLOpsモック・feature_manager・ProductionEnsembleパッチ
- **lightgbm・xgboost**: ProductionEnsemble実テスト・3モデル統合検証
- **pandas・numpy**: 12特徴量DataFrame・テストデータ生成・MLOps数値計算

---

**🎯 Phase 19 MLOps対応完了**: 654テスト・59.24%カバレッジ・feature_manager 12特徴量・ProductionEnsemble 3モデル統合・週次自動学習・Cloud Run 24時間稼働・Discord監視統合により、包括的なMLOps品質保証システムを実現。