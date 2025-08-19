"""
HTTPクライアント最適化モジュール
Phase H.19: Cloud Run環境での外部API接続安定化

主な最適化:
- HTTPセッションの再利用
- DNS解決の最適化
- 接続プールの管理
- リトライ戦略の改善
- Cloud Run環境特有の設定
"""

import logging
import os
from typing import Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class OptimizedHTTPClient:
    """最適化されたHTTPクライアント"""

    # グローバルセッションインスタンス（シングルトン）
    _instances: Dict[str, "OptimizedHTTPClient"] = {}

    def __init__(self, client_name: str = "default"):
        """初期化

        Args:
            client_name: クライアント識別名（API別に分ける場合）
        """
        self.client_name = client_name
        self.is_cloud_run = os.getenv("K_SERVICE") is not None

        # セッション作成
        self.session = self._create_optimized_session()

        # DNS解決最適化
        self._optimize_dns_resolution()

        logger.info(
            f"🚀 OptimizedHTTPClient '{client_name}' initialized "
            f"(Cloud Run: {self.is_cloud_run})"
        )

    @classmethod
    def get_instance(cls, client_name: str = "default") -> "OptimizedHTTPClient":
        """シングルトンインスタンスの取得"""
        if client_name not in cls._instances:
            if cls.__name__ == "OptimizedHTTPClient":
                cls._instances[client_name] = cls(client_name)
            else:
                # サブクラスの場合は引数なしで初期化
                cls._instances[client_name] = cls()
        return cls._instances[client_name]

    def _create_optimized_session(self) -> requests.Session:
        """最適化されたHTTPセッションの作成"""
        session = requests.Session()

        # Phase H.20.1.2: 強化されたリトライ戦略
        retry_strategy = Retry(
            total=5,  # 総リトライ回数増加（3→5）
            backoff_factor=2.0,  # より積極的な指数バックオフ（1.5→2.0）
            status_forcelist=[
                429,
                500,
                502,
                503,
                504,
                520,
                521,
                522,
                523,
                524,
            ],  # CloudFlareエラーも追加
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"],
            # Cloud Run環境では接続エラーもリトライ
            raise_on_status=False if self.is_cloud_run else True,
            # 接続エラーもリトライ対象に追加
            raise_on_redirect=False,
        )

        # Phase H.20.1.2: Cloud Run環境用強化設定
        if self.is_cloud_run:
            # 接続プールサイズを増やす
            pool_connections = 25  # 20→25に増加
            pool_maxsize = 25
            # より積極的なタイムアウト設定
            timeout_connect = 15  # 10→15秒に延長
            timeout_read = 45  # 30→45秒に延長
        else:
            # ローカル環境
            pool_connections = 10
            pool_maxsize = 10
            timeout_connect = 8  # 5→8秒に延長
            timeout_read = 25  # 15→25秒に延長

        # HTTPアダプター設定
        adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=retry_strategy,
            pool_block=False,  # プールが満杯でもブロックしない
        )

        # アダプターをマウント
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # デフォルトヘッダー設定
        session.headers.update(
            {
                "User-Agent": (
                    "CryptoBot/1.0 (Cloud Run Optimized)"
                    if self.is_cloud_run
                    else "CryptoBot/1.0"
                ),
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",  # 接続の再利用
                "Cache-Control": "no-cache",
            }
        )

        # タイムアウト設定（デフォルト）
        session.timeout = (timeout_connect, timeout_read)

        # SSL検証（必要に応じて調整）
        session.verify = True

        return session

    def _optimize_dns_resolution(self):
        """DNS解決の最適化"""
        if self.is_cloud_run:
            # Cloud Run環境でのDNS最適化
            # Google Cloud内部DNSを優先
            import socket

            # DNSキャッシュタイムアウトを延長
            socket.setdefaulttimeout(10)

            # 環境変数でDNSキャッシュ設定
            os.environ.setdefault("PYRESHARK_DNS_CACHE_TTL", "3600")  # 1時間

            logger.debug("DNS resolution optimized for Cloud Run")

    def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> requests.Response:
        """HTTPリクエストの実行

        Args:
            method: HTTPメソッド
            url: リクエストURL
            headers: 追加ヘッダー
            timeout: タイムアウト（秒）
            **kwargs: その他のrequestsパラメータ

        Returns:
            レスポンスオブジェクト
        """
        # Cloud Run環境では長めのタイムアウト
        if timeout is None:
            timeout = (10, 30) if self.is_cloud_run else (5, 15)

        # ヘッダーのマージ
        if headers:
            request_headers = self.session.headers.copy()
            request_headers.update(headers)
        else:
            request_headers = None

        # リクエスト実行
        response = self.session.request(
            method=method, url=url, headers=request_headers, timeout=timeout, **kwargs
        )

        return response

    def get(self, url: str, **kwargs) -> requests.Response:
        """GETリクエスト"""
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        """POSTリクエスト"""
        return self.request("POST", url, **kwargs)

    def close(self):
        """セッションのクローズ"""
        if hasattr(self, "session"):
            self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # Phase H.20.1.2: 外部API別最適化メソッド
    def get_api_optimized_headers(self, api_type: str) -> Dict[str, str]:
        """API別の最適化ヘッダーを取得"""
        base_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/html, */*",
            "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
        }

        # API別の特別設定
        if api_type == "yahoo_finance":
            base_headers.update(
                {
                    "Referer": "https://finance.yahoo.com/",
                    "Origin": "https://finance.yahoo.com",
                    "X-Requested-With": "XMLHttpRequest",
                }
            )
        elif api_type == "alternative_me":
            base_headers.update(
                {
                    "Referer": "https://alternative.me/",
                    "Accept": "application/json",
                }
            )
        elif api_type == "binance":
            base_headers.update(
                {
                    "Accept": "application/json",
                    "X-MBX-APIKEY": "",  # 必要に応じて設定
                }
            )
        elif api_type == "coingecko":
            base_headers.update(
                {
                    "Accept": "application/json",
                    "X-CG-Demo-API-Key": "",  # デモキー
                }
            )
        elif api_type == "cryptocompare":
            base_headers.update(
                {
                    "Accept": "application/json",
                    "authorization": "Apikey {demo_key}",  # デモキー
                }
            )
        elif api_type == "alpha_vantage":
            base_headers.update(
                {
                    "Accept": "application/json",
                    "User-Agent": "AlphaVantage-Client/1.0",
                }
            )
        elif api_type == "polygon":
            base_headers.update(
                {
                    "Accept": "application/json",
                    "Authorization": "Bearer DEMO_KEY",  # デモキー
                }
            )

        return base_headers

    def get_with_api_optimization(
        self, url: str, api_type: str, **kwargs
    ) -> requests.Response:
        """API最適化ヘッダーでGETリクエスト実行"""
        optimized_headers = self.get_api_optimized_headers(api_type)

        # 既存ヘッダーとマージ
        if "headers" in kwargs:
            optimized_headers.update(kwargs["headers"])
        kwargs["headers"] = optimized_headers

        # Phase H.20.1.2: API別タイムアウト調整
        if "timeout" not in kwargs:
            if api_type == "yahoo_finance":
                kwargs["timeout"] = (20, 60) if self.is_cloud_run else (10, 30)
            elif api_type == "alternative_me":
                kwargs["timeout"] = (15, 45) if self.is_cloud_run else (8, 25)
            elif api_type == "binance":
                kwargs["timeout"] = (10, 30) if self.is_cloud_run else (5, 15)
            else:
                kwargs["timeout"] = (15, 45) if self.is_cloud_run else (8, 25)

        return self.get(url, **kwargs)


# Yahoo Finance用の特殊最適化
class YahooFinanceHTTPClient(OptimizedHTTPClient):
    """Yahoo Finance API用に最適化されたHTTPクライアント"""

    def __init__(self):
        super().__init__("yahoo_finance")

        # Phase H.20.1.2: Yahoo Finance強化ヘッダー
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json, text/html, */*",
                "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Origin": "https://finance.yahoo.com",
                "Referer": "https://finance.yahoo.com/",
                "X-Requested-With": "XMLHttpRequest",
                "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"macOS"',
            }
        )

        # Yahoo Finance用のクッキー設定
        if self.is_cloud_run:
            # Cloud Run環境では追加のクッキー設定
            self.session.cookies.set("B", "abc123", domain=".yahoo.com")


# Alternative.me用の特殊最適化
class AlternativeMeHTTPClient(OptimizedHTTPClient):
    """Alternative.me API用に最適化されたHTTPクライアント"""

    def __init__(self):
        super().__init__("alternative_me")

        # Alternative.me特有の設定
        self.session.headers.update(
            {
                "Accept": "application/json",
                "X-Requested-With": "XMLHttpRequest",
            }
        )


# Binance用の特殊最適化
class BinanceHTTPClient(OptimizedHTTPClient):
    """Binance API用に最適化されたHTTPクライアント"""

    def __init__(self):
        super().__init__("binance")

        # Binance特有の設定
        self.session.headers.update(
            {
                "X-MBX-APIKEY": "",  # APIキーは使用時に設定
            }
        )

        # Binanceは頻繁なリクエストがあるため、接続プールを大きく
        if self.is_cloud_run:
            adapter = HTTPAdapter(
                pool_connections=30,
                pool_maxsize=30,
                max_retries=Retry(
                    total=3,
                    backoff_factor=0.5,
                    status_forcelist=[429, 500, 502, 503, 504],
                ),
            )
            self.session.mount("https://", adapter)


# グローバルクライアント取得関数
def get_optimized_client(api_type: str = "default") -> OptimizedHTTPClient:
    """API種別に応じた最適化されたHTTPクライアントを取得

    Args:
        api_type: API種別 ("yahoo", "alternative_me", "binance", "default")

    Returns:
        最適化されたHTTPクライアント
    """
    if api_type == "yahoo":
        return YahooFinanceHTTPClient.get_instance()
    elif api_type == "alternative_me":
        return AlternativeMeHTTPClient.get_instance()
    elif api_type == "binance":
        return BinanceHTTPClient.get_instance()
    else:
        return OptimizedHTTPClient.get_instance(api_type)


# 既存コードとの互換性のためのラッパー関数
def create_optimized_session(api_type: str = "default") -> requests.Session:
    """最適化されたセッションの作成（後方互換性用）

    Args:
        api_type: API種別

    Returns:
        最適化されたrequestsセッション
    """
    client = get_optimized_client(api_type)
    return client.session
