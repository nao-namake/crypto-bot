# tests/unit/ - 単体テストシステム（Phase 49完了時点）

## 🎯 役割・責任

システム全体の単体テストを管理し、コード品質の保証、回帰防止、継続的品質向上を支援します。機械学習モデル、取引戦略、データ処理、監視システムまで、包括的なテストカバレッジでシステムの信頼性を確保します（Phase 49: 1,117テスト・68.32%カバレッジ達成）。

## 📂 ディレクトリ構成（Phase 49完了版）

```
tests/unit/
├── README.md                    # このファイル（Phase 49完了版）
├── backtest/                    # バックテストエンジンテスト
│   └── test_engine.py              # バックテストエンジン・性能評価テスト
├── core/                        # コアシステムテスト
│   ├── services/                   # コアサービステスト
│   │   ├── test_health_checker.py      # ヘルスチェック機能テスト
│   │   └── test_trading_logger.py      # 取引ログシステムテスト
│   ├── test_config_thresholds.py       # 設定・閾値管理テスト
│   └── test_ml_adapter_exception_handling.py  # ML統合・例外処理テスト
├── data/                        # データ層テスト
│   └── test_data_cache.py           # データキャッシュ・管理テスト
├── features/                    # 特徴量システムテスト
│   └── test_feature_generator.py       # 特徴量生成・管理テスト（55特徴量対応）
├── ml/                          # 機械学習システムテスト
│   ├── models/                     # 個別モデルテスト
│   │   ├── test_rf_model.py            # RandomForest モデルテスト
│   │   └── test_xgb_model.py           # XGBoost モデルテスト
│   ├── production/                 # 本番モデルテスト
│   │   └── test_ensemble.py            # ProductionEnsemble テスト
│   ├── test_ensemble_model.py          # アンサンブルモデル統合テスト
│   ├── test_ml_integration.py          # ML統合・パイプラインテスト
│   ├── test_model_manager.py           # モデル管理・バージョン管理テスト
│   └── test_voting_system.py           # 投票システム・重み付けテスト
├── monitoring/                  # 監視システムテスト
│   ├── test_discord_client.py          # Discord クライアントテスト
│   ├── test_discord_formatter.py       # Discord フォーマッターテスト
│   └── test_discord_manager.py         # Discord 管理システムテスト
├── strategies/                  # 取引戦略システムテスト
│   ├── base/                       # 戦略基盤テスト
│   │   └── test_strategy_base.py       # 戦略基盤クラステスト
│   ├── implementations/            # 戦略実装テスト
│   │   ├── test_atr_based.py           # ATR戦略テスト
│   │   ├── test_fibonacci_retracement.py # フィボナッチ戦略テスト
│   │   ├── test_mochipoy_alert.py      # もちぽよアラート戦略テスト
│   │   └── test_multi_timeframe.py     # マルチタイムフレーム戦略テスト
│   ├── utils/                      # 戦略ユーティリティテスト
│   │   ├── test_constants.py           # 戦略定数テスト
│   │   ├── test_risk_manager.py        # リスク管理テスト
│   │   └── test_signal_builder.py      # シグナル構築テスト
│   └── test_strategy_manager.py        # 戦略管理システムテスト
└── trading/                     # 取引システムテスト
    ├── test_anomaly_detector.py        # 異常検知システムテスト
    ├── test_drawdown_manager.py        # ドローダウン管理テスト
    ├── test_executor.py                # 取引実行エンジンテスト
    ├── test_init.py                    # 取引システム初期化テスト
    ├── test_integrated_risk_manager.py # 統合リスク管理テスト
    └── test_kelly_criterion.py         # Kelly基準・ポジションサイジングテスト
```

## 📋 主要テストカテゴリの役割

### **ml/ - 機械学習システムテスト**
機械学習モデルの品質保証と統合テストを担当します。
- **個別モデルテスト**: RandomForest・XGBoost の学習・予測・性能評価
- **ProductionEnsemble**: 3モデル統合・重み付け投票・本番運用テスト
- **統合テスト**: 特徴量→モデル→予測のエンドツーエンドテスト
- **モデル管理**: バージョン管理・メタデータ・学習履歴・品質評価
- 8テストファイル・機械学習パイプライン全体をカバー

### **strategies/ - 取引戦略システムテスト**（Phase 49完了版）
5つの取引戦略の動作確認と戦略管理システムのテストです。
- **戦略実装**: ATR・フィボナッチ・もちぽよアラート・マルチタイムフレーム・Donchian Channel
- **戦略基盤**: 共通基盤クラス・戦略インターフェース・統合制御
- **ユーティリティ**: シグナル構築・リスク管理・定数管理
- **戦略管理**: 複数戦略の統合・競合解決・信頼度評価
- 8テストファイル・戦略システム全体をカバー

### **trading/ - 取引システムテスト**
実際の取引実行とリスク管理システムの品質保証です。
- **取引実行**: 実取引・ペーパートレード・注文管理・レイテンシー監視
- **リスク管理**: Kelly基準・ポジションサイジング・統合リスク評価
- **異常検知**: 市場異常・システム異常・アラート・自動停止
- **ドローダウン管理**: 損失制限・安全係数・復旧判定
- 6テストファイル・取引システム全体をカバー

### **monitoring/ - 監視システムテスト**
Discord通知とシステム監視の品質保証です。
- **Discord統合**: クライアント・フォーマッター・管理システム
- **通知機能**: Critical/Warning/Info 3階層通知・アラート・レポート
- **監視連携**: Cloud Run・システムヘルス・パフォーマンス監視
- 3テストファイル・監視システム全体をカバー

### **features/ - 特徴量システムテスト**（Phase 49完了版）
特徴量生成とデータ処理の品質保証です。
- **特徴量生成**: 55特徴量（50基本+5戦略信号）・テクニカル指標・Strategy-Aware ML対応
- **データ品質**: 欠損値処理・異常値検知・データ整合性
- **パフォーマンス**: 生成速度・メモリ効率・スケーラビリティ
- 1アクティブテストファイル・特徴量システムをカバー

### **core/ - コアシステムテスト**
システム基盤とサービスの品質保証です。
- **設定管理**: 閾値・パラメータ・環境変数・設定検証
- **ML統合**: 機械学習アダプター・例外処理・フォールバック
- **ヘルスチェック**: システム監視・サービス状態・復旧処理
- 4テストファイル・システム基盤をカバー

## 📝 使用方法・例

### **全テスト実行**
```bash
# 全単体テスト実行（推奨）
python -m pytest tests/unit/ -v --tb=short

# カバレッジ付き実行
python -m pytest tests/unit/ --cov=src --cov-report=html --cov-report=term-missing

# 並列実行（高速化）
python -m pytest tests/unit/ -n auto --maxfail=5

# 品質チェック統合実行
bash scripts/testing/checks.sh
```

### **カテゴリ別テスト実行**
```bash
# 機械学習システムテスト
python -m pytest tests/unit/ml/ -v --tb=short

# 取引戦略システムテスト
python -m pytest tests/unit/strategies/ -v --tb=short

# 取引システムテスト
python -m pytest tests/unit/trading/ -v --tb=short

# 監視システムテスト
python -m pytest tests/unit/monitoring/ -v --tb=short

# 特徴量システムテスト
python -m pytest tests/unit/features/ -v --tb=short
```

### **個別テスト実行**
```bash
# ProductionEnsemble テスト
python -m pytest tests/unit/ml/production/test_ensemble.py -v

# 特徴量生成テスト
python -m pytest tests/unit/features/test_feature_generator.py -v

# 取引実行エンジンテスト
python -m pytest tests/unit/trading/test_executor.py -v

# Discord通知テスト
python -m pytest tests/unit/monitoring/test_discord_manager.py -v
```

### **テスト結果分析**
```bash
# 失敗したテストの詳細表示
python -m pytest tests/unit/ -v --tb=long --maxfail=3

# 特定のテストメソッド実行
python -m pytest tests/unit/ml/test_ensemble_model.py::TestEnsembleModel::test_predict -v

# カバレッジレポート確認
open coverage-reports/htmlcov/index.html
```

## ⚠️ 注意事項・制約

### **実行環境要件**
- **Python環境**: Python 3.8以上・pytest・pytest-cov・pytest-mock必須
- **実行場所**: プロジェクトルートディレクトリ（/Users/nao/Desktop/bot）から実行
- **依存関係**: 機械学習ライブラリ（scikit-learn・lightgbm・xgboost）完全インストール
- **実行時間**: 全テスト約30-60秒・個別カテゴリ5-15秒

### **テスト品質基準**
- **成功率**: 全テスト100%成功・回帰エラー0件・継続的品質維持
- **カバレッジ**: 50%以上維持・新機能追加時のテスト追加必須
- **実行速度**: 高速実行・CI/CD統合・開発効率重視
- **品質保証**: 正常系・異常系・境界値・統合テストの完全カバー

### **モック・テストデータ戦略**
- **外部API**: Bitbank API・Discord Webhook・Cloud Run API 完全モック化
- **機械学習**: ProductionEnsemble軽量版・予測可能テストデータ
- **時間依存**: 固定datetime・タイムゾーン・市場時間の一貫性
- **リソース**: メモリ効率・テスト分離・クリーンアップ・状態管理

### **CI/CD統合制約**
- **自動実行**: GitHub Actions・品質ゲート・自動品質チェック
- **段階的実行**: プルリクエスト・マージ前・デプロイ前の自動実行
- **失敗時対応**: 自動通知・詳細レポート・問題特定・修正ガイド
- **品質維持**: 継続的監視・パフォーマンス追跡・品質指標管理

## 🔗 関連ファイル・依存関係

### **テスト対象システム**（Phase 49完了版）
- `src/features/feature_manager.py`: 特徴量生成・55特徴量（50基本+5戦略信号）・データ前処理
- `src/ml/ensemble.py`: ProductionEnsemble・3モデル統合・予測エンジン
- `src/strategies/`: 5戦略・戦略管理・シグナル生成・リスク管理
- `src/trading/`: 取引実行・リスク管理・異常検知・ドローダウン管理
- `src/monitoring/`: Discord通知・システム監視・アラート・ヘルスチェック

### **テスト基盤・環境**
- `pytest.ini`: pytest設定・テストパス・カバレッジ設定・実行オプション
- `conftest.py`: フィクスチャ・モック・テストデータ・環境設定
- `scripts/testing/checks.sh`: 品質チェック・テスト実行・統合確認
- `coverage-reports/`: カバレッジレポート・品質指標・HTML出力

### **外部依存・ライブラリ**
- **pytest**: テストフレームワーク・アサーション・テストランナー
- **pytest-mock**: モック機能・外部API・システム依存のテスト分離
- **pytest-cov**: カバレッジ測定・品質指標・レポート生成
- **機械学習**: scikit-learn・lightgbm・xgboost・pandas・numpy

### **品質保証・CI/CD**
- `.github/workflows/`: CI/CDパイプライン・自動テスト・品質ゲート
- `scripts/testing/checks.sh`: 品質チェック（Phase 49完了版）・テスト実行・統合確認
- Discord通知・Cloud Run監視・GitHub Actions統合・自動品質管理