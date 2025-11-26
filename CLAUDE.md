# CLAUDE.md - システム開発ガイド

**Claude Codeが即座に理解すべき開発指針と技術情報**

---

## 🎯 システム現状（最重要・即座理解）

### 本番稼働ステータス

**現在の状況**: **本番環境稼働中**（GCP Cloud Run・24時間自動取引）

### 最新システム状態（2025/11/27時点）

**Phase 55.7b完了 - バックテストクールダウン修正・エントリー数5倍改善**:
- **問題**: バックテストで`datetime.now()`が実時間を返すためクールダウンが常に作動
- **修正内容**: `is_backtest_mode()`チェック追加・バックテスト時クールダウンスキップ
- **効果**: 7日間エントリー 8回→43回（+437%）、勝率53.49%
- **詳細**: `docs/開発履歴/Phase_55.md`

**Phase 53.8.3完了 - 48時間エントリーゼロ問題完全解決**:
- **ML統合設定最適化**: 統計的根拠に基づく閾値調整（hold_conversion_threshold 0.30→0.20、tight_range 0.50→0.40）
- **MLモデル再学習**: CV F1スコア 0.52-0.59達成（RandomForest 0.59±0.06が最高性能）
- **GitHub Actions修正**: データ収集統合・PYTHONPATH設定・週次自動学習正常化
- **期待効果**: エントリー率 <5% → 10-15%、ML統合率 10-20% → 30-40%、ML hold予測正常化 80% → 40-50%

**Phase 53.5完了 - RandomForestクラッシュ修正**:
- **修正内容**: `n_jobs=-1` → `n_jobs=1`（GCP Cloud Run gVisor環境互換性）
- **効果**: 99%稼働率目標達成（33.74% → 99%）・クラッシュゼロ・システム安定性向上

**品質指標**（最新）:
- **テスト成功率**: 100%（1,259テスト）
- **カバレッジ**: 66.37%（65%目標超過）
- **コード品質**: flake8・isort・black全てPASS
- **CI/CD**: GitHub Actions成功・GCP Cloud Runデプロイ完了
- **設定管理**: Single Source of Truth確立

**モデルシステム**:
- **ensemble_full.pkl**（55特徴量・デフォルト）← **n_jobs=1設定済み**
- **ensemble_basic.pkl**（49特徴量・フォールバック）← **n_jobs=1設定済み**
- **DummyModel**（最終フォールバック・ゼロダウンタイム保証）

**アーキテクチャ基盤**:
- **拡張性**: Registry Pattern実装・戦略追加が2ファイルのみ（93%削減）
- **技術的負債**: ゼロ
- **動的戦略管理**: 6戦略統合・55特徴量システム
- **システム整合性**: 100%達成

**運用仕様**:
- bitbank信用取引・BTC/JPY専用
- 24時間稼働（GCP Cloud Run）
- 月額700-900円（Phase 48コスト削減達成）
- 5分間隔実行（Phase 37.3最適化）
- 1万円スタート → 最大50万円（段階的拡大）

### システム概要

**AI自動取引システム**: 6戦略 + ML統合（**55特徴量システム**）による真のハイブリッドMLbot

**技術構成**:
- Python 3.11・GCP gVisor互換性確保・99%稼働率達成（Phase 53.5/53.8）
- **6戦略統合**（Phase 51.7）:
  - レンジ型3個: ATRBased・DonchianChannel・BBReversal
  - トレンド型3個: ADXTrendStrength・StochasticReversal・MACDEMACrossover
- **動的戦略管理**: Registry Pattern・93%影響削減
- 3モデルアンサンブル（LightGBM 50%・XGBoost 30%・RandomForest 20%・**n_jobs=1設定**・CV F1: 0.52-0.59）
- 4時間足（トレンド）+ 15分足（エントリー）
- **本番稼働中**: 55特徴量システム・ML統合設定最適化完了（Phase 53.8.3）

**リスク管理**:
- **TP/SL設定**（レジーム別動的設定）:
  - tight_range: TP 0.6% / SL 0.8%
  - normal_range: TP 1.0% / SL 0.7%（基本設定・RR比0.67:1）
  - trending: TP 2.0% / SL 2.0%
- **個別TP/SL管理**: エントリー毎に独立したTP/SL注文（Phase 46回帰）
- **完全指値オンリー**: 年間¥150,000削減（Phase 38.7.2）
- **適応型ATR**: ボラティリティ別SL調整（低2.5x・通常2.0x・高1.5x）
- **証拠金維持率80%確実遵守**（Phase 49.18）

**ML統合**（最新システム）:
- **55特徴量システム**（確立・一元管理・n_jobs=1設定）:
  - 49基本テクニカル特徴量
  - 6戦略信号特徴量（Phase 51.7: 6戦略すべてのシグナル）
  - feature_order.jsonが唯一の真実（Single Source of Truth）
- **真の3クラス分類**:
  - 0=sell, 1=hold, 2=buy（F1改善+9.7%）
- Strategy-Aware ML: 実戦略信号学習
- ML統合率100%達成
- 3段階統合ロジック（<0.45: 戦略のみ・0.45-0.60: 加重平均・≥0.60: ボーナス/ペナルティ）
- **2段階Graceful Degradation**:
  - **Level 1（デフォルト）**: 55特徴量 ← **ensemble_full.pkl**（完全特徴量セット）
  - **Level 2（フォールバック）**: 49特徴量 ← **ensemble_basic.pkl**（戦略信号なし）
  - **Level 3（最終）**: DummyModel（全holdシグナル・システム継続動作保証）
  - 外部API依存削除・セマンティック命名採用・システム安定性向上

---

## 🚀 必須コマンド（開発時必読）

### 品質チェック（開発前後必須）

```bash
# 品質チェック - 開発前後に必ず実行
bash scripts/testing/checks.sh

# Phase 55.7b時点:
# ✅ 1,259テスト・100%成功
# ✅ 66.37%カバレッジ達成（65%目標超過）
# ✅ flake8・isort・black全てPASS
# ✅ 実行時間: 約74秒で完了
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

### バックテスト実行（Phase 51.8-J4対応）

```bash
# データ存在確認（必須）
wc -l src/backtest/data/historical/BTC_JPY_4h.csv    # 例: ~2,000行（180日分4時間足）
wc -l src/backtest/data/historical/BTC_JPY_15m.csv   # 例: ~30,000行（180日分15分足）

# データ収集（不足時）
python src/backtest/scripts/collect_historical_csv.py --days 180

# バックテスト実行（推奨：ログ自動保存）
bash scripts/backtest/run_backtest.sh              # デフォルト
bash scripts/backtest/run_backtest.sh phase51.8    # カスタム名

# または直接実行（手動ログ管理）
python3 main.py --mode backtest
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
├── strategies/             # 🎯 6戦略統合システム
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

### データフロー（Phase 52.5最新）

```
データ取得（Bitbank API・15分足直接取得）
    ↓
特徴量生成（15指標 → 49基本特徴量）
    ↓
戦略実行（6戦略 → 6戦略信号特徴量追加 → 55特徴量）
    ↓
ML予測（ensemble_full.pkl: 55特徴量モデル → 信頼度）
    ↓
リスク評価（Kelly基準・ポジション制限・ドローダウン管理）
    ↓
取引判断（レジーム別動的TP/SL・適応型ATR）
    ↓
取引実行（Atomic Entry・完全指値オンリー・bitbank API）
```

**Phase 52.5変更点**:
- 設定ファイル最適化（重複削除110行・Single Source of Truth確立）
- feature_order.json（55特徴量）が唯一の真実源
- 使用箇所ドキュメント化（10+主要設定）
- 視覚的改善（12個のセクション区切り）
- 1,252テスト100%成功・66.78%カバレッジ達成

---

## 🎯 開発原則・品質基準

### 品質保証（必須遵守）

- **テスト実行**: 開発前後に`checks.sh`必須実行・1,259テスト100%維持・66.37%カバレッジ
- **カバレッジ**: 65%以上維持・新機能は必ずテスト追加
- **CI/CD**: GitHub Actions自動品質ゲート・失敗時は修正必須

**Phase 55.7b完了後の品質指標**:
- 全テスト数: 1,259テスト（Phase 55シリーズ: +7テスト追加）
- カバレッジ: 66.37%（目標65%超過）
- コード品質: flake8・black・isort全てPASS
- CI/CD: GitHub Actions成功・GCP Cloud Runデプロイ完了
- 設定管理: Single Source of Truth確立・重複削除110行

### 設定管理統一（最重要）

**ハードコード禁止**: すべて設定ファイル・環境変数で管理

**3層設定体系**:
1. `config/core/features.yaml`: 機能トグル設定
2. `config/core/unified.yaml`: 基本設定（残高・実行間隔等）
3. `config/core/thresholds.yaml`: 動的値（ML閾値・リスク設定等）

**設定変更パターン（推奨）**:
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

### 必須確認事項（Phase 55.7b完了後）

1. **品質チェック**: `bash scripts/testing/checks.sh`で1,259テスト・66.37%カバレッジ確認
2. **モデルファイル確認**: ensemble_full.pkl（55特徴量）・ensemble_basic.pkl（49特徴量）存在確認
3. **55特徴量動作確認**: 特徴量生成・ML予測・エントリー判断正常動作
4. **6戦略動作確認**: ATRBased・DonchianChannel・ADXTrendStrength・BBReversal・StochasticReversal・MACDEMACrossover稼働確認
5. **本番環境確認**: Cloud Run・55特徴量・ensemble_full.pkl使用確認
6. **動的戦略管理確認**: strategies.yaml・動的ロード正常動作
7. **設定整合性**: features.yaml・unified.yaml・thresholds.yaml・feature_order.json確認（Single Source of Truth）

### 開発開始前チェック

1. **最新状況把握**: **Phase 55.7b完了**・docs/開発計画/ToDo.md確認
2. **品質基準**: 1,259テスト100%成功・66.37%カバレッジ維持必須
3. **設定管理**: ハードコード禁止・get_threshold()パターン遵守・Single Source of Truth（feature_order.json）
4. **Phase 55.7b理解**: バックテストクールダウン修正・エントリー数5倍改善（8→43回/7日）
5. **本番安定稼働**: レジーム別動的TP/SL・DrawdownManager統合・週次バックテスト自動化

---

📅 最終更新: 2025年11月27日 - Phase 55.7b完了（バックテストクールダウン修正・エントリー数5倍改善・1,259テスト100%成功）
## 🔧 主要開発履歴（重要改善のみ）

### 最新システム改善

**バックテストクールダウン修正**（2025/11/27 - Phase 55.7b）:
- **問題**: バックテストで`datetime.now()`が実時間を返すためクールダウンが常に作動
- **修正**: `is_backtest_mode()`チェック追加・バックテスト時クールダウンスキップ
- **効果**: 7日間エントリー 8回→43回（+437%）、勝率53.49%
- **詳細**: `docs/開発履歴/Phase_55.md`

**48時間エントリーゼロ問題完全解決**（2025/11/21 - Phase 53.8.3）:
- **問題**: 2025-11-19 06:00以降48時間エントリーゼロ・ML hold予測80%異常
- **根本原因**: ML統合設定の過剰適用・モデルデータ古さ（12日前）
- **修正**: 統計的根拠に基づく閾値最適化・最新180日データで再学習・GitHub Actions修正
- **効果**: エントリー率 <5% → 10-15%見込み、ML統合率 10-20% → 30-40%、CV F1: 0.52-0.59達成
- **詳細**: `docs/開発履歴/Phase_53.md`

**RandomForestクラッシュ修正**（2025/11/19 - Phase 53.5）:
- **問題**: RandomForest `n_jobs=-1`がGCP Cloud Run（gVisor）でクラッシュ（105回/7日間・稼働率33.74%）
- **修正**: `n_jobs=1`設定・訓練スクリプト2箇所・モデル再訓練完了
- **効果**: クラッシュゼロ・99%稼働率達成（33.74% → 99%）
- **詳細**: `docs/開発履歴/Phase_53.md`

**バックテスト完全改修**（2025/10/26）:
- TradeTracker実装（エントリー/エグジットペアリング・損益計算）
- matplotlib可視化（エクイティカーブ・損益分布・ドローダウン・価格チャート）
- 証拠金維持率80%確実遵守

**Discord週間レポート**（2025/10/22）:
- 通知99%削減（300-1,500回/月 → 4回/月）
- 損益曲線グラフ・コスト35%削減
- GitHub Actions週次実行（毎週月曜9:00 JST）

**確定申告対応システム**（2025/10/22）:
- SQLite取引履歴記録・移動平均法損益計算
- CSV出力（国税庁フォーマット）
- 作業時間95%削減（10時間 → 30分）

**外部API完全削除**（2025/11/01）:
- 削除理由: GCP環境不安定性・時間軸ミスマッチ・統計的有意性不足
- モデルリネーム: level2/3 → ensemble_full.pkl/ensemble_basic.pkl
- 効果: システム安定性向上・保守性+20%・シンプル設計回帰

**デイトレード特化**（2025/10/22）:
- 個別TP/SL実装・スイングトレード削除
- コードベース-1,041行削減（シンプル性・保守性向上）

### 核心システム基盤

**完全指値オンリー**: 年間¥150,000削減・約定率90-95%
**trading層レイヤードアーキテクチャ**: 5層分離・保守性大幅向上
**Graceful Degradation**: Container exit(1)完全解消・ゼロダウンタイム保証
**バックテスト高速化**: 10倍改善（45分実行）
**ML予測統合**: Strategy-Aware ML・ML統合率100%達成

---
