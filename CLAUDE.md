# CLAUDE.md - Phase 52.5完了・開発ガイド

**Claude Codeが即座に理解すべき開発指針と技術情報**

---

## 🎯 システム現状（最重要・即座理解）

### Phase 52.5完了ステータス（2025/11/18）

**現在の状況**: Phase 52.5完了 ✅ → **本番環境安定稼働中**（設定ファイル最適化・1,252テスト100%成功）

**Phase 50.9: 外部API完全削除**（完了 ✅）:
- **目的**: GCP環境不安定性・時間軸ミスマッチ（日次 vs 5分足）・統計的有意性不足（+0.83%）により外部API削除
- **削除内容**:
  - `src/features/external_api.py`（436行）完全削除
  - `tests/unit/features/test_external_api.py`（402行）完全削除
  - `models/production/ensemble_level1.pkl`（4.2MB・70特徴量）削除
- **モデルリネーム**（重要：旧レベルシステム廃止）:
  - `ensemble_level2.pkl`（62特徴量） → **`ensemble_full.pkl`**（デフォルト）
  - `ensemble_level3.pkl`（57特徴量） → **`ensemble_basic.pkl`**（フォールバック）
- **特徴量変更**: 70特徴量 → 62特徴量 → **55特徴量**（Phase 51.7: 6戦略シグナル）
- **期待効果**: システム安定性向上・ゼロダウンタイム実現・保守性+20%・シンプル設計回帰
- **実装詳細**: `docs/開発履歴/Phase_50.md` Phase 50.9参照

**Phase 51完走完了**（2025/11/05-11/12）:
- **Phase 51.6**: TP/SL見直し（RR比0.7:1 → 0.67:1）・基礎設定統一
- **Phase 51.7**: 6戦略実装完了（レンジ3・トレンド3）・55特徴量確立
- **Phase 51.8**: レジーム別ポジション制限・ML統合最適化
- **Phase 51.9**: 真の3クラス分類実装（F1改善+9.7%）・バックテスト検証
- **Phase 51.10**: TP/SL孤児注文完全解決（Option D実装）
- **Phase 51.11**: 本番デプロイ完了・Phase 51完走宣言

**Phase 52シリーズ完了**（2025/11/12-11/18）:
- **Phase 52.0**: レジーム別動的TP/SL実装（tight_range/normal_range/trending）
- **Phase 52.1**: 週次バックテスト自動化（GitHub Actions）
- **Phase 52.2**: 本番シミュレーションモード・DrawdownManager統合
- **Phase 52.3**: コード品質改善（flake8エラー完全解消）
- **Phase 52.4**: CI/CD系統整理（特徴量数一元化・環境変数化）
- **Phase 52.5**: 設定ファイル最適化完了（重複削除110行・Single Source of Truth確立）

**開発基盤**（Phase 52.5完了時点）:
- **拡張性**: Registry Pattern実装により戦略追加が2ファイルのみ（93%削減達成）
- **技術的負債**: ゼロ（Phase 51.5-D完全調査・Phase 52.3コード品質改善・Phase 52.5設定最適化）
- **品質基盤**: 1,252テスト・66.78%カバレッジ達成
- **設定管理**: Single Source of Truth確立・重複削除110行・使用箇所ドキュメント化
- **開発速度**: 安定稼働優先（動的戦略管理基盤・システム整合性100%）

---

### Phase 50完了ステータス（Phase 50.1-50.9）

**Phase 50.9完了内容**（2025/11/01）:
- **外部API完全削除**（62特徴量固定システム・2段階Graceful Degradation）
- **モデルファイルリネーム**（ensemble_level2/3 → ensemble_full/basic）
- **コード削減**（~1,438行削除・保守性+20%）
- **シンプル設計回帰**（KISS原則徹底・ゼロダウンタイム保証）

**Phase 50.8完了内容**:
- **Graceful Degradation完全実装**（外部API障害対応・動的モデル選択）
- **本番環境0エントリー問題解決**（根本原因：外部API不安定性）

**その他Phase完了**:
- **Phase 49**: バックテスト完全改修（信頼性100%達成・TradeTracker統合・matplotlib可視化）
- **Phase 48**: Discord週間レポート（通知99%削減・コスト35%削減）
- **Phase 47**: 確定申告対応システム（作業時間95%削減）

**品質指標**（Phase 52.5完了後）:
- **テスト成功率**: 100%（1,252テスト）
- **カバレッジ**: 66.78%（65%目標超過）
- **コード品質**: flake8・isort・black全てPASS
- **CI/CD**: GitHub Actions成功・GCP Cloud Runデプロイ完了
- **設定管理**: Single Source of Truth確立・重複削除110行

**運用仕様**:
- bitbank信用取引・BTC/JPY専用
- 24時間稼働（GCP Cloud Run）
- 月額700-900円（Phase 48コスト削減達成）
- 5分間隔実行（Phase 37.3最適化）
- 1万円スタート → 最大50万円（段階的拡大）

### システム概要

**AI自動取引システム**: 6戦略 + ML統合（**55特徴量システム**）による真のハイブリッドMLbot

**技術構成**:
- Python 3.13・MLライブラリ互換性最適化
- **6戦略統合**（Phase 51.7）:
  - レンジ型3個: ATRBased・DonchianChannel・BBReversal
  - トレンド型3個: ADXTrendStrength・StochasticReversal・MACDEMACrossover
- **動的戦略管理**（Phase 51.5-B）: Registry Pattern・93%影響削減
- 3モデルアンサンブル（LightGBM 50%・XGBoost 30%・RandomForest 20%）
- 4時間足（トレンド）+ 15分足（エントリー）
- **Phase 52.5**: 55特徴量システム本番稼働中・設定ファイル最適化完了

**リスク管理**:
- **TP/SL設定**（Phase 52.0レジーム別動的設定）:
  - tight_range: TP 0.6% / SL 0.8%
  - normal_range: TP 1.0% / SL 0.7%（Phase 51.6基本設定）
  - trending: TP 2.0% / SL 2.0%
- **個別TP/SL管理**: エントリー毎に独立したTP/SL注文（Phase 46回帰）
- **完全指値オンリー**: 年間¥150,000削減（Phase 38.7.2）
- **適応型ATR**: ボラティリティ別SL調整（低2.5x・通常2.0x・高1.5x）
- **証拠金維持率80%確実遵守**（Phase 49.18）

**ML統合**（Phase 52.4-A完了）:
- **55特徴量システム**（Phase 51.7確立・Phase 52.4-A一元管理）:
  - 49基本テクニカル特徴量
  - 6戦略信号特徴量（Phase 51.7: 6戦略すべてのシグナル）
  - feature_order.jsonが唯一の真実（Single Source of Truth）
- **真の3クラス分類**（Phase 51.9）:
  - 0=sell, 1=hold, 2=buy
  - F1スコア+9.7%改善
- Strategy-Aware ML: 実戦略信号学習（Phase 41.8）
- ML統合率100%達成（Phase 41.8.5）
- 3段階統合ロジック（<0.45: 戦略のみ・0.45-0.60: 加重平均・≥0.60: ボーナス/ペナルティ）
- **2段階Graceful Degradation**（Phase 50.9）:
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

# Phase 52.5時点:
# ✅ 1,252テスト・100%成功
# ✅ 66.78%カバレッジ達成（65%目標超過）
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

- **テスト実行**: 開発前後に`checks.sh`必須実行・1,252テスト100%維持・66.78%カバレッジ
- **カバレッジ**: 65%以上維持・新機能は必ずテスト追加
- **CI/CD**: GitHub Actions自動品質ゲート・失敗時は修正必須

**Phase 52.5完了後の品質指標**:
- 全テスト数: 1,252テスト（Phase 52シリーズ: +99テスト追加）
- カバレッジ: 66.78%（目標65%超過）
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

## 🔧 重要技術ポイント（Phase履歴）

### Phase 49（2025/10/26）- バックテスト完全改修

**Phase 49.16: TP/SL計算完全見直し**
- strategy_utils.py・executor.pyのハードコード値削除
- `get_threshold()`パターン適用（設定管理統一）
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

### Phase 50（2025/10/27-11/01）- 外部API統合→削除の教訓

**Phase 50.1-50.8完了内容**:
- **Phase 50.1**: 3段階Graceful Degradation実装・TP/SL修正・証拠金維持率修正
- **Phase 50.2**: 時間的特徴量追加（7特徴量）
- **Phase 50.3**: 外部API統合（Yahoo Finance・Alternative.me・8特徴量）
- **Phase 50.4**: 証拠金維持率80%完全修正（API直接取得）
- **Phase 50.5**: SL注文保護・Phase 42完全削除
- **Phase 50.6**: 外部API取得完全修正（asyncio.to_thread()実装）
- **Phase 50.7**: 3レベルモデルシステム・バックテスト検証
- **Phase 50.8**: Graceful Degradation完全実装・動的モデル選択

**Phase 50.9完了**（外部API完全削除）:
- **削除理由**: GCP環境不安定性・時間軸ミスマッチ（日次 vs 5分足）・統計的有意性不足（+0.83%）
- **削除内容**: external_api.py完全削除・ensemble_level1.pkl削除
- **モデルリネーム**: level2/3 → ensemble_full.pkl/ensemble_basic.pkl（レベルシステム廃止）
- **特徴量変更**: 70 → 62特徴量に最適化
- **効果**: システム安定性向上・ゼロダウンタイム・保守性+20%・シンプル設計回帰

**レガシーシステムからの教訓**:
- 外部API依存は GCP環境で根本的に不安定
- 日次更新データは5分足取引に不適合（288回中287回同じ値）
- 統計的有意性の慎重な評価必要（+0.83%は誤差範囲内）
- 複雑性増加 vs 効果のトレードオフ慎重判断

### Phase 46（2025/10/22）- デイトレード特化・個別TP/SL実装

**実施内容**:
- **個別TP/SL実装**（エントリー毎に独立したTP/SL注文）
- **デイトレード特化設定**: 初期設定後Phase 49.18で最終調整（SL 1.5%・TP 1.0%・RR比0.67:1）
- **コードベース大幅簡略化**: シンプル設計・保守性向上

**効果**: シンプル性・保守性大幅向上・予測可能な動作・デバッグ容易性確保

### Phase 41.8.5（2025/10/17）- ML統合閾値最適化

- `min_ml_confidence`: 0.6 → 0.45
- `high_confidence_threshold`: 0.8 → 0.60
- ML統合率: 10% → 100%達成
- 3段階統合ロジック再設計

### Phase 41.8（2025/10/17）- Strategy-Aware ML

- 55特徴量学習（49基本+6戦略信号）
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

### 必須確認事項（Phase 52.5完了後）

1. **品質チェック**: `bash scripts/testing/checks.sh`で1,252テスト・66.78%カバレッジ確認
2. **モデルファイル確認**: ensemble_full.pkl（55特徴量）・ensemble_basic.pkl（49特徴量）存在確認
3. **55特徴量動作確認**: 特徴量生成・ML予測・エントリー判断正常動作
4. **6戦略動作確認**: ATRBased・DonchianChannel・ADXTrendStrength・BBReversal・StochasticReversal・MACDEMACrossover稼働確認
5. **本番環境確認**: Cloud Run・55特徴量・ensemble_full.pkl使用確認
6. **動的戦略管理確認**: strategies.yaml・動的ロード正常動作
7. **設定整合性**: features.yaml・unified.yaml・thresholds.yaml・feature_order.json確認（Single Source of Truth）

### 開発開始前チェック

1. **最新状況把握**: **Phase 52.5完了**・**Phase 51/52完走完了**・docs/開発計画/ToDo.md確認
2. **品質基準**: 1,252テスト100%成功・66.78%カバレッジ維持必須
3. **設定管理**: ハードコード禁止・get_threshold()パターン遵守・Single Source of Truth（feature_order.json）
4. **Phase 52.5理解**: 6戦略・55特徴量・動的戦略管理基盤（93%削減）・設定最適化完了（重複削除110行）
5. **本番安定稼働**: レジーム別動的TP/SL・DrawdownManager統合・週次バックテスト自動化

---

**📅 最終更新**: 2025年11月18日 - **Phase 52.5完了**（設定ファイル最適化・重複削除110行・Single Source of Truth確立・1,252テスト100%成功）
