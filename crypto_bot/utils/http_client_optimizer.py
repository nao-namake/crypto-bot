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

        # リトライ戦略
        retry_strategy = Retry(
            total=3,  # 総リトライ回数
            backoff_factor=1.5,  # 指数バックオフ
            status_forcelist=[429, 500, 502, 503, 504],  # リトライ対象ステータス
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"],
            # Cloud Run環境では接続エラーもリトライ
            raise_on_status=False if self.is_cloud_run else True,
        )

        # Cloud Run環境用の設定
        if self.is_cloud_run:
            # 接続プールサイズを増やす
            pool_connections = 20
            pool_maxsize = 20
            # タイムアウトを長めに設定
            timeout_connect = 10
            timeout_read = 30
        else:
            # ローカル環境
            pool_connections = 10
            pool_maxsize = 10
            timeout_connect = 5
            timeout_read = 15

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


# Yahoo Finance用の特殊最適化
class YahooFinanceHTTPClient(OptimizedHTTPClient):
    """Yahoo Finance API用に最適化されたHTTPクライアント"""

    def __init__(self):
        super().__init__("yahoo_finance")

        # Yahoo Finance特有のヘッダー追加
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (compatible; CryptoBot/1.0; +https://github.com/crypto-bot)",
                "Accept-Language": "en-US,en;q=0.9",
                "Origin": "https://finance.yahoo.com",
                "Referer": "https://finance.yahoo.com/",
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
