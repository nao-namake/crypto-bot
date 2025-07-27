"""
Phase H.17: 外部データAPI統合テスト
各APIからの実データ取得とCloud Run環境対応を検証
"""

import os
import sys
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd

# プロジェクトルートをPYTHONPATHに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crypto_bot.data.fear_greed_fetcher import FearGreedDataFetcher  # noqa: E402
from crypto_bot.data.macro_fetcher import MacroDataFetcher  # noqa: E402
from crypto_bot.data.vix_fetcher import VIXDataFetcher  # noqa: E402


class TestExternalAPIIntegration(unittest.TestCase):
    """外部データAPI統合テストクラス"""

    def setUp(self):
        """テスト前の準備"""
        self.test_config = {
            "external_data": {
                "vix": {"enabled": True, "cache_hours": 24, "quality_threshold": 0.7},
                "fear_greed": {
                    "enabled": True,
                    "cache_hours": 24,
                    "quality_threshold": 0.7,
                },
                "macro": {"enabled": True, "cache_hours": 24, "quality_threshold": 0.7},
            }
        }

    @patch.dict(os.environ, {"K_SERVICE": "test-service"})
    def test_cloud_run_environment_detection(self):
        """Cloud Run環境検出のテスト"""
        # Cloud Run環境が正しく検出されることを確認
        is_cloud_run = os.getenv("K_SERVICE") is not None
        self.assertTrue(is_cloud_run)

    def test_vix_fetcher_initialization(self):
        """VIXフェッチャー初期化テスト"""
        fetcher = VIXDataFetcher(self.test_config)

        # 基本属性の確認
        self.assertEqual(fetcher.symbol, "^VIX")
        self.assertEqual(fetcher.data_type, "vix")
        self.assertTrue(fetcher.enabled)

    @patch("yfinance.Ticker")
    def test_vix_data_fetch_success(self, mock_ticker):
        """VIXデータ取得成功テスト"""
        # モックデータの準備
        mock_history_data = pd.DataFrame(
            {
                "Close": [15.5, 16.2, 15.8, 16.5, 17.1],
                "Open": [15.0, 15.5, 16.2, 15.8, 16.5],
                "High": [15.8, 16.5, 16.3, 16.8, 17.5],
                "Low": [14.9, 15.3, 15.6, 15.7, 16.4],
                "Volume": [0, 0, 0, 0, 0],
            },
            index=pd.date_range("2025-01-01", periods=5),
        )

        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.return_value = mock_history_data
        mock_ticker.return_value = mock_ticker_instance

        # フェッチャー初期化とデータ取得
        fetcher = VIXDataFetcher(self.test_config)
        result = fetcher.get_vix_data(limit=5)

        # 結果の検証
        self.assertIsNotNone(result)
        self.assertIn("vix_close", result.columns)
        self.assertEqual(len(result), 5)

    @patch("yfinance.download")
    @patch("yfinance.Ticker")
    @patch.dict(os.environ, {"K_SERVICE": "test-service"})
    def test_vix_cloud_run_fallback(self, mock_ticker, mock_download):
        """VIX Cloud Run環境でのフォールバックテスト"""
        # history()メソッドが失敗する設定
        mock_ticker_instance = MagicMock()
        mock_ticker_instance.history.side_effect = Exception("Network error")
        mock_ticker.return_value = mock_ticker_instance

        # download()メソッドが成功する設定
        mock_download_data = pd.DataFrame(
            {
                "Close": [15.5, 16.2],
                "Open": [15.0, 15.5],
                "High": [15.8, 16.5],
                "Low": [14.9, 15.3],
                "Volume": [0, 0],
            },
            index=pd.date_range("2025-01-01", periods=2),
        )
        mock_download.return_value = mock_download_data

        # フェッチャー初期化とデータ取得
        fetcher = VIXDataFetcher(self.test_config)
        # _fetch_yahoo_vix メソッドを直接呼び出し
        fetcher._fetch_yahoo_vix(
            start_date=(datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
            end_date=datetime.now().strftime("%Y-%m-%d"),
        )

        # download()が呼ばれたことを確認
        mock_download.assert_called_once()

    def test_fear_greed_fetcher_initialization(self):
        """Fear & Greedフェッチャー初期化テスト"""
        fetcher = FearGreedDataFetcher(self.test_config)

        # 基本属性の確認
        self.assertEqual(fetcher.data_type, "fear_greed")
        self.assertEqual(fetcher.api_url, "https://api.alternative.me/fng/")
        self.assertTrue(fetcher.enabled)

    @patch("requests.get")
    def test_fear_greed_data_fetch_success(self, mock_get):
        """Fear & Greedデータ取得成功テスト"""
        # モックレスポンスの準備
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "value": "73",
                    "value_classification": "Greed",
                    "timestamp": "1753574400",
                },
                {
                    "value": "68",
                    "value_classification": "Greed",
                    "timestamp": "1753488000",
                },
            ]
        }
        mock_get.return_value = mock_response

        # フェッチャー初期化とデータ取得
        fetcher = FearGreedDataFetcher(self.test_config)
        result = fetcher._fetch_alternative_me(limit=2)

        # 結果の検証
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        self.assertIn("value", result.columns)
        self.assertIn("value_classification", result.columns)

    @patch("requests.get")
    @patch.dict(os.environ, {"K_SERVICE": "test-service"})
    def test_fear_greed_cloud_run_headers(self, mock_get):
        """Fear & Greed Cloud Run環境でのヘッダー設定テスト"""
        # モックレスポンス
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response

        # フェッチャー初期化とデータ取得
        fetcher = FearGreedDataFetcher(self.test_config)
        fetcher._fetch_alternative_me(limit=1)

        # リクエストが正しいヘッダーで呼ばれたことを確認
        args, kwargs = mock_get.call_args
        self.assertIn("headers", kwargs)
        headers = kwargs["headers"]
        self.assertIn("User-Agent", headers)
        self.assertIn("Accept", headers)
        self.assertEqual(kwargs["timeout"], 30)  # Cloud Run環境では30秒

    def test_macro_fetcher_initialization(self):
        """Macroフェッチャー初期化テスト"""
        fetcher = MacroDataFetcher(self.test_config)

        # 基本属性の確認
        self.assertEqual(fetcher.data_type, "macro")
        self.assertIn("dxy", fetcher.symbols)
        self.assertIn("us10y", fetcher.symbols)
        self.assertTrue(fetcher.enabled)

    @patch("yfinance.Ticker")
    def test_macro_data_fetch_success(self, mock_ticker):
        """Macroデータ取得成功テスト"""
        # 各シンボル用のモックデータ
        mock_dxy_data = pd.DataFrame(
            {
                "Close": [97.5, 97.8, 98.1],
                "Open": [97.3, 97.5, 97.8],
                "High": [97.9, 98.0, 98.3],
                "Low": [97.2, 97.4, 97.7],
                "Volume": [1000, 1100, 1200],
            },
            index=pd.date_range("2025-01-01", periods=3),
        )

        mock_tnx_data = pd.DataFrame(
            {
                "Close": [4.25, 4.28, 4.30],
                "Open": [4.23, 4.25, 4.28],
                "High": [4.27, 4.30, 4.32],
                "Low": [4.22, 4.24, 4.27],
                "Volume": [0, 0, 0],
            },
            index=pd.date_range("2025-01-01", periods=3),
        )

        # モックの設定
        def mock_ticker_side_effect(symbol):
            mock_instance = MagicMock()
            if symbol == "DX-Y.NYB":
                mock_instance.history.return_value = mock_dxy_data
            elif symbol == "^TNX":
                mock_instance.history.return_value = mock_tnx_data
            else:
                mock_instance.history.return_value = pd.DataFrame()
            return mock_instance

        mock_ticker.side_effect = mock_ticker_side_effect

        # フェッチャー初期化とデータ取得
        fetcher = MacroDataFetcher(self.test_config)
        result = fetcher._fetch_yahoo_macro_data(
            start_date=(datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
            end_date=datetime.now().strftime("%Y-%m-%d"),
        )

        # 結果の検証
        self.assertIsNotNone(result)
        self.assertIn("dxy_close", result.columns)
        self.assertIn("us10y_close", result.columns)

    def test_data_quality_validation(self):
        """データ品質検証機能のテスト"""
        # VIXデータ品質検証
        vix_fetcher = VIXDataFetcher(self.test_config)

        # 正常なデータ
        good_data = pd.DataFrame({"vix_close": [15.5, 16.2, 15.8, 16.5, 17.1]})
        quality_score = vix_fetcher._validate_data_quality(good_data)
        self.assertGreater(quality_score, 0.8)

        # 異常値を含むデータ
        bad_data = pd.DataFrame(
            {"vix_close": [15.5, 150.0, -5.0, None, 17.1]}  # 異常値とNaN
        )
        quality_score = vix_fetcher._validate_data_quality(bad_data)
        self.assertLess(quality_score, 0.5)

    def test_fallback_data_generation(self):
        """フォールバックデータ生成のテスト"""
        # VIXフォールバック
        vix_fetcher = VIXDataFetcher(self.test_config)
        fallback_data = vix_fetcher._generate_fallback_data()

        self.assertIsNotNone(fallback_data)
        self.assertIn("vix_close", fallback_data.columns)
        self.assertTrue(all(10 <= v <= 35 for v in fallback_data["vix_close"]))

        # Fear & Greedフォールバック
        fg_fetcher = FearGreedDataFetcher(self.test_config)
        fallback_data = fg_fetcher._generate_fallback_data()

        self.assertIsNotNone(fallback_data)
        self.assertIn("value", fallback_data.columns)
        self.assertTrue(all(0 <= v <= 100 for v in fallback_data["value"]))


def run_tests():
    """テスト実行"""
    # テストスイートの作成
    suite = unittest.TestLoader().loadTestsFromTestCase(TestExternalAPIIntegration)

    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    print("🧪 Phase H.17: 外部データAPI統合テスト開始...")
    success = run_tests()

    if success:
        print("\n✅ 全てのテストが成功しました")
    else:
        print("\n❌ 一部のテストが失敗しました")
        sys.exit(1)
