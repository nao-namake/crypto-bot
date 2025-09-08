# tests/ - テスト・品質保証システム

## 🎯 役割・責任

システム全体のテスト・品質保証を統合管理し、コード品質の維持、回帰防止、継続的品質向上を支援します。単体テストから手動テストまで、包括的なテストカバレッジでシステムの信頼性と安定性を確保し、開発効率の向上と品質の継続的改善を実現します。

## 📂 ディレクトリ構成

```
tests/
├── README.md                    # このファイル
├── unit/                        # 単体テストシステム（32テストファイル）
│   ├── backtest/                   # バックテストエンジンテスト
│   ├── core/                       # コアシステム・設定・ML統合テスト
│   ├── data/                       # データ層・キャッシュ・API接続テスト
│   ├── features/                   # 特徴量生成・管理テスト
│   ├── ml/                         # 機械学習・モデル・アンサンブルテスト
│   ├── monitoring/                 # Discord通知・監視システムテスト
│   ├── strategies/                 # 取引戦略・戦略管理テスト
│   ├── trading/                    # 取引実行・リスク管理テスト
│   └── README.md                   # 単体テスト詳細ガイド
└── manual/                      # 手動テスト・開発検証（1テストファイル）
    ├── manual_bitbank_client.py       # Bitbank APIクライアント手動テスト
    └── README.md                   # 手動テスト詳細ガイド
```

## 📋 主要テストカテゴリの役割

### **unit/ - 単体テストシステム**
システム全体の自動テストによる品質保証を担当します。
- **32テストファイル**: 機械学習・取引戦略・データ処理・監視システムの包括的テスト
- **自動実行**: pytest による高速・並列・CI/CD統合テスト実行
- **品質保証**: カバレッジ測定・回帰防止・コード品質チェック・継続的品質維持
- **モック統合**: 外部API・システム依存のテスト分離・予測可能な結果
- **開発効率**: 迅速なフィードバック・問題早期発見・安全なリファクタリング

### **manual/ - 手動テスト・開発検証**
自動テストでカバーできない実際の統合動作の検証を担当します。
- **1テストファイル**: Bitbank APIクライアントの実API接続テスト
- **実API接続**: モックではない実際のAPI・ネットワーク・レスポンス確認
- **開発支援**: 新機能実装時の動作確認・問題特定・トラブルシューティング
- **統合確認**: 複数システム間の実際の連携動作・エンドツーエンドテスト
- **品質補完**: 自動テストの限界を補完・実環境での動作保証

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

### **手動テスト実行**
```bash
# Bitbank APIクライアント手動テスト
cd /Users/nao/Desktop/bot
python tests/manual/manual_bitbank_client.py

# 期待結果:
# ✅ クライアント初期化成功
# 📊 サポート時間軸確認
# 📈 統計情報取得
# 🎉 基本テスト完了
```

### **開発時品質チェック**
```bash
# 統合品質チェック（開発時必須）
bash scripts/testing/checks.sh

# 統合開発管理CLI
python3 scripts/testing/dev_check.py full-check

# 個別品質確認
python3 scripts/testing/dev_check.py validate       # 基本品質チェック
python3 scripts/testing/dev_check.py ml-models      # 機械学習モデル確認
python3 scripts/testing/dev_check.py status         # システム状態確認
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
- **実行場所**: プロジェクトルートディレクトリ（/Users/nao/Desktop/bot）から実行必須
- **依存関係**: 機械学習ライブラリ（scikit-learn・lightgbm・xgboost）完全インストール
- **実行時間**: 全テスト約30-60秒・手動テスト10-30秒・開発効率重視

### **テスト品質基準**
- **成功率**: 全テスト100%成功・回帰エラー0件・継続的品質維持必須
- **カバレッジ**: 50%以上維持・新機能追加時のテスト追加必須・品質指標管理
- **実行速度**: 高速実行・CI/CD統合・開発フィードバック迅速化
- **品質保証**: 正常系・異常系・境界値・統合テストの完全カバー

### **モック・テストデータ戦略**
- **外部API**: Bitbank API・Discord Webhook・Cloud Run API 完全モック化
- **機械学習**: ProductionEnsemble軽量版・予測可能テストデータ・固定結果
- **時間依存**: 固定datetime・タイムゾーン・市場時間の一貫性・再現性確保
- **リソース**: メモリ効率・テスト分離・クリーンアップ・状態管理・並列実行対応

### **CI/CD統合制約**
- **自動実行**: GitHub Actions・品質ゲート・プルリクエスト時自動実行
- **段階的実行**: 開発・ステージング・本番の段階的品質確認
- **失敗時対応**: 自動通知・詳細レポート・問題特定・修正ガイド提供
- **品質維持**: 継続的監視・パフォーマンス追跡・品質指標管理・改善提案

## 🔗 関連ファイル・依存関係

### **テスト対象システム**
- `src/features/feature_generator.py`: 特徴量生成・12特徴量・データ前処理
- `src/ml/ensemble.py`: ProductionEnsemble・3モデル統合・予測エンジン
- `src/strategies/`: 4戦略・戦略管理・シグナル生成・リスク管理
- `src/trading/`: 取引実行・リスク管理・異常検知・ドローダウン管理
- `src/monitoring/`: Discord通知・システム監視・アラート・ヘルスチェック

### **テスト基盤・環境**
- `pytest.ini`: pytest設定・テストパス・カバレッジ設定・実行オプション
- `conftest.py`: フィクスチャ・モック・テストデータ・環境設定・共通処理
- `coverage-reports/`: カバレッジレポート・品質指標・HTML出力・分析データ
- `logs/`: テストログ・エラーログ・実行履歴・デバッグ情報

### **品質保証・CI/CD統合**
- `scripts/testing/checks.sh`: 品質チェック・テスト実行・統合確認・CI/CD対応
- `scripts/testing/dev_check.py`: 統合開発管理・品質確認・システム診断・多機能CLI
- `.github/workflows/`: CI/CDパイプライン・自動テスト・品質ゲート・デプロイ統合
- GitHub Actions・自動品質管理・Discord通知・Cloud Run監視統合

### **外部依存・ライブラリ**
- **pytest**: テストフレームワーク・アサーション・テストランナー・並列実行
- **pytest-mock**: モック機能・外部API・システム依存のテスト分離・スタブ
- **pytest-cov**: カバレッジ測定・品質指標・レポート生成・HTML出力
- **機械学習**: scikit-learn・lightgbm・xgboost・pandas・numpy・モデルテスト

### **監視・レポートシステム**
- `src/monitoring/discord_notifier.py`: テスト結果通知・品質アラート・レポート配信
- Cloud Run監視・ヘルスチェック・パフォーマンス・エラー検知・自動復旧
- HTMLダッシュボード・可視化・統計分析・トレンド監視・品質メトリクス

### **設定・環境管理**
- `config/`: テスト設定・品質閾値・環境変数・認証情報・パラメータ管理
- `.flake8`・`pyproject.toml`: コード品質・プロジェクト設定・ツール設定・品質基準
- 環境変数・API認証・ネットワーク設定・プロキシ・セキュリティ設定

### **継続的改善**
- **フィードバックループ**: テスト結果→改善提案→実装→再テスト
- **品質指標管理**: カバレッジ・成功率・実行時間・パフォーマンス追跡
- **自動化拡張**: 手動テスト→自動テスト化・CI/CD統合拡張・効率改善
- **知識蓄積**: ベストプラクティス・トラブルシューティング・ドキュメント整備