# scripts/testing/ - 品質保証・テストシステム

**最終更新**: 2025年11月16日 - Phase 52.4更新・1,191テスト100%成功・68.77%カバレッジ達成・60特徴量システム完全対応

## 🎯 役割・責任

システム全体の品質保証、テスト実行、コード品質チェックを担当するテストシステムです。単体テストから統合テスト、カバレッジ測定、コードスタイルチェック、機械学習モデル検証、システム整合性検証まで、包括的な品質保証機能を提供し、継続的な品質向上と回帰防止を支援します。

**Phase 52.4更新内容**: 1,191テスト100%成功（+74テスト）・68.77%カバレッジ達成・60特徴量システム完全対応・ensemble_full.pkl/ensemble_basic.pkl 2段階Graceful Degradation・fix_*.py削除（Phase 52.3使い捨てスクリプト4ファイル・444行削減）

**Phase 49-52成果**: バックテスト完全改修・確定申告対応・週間レポート・外部API削除（Phase 50.9）・3戦略+60特徴量システム・動的戦略管理基盤（Phase 51.5-B）

## 📂 ファイル構成

```
scripts/testing/
├── README.md                      # このファイル
├── checks.sh                      # 品質チェック・テスト実行スクリプト
├── validate_system.sh             # システム整合性検証スクリプト
└── validate_model_consistency.py  # MLモデル整合性検証
```

**Phase 52.4削除ファイル**（Phase 52.3使い捨てスクリプト・444行削減）:
- ~~fix_e115.py~~ - E115エラー自動修正（既に修正完了・不要）
- ~~fix_e226.py~~ - E226エラー自動修正（既に修正完了・不要）
- ~~fix_f541.py~~ - F541エラー自動修正（既に修正完了・不要）
- ~~fix_f811_f841.py~~ - F811/F841エラー自動修正（既に修正完了・不要）

## 📋 主要ファイル・フォルダの役割

### **checks.sh**
システム全体の品質チェックとテスト実行を管理するメインスクリプトです。

**主要機能**:
- **テスト実行**: pytest による全テストスイート実行・**1,191テスト・100%成功**
- **カバレッジ測定**: coverage による網羅率測定（**68.77%達成**・65%目標超過）・HTML/JSON/Term出力
- **コードスタイル**: flake8・black・isort によるPEP8準拠チェック
- **ML学習データ確認**: 実データファイル存在確認（15m/4h両タイムフレーム・17,272件）
- **60特徴量システム**: 49基本+3戦略+7時間+1シグナル特徴量完全対応
- **必須ライブラリ確認**: imbalanced-learn・optuna・matplotlib・Pillow対応
- **機能トグル設定**: config/core/features.yaml完全対応
- **trading層アーキテクチャ**: Phase 38完了（**5層分離**・core/balance/execution/position/risk）
- **システム検証**: validate_system.sh統合・Dockerfile/特徴量/戦略整合性確認（7項目）
- **MLモデル検証**: validate_model_consistency.py統合・ensemble_full.pkl/ensemble_basic.pkl検証
- **ディレクトリ構造確認**: プロジェクトルート・tax/フォルダ確認
- **品質ゲート**: 品質基準チェック・CI/CD統合・デプロイ前確認
- **レポート生成**: coverage-reports/への詳細レポート出力

**実行時間**: 約80-100秒（1,191テスト）

### **validate_system.sh**
システム整合性を検証し、開発・デプロイ段階で不整合を検出する検証スクリプトです。

**7項目チェック**:
1. **Dockerfile整合性チェック**: 必須ディレクトリ（src/config/models/tax/tests）のCOPY命令確認
2. **特徴量数検証**: feature_order.json（60特徴量）とproduction_model_metadata.json（60特徴量）の一致確認
3. **戦略整合性検証**: strategies.yaml・feature_order.json・implementations/の戦略リスト一致確認（Phase 51.5-B: 動的戦略管理対応）
4. **モジュールimport検証**: 重要モジュール（TradingOrchestrator・ExecutionService・TradeHistoryRecorder等）のimport成功確認
5. **設定ファイル整合性チェック**:
   - YAML構文チェック（unified.yaml・thresholds.yaml・features.yaml・strategies.yaml）
   - unified.yaml 必須フィールド確認（mode・risk・execution等）
   - thresholds.yaml 設定値妥当性チェック（TP/SL率・ML統合閾値 0.0-1.0範囲検証）
6. **環境変数・Secret チェック**:
   - DISCORD_WEBHOOK_URL 確認
   - BITBANK_API_KEY / BITBANK_API_SECRET 確認
   - ローカル/本番環境の適切な警告レベル
7. **モデルメタデータ整合性チェック**:
   - F1スコア妥当性チェック（0.4-0.8範囲検証）
   - 特徴量数一致確認（feature_order.json vs production_model_metadata.json）
   - モデル作成日チェック（90日以内推奨・タイムゾーン対応）
   - 訓練データサイズチェック（10,000件以上推奨）
   - モデルファイル存在・サイズ確認（ensemble_full.pkl/ensemble_basic.pkl - Phase 50.9リネーム対応）

**重要特徴**: すべてのチェックは**動的設定読み込み方式**（特徴量・戦略数の増減に自動対応・strategies.yaml対応）

**使用箇所**:
- `scripts/management/run_safe.sh`: ペーパートレード起動時自動実行
- GitHub Actions CI: Quality Check jobで自動実行
- 手動実行: 開発段階での整合性確認・デプロイ前チェック

**実行時間**: 約3-5秒（7項目軽量検証）

### **主要機能と特徴**
- **継続的品質保証**: 開発サイクルでの品質維持・回帰防止・自動化・1,191テスト100%維持
- **包括的検証**: 60特徴量システム・trading層5層アーキテクチャ・機能トグル設定・動的戦略管理の完全確認
- **システム整合性検証**: 7項目チェック（Dockerfile/特徴量/戦略/モジュール/設定ファイル/環境変数/モデルメタデータ）
- **動的設定読み込み**: すべてのチェックが設定ファイルから動的取得・特徴量・戦略数の増減に自動対応・strategies.yaml対応（Phase 51.5-B）
- **CI/CD統合**: GitHub Actions・品質ゲート・段階的デプロイ対応・週次モデル再学習統合
- **Phase 47-52対応**: バックテスト完全改修・確定申告対応・週間レポート・3戦略+60特徴量システムの全機能を品質保証

## 📝 使用方法・例

### **日常開発での品質チェック**
```bash
# 基本的な品質チェック（開発時必須）
bash scripts/testing/checks.sh

# 期待結果:
# ✅ 1,191テスト100%成功
# ✅ 68.77%カバレッジ達成（目標65%超過）
# ✅ コードスタイル準拠（flake8・black・isort）
# ✅ ML学習データ確認（17,272件・180日分15分足）
# ✅ 60特徴量Strategy-Aware ML対応
# ✅ 必須ライブラリ確認（imbalanced-learn・optuna・matplotlib・Pillow）
# ✅ 機能トグル設定確認（features.yaml）
# ✅ trading層5層分離アーキテクチャ確認
# ✅ システム検証（validate_system.sh統合）
# ✅ 約80秒で完了

# システム整合性検証
bash scripts/testing/validate_system.sh

# 期待結果:
# ✅ [1/7] Dockerfile整合性: src/config/models/tax/tests COPY確認
# ✅ [2/7] 特徴量数一致: 60特徴量（feature_order.json = production_model_metadata.json）
# ⚠️ [3/7] 戦略整合性: strategies.yaml動的読み込み対応（feature_order.json = implementations/）
# ✅ [4/7] モジュールimport成功: TradingOrchestrator・ExecutionService・TradeHistoryRecorder
# ✅ [5/7] 設定ファイル整合性: YAML構文・必須フィールド・設定値妥当性確認（strategies.yaml含む）
# ⚠️ [6/7] 環境変数・Secret: DISCORD_WEBHOOK_URL・BITBANK_API_KEY/SECRET確認
# ✅ [7/7] モデルメタデータ整合性: ensemble_full.pkl/ensemble_basic.pkl・F1スコア・特徴量数確認
# ✅ 約3-5秒で完了

# カバレッジレポート確認
open coverage-reports/htmlcov/index.html
```

### **CI/CD統合使用**
```bash
# CI前品質チェック（必須）
bash scripts/testing/checks.sh
if [ $? -eq 0 ]; then
    echo "✅ 品質チェック成功 - CI実行可能"
else
    echo "❌ 品質チェック失敗 - 修正必要"
    exit 1
fi

# GitHub Actions自動実行
# .github/workflows/ci.yml で自動実行されます
```

### **機械学習モデル管理**
```bash
# Phase 52.4版MLモデル学習（60特徴量Strategy-Aware ML）
python3 scripts/ml/create_ml_models.py

# Optunaハイパーパラメータ最適化（推奨）
python3 scripts/ml/create_ml_models.py --optimize --n-trials 50

# 期待結果:
# ✅ CSV実データ読み込み（17,272件・180日分15分足）
# ✅ 60特徴量Strategy-Aware ML（50基本+5戦略信号）
# ✅ 実戦略信号生成（訓練/推論一貫性確保）
# ✅ Look-ahead bias防止（df.iloc[:i+1]）
# ✅ 3クラス分類（閾値0.5%・SELL/HOLD/BUY）
# ✅ TimeSeriesSplit n_splits=5
# ✅ SMOTE oversampling
# ✅ Optuna TPESampler最適化
# ✅ ProductionEnsemble作成（LightGBM 40%・XGBoost 40%・RandomForest 20%）
# ✅ F1スコア: 0.56-0.61（XGBoost 0.593・RandomForest 0.614・LightGBM 0.489）

# 週次自動再学習（GitHub Actions）
# .github/workflows/model-training.yml - 毎週日曜18:00 JST自動実行
```

### **トラブルシューティング**
```bash
# テスト失敗時の詳細確認
bash scripts/testing/checks.sh 2>&1 | tee test_output.log

# システム整合性検証（Phase 49.15・7項目チェック）
bash scripts/testing/validate_system.sh

# 個別テスト実行
python3 -m pytest tests/unit/ml/ -v
python3 -m pytest tests/test_backtest/ -v  # バックテストテスト（Phase 49完全改修）
python3 -m pytest tests/test_tax/ -v       # 確定申告システムテスト

# カバレッジ確認
python3 -m pytest tests/ --cov=src --cov-report=html

# コードスタイル修正
python3 -m black src/ tests/ scripts/ tax/
python3 -m isort src/ tests/ scripts/ tax/

# ML学習データ確認（Phase 49: 17,272件・180日分）
ls -lh data/btc_jpy/15m_sample.csv
wc -l data/btc_jpy/15m_sample.csv

# 特徴量数確認（Phase 49: 60特徴量）
python3 -c "import json; print(json.load(open('config/core/feature_order.json'))['total_features'])"

# 必須ライブラリインストール
pip3 install imbalanced-learn optuna matplotlib Pillow
```

## ⚠️ 注意事項・制約

### **実行環境要件**
- **Python環境**: Python 3.13・pytest・coverage・flake8・black・isort
- **必須ライブラリ**: imbalanced-learn・optuna・matplotlib・Pillow（週間レポート・バックテスト可視化）
- **実行場所**: プロジェクトルートディレクトリからの実行必須
- **依存関係**: 全システムモジュール・機械学習ライブラリ・設定ファイル・tax/モジュール
- **権限**: テスト実行・ファイル作成・ネットワークアクセス・SQLite書き込み権限

### **品質基準**（最新状態）
- **テスト成功率**: 1,191テスト100%成功・回帰防止・継続的品質維持
- **カバレッジ基準**: 65%以上維持（68.77%達成）・新機能でのテスト追加必須
- **コードスタイル**: PEP8準拠・flake8・black・isort通過必須
- **システム整合性**: validate_system.sh検証通過必須
- **動的設定読み込み**: すべてのチェックが設定ファイルから動的取得・ハードコード値禁止・strategies.yaml対応
- **実行時間**: checks.sh約80-100秒（1,191テスト実行時間含む）・validate_system.sh約3-5秒

### **CI/CD統合制約**
- **品質ゲート**: 全チェック通過後のデプロイ実行・失敗時停止・validate_system.sh統合
- **自動実行**: GitHub Actions・CI/CD パイプライン統合・週次モデル再学習（毎週日曜18:00 JST）
- **段階的デプロイ**: 各段階での品質確認・問題時ロールバック
- **監視統合**: Discord通知・週間レポート自動送信・アラート・レポート配信

### **機械学習検証制約**（Phase 49完了）
- **データ要件**: CSV実データ（17,272件・180日分15分足）
- **60特徴量**: 50基本特徴量+5戦略信号特徴量（Strategy-Aware ML・Phase 41.8）
- **実戦略信号**: 訓練/推論一貫性確保・Look-ahead bias防止（df.iloc[:i+1]）
- **モデル品質**: TimeSeriesSplit n_splits=5・SMOTE・Optuna TPESampler最適化
- **F1スコア基準**: 0.56-0.61（XGBoost 0.593・RandomForest 0.614・LightGBM 0.489）
- **リソース制限**: メモリ使用量・計算時間・ストレージ容量管理
- **バージョン管理**: モデル保存・メタデータ・履歴追跡・週次自動再学習・models/archive/自動バックアップ

## 🔗 関連ファイル・依存関係

### **テスト・品質保証システム**
- `tests/`: 単体テスト・統合テスト・機械学習テスト・全テストスイート
- `coverage-reports/`: カバレッジレポート・HTML・JSON・統計データ
- `logs/reports/ci_checks/`: 品質チェックレポート・履歴・分析データ

### **機械学習システム**（Phase 49完了）
- `src/features/feature_generator.py`: 特徴量生成・60特徴量管理（50基本+5戦略信号）
- `src/ml/ensemble.py`: ProductionEnsemble・3モデル統合（LightGBM 40%・XGBoost 40%・RandomForest 20%）
- `models/production/`: 本番モデル（Phase 49完了・Strategy-Aware ML・Optuna最適化済み）
- `models/production/production_ensemble.pkl`: アンサンブルモデル（60特徴量対応）
- `models/production/production_model_metadata.json`: モデルメタデータ（F1スコア・特徴量数等）
- `models/archive/`: モデルバックアップ（週次自動更新前の旧モデル保管）
- `scripts/ml/create_ml_models.py`: モデル学習・Phase 52.4版（Strategy-Aware ML実装）

### **バックテスト・税務システム**（Phase 47-49実装）
- `src/backtest/engine.py`: バックテストエンジン（Phase 49完全改修・戦略シグナル事前計算）
- `src/backtest/trade_tracker.py`: TradeTracker（Phase 46実装・エントリー/エグジットペアリング）
- `src/backtest/visualizer.py`: matplotlib可視化（Phase 47-49実装・4種類グラフ）
- `tax/trade_history_recorder.py`: 取引履歴記録（Phase 47実装・SQLite）
- `tax/pnl_calculator.py`: 損益計算エンジン（Phase 47実装・移動平均法）
- `tax/trade_history.db`: 取引履歴データベース（Phase 47実装）

### **設定・環境管理**
- `config/core/unified.yaml`: 統一設定ファイル（全環境対応・5戦略設定）
- `config/core/thresholds.yaml`: 動的閾値・ML統合設定・TP/SL設定（Phase 42.4最適化）
- `config/core/features.yaml`: 機能トグル設定（Phase 31.1・7カテゴリー~50機能）
- `config/core/feature_order.json`: 60特徴量順序定義（Phase 41.8・50基本+5戦略信号）
- `.flake8`: コードスタイル設定・品質基準・除外ルール
- `pyproject.toml`: プロジェクト設定・依存関係・ツール設定
- `Dockerfile`: コンテナ化・tax/モジュール統合（Phase 49.13修正）

### **CI/CD・デプロイシステム**
- `.github/workflows/ci.yml`: CI/CDパイプライン・自動テスト・品質ゲート・validate_system.sh統合
- `.github/workflows/model-training.yml`: 週次モデル再学習（毎週日曜18:00 JST・Optuna最適化）
- `.github/workflows/weekly_report.yml`: 週間レポート自動送信（Phase 48・毎週月曜9:00 JST）
- `scripts/deployment/`: デプロイメント・Cloud Run・本番環境統合
- `scripts/deployment/docker-entrypoint.sh`: Dockerコンテナエントリーポイント・ヘルスチェック
- `src/monitoring/discord_notifier.py`: 通知・アラート・レポート送信
- `src/core/reporting/`: 週間レポート生成（Phase 48・損益曲線グラフ・matplotlib）

### **外部システム統合**
- **GitHub Actions**: CI/CDパイプライン・自動テスト・品質ゲート・週次モデル再学習・週間レポート自動送信
- **GCP Cloud Run**: 本番環境（asia-northeast1）・1Gi・1CPU・月額700-900円
- **Discord API**: 3階層通知（Critical/Warning/Info）・週間レポート配信（Phase 48・通知99%削減）
- **Bitbank API**: BTC/JPY信用取引・市場データ取得・取引履歴記録

### **品質管理ツール**（Phase 49完了）
- **pytest**: テストフレームワーク・1,191テスト・単体/統合テスト
- **coverage**: カバレッジ測定（68.32%達成）・HTML/JSON出力
- **flake8**: コードスタイル・PEP8準拠・品質チェック
- **black・isort**: コード整形・インポート整理・一貫性確保
- **imbalanced-learn**: SMOTE oversampling（Phase 39.4）
- **optuna**: TPESamplerハイパーパラメータ最適化（Phase 39.5）
- **matplotlib・Pillow**: グラフ生成・週間レポート・バックテスト可視化
- **validate_system.sh**: システム整合性検証（Phase 49.15・7項目チェック・動的設定読み込み方式）

---

**🎯 最新状態時点の重要事項**:
- ✅ **1,191テスト100%成功・68.77%カバレッジ達成**（+74テスト） - 企業級品質保証
- ✅ **60特徴量システム完全対応** - 49基本+3戦略+7時間+1シグナル・訓練/推論一貫性
- ✅ **バックテスト完全改修** - TradeTracker・matplotlib可視化・信頼性100%達成
- ✅ **確定申告対応システム** - SQLite取引記録・移動平均法損益計算・作業時間95%削減
- ✅ **週間レポート実装** - Discord自動送信・損益曲線グラフ・通知99%削減
- ✅ **システム整合性検証7項目** - validate_system.sh Phase 52.4版（strategies.yaml対応・ensemble_full.pkl/ensemble_basic.pkl対応）
- ✅ **動的戦略管理基盤**（Phase 51.5-B） - Registry Pattern・影響範囲93%削減・strategies.yaml統合
- ✅ **fix_*.py削除** - Phase 52.3使い捨てスクリプト4ファイル・444行削減・保守性向上

**推奨運用方法**:
1. **開発前後**: `bash scripts/testing/checks.sh` で品質確認（必須・約80秒）
2. **デプロイ前チェック**: `bash scripts/testing/validate_system.sh` で7項目整合性確認（推奨・約3-5秒）
3. **CI/CD統合**: GitHub Actions自動品質ゲート・週次モデル再学習・週間レポート自動送信
4. **本番デプロイ**: 品質チェック+整合性検証通過後の段階的デプロイ・監視統合・ロールバック対応