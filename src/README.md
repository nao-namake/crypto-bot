# src/ - システム実装ディレクトリ

**Phase 11完了**: システムの核心機能を実装するメインディレクトリです。レイヤードアーキテクチャに基づいて設計され、段階的開発により品質保証されています（399テスト・99.7%合格・CI/CD統合・24時間監視・段階的デプロイ対応）。

## 📁 ディレクトリ構成

```
src/
├── core/              # 基盤システム ✅ Phase 11統合完了
│   ├── config.py      # 設定管理（環境変数・YAML統合・CI/CD対応）
│   ├── logger.py      # ログシステム（Discord通知統合・24時間監視）
│   └── exceptions.py  # カスタム例外・階層化エラー処理・GitHub Actions対応
├── data/              # データ層 ✅ Phase 2完了
│   ├── bitbank_client.py  # Bitbank API（ccxt・信用取引専用）
│   ├── data_pipeline.py   # マルチタイムフレーム（15m/1h/4h）
│   └── data_cache.py      # キャッシング（LRU+ディスク・3ヶ月保存）
├── features/          # 特徴量エンジニアリング ✅ Phase 3完了
│   ├── technical.py   # テクニカル指標（12個厳選・47%削減）
│   └── anomaly.py     # 異常検知（Zスコア・56%削減）
├── strategies/        # 取引戦略システム ✅ Phase 3-4完了
│   ├── base/          # 戦略基盤システム
│   │   ├── strategy_base.py     # 抽象基底クラス
│   │   └── strategy_manager.py  # 戦略統合管理
│   ├── implementations/  # 戦略実装群
│   │   ├── atr_based.py           # ATRベース戦略（38%削減）
│   │   ├── mochipoy_alert.py      # もちぽよアラート（49%削減）
│   │   ├── multi_timeframe.py     # マルチタイムフレーム（53%削減）
│   │   └── fibonacci_retracement.py # フィボナッチ戦略（31%削減）
│   └── utils/         # 共通処理モジュール
│       ├── constants.py     # 定数・型システム
│       ├── risk_manager.py  # リスク管理計算
│       └── signal_builder.py # シグナル生成統合
├── ml/                # 機械学習層 ✅ Phase 5完了
│   ├── models/        # 個別モデル（LightGBM・XGBoost・RandomForest）
│   ├── ensemble/      # アンサンブル統合・重み付け投票・モデル管理
│   └── __init__.py    # ML層統合インターフェース
├── backtest/          # バックテストシステム ✅ Phase 8完了
│   ├── engine.py      # バックテストエンジン・ポジション管理
│   ├── evaluator.py   # 統計指標・パフォーマンス評価
│   ├── data_loader.py # データローダー・品質管理
│   ├── reporter.py    # レポート生成・多形式出力
│   ├── data/          # 履歴データ・キャッシュ
│   └── models/        # バックテスト専用モデル
├── trading/           # 取引実行層 ✅ Phase 11完了
│   ├── executor.py    # 注文実行ロジック・レイテンシー最適化・CI/CD統合
│   ├── risk.py        # Kelly基準・ドローダウン管理・24時間監視
│   ├── position_sizing.py # ポジションサイジング・動的調整・段階的デプロイ対応
│   ├── anomaly_detector.py # 取引異常検知・スプレッド監視・GitHub Actions対応
│   └── drawdown_manager.py # ドローダウン制御・自動停止・監視統合
└── monitoring/        # 監視層 ✅ Phase 1完了
    └── discord.py     # Discord通知（Critical/Warning/Info）
```

## 🎯 設計原則

### レイヤードアーキテクチャ
- **データ層**: 市場データの取得・保存・管理
- **ビジネスロジック層**: 戦略実行・シグナル生成・リスク管理
- **API層**: 取引所との通信・注文実行

### 信用取引特化
- **Bitbank信用取引**（レバレッジ1.0-2.0倍）に特化
- **ロング・ショート**両対応
- **必要最小限**の機能に絞った実装

## 📂 Phase別実装状況

### ✅ Phase 1: 基盤システム (core/ + monitoring/)
- **config.py**: 環境変数・YAML統合・設定検証
- **logger.py**: 構造化ログ・Discord通知・日次ローテーション
- **exceptions.py**: 階層化カスタム例外・エラー処理統合
- **discord.py**: 3階層通知（Critical/Warning/Info）

### ✅ Phase 2: データ層 (data/)
- **bitbank_client.py**: ccxt統合・信用取引特化・公開API対応
- **data_pipeline.py**: マルチタイムフレーム（15m/1h/4h）・キャッシュ統合
- **data_cache.py**: LRU+ディスク永続化・3ヶ月保存・圧縮機能

### ✅ Phase 3: 特徴量エンジニアリング (features/)
- **technical.py**: 12個厳選指標・47%コード削減・重複計算排除
- **anomaly.py**: Zスコア異常検知・56%コード削減・シンプル化

### ✅ Phase 3-4: 戦略システム (strategies/)
#### 戦略基盤 (base/)
- **strategy_base.py**: 抽象基底クラス・統一インターフェース
- **strategy_manager.py**: 戦略統合管理・重み付け判定・コンフリクト解決

#### 戦略実装 (implementations/)
- **atr_based.py**: ATRベース戦略（566→348行・38%削減）
- **mochipoy_alert.py**: もちぽよアラート（559→283行・49%削減）
- **multi_timeframe.py**: マルチタイムフレーム（668→313行・53%削減）
- **fibonacci_retracement.py**: フィボナッチ戦略（812→563行・31%削減）

#### 共通モジュール (utils/)
- **constants.py**: 定数・型システム・列挙型
- **risk_manager.py**: ATRベースSL・ポジションサイズ計算
- **signal_builder.py**: 統合シグナル生成・エラーハンドリング

### ✅ Phase 5: 機械学習層 (ml/)
#### 個別モデル (models/)
- **lgbm_model.py**: LightGBM実装・ハイパーパラメータ最適化
- **xgb_model.py**: XGBoost実装・早期停止対応
- **rf_model.py**: RandomForest実装・特徴量重要度算出

#### アンサンブル統合 (ensemble/)
- **ensemble_model.py**: 3モデル統合・信頼度閾値管理
- **voting_system.py**: SOFT/HARD/WEIGHTED投票・重み管理
- **model_manager.py**: バージョン管理・A/Bテスト・ストレージ管理

### ✅ Phase 11: バックテストシステム (backtest/)
- **engine.py**: バックテストエンジン・ポジション管理・性能最適化（30-50%高速化）・CI/CD統合
- **evaluator.py**: 統計指標計算・パフォーマンス評価・品質管理・24時間監視
- **data_loader.py**: 6ヶ月データ処理・品質管理・キャッシュ効率化・GitHub Actions対応
- **reporter.py**: CSV/JSON/Discord/HTML出力・統合レポート機能・段階的デプロイ対応

### ✅ Phase 11: 取引実行層 (trading/)
- **executor.py**: 注文実行ロジック・レイテンシー最適化・API統合・CI/CD監視
- **risk.py**: Kelly基準・ドローダウン管理（最大20%制限）・24時間監視統合
- **position_sizing.py**: 動的ポジションサイジング・ATR考慮・安全係数・段階的デプロイ対応
- **anomaly_detector.py**: スプレッド・API遅延・価格スパイク検知・GitHub Actions統合
- **drawdown_manager.py**: 連続損失制御・自動停止・クールダウン機能・監視統合

## 🔄 実装済みデータフロー

```
📊 data/ (Phase 2)
    ↓ MarketData (15m/1h/4h)
🔢 features/ (Phase 3)
    ↓ TechnicalIndicators (12個厳選)
🎯 strategies/ (Phase 3-4)
    ↓ TradingSignals (4戦略統合)
🤖 ml/ (Phase 5)
    ↓ PredictionResults (アンサンブル)
📊 backtest/ (Phase 8)
    ↓ BacktestResults (性能評価)
💼 trading/ (Phase 8)
    ↓ OrderExecution (リスク管理)
📡 monitoring/ (Phase 1)
```

## 🏆 Phase 11完了成果

### 品質指標
- **コード削減**: 42%削減（戦略層）・47-56%削減（特徴量層）
- **テスト成功率**: 99.7%（399/400テスト合格・CI/CD統合）
- **実行速度**: 戦略0.44秒・ML約8秒・バックテスト約12秒・リスク管理約5秒・GitHub Actions対応

### 技術成果
- **設計パターン適用**: Strategy・Template Method・Observer・Factory
- **DRY原則徹底**: 共通処理統合・重複コード排除・品質最適化
- **包括的テスト**: 113戦略+89ML+84バックテスト+113リスク管理テスト・CI/CD統合

### Phase 11新機能
- **CI/CD統合**: GitHub Actions・品質ゲート・段階的デプロイ・自動ロールバック
- **24時間監視**: パフォーマンス追跡・自動アラート・Discord通知・監視統合
- **段階的デプロイ**: 10%→50%→100%カナリアリリース・品質ゲート・無停止デプロイ
- **統合管理システム**: bot_manager.py・統合CLI・運用効率化・監視統合

## 🚨 重要な設計原則

1. **レイヤー間の疎結合**: 各レイヤーは独立して動作・テスト可能
2. **インターフェース指向**: 抽象基底クラスによる統一インターフェース
3. **エラーハンドリング**: 階層化例外・適切なエラー伝播
4. **テスタビリティ**: モック対応・独立したテスト環境

## 📝 開発ガイドライン

### 実装時のルール
- **必須確認**: 該当レイヤーのREADME.md読了
- **依存関係**: 他レイヤーへの直接依存禁止
- **共通機能**: core/配置・utils/活用
- **テスト駆動**: 実装と並行してテスト作成

### コード品質ルール
- **レガシー参考OK**: 構造・ロジック理解して活用
- **コピペ禁止**: エラー・バグ持ち込み防止
- **段階的実装**: フェーズごとに確実進行
- **100%テスト**: 各フェーズでテスト完全実行

### Phase 11完了機能
- **リスク管理**: Kelly基準・ドローダウン20%制限・異常検知完備・CI/CD統合
- **バックテスト**: 性能最適化・統計指標・多形式レポート・GitHub Actions対応
- **品質保証**: 399テスト・99.7%合格・包括的カバレッジ・段階的デプロイ対応
- **統合システム**: 全レイヤー連携・エラーハンドリング完全対応・24時間監視統合

---

**Phase 11完了**: 56,355行→高品質システムへの大規模リファクタリング完了・CI/CD統合・24時間監視・段階的デプロイ対応  
*保守性・安定性・効率性・品質保証・運用管理統合を実現した新システムアーキテクチャ*