"""
ML信頼度計算ヘルパー - Phase 87 C2 / H10

旧実装: confidence = float(np.max(probabilities[-1]))
    → 「予測クラスの確率」ではなく「最大確率」を返していた。
    → meta-labeling では p(1) を必要とするが、p(0) を返すケースがあり
       品質フィルタの判定がブレた。

新実装: predicted_class = np.argmax(probabilities[-1]);
       confidence = probabilities[-1][predicted_class]
    → predict() と argmax() が完全に一致する保証。
    → trading_cycle_manager.py と backtest_runner.py で同一ロジックを共有
       することで H10 (ライブ vs バックテスト整合性) を確保する。
"""

from typing import Tuple

import numpy as np


def get_predicted_class_proba(probabilities: np.ndarray) -> Tuple[int, float]:
    """probabilities から (predicted_class, confidence) を返す。

    Args:
        probabilities: 形状 (n_samples, n_classes) の確率配列、
                       または最終1サンプル分の (n_classes,) 配列。

    Returns:
        (predicted_class, confidence): predicted_class は argmax、
        confidence は predicted_class の確率。

    Note:
        - 正常な確率分布（要素 ≥ 0、合計 ≈ 1）であれば `confidence`
          は `np.max(probs)` と数学的に等価。
        - 確率が同値で複数の argmax 候補がある場合（例: [0.5, 0.5]）、
          numpy の argmax は **先勝ち（最小インデックス）** を返す。
          メタラベリングモードでは class 1 を「成功」と扱うため、
          同値時に class 0 が選ばれ confidence=0.5 のまま品質フィルタ
          で reject されることが起こりうる。
        - 空配列 (`np.array([])`) は IndexError/ValueError を発生させる
          ことで silent failure を防止する設計。
    """
    arr = np.asarray(probabilities)
    last = arr[-1] if arr.ndim > 1 else arr
    predicted_class = int(np.argmax(last))
    confidence = float(last[predicted_class])
    return predicted_class, confidence
