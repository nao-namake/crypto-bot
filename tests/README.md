# tests/ - 暗号通貨自動取引システムテストスイート

## 📋 概要

**Cryptocurrency Trading Bot Test Suite**  
crypto-bot プロジェクトの包括的なテストスイートです。ユニットテスト、統合テスト、エンドツーエンドテストを通じて、システムの品質と信頼性を保証します。

## 🎯 テスト構造

```
tests/
├── unit/                   # ユニットテスト（モジュール単位）
│   ├── backtest/          # バックテストエンジン（4ファイル）
│   ├── data/              # データ取得・処理（2ファイル）
│   ├── drift_detection/   # ドリフト検出（3ファイル）
│   ├── execution/         # 取引実行（8ファイル）
│   ├── ha/                # 高可用性（1ファイル）
│   ├── indicator/         # テクニカル指標（1ファイル）
│   ├── main/              # メイン機能（2ファイル）
│   ├── ml/                # 機械学習（6ファイル）
│   ├── online_learning/   # オンライン学習（4ファイル）
│   ├── risk/              # リスク管理（1ファイル）
│   ├── scripts/           # スクリプト（3ファイル）
│   ├── strategy/          # 取引戦略（10ファイル）
│   └── utils/             # ユーティリティ（2ファイル）
├── integration/            # 統合テスト
│   ├── bitbank/           # Bitbank統合（1ファイル）
│   ├── bitFlyer/          # bitFlyer統合（1ファイル）
│   ├── bybit/             # Bybit統合（1ファイル）
│   ├── main/              # メイン統合（1ファイル）
│   └── okcoinjp/          # OKCoinJP統合（1ファイル）
└── deprecated/             # 不要・古いテスト（整理済み）
```

## 📊 テスト統計

- **総テスト数**: 約694個のテスト関数
- **ユニットテスト**: 45ファイル
- **統合テスト**: 7ファイル
- **カバレッジ目標**: 33%以上（CI/CD設定）

## 🧪 ユニットテスト詳細

### **backtest/** - バックテストエンジン
- `test_analysis.py` - バックテスト分析機能
- `test_engine.py` - バックテストエンジン本体
- `test_metrics.py` - パフォーマンス指標計算
- `test_optimizer.py` - パラメータ最適化

### **data/** - データ取得・処理
- `test_fetcher.py` - マーケットデータ取得
- `test_streamer.py` - リアルタイムストリーミング

### **drift_detection/** - ドリフト検出
- `test_detectors.py` - ドリフト検出アルゴリズム
- `test_ensemble.py` - アンサンブルドリフト検出
- `test_monitor.py` - ドリフト監視

### **execution/** - 取引実行
- `test_execution_base.py` - 基底クラステスト
- `test_execution_engine.py` - 実行エンジン
- `test_factory.py` - ファクトリーパターン
- `test_bitbank_client.py` - Bitbankクライアント
- `test_bitbank_margin.py` - Bitbank信用取引
- `test_bitflyer_client.py` - bitFlyerクライアント
- `test_bybit_client.py` - Bybitクライアント
- `test_okcoinjp_client.py` - OKCoinJPクライアント

### **ha/** - 高可用性
- `test_state_manager.py` - 状態管理

### **indicator/** - テクニカル指標
- `test_calculator.py` - 指標計算

### **main/** - メイン機能
- `test_main_cli.py` - CLIコマンドテスト
- `test_main_train.py` - 学習コマンドテスト

### **ml/** - 機械学習
- `test_model.py` - MLモデルラッパー
- `test_preprocessor.py` - 前処理パイプライン
- `test_ensemble.py` - アンサンブル学習
- `test_ml_optimizer.py` - ML最適化
- `test_target.py` - ターゲット生成
- `test_feature_consistency.py` - 特徴量一貫性検証

### **online_learning/** - オンライン学習
- `test_base.py` - 基底クラス
- `test_models.py` - オンライン学習モデル
- `test_monitoring.py` - 学習監視
- `test_scheduler.py` - スケジューラー

### **risk/** - リスク管理
- `test_manager.py` - リスク管理システム

### **scripts/** - スクリプト
- `test_plot_equity.py` - エクイティカーブ描画
- `test_walk_forward.py` - ウォークフォワード分析
- `test_walk_forward_extra.py` - 拡張ウォークフォワード

### **strategy/** - 取引戦略
- `test_base.py` - 基底戦略クラス
- `test_simple_ma.py` - 移動平均戦略
- `test_ml_strategy.py` - ML戦略
- `test_ensemble_ml_strategy.py` - アンサンブルML戦略
- `test_multi_timeframe_ensemble.py` - マルチタイムフレーム
- `test_composite.py` - 複合戦略
- `test_registry.py` - 戦略レジストリ
- `test_strategy_factory.py` - 戦略ファクトリー
- `test_bitbank_btc_jpy_strategy.py` - Bitbank BTC/JPY戦略
- `test_bitbank_xrp_jpy_strategy.py` - Bitbank XRP/JPY戦略

### **utils/** - ユーティリティ
- `test_config_validator.py` - 設定検証
- `test_status.py` - ステータス管理

## 🔄 統合テスト詳細

### **取引所別統合テスト**
- `bitbank/test_bitbank_e2e.py` - Bitbankエンドツーエンド
- `bitFlyer/test_bitflyer_e2e_real.py` - bitFlyer実環境テスト
- `bybit/test_bybit_e2e.py` - Bybitエンドツーエンド
- `okcoinjp/test_okcoinjp_e2e_real.py` - OKCoinJP実環境テスト

### **システム統合テスト**
- `main/test_main_e2e.py` - メインシステムE2E
- `test_bitbank_fee_optimization_integration.py` - 手数料最適化
- `test_multi_exchange_flow.py` - マルチ取引所フロー

## 🚀 テスト実行方法

### **全テスト実行**
```bash
# 品質チェックと全テスト実行
bash scripts/checks.sh

# pytestで全テスト実行
python -m pytest tests/
```

### **ユニットテストのみ**
```bash
# ユニットテストのみ実行
python -m pytest tests/unit/

# 特定モジュールのテスト
python -m pytest tests/unit/ml/
python -m pytest tests/unit/strategy/
```

### **統合テストのみ**
```bash
# 統合テストのみ実行
python -m pytest tests/integration/

# 特定の取引所テスト
python -m pytest tests/integration/bitbank/
```

### **カバレッジ測定**
```bash
# カバレッジレポート生成
python -m pytest --cov=crypto_bot --cov-report=html tests/

# カバレッジ閾値チェック（CI/CD用）
python -m pytest --cov=crypto_bot --cov-fail-under=33 tests/
```

### **特定のテスト実行**
```bash
# 特定のテストファイル
python -m pytest tests/unit/ml/test_ensemble.py

# 特定のテスト関数
python -m pytest tests/unit/ml/test_ensemble.py::TestEnsemble::test_predict

# キーワードでフィルタ
python -m pytest -k "ensemble" tests/
```

## ⚠️ 注意事項

### **テスト作成ガイドライン**
1. **命名規則**: `test_*.py`または`*_test.py`
2. **配置場所**: 対応するモジュールと同じ構造
3. **モック使用**: 外部依存は必ずモック化
4. **独立性**: 各テストは独立して実行可能に

### **除外されているテスト**
- `tests/unit/test_monitor.py` - Streamlitモジュール依存（checks.shで除外）
- `tests/integration/` - CI環境では一部スキップ

### **テスト環境**
- **Python**: 3.9以上
- **依存関係**: `requirements-dev.txt`から自動インストール
- **CI/CD**: GitHub Actionsで自動実行

### **整理による効果**
- **構造明確化**: モジュール別に整理
- **不要ファイル削除**: Phase関連の古いテスト削除
- **配置最適化**: test_feature_consistency.pyを適切な場所へ
- **保守性向上**: 明確な命名と配置

## 📝 今後の追加ガイドライン

1. **新規テスト追加時**
   - 対応するモジュールと同じディレクトリ構造に配置
   - docstringでテストの目的を明記
   - 外部依存はモック化

2. **テスト修正時**
   - 関連するすべてのテストを確認
   - カバレッジが低下しないよう注意

3. **統合テスト追加時**
   - 実環境依存を最小限に
   - CI環境でも動作するよう設計

---

*Tests構造は2025年8月7日に整理・最適化されました*