# Phase 71-74: 構造的改善（緊急止血・戦略品質・ML刷新・戦略見直し）

**期間**: 2026年3月26日-30日
**状態**: ✅ 完了

---

## 背景

Phase 70ライブ検証（3/22-3/26）で10取引中8敗（勝率20%、PnL -4,117円）。
根本原因3つ: (1)レジーム誤分類 (2)逆張りsell連発 (3)ML精度不足（方向予測の限界）。

---

## Phase 71: 緊急止血（2026年3月26日）

### 71-A: DonchianChannel無効化
- 勝率14%（7戦中1勝）で最大損失源
- `feature_flags.strategies.individual.DonchianChannel.enabled: false`
- 重み再配分: tight_range ATRBased 0.45→0.75

### 71-B: レジーム分類の優先順位修正
- 判定順を `trending → tight_range` に変更（旧: tight_range優先）
- tight_rangeにEMA傾き拒否条件追加（max_ema_slope: 0.0008）
- trending閾値緩和（ADX 22→20, EMA slope 0.001→0.0007）
- 結果: trending検出率35%→68%

### 71-C: トレンドフィルタ強化
- 強トレンド時: 逆方向をholdに完全変換（旧: 50%ペナルティのみ）
- DI spread確認（|plus_di - minus_di| > 5）
- EMA lookback 2期間→5期間に延長
- 結果: 強トレンドブロック20回発動

---

## Phase 72: 戦略品質改善（2026年3月27日）

### 72-A: CMF特徴量追加
- donchian_high_20 → cmf_20（Chaikin Money Flow 20期間）

### 72-B: CCI・Williams %R追加
- donchian_low_20 → cci_20（Commodity Channel Index 20期間）
- is_market_open_hour → williams_r_14（Williams %R 14期間）
- 55特徴量を維持（低重要度3特徴量と入替）

### 72-C: ATRBased出来高確認
- CMF方向確認: buy時cmf>-0.1, sell時cmf<0.1（不一致で-0.15ペナルティ）
- 低出来高フィルタ: volume_ratio<0.5で-0.10ペナルティ

---

## Phase 73: ML刷新（2026年3月27日-29日）

### 73-A: 学習データ拡張
- 17,628サンプル（6ヶ月）→ 34,970サンプル（12ヶ月: 2025/1-12月）
- bitbank APIから2025/1-6月分を追加取得してマージ

### 73-B: バイナリ分類導入
- 3クラス(BUY/HOLD/SELL, F1=0.45) → 2クラス(DOWN/UP, F1=0.60)
- 推論側のクラスマッピングを動的化（2/3クラス自動判定）
- **致命的な偏り判明**: 高信頼度0.65+でDOWN予測99.2%

### 73-C: 多角検証・実験
- 8パターン正則化実験: 全パターンでベースライン以下
- 5パターン閾値実験: 均衡にすると精度50%（コイントス）
- **結論: 15分足方向予測の実力は51%。テクニカル指標ベースの短期価格予測の限界。**

### 73-D: メタラベリング導入（最終解）

**MLの役割を根本的に変更:**
- 旧: 「次は上がる/下がる」→ 方向予測（実力51%）
- 新: 「この取引は成功する/しない」→ 品質判定（Go/No-Go）

**Triple Barrier Method:**
- 上方バリア: +0.075%到達 → 成功(1)
- 下方バリア: -0.050%到達 → 失敗(0)
- 時間バリア: 20本（5時間）以内 → 失敗(0)

**推論側:**
- 戦略が方向を100%決定（MLは方向に不介入）
- ML予測=1（高品質）+ 信頼度≥0.60 → 取引許可
- ML予測=0（低品質）または信頼度<0.40 → 取引拒否

**検証結果:**

| 指標 | 旧（方向予測） | 新（メタラベリング） |
|------|--------------|-------------------|
| クラス分布 | DOWN 66% / UP 34% | 成功55% / 失敗45% |
| 予測偏り | DOWN 76%偏重 | 成功56% / 失敗44% |
| ベースライン比 | -1.7pt | **+1.8pt** |
| 過学習Gap | 7.2% | **4.5%** |
| CV全Fold BL超え | Fold5で-3pt | **全5Fold超え** |
| 0.60+精度 | 73.5%（DOWN偏重） | **72.7%（均衡）** |
| 0.60+期待値 | 見かけのみ | **+456円/取引** |

---

## ML実験ログ

| 日付 | 実験 | 結果 |
|------|------|------|
| 3/27 | 3クラス→バイナリ切替 | F1: 0.45→0.60（DOWN偏重が原因） |
| 3/28 | 8パターン正則化比較 | 全パターンBL以下 |
| 3/28 | 5パターン閾値比較 | 均衡時51%精度（方向予測の限界） |
| 3/28 | 12ヶ月データ+強正則化 | Gap 7.2%→4.5%改善、BL比-1.7pt |
| 3/29 | DOWN偏重詳細分析 | 0.65+で99.2%がDOWN予測（致命的） |
| 3/29 | **メタラベリング(Triple Barrier)** | **BL比+1.8pt・偏り解消・0.60+精度72.7%** |

---

## Phase 74: 戦略見直し（2026年3月30日）

### 背景

ライブ全期間（3/21-3/29）の19エントリー中、ATRBasedが8件、DonchianChannelが9件（無効化済み）。残り4戦略（ADXTrendStrength, MACDEMACrossover, BBReversal, StochasticReversal）はエントリー0件。

原因:
1. レジーム重み0.0: tight_rangeでADXTrend/MACDEMAが重み0.0
2. 戦略の内部条件が厳しすぎ: 15分足BTC/JPYの実態に合わない閾値
3. DonchianChannelは特徴量削除（Phase 72）で物理的に動作不能

### DonchianChannel → CMFReversal 入替

**理由**: DonchianChannelはdonchian_high_20/low_20特徴量がPhase 72で削除済みのため動作不能。バックテストではPF1.14だったが、ライブでは勝率14%。

**CMFReversal**:
- CMF < -0.10（売り圧力減少）→ BUY
- CMF > +0.10（買い圧力減少）→ SELL
- ADX > 28 → HOLD（トレンド除外）
- CMF特徴量は既に計算済み（Phase 72）

### レジーム重み再配分

全6戦略が全レジームで最低0.05-0.10重みを持つよう再配分:

| 戦略 | tight_range | normal_range | trending |
|------|------------|-------------|---------|
| ATRBased | 0.35 | 0.25 | 0.15 |
| CMFReversal | 0.20 | 0.15 | 0.10 |
| BBReversal | 0.20 | 0.15 | 0.10 |
| StochasticReversal | 0.10 | 0.15 | 0.10 |
| ADXTrendStrength | 0.10 | 0.15 | 0.30 |
| MACDEMACrossover | 0.05 | 0.15 | 0.25 |

### 4戦略の閾値緩和

| 戦略 | 変更 |
|------|------|
| ADXTrendStrength | RSI駆動モード有効化、強トレンド閾値25→22、DI閾値緩和 |
| MACDEMACrossover | ADX閾値18→15、出来高フィルタ1.0→0.8 |
| BBReversal | BB幅3.5%→6%、BB位置0.3/0.7→0.25/0.75 |
| StochasticReversal | ルックバック5→8、価格変動0.5%→0.3% |

### 設計思想

メタラベリング（Phase 73-D）が品質フィルタとして機能するため、戦略は広くシグナルを生成し、MLが低品質を除外する「漏斗型」設計:

```
6戦略 → 広いシグナル生成
  ↓ トレンドフィルタ → 逆トレンド除外
  ↓ ML品質フィルタ → 低品質除外（Go/No-Go）
  ↓ シグナル一貫性 → ノイズ除外
  ↓ リスク管理
  ↓ エントリー実行
```

---

## バグ修正（2026年3月30日）

### BUG 1: MLモデルがダミーモデルにフォールバック（CRITICAL）

**症状**: 3/28以降エントリーがゼロ。GCPログに「想定外の特徴量数: 99」「ダミーモデル使用」。

**原因**: `trading_cycle_manager.py`の`ensure_correct_model()`に`main_features`の全カラム数（open/high/low含む99列）が渡されていた。MLモデルは55特徴量なので不一致判定→ダミーモデル（全hold）にフォールバック→品質フィルタにシグナルが来ない→エントリーゼロ。

**修正**: `main_features_for_ml.columns`（ML用に選択済みの55特徴量）を使用。

### BUG 2: DonchianChannelがRegistryに残留してエラー

**症状**: 毎サイクル「DonchianChannel シグナル生成エラー: 必要特徴量が不足」。

**原因**: `__init__.py`のimportでDonchianChannelStrategyが自動的にStrategyRegistryに登録。thresholds.yamlに定義がなくてもimportチェーンで登録される。Phase 72でdonchian_high_20/low_20特徴量を削除済みのためエラー。

**修正**: `__init__.py`からDonchianChannelのimportを除去。ファイル自体は過去参照用に残す。
