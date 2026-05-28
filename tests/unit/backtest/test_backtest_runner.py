"""
BacktestRunner._precompute_ml_predictions ユニットテスト - Phase 90γ-⑨

Phase 35.4 の ML 予測事前計算経路を異常系含めて検証する。
バックテストとライブの整合性に直結する経路だが、これまで直接テストが無かったため
Phase 90γ-⑦ で追加した新規 WARNING ログのアサートと同時に整備する。
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from src.core.execution.backtest_runner import BacktestRunner


@pytest.fixture
def mock_logger():
    """モックロガー"""
    logger = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    logger.info = MagicMock()
    logger.debug = MagicMock()
    return logger


@pytest.fixture
def runner(mock_logger):
    """BacktestRunner インスタンスを最小構成で生成（__init__ バイパス）.

    `_precompute_ml_predictions` はインスタンスの少数属性しか触らないため、
    重い MarketRegimeClassifier や DrawdownManager 初期化はスキップする。
    """
    instance = BacktestRunner.__new__(BacktestRunner)
    instance.logger = mock_logger
    instance.timeframes = ["15m", "4h"]
    instance.precomputed_features = {}
    instance.precomputed_ml_predictions = {}
    instance.orchestrator = MagicMock()
    instance.orchestrator.ml_service = MagicMock()
    return instance


def _make_features_df(n_rows: int, feature_names) -> pd.DataFrame:
    """指定特徴量名で n_rows 行のダミーデータを作る"""
    data = {name: np.linspace(0.0, 1.0, n_rows) for name in feature_names}
    return pd.DataFrame(data)


class TestBacktestRunnerMLPrecompute:
    """`_precompute_ml_predictions` の正常・異常系テスト（Phase 90γ-⑨）"""

    @pytest.mark.asyncio
    async def test_predicts_successfully_when_all_features_available(self, runner):
        """全特徴量が揃っているとき predictions/probabilities が保存される"""
        feature_names = ["feat_a", "feat_b", "feat_c"]
        df = _make_features_df(10, feature_names)
        runner.precomputed_features["15m"] = df

        # ml_service.predict / predict_proba をスタブ
        runner.orchestrator.ml_service.predict.return_value = np.zeros(10, dtype=int)
        runner.orchestrator.ml_service.predict_proba.return_value = np.full((10, 3), 1.0 / 3.0)

        with patch(
            "src.core.config.feature_manager.get_feature_names",
            return_value=feature_names,
        ):
            await runner._precompute_ml_predictions()

        assert "15m" in runner.precomputed_ml_predictions
        assert len(runner.precomputed_ml_predictions["15m"]["predictions"]) == 10
        assert runner.precomputed_ml_predictions["15m"]["probabilities"].shape == (10, 3)

    @pytest.mark.asyncio
    async def test_warns_and_skips_when_features_missing(self, runner):
        """特徴量不足のとき WARNING を出して保存スキップ"""
        df = _make_features_df(5, ["feat_a"])
        runner.precomputed_features["15m"] = df

        with patch(
            "src.core.config.feature_manager.get_feature_names",
            return_value=["feat_a", "feat_b", "feat_c"],  # 3 個必要だが 1 個しかない
        ):
            await runner._precompute_ml_predictions()

        # ML 予測は呼ばれない・予測結果も保存されない
        runner.orchestrator.ml_service.predict.assert_not_called()
        assert "15m" not in runner.precomputed_ml_predictions

        # 特徴量不足 WARNING が出る
        warning_messages = [str(c.args[0]) for c in runner.logger.warning.call_args_list]
        assert any("特徴量不足" in msg for msg in warning_messages)

    @pytest.mark.asyncio
    async def test_no_action_when_main_timeframe_missing(self, runner):
        """precomputed_features に main_timeframe が無いときは何も保存されない"""
        # 15m を入れない（空のまま）
        with patch(
            "src.core.config.feature_manager.get_feature_names",
            return_value=["feat_a"],
        ):
            await runner._precompute_ml_predictions()

        assert runner.precomputed_ml_predictions == {}
        runner.orchestrator.ml_service.predict.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_predict_exception_gracefully(self, runner):
        """predict 中に例外が出ても error ログ + dict クリアで継続"""
        feature_names = ["feat_a", "feat_b"]
        runner.precomputed_features["15m"] = _make_features_df(5, feature_names)
        runner.orchestrator.ml_service.predict.side_effect = RuntimeError("model crashed")

        with patch(
            "src.core.config.feature_manager.get_feature_names",
            return_value=feature_names,
        ):
            await runner._precompute_ml_predictions()

        # error ログが出力されている
        error_messages = [str(c.args[0]) for c in runner.logger.error.call_args_list]
        assert any("ML予測事前計算エラー" in msg for msg in error_messages)
        # precomputed_ml_predictions はクリアされた状態
        assert runner.precomputed_ml_predictions == {}

    @pytest.mark.asyncio
    async def test_handles_predict_proba_exception_gracefully(self, runner):
        """predict_proba 例外も同様に error ログ + dict クリア"""
        feature_names = ["feat_a", "feat_b"]
        runner.precomputed_features["15m"] = _make_features_df(5, feature_names)
        runner.orchestrator.ml_service.predict.return_value = np.zeros(5, dtype=int)
        runner.orchestrator.ml_service.predict_proba.side_effect = ValueError("shape mismatch")

        with patch(
            "src.core.config.feature_manager.get_feature_names",
            return_value=feature_names,
        ):
            await runner._precompute_ml_predictions()

        error_messages = [str(c.args[0]) for c in runner.logger.error.call_args_list]
        assert any("ML予測事前計算エラー" in msg for msg in error_messages)
        assert runner.precomputed_ml_predictions == {}

    @pytest.mark.asyncio
    async def test_falls_back_to_15m_when_timeframes_empty(self, runner):
        """timeframes が空のときデフォルト '15m' が main_timeframe として使用される"""
        runner.timeframes = []
        feature_names = ["feat_a"]
        runner.precomputed_features["15m"] = _make_features_df(3, feature_names)
        runner.orchestrator.ml_service.predict.return_value = np.zeros(3, dtype=int)
        runner.orchestrator.ml_service.predict_proba.return_value = np.full((3, 3), 1.0 / 3.0)

        with patch(
            "src.core.config.feature_manager.get_feature_names",
            return_value=feature_names,
        ):
            await runner._precompute_ml_predictions()

        # 15m が使われた → 結果が保存されている
        assert "15m" in runner.precomputed_ml_predictions

    @pytest.mark.asyncio
    async def test_emits_start_and_complete_warning_logs(self, runner):
        """開始・完了の WARNING ログが出力される（本番 LOG_LEVEL=WARNING で観察可能）"""
        feature_names = ["feat_a"]
        runner.precomputed_features["15m"] = _make_features_df(2, feature_names)
        runner.orchestrator.ml_service.predict.return_value = np.zeros(2, dtype=int)
        runner.orchestrator.ml_service.predict_proba.return_value = np.full((2, 3), 1.0 / 3.0)

        with patch(
            "src.core.config.feature_manager.get_feature_names",
            return_value=feature_names,
        ):
            await runner._precompute_ml_predictions()

        warning_messages = [str(c.args[0]) for c in runner.logger.warning.call_args_list]
        assert any("ML予測事前計算開始" in msg for msg in warning_messages)
        assert any("ML予測事前計算完了" in msg for msg in warning_messages)

    @pytest.mark.asyncio
    async def test_empty_features_df_does_not_crash(self, runner):
        """空 DataFrame のときも例外で落ちず、結果が安全に処理される"""
        runner.precomputed_features["15m"] = pd.DataFrame()
        # get_feature_names は何個か返すが、列が一致しないので available_features=0 → スキップ
        with patch(
            "src.core.config.feature_manager.get_feature_names",
            return_value=["feat_a", "feat_b"],
        ):
            await runner._precompute_ml_predictions()

        # ML 予測は呼ばれず、precomputed_ml_predictions は空のまま
        runner.orchestrator.ml_service.predict.assert_not_called()
        assert runner.precomputed_ml_predictions == {}
