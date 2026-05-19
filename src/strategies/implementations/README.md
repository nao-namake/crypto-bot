# src/strategies/implementations/ - 取引戦略実装群

**Phase 90α**: 6 戦略（レンジ型 4 + トレンド型 2）によるレジーム別動的戦略選択システム。DonchianChannel は Phase 74 で CMFReversal に置換済（実体削除済）。

## ファイル構成

```
src/strategies/implementations/
├── __init__.py               # 6 戦略エクスポート
├── atr_based.py              # ATRBased 戦略（レンジ型・主力・707 行）
├── bb_reversal.py            # BBReversal 戦略（レンジ型・409 行）
├── stochastic_reversal.py    # StochasticReversal 戦略（レンジ型・589 行）
├── cmf_reversal.py           # CMFReversal 戦略（レンジ型・237 行・Phase 74 で DonchianChannel 置換）
├── macd_ema_crossover.py     # MACDEMACrossover 戦略（トレンド型・350 行）
└── adx_trend.py              # ADXTrendStrength 戦略（トレンド型・961 行）
```

## 6 戦略一覧

### レンジ型（4 戦略）

| 戦略 | 核心ロジック | 備考 |
|------|-------------|------|
| **ATRBased** | ATR 消尽率 70% 以上 → 反転期待 | 主力戦略 |
| **BBReversal** | BB 位置主導 + RSI ボーナス → 平均回帰 | Phase 62.2: AND→BB 主導 |
| **StochasticReversal** | 価格と Stochastic の乖離検出 → 反転 | Phase 62.2: 価格変化フィルタ追加 |
| **CMFReversal** | CMF 売り圧力減少→BUY / 買い圧力減少→SELL | Phase 74: DonchianChannel 置換 |

### トレンド型（2 戦略）

| 戦略 | 核心ロジック |
|------|-------------|
| **MACDEMACrossover** | MACD クロス + EMA トレンド確認 |
| **ADXTrendStrength** | ADX≥22 + DI クロス → トレンドフォロー（Phase 74 で閾値緩和）|

## レジーム別重みづけ（Phase 85: trending 全停止）

設定: `config/core/thresholds.yaml` の `dynamic_strategy_selection.regime_strategy_mapping`

| 戦略 | tight_range | normal_range | trending |
|------|------------|-------------|---------|
| ATRBased | 0.35 | 0.25 | **0.0** |
| CMFReversal | 0.20 | 0.15 | **0.0** |
| BBReversal | 0.20 | 0.15 | **0.0** |
| StochasticReversal | 0.10 | 0.15 | **0.0** |
| ADXTrendStrength | 0.10 | 0.15 | **0.0** |
| MACDEMACrossover | 0.05 | 0.15 | **0.0** |

**Phase 85 trending 全停止根拠**: 過去 30 日 trending 23 件で全シナリオ赤字（TP1500/SL2000 floor 0.7% でも勝率 45%・-8,500 円）。「レンジ専用 bot」設計と完全合致。

## 共通アーキテクチャ

- 全戦略が `StrategyBase` を継承し `StrategySignal` を返却
- `StrategyManager` が統合判定（重み付け平均方式・Phase 59.4 で 2 票ルール廃止）
- 設定は `config/core/thresholds.yaml` で一元管理（`get_threshold()` パターン）
- 動的信頼度計算（市場不確実性を反映、0.2-0.8 範囲）

## テスト

```bash
# 全戦略テスト
python -m pytest tests/unit/strategies/implementations/ -v

# 個別戦略テスト
python -m pytest tests/unit/strategies/implementations/test_atr_based.py -v
python -m pytest tests/unit/strategies/implementations/test_adx_trend.py -v
```

## 関連リンク

- 親 README: [../README.md](../README.md)
- 戦略基盤: [../base/README.md](../base/README.md)
- 共通処理: [../utils/README.md](../utils/README.md)

---

**最終更新**: 2026年5月19日（Phase 90α: DonchianChannel 実体削除・CMFReversal 反映・trending 全停止反映）
