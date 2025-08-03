# 設定ファイル構造ガイド

このディレクトリは環境別・用途別に整理された設定ファイルを管理します。

## 📁 ディレクトリ構造

```
config/
├── production/         # 本番環境用設定
├── development/        # 開発環境用設定
├── validation/         # 検証・実験用設定
└── README.md          # このファイル
```

## 🚀 本番環境設定 (`production/`)

**97特徴量最適化システム本番設定**

### ✅ `production.yml` - **現在の本番設定**
- **ML特徴量**: 97特徴量最適化システム（30重複特徴量削除版）
- **外部データ**: 一時無効化（安定性重視）
- **取引設定**: Bitbank信用取引・¥10,000スタート・レバレッジ1倍
- **GCP対応**: Cloud Run・Docker環境完全対応
- **品質監視**: 緊急停止・データ品質管理・エラー耐性システム

### `production_lite.yml` - **軽量版**
- **用途**: 高速起動・テスト用軽量設定
- **特徴**: 最小限設定・デバッグ時使用

## 🔧 開発環境設定 (`development/`)

**開発・テスト用設定**

### `bitbank_config.yml`
- **用途**: ローカル開発・検証用設定
- **特徴**: production設定のコピー（必要に応じて調整可能）
- **使用場面**: 新機能テスト・デバッグ作業

## 🧪 検証・バックテスト用設定 (`validation/`)

**GCP環境対応・本番昇格候補設定**

### 🎯 **97特徴量バックテスト設定**
- **`unified_97_features_backtest.yml`**: 97特徴量最適化システム検証用
- **`production_97_backtest.yml`**: 本番97特徴量設定のバックテスト版
- **GCP環境整合**: production.ymlと設定構造完全一致

### 📊 **比較検証用設定**
- **`unified_127_features_backtest.yml`**: 127特徴量比較用（効率化効果測定）
- **`bitbank_125features_production_backtest.yml`**: 125特徴量版検証
- **`bitbank_124features_production_backtest.yml`**: 124特徴量版検証

### ⚡ **高速バックテスト設定**
- **`bitbank_101features_csv_backtest.yml`**: CSV高速バックテスト・1年間
- **`fast_production_validation_backtest.yml`**: 本番設定高速検証
- **`quick_profit_test.yml`**: 収益性迅速検証

### 🎛️ **最適化・実験用設定**
- **`ensemble_trading.yml`**: アンサンブル学習専用・trading_stacking
- **`bitbank_optimized_045_threshold.yml`**: 閾値最適化版
- **`profitable_validation_backtest.yml`**: 収益性重視設定
- **`robust_model_backtest.yml`**: 堅牢性検証設定

### 📋 **参考・管理用**
- **`api_versions.json`**: 各取引所APIバージョン管理
- **`default.yml`**: システム標準設定・新規作成時ベースライン

## 🔄 設定ファイル使用方法

### 🚀 本番稼働（97特徴量最適化システム）
```bash
# 97特徴量本番設定での稼働
python -m crypto_bot.main live-bitbank --config config/production/production.yml

# GCP Cloud Run自動デプロイ
gcloud run deploy crypto-bot-service-prod --source . --region=asia-northeast1
```

### 🧪 バックテスト・検証（昇格候補テスト）
```bash
# 97特徴量バックテスト（本番昇格前検証）
python -m crypto_bot.main backtest --config config/validation/unified_97_features_backtest.yml

# 効率化効果比較（127 vs 97特徴量）
python -m crypto_bot.main backtest --config config/validation/unified_127_features_backtest.yml

# 高速収益性検証
python -m crypto_bot.main backtest --config config/validation/quick_profit_test.yml

# アンサンブル学習検証
python -m crypto_bot.main backtest --config config/validation/ensemble_trading.yml
```

### 🔧 開発・ローカルテスト
```bash
# 開発用設定でテスト
python -m crypto_bot.main live-bitbank --config config/development/bitbank_config.yml

# 軽量版でのテスト
python -m crypto_bot.main live-bitbank --config config/production/production_lite.yml
```

## 📋 設定昇格ワークフロー・今後の展開

### 🎯 **設定昇格フロー（バックテスト→本番）**
1. **検証フェーズ**: `validation/`で新設定のバックテスト実行
2. **性能評価**: 収益性・勝率・シャープレシオを既存本番設定と比較
3. **昇格判定**: 優秀な結果確認後、`production/`にコピー・適用
4. **本番移行**: GCP環境でのデプロイ・実稼働開始

### 🚀 **Phase 4: 97特徴量システム本格運用**
- ✅ **97特徴量モデル検証**: `models/validation/`の新モデルをバックテスト
- 🔄 **最適モデル昇格**: 最高性能モデルを`models/production/model.pkl`に昇格
- 🔄 **効率化効果実測**: 127→97特徴量の24%効率向上確認

### 🔮 **Phase 5: 拡張機能統合**
- **外部データ復旧**: VIX・Macro・Fear&Greed統合・外部データ有効化
- **アンサンブル学習強化**: `ensemble_trading.yml`本番統合
- **複数通貨ペア対応**: ETH/JPY・XRP/JPY拡張・ポートフォリオ分散

## ⚠️ 重要事項

### 🔐 **設定変更時の注意**
1. **production設定**: GCP本番稼働中・変更は慎重に・必ずバックアップ作成
2. **validation設定**: バックテスト検証用・昇格候補管理・自由に実験可能
3. **development設定**: ローカル開発用・自由に変更・実験用途

### 🎯 **GCP環境整合性**
- **production.yml**: GCP Cloud Run環境完全対応・Docker最適化済み
- **validation/**: 本番環境と設定構造一致・昇格時の整合性確保
- **GCP変数**: `${BITBANK_API_KEY}`・`${BITBANK_API_SECRET}`環境変数対応

### 📁 **ファイル管理原則**
- **追加**: 新規バックテスト設定は`validation/`に配置
- **昇格**: 優秀な結果の設定を`production/`にコピー
- **削除**: 本番稼働中設定の削除厳禁・validation/は実験自由
- **バックアップ**: 本番設定変更前は必ずバックアップ作成

---

*97特徴量最適化システム対応・GCP環境整合・昇格ワークフロー確立（2025年8月2日更新）*