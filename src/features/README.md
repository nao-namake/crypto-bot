# src/features/ - 特徴量生成システム

55特徴量固定システム（49基本 + 6戦略シグナル）。feature_order.json単一真実源連携。

## ファイル構成

```
src/features/
├── __init__.py            # 遅延インポート（循環インポート回避）
└── feature_generator.py   # 統合特徴量生成（FeatureGeneratorクラス）
```

## FeatureGenerator

```python
class FeatureGenerator:
    async def generate_features(self, market_data, strategy_signals=None) -> pd.DataFrame
    def generate_features_sync(self, df, strategy_signals=None) -> pd.DataFrame
    def get_feature_info(self) -> Dict
```

async版・sync版は共通パイプライン `_run_feature_pipeline()` を使用。

## 55特徴量構成

| カテゴリ | 個数 | 内容 |
|---------|------|------|
| 基本データ | 2 | close, volume |
| テクニカル指標 | 17 | rsi_14, macd/signal/histogram, atr_14, bb_upper/lower/position, ema_20/50, donchian_high_20/low_20, channel_position, adx_14, plus_di_14/minus_di_14, stoch_k/d, volume_ema, atr_ratio |
| 異常検知 | 1 | volume_ratio |
| ラグ特徴量 | 9 | close_lag_{1,2,3,10}, volume_lag_{1,2,3}, rsi_lag_1, macd_lag_1 |
| 移動統計量 | 5 | close_ma_{10,20}, close_std_{5,10,20} |
| 交互作用 | 5 | rsi_x_atr, macd_x_volume, bb_position_x_volume_ratio, close_x_atr, volume_x_bb_position |
| 時間ベース | 7 | hour, day_of_week, is_market_open_hour, is_europe_session, hour_cos, day_sin, day_cos |
| 戦略シグナル | 6 | strategy_signal_{ATRBased, BBReversal, StochasticDivergence, DonchianChannel, ADXTrendStrength, MACDEMACrossover} |
| **合計** | **55** | |

戦略シグナル特徴量はstrategies.yamlから動的取得。strategy_signals=None時は0.0で生成。

## 使用例

```python
from src.features import FeatureGenerator

generator = FeatureGenerator()

# async版（ライブトレード）
features_df = await generator.generate_features(market_data, strategy_signals)

# sync版（バックテスト）
features_df = generator.generate_features_sync(df, strategy_signals)
```

## 設定

- **データ要件**: OHLCV必須（open, high, low, close, volume）
- **依存**: config/core/feature_order.json（55特徴量定義）
- **環境変数**: 不要（設定ファイルから自動取得）
