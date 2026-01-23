"""
市場レジーム分類器 - Phase 61.1

市場状況を4段階に分類し、動的戦略選択とML統合最適化を実現する。
レンジ型bot最適化のための核心システム。

判定ロジック（thresholds.yamlから読み込み）:
- tight_range: BB幅 < 2.5% AND 価格変動 < 1.5%（Phase 61.1: 厳格化）
- normal_range: BB幅 < 5% AND ADX < 20
- trending: ADX > 20 AND EMA傾き > 0.7%（Phase 61.1: 緩和）
- high_volatility: ATR比 > 1.8%

Phase 51.2-New: 市場状況分類器実装
Phase 61.1: ハードコード値をthresholds.yamlから読み込むように変更
"""

import os
from typing import Optional

import pandas as pd

from ...core.config.threshold_manager import get_threshold
from ...core.logger import get_logger
from .regime_types import RegimeType


class MarketRegimeClassifier:
    """
    市場レジーム分類器

    市場データ（DataFrame）を受け取り、現在の市場状況を4段階に分類。
    レンジ/トレンド/高ボラティリティを自動判定する。

    分類結果は動的戦略選択・ML統合最適化に使用される。

    Attributes:
        logger: ロガー
        bb_period: ボリンジャーバンド期間（デフォルト: 20）
        donchian_period: Donchianチャネル期間（デフォルト: 20）
        ema_period: EMA期間（デフォルト: 20）
        ema_lookback: EMA傾き計算参照期間（デフォルト: 5）
        price_range_lookback: 価格変動率計算参照期間（デフォルト: 20）
    """

    def __init__(
        self,
        bb_period: int = 20,
        donchian_period: int = 20,
        ema_period: int = 20,
        ema_lookback: int = 5,
        price_range_lookback: int = 20,
    ):
        """
        初期化

        Args:
            bb_period: ボリンジャーバンド期間
            donchian_period: Donchianチャネル期間
            ema_period: EMA期間
            ema_lookback: EMA傾き計算参照期間
            price_range_lookback: 価格変動率計算参照期間
        """
        self.logger = get_logger()
        self.bb_period = bb_period
        self.donchian_period = donchian_period
        self.ema_period = ema_period
        self.ema_lookback = ema_lookback
        self.price_range_lookback = price_range_lookback

    def classify(self, df: pd.DataFrame) -> RegimeType:
        """
        市場状況を4段階分類

        優先順位:
        1. 高ボラティリティ判定（最優先・リスク回避）
        2. 狭いレンジ判定
        3. トレンド判定
        4. 通常レンジ判定
        5. デフォルト: 通常レンジ

        Args:
            df: 市場データ（必須カラム: close, high, low, atr_14, adx_14, ema_20等）

        Returns:
            RegimeType: 分類結果

        Raises:
            ValueError: 必須カラムが不足している場合
        """
        try:
            # 必須カラム確認
            required_columns = ["close", "high", "low", "atr_14", "adx_14"]
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"必須カラムが不足しています: {missing_columns}")

            # レンジ判定指標計算
            bb_width = self._calc_bb_width(df)
            _donchian_width = self._calc_donchian_width(df)  # noqa: F841 将来の拡張用
            price_range = self._calc_price_range(df, lookback=self.price_range_lookback)

            # トレンド判定指標計算
            adx = df["adx_14"].iloc[-1]
            ema_slope = self._calc_ema_slope(df, period=self.ema_period, lookback=self.ema_lookback)

            # ボラティリティ判定指標計算
            atr_ratio = df["atr_14"].iloc[-1] / df["close"].iloc[-1]

            # 閾値を設定ファイルから取得（ログ表示用）
            hv_threshold = get_threshold("market_regime.high_volatility.atr_ratio_threshold", 0.018)
            tr_bb_threshold = get_threshold("market_regime.tight_range.bb_width_threshold", 0.025)
            tr_price_threshold = get_threshold(
                "market_regime.tight_range.price_range_threshold", 0.015
            )
            trend_adx_threshold = get_threshold("market_regime.trending.adx_threshold", 20)
            trend_ema_threshold = get_threshold("market_regime.trending.ema_slope_threshold", 0.007)
            nr_bb_threshold = get_threshold("market_regime.normal_range.bb_width_threshold", 0.05)
            nr_adx_threshold = get_threshold("market_regime.normal_range.adx_threshold", 20)

            # 分類ロジック（優先順位順）
            # 1. 高ボラティリティ判定（最優先）
            if self._is_high_volatility(atr_ratio):
                # Phase 51.9-Fix: バックテストモードでDEBUGに変更（速度最適化・99%ログ削減）
                if os.environ.get("BACKTEST_MODE") == "true":
                    self.logger.debug(
                        f"⚠️ 高ボラティリティ検出: ATR比={atr_ratio:.4f} (> {hv_threshold})"
                    )
                else:
                    self.logger.warning(
                        f"⚠️ 高ボラティリティ検出: ATR比={atr_ratio:.4f} (> {hv_threshold})"
                    )
                return RegimeType.HIGH_VOLATILITY

            # 2. 狭いレンジ判定
            if self._is_tight_range(bb_width, price_range):
                # Phase 51.9-Fix: バックテストモードでDEBUGに変更（速度最適化・99%ログ削減）
                if os.environ.get("BACKTEST_MODE") == "true":
                    self.logger.debug(
                        f"📊 狭いレンジ検出: BB幅={bb_width:.4f} (< {tr_bb_threshold}), "
                        f"価格変動={price_range:.4f} (< {tr_price_threshold})"
                    )
                else:
                    self.logger.warning(
                        f"📊 狭いレンジ検出: BB幅={bb_width:.4f} (< {tr_bb_threshold}), "
                        f"価格変動={price_range:.4f} (< {tr_price_threshold})"
                    )
                return RegimeType.TIGHT_RANGE

            # 3. トレンド判定
            if self._is_trending(adx, ema_slope):
                # Phase 51.9-Fix: バックテストモードでDEBUGに変更（速度最適化・99%ログ削減）
                if os.environ.get("BACKTEST_MODE") == "true":
                    self.logger.debug(
                        f"📈 トレンド検出: ADX={adx:.2f} (> {trend_adx_threshold}), "
                        f"EMA傾き={ema_slope:.4f} (> {trend_ema_threshold})"
                    )
                else:
                    self.logger.warning(
                        f"📈 トレンド検出: ADX={adx:.2f} (> {trend_adx_threshold}), "
                        f"EMA傾き={ema_slope:.4f} (> {trend_ema_threshold})"
                    )
                return RegimeType.TRENDING

            # 4. 通常レンジ判定
            if self._is_normal_range(bb_width, adx):
                # Phase 51.9-Fix: バックテストモードでDEBUGに変更（速度最適化・99%ログ削減）
                if os.environ.get("BACKTEST_MODE") == "true":
                    self.logger.debug(
                        f"📊 通常レンジ検出: BB幅={bb_width:.4f} (< {nr_bb_threshold}), "
                        f"ADX={adx:.2f} (< {nr_adx_threshold})"
                    )
                else:
                    self.logger.warning(
                        f"📊 通常レンジ検出: BB幅={bb_width:.4f} (< {nr_bb_threshold}), "
                        f"ADX={adx:.2f} (< {nr_adx_threshold})"
                    )
                return RegimeType.NORMAL_RANGE

            # 5. デフォルト: 通常レンジ
            # Phase 51.9-Fix: バックテストモードでDEBUGに変更（速度最適化・99%ログ削減）
            if os.environ.get("BACKTEST_MODE") == "true":
                self.logger.debug(
                    f"📊 デフォルト分類: 通常レンジ (BB幅={bb_width:.4f}, ADX={adx:.2f})"
                )
            else:
                self.logger.warning(
                    f"📊 デフォルト分類: 通常レンジ (BB幅={bb_width:.4f}, ADX={adx:.2f})"
                )
            return RegimeType.NORMAL_RANGE

        except Exception as e:
            self.logger.error(f"市場状況分類エラー: {e} - デフォルト（通常レンジ）を返却")
            return RegimeType.NORMAL_RANGE

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 計算メソッド
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _calc_bb_width(self, df: pd.DataFrame, period: Optional[int] = None) -> float:
        """
        ボリンジャーバンド幅を計算

        Args:
            df: 市場データ
            period: BB期間（Noneの場合はself.bb_period使用）

        Returns:
            float: BB幅（終値に対する比率）
        """
        period = period or self.bb_period
        close = df["close"].iloc[-period:]

        bb_middle = close.mean()
        bb_std_dev = close.std()

        # Phase 55.12: NaN値チェック（データ不足時のフォールバック）
        if pd.isna(bb_std_dev) or pd.isna(bb_middle):
            return 0.04  # TIGHT_RANGE閾値(0.03)とNORMAL_RANGE閾値(0.05)の中間値

        bb_upper = bb_middle + (bb_std_dev * 2)
        bb_lower = bb_middle - (bb_std_dev * 2)

        bb_width = (bb_upper - bb_lower) / bb_middle if bb_middle > 0 else 0.0
        return bb_width

    def _calc_donchian_width(self, df: pd.DataFrame, period: Optional[int] = None) -> float:
        """
        Donchianチャネル幅を計算

        Args:
            df: 市場データ
            period: Donchian期間（Noneの場合はself.donchian_period使用）

        Returns:
            float: Donchian幅（終値に対する比率）
        """
        period = period or self.donchian_period

        if "donchian_high_20" in df.columns and "donchian_low_20" in df.columns:
            # 既存のDonchianカラムを使用
            donchian_high = df["donchian_high_20"].iloc[-1]
            donchian_low = df["donchian_low_20"].iloc[-1]
        else:
            # 手動計算
            high = df["high"].iloc[-period:]
            low = df["low"].iloc[-period:]
            donchian_high = high.max()
            donchian_low = low.min()

        close = df["close"].iloc[-1]
        donchian_width = (donchian_high - donchian_low) / close if close > 0 else 0.0
        return donchian_width

    def _calc_price_range(self, df: pd.DataFrame, lookback: int = 20) -> float:
        """
        価格変動率を計算（過去N期間の最高値と最安値の差）

        Args:
            df: 市場データ
            lookback: 参照期間

        Returns:
            float: 価格変動率
        """
        close = df["close"].iloc[-lookback:]
        price_max = close.max()
        price_min = close.min()
        current_price = df["close"].iloc[-1]

        price_range = (price_max - price_min) / current_price if current_price > 0 else 0.0
        return price_range

    def _calc_ema_slope(self, df: pd.DataFrame, period: int = 20, lookback: int = 5) -> float:
        """
        EMA傾きを計算

        Args:
            df: 市場データ
            period: EMA期間
            lookback: 傾き計算参照期間

        Returns:
            float: EMA傾き（比率）
        """
        ema_col = f"ema_{period}"

        if ema_col in df.columns:
            # 既存のEMAカラムを使用
            ema = df[ema_col]
        else:
            # 手動計算
            ema = df["close"].ewm(span=period, adjust=False).mean()

        # 傾き計算: (現在のEMA - lookback期間前のEMA) / lookback期間前のEMA
        if len(ema) < lookback + 1:
            return 0.0

        current_ema = ema.iloc[-1]
        past_ema = ema.iloc[-(lookback + 1)]

        ema_slope = (current_ema - past_ema) / past_ema if past_ema > 0 else 0.0
        return ema_slope

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 判定メソッド
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _is_tight_range(self, bb_width: float, price_range: float) -> bool:
        """
        狭いレンジ相場判定

        判定基準: BB幅 < threshold AND 価格変動 < threshold
        Phase 61.1: thresholds.yamlから閾値を読み込み

        Args:
            bb_width: BB幅
            price_range: 価格変動率

        Returns:
            bool: 狭いレンジの場合True
        """
        bb_threshold = get_threshold("market_regime.tight_range.bb_width_threshold", 0.025)
        price_threshold = get_threshold("market_regime.tight_range.price_range_threshold", 0.015)
        return bb_width < bb_threshold and price_range < price_threshold

    def _is_normal_range(self, bb_width: float, adx: float) -> bool:
        """
        通常レンジ相場判定

        判定基準: BB幅 < threshold AND ADX < threshold
        Phase 61.1: thresholds.yamlから閾値を読み込み

        Args:
            bb_width: BB幅
            adx: ADX値

        Returns:
            bool: 通常レンジの場合True
        """
        bb_threshold = get_threshold("market_regime.normal_range.bb_width_threshold", 0.05)
        adx_threshold = get_threshold("market_regime.normal_range.adx_threshold", 20)
        return bb_width < bb_threshold and adx < adx_threshold

    def _is_trending(self, adx: float, ema_slope: float) -> bool:
        """
        トレンド相場判定

        判定基準: ADX > threshold AND |EMA傾き| > threshold
        Phase 61.1: thresholds.yamlから閾値を読み込み（緩和して発生率増加）

        Args:
            adx: ADX値
            ema_slope: EMA傾き

        Returns:
            bool: トレンド相場の場合True
        """
        adx_threshold = get_threshold("market_regime.trending.adx_threshold", 20)
        ema_threshold = get_threshold("market_regime.trending.ema_slope_threshold", 0.007)
        return adx > adx_threshold and abs(ema_slope) > ema_threshold

    def _is_high_volatility(self, atr_ratio: float) -> bool:
        """
        高ボラティリティ判定

        判定基準: ATR比 > threshold
        Phase 61.1: thresholds.yamlから閾値を読み込み

        Phase 51.2-Fix: 3.0% → 1.8%（4時間足最適化）
        - 根拠: 全期間最大2.20%・10月11日暴落1.97%を確実に検出

        Args:
            atr_ratio: ATR比（ATR / 終値）

        Returns:
            bool: 高ボラティリティの場合True
        """
        threshold = get_threshold("market_regime.high_volatility.atr_ratio_threshold", 0.018)
        return atr_ratio > threshold

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ユーティリティメソッド
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def get_regime_stats(self, df: pd.DataFrame) -> dict:
        """
        市場状況の詳細統計を取得（デバッグ・分析用）

        Args:
            df: 市場データ

        Returns:
            dict: 市場状況統計
        """
        bb_width = self._calc_bb_width(df)
        donchian_width = self._calc_donchian_width(df)
        price_range = self._calc_price_range(df)
        adx = df["adx_14"].iloc[-1]
        ema_slope = self._calc_ema_slope(df)
        atr_ratio = df["atr_14"].iloc[-1] / df["close"].iloc[-1]

        return {
            "regime": self.classify(df),
            "bb_width": bb_width,
            "donchian_width": donchian_width,
            "price_range": price_range,
            "adx": adx,
            "ema_slope": ema_slope,
            "atr_ratio": atr_ratio,
        }
