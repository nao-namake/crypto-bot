# CLAUDE.md

## しおり（現在地）

| 項目 | 値 |
|------|-----|
| **現在Phase** | 79（Maker失敗100%+ML品質フィルタ機能不全 緊急修正）完了 |
| **直前の作業** | Phase 79: Maker価格をスプレッド内配置に修正 / ML品質フィルタ閾値0.55→0.65 |
| **次の予定** | デプロイ → 1週間運用 → 統計データで戦略判断 |
| **最新成果** | post_only拒否バグ修正（Phase 68設計矛盾）/ 品質フィルタ通過率100%→約30%目標 |
| **最終更新** | 2026年4月8日 |

> 開発履歴: `docs/開発履歴/SUMMARY.md`（Phase 1-77）、`docs/開発履歴/Phase_71-79.md`（最新）

---

## 推論言語

このプロジェクトでは**日本語で推論**してください。コード内のコメント・変数名は英語のまま維持しますが、思考プロセス・計画・説明は日本語で行ってください。

---

## システム概要

| 項目 | 値 |
|------|-----|
| **対象** | bitbank信用取引・BTC/JPY専用 |
| **稼働** | 24時間（GCP Cloud Run）・5分間隔 |
| **月額コスト** | 700-900円 |
| **証拠金** | 50万円 |
| **年利目標** | 10%（DD 10%許容） |
| **戦略数** | 6戦略（レンジ型4 + トレンド型2、CMFReversalがDonchianChannel置換） |
| **特徴量数** | 37特徴量（Phase 77: SHAP+Forward Selectionで最適化） |
| **MLモデル** | ProductionEnsemble（LGB40%/XGB40%/RF20%） |
| **ML方式** | メタラベリング（取引品質フィルタ: Go/No-Go判定） |

---

## クイックリファレンス

### 品質チェック（開発前後必須）

```bash
bash scripts/testing/checks.sh
# 期待結果: 全テスト成功・75%+カバレッジ・flake8/black/isort PASS
```

### システム実行

```bash
# ペーパートレード
bash scripts/paper/run_paper.sh

# 停止 / 状況確認
bash scripts/paper/run_paper.sh stop
bash scripts/paper/run_paper.sh status

# ライブトレード
python3 main.py --mode live
```

### GCP確認

```bash
# サービス稼働状況
TZ='Asia/Tokyo' gcloud run services describe crypto-bot-service-prod \
  --region=asia-northeast1 \
  --format="value(status.conditions[0].status,status.url)"

# 最新リビジョン
TZ='Asia/Tokyo' gcloud run revisions list \
  --service=crypto-bot-service-prod \
  --region=asia-northeast1 --limit=3

# ログ確認
gcloud logging read "resource.type=cloud_run_revision" --limit=10
```

### 分析コマンド

```bash
# ライブモード標準分析（24時間）
python3 scripts/live/standard_analysis.py
python3 scripts/live/standard_analysis.py --hours 48
python3 scripts/live/standard_analysis.py --quick

# バックテスト実行
bash scripts/backtest/run_backtest.sh

# バックテスト標準分析
python3 scripts/backtest/standard_analysis.py --from-ci
python3 scripts/backtest/standard_analysis.py results/backtest_result.json

# 戦略個別パフォーマンス分析
python3 scripts/analysis/strategy_performance_analysis.py

# シグナルシミュレーション（Phase 75: 事後検証）
python3 scripts/analysis/signal_simulation.py                          # 直近7日全足
python3 scripts/analysis/signal_simulation.py --with-signals           # GCPシグナル検証
python3 scripts/analysis/signal_simulation.py --start 2026-03-25 --end 2026-04-01 --full
```

---

## アーキテクチャ概要

### ディレクトリ構成

```
src/
├── core/                   # 基盤システム
│   ├── orchestration/      # TradingOrchestrator
│   ├── config/             # 設定管理（thresholds.yaml）
│   ├── execution/          # 取引実行制御
│   ├── reporting/          # レポート生成
│   └── services/           # GracefulShutdown・MarketRegimeClassifier
├── data/                   # Bitbank API・キャッシュ
├── features/               # 特徴量生成（15指標）
├── strategies/             # 6戦略（Registry Pattern）
├── ml/                     # ProductionEnsemble（3モデル）
├── trading/                # 取引管理（5層分離）
│   ├── core/               # enums・types
│   ├── balance/            # MarginMonitor
│   ├── execution/          # ExecutionService・OrderStrategy・TPSLManager・PositionRestorer
│   ├── position/           # Tracker・Limits・Cleanup
│   └── risk/               # IntegratedRiskManager
└── backtest/               # バックテストシステム

tax/                        # 税務システム（SQLite・移動平均法）
scripts/                    # 運用スクリプト
config/core/                # 設定ファイル群
models/production/          # MLモデル（週次更新）
```

### データフロー

```
Bitbank API（15分足取得）
    ↓
特徴量生成（37特徴量・SHAP最適化）
    ↓
ML予測（ensemble_full.pkl → 信頼度）
    ↓
レジーム判定（tight_range / normal_range / trending）
    ↓
動的戦略選択（レジーム別重みづけ適用）
    ↓
リスク評価（Kelly基準・ポジション制限）
    ↓
取引判断（レジーム別TP/SL適用）
    ↓
取引実行（完全指値・bitbank API）
```

### 設定管理

#### 1ファイル設定体系

| ファイル | 役割 |
|---------|------|
| `config/core/thresholds.yaml` | 全設定一元管理（環境設定 + パラメータ + 機能トグル） |

#### 設定参照パターン

```python
# ハードコード禁止
from src.core.config.threshold_manager import get_threshold

sl_rate = get_threshold("risk.sl_min_distance_ratio", 0.02)

# TP/SL設定はTPSLConfig定数を使用（文字列リテラル禁止）
from src.trading.execution.tp_sl_config import TPSLConfig

tp_ratio = get_threshold(TPSLConfig.TP_MIN_PROFIT_RATIO, 0.009)
sl_ratio = get_threshold(TPSLConfig.SL_MAX_LOSS_RATIO, 0.007)
regime_tp = get_threshold(TPSLConfig.tp_regime_path("tight_range", "min_profit_ratio"), 0.004)

# 機能トグル参照（thresholds.yaml の feature_flags セクション）
from src.core.config import get_features_config

features = get_features_config()
cooldown_enabled = features.get("trading", {}).get("cooldown", {}).get("enabled", True)
```

#### 動的戦略選択

```yaml
# thresholds.yaml
dynamic_strategy_selection:
  enabled: true
  regime_strategy_mapping:
    tight_range:    # レンジ型3戦略に集中
    normal_range:   # バランス型配分
    trending:       # トレンド型優先
    high_volatility: # 全戦略無効化
```

#### シークレット管理

- ローカル: `config/secrets/.env`（`.gitignore`で除外済み）
- GCP: Secret Manager（具体的バージョン番号使用。`key:latest`は禁止）

---

## 現行設定値

### 6戦略構成

| 区分 | 戦略名 | 核心ロジック |
|------|--------|-------------|
| **レンジ型** | BBReversal | BB位置主導 + RSIボーナス → 平均回帰 |
| **レンジ型** | StochasticDivergence | 価格とStochasticの乖離検出 → 反転 |
| **レンジ型** | ATRBased | ATR消尽率70%以上 → 反転期待（主力） |
| **レンジ型** | CMFReversal | CMF売り圧力減少→BUY / 買い圧力減少→SELL |
| **トレンド型** | MACDEMACrossover | MACDクロス + EMAトレンド確認 |
| **トレンド型** | ADXTrendStrength | ADX≥22 + DIクロス → トレンドフォロー |

### レジーム別重みづけ（Phase 74）

| 戦略 | tight_range | normal_range | trending |
|------|------------|-------------|---------|
| ATRBased | 0.35 | 0.25 | 0.15 |
| CMFReversal | 0.20 | 0.15 | 0.10 |
| BBReversal | 0.20 | 0.15 | 0.10 |
| StochasticReversal | 0.10 | 0.15 | 0.10 |
| ADXTrendStrength | 0.10 | 0.15 | 0.30 |
| MACDEMACrossover | 0.05 | 0.15 | 0.25 |

### レジーム別TP/SL設定

#### 平日

| レジーム | TP | SL | RR比 |
|---------|-----|-----|------|
| tight_range | 0.4% | 0.4% | 1.00:1 |
| normal_range | 1.0% | 0.7% | 1.43:1 |
| trending | 1.5% | 1.0% | 1.50:1 |

#### 土日（平日の約65%）

| レジーム | TP | SL |
|---------|-----|-----|
| tight_range | 0.25% | 0.25% |
| normal_range | 0.65% | 0.45% |
| trending | 1.0% | 0.65% |

### 固定金額TP/SL（Phase 75: SL距離正常化）

| 信頼度 | 閾値 | TP金額 | SL金額 | Net RR比 |
|--------|------|--------|--------|----------|
| 低 | <0.40 | 600円 | 800円 | 0.75:1 |
| 高 | >=0.40 | 750円 | 1,000円 | 0.75:1 |
| フォールバック | 信頼度不明 | 750円 | 1,000円 | 0.75:1 |

SL距離改善（0.015BTC基準）: 11,733円(0.11%)→45,067円(0.42%)

TP計算式: `TP価格 = エントリー価格 ± (必要含み益 / 数量)`
必要含み益: `目標純利益 + エントリー手数料(0.1%) + 利息 + 決済手数料(0%)`

SL計算式: `SL価格 = エントリー価格 ∓ (SL距離 / 数量)`
SL距離: `(目標最大損失 - エントリー手数料(0.1%) - 決済手数料(0.1%)) / ポジションサイズ`（Phase 70.2: entry_fee再包含）

### 手数料設定（2026年2月2日改定）

| 項目 | エントリー | TP決済 | SL決済 |
|------|----------|--------|--------|
| 手数料率 | 0%（Maker成功時）/ 0.1%（Taker） | 0%（Maker） | 0.1%（Taker） |
| TP/SL計算時 | 0.1%（Taker想定） | 0%（Maker想定） | 0.1%（Taker想定） |

### SL設定

| 設定 | 値 |
|------|-----|
| 注文タイプ | `stop_limit`（Phase 78: stop→stop_limit、スリッページ上限制御） |
| slippage_buffer | 0.5%（Phase 78: 0.8%→0.5%、stop_limit指値範囲） |
| skip_bot_monitoring | true |
| stop_limit_timeout | 900秒（Phase 69.3: 300→900秒） |
| 固定金額SL | 800-1,000円（Phase 75 信頼度別） |
| 日次損失上限 | 5,000円（1%） |
| 週次損失上限 | 20,000円（4%） |
| 連敗サイズ縮小 | 5回:50% / 6回:40% / 7回:25% / 8回:停止 |

---

## 開発原則

### 品質基準

- **開発前後**: `bash scripts/testing/checks.sh`必須実行
- **テスト**: 全テスト100%成功維持
- **カバレッジ**: 75%以上維持
- **コード品質**: flake8 / black / isort通過必須
- **CI/CD**: GitHub Actions自動品質ゲート

### コーディング規約

- **設定**: ハードコード禁止・`get_threshold()`パターン使用
- **ログ**: JST時刻・構造化ログ
- **テスト**: 単体・統合・エラーケーステスト完備
- **アーキテクチャ**: レイヤードアーキテクチャ遵守

### GCP特有の制約

| 制約 | 対策 |
|------|------|
| gVisor fork()制限 | RandomForest `n_jobs=1`固定 |
| Cloud Runタイムアウト | `signal.alarm`無効化 |
| Container再起動 | 起動時ポジション復元（実ポジションベース） |

### Git運用規則

| 規則 | 内容 |
|------|------|
| **全体コミット必須** | `git add .`を使用（個別add禁止） |
| **コミット前確認** | `git status`必須 |

```bash
git status && git add . && git commit -m "..." && git push origin main
```

---

## トラブルシューティング + ドキュメント索引

### よくあるエラー

| エラー | 対策 |
|--------|------|
| `'BitbankClient' has no attribute 'get_active_orders'` | `fetch_active_orders`を使用 |
| Container exit(1) | GCP制約対策確認（n_jobs=1, signal.alarm無効化） |
| bitbank 50062「保有建玉数量超過」 | 既存TP/SL注文キャンセル後に成行決済（Phase 68.2で修正済み） |

### デバッグコマンド

```bash
# importエラー確認
python3 -c "import sys; sys.path.insert(0, '.'); from src.core.logger import CryptoBotLogger"

# 設定整合性確認
python3 scripts/testing/dev_check.py validate

# GCPエラーログ
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" --limit=20
```

### ドキュメント索引

| カテゴリ | ファイル | 内容 |
|---------|---------|------|
| **運用** | [統合運用ガイド.md](docs/運用ガイド/統合運用ガイド.md) | デプロイ・日常運用・緊急対応 |
| **運用** | [GCP運用ガイド.md](docs/運用ガイド/GCP運用ガイド.md) | IAM権限・リソースクリーンアップ |
| **運用** | [システムリファレンス.md](docs/運用ガイド/システムリファレンス.md) | 仕様+実装の統合リファレンス |
| **運用** | [bitbank_APIリファレンス.md](docs/運用ガイド/bitbank_APIリファレンス.md) | API仕様・署名方式 |
| **運用** | [税務対応ガイド.md](docs/運用ガイド/税務対応ガイド.md) | 確定申告・移動平均法 |
| **履歴** | [SUMMARY.md](docs/開発履歴/SUMMARY.md) | 全Phase総括（Phase 1-77） |
| **履歴** | [Phase_71-79.md](docs/開発履歴/Phase_71-79.md) | 最新Phase詳細 |
| **計画** | [ToDo.md](docs/開発計画/ToDo.md) | 開発計画 |
