# tests/unit/ - 単体テストシステム（Phase 61更新）

## 役割・責任

システム全体の単体テストを管理し、コード品質の保証、回帰防止、継続的品質向上を支援します。機械学習モデル、取引戦略、データ処理、監視システムまで、包括的なテストカバレッジでシステムの信頼性を確保します。

## テスト統計（Phase 61時点）

| カテゴリ | テスト数 | 状態 |
|---------|---------|------|
| core/ | 167 | passed |
| data/ | 67 | passed |
| features/ | 21 | passed |
| ml/ | 168 | passed (1 skipped) |
| monitoring/ | 28 | passed |
| services/ | 57 | passed |
| strategies/ | 261 | passed |
| trading/ | 437 | passed (1 xfailed) |
| **合計** | **約1,200** | **全成功** |

## ディレクトリ構成

```
tests/unit/
├── README.md                    # このファイル
├── core/                        # コアシステムテスト（167テスト）
│   ├── services/                   # コアサービステスト
│   │   ├── test_health_checker.py
│   │   └── test_trading_logger.py
│   ├── test_config_thresholds.py
│   └── test_ml_adapter_exception_handling.py
├── data/                        # データ層テスト（67テスト）
│   ├── test_bitbank_client.py
│   ├── test_data_cache.py
│   └── ...
├── features/                    # 特徴量システムテスト（21テスト）
│   └── test_feature_generator.py    # 55特徴量対応
├── ml/                          # 機械学習システムテスト（168テスト）
│   ├── models/                     # 個別モデルテスト
│   │   ├── test_lgb_model.py
│   │   ├── test_rf_model.py
│   │   └── test_xgb_model.py
│   ├── production/                 # 本番モデルテスト
│   │   └── test_ensemble.py
│   ├── test_ensemble_model.py
│   ├── test_ml_integration.py
│   ├── test_model_manager.py
│   └── test_voting_system.py
├── monitoring/                  # 監視システムテスト（28テスト）
│   └── test_discord_client.py
├── services/                    # サービステスト（57テスト）
│   ├── test_dynamic_strategy_selector.py
│   ├── test_execution_service.py
│   ├── test_market_regime_classifier.py
│   └── test_regime_types.py
├── strategies/                  # 取引戦略システムテスト（261テスト）
│   ├── base/
│   │   └── test_strategy_base.py
│   ├── implementations/           # 6戦略実装テスト
│   │   ├── test_atr_based.py
│   │   ├── test_bb_reversal.py
│   │   ├── test_donchian_channel.py
│   │   └── ...
│   ├── utils/
│   │   ├── test_constants.py
│   │   ├── test_risk_manager.py
│   │   └── test_signal_builder.py
│   └── test_strategy_manager.py
└── trading/                     # 取引システムテスト（437テスト）
    ├── balance/
    │   └── test_margin_monitor.py
    ├── execution/
    │   ├── test_executor.py
    │   ├── test_order_strategy.py
    │   └── test_stop_manager.py
    ├── position/
    │   ├── test_cooldown.py
    │   ├── test_limits.py
    │   └── test_tracker.py
    ├── test_anomaly_detector.py
    ├── test_drawdown_manager.py
    ├── test_integrated_risk_manager.py
    └── test_kelly_criterion.py
```

## 主要テストカテゴリ

### ml/ - 機械学習システムテスト
- **個別モデルテスト**: LightGBM・XGBoost・RandomForest
- **ProductionEnsemble**: 3モデル統合・重み付け平均
- **統合テスト**: 特徴量→モデル→予測のパイプライン

### strategies/ - 取引戦略システムテスト
6つの取引戦略の動作確認:
- レンジ型: BBReversal, StochasticReversal, ATRBased, DonchianChannel
- トレンド型: MACDEMACrossover, ADXTrendStrength

### trading/ - 取引システムテスト
- **取引実行**: ExecutionService・OrderStrategy
- **リスク管理**: Kelly基準・ポジションサイジング・統合リスク評価
- **異常検知**: 市場異常・システム異常・アラート
- **ドローダウン管理**: 損失制限・クールダウン

### services/ - サービステスト
- **MarketRegimeClassifier**: レジーム判定（tight_range/normal_range/trending/high_volatility）
- **DynamicStrategySelector**: レジーム別戦略選択

## 使用方法

### 全テスト実行
```bash
# 全単体テスト実行
python -m pytest tests/unit/ -v --tb=short

# カバレッジ付き実行
python -m pytest tests/unit/ --cov=src --cov-report=term-missing

# 品質チェック統合実行
bash scripts/testing/checks.sh
```

### カテゴリ別テスト実行
```bash
# 機械学習テスト
python -m pytest tests/unit/ml/ -v

# 取引戦略テスト
python -m pytest tests/unit/strategies/ -v

# 取引システムテスト
python -m pytest tests/unit/trading/ -v

# サービステスト
python -m pytest tests/unit/services/ -v
```

## 注意事項

### テスト品質基準
- **成功率**: 全テスト100%成功維持
- **カバレッジ**: 64%以上維持
- **CI/CD**: GitHub Actions自動品質ゲート

### モック戦略
- **外部API**: Bitbank API・Discord Webhook 完全モック化
- **機械学習**: ProductionEnsemble軽量版使用
- **時間依存**: 固定datetime・タイムゾーン一貫性

### 特記事項
- `tests/unit/ml/`: 1件のスキップ（GPU非対応環境でのGPUテスト）
- `tests/unit/trading/`: 1件のxfail（トレンド強度計算の期待値調整待ち）

## 関連ファイル

| ファイル | 役割 |
|---------|------|
| `pytest.ini` | pytest設定 |
| `conftest.py` | フィクスチャ・モック |
| `scripts/testing/checks.sh` | 品質チェックスクリプト |

---

**最終更新**: 2026年1月24日（Phase 61: テスト整理完了）
