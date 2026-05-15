"""
Phase 89-β: 外部 API 派生特徴量テスト（+10）

feature_generator._add_external_features の動作と generate_features 経由での
external_api_client 連携を検証。
"""

import numpy as np
import pandas as pd
import pytest

from src.features.feature_cache import reset_feature_cache
from src.features.feature_generator import FeatureGenerator


@pytest.fixture(autouse=True)
def _reset_feature_cache():
    """各テストで FeatureCache シングルトンをリセット（前テストのキャッシュヒット防止）."""
    reset_feature_cache()
    yield
    reset_feature_cache()


@pytest.fixture
def base_df():
    """100 行の OHLCV データ（btc_realized_vol_24h 計算可能な長さ）."""
    np.random.seed(0)
    n = 100
    idx = pd.date_range("2026-01-01", periods=n, freq="15min")
    closes = 5_000_000 * np.cumprod(1 + np.random.normal(0, 0.005, n))
    return pd.DataFrame(
        {
            "open": closes,
            "high": closes * 1.002,
            "low": closes * 0.998,
            "close": closes,
            "volume": np.random.lognormal(7, 0.3, n),
        },
        index=idx,
    )


def test_add_external_features_fallback_to_zero_when_no_values(base_df):
    """external_values=None → funding/sentiment は 0、depth_ratio は neutral 1.0."""
    gen = FeatureGenerator()
    result = gen._add_external_features(base_df.copy(), external_values=None)
    assert (result["funding_rate_8h_avg"] == 0.0).all()
    assert (result["fear_greed_index"] == 0.0).all()
    assert (result["depth_ratio"] == 1.0).all()


def test_add_external_features_propagates_supplied_values(base_df):
    """渡された external_values が funding/sentiment 列に反映される."""
    gen = FeatureGenerator()
    values = {"funding_rate_8h_avg": 0.0003, "fear_greed_index": 0.75}
    result = gen._add_external_features(base_df.copy(), external_values=values)
    assert (result["funding_rate_8h_avg"] == 0.0003).all()
    assert (result["fear_greed_index"] == 0.75).all()


def test_add_external_features_creates_all_ten_columns(base_df):
    """10 特徴量が全て df に追加される."""
    gen = FeatureGenerator()
    result = gen._add_external_features(base_df.copy())
    expected = {
        "funding_rate_8h_avg",
        "fear_greed_index",
        "ofi_top5",
        "bid_ask_imbalance",
        "depth_ratio",
        "btc_dominance_change",
        "usdjpy_change",
        "nikkei_change_proxy",
        "btc_realized_vol_24h",
        "btc_funding_premium",
    }
    assert expected.issubset(result.columns)
    # computed_features にも登録されているか
    assert expected.issubset(gen.computed_features)


def test_btc_realized_vol_computed_from_close(base_df):
    """btc_realized_vol_24h が close 列の log return rolling std から非ゼロ値で計算される."""
    gen = FeatureGenerator()
    result = gen._add_external_features(base_df.copy())
    # 96 本未満の min_periods=24 でも非ゼロが出るはず
    vol_series = result["btc_realized_vol_24h"]
    # 24 行目以降は非ゼロ（rolling 完成後）
    non_zero_count = (vol_series.iloc[24:] != 0.0).sum()
    assert non_zero_count > 0


def test_btc_realized_vol_zero_for_short_df():
    """短い DF（24 行未満）では btc_realized_vol_24h は 0 fill."""
    short_df = pd.DataFrame(
        {
            "open": [1.0] * 10,
            "high": [1.0] * 10,
            "low": [1.0] * 10,
            "close": [1.0] * 10,
            "volume": [1.0] * 10,
        }
    )
    gen = FeatureGenerator()
    result = gen._add_external_features(short_df.copy())
    assert (result["btc_realized_vol_24h"] == 0.0).all()


def test_btc_funding_premium_annualized(base_df):
    """funding_rate × 365 × 3 で年率プレミアム算出."""
    gen = FeatureGenerator()
    values = {"funding_rate_8h_avg": 0.0001, "fear_greed_index": 0.5}
    result = gen._add_external_features(base_df.copy(), external_values=values)
    expected = 0.0001 * 365 * 3
    assert np.allclose(result["btc_funding_premium"].values, expected, atol=1e-9)


@pytest.mark.asyncio
async def test_generate_features_uses_external_api_client(base_df):
    """external_api_client 注入時、generate_features が funding/fear_greed を取得して反映する."""
    from unittest.mock import AsyncMock

    mock_client = AsyncMock()
    mock_client.fetch_funding_rate = AsyncMock(return_value=0.0002)
    mock_client.fetch_fear_greed_index = AsyncMock(return_value=0.6)

    gen = FeatureGenerator(external_api_client=mock_client)
    result = await gen.generate_features(base_df)

    assert (result["funding_rate_8h_avg"] == 0.0002).all()
    assert (result["fear_greed_index"] == 0.6).all()
    mock_client.fetch_funding_rate.assert_awaited_once()
    mock_client.fetch_fear_greed_index.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_features_falls_back_on_external_api_exception(base_df):
    """external_api_client が例外を投げても 0 fill で動作継続（fail-open）."""
    from unittest.mock import AsyncMock

    mock_client = AsyncMock()
    mock_client.fetch_funding_rate = AsyncMock(side_effect=RuntimeError("API down"))
    mock_client.fetch_fear_greed_index = AsyncMock(return_value=0.5)

    gen = FeatureGenerator(external_api_client=mock_client)
    result = await gen.generate_features(base_df)

    # fetch_funding_rate が失敗したため、_fetch_external_values は全 0 fallback
    assert (result["funding_rate_8h_avg"] == 0.0).all()
    assert (result["fear_greed_index"] == 0.0).all()


# ===== Phase 89-γ: VPIN + HMM 状態確率 (+5) =====


def test_add_microstructure_advanced_creates_five_columns(base_df):
    """VPIN 3 + HMM 2 = 5 列が追加される."""
    gen = FeatureGenerator()
    result = gen._add_microstructure_advanced_features(base_df.copy())
    for name in ("vpin", "vpin_ma20", "vpin_change", "hmm_state_bear_prob", "hmm_state_bull_prob"):
        assert name in result.columns
        assert name in gen.computed_features


def test_vpin_within_zero_one_range(base_df):
    """VPIN は [0, 1] にクリップされる."""
    gen = FeatureGenerator()
    result = gen._add_microstructure_advanced_features(base_df.copy())
    assert result["vpin"].between(0.0, 1.0).all()
    assert result["vpin_ma20"].between(0.0, 1.0).all()


def test_vpin_change_is_diff_of_vpin(base_df):
    """vpin_change が vpin の 1 期間差分."""
    gen = FeatureGenerator()
    result = gen._add_microstructure_advanced_features(base_df.copy())
    # 先頭以外は diff の定義通り
    diff = result["vpin"].diff().fillna(0.0)
    assert np.allclose(result["vpin_change"].values, diff.values, atol=1e-9)


def test_hmm_probs_uniform_without_regime_classifier(base_df):
    """regime_classifier=None なら HMM 確率は 1/3 fill."""
    gen = FeatureGenerator()  # regime_classifier 未指定
    result = gen._add_microstructure_advanced_features(base_df.copy())
    assert np.allclose(result["hmm_state_bear_prob"].values, 1.0 / 3, atol=1e-6)
    assert np.allclose(result["hmm_state_bull_prob"].values, 1.0 / 3, atol=1e-6)


def test_hmm_probs_use_regime_classifier_when_provided(base_df):
    """regime_classifier 注入で HMM 確率値が反映される."""
    from unittest.mock import MagicMock

    mock_regime = MagicMock()
    mock_regime.get_hmm_state_probabilities = MagicMock(
        return_value={
            "hmm_state_bear_prob": 0.2,
            "hmm_state_sideways_prob": 0.3,
            "hmm_state_bull_prob": 0.5,
        }
    )

    gen = FeatureGenerator(regime_classifier=mock_regime)
    result = gen._add_microstructure_advanced_features(base_df.copy())
    assert np.allclose(result["hmm_state_bear_prob"].values, 0.2, atol=1e-6)
    assert np.allclose(result["hmm_state_bull_prob"].values, 0.5, atol=1e-6)


# ===== Phase 89-δ: BTC-ETH 相関 (+3) =====


def test_cross_asset_creates_three_columns(base_df):
    """_add_cross_asset_features は 3 列を追加."""
    gen = FeatureGenerator()
    result = gen._add_cross_asset_features(base_df.copy(), external_values=None)
    for name in ("eth_btc_price_ratio", "eth_btc_corr_24h", "eth_returns_15m"):
        assert name in result.columns
        assert name in gen.computed_features


def test_cross_asset_zero_fill_when_no_eth(base_df):
    """external_values=None / ETH=0 のとき全列 0 fill."""
    gen = FeatureGenerator()
    result = gen._add_cross_asset_features(base_df.copy())
    assert (result["eth_btc_price_ratio"] == 0.0).all()
    assert (result["eth_btc_corr_24h"] == 0.0).all()
    assert (result["eth_returns_15m"] == 0.0).all()


def test_cross_asset_price_ratio_computed_with_eth(base_df):
    """ETH last 注入で eth_btc_price_ratio = eth/btc."""
    gen = FeatureGenerator()
    btc_last = float(base_df["close"].iloc[-1])
    eth_last = 250000.0
    result = gen._add_cross_asset_features(
        base_df.copy(), external_values={"eth_jpy_last": eth_last}
    )
    expected_ratio = eth_last / btc_last
    assert np.isclose(result["eth_btc_price_ratio"].iloc[0], expected_ratio, atol=1e-9)


def test_eth_returns_15m_uses_history_diff(base_df):
    """連続 2 回の eth 値で eth_returns_15m が (curr-prev)/prev になる."""
    gen = FeatureGenerator()
    # 1 回目: history に 250000 が積まれる
    gen._add_cross_asset_features(
        base_df.copy(), external_values={"eth_jpy_last": 250000.0}
    )
    # 2 回目: history に 252500 (+1%) が積まれる
    result = gen._add_cross_asset_features(
        base_df.copy(), external_values={"eth_jpy_last": 252500.0}
    )
    # eth_returns_15m = (252500-250000)/250000 = 0.01
    assert np.isclose(result["eth_returns_15m"].iloc[0], 0.01, atol=1e-9)


def test_corr_zero_when_history_short(base_df):
    """24 サンプル未満では eth_btc_corr_24h=0."""
    gen = FeatureGenerator()
    # 数回しか蓄積しない
    for _ in range(5):
        gen._add_cross_asset_features(
            base_df.copy(), external_values={"eth_jpy_last": 250000.0}
        )
    # history 5 件 → 24 未満 → corr=0
    assert gen._add_cross_asset_features(
        base_df.copy(), external_values={"eth_jpy_last": 250000.0}
    )["eth_btc_corr_24h"].iloc[0] == 0.0
