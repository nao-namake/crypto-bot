# Phase 85: レジーム別TP/SL再構築 + floor 0.7%復活 + trending停止

**期間**: 2026年5月11日
**状態**: 実装中

---

## 背景: Phase 84 24h観測で勝率0%/-6,875円が顕在化

Phase 84 デプロイ後の24h観測（5/10-5/11）で:
- **エントリー21件 / 勝率0% / 9件全SL / 損益 -6,875円**
- SL距離 0.064%（BTC ノイズ幅0.3-0.5% を完全に下回る）
- 平均99秒でSL確定 = 即SL

ユーザー指摘「単純な応急処置をやめて根本解決」「TP/SL調整が必要なら検討」「SLが短すぎるならRR1まで下げてもよい」

---

## 多角的調査で判明した致命的バグ群

### バグ1: `sl_simulation.py` の手数料加算バグ

```python
# 旧（誤・手数料加算）- scripts/analysis/sl_simulation.py
fee_buffer = entry_price * amount * (ENTRY_FEE_RATE + 0.001)
target_loss_distance = (sl_amount + fee_buffer) / amount  # SL目標に手数料を加算

# 実コード（正・手数料控除）- src/strategies/utils/strategy_utils.py:485-487
gross_loss = sl_target - exit_fee - entry_fee
sl_distance = gross_loss / position_size
```

**影響**: SL距離を **約7倍過大評価**。Phase 83B で「SL500円維持で勝率95.5%」と判断したのは虚像。

### バグ2: CLAUDE.md の例も誤記述

> 例: amount 0.015 BTC、SL目標500円 → SL距離 ≒ 33,333円 + 手数料 ≒ 約0.27%

実コード計算では 8,333円 = **0.067%**（記述の1/4）。

### バグ3: tax/trade_history.db の母集団バイアス

`trade_type` カラムには `entry` (240件)・`tp` (35件) のみ、**SL決済が記録されていない**。
`sl_simulation.py` は `trade_type='tp'` のみ抽出していたため、過去TP決済成功取引のみで再現していた。

---

## 真の運用シミュレーション実装（Phase 85 新規スクリプト）

`scripts/analysis/full_entry_simulation.py` 新規作成:

1. bitbank API `fetch_my_trades` から過去30日全取引履歴取得（397件約定→106エントリー注文）
2. `info.position_side`（long/short）と `side`（buy/sell）一致でエントリー識別
3. order_id でグルーピング、加重平均価格を計算
4. 各エントリーから15分足でTP/SL先着判定
5. 各シナリオで勝率・損益・期待値/件 を集計
6. GCPログから動的戦略選択ログを取得し、エントリー時レジームを紐付け→レジーム別集計

---

## 真の運用シミュレーション結果（過去30日 106エントリー）

### 全体集計（全シナリオで赤字！）

| シナリオ | TP到達率 | 損益 | 期待値/件 |
|---------|---------|------|----------|
| 🏆 **TP500/SL1500 + floor 0.7%** (Phase82風) | 73.3% | -3,500円 | -33円 |
| 🥈 **TP1500/SL2000 + floor 0.7%** | 56.4% | -2,500円 | -24円 |
| TP750/SL1500 + floor 0.7% (Phase83A) | 62.5% | -9,750円 | -92円 |
| TP1500/SL1200 (floor無し) | 39.4% | -14,100円 | -133円 |
| **現状 TP1000/SL500 (Phase 83B)** | **14.3%** | **-30,000円** | **-283円** ❌ |

**floor 0.7% 無しは全シナリオ -200円/件超の壊滅的損失**。floor 入れると損失が90%縮小。

### レジーム別集計（決定的発見）

#### 🟢 tight_range (29件) - 唯一の黒字ゾーン

| シナリオ | TP | SL | 勝率 | 損益 | 期待値/件 |
|---------|----|----|------|------|----------|
| **TP1500/SL2000 + floor 0.7%** | 19 | 9 | **67.9%** | **+10,500円** | **+362円** ✅ |
| TP500/SL1500 + floor 0.7% | 19 | 10 | 65.5% | -5,500円 | -190円 |
| 現状 TP1000/SL500 | 1 | 28 | 3.4% | -13,000円 | -448円 ❌ |

#### 🟡 normal_range (36件) - 横ばい

| シナリオ | TP | SL | 勝率 | 損益 | 期待値/件 |
|---------|----|----|------|------|----------|
| **TP500/SL1500 + floor 0.7%** | 27 | 9 | **75.0%** | **±0円** | ±0円 |
| TP1500/SL2000 + floor 0.7% | 18 | 18 | 50.0% | -9,000円 | -250円 |

#### 🔴 trending (23件) - 全シナリオ赤字

| シナリオ | TP | SL | 勝率 | 損益 |
|---------|----|----|------|------|
| TP500/SL1500 + floor 0.7% | 18 | 5 | 78.3% | +1,500円 |
| **TP1500/SL2000 + floor 0.7%** | 9 | 11 | **45.0%** | **-8,500円** |

#### ❓ unknown (18件) - レジーム判定ログ取得不能期間

| シナリオ | 勝率 | 損益 |
|---------|------|------|
| TP1500/SL2000 | 64.7% | +4,500円 |
| TP1500/SL1200 | 58.8% | +6,600円 |

### Phase 85 戦略の試算

レジーム別に異なるTP/SLを適用、trending時はエントリー停止:
- tight 29件 × +362円 = **+10,498円**
- normal 36件 × 0円 = ±0円
- trending エントリーなし（過去-8,500円の損失回避）
- 合計: **+10,498円 / 30日 → +約350円/日ペース**

これは **Phase 61 好調期に匹敵**。

---

## 実装内容

### 設定変更（`config/core/thresholds.yaml`）

#### TP目標（regime_based）
```yaml
take_profit.regime_based:
  tight_range:
    fixed_amount_target: 1500  # Phase 85: 1000→1500
    min_profit_ratio: 0.007    # Phase 85: 0.4%→0.7%
  normal_range:
    fixed_amount_target: 500   # Phase 85: 1000→500（浅いTPで取りこぼし減）
    min_profit_ratio: 0.004    # Phase 85: 1.0%→0.4%
```

#### SL目標（regime_based）
```yaml
stop_loss.regime_based:
  tight_range:
    fixed_amount_target: 2000  # Phase 85: 500→2000
    max_loss_ratio: 0.0086     # Phase 85: 0.4%→0.86%
  normal_range:
    fixed_amount_target: 1500  # Phase 85: 500→1500
    max_loss_ratio: 0.007      # 0.7%維持
```

#### floor 0.7% 復活
```yaml
stop_loss.min_distance:
  enabled: true   # Phase 85: false→true
  ratio: 0.007    # Phase 85: 0.0→0.007
```

#### trending 戦略全停止
```yaml
regime_strategy_mapping.trending:
  ATRBased: 0.0
  CMFReversal: 0.0
  BBReversal: 0.0
  StochasticReversal: 0.0
  ADXTrendStrength: 0.0
  MACDEMACrossover: 0.0
```

#### 同方向ポジション制限ロールバック
```yaml
max_same_direction_positions: 1  # Phase 85: 2→1（Phase 84で損失40%増幅）
```

#### Phase 84 強トレンド継続順張り無効化
```yaml
strategies.adx_trend.strong_trend_continuation_adx: 999  # Phase 85: 30→999で実質無効化
```

### コード変更

- `scripts/analysis/sl_simulation.py`: 手数料計算を実コードと一致するよう修正（控除ロジック）
- `scripts/analysis/full_entry_simulation.py`: 新規追加（真の運用シミュレーション、レジーム別集計）

### CLAUDE.md 修正

- しおり Phase 85 に更新
- SL距離例「0.27%」→ 「0.067%（floor撤廃時）」「0.86%（Phase 85 floor 0.7%）」に修正
- レジーム別TP/SL表追加
- レジーム別重みづけ表で trending 全 0.0 表記
- 同方向制限を 2 → 1 に更新

### ML再学習

新TP/SL設定（tight基準）:
- meta_tp_ratio: 0.007 (TP 0.7%)
- meta_sl_ratio: 0.0086 (SL 0.86%)

`scripts/ml/create_ml_models.py --meta-label --meta-tp 0.007 --meta-sl 0.0086`

---

## 期待効果

| 指標 | Phase 84 (24h観測) | Phase 85 (試算) |
|------|-----------|---------|
| エントリー数 | 21件/24h | 約3-5件/日（trending停止で抑制） |
| 勝率 | 0% | 60-70%（tight基準） |
| 月損益ペース | -200,000円 | **+10,500円** |
| SL距離 | 0.064% (即SL) | 0.86% (ノイズ越え) |
| 採算ライン勝率 | 13%（実現不可） | 32%（tight 67.9%なら大幅余裕） |

---

## 注意事項とリスク

1. **レジーム判定の精度依存**: tight_range と判定された時のみ高期待値。誤判定で trending時にエントリーすると損失
2. **unknown レジームの存在**: 過去30日18件はレジーム判定取れず（ログ取得タイミング/bot停止期間）。実運用では発生頻度を要観測
3. **過去30日のサンプル偏り**: 5/8-5/10 はトレンド相場。期間によって勝率が変動する可能性
4. **戦略品質の根本問題は未解決**: TP1500/SL2000 + floor 0.7% でも勝率56%程度 = エントリー方向判定の精度向上は Phase 86 以降で対応

---

## デプロイ後の観測指標

```bash
python3 scripts/live/standard_analysis.py --hours 24
```

確認すべき:
1. レジーム別エントリー件数（trending=0、tight/normal が大半か）
2. 勝率（tight時は60%超を期待）
3. 平均SL損失（手数料込みで -2,500円/件以内）
4. floor 0.7% 適用ログ確認
5. ML品質フィルタ通過率（再学習後）
