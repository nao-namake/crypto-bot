# src/strategies/implementations/ - 取引戦略実装群

**Phase 64.5**: 6戦略（レンジ型4 + トレンド型2）によるレジーム別動的戦略選択システム。

## ファイル構成

```
src/strategies/implementations/
├── __init__.py               # 6戦略エクスポート
├── atr_based.py              # ATRBased戦略（レンジ型・主力）
├── bb_reversal.py            # BBReversal戦略（レンジ型）
├── stochastic_reversal.py    # StochasticReversal戦略（レンジ型）
├── donchian_channel.py       # DonchianChannel戦略（レンジ型）
├── macd_ema_crossover.py     # MACDEMACrossover戦略（トレンド型）
└── adx_trend.py              # ADXTrendStrength戦略（トレンド型）
```

## 6戦略一覧

### レンジ型（4戦略）

| 戦略 | 核心ロジック | 備考 |
|------|-------------|------|
| **ATRBased** | ATR消尽率70%以上 → 反転期待 | 主力戦略 |
| **BBReversal** | BB位置主導 + RSIボーナス → 平均回帰 | Phase 62.2: AND→BB主導 |
| **StochasticReversal** | 価格とStochasticの乖離検出 → 反転 | Phase 62.2: 価格変化フィルタ追加 |
| **DonchianChannel** | チャネル端部反転 + RSIボーナス | Phase 62.2: RSIボーナス制度 |

### トレンド型（2戦略）

| 戦略 | 核心ロジック |
|------|-------------|
| **MACDEMACrossover** | MACDクロス + EMAトレンド確認 |
| **ADXTrendStrength** | ADX≥25 + DIクロス → トレンドフォロー |

## レジーム別重みづけ

戦略選択はレジーム（tight_range / normal_range / trending）に応じて動的に重みづけされる。
設定は `config/core/thresholds.yaml` の `dynamic_strategy_selection.regime_strategy_mapping` で管理。

```yaml
# tight_range例
tight_range:
  BBReversal: 0.35
  StochasticReversal: 0.35
  ATRBased: 0.20
  DonchianChannel: 0.10
  ADXTrendStrength: 0.0
  MACDEMACrossover: 0.0
```

## 共通アーキテクチャ

- 全戦略が `StrategyBase` を継承し `StrategySignal` を返却
- `StrategyManager` が統合判定（重み付け投票）
- 設定は `config/core/thresholds.yaml` で一元管理（`get_threshold()` パターン）
- 動的信頼度計算（市場不確実性を反映、0.2-0.8範囲）

## テスト

```bash
# 全戦略テスト
python -m pytest tests/unit/strategies/implementations/ -v

# 個別戦略テスト
python -m pytest tests/unit/strategies/implementations/test_atr_based.py -v
python -m pytest tests/unit/strategies/implementations/test_adx_trend.py -v
```

---

**Phase 64.5更新**: デッドコード削除（Phase 55.3/55.6実験的機能）・6戦略構成に合わせたドキュメント刷新。
