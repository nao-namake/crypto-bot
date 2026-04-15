# Phase 82: ゴーストポジション TP/SL 異常値バグ修正 + SL目標調整 + ML再学習

**期間**: 2026年4月16日
**状態**: 実装完了・デプロイ待ち

---

## 背景

### Phase 81 完了後の1週間運用（2026/04/09-04/16）

**6日間の取引結果（決済済み12件）**:
- 勝率: **50.0%**（6勝6敗）
- 総損益: **-2,555円**（TP +4,596円 / SL -7,151円）
- 平均勝ち: +766円（目標750円にほぼ一致）
- 平均負け: **-1,192円**（目標1,000円に対し +19% 超過）
- 実績RR比: 0.64:1（目標0.75:1）
- 損益分岐勝率: 60.9% vs 実績50.0% → **10.9pt不足**

### 発生した重大バグ

**2026/04/13 22:29** に以下の配置が実行された:
- TP注文: 18,821,161円（エントリー11,321,161円から **+66.3%**、絶対約定不可）
- SL注文: 1,343,803円（エントリーから **-88.1%**、絶対到達不可）

**直接原因**: bitbank API が short TP決済後の残渣 `long 0.0001 BTC @ 11,321,161円` を返し、Phase 65.2「TP/SLカバレッジ不足検出」→「統合TP/SL復旧」フローが発動。固定金額TP/SL計算が分母極小で以下の計算になった:

- TP = 11,321,161 + (750円 / **0.0001**) = 18,821,161円
- SL = 11,321,161 - (1,000円 / **0.0001**) = 1,343,803円

配置時に `⚠️ SL価格が極端に遠い: 88.13% > 2.1%` の警告は出たが、**ログのみで配置を強行**。

**二次被害**: ゴーストポジションにより3日間新規エントリーがブロック。

---

## 82-A: ダスト/微小ポジション検出（CRITICAL）

### (1) `_place_missing_tp_sl()` にダスト検出ガード追加

`src/trading/execution/tp_sl_manager.py:880-906`

amount < `min_valid_position_btc`（デフォルト 0.001 BTC）の場合、TP/SL配置をスキップし `{"action": "dust_cleanup_required"}` を返却。

### (2) `ensure_tp_sl_for_existing_positions()` に自動クリーンアップ追加

`src/trading/execution/tp_sl_manager.py:689-706`

ダスト検出時は `_cleanup_dust_position()` で成行決済を自動発動。手動介入不要に。

### (3) SL極端警告 → 配置中止（TradingError）

`src/trading/execution/tp_sl_manager.py:282-290`

`SL距離 > max_loss_ratio × 3`（2.1%）で `TradingError` 送出し配置を中止。旧: WARNINGログのみで配置継続。

### (4) 固定金額TP/SL計算に amount 下限ガード

`src/trading/execution/tp_sl_manager.py:1204, 1245`

`_calculate_fixed_amount_tp/sl_for_position()` に amount < 0.001 BTC で `ValueError` を送出。防御的二重チェック。

### 設定追加

`config/core/thresholds.yaml`:
```yaml
position_management:
  min_valid_position_btc: 0.001  # Phase 82: ダスト判定下限
```

---

## 82-B: SL目標値 1000→800円（勝率改善）

### 背景

6日間実績の平均負け -1,192円（目標 -1,000円 を +19% 超過）。SLスリッページを考慮し、目標を下げて実績を目標水準に収束させる。

### 変更

`config/core/thresholds.yaml`:
```yaml
stop_loss:
  fixed_amount:
    target_max_loss: 800  # Phase 82: 1000→800
    confidence_based:
      low: 600   # Phase 82: 800→600
      high: 800  # Phase 82: 1000→800
  regime_based:
    tight_range:
      fixed_amount_target: 800  # 全レジーム 1000→800
    normal_range:
      fixed_amount_target: 800
    trending:
      fixed_amount_target: 800
    high_volatility:
      fixed_amount_target: 800
```

### 期待効果

| 項目 | 旧 (SL 1000円) | 新 (SL 800円) |
|------|---------------|---------------|
| SL距離 (0.015 BTC) | 45,067円 (0.42%) | 32,533円 (0.30%) |
| Net RR比 (高信頼度) | 0.75:1 | 0.94:1 |
| BE勝率 | 57.1% | 51.5% |
| 実績勝率50%での期待損益 | -42円/取引 | -25円/取引 |

---

## 82-C: ML再学習（メタラベリング運用整合）

### 背景

旧モデル（Phase 76: threshold=0.003）の学習パラメータと実運用TP/SL距離に乖離:
- 旧学習: TP 0.45% / SL 0.30%
- 旧運用: TP 0.52% / SL 0.42%（Phase 75-B）
- 新運用: TP 0.43% / SL 0.37%（Phase 82 SL変更後）

Phase 82 の SL 目標変更で運用TP/SLは **TP 0.43% / SL 0.37%** になる。この乖離を解消するため再学習。

### `create_ml_models.py` 機能追加

CLI に `--meta-tp-ratio` / `--meta-sl-ratio` を追加し、Triple Barrier の TP/SL バリアを個別指定可能に。

### 再学習実行

```bash
python3 scripts/ml/create_ml_models.py \
  --meta-label \
  --meta-tp-ratio 0.0043 \
  --meta-sl-ratio 0.0037 \
  --threshold 0.003 \
  --days 365
```

### 学習結果

| 指標 | 値 |
|------|-----|
| 学習データ | 34,970サンプル（12ヶ月） |
| 成功クラス分布 | 成功 39.4% / 失敗 60.6% |
| LightGBM Test F1 | 0.558, CV F1: 0.533±0.032 |
| XGBoost Test F1 | 0.533, CV F1: 0.507±0.056 |
| RandomForest Test F1 | 0.514, CV F1: 0.505±0.082 |
| アンサンブル F1 | 0.5337（閾値0.5） |

### 予測性能検証（実データ470サンプル）

**偏りなし・健全**:
- 予測クラス分布: Class 0 **43.4%** / Class 1 **56.6%**
- Class 1 確率分布: mean=0.50, std=0.10, range=[0.25, 0.78]

### ML閾値再調整

**旧（Phase 79）**: モデル平均0.59 → accept 0.65で通過率~30%
**新（Phase 82）**: モデル平均0.50 → accept 0.65だと通過率5.1%（厳しすぎ）

調整:

| 閾値 | 旧 | 新 | 新モデルでの動作 |
|------|-----|-----|------------------|
| accept_threshold | 0.65 | **0.58** | 通過率 21.9% |
| reject_threshold | 0.45 | **0.42** | リジェクト率 21.3% |
| uncertain_penalty | 0.5 | 0.5 | 中間帯 56.8% は50%縮小（維持） |

### 新モデルファイル

- `models/production/ensemble_full.pkl`（Apr 16 06:11 更新）
- `models/production/ensemble_basic.pkl`（full と同一コピー・Phase 77設計準拠）
- `models/production/production_model_metadata.json`

---

## バグ全体像のまとめ

| # | バグ | 対策Phase |
|---|------|----------|
| 1 | TP/SL決済後にダスト(0.0001 BTC)残り | Phase 82-A(1)(2) |
| 2 | ダストにTP/SL配置しようとする | Phase 82-A(1) |
| 3 | SL極端警告が無視される | Phase 82-A(3) |
| 4 | 固定金額計算の分母ガード不足 | Phase 82-A(4) |
| 5 | ゴーストポジションで新規エントリーブロック | Phase 82-A(2)自動クリーンアップ |

---

## テスト

### 追加テスト（`tests/unit/trading/execution/test_tp_sl_manager.py`）

- `TestPhase82DustDetection::test_place_missing_tp_sl_skips_dust`: ダスト検出でスキップ
- `TestPhase82DustDetection::test_fixed_amount_tp_raises_on_dust`: TP計算で ValueError
- `TestPhase82DustDetection::test_fixed_amount_sl_raises_on_dust`: SL計算で ValueError

### 既存テスト更新

- `test_sl_distance_too_far_warning` → `test_sl_distance_too_far_raises`（TradingError を期待）
- `test_ensure_tp_sl_places_missing_orders` / `test_ensure_tp_sl_short_position`: amount 0.0001 → 0.01（ダスト判定対象外）

### 副次的修正

- `scripts/testing/checks.sh` [4]戦略整合性: Phase 77の strategy_signals 削除に対応
- `src/trading/execution/tp_sl_manager.py:1303` 未使用変数 `target_sl_side` 削除

---

## 期待効果

| 項目 | 改善内容 |
|------|---------|
| ダスト事故 | 完全防止（検出 + 自動クリーンアップ） |
| SL実損超過 | +19%超過 → 目標水準に収束 |
| MLフィルタ通過率 | 5.1% → 21.9%（適切な通過率） |
| モデル偏り | 予測クラス 43%:57% で健全 |
| 学習/運用乖離 | TP/SL共に誤差±0.02pt以内に縮小 |

---

## 次Phase候補（継続検討）

1. Phase 65.2 復旧フローの設計見直し（TP約定後のダスト残りを新規扱いしない）
2. SL 800円での実績検証（1週間運用後、必要に応じ再調整）
3. ML閾値の実績ベース再調整（1週間分の通過率とPnLを見て微調整）
