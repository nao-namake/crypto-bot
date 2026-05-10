# Phase 84: エントリー機会拡大（ML閾値yaml化・同方向制限緩和・強トレンド継続順張り）

**期間**: 2026年5月10日
**状態**: 実装完了・コミット済み（f0fece91）・GCPデプロイ完了

---

## 背景: Phase 83C デプロイ後 24時間ゼロエントリー

Phase 83B（TP1000/SL500/floor撤廃）+ Phase 83C（包括バグ修正13件）デプロイ後、24時間（5/9-5/10）の `live/standard_analysis.py` で:

- **エントリー総数: 0件**
- 統合シグナル: 全て hold（信頼度 0.42-0.43 固定）
- ML品質フィルタ拒否: 14件（短い瞬間の弱シグナルのみ）
- レジーム: **24時間100% trending**（ADX 51-67 継続）

ユーザー要件: 「botはレンジ専用設計だが、トレンドでも0にするとまでは思わない。１日数回はエントリーしたい。」

---

## 真因分析（多角調査）

### 結論1: 「ML=0 信頼度=0.808」は **正常動作**

Phase 83C 時に書いた confidence のコメントが誤っていた。

- 誤: `confidence = p(class 1)` → 失敗確信80.8%なのにエントリー誤通過
- 正: `confidence = max(p_0, p_1)` → 失敗確率80.8% → 正しく拒否

ML品質フィルタは健全。ML側は問題ではない。

### 結論2: ML calibration 二次的問題

`ProductionEnsemble` は `CalibratedClassifierCV` 非対応で **uncalibrated**。XGBoost confidence mean=0.731 と高めで信頼度が +0.12 上振れする可能性。ただし判定ロジックは健全。

### 結論3: ゼロエントリーの真因は **3つの隠れた制限**

#### 真因A: ハードコード閾値 0.55 が中庸シグナルを全拒否

`src/core/services/trading_cycle_manager.py:1262`（旧）:
```python
elif (ml_pred == 0 and ml_confidence >= 0.55) or ml_confidence < reject_threshold:
    # → action = "hold"
```

- 失敗確信55-65%（成功確信35-45%）の取引を問答無用で拒否
- RR比2.0:1なら勝率33%が採算ライン → 35-45%なら長期黒字想定
- yaml参照ではなくハードコード値 → ユーザーの過去 accept_threshold 調整では届かない別軸

#### 真因B: 同方向ポジション制限 1個

5/8 16:56 ログ: `同方向ポジション制限(buy: 1個)に達しています`

複数の安全弁（保証金維持率予測80%/レジーム別上限/連敗縮小/日次損失上限）があるため、過剰防衛。

#### 真因C: ADXTrendStrength 強トレンド継続中の hold

`adx_trend.py:_determine_signal` の旧設計:
- 「強トレンド + DIクロスオーバー」必須
- 5/9-5/10 24時間中 ADX 51-67 が継続するも DIクロス未発生 → 全期間 hold

---

## 実装内容（A + E + F）

### 案E: ML品質フィルタ「失敗高確信閾値」yaml化（最重要）

**変更**: `src/core/services/trading_cycle_manager.py:1241-1262`

```python
high_conf_failure = get_threshold(
    "ml.quality_filter.high_confidence_failure_threshold", 0.65
)
# ...
elif (
    ml_pred == 0 and ml_confidence >= high_conf_failure
) or ml_confidence < reject_threshold:
```

**設定**: `config/core/thresholds.yaml`
```yaml
ml:
  quality_filter:
    high_confidence_failure_threshold: 0.65  # 旧ハードコード0.55
```

**効果**:
- 失敗確信55-65%の取引が通過
- 失敗確信65%超は引き続き拒否（過剰防衛は維持）
- yaml経由で運用中に動的調整可能に

### 案F: 同方向ポジション制限 1→2

**設定**: `config/core/thresholds.yaml`
```yaml
position_management:
  max_same_direction_positions: 2  # 旧1
```

**安全担保**:
- 保証金維持率予測80%でエントリー拒否
- レジーム別最大ポジション数（trending=2など）
- 連敗縮小ロジック（5連敗50%、8連敗0%）
- 日次/週次損失上限（1%/4%）

### 案A: ADXTrendStrength 強トレンド継続順張り（DIクロス不要）

**変更**: `src/strategies/implementations/adx_trend.py:289-368`

```python
# __init__ に追加
self.strong_trend_continuation_adx = get_threshold(
    "strategies.adx_trend.strong_trend_continuation_adx", 30
)
self.strong_trend_continuation_di_diff = get_threshold(
    "strategies.adx_trend.strong_trend_continuation_di_diff", 8.0
)
self.strong_trend_continuation_confidence = get_threshold(
    "strategies.adx_trend.strong_trend_continuation_confidence", 0.5
)

# _determine_signal の「1. 強いトレンド + DIクロスオーバー」直後に追加
# 1b. Phase 84: 強トレンド継続中のDI差順張り（DIクロス不要）
if (
    analysis["adx"] >= self.strong_trend_continuation_adx
    and not analysis["bullish_crossover"]
    and not analysis["bearish_crossover"]
):
    if analysis["di_difference"] >= self.strong_trend_continuation_di_diff:
        return self._create_signal(action="buy", ...)
    elif analysis["di_difference"] <= -self.strong_trend_continuation_di_diff:
        return self._create_signal(action="sell", ...)
```

**設定**: `config/core/thresholds.yaml`
```yaml
strategies:
  adx_trend:
    strong_trend_continuation_adx: 30        # ADX≥30 で発火
    strong_trend_continuation_di_diff: 8.0   # |+DI - -DI|≥8
    strong_trend_continuation_confidence: 0.5
```

**効果**: 強トレンド継続中（ADX 30+）でも方向確信時に保守的順張り発火。

---

## テスト追加

### tests/unit/core/test_quality_filter.py（新規・4件）

| テスト | 検証内容 |
|--------|---------|
| `test_default_threshold_is_065` | デフォルト 0.65 で失敗確率 0.60 が通過 |
| `test_high_failure_confidence_still_rejected` | 失敗確率 0.808 は引き続き拒否 |
| `test_yaml_override_threshold` | yaml で 0.50 にすると失敗確率 0.55 で拒否 |
| `test_legacy_055_threshold_passes_058` | 旧0.55で拒否されていた 0.58 が新0.65で通過 |

### tests/unit/strategies/implementations/test_adx_trend.py（追加・4件）

`TestPhase84StrongTrendContinuation` クラス:
- 強トレンド継続 BUY 発火（ADX=35, DI diff=10）
- 強トレンド継続 SELL 発火（ADX=35, DI diff=-10）
- DI差<8 で hold（条件不成立）
- ADX<30 で hold（条件不成立）

---

## 設計思想との整合性

ユーザー設計思想: 「botはレンジ状態だけで稼働、トレンドで火傷しない」

Phase 84 のアプローチ:
- **レンジ専用思想は維持**（純化はしない）
- トレンド時の活動を完全停止せず、ADX>30+DI差大の方向確信時のみ発火（保守的）
- レンジ時のエントリー機会も MLフィルタ緩和で増加

つまり、レンジ中心 + 強確信トレンドのみ補助、というハイブリッドの保守的版。

---

## 期待効果

24時間ゼロエントリー → **1日数件のエントリー復活**を想定。

- ML品質フィルタ過剰防衛 → 適度な防衛（失敗確信65%超のみ拒否）
- 同方向2件まで許容 → 取引機会の取りこぼし減
- ADXTrendStrength 強トレンド時の hold 解消 → trending 時もシグナル発火

多重安全弁（保証金維持率/連敗縮小/損失上限）で守られる前提。

---

## デプロイと品質チェック

### CI/CD結果

- pytest: **2,056件 PASS**
- カバレッジ: **74.12%**
- flake8 / black / isort: PASS
- CI run 25612707452: success
- GCP Cloud Run デプロイ: 完了

### コミット

```
f0fece91 feat: Phase 84 エントリー機会拡大（ML閾値yaml化・同方向制限緩和・強トレンド継続順張り）
```

5 files changed: 289 insertions(+), 11 deletions(-)
- `config/core/thresholds.yaml`: +5パラメータ
- `src/core/services/trading_cycle_manager.py`: ハードコード0.55除去
- `src/strategies/implementations/adx_trend.py`: 強トレンド継続ロジック追加
- `tests/unit/core/test_quality_filter.py`: 新規125行
- `tests/unit/strategies/implementations/test_adx_trend.py`: +79行

---

## 次ステップ（観測タスク）

```bash
python3 scripts/live/standard_analysis.py --hours 24
```

**確認項目**:
- エントリー数（目標: 1日数件）
- レジーム別エントリー比率（trending時もエントリーあるか）
- ML品質フィルタの「失敗確信65%超で拒否」適用件数
- ADXTrendStrength 強トレンド継続条件での発火件数
- SL固定金額500円の実現状況（floor撤廃適用率100%）

24-48時間で初期判定、1週間で累積損益・勝率を評価。

**注意点**:
- ML信頼度上振れ可能性（uncalibrated）あり、accept率が異常に高い場合 accept_threshold を 0.65 に再調整検討
- trending時のエントリー集中で連敗増の可能性 → 連敗縮小ロジックで自動制御

---

## 失敗から学んだこと

### 設計レビューの教訓

- ハードコード閾値（0.55）は yaml化以外見つけにくい。Phase 83C のバグ調査で発見できなかった
- confidence の意味（max vs class 1 prob）はコード読まないと判別不可。コメント整備重要
- 「ML品質フィルタは健全」と判断する前に、フィルタ通過数を24h単位で計測すべき

### 多重安全弁の設計

- 同方向ポジション制限のような「単純カウント上限」は撤廃しても、保証金維持率/レジーム上限/連敗縮小で十分守れる
- 機能追加よりも、既存機能の制限緩和の方がリスクが小さい場合がある
