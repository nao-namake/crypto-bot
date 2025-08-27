# tests/unit/ - 単体テストシステム

**Phase 13対応**: 306テスト・58.88%カバレッジ・pytest統合・CI/CD品質保証（2025年8月26日現在）

## 🎯 役割・責任

単体テストシステムとして以下を提供：
- **モジュール別テスト**: 戦略・ML・取引・バックテスト・データ・特徴量・監視
- **品質保証**: 306テスト・58.88%カバレッジ・正常系・異常系・境界値
- **CI/CD統合**: pytest・GitHub Actions・自動品質チェック・継続的統合
- **回帰防止**: モック・スタブ・テストデータ管理・予測可能テスト

## 📂 ファイル構成

```
unit/
├── strategies/          # 戦略システムテスト（113テスト・100%合格）
│   ├── implementations/ # 戦略実装テスト（62テスト）
│   ├── base/           # 戦略基盤テスト（18テスト）
│   ├── utils/          # 共通ユーティリティテスト（33テスト）
│   ├── test_strategy_manager.py  # 戦略管理テスト
│   └── README.md       # 戦略テスト詳細
├── ml/                  # 機械学習テスト（89テスト・8クラス・164関数）
│   ├── models/         # 個別モデルテスト（RF・XGB）
│   ├── production/     # 本番アンサンブルテスト
│   ├── test_ensemble_model.py    # アンサンブルモデルテスト
│   ├── test_ml_integration.py    # ML統合テスト
│   ├── test_model_manager.py     # モデル管理テスト
│   ├── test_voting_system.py     # 投票システムテスト
│   └── README.md       # MLテスト詳細
├── trading/             # 取引実行・リスク管理テスト（113テスト）
│   ├── test_executor.py           # 取引実行テスト
│   ├── test_integrated_risk_manager.py  # 統合リスク管理テスト
│   ├── test_kelly_criterion.py   # Kelly基準テスト
│   ├── test_anomaly_detector.py  # 異常検知テスト
│   ├── test_drawdown_manager.py  # ドローダウン管理テスト
│   └── README.md       # 取引テスト詳細
├── backtest/            # バックテストエンジンテスト（84テスト）
│   ├── test_engine.py  # バックテストエンジンテスト
│   └── README.md       # バックテストテスト詳細
├── data/                # データ層テスト
│   ├── test_bitbank_client.py    # BitbankAPIテスト
│   └── test_data_cache.py        # データキャッシュテスト
├── features/            # 特徴量システムテスト
│   ├── test_technical.py         # テクニカル指標テスト
│   └── test_anomaly.py           # 異常検知特徴量テスト
├── monitoring/          # 監視・通知テスト
│   └── test_discord.py           # Discord通知テスト
└── README.md            # このファイル
```

## ✅ 主要機能・実装

### **strategies/**: 戦略システムテスト（113テスト・0.44秒実行）
- ATRベース・フィボナッチ・もちぽよアラート・マルチタイムフレーム戦略
- 戦略基盤・戦略管理・共通ユーティリティ・シグナル生成
- ボラティリティ分析・多数決システム・タイムフレーム同期・リスク管理

### **ml/**: 機械学習テスト（89テスト・8クラス・164関数）
- アンサンブルモデル・投票システム・個別モデル・モデル管理
- ML統合・LightGBM・XGBoost・RandomForest・本番環境統合
- sklearn警告解消・重み付け投票・信頼度閾値・予測精度評価

### **trading/**: 取引実行・リスク管理テスト（113テスト）
- 統合リスク管理・Kelly基準・取引実行・異常検知・ドローダウン管理
- ペーパートレード・注文管理・ポジションサイジング・3段階リスク判定
- レイテンシー監視・Discord通知・安全係数・リスク制限

### **backtest/**: バックテストエンジンテスト（84テスト）
- バックテストエンジン・ポジション管理・性能評価・統計分析
- データローダー・レポートシステム・CSV/JSON出力・品質管理

## 🔧 使用方法・例

### **全テスト実行**
```bash
# 全単体テスト実行（306テスト）
python -m pytest tests/unit/ -v

# カバレッジ付き実行
python -m pytest tests/unit/ --cov=src --cov-report=html

# 高速実行（並列）
python -m pytest tests/unit/ -n auto
```

### **モジュール別テスト**
```bash
# 戦略システムテスト（113テスト・0.44秒）
python -m pytest tests/unit/strategies/ -v

# 機械学習テスト（89テスト）
python -m pytest tests/unit/ml/ -v

# 取引実行テスト（113テスト）
python -m pytest tests/unit/trading/ -v

# バックテストテスト（84テスト）
python -m pytest tests/unit/backtest/ -v
```

### **詳細テスト**
```bash
# 特定テストクラス実行
python -m pytest tests/unit/ml/test_ensemble_model.py::TestEnsembleModel -v

# 特定テスト関数実行
python -m pytest tests/unit/strategies/implementations/test_atr_based.py::TestATRBasedStrategy::test_generate_signal -v

# 失敗時詳細表示
python -m pytest tests/unit/ -v --tb=short
```

## ⚠️ 注意事項・制約

### **実行環境制約**
1. **プロジェクトルート**: 必ず`/Users/nao/Desktop/bot`から実行
2. **pytest環境**: pytest・pytest-cov・pytest-mock・numpy・pandas必須
3. **依存関係**: src/全モジュール・config/設定・models/MLモデル
4. **実行時間**: 全テスト約25秒・戦略テスト0.44秒

### **テスト品質基準**
- **成功率**: 306テスト100%合格必須・回帰エラー0件
- **カバレッジ**: 58.88%以上・正常系・異常系・境界値カバー
- **実行速度**: 全テスト30秒以内・個別モジュール5秒以内
- **保守性**: モック・フィクスチャ・テストデータ分離

### **モック・テストデータ戦略**
- **外部API**: BitbankAPI・Discord Webhook完全モック化
- **MLモデル**: テスト用軽量モデル・予測可能データ
- **ファイルシステム**: 一時ディレクトリ・tempfile活用
- **時間依存処理**: 固定datetime・タイムスタンプ管理

## 🔗 関連ファイル・依存関係

### **テスト対象システム**
- **src/strategies/**: 戦略システム実装・テスト対象コード
- **src/ml/**: 機械学習システム・アンサンブル・モデル管理
- **src/trading/**: 取引実行・リスク管理・ポジション管理
- **src/backtest/**: バックテストエンジン・評価・レポート

### **テスト基盤・環境**
- **pytest.ini**: pytest設定・テストパス・カバレッジ設定
- **conftest.py**: 共通フィクスチャ・テストセットアップ
- **coverage-reports/**: カバレッジレポート・品質指標・HTML出力

### **外部依存**
- **pytest**: テストフレームワーク・テストランナー・アサーション
- **pytest-mock**: モック・パッチ・外部依存分離
- **numpy・pandas**: テストデータ生成・数値計算・データフレーム
- **scikit-learn**: MLテスト・モデル検証・評価指標

---

**🎯 Phase 13対応完了**: 306テスト・58.88%カバレッジ・pytest統合・CI/CD品質保証により包括的な単体テストシステムを実現。