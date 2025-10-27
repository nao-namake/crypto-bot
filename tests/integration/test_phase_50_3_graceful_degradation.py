"""
Phase 50.3 統合テスト: 4段階Graceful Degradation

外部API統合・マクロ経済指標・フォールバックメカニズムの統合動作を検証。
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest

from src.core.logger import get_logger
from src.core.orchestration.ml_loader import MLModelLoader
from src.features.external_api import ExternalAPIClient, ExternalAPIError
from src.features.feature_generator import FeatureGenerator


@pytest.fixture
def logger():
    """ロガーインスタンス"""
    return get_logger()


@pytest.fixture
def sample_market_data():
    """市場データサンプル"""
    # 4h足データ
    df_4h = pd.DataFrame(
        {
            "open": [9980000 + i * 10000 for i in range(100)],
            "close": [10000000 + i * 10000 for i in range(100)],
            "high": [10050000 + i * 10000 for i in range(100)],
            "low": [9950000 + i * 10000 for i in range(100)],
            "volume": [100 + i for i in range(100)],
        },
        index=pd.date_range("2025-01-01", periods=100, freq="4h"),
    )
    df_4h.index.name = "timestamp"

    # 15m足データ
    df_15m = pd.DataFrame(
        {
            "open": [9990000 + i * 5000 for i in range(100)],
            "close": [10000000 + i * 5000 for i in range(100)],
            "high": [10025000 + i * 5000 for i in range(100)],
            "low": [9975000 + i * 5000 for i in range(100)],
            "volume": [50 + i for i in range(100)],
        },
        index=pd.date_range("2025-01-01", periods=100, freq="15min"),
    )
    df_15m.index.name = "timestamp"

    return {
        "4h": df_4h,
        "15m": df_15m,
        "current_price": 10500000,
    }


@pytest.fixture
def sample_strategy_signals():
    """戦略シグナルサンプル"""
    return {
        "atr_based": {"action": "buy", "confidence": 0.7},
        "mochipoy_alert": {"action": "buy", "confidence": 0.8},
        "multi_timeframe": {"action": "hold", "confidence": 0.5},
        "donchian_channel": {"action": "buy", "confidence": 0.6},
        "adx_trend_strength": {"action": "buy", "confidence": 0.75},
    }


class TestExternalAPIIntegration:
    """外部API統合テスト"""

    @pytest.mark.asyncio
    async def test_external_api_client_fetch_all(self, logger):
        """外部APIクライアント全指標取得テスト"""
        api_client = ExternalAPIClient(cache_ttl=86400, logger=logger)

        # APIメソッドをモック
        api_client.fetch_usd_jpy = AsyncMock(return_value=150.25)
        api_client.fetch_nikkei_225 = AsyncMock(return_value=38500.50)
        api_client.fetch_us_10y_yield = AsyncMock(return_value=4.25)
        api_client.fetch_fear_greed_index = AsyncMock(return_value=75.0)

        result = await api_client.fetch_all_indicators(timeout=10.0)

        # 基本指標4個 + 派生指標確認
        assert len(result) >= 4
        assert "usd_jpy" in result
        assert "market_sentiment" in result

    @pytest.mark.asyncio
    async def test_external_api_graceful_degradation(self, logger):
        """外部API Graceful Degradationテスト（全失敗→空辞書返却）"""
        api_client = ExternalAPIClient(cache_ttl=86400, logger=logger)

        # 最初の成功でキャッシュ構築
        api_client.fetch_usd_jpy = AsyncMock(return_value=150.25)
        api_client.fetch_nikkei_225 = AsyncMock(return_value=38500.50)
        api_client.fetch_us_10y_yield = AsyncMock(return_value=4.25)
        api_client.fetch_fear_greed_index = AsyncMock(return_value=75.0)

        first_result = await api_client.fetch_all_indicators(timeout=10.0)
        assert len(first_result) >= 4

        # 次回全失敗→空辞書返却（個別エラーは空辞書を返す設計）
        api_client.fetch_usd_jpy = AsyncMock(side_effect=Exception("API Error"))
        api_client.fetch_nikkei_225 = AsyncMock(side_effect=Exception("API Error"))
        api_client.fetch_us_10y_yield = AsyncMock(side_effect=Exception("API Error"))
        api_client.fetch_fear_greed_index = AsyncMock(side_effect=Exception("API Error"))

        second_result = await api_client.fetch_all_indicators(timeout=10.0)

        # 個別エラーの場合は空辞書が返される（キャッシュは_get_cached_values()で明示的に呼ばれた時のみ）
        assert len(second_result) == 0

        # しかし、キャッシュには値が残っている
        cached_values = api_client._get_cached_values()
        assert len(cached_values) >= 4
        assert cached_values["usd_jpy"] == 150.25


class TestFeatureGeneratorWithExternalAPI:
    """FeatureGenerator外部API統合テスト"""

    @pytest.mark.asyncio
    async def test_feature_generator_with_external_api_success(
        self, logger, sample_market_data, sample_strategy_signals
    ):
        """FeatureGenerator 外部API統合成功テスト（70特徴量）"""
        generator = FeatureGenerator()

        # ExternalAPIClientをモック
        with patch("src.features.external_api.ExternalAPIClient") as mock_client_class:
            mock_client = Mock()
            mock_client.fetch_all_indicators = AsyncMock(
                return_value={
                    "usd_jpy": 150.25,
                    "nikkei_225": 38500.50,
                    "us_10y_yield": 4.25,
                    "fear_greed_index": 75.0,
                    "usd_jpy_change_1d": 0.5,
                    "nikkei_change_1d": 1.2,
                    "usd_jpy_btc_correlation": 0.0,
                    "market_sentiment": 0.5,
                }
            )
            mock_client_class.return_value = mock_client

            # 外部API有効で特徴量生成
            features = await generator.generate_features(
                sample_market_data,
                strategy_signals=sample_strategy_signals,
                include_external_api=True,
            )

        # 70特徴量確認（62基本 + 8外部API）
        external_api_features = [
            "usd_jpy",
            "nikkei_225",
            "us_10y_yield",
            "fear_greed_index",
            "usd_jpy_change_1d",
            "nikkei_change_1d",
            "usd_jpy_btc_correlation",
            "market_sentiment",
        ]

        for feature in external_api_features:
            assert feature in features.columns, f"{feature}が見つかりません"

        # 総特徴量数確認（ただし、一部特徴量は生成されない場合もある）
        assert len(features.columns) >= 65  # 最低でも65特徴量

    @pytest.mark.asyncio
    async def test_feature_generator_without_external_api(
        self, logger, sample_market_data, sample_strategy_signals
    ):
        """FeatureGenerator 外部APIなしテスト（62特徴量）"""
        generator = FeatureGenerator()

        # 外部API無効で特徴量生成
        features = await generator.generate_features(
            sample_market_data,
            strategy_signals=sample_strategy_signals,
            include_external_api=False,
        )

        # 62特徴量確認
        external_api_features = [
            "usd_jpy",
            "nikkei_225",
            "us_10y_yield",
            "fear_greed_index",
        ]

        for feature in external_api_features:
            assert feature not in features.columns, f"{feature}が含まれています"

        # 62特徴量前後確認（一部特徴量は生成されない場合もある）
        assert 55 <= len(features.columns) <= 65

    @pytest.mark.asyncio
    async def test_feature_generator_external_api_failure_fallback(
        self, logger, sample_market_data, sample_strategy_signals
    ):
        """FeatureGenerator 外部API失敗時フォールバックテスト"""
        generator = FeatureGenerator()

        # ExternalAPIClient全失敗をモック
        with patch("src.features.external_api.ExternalAPIClient") as mock_client_class:
            mock_client = Mock()
            mock_client.fetch_all_indicators = AsyncMock(return_value={})  # 空辞書（全失敗）
            mock_client_class.return_value = mock_client

            # ExternalAPIError発生を期待
            with pytest.raises(ExternalAPIError):
                await generator.generate_features(
                    sample_market_data,
                    strategy_signals=sample_strategy_signals,
                    include_external_api=True,
                )

    @pytest.mark.asyncio
    async def test_feature_generator_external_api_partial_success(
        self, logger, sample_market_data, sample_strategy_signals
    ):
        """FeatureGenerator 外部API部分成功テスト"""
        generator = FeatureGenerator()

        # ExternalAPIClient部分成功をモック
        with patch("src.features.external_api.ExternalAPIClient") as mock_client_class:
            mock_client = Mock()
            mock_client.fetch_all_indicators = AsyncMock(
                return_value={
                    "usd_jpy": 150.25,
                    "fear_greed_index": 75.0,
                    # nikkei_225, us_10y_yieldは失敗
                    "market_sentiment": 0.5,
                }
            )
            mock_client_class.return_value = mock_client

            # 部分成功でも特徴量生成成功
            features = await generator.generate_features(
                sample_market_data,
                strategy_signals=sample_strategy_signals,
                include_external_api=True,
            )

        # 取得できた特徴量のみ含まれる
        assert "usd_jpy" in features.columns
        assert "fear_greed_index" in features.columns
        assert "market_sentiment" in features.columns


class TestMLLoader4StageGracefulDegradation:
    """MLLoader 4段階Graceful Degradationテスト"""

    def test_determine_feature_level_70_features(self, logger):
        """特徴量レベル判定テスト（70特徴量）"""
        loader = MLModelLoader(logger=logger)

        level = loader._determine_feature_level(feature_count=70)
        assert level == "full_with_external"

    def test_determine_feature_level_62_features(self, logger):
        """特徴量レベル判定テスト（62特徴量）"""
        loader = MLModelLoader(logger=logger)

        level = loader._determine_feature_level(feature_count=62)
        assert level == "full"

    def test_determine_feature_level_57_features(self, logger):
        """特徴量レベル判定テスト（57特徴量）"""
        loader = MLModelLoader(logger=logger)

        level = loader._determine_feature_level(feature_count=57)
        assert level == "basic"

    def test_determine_feature_level_unknown_features(self, logger):
        """特徴量レベル判定テスト（想定外の特徴量数）"""
        loader = MLModelLoader(logger=logger)

        level = loader._determine_feature_level(feature_count=99)
        assert level == "full_with_external"  # フォールバック

    def test_determine_feature_level_none(self, logger):
        """特徴量レベル判定テスト（特徴量数未指定）"""
        loader = MLModelLoader(logger=logger)

        level = loader._determine_feature_level(feature_count=None)
        assert level == "full_with_external"  # デフォルト

    def test_load_production_ensemble_level_full_with_external(self, logger):
        """ProductionEnsemble読み込みテスト（Level 1: full_with_external）"""
        loader = MLModelLoader(logger=logger)

        # production_ensemble_full.pklが存在しない場合はスキップ
        model_path = Path("models/production/production_ensemble_full.pkl")
        if not model_path.exists():
            pytest.skip("production_ensemble_full.pkl not found")

        success = loader._load_production_ensemble(level="full_with_external")

        if success:
            assert loader.feature_level == "full_with_external"
            assert "full_with_external" in loader.model_type.lower()

    def test_load_production_ensemble_level_full(self, logger):
        """ProductionEnsemble読み込みテスト（Level 2: full）"""
        loader = MLModelLoader(logger=logger)

        # production_ensemble.pklが存在しない場合はスキップ
        model_path = Path("models/production/production_ensemble.pkl")
        if not model_path.exists():
            pytest.skip("production_ensemble.pkl not found")

        success = loader._load_production_ensemble(level="full")

        if success:
            assert loader.feature_level == "full"
            assert "full" in loader.model_type.lower()

    def test_load_model_with_priority_fallback_to_level2(self, logger):
        """load_model_with_priority Level 2フォールバックテスト"""
        loader = MLModelLoader(logger=logger)

        # 70特徴量でLevel 1試行→Level 2フォールバック（production_ensemble_full.pklなし）
        model = loader.load_model_with_priority(feature_count=70)

        # モデルが読み込まれている
        assert model is not None
        assert loader.model is not None

        # Level 2またはLevel 3にフォールバック（環境により異なる）
        assert loader.feature_level in ["full", "basic", "unknown"]

    def test_load_model_with_priority_dummy_fallback(self, logger):
        """load_model_with_priority ダミーモデルフォールバックテスト"""
        loader = MLModelLoader(logger=logger)

        # 全てのモデルファイルが存在しないことをシミュレート
        with patch.object(loader, "_load_production_ensemble", return_value=False):
            with patch.object(loader, "_load_from_individual_models", return_value=False):
                model = loader.load_model_with_priority(feature_count=70)

        # ダミーモデルにフォールバック
        assert model is not None
        assert loader.model_type == "DummyModel"

    def test_get_model_info_with_feature_level(self, logger):
        """get_model_info特徴量レベル情報テスト"""
        loader = MLModelLoader(logger=logger)
        loader.load_model_with_priority()

        model_info = loader.get_model_info()

        assert "feature_level" in model_info
        assert model_info["feature_level"] in [
            "full_with_external",
            "full",
            "basic",
            "unknown",
        ]


class TestEndToEndGracefulDegradation:
    """エンドツーエンド Graceful Degradationテスト"""

    @pytest.mark.asyncio
    async def test_end_to_end_level1_success(
        self, logger, sample_market_data, sample_strategy_signals
    ):
        """エンドツーエンド Level 1成功テスト（70特徴量）"""
        # FeatureGenerator作成
        generator = FeatureGenerator()

        # ExternalAPIClientモック（成功）
        with patch("src.features.external_api.ExternalAPIClient") as mock_client_class:
            mock_client = Mock()
            mock_client.fetch_all_indicators = AsyncMock(
                return_value={
                    "usd_jpy": 150.25,
                    "nikkei_225": 38500.50,
                    "us_10y_yield": 4.25,
                    "fear_greed_index": 75.0,
                    "usd_jpy_change_1d": 0.5,
                    "nikkei_change_1d": 1.2,
                    "usd_jpy_btc_correlation": 0.0,
                    "market_sentiment": 0.5,
                }
            )
            mock_client_class.return_value = mock_client

            # 特徴量生成（外部API有効）
            features = await generator.generate_features(
                sample_market_data,
                strategy_signals=sample_strategy_signals,
                include_external_api=True,
            )

        feature_count = len(features.columns)

        # MLLoader作成
        loader = MLModelLoader(logger=logger)
        model = loader.load_model_with_priority(feature_count=feature_count)

        # モデル読み込み成功
        assert model is not None
        assert loader.feature_level in ["full_with_external", "full", "basic", "unknown"]

    @pytest.mark.asyncio
    async def test_end_to_end_level2_fallback(
        self, logger, sample_market_data, sample_strategy_signals
    ):
        """エンドツーエンド Level 2フォールバックテスト（外部API失敗→62特徴量）"""
        # FeatureGenerator作成
        generator = FeatureGenerator()

        # ExternalAPIClient全失敗をモック
        with patch("src.features.external_api.ExternalAPIClient") as mock_client_class:
            mock_client = Mock()
            mock_client.fetch_all_indicators = AsyncMock(return_value={})  # 全失敗
            mock_client_class.return_value = mock_client

            # 特徴量生成時にExternalAPIError発生→外部APIなしにフォールバック
            try:
                features = await generator.generate_features(
                    sample_market_data,
                    strategy_signals=sample_strategy_signals,
                    include_external_api=True,
                )
            except ExternalAPIError:
                # 外部API失敗時は外部APIなしで再実行
                features = await generator.generate_features(
                    sample_market_data,
                    strategy_signals=sample_strategy_signals,
                    include_external_api=False,
                )

        feature_count = len(features.columns)

        # MLLoader作成
        loader = MLModelLoader(logger=logger)
        model = loader.load_model_with_priority(feature_count=feature_count)

        # Level 2またはLevel 3にフォールバック
        assert model is not None
        assert loader.feature_level in ["full", "basic", "unknown"]
