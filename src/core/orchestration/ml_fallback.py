"""
MLサービス フォールバック機能 - Phase 49完了

ダミーモデル・フォールバック機能・安全ネット機能を提供。
MLモデル読み込み失敗時の最終的な安全装置。

Phase 49完了:
- DummyModel: 全予測でhold信頼度0.5返却（フォールバック用）
- 55特徴量対応（feature_manager統合）
- 3クラス分類対応（buy/hold/sell）
- is_fitted=True固定（常に利用可能状態）

Phase 28-29: ダミーモデル分離・フォールバック機能専門化
"""

from typing import Union

import numpy as np
import pandas as pd


class DummyModel:
    """
    ダミーモデル（最終フォールバック）

    全ての予測でholdシグナル（信頼度0.5）を返すフォールバック用モデル。
    実際のMLモデルが利用できない場合の安全装置として機能。
    """

    def __init__(self) -> None:
        self.is_fitted = True
        self.model_name = "DummyModel"
        # Phase 28-29最適化: 特徴量定義一元化対応
        from ..config.feature_manager import get_feature_count

        self.n_features_ = get_feature_count()

    def predict(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        """常にholdシグナル（0）を返す予測."""
        n_samples = len(X)
        return np.zeros(n_samples, dtype=int)

    def predict_proba(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        """
        設定値から取得した確率値を返す（フォールバック時は0.5）.

        Returns:
            2D array: [[confidence, confidence], ...] 形式
        """
        try:
            from ..config import get_threshold

            confidence = get_threshold("ml.dummy_confidence", 0.5)
        except Exception:
            confidence = 0.5  # フォールバック値

        n_samples = len(X)
        return np.full((n_samples, 2), confidence)
