# CLAUDE.md

## しおり（現在地）

| 項目 | 値 |
|------|-----|
| **現在Phase** | **Phase 90γ-⑥ ローカル実装完了（2026-05-28）・本番デプロイ待ち**（Phase 90γ-③.5 + γ-⑤ + 分析スクリプト修正 は未デプロイのまま統合）|
| **直前の作業** | 5/28 ライブ分析 + bitbank API 実取引履歴 168h 分析で **TP/SL confidence 属性名バグ** が発覚。`tp_sl_manager.py:2221` の `getattr(evaluation, "confidence", None)` が `TradeEvaluation` の実在フィールド名（`confidence_level` / `adjusted_confidence`）と不一致のため、**Phase 68.8（2026-03-13）以降 約 2.5 ヶ月間 confidence_based 上書きが全エントリーでスキップ**されていた。結果 normal_range で TP=500 円・tight_range で TP=1500 円が混在。修正により全レジームで信頼度ベース TP=1500/SL=2000 に統一 |
| **次の予定** | Phase 90γ-③.5 + γ-⑤ + 分析スクリプト修正 + **γ-⑥** の 4 修正をまとめて 1 PR デプロイ → 24h ライブ分析で TP 距離 0.3% → 0.7-0.9% / 実 NET +500 円 → +1,200 円以上 / RR 0.25:1 → 0.6:1 を確認 |
| **🎯 Phase 90γ-⑥ 最重要発見** | bitbank API 実取引 168h で **TP 距離が 0.3% (NET +500) と 0.9% (NET +1500) で混在** とユーザー観察。原因は `TradeEvaluation` に `confidence` フィールドが存在しないのに `getattr(evaluation, "confidence", None)` で取得していた致命バグ。tight_range では regime_based 1500 が偶然正しく動作、normal_range では regime_based 500 が誤って採用されていた。Phase 90γ-⑥ で `evaluation.adjusted_confidence or evaluation.confidence_level` の fallback chain に修正 + TP 配置ログ 4 箇所 INFO→WARNING 格上げ + Maker disable_reason WARNING 化 |
| **特徴量数** | 37 → **55**（Phase 89-β/γ/δ で 6 カテゴリ追加）|
| **ML モデル** | 3 → **4**（N-BEATS 追加・LGB 34%/XGB 34%/RF 17%/N-BEATS 15%） |
| **🎉 v8e (2 クラスメタラベリング) macro F1** | LGB CV 0.546 / Test 0.486・XGB CV 0.459・RF CV 0.530・N-BEATS CV 0.514 Test 0.524（naive 0.41 比 **+0.10〜+0.14 で真の予測力獲得**）|
| **本番効果（5/27 05:44 ライブ分析 24h 時点）** | エントリー **5 件・勝率 80% / +¥701** / Maker 約定 **1 件**（spread<2 円で 4 件 Taker fallback）/ Drift 検出 3 件（許容範囲）/ **50062 エラー 5 件発生**（Phase 90γ-⑤ で対処）/ Phase 90γ-③.4 ログ格上げで Maker 経路完全観察可能化 → 真因解明 |
| **追加課金** | **ゼロ**（GPU 不採用 / LLM 不採用 / 全て無料 API） |
| **GCP 月額** | 現状 ¥3,000 → Stage 1+3 後 **¥1,400-1,700 見込み**（実測待ち） |
| **最終更新** | 2026年5月28日 - Phase 90γ-⑥ TP/SL confidence 属性名バグ修正 + 観察可能化 3 件 ローカル実装完了・デプロイ待ち |

> **🚀 セッション再開時は `docs/開発計画/ToDo.md` の「セッション再開時の手順」セクションを最優先で確認**
>
> 詳細計画: `docs/開発計画/ToDo.md` / `~/.claude/plans/tp-gcp-jazzy-harbor.md`（Phase 90γ-③.5 + γ-⑤ + 分析スクリプト修正の統合プラン）
> 開発履歴: `docs/開発履歴/SUMMARY.md`（Phase 1-90γ-③.5）、`docs/開発履歴/Phase_71-81.md`、`Phase_82.md`〜`Phase_90.md`

---

## 🚀 セッション再開時の最優先タスク（2026-05-27 時点・Phase 90γ-③.5 + γ-⑤ + 分析スクリプト修正 ローカル実装完了 → 3 PR 独立デプロイ段階）

**ローカル品質チェック PASS**（全テスト・カバレッジ 72%+・flake8/black/isort）。**未コミット状態**で 3 修正が共存（feature flag で段階解放可能）。次セッションは PR 分割コミット → デプロイ → 24h KPI 確認。

統合プラン書: [`~/.claude/plans/tp-gcp-jazzy-harbor.md`](~/.claude/plans/tp-gcp-jazzy-harbor.md)

### Step 1: PR 分割コミット（推奨 A→C→B 独立 3 PR）

```bash
# PR A: 分析スクリプト統一（最小リスク・即恩恵）
git add scripts/live/standard_analysis.py tests/unit/scripts/test_standard_analysis_tp_sl_count.py
git commit -m "fix: Phase 90γ-③.5 分析スクリプト TP/SL 集計を bitbank API ベースに統一"

# PR C: TP/SL 配置前ポジ確認（50062 連発対策）
git add src/trading/execution/tp_sl_manager.py tests/unit/trading/execution/test_tp_sl_manager.py
git add config/core/thresholds.yaml  # 注: PR B でも修正するので分割するなら git add -p 推奨
git commit -m "fix: Phase 90γ-⑤ TP/SL 配置前ポジション存在確認で 50062 連発対策"

# PR B: 狭 spread best_bid 配置 + 仕様誤読コメント訂正
git add src/trading/execution/order_strategy.py tests/unit/trading/execution/test_order_strategy.py
git commit -m "fix: Phase 90γ-③.5 狭 spread での best_bid 直接配置 + Phase 68/79 仕様誤読訂正"

# ドキュメント更新（4 ファイル）は最後に統合 or PR ごとに分配
git add CLAUDE.md README.md docs/開発履歴/Phase_90.md docs/開発計画/ToDo.md
git commit -m "docs: Phase 90γ-③.5 + γ-⑤ + 分析スクリプト修正完了に伴うドキュメント更新"
```

または統合 1 コミット（全 feature flag 有効化済・段階解放は config 切替で対応）も可能。

### Step 2: 各 PR デプロイ後の 24h KPI 確認

**Day 1（A デプロイ後）**: 分析スクリプトの集計正確化を確認
```bash
venv/bin/python3 scripts/live/standard_analysis.py --hours 24
# 期待: 「取引数: エントリーN件 / 決済M件 (TP:x SL:y)」が bitbank API の win_count/loss_count と一致
# 期待: Phase 90γ-③.5 乖離検出 WARNING ログが 0 件 or 微小（API 値が正・GCP ログは不完全）
```

**Day 2-3（C デプロイ後）**: 50062 エラー解消を確認
```bash
gcloud logging read 'textPayload=~"50062"' --freshness=24h | wc -l  # 期待: 0
gcloud logging read 'textPayload=~"Phase 90γ-⑤.*配置スキップ"' --freshness=24h | wc -l  # 期待: SL 成行決済時に該当
```

**Day 4-7（B デプロイ後）**: Maker 化率向上を確認
```bash
echo -n "狭spread Maker: " && gcloud logging read 'textPayload=~"Phase 90γ-③.5: 狭spread Maker"' --freshness=24h --format='value(timestamp)' | wc -l
echo -n "Maker 約定成功: " && gcloud logging read 'textPayload=~"Maker約定成功"' --freshness=24h --format='value(timestamp)' | wc -l
# 期待: Phase 86 Taker 率 83.3% → ≤30% / Maker 約定数 1→5+/日 / エントリー件数維持
```

### Step 3: 各修正の KPI 達成判定

| 指標 | 現状 (5/27) | 目標 (Day 7) | ロールバック判断 |
|---|---|---|---|
| 表示 TP 件数 vs API TP 件数 | 不一致 (0 vs 4) | 一致 (4 vs 4) | A: GCP 乖離 WARNING 多発で `count_logs` 取得そのものを停止検討 |
| Phase 86 Taker 率 | 83.3% | ≤ 30% | B: 改善ゼロ or 約定 0 件多発 → narrow_spread_strategy.enabled=false |
| 50062 エラー /24h | 5 件 | 0 件 | C: 正常 TP 配置がスキップされて TP 未設置事故 → tp_sl_placement_guard.enabled=false |
| Maker 約定数 /24h | 1 件 | 5+ 件 | （B と連動）|
| エントリー件数 /24h | 5-10 件 | 維持 | （B で エントリー減検出時 ロールバック）|

### Step 4: ロールバック手順（緊急時・5 分以内）

```bash
# 修正 B 無効化（最もリスク高）
yq -i '.order_execution.maker_strategy.narrow_spread_strategy.enabled = false' config/core/thresholds.yaml
git add config/core/thresholds.yaml && git commit -m "rollback: Phase 90γ-③.5 狭 spread 配置無効化" && git push origin main

# 修正 C 無効化
yq -i '.position_management.tp_sl_placement_guard.enabled = false' config/core/thresholds.yaml
git add config/core/thresholds.yaml && git commit -m "rollback: Phase 90γ-⑤ TP/SL 配置前ガード無効化" && git push origin main

# コード revert（必要時のみ）
git revert <コミットハッシュ>
git push origin main
```

修正 A は観測系のため revert 不要（取引ロジック無影響）。

### 24h 観察結果による次フェーズ着手判断

| Day 7 結果 | 次フェーズ |
|---|---|
| 3 修正すべて KPI 達成 | ✅ **Phase 90γ-④ (ML 改善) 着手**（Optuna 50→100 + Focal Loss + Calibration）|
| B で Maker 化率改善せず queue 末尾で約定遅延 | Phase 90γ-③.6: queue position 推定 + 価格再評価ロジック追加検討 |
| C で誤検知による TP 未設置事故 | position_exists_threshold_ratio 0.5 → 0.2 緩和、または `_wait_position_reflected` の戻り値併用 |
| 50062 が別経路で再発 | Phase 64.12 SL 成行決済時に明示的に TP キャンセル追加（副案検討）|


### セッション再開時 Step 2: SLMonitor DRY_RUN→false 切替判定（7 日後・既存）

```bash
# 誤発火率算出
venv/bin/python3 scripts/analysis/sl_monitor_validator.py --days 7

# 終了コード 0 (SAFE) なら config/core/thresholds.yaml:806 で dry_run: false に切替
```

### セッション再開時 Step 3: Phase 90γ-④ 着手判断

7 日観察結果に基づき以下を判定:
- Maker 約定数 増 / Taker 許可数 ≧ スキップ数 → Phase 90γ-③.2/③.3 完全成功 → Phase 90γ-④ (ML 改善) 着手
- スキップが過剰（取引機会喪失大）→ taker_fallback_confidence_threshold を 0.65 → 0.60 に緩和検討

Phase 90γ-④ 候補（Phase 90α からの継続課題・推奨「案 1: 短期 ROI 最大化」）:
1. **Optuna 試行数増** (50→100) [最優先・容易・1 行変更で XGB 過学習対策・期待 +0.02-0.05]
2. **Focal Loss** (LGB/XGB) [容易・SMOTE と相補・期待 +0.01-0.03]
3. **Isotonic Calibration 修正**（v8e で失敗・`ProductionEnsemble` に `fit` メソッド不足）[容易・品質フィルタ精度向上]
4. **CatBoost 追加** or RF 置換: ensemble 多様性向上 [中・コンテナ肥大化 30-40%]
5. **Multi-Level VPIN + OFI 拡張**: マイクロ構造特徴強化 [困難・WebSocket 統合必要]
6. **ADX 遅行性対策（要慎重検証）**: 価格は収束していても ADX が高止まりして trending 継続判定する問題。Phase 85 全停止根拠（過去 30 日 trending 23 件全シナリオ赤字）との両立検証が必須。

### Phase 90γ 異常時のロールバック

```bash
# 個別コミット revert
git revert 1dbaf0ec  # γ-③.4 取消（Maker 観察可能化 + timeout 拡張）
git revert a6b5fe1e  # γ-③.3 取消（ML 信頼度ベース動的 fallback）
git revert 6996737a  # γ-③.2 取消（Maker タイムアウト対策）
git revert 0c40575b  # γ-③.1 取消（exclude_features 拡張 + min_instances 整合）
git revert e529909e  # γ-③ 取消
git revert 488c820f  # γ-② 取消
git revert 8c55dc71  # γ-① レビュー修正取消
git revert 6aa26ea9  # γ-① 取消
git push origin main

# Phase 90γ-③.3 の閾値だけ無効化（コード変更は残す・旧挙動と同等）
yq -i '.order_execution.maker_strategy.taker_fallback_confidence_threshold = 0.0' config/core/thresholds.yaml
git add config/core/thresholds.yaml && git commit -m "rollback: Phase 90γ-③.3 動的判定無効化" && git push origin main

# Drift 検出設定だけ旧に戻す（exclude_features 無効化）
yq -i '.ml.drift.exclude_features = []' config/core/thresholds.yaml
yq -i '.ml.drift.significant_feature_min = 3' config/core/thresholds.yaml
git add config/core/thresholds.yaml && git commit -m "rollback: Phase 90γ-① 設定無効化" && git push origin main
```

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
| **特徴量数** | **55 特徴量**（Phase 89-β/γ/δ で 37→55 拡張・Phase 92 で更なる拡張余地）|
| **MLモデル** | **ProductionEnsemble 4 モデル**（LGB 34%/XGB 34%/RF 17%/N-BEATS 15%・Phase 89-γ で N-BEATS 追加）|
| **ML方式** | **メタラベリング 2 クラス**（success/failure・Phase 90α）+ HMM レジーム検出（Phase 89-γ）+ Fear & Greed センチメント（LLM 不採用・Phase 89-β で確定）|

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

# 戦略個別パフォーマンス分析（旧 strategy_performance_analysis.py の後継・Phase 61 統合）
python3 scripts/analysis/unified_strategy_analyzer.py --mode theoretical  # 理論分析（数秒）
python3 scripts/analysis/unified_strategy_analyzer.py --mode full         # 完全実証（3分）

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
特徴量生成（55 特徴量・Phase 89-β/γ/δ 拡張）
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

### Maker戦略（Phase 90γ-③.5 仕様訂正）

| 設定 | 値 |
|------|-----|
| 価格配置 (spread≥2円) | best_bid + improvement / best_ask - improvement（queue 先頭側に並ぶ既存戦略）|
| 価格配置 (spread<2円) | **Phase 90γ-③.5**: best_bid / best_ask 直接配置（queue 末尾待機戦略・bitbank post_only は反対側板マッチ時のみ cancel という公式仕様に基づく） |
| improvement | max(1, min(int(spread×0.3), spread-1))（Phase 90γ-③.2 で ×0.1→×0.3）|
| spread<=0円（クロス板） | 配置中止（異常検出） |
| timeout | 120秒（Phase 90γ-③.4: 60→120）、リトライ 5 回（Phase 90γ-③.4: 3→5）|
| retry_interval_ms | 1500（Phase 90γ-③.4: 2000→1500）|
| Maker 失敗時 fallback | Phase 90γ-③.3 ML信頼度動的判定：confidence≥0.65 で Taker 進行、<0.65 でスキップ |
| 注: Phase 79 コメント | 「best_bid 直接配置で必ず reject」は仕様誤読・Phase 90γ-③.5 で訂正 |

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

# 設定整合性確認（checks.sh [5/12] で実施・dev_check.py は Phase 40.6 で統合廃止）
bash scripts/testing/checks.sh

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
