# CLAUDE.md - Phase 50.3完了・開発ガイド

**Claude Codeが即座に理解すべき開発指針と技術情報**

---

## 🎯 システム現状（最重要・即座理解）

### Phase 50.3完了ステータス

**最新Phase**: Phase 50.3完了（2025/10/28）
- **マクロ経済指標統合**（外部API統合・8特徴量追加・4段階Graceful Degradation）
- **70特徴量対応**（62基本+8外部API・Phase 50.2時間的特徴量+Phase 50.3外部API）
- **レガシー教訓反映**（外部API失敗時もシステム継続動作保証）
- **Phase 49**: バックテスト完全改修（信頼性100%達成・TradeTracker統合・matplotlib可視化）
- **Phase 48**: Discord週間レポート（通知99%削減・コスト35%削減）
- **Phase 47**: 確定申告対応システム（作業時間95%削減）

**品質指標**:
- 326テスト成功（Phase 50.3: +50テスト）
- 7テストスキップ（aiohttp mock問題・Phase 50.3.1修正予定）
- 3テスト失敗（70特徴量期待値調整・Phase 50.3.1修正予定）
- CI/CD統合完了

**運用仕様**:
- bitbank信用取引・BTC/JPY専用
- 24時間稼働（GCP Cloud Run）
- 月額700-900円（Phase 48コスト削減達成）
- 5分間隔実行（Phase 37.3最適化）
- 1万円スタート → 最大50万円（段階的拡大）

### システム概要

**AI自動取引システム**: 5戦略 + ML統合（**Phase 50.3: 70特徴量**）による真のハイブリッドMLbot

**技術構成**:
- Python 3.13・MLライブラリ互換性最適化
- 5戦略統合（ATR・MochiPoy・MultiTimeframe・Donchian・ADX）
- 3モデルアンサンブル（LightGBM 40%・XGBoost 40%・RandomForest 20%）
- 4時間足（トレンド）+ 15分足（エントリー）
- **Phase 50.3**: 外部API統合（Yahoo Finance・Alternative.me）

**リスク管理**:
- **TP/SL設定**: SL 1.5%・TP 1.0%・RR比0.67:1（Phase 49.18デイトレード特化）
- **個別TP/SL管理**: エントリー毎に独立したTP/SL注文（Phase 46回帰）
- **完全指値オンリー**: 年間¥150,000削減（Phase 38.7.2）
- **適応型ATR**: ボラティリティ別SL調整（低2.5x・通常2.0x・高1.5x）
- **証拠金維持率80%確実遵守**（Phase 49.18）

**ML統合**:
- **Phase 50.3**: 70特徴量（62基本+8外部API）
  - 62基本特徴量: 50特徴量+5戦略信号+7時間的特徴量（Phase 50.2）
  - 8外部API特徴量: USD/JPY・日経平均・米10年債・Fear & Greed Index・派生4指標
- Strategy-Aware ML: 実戦略信号学習（Phase 41.8）
- ML統合率100%達成（Phase 41.8.5）
- 3段階統合ロジック（<0.45: 戦略のみ・0.45-0.60: 加重平均・≥0.60: ボーナス/ペナルティ）
- **4段階Graceful Degradation**（Phase 50.3）:
  - Level 1: 70特徴量（外部API含む）
  - Level 2: 62特徴量（外部APIなし）← **外部API失敗時フォールバック**
  - Level 3: 57特徴量（戦略信号なし）
  - Level 4: DummyModel（最終フォールバック）

---

## 🚀 必須コマンド（開発時必読）

### 品質チェック（開発前後必須）

```bash
# Phase 50.3品質チェック - 開発前後に必ず実行
bash scripts/testing/checks.sh

# 期待結果:
# ✅ 326テスト成功（Phase 50.3: +50テスト追加）
# ⚠️ 7テストスキップ（aiohttp mock問題・Phase 50.3.1修正予定）
# ⚠️ 3テスト失敗（70特徴量期待値調整・Phase 50.3.1修正予定）
# ✅ 実行時間: 約80秒で完了
```

### システム実行

```bash
# ✅ 推奨: フォアグラウンド実行（Claude Code誤認識回避）
bash scripts/management/run_safe.sh local paper  # ペーパートレード
bash scripts/management/run_safe.sh local live   # ライブトレード

# 実行状況確認（実プロセス確認）
bash scripts/management/bot_manager.sh check

# 停止
bash scripts/management/run_safe.sh stop
```

### 本番環境確認（GCP）

```bash
# Cloud Run稼働状況
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1

# システムログ確認
gcloud logging read "resource.type=cloud_run_revision" --limit=10

# 残高確認
gcloud logging read "textPayload:\"残高\" OR textPayload:\"balance\"" --limit=5
```

### バックテスト実行（Phase 49最適化）

```bash
# データ存在確認（必須）
wc -l src/backtest/data/historical/btc_jpy_4h.csv    # 期待: 1,081行
wc -l src/backtest/data/historical/btc_jpy_15m.csv   # 期待: 17,272行

# データ収集（不足時）
python src/backtest/data/historical/collect_historical_csv.py --days 180

# バックテスト実行
python src/backtest/scripts/run_backtest.py
```

---

## 📂 システム構造（アーキテクチャ理解）

### ディレクトリ構成

```
src/                        # メイン実装・レイヤードアーキテクチャ
├── core/                   # 🔧 基盤システム
│   ├── orchestration/          # システム統合制御・TradingOrchestrator
│   ├── config/                 # 設定管理・統一設定（unified.yaml）
│   ├── execution/              # 取引実行制御・ExecutionService
│   ├── reporting/              # レポーティング・Discord週間レポート
│   └── services/               # システムサービス・GracefulShutdown
├── data/                   # 📊 データ層（Bitbank API・キャッシュ）
├── features/               # 📈 特徴量生成（15指標）
├── strategies/             # 🎯 5戦略統合システム
├── ml/                     # 🧠 ProductionEnsemble・3モデル統合
├── trading/                # ⚖️ 取引管理層（Phase 38レイヤードアーキテクチャ）
│   ├── core/                   # 共通定義層（enums・types）
│   ├── balance/                # 残高監視層（MarginMonitor）
│   ├── execution/              # 注文実行層（ExecutionService・OrderStrategy）
│   ├── position/               # ポジション管理層（Tracker・Limits・Cleanup）
│   └── risk/                   # リスク管理層（IntegratedRiskManager）
├── backtest/               # 📉 バックテストシステム（Phase 49完全改修）
└── monitoring/             # 📢 週間レポート（Phase 48）

tax/                        # 📊 税務システム（Phase 47）
├── trade_history_recorder.py   # 取引履歴記録（SQLite）
├── pnl_calculator.py           # 損益計算（移動平均法）
└── trade_history.db            # 取引履歴DB

scripts/
├── testing/checks.sh           # 品質チェック（開発必須）
├── reports/weekly_report.py    # 週間レポート生成
└── tax/                        # 税務スクリプト

📁 重要ファイル:
├── config/core/features.yaml       # 機能トグル設定
├── config/core/unified.yaml        # 統合設定ファイル
├── config/core/thresholds.yaml     # ML統合・リスク管理設定
└── models/production/              # 本番MLモデル（週次自動更新）
```

### データフロー

```
データ取得（Bitbank API）
    ↓
特徴量生成（15指標 → 50基本特徴量）
    ↓
戦略実行（5戦略 → 5戦略信号特徴量追加 → 55特徴量）
    ↓
ML予測（3モデルアンサンブル → 信頼度）
    ↓
リスク評価（Kelly基準・ポジション制限）
    ↓
取引判断（個別TP/SL・適応型ATR）
    ↓
取引実行（完全指値オンリー・bitbank API）
```

---

## 🎯 開発原則・品質基準

### 品質保証（必須遵守）

- **テスト実行**: 開発前後に`checks.sh`必須実行・1,065テスト100%維持・66.72%カバレッジ
- **カバレッジ**: 66%以上維持・新機能は必ずテスト追加
- **CI/CD**: GitHub Actions自動品質ゲート・失敗時は修正必須

### 設定管理統一（最重要）

**ハードコード禁止**: すべて設定ファイル・環境変数で管理

**3層設定体系**:
1. `config/core/features.yaml`: 機能トグル設定
2. `config/core/unified.yaml`: 基本設定（残高・実行間隔等）
3. `config/core/thresholds.yaml`: 動的値（ML閾値・リスク設定等）

**設定変更パターン（Phase 42.4以降）**:
```python
# ❌ 避けるべき: ハードコード
sl_rate = 0.02

# ✅ 推奨: get_threshold()パターン
from src.core.config.threshold_manager import get_threshold
sl_rate = get_threshold("risk.sl_min_distance_ratio", 0.02)
```

**Secret Manager**: 具体的バージョン番号使用（`key:3`など・`key:latest`禁止）

### 実装品質基準

- **コード品質**: flake8・black・isort通過必須
- **ログ品質**: JST時刻・構造化ログ・Discord通知対応
- **テスト品質**: 単体・統合・エラーケーステスト完備
- **レイヤードアーキテクチャ**: 各層責任明確・依存関係遵守

---

## 🔧 重要技術ポイント（Phase履歴）

### Phase 49（2025/10/26）- バックテスト完全改修

**Phase 49.16: TP/SL計算完全見直し**
- strategy_utils.py・executor.pyのハードコード値削除
- `get_threshold()`パターン適用（Phase 42.4パターン踏襲）
- 効果: 設定ファイル変更のみで動作変更可能

**Phase 49.15: 証拠金維持率80%遵守**
- critical維持率: 100.0 → 80.0変更
- TradeTracker統合: エントリー/エグジットペアリング・損益計算

**Phase 49.13-14: matplotlib可視化システム**
- エクイティカーブ・損益分布・ドローダウン・価格チャート実装
- 4種類のグラフによるバックテスト分析強化

**Phase 49.1-12: バックテスト信頼性100%達成**
- 戦略シグナル事前計算・TP/SL決済ロジック実装
- SELL判定正常化・ライブモード完全一致

**品質保証**: 1,065テスト100%成功・66.72%カバレッジ達成

### Phase 48（2025/10/22）- Discord週間レポート

- 損益曲線グラフ・matplotlib・Pillow実装
- 通知99%削減（300-1,500回/月 → 4回/月）
- コスト35%削減（月額700-900円達成）
- GitHub Actions週次実行（毎週月曜9:00 JST）

### Phase 47（2025/10/22）- 確定申告対応システム

- SQLite取引履歴記録・移動平均法損益計算
- CSV出力（国税庁フォーマット）
- 作業時間95%削減（10時間 → 30分）
- ExecutionService統合

### Phase 46（2025/10/22）- デイトレード特化・シンプル設計回帰

**背景**: スイングトレード機能（Phase 42実装）が過剰に複雑・デイトレードに不適合

**実施内容**:
- **スイングトレード機能完全削除**（統合TP/SL・トレーリングストップ）
- **個別TP/SL管理に回帰**（エントリー毎に独立したTP/SL注文）
- **デイトレード特化設定**: 初期設定後Phase 49.18で最終調整（SL 1.5%・TP 1.0%・RR比0.67:1）
- **コードベース大幅簡略化**: -1,041行削除（executor.py: -51.2%、stop_manager.py: -89.9%）

**効果**: シンプル性・保守性大幅向上・予測可能な動作・デバッグ容易性確保

### Phase 42.3-42.4（2025/10/18-20）- バグ修正・TP/SL最適化

**Phase 42.3: バグ修正3件**
- ML Agreement Logic修正（strict matching）
- Feature Warning抑制（strategy_signal_*除外）
- 証拠金チェックリトライ（Error 20001対策・3回リトライ）

**Phase 42.4: TP/SL設定最適化**
- order_strategy.pyハードコード値削除（`get_threshold()`パターン適用）
- thresholds.yaml完全準拠（設定変更のみで動作変更可能）

**注**: Phase 42.1-42.2で実装した統合TP/SL・トレーリングストップは**Phase 46で削除済み**

### Phase 41.8.5（2025/10/17）- ML統合閾値最適化

- `min_ml_confidence`: 0.6 → 0.45
- `high_confidence_threshold`: 0.8 → 0.60
- ML統合率: 10% → 100%達成
- 3段階統合ロジック再設計

### Phase 41.8（2025/10/17）- Strategy-Aware ML

- 55特徴量学習（50基本+5戦略信号）
- 実戦略信号学習・訓練/推論一貫性確保
- Look-ahead bias防止（`df.iloc[: i + 1]`）
- F1スコア0.56-0.61達成

### 核心システム基盤（Phase 29-40要点）

**Phase 40**: 79パラメータOptuna最適化・期待効果+50-70%収益向上

**Phase 38.7.2**: 完全指値オンリー・年間¥150,000削減・約定率90-95%

**Phase 38**: trading層レイヤードアーキテクチャ・5層分離・保守性大幅向上

**Phase 37.4**: SL配置成功率100%・trigger_price修正・エラー30101解消

**Phase 37.3**: コスト削減35-45%・5分間隔実行

**Phase 37.2**: bitbank API GET認証対応・エラー20003解消

**Phase 37**: SL注文stop対応・エラー50062解消

**Phase 36**: Graceful Degradation・Container exit(1)解消

**Phase 35**: バックテスト10倍高速化（45分実行）

**Phase 34**: 15分足データ収集80倍改善

**Phase 32**: 全5戦略SignalBuilder統一・15m ATR優先

**Phase 31.1**: features.yaml作成・柔軟クールダウン実装

**Phase 29.5**: ML予測統合・戦略70% + ML30%

**Phase 28**: 基本TP/SL機能実装（現在も使用中）

---

## 🛠️ トラブルシューティング

### 開発時問題

```bash
# 品質チェック実行（詳細エラー確認）
bash scripts/testing/checks.sh

# import エラー時（モジュール確認）
python3 -c "import sys; sys.path.insert(0, '.'); from src.core.logger import CryptoBotLogger"

# 設定エラー時（整合性確認）
python3 scripts/testing/dev_check.py validate
```

### Claude Code特有問題

**バックグラウンドプロセス誤認識問題**:
- 原因: Claude Code内部トラッキングシステムの制限
- 解決策: フォアグラウンド実行使用（デフォルト推奨）

```bash
# ✅ 正しい実行方法
bash scripts/management/run_safe.sh local paper

# 📊 実プロセス状況確認（Claude Code表示を無視）
bash scripts/management/bot_manager.sh check
# → 「✅ システム完全停止状態」なら実際には停止中
```

### 本番環境問題（GCP）

```bash
# システム稼働状況確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1

# エラーログ確認
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" --limit=20

# 残高取得確認
gcloud logging read "textPayload:\"残高\" OR textPayload:\"balance\"" --limit=10
```

---

## ✅ 開発時チェックリスト

### 必須確認事項

1. **品質チェック**: `bash scripts/testing/checks.sh`で1,065テスト・66.72%カバレッジ確認
2. **本番稼働**: Cloud Run・週間レポート・取引ログ確認
3. **Phase 49機能**: バックテスト完全改修・TradeTracker・matplotlib可視化確認
4. **Phase 48機能**: Discord週間レポート・通知99%削減確認
5. **Phase 47機能**: 確定申告システム・SQLite取引記録確認
6. **Phase 46機能**: 個別TP/SL管理・デイトレード特化設定確認
7. **設定整合性**: features.yaml・unified.yaml・thresholds.yaml確認

### 開発開始前チェック

1. **最新状況把握**: システム状況・エラー状況・Phase 49ステータス確認
2. **品質基準**: 1,065テスト・66.72%カバレッジ・コード品質確認
3. **設定管理**: ハードコード禁止・get_threshold()パターン遵守

---

**📅 最終更新**: 2025年10月26日 - Phase 49完了
