# crypto_bot モジュール構造

このディレクトリには、暗号通貨自動取引ボットのコアモジュールが含まれています。

## 📁 ディレクトリ構造

```
crypto_bot/
├── __init__.py          # パッケージ初期化
├── main.py             # メインエントリーポイント（簡略版）
├── main_old.py         # 旧メインファイル（移行中）
├── config.py           # 設定管理
│
├── api/                # API関連
│   ├── __init__.py
│   ├── health.py       # ヘルスチェックAPI
│   └── server.py       # APIサーバー
│
├── backtest/           # バックテスト関連
│   ├── __init__.py
│   ├── engine.py       # バックテストエンジン
│   └── reporter.py     # レポート生成
│
├── cli/                # CLIコマンド（Phase 14.2で新規作成）
│   ├── __init__.py
│   ├── backtest.py     # バックテストコマンド
│   ├── live.py         # ライブトレードコマンド（統合版）
│   ├── online.py       # オンライン学習コマンド
│   ├── optimize.py     # 最適化コマンド
│   ├── strategy.py     # 戦略情報コマンド
│   └── train.py        # 学習コマンド
│
├── data/               # データ取得・処理
│   ├── __init__.py
│   ├── fetcher.py      # マーケットデータ取得
│   └── yahoo_fetcher.py # Yahoo Finance統合
│
├── execution/          # 取引実行
│   ├── __init__.py
│   ├── bitbank.py      # Bitbank取引所クライアント
│   ├── engine.py       # 取引実行エンジン
│   └── factory.py      # 取引所クライアントファクトリー
│
├── ml/                 # 機械学習関連
│   ├── __init__.py
│   ├── ensemble.py     # アンサンブル学習
│   ├── feature_engines/ # 特徴量エンジン
│   ├── feature_master_implementation.py # 97特徴量完全実装
│   ├── preprocessor.py # 前処理
│   └── trainer.py      # モデル学習
│
├── risk/               # リスク管理
│   ├── __init__.py
│   └── manager.py      # リスクマネージャー
│
├── scripts/            # スクリプト（移行対象）
│   └── walk_forward.py # ウォークフォワード分析
│
├── strategy/           # 取引戦略
│   ├── __init__.py
│   ├── factory.py      # 戦略ファクトリー
│   ├── ml_strategy.py  # ML戦略
│   └── multi_timeframe_ensemble_strategy.py # マルチタイムフレーム戦略
│
└── utils/              # ユーティリティ（Phase 14.2で新規作成）
    ├── __init__.py
    ├── chart.py        # チャート生成
    ├── config_state.py # 設定状態管理
    ├── data.py         # データ準備
    ├── file.py         # ファイル操作
    ├── model.py        # モデル保存・読込
    ├── pre_computed_cache.py # 事前計算キャッシュ
    └── trading_integration_service.py # 統計システム統合
```

## 🚀 Phase 14リファクタリング概要

### Phase 14.1: 緊急修正（完了）
- INIT-PREFETCHコードブロック削除（8時間取引停止問題解決）
- UnboundLocalError修正（Position変数スコープ問題）

### Phase 14.2: モジュール分離（進行中）
- **main.py**: 2,765行 → 90行に削減
- **cli/**: CLIコマンドを独立モジュールに分離
- **utils/**: ユーティリティ関数を整理
- **live-bitbank統合**: --simpleフラグで通常版/シンプル版切り替え

## 🎯 主要機能

### 1. ライブトレード
```bash
# 通常版（統計システム・詳細ログあり）
python -m crypto_bot.main live-bitbank --config config/production/production.yml

# シンプル版（軽量・最小限の初期化）
python -m crypto_bot.main live-bitbank --config config/production/production.yml --simple
```

### 2. バックテスト
```bash
python -m crypto_bot.main backtest --config config/validation/unified_97_features_backtest.yml
```

### 3. モデル学習
```bash
python -m crypto_bot.main train --config config/production/production.yml
```

## 📊 97特徴量システム

- **OHLCV**: 5特徴量（基本価格データ）
- **extra_features**: 92特徴量（テクニカル指標）
- **合計**: 97特徴量

## 🔧 設定

設定ファイルは`config/`ディレクトリで管理：
- `production/production.yml`: 本番用設定
- `validation/`: 検証用設定

## 📝 注意事項

- Phase 14.1でINIT-5以降のプリフェッチ処理を削除
- INIT-1〜4は基本的な初期化として維持
- 統計システムは通常版のみで動作（--simpleでは無効）