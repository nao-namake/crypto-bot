# CLAUDE.md

## しおり（現在地）

| 項目 | 値 |
|------|-----|
| **現在Phase** | **Phase 86-89 総合レビュー完了 + P0+P1 軽微修正完了（2026-05-16）→ ML 再学習 v7 待ち（macro F1 で真の性能確認）** |
| **直前の作業** | Phase 86-89 全 72 観点レビュー + P0+P1 修正（placeholder/MEMORY/cache/yaml warning/macro F1/cross_asset リーク防止/365 日）|
| **次の予定** | ML 再学習 v7 → 真の性能 (macro F1) 確認 → 実機 1 週間観察 → Phase 90 計画 |
| **直近インシデント** | ML 評価指標の構造的歪み発見（weighted F1 でランダム予測と同等の見かけ性能・修正済）|
| **Phase 87 達成** | Critical 5 + High 10 全完了（本番デプロイ済） |
| **Phase 88 達成** | I1-I4 GCPコスト 4件 + H11 孤児SL + M1-M5 + L1-L3 |
| **Phase 89-α 達成** | Stage 1 取引判断 gating + Stage 3 GCP リソース整理 + Stage 2 特徴量キャッシュ |
| **Phase 89-β 達成** | Fractional Kelly + 特徴量 37→47 + Purged K-Fold + Drift 検出（Bonferroni 補正）|
| **Phase 89-γ 達成** | N-BEATS + 4 モデル化 + HMM + VPIN +3 + 特徴量 47→52 + Auto Retraining |
| **Phase 89-δ 達成** | WebSocket + BTC-ETH 相関 +3 特徴量（52→55）+ マルチペア基盤 |
| **Phase 89 配線修正** | C1-C7（DI 漏れ + SL placeholder バグ）+ H1-H12（永続化 / Bonferroni / VPIN / Kelly / WebSocket cleanup 等） |
| **Phase 89 NB1-NB9** | N-BEATS 完全版（StandardScaler + 200 epoch + Early Stopping + Kaiming init + class_weights + validation メタラベリング対応） |
| **Phase 86-89 レビュー** | 72 観点・Critical ゼロ・軽微 9 件（P0/P1 4 件修正完了・P2 5 件 Phase 90 繰越） |
| **P0+P1 修正完了** | sl_monitor placeholder 統一 / MEMORY 768→1024 / eth_jpy cache 統一 / yaml warning / **macro F1** / cross_asset リーク防止 / 訓練 180→365 日 |
| **特徴量数** | 37 → **55**（+18: funding/sentiment/microstructure/macro_lite/microstructure_advanced/cross_asset 6 カテゴリ追加） |
| **ML モデル** | 3 → **4**（N-BEATS 追加） |
| **モデル性能（旧 weighted F1）** | ⚠️ LGB 0.612→0.893 等の改善は**評価指標歪み**（クラス不均衡 HOLD 94% + weighted F1 = ランダム予測と同水準）|
| **モデル性能（macro F1・真の指標）** | ML 再学習 v7 で確認予定（Phase 84/85 との公平比較可能化） |
| **TPSL 検証結果** | TPSLCalculator 実装は健全。Phase 85 報告 +362円/件は手数料**未控除**の期待値・真の期待値は **+138-254 円/件**（実機運用に影響なし）|
| **追加課金** | **ゼロ**（GPU 不採用 / LLM 不採用 / 全て無料 API） |
| **GCP 月額** | 現状 ¥3,000 → Stage 1+3 後 **¥1,400-1,700 見込み**（実測待ち） |
| **最終更新** | 2026年5月16日 - Phase 86-89 総合レビュー + P0+P1 修正完了 |

> **🚀 セッション再開時は `docs/開発計画/ToDo.md` の「セッション再開時の手順」セクションを最優先で確認**
>
> 詳細計画: `docs/開発計画/ToDo.md` / `~/.claude/plans/c-gleaming-ladybug.md`（Phase 89 修正 + N-BEATS 完全版プラン）
> 開発履歴: `docs/開発履歴/SUMMARY.md`（Phase 1-77）、`docs/開発履歴/Phase_71-81.md`、`Phase_82.md`〜`Phase_89.md`

---

## 🚀 セッション再開時の最優先タスク（2026-05-17 時点・ML 再学習 v7 待ち）

**進行中**: ML 再学習 v7 (run id **25971359708**) が GitHub Actions で稼働中（起動: 2026-05-16 19:53 UTC・50-70 分見込み・365 日データ + 4 モデル + N-BEATS + HMM）。

### Step 1: ML 再学習 v7 の完了確認（最優先・1 分）

```bash
gh run view 25971359708 --json status,conclusion
# 期待: {"conclusion":"success","status":"completed"}
```

- **success** ならば Step 2 へ
- **failure** ならば `gh run view 25971359708 --log-failed | tail -50` で原因確認
- **timeout** ならば再学習時間延長 or n_trials 削減検討

### Step 2: 新モデル取得 + macro F1 比較表作成（必須・30 分）

```bash
git pull origin main  # 新モデル取得

venv/bin/python3 -c "
import json
print('=== macro F1 比較（v7 真の性能 vs 旧 weighted F1）===')

# Phase 84 backup
with open('models/production/production_model_metadata.phase84.json.bak') as f:
    p84 = json.load(f)

# Phase 89 buggy backup
with open('models/production/phase89_buggy_nbeats_metadata.json.bak') as f:
    p89b = json.load(f)

# Phase 89 v7 (新)
with open('models/production/production_model_metadata.json') as f:
    v7 = json.load(f)

# 各モデルの metric 比較表を作成
for m in ['lightgbm', 'xgboost', 'random_forest', 'nbeats']:
    print(f'\\n## {m}')
    print(f'  Phase 84 weighted F1: {p84[\"performance_metrics\"].get(m, {}).get(\"f1_score\", \"-\")}')
    print(f'  Phase 89 buggy weighted F1: {p89b[\"performance_metrics\"].get(m, {}).get(\"f1_score\", \"-\")}')
    print(f'  Phase 89 v7 macro F1: {v7[\"performance_metrics\"].get(m, {}).get(\"f1_score\", \"-\")}  ← 真の指標')
    print(f'  Phase 89 v7 CV F1 mean: {v7[\"performance_metrics\"].get(m, {}).get(\"cv_f1_mean\", \"-\")}')
"
```

### Step 3: 真の改善幅評価（必須）

判定基準:
- **macro F1 > 0.6**: 真の改善あり・喜べる結果
- **macro F1 0.4-0.6**: 部分的改善・実機観察で確認
- **macro F1 < 0.4**: ほぼランダム水準・P2 項目（Transformer/LLM）の Phase 90 計画が急務

### Step 4: 結果次第

- **改善あり**: 実機 1 週間観察 (`scripts/live/standard_analysis.py --hours 24`) フェーズ
- **改善微小**: weighted F1 と乖離度合いから「過去同じ失敗パターン」かを判定 → Phase 90 で根本対策

### 直近の重要文脈

- **ユーザーから「見かけだけの性能で過去失敗した経緯あり」と指摘あり** → 評価指標 weighted → macro へ修正済（P0-2）
- **cross_asset pickle リーク防止済**（P0-3）→ v7 ではリーク除外
- **訓練 180→365 日統一済**（P1-4）→ Phase 84/85 と公平比較可能
- **TPSL +362円/件は手数料未控除**: 真の期待値 +138-254 円/件（docs 訂正済）

### 関連ファイル

- `~/.claude/plans/c-gleaming-ladybug.md`（Phase 86-89 レビュー + P0+P1 修正計画）
- `docs/開発履歴/Phase_89.md` 末尾「Phase 86-89 総合レビュー + P0+P1 修正」セクション
- 旧モデル backup: `models/production/{ensemble_full.phase84.pkl.bak, ensemble_full.phase89_buggy_nbeats.pkl.bak}`
- ロールバック手順: `docs/運用ガイド/Phase89_N-BEATS_rollback.md`

---

## 🚀 Phase 89 リリース完了 - 次の 5 アクション（参考・履歴用）

| Step | アクション | 必須 | 時間 |
|------|-----------|------|------|
| 1 | **既知の問題調査**（macOS SEGFAULT / pickle ハング） | 任意 | - |
| 2 | **手動 ML 再学習**: `gh workflow run model-training.yml --ref main -f n_trials=50` | 必須 | 10分 |
| 3 | **新モデル整合性確認**: `joblib.load('models/production/ensemble_full.pkl').n_features_in_ == 55` | 必須 | 1分 |
| 4 | **本番デプロイ**: `git push origin main` | 必須 | 10分 |
| 5 | **実機 1 週間観察**: 勝率改善 + Drift 検知 + Auto Retraining trigger | 必須 | 7日 |

詳細手順とロールバック手順: `docs/開発計画/ToDo.md` 「🚀 セッション再開時の手順」セクション

---

## 推論言語

このプロジェクトでは**日本語で推論**してください。コード内のコメント・変数名は英語のまま維持しますが、思考プロセス・計画・説明は日本語で行ってください。

---

## システム概要

| 項目 | 値 |
|------|-----|
| **対象** | bitbank信用取引・BTC/JPY専用 |
| **稼働** | 24時間（GCP Cloud Run）・5分間隔 |
| **月額コスト** | **現状: 約3,000円**（min_instances=1 常時稼働分が主因）/ Phase 88 I3 完了後の目標: **300-500円** |
| **証拠金** | 50万円 |
| **年利目標** | 10% (Phase 88 まで) / Phase 89-91 で **15-18%** / Phase 92 で **17-20%**（DD 10%許容） |
| **戦略数** | 6戦略（レンジ型4 + トレンド型2、CMFReversalがDonchianChannel置換） |
| **特徴量数** | 37特徴量（Phase 77: SHAP+Forward Selection）→ Phase 89: 47-50 → Phase 91: 50-55 |
| **MLモデル** | ProductionEnsemble（LGB40%/XGB40%/RF20%）→ Phase 90: + N-BEATS 軽量版 |
| **ML方式** | メタラベリング（品質フィルタ Go/No-Go）+ Phase 90: HMM レジーム検出補強 + LLM センチメント |

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

### レジーム別重みづけ（Phase 85: trending全停止）

| 戦略 | tight_range | normal_range | trending |
|------|------------|-------------|---------|
| ATRBased | 0.35 | 0.25 | **0.0** |
| CMFReversal | 0.20 | 0.15 | **0.0** |
| BBReversal | 0.20 | 0.15 | **0.0** |
| StochasticReversal | 0.10 | 0.15 | **0.0** |
| ADXTrendStrength | 0.10 | 0.15 | **0.0** |
| MACDEMACrossover | 0.05 | 0.15 | **0.0** |

**Phase 85 trending全停止根拠**: 過去30日 trending 23件で全シナリオ赤字（TP1500/SL2000 floor 0.7%でも勝率45%・-8,500円）。設計思想「レンジ専用bot」と完全合致。

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

### 固定金額TP/SL（Phase 85: レジーム別設定 + floor 0.7%復活）

#### レジーム別TP/SL目標

| レジーム | TP目標 | SL目標 | 実TP距離 | 実SL距離 | 過去30日勝率 | 期待値/件 |
|---------|--------|--------|---------|---------|-------------|----------|
| **tight_range** | **1,500円** | **2,000円** | 0.70% | 0.86% | **67.9%** | **+362円** ✅ |
| **normal_range** | **500円** | **1,500円** | 0.23% | 0.70% | 75.0% | ±0円 |
| **trending** | エントリー停止 | エントリー停止 | - | - | - | 損失回避 |

#### 信頼度別TP/SL目標（フォールバック用）

| 信頼度 | 閾値 | TP金額 | SL金額 |
|--------|------|--------|--------|
| 低 | <0.40 | 1,200円 | 1,500円 |
| 高 | >=0.40 | 1,500円 | 2,000円 |

**Phase 85 変更理由**:
1. **Phase 83B floor撤廃は虚像**: `sl_simulation.py` の手数料加算バグ（実コードは控除）で SL距離を約7倍過大評価。「勝率95.5%」は嘘
2. **真の運用シミュ実証**: bitbank API から過去30日全エントリー106件取得→TP/SL先着判定→**全シナリオ赤字**判明
3. **レジーム別が黒字化の鍵**: tight_range で TP1500/SL2000 + floor 0.7% で +362円/件、trendingは全シナリオ赤字
4. **設計思想と合致**: ユーザー「botはレンジ専用」設計 → trending時のエントリー停止が正解

**SL floor 0.7% 復活**:
- `min_distance.enabled: true`, `ratio: 0.007`
- BTC 15分足ノイズ幅（0.3-0.5%）を確実に超える SL距離 0.7%以上を強制
- Phase 83A-2 状態に近い（ただし TP/SL目標金額はレジーム別）

**Phase 86 TP/SL計算の単一実装**: `src/trading/execution/tpsl_calculator.py` の `TPSLCalculator` クラスがすべてのTP/SL計算箇所で使用される唯一の実装（旧4箇所分散を解消）。

TP計算式: `TP価格 = エントリー価格 ± (gross_needed / 数量)`
gross_needed: `TP目標 + エントリー手数料(0.1%) + 決済手数料(Maker 0%想定で 0)` （Phase 86: entry_fee加算バグ修正）

SL計算式: `SL価格 = エントリー価格 ∓ (SL距離 / 数量)`
SL距離: `max((SL目標 - エントリー手数料(0.1%) - 決済手数料(Taker 0.1%)) / ポジションサイズ, エントリー価格 * 0.007)`

実例（amount 0.015 BTC、BTC 12.84M円、tight_range TP1500/SL2000）:
- TP距離 = (1500+193+0)/0.015 = **112,840円 = 0.879%** （Phase 86: +13%拡大）
- SL距離 = max((2000-193-193)/0.015, 12.84M×0.007) = max(107,613円, 89,880円) = **107,613円 = 0.838%**

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
| 同方向ポジション上限 | **1件**（Phase 85: 2→1 ロールバック・Phase 84で損失40%増幅） |

### Maker戦略（Phase 79修正）

| 設定 | 値 |
|------|-----|
| 価格配置 | スプレッド内（Phase 79: best_bid直接配置→spread内に修正） |
| improvement | max(1, min(spread×0.1, spread-1)) |
| spread<2円 | Maker不可、即Takerフォールバック |
| timeout | 60秒、リトライ3回 |
| fallback | Maker失敗時はTakerで成行注文 |

### ML品質フィルタ（Phase 85 再学習）

メタラベリング（Triple Barrier Method）方式。MLは方向予測ではなく、戦略の出した取引が成功するかを判定。
Phase 85: tight基準 TP1500/SL2000 + floor 0.7%に合わせ再学習（meta_tp_ratio 0.007 / meta_sl_ratio 0.0086）。

| 閾値 | 値 | 動作 |
|------|-----|------|
| accept_threshold | **0.58**（維持） | p(1)≥0.58 → 取引承認 |
| reject_threshold | **0.42**（維持） | p(1)<0.42 → 拒否 |
| uncertain_penalty | **0.5**（維持） | 中間帯(0.42-0.58)は信頼度を50%縮小 |
| high_confidence_failure_threshold | **0.65**（Phase 84） | ml_pred==0 かつ confidence≥0.65 で拒否（旧ハードコード0.55） |

**Phase 84 補足**: confidence は `max(p_0, p_1)`（class 1確率ではない）。ml_pred==0 + confidence=0.808 なら失敗確信80.8%＝正常な拒否動作。

**再学習後モデル性能**（2026/5/11学習、Phase 85）:
- CV F1: LGB 0.602±0.051 / XGB 0.577±0.073 / RF 0.571±0.074（Phase 83A-3とほぼ同等）
- 学習サンプル: 35,036件（365日分、2025-05-11〜2026-05-10）
- 信頼度分布: LGB mean=0.633 / XGB mean=0.740 / RF mean=0.677
- 最適閾値: 0.50 (F1=0.5021)
- SMOTE適用: 29,780 → 41,312サンプル

**Phase 85採算ライン勝率**（レジーム別）:
- tight_range (実RR 0.81:1): 採算 55%、実証67.9%で大幅余裕 ✅
- normal_range (実RR 0.16:1): 採算 86%、実証75%でやや厳しい（薄利OK狙い）

**モデルバックアップ**:
- `models/production/ensemble_{full,basic}.phase82.pkl.bak`: Phase 82モデル
- `models/production/ensemble_{full,basic}.phase83a.pkl.bak`: Phase 83A-3モデル
- `models/production/ensemble_{full,basic}.phase84.pkl.bak`: Phase 84モデル

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
