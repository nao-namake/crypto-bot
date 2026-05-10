# CLAUDE.md

## しおり（現在地）

| 項目 | 値 |
|------|-----|
| **現在Phase** | 84（エントリー機会拡大）デプロイ完了 |
| **直前の作業** | Phase 84: ML閾値yaml化(0.55→0.65)・同方向制限1→2・ADX強トレンド継続順張り |
| **次の予定** | 24-48h観測→エントリー数・レジーム別比率・SL適用率確認 |
| **最新成果** | Phase 83C後24h ゼロエントリーの真因(ハードコード0.55閾値+同方向制限+ADX hold)を3点修正 |
| **最終更新** | 2026年5月10日 |

> 開発履歴: `docs/開発履歴/SUMMARY.md`（Phase 1-77）、`docs/開発履歴/Phase_71-81.md`、`docs/開発履歴/Phase_82.md`、`docs/開発履歴/Phase_83.md`、`docs/開発履歴/Phase_84.md`（最新）

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

### 固定金額TP/SL（Phase 83B: TP1000/SL500/floor撤廃 RR比2.0:1）

| 信頼度 | 閾値 | TP金額 | SL金額 | RR比 |
|--------|------|--------|--------|------|
| 低 | <0.40 | 800円 | 400円 | 2.0:1 |
| 高 | >=0.40 | 1,000円 | 500円 | 2.0:1 |

**Phase 83B 変更理由**: Phase 83A-2のSL拡大方針(1500円/floor0.7%)で14日運用結果は-8,522円・SL平均-1,637円と深刻。`scripts/analysis/sl_simulation.py` でTP24件をbitbank 15分足再現したところ、SL500円まで縮小しても勝率95.5%維持・SL転落は1件のみ。RR比意識への方針転換で採算ライン勝率33.3%（現状53.3%でも+黒字想定）。

**SL floor撤廃（Phase 83B）**:
- `min_distance.enabled: false` で floor 0.7%強制を無効化
- 固定金額SL距離が直接適用される（`sl_amount / position_size + 手数料`）
- 例: amount 0.015 BTC、SL目標500円 → SL距離 ≒ 33,333円 + 手数料 ≒ 約0.27%

TP計算式: `TP価格 = エントリー価格 ± (必要含み益 / 数量)`
必要含み益: `目標純利益 + エントリー手数料(0.1%) + 利息 + 決済手数料(0%)`

SL計算式: `SL価格 = エントリー価格 ∓ (SL距離 / 数量)` + floor 0.7%強制
SL距離: `max((目標最大損失 - エントリー手数料(0.1%) - 決済手数料(0.1%)) / ポジションサイズ, エントリー価格 * 0.007)`

### 手数料設定（2026年2月2日改定）

| 項目 | エントリー | TP決済 | SL決済 |
|------|----------|--------|--------|
| 手数料率 | 0%（Maker成功時）/ 0.1%（Taker） | 0%（Maker） | 0.1%（Taker） |
| TP/SL計算時 | 0.1%（Taker想定） | 0%（Maker想定） | 0.1%（Taker想定） |

### SL設定

| 設定 | 値 |
|------|-----|
| 注文タイプ | `stop`（成行）（Phase 80: stop_limit→stopロールバック、Phase 69.8の教訓再確認） |
| slippage_buffer | 0.8%（Phase 69.6設定維持） |
| skip_bot_monitoring | true |
| stop_limit_timeout | 900秒（Phase 69.3: 300→900秒） |
| 固定金額SL | 1,200-1,500円（Phase 83A-2 信頼度別）+ floor 0.7%強制 |
| 日次損失上限 | 5,000円（1%） |
| 週次損失上限 | 20,000円（4%） |
| 連敗サイズ縮小 | 5回:50% / 6回:40% / 7回:25% / 8回:停止 |
| 同方向ポジション上限 | **2件**（Phase 84: 1→2 緩和） |

### Maker戦略（Phase 79修正）

| 設定 | 値 |
|------|-----|
| 価格配置 | スプレッド内（Phase 79: best_bid直接配置→spread内に修正） |
| improvement | max(1, min(spread×0.1, spread-1)) |
| spread<2円 | Maker不可、即Takerフォールバック |
| timeout | 60秒、リトライ3回 |
| fallback | Maker失敗時はTakerで成行注文 |

### ML品質フィルタ（Phase 83B-ML 再学習）

メタラベリング（Triple Barrier Method）方式。MLは方向予測ではなく、戦略の出した取引が成功するかを判定。
Phase 83B-ML: TP1000/SL500/floor撤廃に合わせ再学習（meta_tp_ratio 0.006 / meta_sl_ratio 0.0045）。

| 閾値 | 値 | 動作 |
|------|-----|------|
| accept_threshold | **0.58**（維持） | p(1)≥0.58 → 取引承認 |
| reject_threshold | **0.42**（維持） | p(1)<0.42 → 拒否 |
| uncertain_penalty | **0.5**（維持） | 中間帯(0.42-0.58)は信頼度を50%縮小 |
| high_confidence_failure_threshold | **0.65**（Phase 84） | ml_pred==0 かつ confidence≥0.65 で拒否（旧ハードコード0.55） |

**Phase 84 補足**: confidence は `max(p_0, p_1)`（class 1確率ではない）。ml_pred==0 + confidence=0.808 なら失敗確信80.8%＝正常な拒否動作。

**再学習後モデル信頼度分布**（2026/5/8-9学習、Phase 83B-ML）:
- アンサンブル p(1) mean=0.652, std=0.149, range=[0.243-0.896]
- CV F1: LGB 0.612±0.032 / XGB 0.583±0.060 / RF 0.552±0.075（Phase 83A-3 0.612と一致）
- 学習サンプル: 35,036件（365日分、2025-05-08〜2026-05-07）
- class_distribution: success 31.4% / failure 68.6%
- ランダムデータ推論: accept 72% / middle 17% / reject 11%（前回 24.1/66.7/9.3 から大幅変化）
- 高信頼度(>60%)比率: 71%
- 極端予測 >0.75: 28%（要監視・前回0%）

**注意**: meta_sl_ratio が前回より厳しいため信頼度上振れ。デプロイ後の実データ推論で accept率が高すぎる場合（>50%）、accept_threshold を 0.65 に引き上げ要検討。

**モデルバックアップ**:
- `models/production/ensemble_{full,basic}.phase82.pkl.bak`: Phase 82モデル
- `models/production/ensemble_{full,basic}.phase83a.pkl.bak`: Phase 83A-3モデル

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
| **履歴** | [Phase_71-81.md](docs/開発履歴/Phase_71-81.md) | 最新Phase詳細 |
| **計画** | [ToDo.md](docs/開発計画/ToDo.md) | 開発計画 |
