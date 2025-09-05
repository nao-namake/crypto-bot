# src - MLOps統合システム実装ディレクトリ

## 🎯 役割・責任

MLOps完全統合したAI自動取引システムのメイン実装を提供する。Phase 19 MLOps統合により、feature_manager 12特徴量統一管理・ProductionEnsemble 3モデル統合・654テスト品質保証・週次自動学習・Cloud Run 24時間稼働統合を実現し、企業級品質保証を完備した実用的システムを構築。

## 📂 ファイル構成

```
src/
├── core/                       # MLOps統合基盤システム
│   ├── orchestration/              # 統合制御システム
│   │   ├── orchestrator.py             # システム統合制御・ML/戦略連携
│   │   ├── ml_adapter.py               # MLサービス統合・ProductionEnsemble連携
│   │   └── ml_loader.py                # モデル読み込み・週次学習対応
│   ├── config/                     # 設定管理システム
│   │   └── feature_manager.py          # 12特徴量統一管理・統合基盤
│   ├── config.py                   # 設定読み込み・環境変数管理
│   ├── logger.py                   # JST対応ログ・Discord通知統合
│   ├── exceptions.py               # カスタム例外・階層化エラー処理
│   └── protocols.py                # Protocol分離・型安全性
├── data/                       # データ層
│   ├── bitbank_client.py           # Bitbank API・ccxt統合・信用取引対応
│   ├── data_pipeline.py            # データ取得・多時間軸・キャッシュ統合
│   └── data_cache.py               # LRU+ディスクキャッシュ・3ヶ月保存
├── features/                   # 特徴量エンジニアリング
│   └── feature_generator.py       # 12特徴量生成・feature_manager連携
├── strategies/                 # 戦略システム
│   ├── base/                       # 戦略基盤
│   │   ├── strategy_base.py            # 戦略抽象基底クラス
│   │   └── strategy_manager.py         # 戦略統合管理・重み付け
│   ├── implementations/            # 戦略実装群（4戦略）
│   │   ├── atr_based.py                # ATRベース戦略・ボラティリティ逆張り
│   │   ├── mochipoy_alert.py           # もちぽよアラート・感情分析取引
│   │   ├── multi_timeframe.py          # 多時間軸・トレンド追従
│   │   └── fibonacci_retracement.py    # フィボナッチ・サポレジ戦略
│   └── utils/                      # 戦略共通処理
│       ├── constants.py                # 定数・型システム・列挙型
│       ├── risk_manager.py             # リスク管理計算・ATR損切り
│       └── signal_builder.py           # シグナル生成統合・エラーハンドリング
├── ml/                         # 機械学習層（Phase 19 MLOps統合）
│   ├── models.py                   # MLモデル実装・ProductionEnsemble基盤
│   ├── ensemble.py                 # アンサンブル・3モデル統合・重み付け投票
│   ├── model_manager.py            # モデル管理・週次学習・バージョニング
│   └── __init__.py                 # MLOps統合エクスポート・後方互換性
├── backtest/                   # バックテストシステム（独立実行環境）
│   ├── engine.py                   # BacktestEngine・メイン実行・本番分離
│   ├── evaluator.py                # 性能評価・統計分析・指標計算
│   └── reporter.py                 # 統合レポーター・多形式出力・可視化
├── trading/                    # 取引実行層
│   ├── executor.py                 # 注文実行・レイテンシー最適化
│   ├── risk.py                     # Kelly基準・ドローダウン管理・20%制限
│   ├── position_sizing.py          # 動的ポジションサイジング・ATR考慮
│   ├── anomaly_detector.py         # 異常検知・スプレッド監視・価格スパイク
│   └── drawdown_manager.py         # ドローダウン制御・自動停止・クールダウン
└── monitoring/                 # 監視層
    └── discord_notifier.py     # Discord 3階層通知・Cloud Run監視統合
```

## 🔧 主要機能・実装

### **MLOps統合基盤 (core/)**
- **feature_manager統合** - 12特徴量統一管理・全システム連携・ProductionEnsemble対応
- **orchestrator統合制御** - ML/戦略/取引システム統合制御・エラーハンドリング
- **設定統一管理** - 環境変数・YAML・階層化設定・CI/CD対応
- **ログ監視統合** - JST対応・Discord通知・構造化出力・Cloud Run監視

### **データ統合システム (data/)**
- **Bitbank API統合** - ccxt・信用取引・レート制限・リトライ機能
- **多時間軸データ** - 15m/4h足・キャッシュ統合・品質管理・異常値検出
- **バックテスト分離** - 本番データ影響なし・独立キャッシュ・長期保存

### **AI機械学習統合 (ml/)**
- **ProductionEnsemble** - 3モデル統合（LightGBM/XGBoost/RandomForest）・重み付け投票
- **週次自動学習** - GitHub Actions・CI/CD品質ゲート・段階的デプロイ・モデル更新
- **信頼度管理** - 65%閾値・フォールバック対応・ダミーモデル検知

### **戦略統合システム (strategies/)**
- **4戦略統合** - ATRベース/もちぽよアラート/多時間軸/フィボナッチ
- **統合判定システム** - 重み付け・合意形成・コンフリクト解決・信頼度評価
- **リスク管理統合** - Kelly基準・ATR損切り・ポジションサイジング

## 📝 使用方法・例

### **基本システム初期化**
```python
from src.core.orchestration import Orchestrator
from src.core.config import load_config

# 設定読み込み・システム初期化
config = load_config("config/production/base.yaml")
orchestrator = Orchestrator(config)

# システム統合実行
await orchestrator.run_trading_cycle()
```

### **バックテスト実行**
```python
# バックテスト専用設定で実行
from src.backtest import BacktestEngine

engine = BacktestEngine(
    initial_balance=1000000,
    slippage_rate=0.0005,
    commission_rate=0.0012
)

# 独立環境でバックテスト
results = await engine.run_backtest(
    start_date=datetime(2024, 8, 1),
    end_date=datetime(2024, 9, 1),
    symbol="BTC/JPY"
)
```

### **スクリプト実行**
```bash
# メインシステム実行
python main.py --mode paper    # ペーパートレード
python main.py --mode live     # ライブトレード

# バックテスト実行
python scripts/backtest/run_backtest.py --days 30 --verbose
```

## ⚠️ 注意事項・制約

### **システム環境要件**
- **Python 3.8+** - async/await・型ヒント・dataclass対応必須
- **メモリ要件** - 本番：1GB、バックテスト：2GB以上推奨
- **API制限** - Bitbank 35秒間隔・レート制限対応・接続制限管理

### **本番運用制約**
- **信用取引専用** - Bitbank信用取引・レバレッジ1.0-2.0倍対応
- **リスク管理** - Kelly基準・最大20%DD・連続損失5回制限
- **監視必須** - Discord 3階層通知・Cloud Run監視・ヘルスチェック

### **開発・テスト制約**
- **654テスト必須** - scripts/testing/checks.sh実行・59.24%カバレッジ維持
- **品質ゲート** - CI/CD自動チェック・失敗時はマージ不可
- **設定分離** - 本番/バックテスト完全分離・影響回避

## 🔗 関連ファイル・依存関係

### **設定・実行基盤**
- **`config/production/base.yaml`** - 本番設定・ML・戦略・監視統合設定
- **`config/backtest/`** - バックテスト専用設定・完全分離環境
- **`scripts/backtest/run_backtest.py`** - バックテスト実行スクリプト・CLI対応

### **MLOps統合基盤**
- **`models/production/`** - ProductionEnsemble 3モデル・週次更新対応
- **`config/core/feature_order.json`** - 12特徴量定義・統合基盤・全システム参照
- **`.github/workflows/model-training.yml`** - 週次自動学習・CI/CD品質ゲート

### **品質保証・監視**
- **`scripts/testing/checks.sh`** - 654テスト・品質チェック・開発必須
- **`tests/`** - 単体・統合テスト・59.24%カバレッジ・回帰防止
- **`.github/workflows/ci.yml`** - CI/CD自動化・品質ゲート・デプロイ管理

### **運用・ログ**
- **`logs/`** - システムログ・バックテストレポート・監視データ
- **Cloud Run** - 24時間本番稼働・自動スケーリング・監視統合
- **Discord** - 3階層通知・運用アラート・パフォーマンス報告