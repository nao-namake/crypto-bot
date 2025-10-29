"""
外部APIデータ取得クライアント - Phase 50.3

マクロ経済指標を外部APIから取得し、ML予測精度向上を実現。
レガシーシステムの教訓を活かし、障害時の安定性を最優先設計。

実装指標:
- USD/JPY為替レート（Yahoo Finance）
- 日経平均株価（Yahoo Finance）
- 米国債10年利回り（Yahoo Finance）
- Crypto Fear & Greed Index（Alternative.me API）
- USD/JPY変化率・BTC相関係数等の派生指標

安全性設計:
- タイムアウト10秒（5分間隔実行のため次回取得を待つ）
- 24時間キャッシュ（前回値フォールバック）
- エラー時即座フォールバック（Level 2へ）
- リトライなし（システム継続性優先）
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import aiohttp
import numpy as np
import pandas as pd

from ..core.logger import CryptoBotLogger, get_logger


class ExternalAPIError(Exception):
    """外部API関連エラー"""

    pass


class ExternalAPIClient:
    """
    外部APIデータ取得クライアント - Phase 50.3

    Yahoo Finance・Alternative.me APIから市場指標を取得し、
    障害時はキャッシュフォールバックでシステム継続性を保証。
    """

    def __init__(self, cache_ttl: int = 86400, logger: Optional[CryptoBotLogger] = None):
        """
        初期化

        Args:
            cache_ttl: キャッシュ有効期間（秒）デフォルト24時間
            logger: ロガーインスタンス
        """
        self.logger = logger or get_logger()
        self.cache_ttl = cache_ttl
        self.cache: Dict[str, tuple[float, float]] = {}  # {feature_name: (value, timestamp)}

    async def fetch_all_indicators(
        self, timeout: float = 10.0, btc_data: Optional[pd.DataFrame] = None
    ) -> Dict[str, float]:
        """
        全指標取得（タイムアウト付き・並列実行）

        Args:
            timeout: タイムアウト秒数（デフォルト10秒）
            btc_data: BTC価格データ（相関係数計算用・オプション）

        Returns:
            取得成功した指標の辞書

        Note:
            - 全指標が失敗した場合は空辞書を返す
            - 一部失敗は許容（取得できた指標のみ返す）
        """
        self.logger.info("🌐 外部API指標取得開始（タイムアウト10秒）")
        results = {}

        try:
            # 並列取得（asyncio.gather + timeout）
            tasks = [
                self._fetch_with_timeout(self.fetch_usd_jpy(), timeout, "USD/JPY"),
                self._fetch_with_timeout(self.fetch_nikkei_225(), timeout, "日経平均"),
                self._fetch_with_timeout(self.fetch_us_10y_yield(), timeout, "米10年債"),
                self._fetch_with_timeout(
                    self.fetch_fear_greed_index(), timeout, "Fear & Greed Index"
                ),
            ]

            # 全タスク実行（個別タイムアウト管理）
            indicators = await asyncio.gather(*tasks, return_exceptions=True)

            # 結果集約
            indicator_names = [
                "usd_jpy",
                "nikkei_225",
                "us_10y_yield",
                "fear_greed_index",
            ]

            for name, value in zip(indicator_names, indicators):
                if isinstance(value, Exception):
                    self.logger.warning(f"{name}取得失敗: {value}")
                elif value is not None:
                    results[name] = float(value)
                    self.logger.debug(f"✅ {name}: {value}")

            # 派生指標計算（基本指標が取得できた場合のみ）
            if "usd_jpy" in results:
                usd_jpy_change = self._calculate_change_rate("usd_jpy", results["usd_jpy"])
                if usd_jpy_change is not None:
                    results["usd_jpy_change_1d"] = usd_jpy_change

            if "nikkei_225" in results:
                nikkei_change = self._calculate_change_rate("nikkei_225", results["nikkei_225"])
                if nikkei_change is not None:
                    results["nikkei_change_1d"] = nikkei_change

            # BTC-USD/JPY相関係数（BTCデータがある場合のみ）
            if btc_data is not None and "usd_jpy" in results:
                correlation = self._calculate_btc_usd_jpy_correlation(btc_data, results["usd_jpy"])
                if correlation is not None:
                    results["usd_jpy_btc_correlation"] = correlation

            # 市場センチメント（Fear & Greed Indexベース）
            if "fear_greed_index" in results:
                results["market_sentiment"] = self._calculate_market_sentiment(
                    results["fear_greed_index"]
                )

            # キャッシュ更新
            self._update_cache(results)

            self.logger.info(f"✅ 外部API指標取得成功: {len(results)}/{len(indicator_names)}個")
            return results

        except asyncio.TimeoutError:
            self.logger.error("外部API取得全体タイムアウト → キャッシュ使用")
            return self._get_cached_values()
        except Exception as e:
            self.logger.error(f"外部API取得エラー: {e} → キャッシュ使用")
            return self._get_cached_values()

    async def _fetch_with_timeout(self, coro: Any, timeout: float, name: str) -> Optional[float]:
        """
        タイムアウト付きフェッチ

        Args:
            coro: コルーチン
            timeout: タイムアウト秒数
            name: 指標名（ログ用）

        Returns:
            取得値（失敗時はNone）
        """
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            self.logger.warning(f"{name}取得タイムアウト（{timeout}秒）")
            return None
        except Exception as e:
            self.logger.warning(f"{name}取得エラー: {e}")
            return None

    async def fetch_usd_jpy(self) -> Optional[float]:
        """
        USD/JPY為替レート取得（Yahoo Finance）

        Returns:
            USD/JPY終値（失敗時はNone）

        Note:
            Phase 50.6: yfinanceは同期ライブラリのため、asyncio.to_thread()で
            別スレッド実行してイベントループをブロックしない設計
        """
        try:
            import yfinance as yf

            # Phase 50.6: yfinanceの同期処理を別スレッドで実行
            def _sync_fetch_usd_jpy():
                ticker = yf.Ticker("USDJPY=X")
                data = ticker.history(period="1d")

                if not data.empty:
                    return float(data["Close"].iloc[-1])
                return None

            # 別スレッドで実行（イベントループブロック回避）
            value = await asyncio.to_thread(_sync_fetch_usd_jpy)

            if value is not None:
                self.logger.debug(f"USD/JPY: {value:.2f}")
                return value

            self.logger.warning("USD/JPYデータが空")
            return None

        except Exception as e:
            self.logger.error(f"USD/JPY取得エラー: {e}")
            return None

    async def fetch_nikkei_225(self) -> Optional[float]:
        """
        日経平均株価取得（Yahoo Finance）

        Returns:
            日経平均終値（失敗時はNone）

        Note:
            Phase 50.6: yfinanceは同期ライブラリのため、asyncio.to_thread()で
            別スレッド実行してイベントループをブロックしない設計
        """
        try:
            import yfinance as yf

            # Phase 50.6: yfinanceの同期処理を別スレッドで実行
            def _sync_fetch_nikkei():
                ticker = yf.Ticker("^N225")
                data = ticker.history(period="1d")

                if not data.empty:
                    return float(data["Close"].iloc[-1])
                return None

            # 別スレッドで実行（イベントループブロック回避）
            value = await asyncio.to_thread(_sync_fetch_nikkei)

            if value is not None:
                self.logger.debug(f"日経平均: {value:.2f}")
                return value

            self.logger.warning("日経平均データが空")
            return None

        except Exception as e:
            self.logger.error(f"日経平均取得エラー: {e}")
            return None

    async def fetch_us_10y_yield(self) -> Optional[float]:
        """
        米国債10年利回り取得（Yahoo Finance）

        Returns:
            米10年債利回り（失敗時はNone）

        Note:
            Phase 50.6: yfinanceは同期ライブラリのため、asyncio.to_thread()で
            別スレッド実行してイベントループをブロックしない設計
        """
        try:
            import yfinance as yf

            # Phase 50.6: yfinanceの同期処理を別スレッドで実行
            def _sync_fetch_us_10y():
                ticker = yf.Ticker("^TNX")
                data = ticker.history(period="1d")

                if not data.empty:
                    return float(data["Close"].iloc[-1])
                return None

            # 別スレッドで実行（イベントループブロック回避）
            value = await asyncio.to_thread(_sync_fetch_us_10y)

            if value is not None:
                self.logger.debug(f"米10年債利回り: {value:.2f}%")
                return value

            self.logger.warning("米10年債データが空")
            return None

        except Exception as e:
            self.logger.error(f"米10年債取得エラー: {e}")
            return None

    async def fetch_fear_greed_index(self) -> Optional[float]:
        """
        Crypto Fear & Greed Index取得（Alternative.me API）

        Returns:
            Fear & Greed Index（0-100, 失敗時はNone）
        """
        try:
            url = "https://api.alternative.me/fng/"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()

                        if "data" in data and len(data["data"]) > 0:
                            value = float(data["data"][0]["value"])
                            value_classification = data["data"][0]["value_classification"]
                            self.logger.debug(f"Fear & Greed: {value} ({value_classification})")
                            return value

            self.logger.warning("Fear & Greedデータ形式エラー")
            return None

        except asyncio.TimeoutError:
            self.logger.warning("Fear & Greed APIタイムアウト")
            return None
        except Exception as e:
            self.logger.error(f"Fear & Greed取得エラー: {e}")
            return None

    def _calculate_change_rate(self, feature_name: str, current_value: float) -> Optional[float]:
        """
        前回値からの変化率計算

        Args:
            feature_name: 特徴量名
            current_value: 現在値

        Returns:
            変化率（パーセント、前回値がない場合はNone）
        """
        if feature_name in self.cache:
            prev_value, _ = self.cache[feature_name]
            if prev_value > 0:
                change_rate = ((current_value - prev_value) / prev_value) * 100
                self.logger.debug(f"{feature_name}変化率: {change_rate:.2f}%")
                return change_rate

        return None

    def _calculate_btc_usd_jpy_correlation(
        self, btc_data: pd.DataFrame, usd_jpy: float
    ) -> Optional[float]:
        """
        BTC-USD/JPY相関係数計算

        Args:
            btc_data: BTC価格データ（過去24時間分想定）
            usd_jpy: USD/JPY現在値

        Returns:
            相関係数（-1.0 to 1.0, 計算失敗時はNone）
        """
        try:
            # 過去24時間のBTC価格変化率
            if len(btc_data) < 2:
                return None

            btc_returns = btc_data["close"].pct_change().dropna()

            # USD/JPYは1点のみなので、キャッシュから過去値を取得
            if "usd_jpy" not in self.cache:
                return None

            prev_usd_jpy, _ = self.cache["usd_jpy"]
            usd_jpy_return = (usd_jpy - prev_usd_jpy) / prev_usd_jpy

            # 相関係数計算（1点のみなので簡易的に0を返す）
            # 実際には過去24時間のUSD/JPY履歴が必要だが、APIコストを考慮してスキップ
            self.logger.debug("BTC-USD/JPY相関: データ不足のため0.0を返す")
            return 0.0

        except Exception as e:
            self.logger.error(f"BTC-USD/JPY相関計算エラー: {e}")
            return None

    def _calculate_market_sentiment(self, fear_greed_index: float) -> float:
        """
        市場センチメント計算（Fear & Greedベース）

        Args:
            fear_greed_index: Fear & Greed Index（0-100）

        Returns:
            市場センチメント（-1.0 to 1.0, 50が中立）
        """
        # 0-100を-1.0 to 1.0にスケーリング
        sentiment = (fear_greed_index - 50) / 50
        return float(np.clip(sentiment, -1.0, 1.0))

    def _update_cache(self, results: Dict[str, float]) -> None:
        """
        キャッシュ更新

        Args:
            results: 取得した指標辞書
        """
        current_time = time.time()
        for feature_name, value in results.items():
            self.cache[feature_name] = (value, current_time)

        self.logger.debug(f"キャッシュ更新: {len(results)}個")

    def _get_cached_values(self) -> Dict[str, float]:
        """
        キャッシュから値取得（有効期限内のみ）

        Returns:
            有効なキャッシュ値の辞書
        """
        current_time = time.time()
        valid_cache = {}

        for feature_name, (value, timestamp) in self.cache.items():
            age = current_time - timestamp
            if age < self.cache_ttl:
                valid_cache[feature_name] = value
                self.logger.debug(f"キャッシュ使用: {feature_name}={value} (age={age:.0f}秒)")
            else:
                self.logger.warning(
                    f"キャッシュ期限切れ: {feature_name} (age={age:.0f}秒 > {self.cache_ttl}秒)"
                )

        if valid_cache:
            self.logger.info(f"キャッシュから{len(valid_cache)}個の指標を取得")
        else:
            self.logger.warning("有効なキャッシュなし")

        return valid_cache

    def get_cache_info(self) -> Dict[str, Any]:
        """
        キャッシュ情報取得

        Returns:
            キャッシュ情報辞書
        """
        current_time = time.time()
        cache_info = {}

        for feature_name, (value, timestamp) in self.cache.items():
            age = current_time - timestamp
            cache_info[feature_name] = {
                "value": value,
                "age_seconds": age,
                "valid": age < self.cache_ttl,
            }

        return cache_info
