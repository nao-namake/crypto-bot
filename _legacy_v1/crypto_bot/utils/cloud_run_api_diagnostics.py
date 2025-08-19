"""
Cloud Run環境での外部API接続診断ツール
Phase H.19: 外部API接続問題の根本原因特定用

このツールは以下を診断します：
- DNS解決能力
- HTTPS接続能力
- 各外部APIへの疎通確認
- タイムアウト/レイテンシ測定
- エラーの詳細情報収集
"""

import logging
import os
import socket
import ssl
import time
from datetime import datetime
from typing import Any, Dict, List

import requests
import urllib3

logger = logging.getLogger(__name__)


class CloudRunAPIDiagnostics:
    """Cloud Run環境での外部API接続診断クラス"""

    def __init__(self):
        self.is_cloud_run = os.getenv("K_SERVICE") is not None
        self.results: List[Dict[str, Any]] = []

        # HTTPセッション設定（接続プール最適化）
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=10,
            max_retries=urllib3.Retry(
                total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504]
            ),
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # 診断対象のAPIエンドポイント
        self.api_endpoints = {
            "alternative_me": {
                "url": "https://api.alternative.me/fng/?limit=1",
                "description": "Fear&Greed Index API",
                "timeout": 30,
            },
            "yahoo_finance_vix": {
                "url": "https://query1.finance.yahoo.com/v8/finance/chart/^VIX",
                "description": "Yahoo Finance VIX",
                "timeout": 30,
            },
            "yahoo_finance_dxy": {
                "url": "https://query1.finance.yahoo.com/v8/finance/chart/DX-Y.NYB",
                "description": "Yahoo Finance DXY",
                "timeout": 30,
            },
            "binance_funding": {
                "url": "https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=1",
                "description": "Binance Funding Rate",
                "timeout": 30,
            },
            "binance_server_time": {
                "url": "https://api.binance.com/api/v3/time",
                "description": "Binance Server Time (Test)",
                "timeout": 10,
            },
        }

    def diagnose_all(self) -> Dict[str, Any]:
        """全診断を実行"""
        logger.info(
            f"🔍 Starting Cloud Run API diagnostics (Cloud Run: {self.is_cloud_run})"
        )

        start_time = time.time()

        # 基本的なネットワーク診断
        self._diagnose_basic_network()

        # DNS解決診断
        self._diagnose_dns_resolution()

        # SSL/TLS接続診断
        self._diagnose_ssl_connections()

        # 各APIエンドポイントの診断
        self._diagnose_api_endpoints()

        # HTTPクライアント設定の診断
        self._diagnose_http_client_config()

        # 環境変数の診断
        self._diagnose_environment()

        total_time = time.time() - start_time

        # 診断結果サマリー
        summary = self._generate_summary(total_time)

        return {
            "timestamp": datetime.now().isoformat(),
            "is_cloud_run": self.is_cloud_run,
            "total_diagnostic_time": total_time,
            "results": self.results,
            "summary": summary,
        }

    def _diagnose_basic_network(self):
        """基本的なネットワーク接続診断"""
        logger.info("📡 Diagnosing basic network connectivity...")

        # Google DNSへの接続テスト
        try:
            socket.setdefaulttimeout(5)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
            self.results.append(
                {
                    "test": "basic_network",
                    "target": "8.8.8.8:53 (Google DNS)",
                    "success": True,
                    "message": "Basic network connectivity OK",
                }
            )
        except Exception as e:
            self.results.append(
                {
                    "test": "basic_network",
                    "target": "8.8.8.8:53",
                    "success": False,
                    "error": str(e),
                    "message": "Basic network connectivity FAILED",
                }
            )

    def _diagnose_dns_resolution(self):
        """DNS解決能力の診断"""
        logger.info("🌐 Diagnosing DNS resolution...")

        test_domains = [
            "api.alternative.me",
            "query1.finance.yahoo.com",
            "api.binance.com",
            "fapi.binance.com",
        ]

        for domain in test_domains:
            try:
                start = time.time()
                ip_address = socket.gethostbyname(domain)
                resolution_time = time.time() - start

                self.results.append(
                    {
                        "test": "dns_resolution",
                        "domain": domain,
                        "ip_address": ip_address,
                        "resolution_time_ms": resolution_time * 1000,
                        "success": True,
                    }
                )
            except Exception as e:
                self.results.append(
                    {
                        "test": "dns_resolution",
                        "domain": domain,
                        "success": False,
                        "error": str(e),
                    }
                )

    def _diagnose_ssl_connections(self):
        """SSL/TLS接続の診断"""
        logger.info("🔐 Diagnosing SSL/TLS connections...")

        test_hosts = [
            ("api.alternative.me", 443),
            ("query1.finance.yahoo.com", 443),
            ("api.binance.com", 443),
        ]

        for host, port in test_hosts:
            try:
                start = time.time()
                context = ssl.create_default_context()
                with socket.create_connection((host, port), timeout=10) as sock:
                    with context.wrap_socket(sock, server_hostname=host) as ssock:
                        connection_time = time.time() - start

                        self.results.append(
                            {
                                "test": "ssl_connection",
                                "host": f"{host}:{port}",
                                "success": True,
                                "connection_time_ms": connection_time * 1000,
                                "ssl_version": ssock.version(),
                                "cipher": ssock.cipher(),
                            }
                        )
            except Exception as e:
                self.results.append(
                    {
                        "test": "ssl_connection",
                        "host": f"{host}:{port}",
                        "success": False,
                        "error": str(e),
                    }
                )

    def _diagnose_api_endpoints(self):
        """各APIエンドポイントへの実際の接続診断"""
        logger.info("🔗 Diagnosing API endpoint connections...")

        for name, config in self.api_endpoints.items():
            try:
                headers = {
                    "User-Agent": "CryptoBot/1.0 CloudRunDiagnostics",
                    "Accept": "application/json",
                }

                start = time.time()
                response = self.session.get(
                    config["url"],
                    headers=headers,
                    timeout=config["timeout"],
                    allow_redirects=True,
                )
                request_time = time.time() - start

                result = {
                    "test": "api_endpoint",
                    "name": name,
                    "url": config["url"],
                    "description": config["description"],
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "request_time_ms": request_time * 1000,
                    "response_size": len(response.content),
                    "headers": dict(response.headers),
                }

                # レスポンス内容の簡単な検証
                if response.status_code == 200:
                    try:
                        json_data = response.json()
                        result["has_valid_json"] = True
                        result["sample_data"] = str(json_data)[:200]  # 最初の200文字
                    except (ValueError, requests.exceptions.JSONDecodeError):
                        result["has_valid_json"] = False

                self.results.append(result)

            except requests.exceptions.Timeout as e:
                self.results.append(
                    {
                        "test": "api_endpoint",
                        "name": name,
                        "url": config["url"],
                        "success": False,
                        "error": "Timeout",
                        "error_detail": str(e),
                    }
                )
            except requests.exceptions.ConnectionError as e:
                self.results.append(
                    {
                        "test": "api_endpoint",
                        "name": name,
                        "url": config["url"],
                        "success": False,
                        "error": "ConnectionError",
                        "error_detail": str(e),
                    }
                )
            except Exception as e:
                self.results.append(
                    {
                        "test": "api_endpoint",
                        "name": name,
                        "url": config["url"],
                        "success": False,
                        "error": type(e).__name__,
                        "error_detail": str(e),
                    }
                )

    def _diagnose_http_client_config(self):
        """HTTPクライアント設定の診断"""
        logger.info("⚙️ Diagnosing HTTP client configuration...")

        # urllib3の設定確認
        self.results.append(
            {
                "test": "http_client_config",
                "urllib3_version": urllib3.__version__,
                "requests_version": requests.__version__,
                "session_adapters": str(self.session.adapters),
                "verify_ssl": self.session.verify,
            }
        )

        # プロキシ設定の確認
        proxy_env_vars = {
            "http_proxy": os.getenv("http_proxy", "not set"),
            "https_proxy": os.getenv("https_proxy", "not set"),
            "HTTP_PROXY": os.getenv("HTTP_PROXY", "not set"),
            "HTTPS_PROXY": os.getenv("HTTPS_PROXY", "not set"),
            "no_proxy": os.getenv("no_proxy", "not set"),
            "NO_PROXY": os.getenv("NO_PROXY", "not set"),
        }

        self.results.append(
            {
                "test": "proxy_config",
                "proxy_settings": proxy_env_vars,
            }
        )

    def _diagnose_environment(self):
        """環境変数の診断"""
        logger.info("🌍 Diagnosing environment variables...")

        important_env_vars = {
            "K_SERVICE": os.getenv("K_SERVICE", "not set"),
            "K_REVISION": os.getenv("K_REVISION", "not set"),
            "PORT": os.getenv("PORT", "not set"),
            "GOOGLE_CLOUD_PROJECT": os.getenv("GOOGLE_CLOUD_PROJECT", "not set"),
            "TZ": os.getenv("TZ", "not set"),
            "LANG": os.getenv("LANG", "not set"),
        }

        self.results.append(
            {
                "test": "environment",
                "cloud_run_env": important_env_vars,
                "python_version": os.sys.version,
            }
        )

    def _generate_summary(self, total_time: float) -> Dict[str, Any]:
        """診断結果のサマリー生成"""
        summary = {
            "total_tests": len(self.results),
            "successful_tests": sum(1 for r in self.results if r.get("success", True)),
            "failed_tests": sum(1 for r in self.results if not r.get("success", True)),
            "total_time_seconds": total_time,
        }

        # API別の成功/失敗
        api_results = {}
        for result in self.results:
            if result.get("test") == "api_endpoint":
                name = result.get("name", "unknown")
                api_results[name] = {
                    "success": result.get("success", False),
                    "error": result.get("error", None),
                    "status_code": result.get("status_code", None),
                    "time_ms": result.get("request_time_ms", None),
                }

        summary["api_results"] = api_results

        # 推奨事項の生成
        recommendations = []

        # DNS解決の問題
        dns_failures = [
            r
            for r in self.results
            if r.get("test") == "dns_resolution" and not r.get("success")
        ]
        if dns_failures:
            recommendations.append(
                "DNS解決に問題があります。Cloud RunのVPCコネクタ設定を確認してください。"
            )

        # SSL接続の問題
        ssl_failures = [
            r
            for r in self.results
            if r.get("test") == "ssl_connection" and not r.get("success")
        ]
        if ssl_failures:
            recommendations.append(
                "SSL/TLS接続に問題があります。ファイアウォール規則を確認してください。"
            )

        # API接続の問題
        api_failures = [
            r
            for r in self.results
            if r.get("test") == "api_endpoint" and not r.get("success")
        ]
        if api_failures:
            failed_apis = [r.get("name") for r in api_failures]
            recommendations.append(f"以下のAPIへの接続に失敗: {', '.join(failed_apis)}")

            # タイムアウトの問題
            timeout_failures = [r for r in api_failures if r.get("error") == "Timeout"]
            if timeout_failures:
                recommendations.append(
                    "タイムアウトエラーが発生しています。Cloud Runのタイムアウト設定を延長してください。"
                )

        summary["recommendations"] = recommendations

        return summary


def run_diagnostics() -> Dict[str, Any]:
    """診断を実行してJSON形式で結果を返す"""
    diagnostics = CloudRunAPIDiagnostics()
    return diagnostics.diagnose_all()


if __name__ == "__main__":
    # コマンドラインから実行された場合
    import json

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    results = run_diagnostics()
    print(json.dumps(results, indent=2, ensure_ascii=False))
