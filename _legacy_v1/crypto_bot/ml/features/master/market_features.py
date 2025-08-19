"""
Market Features - Phase 16.3-B Split

統合前: crypto_bot/ml/feature_master_implementation.py（1,801行）
分割後: crypto_bot/ml/features/master/market_features.py

機能:
- サポート・レジスタンス、チャートパターン
- 高度テクニカル分析、市場状態特徴量
- 市場構造分析・パターン認識メソッド群

Phase 16.3-B実装日: 2025年8月8日
"""

import logging

import numpy as np
import pandas as pd

# typing imports removed - not currently used in the class structure


logger = logging.getLogger(__name__)


class MarketFeaturesMixin:
    """市場特徴量生成メソッド群（Mixinクラス）"""

    def _generate_support_resistance_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """サポート・レジスタンス系: 5個 (support_distance, resistance_distance, support_strength, price_breakout_up, price_breakout_down)"""
        logger.debug("🔧 サポート・レジスタンス系特徴量生成中...")

        try:
            if all(col in df.columns for col in ["high", "low", "close"]):
                pivot_window = 5  # ピボット検出期間
                lookback_period = 20  # レベル検索期間

                # ピボットハイ・ロー検出
                pivot_highs = self._find_pivot_highs(df["high"], pivot_window)
                pivot_lows = self._find_pivot_lows(df["low"], pivot_window)

                # サポート・レジスタンスレベル計算
                support_levels = []
                resistance_levels = []
                support_strengths = []

                for i in range(len(df)):
                    # 現在位置より前のlookback_period内のピボットを検索
                    start_idx = max(0, i - lookback_period)

                    # サポートレベル（ピボットロー）検索
                    recent_lows = [
                        pivot_lows[j]
                        for j in range(start_idx, i)
                        if pivot_lows[j] is not None
                    ]
                    if recent_lows:
                        # 最も近いサポートレベル
                        support_level = max(
                            recent_lows
                        )  # 現在価格に最も近い（高い）サポート
                        support_strength = len(
                            [
                                low
                                for low in recent_lows
                                if abs(low - support_level) < support_level * 0.01
                            ]
                        )  # 1%以内の類似レベル数
                    else:
                        support_level = (
                            df["low"].iloc[max(0, i - 10) : i].min()
                            if i > 0
                            else df["low"].iloc[i]
                        )
                        support_strength = 1

                    # レジスタンスレベル（ピボットハイ）検索
                    recent_highs = [
                        pivot_highs[j]
                        for j in range(start_idx, i)
                        if pivot_highs[j] is not None
                    ]
                    if recent_highs:
                        # 最も近いレジスタンスレベル
                        resistance_level = min(
                            recent_highs
                        )  # 現在価格に最も近い（低い）レジスタンス
                    else:
                        resistance_level = (
                            df["high"].iloc[max(0, i - 10) : i].max()
                            if i > 0
                            else df["high"].iloc[i]
                        )

                    support_levels.append(support_level)
                    resistance_levels.append(resistance_level)
                    support_strengths.append(support_strength)

                # 1. サポート距離: (現在価格 - サポートレベル) / サポートレベル * 100
                support_distances = [
                    (df["close"].iloc[i] - support_levels[i]) / support_levels[i] * 100
                    for i in range(len(df))
                ]
                df["support_distance"] = support_distances
                self.implemented_features.add("support_distance")

                # 2. レジスタンス距離: (レジスタンスレベル - 現在価格) / 現在価格 * 100
                resistance_distances = [
                    (resistance_levels[i] - df["close"].iloc[i])
                    / df["close"].iloc[i]
                    * 100
                    for i in range(len(df))
                ]
                df["resistance_distance"] = resistance_distances
                self.implemented_features.add("resistance_distance")

                # 3. サポート強度
                df["support_strength"] = support_strengths
                self.implemented_features.add("support_strength")

                # 4. 上方ブレイクアウト: 現在価格がレジスタンスレベルを上抜け
                prev_close = df["close"].shift(1)
                breakout_up = []
                for i in range(len(df)):
                    if i == 0:
                        breakout_up.append(0)
                    else:
                        # 前回は下、今回は上
                        prev_below = prev_close.iloc[i] <= resistance_levels[i - 1]
                        curr_above = df["close"].iloc[i] > resistance_levels[i]
                        breakout_up.append(1 if prev_below and curr_above else 0)

                df["price_breakout_up"] = breakout_up
                self.implemented_features.add("price_breakout_up")

                # 5. 下方ブレイクアウト: 現在価格がサポートレベルを下抜け
                breakout_down = []
                for i in range(len(df)):
                    if i == 0:
                        breakout_down.append(0)
                    else:
                        # 前回は上、今回は下
                        prev_above = prev_close.iloc[i] >= support_levels[i - 1]
                        curr_below = df["close"].iloc[i] < support_levels[i]
                        breakout_down.append(1 if prev_above and curr_below else 0)

                df["price_breakout_down"] = breakout_down
                self.implemented_features.add("price_breakout_down")

                logger.debug("✅ サポート・レジスタンス系特徴量: 5/5個実装完了")
            else:
                logger.warning("⚠️ high, low, close列が必要です")

        except Exception as e:
            logger.error(f"❌ サポート・レジスタンス系特徴量生成エラー: {e}")

        return df

    def _find_pivot_highs(self, series: pd.Series, window: int) -> list:
        """ピボットハイを検出"""
        pivot_highs = [None] * len(series)

        for i in range(window, len(series) - window):
            is_pivot_high = True
            center_value = series.iloc[i]

            # 前後window期間の最高値かチェック
            for j in range(i - window, i + window + 1):
                if j != i and series.iloc[j] >= center_value:
                    is_pivot_high = False
                    break

            if is_pivot_high:
                pivot_highs[i] = center_value

        return pivot_highs

    def _find_pivot_lows(self, series: pd.Series, window: int) -> list:
        """ピボットローを検出"""
        pivot_lows = [None] * len(series)

        for i in range(window, len(series) - window):
            is_pivot_low = True
            center_value = series.iloc[i]

            # 前後window期間の最安値かチェック
            for j in range(i - window, i + window + 1):
                if j != i and series.iloc[j] <= center_value:
                    is_pivot_low = False
                    break

            if is_pivot_low:
                pivot_lows[i] = center_value

        return pivot_lows

    def _generate_chart_pattern_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """チャートパターン系: 4個 (doji, hammer, engulfing, pinbar)"""
        logger.debug("🔧 チャートパターン系特徴量生成中...")

        try:
            if all(col in df.columns for col in ["open", "high", "low", "close"]):
                # 実体とヒゲの計算
                body_size = np.abs(df["close"] - df["open"])
                total_range = df["high"] - df["low"]
                upper_shadow = df["high"] - np.maximum(df["open"], df["close"])
                lower_shadow = np.minimum(df["open"], df["close"]) - df["low"]

                # ゼロ除算回避
                body_ratio = np.where(total_range > 0, body_size / total_range, 0)
                upper_shadow_ratio = np.where(
                    total_range > 0, upper_shadow / total_range, 0
                )
                lower_shadow_ratio = np.where(
                    total_range > 0, lower_shadow / total_range, 0
                )

                # 1. Doji（同事足）: 実体が小さく（全体の10%以下）、上下にヒゲ
                doji = (
                    (body_ratio < 0.1)
                    & (upper_shadow_ratio > 0.2)
                    & (lower_shadow_ratio > 0.2)
                ).astype(int)
                df["doji"] = doji
                self.implemented_features.add("doji")

                # 2. Hammer（ハンマー足）: 下方向の長いヒゲ、小さな実体、短い上ヒゲ
                # 下降トレンド中に出現すると反転シグナルになる
                prev_close = df["close"].shift(1)
                is_downtrend = df["close"] < prev_close  # 簡略化された下降判定

                hammer = (
                    is_downtrend
                    & (body_ratio < 0.25)  # 実体は全体の25%以下
                    & (lower_shadow_ratio > 0.5)  # 下ヒゲが全体の50%以上
                    & (upper_shadow_ratio < 0.15)
                ).astype(
                    int
                )  # 上ヒゲは15%以下
                df["hammer"] = hammer
                self.implemented_features.add("hammer")

                # 3. Engulfing（包み線）: 前のローソク足を完全に包む
                prev_open = df["open"].shift(1)
                # prev_high = df["high"].shift(1)  # 未使用変数削除
                # prev_low = df["low"].shift(1)   # 未使用変数削除

                # 強気包み線: 前回陰線、今回陽線で前回を包む
                bullish_engulfing = (
                    (prev_close < prev_open)  # 前回陰線
                    & (df["close"] > df["open"])  # 今回陽線
                    & (df["open"] < prev_close)  # 今回始値が前回終値より低い
                    & (df["close"] > prev_open)
                )  # 今回終値が前回始値より高い

                # 弱気包み線: 前回陽線、今回陰線で前回を包む
                bearish_engulfing = (
                    (prev_close > prev_open)  # 前回陽線
                    & (df["close"] < df["open"])  # 今回陰線
                    & (df["open"] > prev_close)  # 今回始値が前回終値より高い
                    & (df["close"] < prev_open)
                )  # 今回終値が前回始値より低い

                # エンゲルフィン（包み線）パターン: 強気または弱気包み線
                engulfing = (bullish_engulfing | bearish_engulfing).astype(int)
                df["engulfing"] = engulfing
                self.implemented_features.add("engulfing")

                # 4. Pinbar（ピンバー）: 一方向に長いヒゲ、小さな実体
                # 上方向ピンバー（上ヒゲが長い）または下方向ピンバー（下ヒゲが長い）
                upper_pinbar = (
                    (body_ratio < 0.25)  # 小さな実体
                    & (upper_shadow_ratio > 0.6)  # 長い上ヒゲ
                    & (lower_shadow_ratio < 0.15)
                )  # 短い下ヒゲ

                lower_pinbar = (
                    (body_ratio < 0.25)  # 小さな実体
                    & (lower_shadow_ratio > 0.6)  # 長い下ヒゲ
                    & (upper_shadow_ratio < 0.15)
                )  # 短い上ヒゲ

                pinbar = (upper_pinbar | lower_pinbar).astype(int)
                df["pinbar"] = pinbar
                self.implemented_features.add("pinbar")

                logger.debug("✅ チャートパターン系特徴量: 4/4個実装完了")
            else:
                logger.warning("⚠️ open, high, low, close列が必要です")

        except Exception as e:
            logger.error(f"❌ チャートパターン系特徴量生成エラー: {e}")

        return df

    def _generate_advanced_technical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """高度テクニカル系: 10個 (roc_10, roc_20, trix, mass_index, keltner_upper, keltner_lower, donchian_upper, donchian_lower, ichimoku_conv, ichimoku_base)"""
        logger.debug("🔧 高度テクニカル系特徴量生成中...")

        try:
            if all(col in df.columns for col in ["high", "low", "close"]):
                # 1-2. ROC (Rate of Change): 変化率
                df["roc_10"] = (
                    (df["close"] - df["close"].shift(10)) / df["close"].shift(10) * 100
                ).fillna(0)
                self.implemented_features.add("roc_10")

                df["roc_20"] = (
                    (df["close"] - df["close"].shift(20)) / df["close"].shift(20) * 100
                ).fillna(0)
                self.implemented_features.add("roc_20")

                # 3. TRIX: Triple Exponentially Smoothed Moving Average
                # 第1段階: EMA
                ema1 = df["close"].ewm(span=14, adjust=False).mean()
                # 第2段階: EMAのEMA
                ema2 = ema1.ewm(span=14, adjust=False).mean()
                # 第3段階: EMAのEMAのEMA
                ema3 = ema2.ewm(span=14, adjust=False).mean()
                # TRIX: EMA3の変化率
                df["trix"] = ((ema3 - ema3.shift(1)) / ema3.shift(1) * 10000).fillna(
                    0
                )  # 10000倍でスケール調整
                self.implemented_features.add("trix")

                # 4. Mass Index: ボラティリティ指標
                high_low_ratio = df["high"] / df["low"]
                ema_ratio = high_low_ratio.ewm(span=9, adjust=False).mean()
                mass_index_sum = ema_ratio.rolling(window=25).sum()
                df["mass_index"] = mass_index_sum.fillna(25.0)  # デフォルト値
                self.implemented_features.add("mass_index")

                # 5-6. Keltner Channel: ケルトナーチャネル
                keltner_period = 20
                keltner_multiplier = 2.0

                # 中央線（EMA）
                keltner_center = (
                    df["close"].ewm(span=keltner_period, adjust=False).mean()
                )

                # ATR計算（True Range）
                prev_close = df["close"].shift(1)
                tr1 = df["high"] - df["low"]
                tr2 = (df["high"] - prev_close).abs()
                tr3 = (df["low"] - prev_close).abs()
                true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                atr = true_range.ewm(span=keltner_period, adjust=False).mean()

                # ケルトナーチャネル上限・下限
                df["keltner_upper"] = keltner_center + (keltner_multiplier * atr)
                self.implemented_features.add("keltner_upper")

                df["keltner_lower"] = keltner_center - (keltner_multiplier * atr)
                self.implemented_features.add("keltner_lower")

                # 7-8. Donchian Channel: ドンチャンチャネル
                donchian_period = 20

                df["donchian_upper"] = df["high"].rolling(window=donchian_period).max()
                self.implemented_features.add("donchian_upper")

                df["donchian_lower"] = df["low"].rolling(window=donchian_period).min()
                self.implemented_features.add("donchian_lower")

                # 9-10. Ichimoku (一目均衡表): 転換線・基準線
                # 転換線: (9期間最高値 + 9期間最安値) / 2
                tenkan_high = df["high"].rolling(window=9).max()
                tenkan_low = df["low"].rolling(window=9).min()
                df["ichimoku_conv"] = (tenkan_high + tenkan_low) / 2
                self.implemented_features.add("ichimoku_conv")

                # 基準線: (26期間最高値 + 26期間最安値) / 2
                kijun_high = df["high"].rolling(window=26).max()
                kijun_low = df["low"].rolling(window=26).min()
                df["ichimoku_base"] = (kijun_high + kijun_low) / 2
                self.implemented_features.add("ichimoku_base")

                logger.debug("✅ 高度テクニカル系特徴量: 10/10個実装完了")
            else:
                logger.warning("⚠️ high, low, close列が必要です")

        except Exception as e:
            logger.error(f"❌ 高度テクニカル系特徴量生成エラー: {e}")

        return df

    def _generate_market_state_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """市場状態系: 6個 (price_efficiency, trend_consistency, volatility_regime, momentum_quality, market_phase, volume_price_correlation)"""
        logger.debug("🔧 市場状態系特徴量生成中...")

        try:
            if all(col in df.columns for col in ["high", "low", "close", "volume"]):
                # 1. Price Efficiency: 価格効率性 (価格変動と真の価格発見の効率性)
                # 方法: 価格変動の効率性指標（Efficiency Ratio）
                prev_close = df["close"].shift(1)

                # 価格変動の絶対値（方向性を考慮した純変動）
                price_change = (
                    df["close"] - df["close"].shift(10)
                ).abs()  # 10期間の価格変動

                # 経路の長さ（実際の価格変動の合計）
                path_length = df["close"].diff().abs().rolling(window=10).sum()

                # 効率性比率: 純変動 / 経路の長さ（1に近いほど効率的）
                efficiency_ratio = np.where(
                    (path_length > 0) & (price_change > 0),
                    price_change / path_length,
                    0.5,
                )
                df["price_efficiency"] = pd.Series(
                    efficiency_ratio, index=df.index
                ).fillna(0.5)
                self.implemented_features.add("price_efficiency")

                # 2. Trend Consistency: トレンド一貫性 (方向性の持続性)
                # 方法: 移動平均の傾きの一貫性を測定
                ma_20 = df["close"].rolling(window=20).mean()
                ma_slope = ma_20.diff()
                # 過去10期間の傾きの標準偏差（小さいほど一貫性が高い）
                slope_consistency = ma_slope.rolling(window=10).std()
                max_consistency = slope_consistency.quantile(
                    0.95
                )  # 95%パーセンタイルを最大値とする
                df["trend_consistency"] = (
                    1 - (slope_consistency / max_consistency).clip(0, 1)
                ).fillna(0.5)
                self.implemented_features.add("trend_consistency")

                # 3. Volatility Regime: ボラティリティ体制 (高/低ボラティリティの判定)
                # 方法: 過去30期間の価格変動率の標準偏差を正規化
                returns_volatility = df["close"].pct_change().rolling(window=30).std()
                vol_median = returns_volatility.median()
                # 中央値基準で正規化（0.5が中央値、1.0が高ボラティリティ）
                volatility_regime_values = np.where(
                    vol_median > 0,
                    (returns_volatility / vol_median / 2).clip(0, 1),
                    0.5,
                )
                df["volatility_regime"] = pd.Series(
                    volatility_regime_values, index=df.index
                ).fillna(0.5)
                self.implemented_features.add("volatility_regime")

                # 4. Momentum Quality: モメンタム品質 (モメンタムの持続性と強さ)
                # 方法: RSIとPrice Momentum Oscillatorを組み合わせた品質指標
                returns = df["close"].pct_change()
                momentum_10 = returns.rolling(window=10).mean()
                momentum_volatility = returns.rolling(window=10).std()

                # モメンタムの信号対雑音比
                momentum_snr = np.where(
                    momentum_volatility > 0, momentum_10.abs() / momentum_volatility, 0
                )
                # 0-1に正規化（上位25%を高品質とする）
                momentum_snr_series = pd.Series(momentum_snr, index=df.index)
                momentum_75p = momentum_snr_series.quantile(0.75)
                if momentum_75p > 0:
                    momentum_quality_values = (momentum_snr_series / momentum_75p).clip(
                        0, 1
                    )
                else:
                    momentum_quality_values = pd.Series(0.5, index=df.index)
                df["momentum_quality"] = momentum_quality_values.fillna(0.5)
                self.implemented_features.add("momentum_quality")

                # 5. Market Phase: 市場フェーズ (トレンド/レンジの判定)
                # 方法: ADXとボリンジャーバンド幅を組み合わせた市場状態判定
                # ADX計算
                high_low = df["high"] - df["low"]
                high_close = (df["high"] - prev_close).abs()
                low_close = (df["low"] - prev_close).abs()
                true_range_adx = pd.concat(
                    [high_low, high_close, low_close], axis=1
                ).max(axis=1)

                plus_dm = np.where(
                    (df["high"].diff() > df["low"].diff().abs())
                    & (df["high"].diff() > 0),
                    df["high"].diff(),
                    0,
                )
                minus_dm = np.where(
                    (df["low"].diff().abs() > df["high"].diff())
                    & (df["low"].diff() < 0),
                    df["low"].diff().abs(),
                    0,
                )

                atr_14 = true_range_adx.rolling(window=14).mean()
                plus_di = (
                    pd.Series(plus_dm, index=df.index).rolling(window=14).mean()
                    / atr_14
                    * 100
                ).fillna(0)
                minus_di = (
                    pd.Series(minus_dm, index=df.index).rolling(window=14).mean()
                    / atr_14
                    * 100
                ).fillna(0)

                # DX計算（ゼロ除算回避）
                di_sum = plus_di + minus_di
                dx = np.where(di_sum > 0, (plus_di - minus_di).abs() / di_sum * 100, 0)
                adx = pd.Series(dx, index=df.index).rolling(window=14).mean().fillna(25)

                # ADX > 25でトレンド、< 25でレンジとして正規化
                df["market_phase"] = (adx / 50).clip(0, 1)  # 0=レンジ, 1=強いトレンド
                self.implemented_features.add("market_phase")

                # 6. Volume Price Correlation: 出来高価格相関 (出来高と価格の連動性)
                # 方法: 過去20期間の出来高と価格変動率の相関係数
                price_change_for_corr = df["close"].pct_change()
                volume_normalized = (
                    df["volume"] / df["volume"].rolling(window=20).mean()
                )

                # 20期間の相関係数を計算
                correlation_window = 20
                volume_price_corr = []
                for i in range(len(df)):
                    if i < correlation_window - 1:
                        volume_price_corr.append(0.0)
                    else:
                        start_idx = i - correlation_window + 1
                        end_idx = i + 1

                        price_slice = price_change_for_corr.iloc[
                            start_idx:end_idx
                        ].dropna()
                        volume_slice = volume_normalized.iloc[
                            start_idx:end_idx
                        ].dropna()

                        if len(price_slice) > 5 and len(volume_slice) > 5:
                            # 共通のインデックスで整列
                            common_idx = price_slice.index.intersection(
                                volume_slice.index
                            )
                            if len(common_idx) > 5:
                                corr = price_slice.loc[common_idx].corr(
                                    volume_slice.loc[common_idx]
                                )
                                volume_price_corr.append(
                                    corr if not pd.isna(corr) else 0.0
                                )
                            else:
                                volume_price_corr.append(0.0)
                        else:
                            volume_price_corr.append(0.0)

                # 相関係数を0-1に変換（絶対値を取って正規化）
                df["volume_price_correlation"] = [abs(x) for x in volume_price_corr]
                self.implemented_features.add("volume_price_correlation")

                logger.debug("✅ 市場状態系特徴量: 6/6個実装完了")
            else:
                logger.warning("⚠️ high, low, close, volume列が必要です")

        except Exception as e:
            logger.error(f"❌ 市場状態系特徴量生成エラー: {e}")

        return df

    def _generate_remaining_features_placeholder(
        self, df: pd.DataFrame
    ) -> pd.DataFrame:
        """将来の追加特徴量用プレースホルダーメソッド"""
        logger.debug("🔧 追加特徴量プレースホルダー（現在は何も処理しない）")
        return df
