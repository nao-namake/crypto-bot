# src/ - AI自動取引システム実装

AI自動取引システムのメイン実装ディレクトリ。データ取得・特徴量生成・戦略実行・機械学習・リスク管理・取引実行を統合したレイヤードアーキテクチャシステム。

## 📂 システム構成

```
src/
├── __init__.py                     # パッケージ初期化
├── core/                          # コア基盤システム
│   ├── orchestration/                 # システム統合制御
│   ├── config/                        # 設定管理・特徴量管理
│   ├── execution/                     # 取引実行制御
│   ├── reporting/                     # レポーティング
│   ├── services/                      # システムサービス
│   ├── config.py                      # 設定読み込み
│   ├── logger.py                      # ログ管理・Discord通知
│   ├── exceptions.py                  # カスタム例外
│   ├── protocols.py                   # インターフェース定義
│   └── market_data.py                 # 市場データ管理
├── data/                          # データ層
│   ├── bitbank_client.py              # Bitbank API統合
│   ├── data_pipeline.py               # データ取得・処理パイプライン
│   └── data_cache.py                  # データキャッシュシステム
├── features/                      # 特徴量システム
│   └── feature_generator.py          # 15特徴量生成・統合管理
├── strategies/                    # 戦略システム → [詳細](strategies/README.md)
│   ├── base/                          # 戦略基盤・統合管理
│   ├── implementations/               # 5戦略実装（ATR・もちぽよ・MTF・Donchian・ADX）
│   └── utils/                         # 戦略共通処理
├── ml/                           # 機械学習システム
│   ├── models.py                      # MLモデル実装
│   ├── ensemble.py                    # アンサンブルモデル・3モデル統合
│   ├── model_manager.py               # モデル管理・バージョニング
│   └── __init__.py                    # ML統合エクスポート
├── trading/                      # 取引実行・リスク管理層 → [詳細](trading/README.md)
│   ├── risk_manager.py                # 統合リスク管理・Kelly基準
│   ├── risk_monitor.py                # 異常検知・ドローダウン管理
│   ├── executor.py                    # 注文実行・統計管理
│   └── __init__.py                    # 取引統合エクスポート
├── backtest/                     # バックテストシステム
│   ├── engine.py                      # バックテストエンジン
│   ├── evaluator.py                   # 性能評価・統計分析
│   └── reporter.py                    # レポート生成・可視化
└── monitoring/                   # 監視システム
    └── discord_notifier.py           # Discord通知・3階層監視
```

## 🔧 システムアーキテクチャ

### **レイヤード設計**

```
📊 monitoring/     ← 監視・通知層
    ↕️
🎯 trading/        ← 取引実行・リスク管理層
    ↕️
📈 strategies/     ← 戦略判定・シグナル生成層
    ↕️
🤖 ml/            ← 機械学習・予測層
    ↕️
⚙️  features/      ← 特徴量エンジニアリング層
    ↕️
📡 data/           ← データ取得・処理層
    ↕️
🏗️  core/          ← 基盤・統合制御層
```

### **データフロー**

```
1. 【data/】Bitbank API → 市場データ取得（4h/15m足）
        ↓
2. 【features/】15特徴量生成 → 技術指標・統計指標
        ↓
3. 【ml/】ProductionEnsemble → 3モデル予測統合
        ↓
4. 【strategies/】5戦略実行 → シグナル統合・重み付け
        ↓
5. 【trading/】リスク評価 → 3段階判定（APPROVED/CONDITIONAL/DENIED）
        ↓
6. 【trading/】注文実行 → ペーパートレード・実取引
        ↓
7. 【monitoring/】Discord通知 → 実行結果・異常通知
```

## 🔧 主要コンポーネント

### **1. core/ - コア基盤システム**
**目的**: システム全体の基盤・統合制御・設定管理

**主要モジュール**:
- `orchestrator.py`: システム統合制御・取引サイクル管理
- `feature_manager.py`: 15特徴量統一定義・システム連携
- `logger.py`: JST対応ログ・構造化出力・Discord統合
- `config.py`: 設定読み込み・環境変数管理・階層化設定

### **2. data/ - データ層**
**目的**: 市場データ取得・処理・キャッシュ管理

**主要モジュール**:
- `bitbank_client.py`: Bitbank API統合・ccxt利用・レート制限対応
- `data_pipeline.py`: データ取得パイプライン・多時間軸・品質管理
- `data_cache.py`: LRUキャッシュ・ディスクキャッシュ・3ヶ月保存

### **3. features/ - 特徴量システム**
**目的**: 技術指標・統計指標の生成・統合管理

**主要モジュール**:
- `feature_generator.py`: 15特徴量生成・feature_manager連携・全システム統合

**生成特徴量（15特徴量・7カテゴリ）**:
- **基本**: close・volume
- **モメンタム**: RSI・MACD
- **ボラティリティ**: ATR・ボリンジャーバンド位置
- **トレンド**: EMA_20・EMA_50
- **出来高**: 出来高比率
- **ブレイクアウト**: Donchianチャネル高値・低値・位置
- **レジーム**: ADX・+DI・-DI

### **4. strategies/ - 戦略システム** → **[詳細ドキュメント](strategies/README.md)**
**目的**: 5戦略統合・シグナル生成・重み付け統合・競合解決

**戦略実装**:
- **ATRBasedStrategy**: ボラティリティ分析・ボリンジャーバンド・RSI統合
- **MochiPoyAlertStrategy**: 複合指標・EMA・MACD・RCI統合
- **MultiTimeframeStrategy**: 4時間足トレンド・15分足タイミング統合
- **DonchianChannelStrategy**: ブレイクアウト戦略・チャネル上下限突破
- **ADXTrendStrengthStrategy**: トレンド強度分析・方向性指標統合

### **5. ml/ - 機械学習システム**
**目的**: 機械学習予測・アンサンブルモデル・モデル管理

**主要モジュール**:
- `models.py`: 個別MLモデル実装・LightGBM・XGBoost・RandomForest
- `ensemble.py`: ProductionEnsemble・3モデル統合・重み付け投票
- `model_manager.py`: モデル管理・バージョニング・週次学習対応

### **6. trading/ - 取引実行・リスク管理層** → **[詳細ドキュメント](trading/README.md)**
**目的**: リスク管理・異常検知・ドローダウン管理・注文実行

**統合機能**:
- **統合リスク管理**: ML信頼度・ドローダウン・異常検知の総合判定
- **Kelly基準ポジションサイジング**: 数学的最適ポジションサイズ計算
- **3段階判定システム**: APPROVED（<0.6）・CONDITIONAL（0.6-0.8）・DENIED（≥0.8）
- **注文実行**: ペーパートレード・実取引・レイテンシー監視

### **7. backtest/ - バックテストシステム**
**目的**: 戦略検証・性能評価・独立実行環境

**主要モジュール**:
- `engine.py`: バックテストエンジン・仮想取引・手数料計算
- `evaluator.py`: 性能評価・統計分析・リスク指標計算
- `reporter.py`: レポート生成・可視化・CSV・HTML出力

### **8. monitoring/ - 監視システム**
**目的**: リアルタイム監視・Discord通知・運用管理

**主要モジュール**:
- `discord_notifier.py`: 3階層通知（Critical/Warning/Info）・Cloud Run監視統合

## 🚀 使用方法

### **基本システム実行**
```python
# メインシステム実行（main.py経由）
python main.py --mode paper    # ペーパートレード
python main.py --mode live     # ライブトレード

# システム統合実行（直接実行）
from src.core.orchestration.orchestrator import Orchestrator
from src.core.config import load_config

config = load_config("config/core/unified.yaml")
orchestrator = Orchestrator(config)
await orchestrator.run_trading_cycle()
```

### **バックテスト実行**
```python
from src.backtest.engine import BacktestEngine

# バックテストエンジン作成
engine = BacktestEngine(
    initial_balance=1000000,
    slippage_rate=0.0005,
    commission_rate=0.0012
)

# バックテスト実行
results = await engine.run_backtest(
    start_date=datetime(2024, 8, 1),
    end_date=datetime(2024, 9, 1),
    symbol="BTC/JPY"
)

# 結果分析
evaluator = BacktestEvaluator(results)
report = evaluator.generate_report()
```

### **個別コンポーネント使用**

**特徴量生成**:
```python
from src.features.feature_generator import FeatureGenerator

generator = FeatureGenerator()
features_df = await generator.generate_features_sync(market_data_df)
```

**戦略実行**:
```python
from src.strategies.base.strategy_manager import StrategyManager

manager = StrategyManager()
# 戦略登録・実行（詳細はstrategies/README.md参照）
```

**取引実行**:
```python
from src.trading import IntegratedRiskManager, create_order_executor

# リスク管理・取引実行（詳細はtrading/README.md参照）
```

## 🧪 テスト・品質保証

### **テスト実行**
```bash
# 全体品質チェック（推奨）
bash scripts/testing/checks.sh

# 個別システムテスト
python -m pytest tests/unit/core/ -v
python -m pytest tests/unit/strategies/ -v
python -m pytest tests/unit/trading/ -v
python -m pytest tests/unit/ml/ -v

# カバレッジ確認
python -m pytest tests/ --cov=src --cov-report=html
```

### **品質指標**
- **テスト成功率**: 625テスト100%成功
- **コードカバレッジ**: 58.64%以上維持
- **実行時間**: システム全体テスト30秒以内

### **継続的品質保証**
- **GitHub Actions**: CI/CD自動品質チェック・失敗時マージ阻止
- **pre-commit hooks**: コード品質・フォーマット自動チェック
- **品質ゲート**: flake8・black・isort・pytest自動実行

## ⚙️ 設定システム

### **設定ファイル階層**
```
config/
├── core/
│   ├── unified.yaml              # 統合設定・本番運用
│   └── feature_order.json       # 15特徴量定義・システム連携KEY
├── backtest/
│   └── backtest.yaml             # バックテスト専用設定
└── infrastructure/
    ├── gcp_config.yaml           # GCP Cloud Run設定
    └── cloudbuild.yaml           # CI/CD設定
```

### **環境変数**
```bash
# API認証
BITBANK_API_KEY=your_api_key
BITBANK_API_SECRET=your_api_secret

# Discord通知
DISCORD_WEBHOOK_URL=your_webhook_url

# システム制御
TRADING_MODE=paper  # paper/live
LOG_LEVEL=INFO      # DEBUG/INFO/WARNING/ERROR
```

## 📈 パフォーマンス指標

### **実行パフォーマンス**
- **取引サイクル**: 15特徴量生成→5戦略→ML予測→リスク評価→実行（2秒以内）
- **データ取得**: Bitbank API・35秒間隔・レート制限遵守
- **メモリ使用量**: 通常運用500MB・バックテスト時1GB以下

### **品質指標**
- **システム統合**: レイヤード設計・疎結合・エラー分離
- **フォールバック**: MLモデル未使用時ダミーモデル自動切替
- **状態管理**: 取引状況・ドローダウン・統計の永続化

## ⚠️ 重要事項

### **システム要件 (Phase 22最適化後)**
- **Python**: 3.12推奨（MLライブラリ互換性最適化済み）・async/await・型ヒント対応
- **メモリ**: 本番運用1GB・バックテスト2GB推奨
- **ディスク**: キャッシュ・ログ・モデル用に5GB以上
- **コード品質**: Phase 22最適化で企業級品質を実現

### **運用制約**
- **API制限**: Bitbank 35秒間隔・接続数制限・レート制限対応
- **リスク管理**: Kelly基準・20%ドローダウン制限・連続5損失停止
- **監視必須**: Discord 3階層通知・Cloud Run監視・ヘルスチェック

### **開発制約 (Phase 22最適化後)**
- **テスト必須**: scripts/testing/checks.sh実行・カバレッジ58.64%維持
- **品質ゲート**: CI/CD自動チェック・失敗時開発停止
- **コード品質**: flake8・black・isort通過必須
- **設定分離**: 本番・バックテスト・開発環境完全分離
- **Phase 22品質**: 未使用コード削除・構造最適化完了

### **依存関係**
- **外部ライブラリ**: pandas・numpy・ccxt・lightgbm・xgboost・scikit-learn
- **API依存**: Bitbank API・Discord Webhook
- **インフラ**: GCP Cloud Run・GitHub Actions・Docker

---

## 🔗 詳細ドキュメント

- **[戦略システム詳細](strategies/README.md)**: 5戦略実装・統合管理・使用方法
- **[取引実行システム詳細](trading/README.md)**: リスク管理・異常検知・注文実行
- **[プロジェクト全体概要](../README.md)**: システム全体・運用手順・開発履歴

---

**AI自動取引システム (Phase 22最適化完了)**: レイヤードアーキテクチャによる統合システム。データ取得→特徴量生成→戦略実行→機械学習→リスク管理→取引実行の完全自動化。ペーパートレードから実取引まで対応し、包括的な品質保証とリスク管理を実現。

**Phase 22成果**: 未使用コード削除(423行)・構造最適化・保守性向上により企業級コード品質を実現。