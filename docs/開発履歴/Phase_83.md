# Phase 83A: CMFバグ修正 + SL距離下限0.7%強制 + ML再学習

**期間**: 2026年4月24日
**状態**: 実装完了・コミット済み・デプロイ待ち

---

## 背景

### Phase 82 完了後の1週間運用（2026/04/16-04/23）

**7日間の取引結果（bitbank API基準）**:
- TP決済: 12件（勝率36.4%）
- SL決済: 21件（SL率63.6%）
- SL合計: -16,900円（平均-994円、目標-800円を194円超過）
- **総損益 (bitbank API): -8,478円**
- 総損益 (GCPログ): -7,900円

### 方向別の偏り

| 方向 | エントリー | SL | SL率 |
|------|-----------|----|------|
| buy | 18件 | 8件 | 44% |
| **sell** | 14件 | 9件 | **64%** ← 顕著に悪い |

### 特定した3つの致命的問題

1. **CMFReversal が ImportError で 1週間0件発火**
   - `cannot import name 'EntryAction' from 'src.strategies.base.strategy_base'`
   - 6戦略中2戦略が完全無効化（MACDEMACrossoverも発火数極少）

2. **固定金額SL(800円)が手数料で圧迫され実効SL幅0.23-0.44%**
   - 0.015BTC @ 12.5M円: 手数料376円(47%) → 実SL幅424円 = 0.23%
   - BTCのノイズ幅(0.3-0.5%)を下回り連続SL発動

3. **ML学習条件と運用条件の乖離**
   - 学習: TP 0.43% / SL 0.37%
   - 運用: TP 0.5% / SL 0.23-0.44%
   - signal_simulation検証でML通過/拒否の勝率差わずか2%（選別能力ほぼなし）

### 反実仮想検証（signal_simulation.py）

| SL幅 | 勝率 | PnL |
|------|------|-----|
| 33,000円 (0.27%) | 52% | +20,000円 |
| 60,000円 (0.50%) | 57% | +26,750円 |
| **90,000円 (0.75%)** | **82%** | **+48,250円** |

SL幅を広げるだけで勝率52→82%に跳ね上がることを実証。

---

## 83A-1: CMFReversal ImportError修正（1行）

### 問題

`src/strategies/implementations/cmf_reversal.py:172` で誤ったパスからimport:

```python
from ..base.strategy_base import EntryAction  # ← 誤
```

`EntryAction` は実際には `src/strategies/utils/strategy_utils.py:31` に定義され、`src/strategies/utils/__init__.py` でexport。他5戦略はすべて `from ..utils import EntryAction` で統一されていたが CMFReversal のみ追従漏れ。

### 修正

```diff
-from ..utils import SignalBuilder, StrategyType
+from ..utils import EntryAction, SignalBuilder, StrategyType

 (Step 5: シグナル生成)
-            from ..base.strategy_base import EntryAction
-
+            # Phase 83A-1: utils 配下の EntryAction を使用（他5戦略と統一）
             action = EntryAction.BUY if direction == "buy" else EntryAction.SELL
```

**期待効果**: CMFReversal 発火復活、6戦略すべて稼働。

---

## 83A-2: SL距離下限0.7%強制 + 目標金額調整

### 問題

`_calculate_fixed_amount_sl_for_position()` で以下の計算:

```
gross_needed = target - exit_fee - entry_fee
sl_offset = gross_needed / amount
```

target=800円、手数料2×188円（0.015BTC @ 12.5M）の場合、gross_needed=424円 → sl_offset=28,267円 → SL距離0.23%。既存の `min_distance.ratio: 0.007`（0.7%）は存在していたが**固定金額SLパスでは適用されていなかった**。

### 修正

**ファイル1**: `src/trading/execution/tp_sl_manager.py:1307-1318`

```python
gross_needed = target - exit_fee - entry_fee
if gross_needed <= 0:
    gross_needed = target
sl_offset = gross_needed / amount

# Phase 83A-2: min_distance floor強制（ノイズ幅以下のSL禁止）
min_ratio = get_threshold("position_management.stop_loss.min_distance.ratio", 0.007)
min_offset = avg_price * min_ratio
if sl_offset < min_offset:
    self.logger.info(
        f"🛡️ Phase 83A-2: SL距離floor適用 - "
        f"{sl_offset:.0f}円({sl_offset / avg_price * 100:.2f}%) → "
        f"{min_offset:.0f}円({min_ratio * 100:.2f}%)"
    )
    sl_offset = min_offset
```

**ファイル2**: `config/core/thresholds.yaml` SL目標金額調整

floor 0.7%と整合するよう SL目標金額を増額（手数料込みで実損失1,000-1,200円想定）:

| 項目 | Phase 82 | Phase 83A-2 |
|------|----------|-------------|
| `target_max_loss` | 800 | **1500** |
| `confidence_based.low` | 600 | **1200** |
| `confidence_based.high` | 800 | **1500** |
| `regime_based.tight_range.fixed_amount_target` | 800 | **1200** |
| `regime_based.normal_range.fixed_amount_target` | 800 | **1500** |
| `regime_based.trending.fixed_amount_target` | 800 | **1800** |
| `regime_based.high_volatility.fixed_amount_target` | 800 | **2000** |

### テスト

既存の Phase 70.2 テスト2件が floor 適用で失敗 → mockに `min_distance.ratio: 0.0` を追加して旧ロジック検証を保持。Phase 83A-2 の floor動作を検証する新規テスト2件追加:

- `test_sl_min_distance_floor_applied`: 素のSL距離0.23%が0.7%にfloor強制されることを検証
- `test_sl_min_distance_floor_not_applied_when_natural_distance_larger`: 素のSL距離>0.7%の場合はfloor非適用を検証

### 期待効果

SL距離0.23-0.44% → 常に≥0.7%。signal_simulation実証の「SL 0.75%時勝率82%」レンジに着地。損失許容は上がるが、SLヒット率が大幅低下しトータルで勝率改善。

---

## 83A-3: MLモデル再学習（--meta-label付き）

### 経緯

初回実行時 `--meta-label` フラグを指定し忘れ、**方向分類(3クラス buy/sell/hold)**のモデルが生成された（CV F1 0.40、Phase 82のメタラベリングと不整合でシステム破壊の危険）。バックアップから復元し、正しく再実行。

### 実行コマンド

```bash
python3 scripts/ml/create_ml_models.py \
  --optimize --n-trials 50 --verbose \
  --meta-label \
  --meta-tp-ratio 0.0065 \
  --meta-sl-ratio 0.007
```

### 学習パラメータ根拠

- `meta-sl-ratio 0.007` → 83A-2で強制したfloor 0.7%と一致
- `meta-tp-ratio 0.0065` → TP/SL比 0.93:1（bitbank手数料後の現実的損益バランス）

### 検証結果（全項目合格）

| 項目 | 値 | Phase 82比 |
|------|-----|-----------|
| n_classes | 2（メタラベリング Go/No-Go） | ✅ 維持 |
| feature_count | 37 | ✅ 維持 |
| training_samples | 34,970（180日） | ✅ 維持 |
| class_distribution | success 33% / failure 67% | Phase 82: 39/61% |
| **CV F1 (LightGBM)** | **0.612** | Phase 82: 0.533 (**+0.08**) |
| Class 1確率 mean | 0.531 | Phase 82: 0.50 |
| Class 1確率 std | 0.067 | Phase 82: 0.10（**安定性向上**） |
| range | [0.305-0.650] | Phase 82: [0.25-0.78] |

### 実データ4,596件検証（直近48日15分足）

- accept (≥0.58): 1,106件 (24.1%)
- middle (0.42-0.58): 3,064件 (66.7%)
- reject (<0.42): 426件 (9.3%)
- 時系列安定性: 隣接足diff mean 0.020（急変なし）
- 極端予測 (>0.75/<0.25): いずれも0件（過学習なし）

### ロールバック用バックアップ

- `models/production/ensemble_full.phase82.pkl.bak`
- `models/production/ensemble_basic.phase82.pkl.bak`
- `models/production/production_model_metadata.phase82.json.bak`

---

## 83A-4: MACDEMACrossover（今フェーズ変更なし）

ログ `シグナル取得成功: hold (0.100)` が定期的に出ており機能自体は生きている。ADX≥15・MACDクロス・EMAトレンド確認の複合条件で待機中。83A-1〜3適用後の1週間再観測で発火数が有意に少なければ別フェーズで ADX閾値調整を検討。

---

## コミット履歴

| ハッシュ | 内容 |
|---------|------|
| 505876ac | fix: Phase 83A-1 CMFReversal ImportError修正（1週間0発火の致命バグ） |
| 12930706 | fix: Phase 83A-2 固定金額SL距離下限0.7%強制 + 目標金額調整 |
| 7558e9b2 | chore: Phase 83A-3 MLモデル再学習（meta_tp=0.65%, meta_sl=0.7%） |

---

## 期待される改善効果

| 指標 | 1週間実績 | 目標 |
|------|----------|------|
| CMFReversal発火 | 0件 | 他戦略並み |
| SL距離 | 0.23-0.44% | ≥0.7% |
| 勝率 | 36.4% | 50%以上 |
| SL率 | 64% | 50%以下 |
| ML CV F1 | 0.533 | **0.612**（+0.08） |
| 累計損益/週 | -8,478円 | プラス圏 |

---

## 検証コマンド

### デプロイ後24時間観測

```bash
python3 scripts/live/standard_analysis.py --hours 24
```

期待値:
- SL率 64% → 50%以下
- CMFReversal発火回数 > 0（1週間0件→稼働）
- sell SL率 64% → buy並の45%前後に収束
- ML「中間帯（uncertain_penalty適用）」件数が通過・拒否と均衡

### 反実仮想シミュレーション

```bash
python3 scripts/analysis/signal_simulation.py --start 2026-04-24 --end 2026-05-01 --tp 90000 --sl 90000 --with-signals
```

新モデルでML通過群勝率が拒否群を5%pt以上上回ることを確認。

---

## 失敗から学んだこと

### ML再学習の教訓（記録しておく価値）

- `scripts/ml/create_ml_models.py` を使う際は必ず `--meta-label` フラグを付ける（付けないと方向分類3クラスモデルが生成され、現行システムと不整合で壊れる）
- 再学習前に `models/production/*.pkl` と `*.json` を `.bak` としてバックアップ必須
- 学習完了後、`n_classes=2` / `class_distribution` が `success/failure` であることをメタデータで確認
- signal_simulationの `--with-signals` モードは**GCPログ記録済みのML値**を使うため、新モデルの性能評価には使えない。実データ検証スクリプトを別途走らせるべき

### 調査の教訓

- GCPログ抽出で `(-?\d+)円` 正規表現を使うと `+750円` を取りこぼすため `([+-]?\d+)` を使う
- 短期間(24-48h)データだけで判断せず、1週間単位で傾向確認（4/16デプロイ直後は勝率67%と好調だったが週後半悪化）
- bitbank APIベースの損益とGCPログベースの損益は微妙に異なる（手数料計算タイミング）。感覚値と両方を照合
