# CLAUDE.md - Phase 51.5-E完了・開発ガイド

**Claude Codeが即座に理解すべき開発指針と技術情報**

---

## 🎯 システム現状（最重要・即座理解）

### Phase 51.5-E完了ステータス（2025/11/04）

**現在の状況**: Phase 51.5シリーズ完全完了 ✅ → **Phase 51完走計画（Phase 51.6-51.11）**

**Phase 50.9: 外部API完全削除**（完了 ✅）:
- **目的**: GCP環境不安定性・時間軸ミスマッチ（日次 vs 5分足）・統計的有意性不足（+0.83%）により外部API削除
- **削除内容**:
  - `src/features/external_api.py`（436行）完全削除
  - `tests/unit/features/test_external_api.py`（402行）完全削除
  - `models/production/ensemble_level1.pkl`（4.2MB・70特徴量）削除
- **モデルリネーム**（重要：旧レベルシステム廃止）:
  - `ensemble_level2.pkl`（62特徴量） → **`ensemble_full.pkl`**（デフォルト）
  - `ensemble_level3.pkl`（57特徴量） → **`ensemble_basic.pkl`**（フォールバック）
- **特徴量変更**: 70特徴量 → 62特徴量 → **60特徴量**（Phase 51.5-A: 3戦略シグナル）
- **期待効果**: システム安定性向上・ゼロダウンタイム実現・保守性+20%・シンプル設計回帰
- **実装詳細**: `docs/開発履歴/Phase_50.md` Phase 50.9参照

**Phase 51.5シリーズ完了**（2025/11/03-04）:
- **Phase 51.5-A**: 戦略削減（5→3）・60特徴量固定システム確立
- **Phase 51.5-A Fix**: データ行数問題修正（1,081→17,272行）
- **Phase 51.5-A Fix 2**: MLモデル一括生成システム実装
- **Phase 51.5-B**: 動的戦略管理基盤（影響範囲93%削減・27→2ファイル）
- **Phase 51.5-C**: 本番環境緊急対応（5問題同時修正・45分完了）
- **Phase 51.5-D**: レガシーコード完全修正（システム整合性100%）
- **Phase 51.5-E**: 統合デプロイ・MLモデル再訓練（CI/CD成功・GCPデプロイ完了）
- **開発履歴**: `docs/開発履歴/Phase_51.5.md`（722行・7サブPhase記録）

**Phase 51完走計画**（Phase 51.6-51.11）:
- **基本方針**: データドリブンな戦略選択（各ステップでバックテスト評価）
- **Phase 51.6**: 新戦略実装（レンジ型・トレンド型厳選）+ バックテスト評価
- **Phase 51.7**: レジーム別戦略重み最適化 + バックテスト評価
- **Phase 51.8**: ML統合最適化（レジーム別）+ バックテスト評価
- **Phase 51.9**: バックテスト総合検証
- **Phase 51.10**: ペーパートレード検証（1週間）
- **Phase 51.11**: 本番展開
- **Phase 52以降**: 凍結（実運用3ヶ月データ収集後に再検討）

**開発基盤**（Phase 51.5完了により確立）:
- **拡張性**: Registry Pattern実装により戦略追加が2ファイルのみ（93%削減達成）
- **技術的負債**: ゼロ（Phase 51.5-D完全調査）
- **品質基盤**: 1,153テスト・68.77%カバレッジ
- **開発速度**: +40-60%向上見込み（動的戦略管理基盤・システム整合性100%）

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

**品質指標**（Phase 51.5-E完了後）:
- **テスト成功率**: 100%（1,153テスト全成功）
- **カバレッジ**: 68.77%（目標68.27%超過）
- **コード品質**: flake8・isort・black全てPASS
- **CI/CD**: GitHub Actions成功・GCP Cloud Runデプロイ完了

**運用仕様**:
- bitbank信用取引・BTC/JPY専用
- 24時間稼働（GCP Cloud Run）
- 月額700-900円（Phase 48コスト削減達成）
- 5分間隔実行（Phase 37.3最適化）
- 1万円スタート → 最大50万円（段階的拡大）

### システム概要

**AI自動取引システム**: 3戦略 + ML統合（**60特徴量固定**）による真のハイブリッドMLbot

**技術構成**:
- Python 3.13・MLライブラリ互換性最適化
- **3戦略統合**（Phase 51.5-A）: ATRBased・DonchianChannel・ADXTrendStrength
- **動的戦略管理**（Phase 51.5-B）: Registry Pattern・93%影響削減
- 3モデルアンサンブル（LightGBM 40%・XGBoost 40%・RandomForest 20%）
- 4時間足（トレンド）+ 15分足（エントリー）
- **Phase 51.5-E**: 60特徴量システム本番稼働開始

**リスク管理**:
- **TP/SL設定**: SL 1.5%・TP 1.0%・RR比0.67:1（Phase 49.18デイトレード特化・**レンジ型に最適**）
- **個別TP/SL管理**: エントリー毎に独立したTP/SL注文（Phase 46回帰）
- **完全指値オンリー**: 年間¥150,000削減（Phase 38.7.2）
- **適応型ATR**: ボラティリティ別SL調整（低2.5x・通常2.0x・高1.5x）
- **証拠金維持率80%確実遵守**（Phase 49.18）

**ML統合**（Phase 51.5-A完了）:
- **60特徴量固定システム**（Phase 51.5-A: 50基本+3戦略シグナル+7時間的）
  - 50テクニカル特徴量
  - 3戦略信号特徴量（Phase 51.5-A: ATRBased・DonchianChannel・ADXTrendStrength）
  - 7時間的特徴量（Phase 50.2: 曜日・時間帯・地域別市場時間）
- Strategy-Aware ML: 実戦略信号学習（Phase 41.8）
- ML統合率100%達成（Phase 41.8.5）
- 3段階統合ロジック（<0.45: 戦略のみ・0.45-0.60: 加重平均・≥0.60: ボーナス/ペナルティ）
- **2段階Graceful Degradation**（Phase 50.9: シンプル化）:
  - **Level 1（デフォルト）**: 60特徴量 ← **ensemble_full.pkl**（完全特徴量セット）
  - **Level 2（フォールバック）**: 57特徴量 ← **ensemble_basic.pkl**（戦略信号なし）
  - **Level 3（最終）**: DummyModel（全holdシグナル・システム継続動作保証）
  - **Phase 50.9完了**: 外部API依存削除・セマンティック命名採用・システム安定性向上
- **削除理由**: GCP環境不安定性・時間軸ミスマッチ（日次 vs 5分足）・統計的有意性不足（+0.83%）

---

## 🚀 必須コマンド（開発時必読）

### 品質チェック（開発前後必須）

```bash
# 品質チェック - 開発前後に必ず実行
bash scripts/testing/checks.sh

# Phase 50.8時点（Phase 50.9実装前）:
# ✅ 1,117テスト全成功（100%達成）
# ✅ 68.32%カバレッジ達成（65%目標超過）
# ✅ flake8・isort・black全てPASS
# ✅ 実行時間: 約74秒で完了

# Phase 50.9実装後の期待結果:
# ✅ 280テスト全成功（-46テスト・外部API関連削除）
# ✅ 68%以上カバレッジ維持
# ✅ flake8・isort・black全てPASS
# ✅ 実行時間: 約60秒で完了（高速化）
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

### データフロー（Phase 51.5-E完了後）

```
データ取得（Bitbank API・15分足直接取得）
    ↓
特徴量生成（15指標 → 50基本特徴量 + 7時間的特徴量 = 57特徴量）
    ↓
戦略実行（3戦略 → 3戦略信号特徴量追加 → 60特徴量）
    ↓
ML予測（ensemble_full.pkl: 60特徴量モデル → 信頼度）
    ↓
リスク評価（Kelly基準・ポジション制限）
    ↓
取引判断（個別TP/SL・適応型ATR・RR比0.67:1）
    ↓
取引実行（完全指値オンリー・bitbank API）
```

**Phase 51.5シリーズ変更点**:
- 戦略削減（5戦略 → **3戦略**）
- 特徴量最適化（62 → **60特徴量**）
- 動的戦略管理基盤実装（Registry Pattern）
- システム整合性100%達成
- 15分足直接API実装（Phase 51.5-C）

---

## 🎯 開発原則・品質基準

### 品質保証（必須遵守）

- **テスト実行**: 開発前後に`checks.sh`必須実行・1,153テスト100%維持・68.77%カバレッジ
- **カバレッジ**: 68%以上維持・新機能は必ずテスト追加
- **CI/CD**: GitHub Actions自動品質ゲート・失敗時は修正必須

**Phase 51.5-E完了後の品質指標**:
- 全テスト数: 1,153テスト（Phase 51.5-B: +58テスト追加）
- カバレッジ: 68.77%（目標68.27%超過）
- コード品質: flake8・black・isort全てPASS
- CI/CD: GitHub Actions成功・GCP Cloud Runデプロイ完了

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

### 必須確認事項（Phase 51.5-E完了後）

1. **品質チェック**: `bash scripts/testing/checks.sh`で1,153テスト・68.77%カバレッジ確認
2. **モデルファイル確認**: ensemble_full.pkl（60特徴量）・ensemble_basic.pkl（57特徴量）存在確認
3. **60特徴量動作確認**: 特徴量生成・ML予測・エントリー判断正常動作
4. **3戦略動作確認**: ATRBased・DonchianChannel・ADXTrendStrength稼働確認
5. **本番環境確認**: Cloud Run・60特徴量・ensemble_full.pkl使用確認
6. **動的戦略管理確認**: strategy_config.py・strategies.yaml・動的ロード正常動作
7. **設定整合性**: features.yaml・unified.yaml・thresholds.yaml確認

### 開発開始前チェック

1. **最新状況把握**: **Phase 51.5-E完了**・**Phase 51完走計画（Phase 51.6-51.11）**・ToDo.md確認
2. **品質基準**: 1,153テスト100%成功・68.77%カバレッジ維持必須
3. **設定管理**: ハードコード禁止・get_threshold()パターン遵守
4. **Phase 51.5理解**: 3戦略・60特徴量・動的戦略管理基盤（93%削減）・システム整合性100%
5. **Phase 51完走**: データドリブンな戦略選択・バックテスト評価重視・Phase 52以降凍結

---

**📅 最終更新**: 2025年11月04日 - **Phase 51.5-E完了**（統合デプロイ・MLモデル再訓練・CI/CD成功・GCPデプロイ完了）+ **Phase 51完走計画確定**（Phase 51.6-51.11・データドリブンな戦略選択・Phase 52以降凍結）
