"""
Phase 51.3統合テスト: 市場レジーム連動動的戦略選択

MarketRegimeClassifier + DynamicStrategySelector の統合動作を検証。
"""

import pandas as pd
import pytest

from src.core.services.dynamic_strategy_selector import DynamicStrategySelector
from src.core.services.market_regime_classifier import MarketRegimeClassifier
from src.core.services.regime_types import RegimeType


class TestPhase51_3RegimeStrategyIntegration:
    """Phase 51.3: 市場レジーム連動動的戦略選択統合テスト"""

    @pytest.fixture
    def classifier(self):
        """MarketRegimeClassifier インスタンスを返すfixture"""
        return MarketRegimeClassifier()

    @pytest.fixture
    def selector(self):
        """DynamicStrategySelector インスタンスを返すfixture"""
        return DynamicStrategySelector()

    @pytest.fixture
    def base_df(self):
        """基本的な市場データDataFrameを返すfixture"""
        return pd.DataFrame(
            {
                "close": [100.0] * 50,
                "high": [102.0] * 50,
                "low": [98.0] * 50,
                "volume": [1000.0] * 50,
                "atr_14": [1.5] * 50,
                "adx_14": [15.0] * 50,
                "ema_20": [100.0] * 50,
                "ema_50": [100.0] * 50,
                "donchian_high_20": [102.0] * 50,
                "donchian_low_20": [98.0] * 50,
            }
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # レジーム分類 → 戦略重み取得統合テスト
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_tight_range_classification_to_weights(self, classifier, selector, base_df):
        """狭いレンジ相場: 分類 → 戦略重み取得の統合フロー"""
        # 狭いレンジ相場データ
        df = base_df.copy()
        df["close"] = [100.0 + i * 0.01 for i in range(50)]  # 微小な変動
        df["atr_14"] = [0.5] * 50  # 低ボラティリティ
        df["adx_14"] = [10.0] * 50  # 低ADX

        # 1. レジーム分類
        regime = classifier.classify(df)
        assert regime == RegimeType.TIGHT_RANGE

        # 2. 戦略重み取得
        weights = selector.get_regime_weights(regime)
        assert "ATRBased" in weights
        assert "DonchianChannel" in weights
        assert selector.validate_weights(weights)

    def test_normal_range_classification_to_weights(self, classifier, selector, base_df):
        """通常レンジ相場: 分類 → 戦略重み取得の統合フロー"""
        # 通常レンジ相場データ
        df = base_df.copy()
        df["close"] = [100.0 + (i % 10) * 0.5 for i in range(50)]  # レンジ変動
        df["atr_14"] = [1.0] * 50
        df["adx_14"] = [15.0] * 50  # ADX < 20

        # 1. レジーム分類
        regime = classifier.classify(df)
        assert regime == RegimeType.NORMAL_RANGE

        # 2. 戦略重み取得
        weights = selector.get_regime_weights(regime)
        assert "ATRBased" in weights
        assert "DonchianChannel" in weights
        assert "ADXTrendStrength" in weights
        assert selector.validate_weights(weights)

    def test_trending_classification_to_weights(self, classifier, selector, base_df):
        """トレンド相場: 分類 → 戦略重み取得の統合フロー"""
        # トレンド相場データ
        df = base_df.copy()
        df["close"] = [100.0 + i * 0.5 for i in range(50)]  # 上昇トレンド
        df["atr_14"] = [2.0] * 50
        df["adx_14"] = [30.0] * 50  # ADX > 25
        df["ema_20"] = [100.0 + i * 0.5 for i in range(50)]  # EMA上昇

        # 1. レジーム分類
        regime = classifier.classify(df)
        assert regime == RegimeType.TRENDING

        # 2. 戦略重み取得 - Phase 51.5-A: 3戦略構成
        weights = selector.get_regime_weights(regime)
        assert "ADXTrendStrength" in weights
        assert "ATRBased" in weights
        assert "DonchianChannel" in weights
        assert selector.validate_weights(weights)

    def test_high_volatility_classification_to_weights(self, classifier, selector, base_df):
        """高ボラティリティ: 分類 → 全戦略無効化の統合フロー"""
        # 高ボラティリティデータ
        df = base_df.copy()
        df["close"] = [100.0] * 50
        df["atr_14"] = [3.5] * 50  # ATR / close = 0.035 > 0.018

        # 1. レジーム分類
        regime = classifier.classify(df)
        assert regime == RegimeType.HIGH_VOLATILITY

        # 2. 戦略重み取得（全戦略0.0） - Phase 51.5-A: 3戦略構成
        weights = selector.get_regime_weights(regime)
        assert len(weights) == 3  # 全3戦略を含む - Phase 51.5-A
        assert all(weight == 0.0 for weight in weights.values())  # 全戦略無効化
        assert selector.validate_weights(weights)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # エラーハンドリングテスト
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_integration_with_invalid_data(self, classifier, selector):
        """不正データでのエラーハンドリング統合テスト"""
        # 空のDataFrame
        df = pd.DataFrame()

        # 1. レジーム分類（エラーハンドリング → デフォルト）
        regime = classifier.classify(df)
        assert regime == RegimeType.NORMAL_RANGE  # デフォルト

        # 2. 戦略重み取得
        weights = selector.get_regime_weights(regime)
        assert selector.validate_weights(weights)

    def test_integration_with_missing_columns(self, classifier, selector):
        """必須カラム不足でのエラーハンドリング統合テスト"""
        # 必須カラム不足
        df = pd.DataFrame(
            {
                "close": [100.0] * 50,
                # atr_14, adx_14が不足
            }
        )

        # 1. レジーム分類（エラーハンドリング → デフォルト）
        regime = classifier.classify(df)
        assert regime == RegimeType.NORMAL_RANGE  # デフォルト

        # 2. 戦略重み取得
        weights = selector.get_regime_weights(regime)
        assert selector.validate_weights(weights)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 複数レジーム遷移テスト
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def test_regime_transition_weights_update(self, classifier, selector, base_df):
        """レジーム遷移時の戦略重み更新シナリオテスト"""
        # シナリオ1: 狭いレンジ
        df1 = base_df.copy()
        df1["close"] = [100.0 + i * 0.01 for i in range(50)]
        df1["atr_14"] = [0.5] * 50
        df1["adx_14"] = [10.0] * 50

        regime1 = classifier.classify(df1)
        weights1 = selector.get_regime_weights(regime1)

        # シナリオ2: トレンド相場
        df2 = base_df.copy()
        df2["close"] = [100.0 + i * 0.5 for i in range(50)]
        df2["atr_14"] = [2.0] * 50
        df2["adx_14"] = [30.0] * 50
        df2["ema_20"] = [100.0 + i * 0.5 for i in range(50)]

        regime2 = classifier.classify(df2)
        weights2 = selector.get_regime_weights(regime2)

        # 異なるレジーム → 異なる戦略重み
        assert regime1 != regime2
        assert weights1 != weights2

        # どちらも有効な重み
        assert selector.validate_weights(weights1)
        assert selector.validate_weights(weights2)
