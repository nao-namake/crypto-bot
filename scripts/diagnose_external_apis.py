#!/usr/bin/env python3
"""
外部データAPI接続診断ツール
Phase H.17: 各APIへの直接接続テスト・エラー詳細収集

使用方法:
    python scripts/diagnose_external_apis.py

Cloud Run環境での実行:
    gcloud run jobs execute diagnose-apis --region=asia-northeast1
"""

import json
import logging
import os
import sys
import time
from datetime import datetime

import requests
import yfinance as yf

# プロジェクトルートをPYTHONPATHに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ExternalAPIHealthChecker:
    """外部API接続診断クラス"""

    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "environment": self._detect_environment(),
            "api_tests": {},
            "summary": {},
        }

    def _detect_environment(self):
        """実行環境の検出"""
        env_info = {
            "is_cloud_run": os.getenv("K_SERVICE") is not None,
            "is_docker": os.path.exists("/.dockerenv"),
            "python_version": sys.version,
            "platform": sys.platform,
        }
        logger.info(f"🔍 実行環境: {json.dumps(env_info, indent=2)}")
        return env_info

    def test_vix_api(self):
        """VIX (Yahoo Finance) API接続テスト"""
        logger.info("\n🔧 === VIX (Yahoo Finance) API テスト開始 ===")
        result = {
            "api_name": "Yahoo Finance VIX",
            "symbol": "^VIX",
            "status": "FAILED",
            "error": None,
            "data_sample": None,
            "latency_ms": None,
            "details": {},
        }

        start_time = time.time()

        try:
            # yfinanceバージョン確認
            logger.info(f"📦 yfinance version: {yf.__version__}")

            # VIXデータ取得テスト
            ticker = yf.Ticker("^VIX")

            # 複数の期間でテスト
            test_periods = [("1d", "1日"), ("5d", "5日"), ("1mo", "1ヶ月")]

            for period, desc in test_periods:
                logger.info(f"📊 {desc}データ取得テスト...")
                try:
                    hist = ticker.history(period=period)
                    if not hist.empty:
                        logger.info(f"✅ {desc}データ取得成功: {len(hist)}件")
                        result["details"][f"period_{period}"] = {
                            "success": True,
                            "records": len(hist),
                            "latest_value": float(hist["Close"].iloc[-1]),
                        }

                        if period == "5d":
                            result["data_sample"] = {
                                "latest_close": float(hist["Close"].iloc[-1]),
                                "date": str(hist.index[-1]),
                                "5d_avg": float(hist["Close"].mean()),
                            }
                    else:
                        logger.warning(f"⚠️ {desc}データが空です")
                        result["details"][f"period_{period}"] = {
                            "success": False,
                            "error": "Empty data",
                        }
                except Exception as e:
                    logger.error(f"❌ {desc}データ取得失敗: {e}")
                    result["details"][f"period_{period}"] = {
                        "success": False,
                        "error": str(e),
                    }

            # info取得テスト
            try:
                info = ticker.info
                if info:
                    logger.info("✅ Ticker info取得成功")
                    result["details"]["info_available"] = True
                else:
                    logger.warning("⚠️ Ticker infoが空です")
                    result["details"]["info_available"] = False
            except Exception as e:
                logger.error(f"❌ Ticker info取得失敗: {e}")
                result["details"]["info_available"] = False
                result["details"]["info_error"] = str(e)

            # 成功判定
            successful_periods = sum(
                1
                for k, v in result["details"].items()
                if k.startswith("period_") and v.get("success", False)
            )

            if successful_periods > 0:
                result["status"] = "SUCCESS"
                logger.info(f"✅ VIX API接続成功 ({successful_periods}/3 期間)")
            else:
                result["status"] = "FAILED"
                logger.error("❌ VIX API接続失敗: 全期間でデータ取得失敗")

        except Exception as e:
            logger.error(f"❌ VIX APIテスト失敗: {e}")
            result["error"] = str(e)
            result["details"]["exception"] = {
                "type": type(e).__name__,
                "message": str(e),
            }

        result["latency_ms"] = int((time.time() - start_time) * 1000)
        self.results["api_tests"]["vix"] = result

    def test_fear_greed_api(self):
        """Fear & Greed Index API接続テスト"""
        logger.info("\n🔧 === Fear & Greed Index API テスト開始 ===")
        result = {
            "api_name": "Alternative.me Fear & Greed",
            "endpoint": "https://api.alternative.me/fng/",
            "status": "FAILED",
            "error": None,
            "data_sample": None,
            "latency_ms": None,
            "details": {},
        }

        start_time = time.time()

        try:
            # APIエンドポイント
            base_url = "https://api.alternative.me/fng/"

            # ヘッダー設定（User-Agent追加）
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " "AppleWebKit/537.36"
                )
            }

            # 複数のテストケース
            test_cases = [
                ("最新データ", {"limit": 1}),
                ("7日間データ", {"limit": 7}),
                ("30日間データ", {"limit": 30}),
            ]

            for desc, params in test_cases:
                logger.info(f"📊 {desc}取得テスト...")
                try:
                    response = requests.get(
                        base_url, params=params, headers=headers, timeout=30
                    )

                    logger.info(f"📡 レスポンスステータス: {response.status_code}")

                    if response.status_code == 200:
                        data = response.json()
                        if "data" in data and data["data"]:
                            logger.info(f"✅ {desc}取得成功: {len(data['data'])}件")
                            result["details"][desc] = {
                                "success": True,
                                "records": len(data["data"]),
                                "latest_value": data["data"][0]["value"],
                                "latest_classification": data["data"][0][
                                    "value_classification"
                                ],
                            }

                            if desc == "最新データ":
                                result["data_sample"] = {
                                    "value": int(data["data"][0]["value"]),
                                    "classification": data["data"][0][
                                        "value_classification"
                                    ],
                                    "timestamp": data["data"][0]["timestamp"],
                                }
                        else:
                            logger.warning(f"⚠️ {desc}のレスポンスにデータがありません")
                            result["details"][desc] = {
                                "success": False,
                                "error": "No data in response",
                            }
                    else:
                        logger.error(f"❌ {desc}取得失敗: HTTP {response.status_code}")
                        result["details"][desc] = {
                            "success": False,
                            "error": f"HTTP {response.status_code}",
                            "response_text": response.text[:200],
                        }

                except requests.exceptions.Timeout:
                    logger.error(f"❌ {desc}取得タイムアウト")
                    result["details"][desc] = {"success": False, "error": "Timeout"}
                except Exception as e:
                    logger.error(f"❌ {desc}取得失敗: {e}")
                    result["details"][desc] = {"success": False, "error": str(e)}

            # 成功判定
            successful_tests = sum(
                1 for v in result["details"].values() if v.get("success", False)
            )

            if successful_tests > 0:
                result["status"] = "SUCCESS"
                logger.info(
                    f"✅ Fear & Greed API接続成功 ({successful_tests}/3 テスト)"
                )
            else:
                result["status"] = "FAILED"
                logger.error("❌ Fear & Greed API接続失敗: 全テスト失敗")

        except Exception as e:
            logger.error(f"❌ Fear & Greed APIテスト失敗: {e}")
            result["error"] = str(e)

        result["latency_ms"] = int((time.time() - start_time) * 1000)
        self.results["api_tests"]["fear_greed"] = result

    def test_macro_api(self):
        """Macro Data (DXY, Treasury) API接続テスト"""
        logger.info("\n🔧 === Macro Data API テスト開始 ===")
        result = {
            "api_name": "Yahoo Finance Macro Data",
            "symbols": ["DX-Y.NYB", "^TNX", "^TYX"],
            "status": "FAILED",
            "error": None,
            "data_sample": None,
            "latency_ms": None,
            "details": {},
        }

        start_time = time.time()

        try:
            # テストシンボル
            test_symbols = {
                "DX-Y.NYB": "ドル指数",
                "^TNX": "10年米国債利回り",
                "^TYX": "30年米国債利回り",
            }

            for symbol, desc in test_symbols.items():
                logger.info(f"📊 {desc} ({symbol}) データ取得テスト...")
                try:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period="5d")

                    if not hist.empty:
                        logger.info(f"✅ {desc}データ取得成功: {len(hist)}件")
                        result["details"][symbol] = {
                            "success": True,
                            "description": desc,
                            "records": len(hist),
                            "latest_value": float(hist["Close"].iloc[-1]),
                        }
                    else:
                        logger.warning(f"⚠️ {desc}データが空です")
                        result["details"][symbol] = {
                            "success": False,
                            "description": desc,
                            "error": "Empty data",
                        }
                except Exception as e:
                    logger.error(f"❌ {desc}データ取得失敗: {e}")
                    result["details"][symbol] = {
                        "success": False,
                        "description": desc,
                        "error": str(e),
                    }

            # データサンプル作成
            successful_symbols = [
                k for k, v in result["details"].items() if v.get("success", False)
            ]

            if successful_symbols:
                result["data_sample"] = {
                    sym: result["details"][sym]["latest_value"]
                    for sym in successful_symbols
                }
                result["status"] = "SUCCESS"
                logger.info(
                    f"✅ Macro API接続成功 ({len(successful_symbols)}/3 シンボル)"
                )
            else:
                result["status"] = "FAILED"
                logger.error("❌ Macro API接続失敗: 全シンボル取得失敗")

        except Exception as e:
            logger.error(f"❌ Macro APIテスト失敗: {e}")
            result["error"] = str(e)

        result["latency_ms"] = int((time.time() - start_time) * 1000)
        self.results["api_tests"]["macro"] = result

    def generate_summary(self):
        """診断結果のサマリー生成"""
        api_tests = self.results["api_tests"]

        total_apis = len(api_tests)
        successful_apis = sum(
            1 for test in api_tests.values() if test["status"] == "SUCCESS"
        )

        self.results["summary"] = {
            "total_apis_tested": total_apis,
            "successful_apis": successful_apis,
            "failed_apis": total_apis - successful_apis,
            "success_rate": (
                f"{(successful_apis/total_apis)*100:.1f}%" if total_apis > 0 else "0%"
            ),
            "api_status": {name: test["status"] for name, test in api_tests.items()},
        }

    def print_results(self):
        """診断結果の表示"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 外部API接続診断結果")
        logger.info("=" * 60)

        # サマリー表示
        summary = self.results["summary"]
        logger.info("\n📈 総合結果:")
        logger.info(f"  - テストしたAPI数: {summary['total_apis_tested']}")
        logger.info(f"  - 成功: {summary['successful_apis']}")
        logger.info(f"  - 失敗: {summary['failed_apis']}")
        logger.info(f"  - 成功率: {summary['success_rate']}")

        # 各APIの詳細結果
        logger.info("\n📋 API別結果:")
        for api_name, test_result in self.results["api_tests"].items():
            status_icon = "✅" if test_result["status"] == "SUCCESS" else "❌"
            logger.info(f"\n{status_icon} {test_result['api_name']}:")
            logger.info(f"  - ステータス: {test_result['status']}")
            logger.info(f"  - レイテンシ: {test_result['latency_ms']}ms")

            if test_result["status"] == "SUCCESS" and test_result["data_sample"]:
                logger.info(
                    f"  - データサンプル: {json.dumps(test_result['data_sample'], indent=4)}"
                )
            elif test_result["error"]:
                logger.info(f"  - エラー: {test_result['error']}")

        # 推奨事項
        logger.info("\n💡 推奨事項:")
        if summary["failed_apis"] > 0:
            logger.info("  ⚠️ 失敗したAPIがあります。以下を確認してください:")
            logger.info("  1. ネットワーク接続・ファイアウォール設定")
            logger.info("  2. Cloud Run環境での外部API接続設定")
            logger.info("  3. APIエンドポイントの変更有無")
            logger.info("  4. レート制限・認証要件")
        else:
            logger.info("  ✅ 全てのAPIが正常に動作しています")

        # 結果をJSONファイルに保存
        output_file = f"api_diagnosis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        logger.info(f"\n📁 詳細結果を保存しました: {output_file}")


def main():
    """メイン実行関数"""
    logger.info("🚀 外部API接続診断を開始します...")

    checker = ExternalAPIHealthChecker()

    # 各APIのテスト実行
    checker.test_vix_api()
    checker.test_fear_greed_api()
    checker.test_macro_api()

    # サマリー生成と結果表示
    checker.generate_summary()
    checker.print_results()

    # 終了コード決定
    if checker.results["summary"]["failed_apis"] > 0:
        logger.warning("\n⚠️ 一部のAPIで問題が検出されました")
        sys.exit(1)
    else:
        logger.info("\n✅ 全てのAPIが正常に動作しています")
        sys.exit(0)


if __name__ == "__main__":
    main()
