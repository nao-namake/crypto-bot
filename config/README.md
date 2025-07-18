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

**現在使用中の本番設定**

### `bitbank_config.yml`
- **用途**: 現在稼働中のライブトレード設定
- **特徴**: 軽量設定（INIT-5ハング問題解決版）
- **ML特徴量**: 基本3特徴量（RSI・MACD・SMA）
- **データ制限**: 100件取得・外部データ一時無効化
- **状況**: ✅ **現在稼働中** - `=== Bitbank Live Trading Started ===`

## 🔧 開発環境設定 (`development/`)

**開発・テスト用設定**

### `bitbank_config.yml`
- **用途**: ローカル開発・検証用設定
- **特徴**: production設定のコピー（必要に応じて調整可能）
- **使用場面**: 新機能テスト・デバッグ作業

## 🧪 検証・実験用設定 (`validation/`)

**将来的な機能拡張・研究用設定**

### `api_versions.json`
- **用途**: 各取引所APIのバージョン管理情報
- **対象**: Bybit・Bitbank・Bitflyer・OKCoinJP
- **価値**: 複数取引所対応時の参考資料

### `bitbank_101features_csv_backtest.yml`
- **用途**: CSV高速バックテスト専用設定
- **特徴**: 101特徴量フル対応・1年間バックテスト
- **ML手法**: アンサンブル学習・Optuna最適化
- **使用場面**: フル機能復旧後の性能検証

### `bitbank_production_jpy_realistic.yml`
- **用途**: JPY建て本番運用向け詳細設定
- **特徴**: 90特徴量対応・50万円想定・現実的パラメータ
- **期待効果**: 年間18-22%リターン（75-78%勝率）
- **使用場面**: 外部データ復旧後の本番移行

### `default.yml`
- **用途**: システム標準設定・参考用
- **特徴**: 59特徴量対応・詳細設定例
- **価値**: 新規設定作成時のベースライン

### `ensemble_trading.yml`
- **用途**: アンサンブル学習専用設定
- **特徴**: 取引特化型アンサンブル・101特徴量
- **手法**: trading_stacking・動的閾値最適化
- **使用場面**: アンサンブル学習本格導入時

## 🔄 設定ファイル使用方法

### 現在の本番稼働
```bash
# 本番用設定で稼働中（自動実行）
python scripts/start_live_with_api_fixed.py
# → production/bitbank_config.yml を使用
```

### 開発・テスト用
```bash
# 開発用設定でテスト
python -m crypto_bot.main train --config config/development/bitbank_config.yml
```

### 検証用設定の活用
```bash
# CSV高速バックテスト
python -m crypto_bot.main backtest --config config/validation/bitbank_101features_csv_backtest.yml

# アンサンブル学習テスト
python -m crypto_bot.main train --config config/validation/ensemble_trading.yml

# JPY建て詳細バックテスト
python -m crypto_bot.main backtest --config config/validation/bitbank_production_jpy_realistic.yml
```

## 📋 今後の展開計画

### Phase 1: 外部データ復旧
- VIX・Macro・Fear&Greed データ復旧後
- `validation/bitbank_production_jpy_realistic.yml` → `production/` 移行

### Phase 2: アンサンブル学習導入
- A/Bテスト実行・統計的検証完了後
- `validation/ensemble_trading.yml` → `production/` 移行

### Phase 3: 101特徴量フル活用
- 全外部データ安定稼働確認後
- `validation/bitbank_101features_csv_backtest.yml` 知見を production 反映

## ⚠️ 重要事項

### 設定変更時の注意
1. **production設定**: 本番稼働中のため慎重に変更
2. **development設定**: テスト用なので自由に変更可能
3. **validation設定**: 将来用なので保存目的で変更避ける

### ファイル管理原則
- **追加**: 新規用途は適切なフォルダに配置
- **削除**: 使用中設定の削除厳禁
- **移動**: production↔development間での移動は慎重に

---

*設定ファイル構造は2025年7月17日に整理・最適化されました*