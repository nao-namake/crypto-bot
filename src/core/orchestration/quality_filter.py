"""品質フィルタ共通モジュール - Phase 87 Stage 3 H10 / H6

メタラベリング (Triple Barrier) の Go/No-Go 判定を、ライブ取引（trading_cycle_manager）と
バックテスト（backtest_runner）の両方で **同一ロジック** で実施するための共通モジュール。

Phase 87 Stage 3 着手前の課題:
- ライブ側 (`trading_cycle_manager._apply_quality_filter`) は accept/reject/uncertain の3分岐で
  シグナル変換していたが、バックテスト側は confidence を記録するだけで品質フィルタ未適用。
- H6 でレジーム別閾値を導入する設計だったが、`_apply_quality_filter` には regime 引数が
  渡されていなかった（trading_cycle_manager.py:744 で呼び出し時に未渡し）。

本モジュールの責務:
1. `QualityFilter.evaluate(ml_prediction, ml_confidence, regime)` → 純粋判定（StrategySignal 非依存）
2. `apply_to_signal(result, strategy_signal)` → StrategySignal 変換（既存 _apply_quality_filter 互換）
3. レジーム別閾値ルックアップ（regime_thresholds.<regime> → quality_filter.<key> フォールバック）

呼び出し側:
- `trading_cycle_manager._apply_quality_filter`: evaluate + apply_to_signal を順に呼ぶ
- `backtest_runner._precompute_ml_predictions`: evaluate を呼んで verdict を ML予測dict に含める
  → verdict='reject' のサンプルでバックテスト側もエントリー拒否可能
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, Literal, Optional

from ..config import get_threshold
from ..logger import get_logger

if TYPE_CHECKING:
    from ...strategies.base.strategy_base import StrategySignal


# verdict 3 種類
Verdict = Literal["accept", "reject", "uncertain"]


@dataclass
class QualityFilterResult:
    """品質フィルタの判定結果。

    Attributes:
        verdict: "accept" (取引承認) / "reject" (取引拒否=HOLD) / "uncertain" (信頼度縮小)
        ml_prediction: 元の ML予測値 (0 or 1 等)
        ml_confidence: 元の ML 信頼度
        adjusted_confidence_factor: confidence 縮小倍率（uncertain時は uncertain_penalty、reject時は0.1、accept時は1.0）
        regime: 判定時のレジーム文字列
        thresholds_used: 実際に使用された閾値辞書（accept/reject/high_conf_fail）
        reason: 判定理由（ログ・記録用）
    """

    verdict: Verdict
    ml_prediction: int
    ml_confidence: float
    adjusted_confidence_factor: float
    regime: str = "unknown"
    thresholds_used: Dict[str, float] = field(default_factory=dict)
    reason: str = ""


class QualityFilter:
    """品質フィルタ判定ロジック（純粋関数的、StrategySignal 非依存）"""

    # Global デフォルト（thresholds.yaml の ml.quality_filter にフォールバック）
    DEFAULT_ACCEPT_THRESHOLD = 0.58
    DEFAULT_REJECT_THRESHOLD = 0.42
    DEFAULT_UNCERTAIN_PENALTY = 0.5
    DEFAULT_HIGH_CONF_FAILURE = 0.65

    def __init__(self, regime_aware: bool = True) -> None:
        """
        Args:
            regime_aware: True なら regime に応じて閾値を切替。False なら常にグローバル値。
        """
        self.logger = get_logger()
        self.regime_aware = regime_aware

    def evaluate(
        self,
        ml_prediction: int,
        ml_confidence: float,
        regime: str = "unknown",
    ) -> QualityFilterResult:
        """ML予測と信頼度から品質フィルタ判定を行う。

        判定ロジック（既存 `_apply_quality_filter` から移植）:
          1. ml_pred == 1 かつ confidence >= accept_threshold → accept
          2. (ml_pred == 0 かつ confidence >= high_conf_failure) または confidence < reject_threshold
             → reject (HOLD化)
          3. それ以外（中間帯）→ uncertain (信頼度を uncertain_penalty 倍に縮小)

        Args:
            ml_prediction: ML 予測クラス（0 or 1）
            ml_confidence: ML 信頼度 (max prob or predicted_class_proba)
            regime: 市場レジーム文字列（"tight_range"/"normal_range"/"trending"/"high_volatility"/"unknown"）

        Returns:
            QualityFilterResult: 判定結果
        """
        thresholds = self._lookup_thresholds(regime)
        accept = thresholds["accept_threshold"]
        reject = thresholds["reject_threshold"]
        high_conf_fail = thresholds["high_confidence_failure_threshold"]
        uncertain_penalty = thresholds["uncertain_penalty"]

        # accept 判定
        if ml_prediction == 1 and ml_confidence >= accept:
            return QualityFilterResult(
                verdict="accept",
                ml_prediction=ml_prediction,
                ml_confidence=ml_confidence,
                adjusted_confidence_factor=1.0,
                regime=regime,
                thresholds_used=thresholds,
                reason=f"accept: ml_pred=1, conf={ml_confidence:.3f}>={accept:.3f}",
            )

        # reject 判定
        if (ml_prediction == 0 and ml_confidence >= high_conf_fail) or (ml_confidence < reject):
            return QualityFilterResult(
                verdict="reject",
                ml_prediction=ml_prediction,
                ml_confidence=ml_confidence,
                adjusted_confidence_factor=0.1,  # reject時は confidence を 10% に
                regime=regime,
                thresholds_used=thresholds,
                reason=(
                    f"reject: ml_pred={ml_prediction}, conf={ml_confidence:.3f} "
                    f"(reject_th={reject:.3f}, high_conf_fail={high_conf_fail:.3f})"
                ),
            )

        # uncertain (中間帯)
        return QualityFilterResult(
            verdict="uncertain",
            ml_prediction=ml_prediction,
            ml_confidence=ml_confidence,
            adjusted_confidence_factor=uncertain_penalty,
            regime=regime,
            thresholds_used=thresholds,
            reason=(
                f"uncertain: ml_pred={ml_prediction}, conf={ml_confidence:.3f} "
                f"in [{reject:.3f}, {accept:.3f}) → factor={uncertain_penalty}"
            ),
        )

    def _lookup_thresholds(self, regime: str) -> Dict[str, float]:
        """Phase 87 H6: regime に応じた閾値を返す。

        ルックアップ順:
          1. `ml.quality_filter.regime_thresholds.<regime>.<key>`
          2. `ml.quality_filter.<key>`
          3. クラス定数（DEFAULT_*）
        """
        # Global デフォルト
        global_accept = get_threshold(
            "ml.quality_filter.accept_threshold", self.DEFAULT_ACCEPT_THRESHOLD
        )
        global_reject = get_threshold(
            "ml.quality_filter.reject_threshold", self.DEFAULT_REJECT_THRESHOLD
        )
        global_high_conf_fail = get_threshold(
            "ml.quality_filter.high_confidence_failure_threshold",
            self.DEFAULT_HIGH_CONF_FAILURE,
        )
        global_uncertain_penalty = get_threshold(
            "ml.quality_filter.uncertain_penalty", self.DEFAULT_UNCERTAIN_PENALTY
        )

        if not self.regime_aware or not regime or regime == "unknown":
            return {
                "accept_threshold": float(global_accept),
                "reject_threshold": float(global_reject),
                "high_confidence_failure_threshold": float(global_high_conf_fail),
                "uncertain_penalty": float(global_uncertain_penalty),
            }

        # レジーム別ルックアップ（個別キーごとに fallback）
        base = f"ml.quality_filter.regime_thresholds.{regime}"
        return {
            "accept_threshold": float(get_threshold(f"{base}.accept_threshold", global_accept)),
            "reject_threshold": float(get_threshold(f"{base}.reject_threshold", global_reject)),
            "high_confidence_failure_threshold": float(
                get_threshold(f"{base}.high_confidence_failure_threshold", global_high_conf_fail)
            ),
            "uncertain_penalty": float(
                get_threshold(f"{base}.uncertain_penalty", global_uncertain_penalty)
            ),
        }


def apply_to_signal(
    result: QualityFilterResult, strategy_signal: "StrategySignal"
) -> "StrategySignal":
    """QualityFilterResult を StrategySignal に適用する。

    既存 `_apply_quality_filter` の StrategySignal 変換ロジックを共通化。
    - verdict='accept': そのまま通過
    - verdict='reject': HOLD化、confidence を 10% に縮小
    - verdict='uncertain': 元の action 維持、confidence を uncertain_penalty 倍に縮小

    HOLD/none/空アクションは判定不要として常にそのまま返す。
    """
    from ...strategies.base.strategy_base import StrategySignal

    # 非取引シグナルは素通り
    if strategy_signal.action in ("hold", "none", ""):
        return strategy_signal

    if result.verdict == "accept":
        return strategy_signal

    if result.verdict == "reject":
        return StrategySignal(
            strategy_name=strategy_signal.strategy_name,
            timestamp=strategy_signal.timestamp,
            action="hold",
            confidence=strategy_signal.confidence * result.adjusted_confidence_factor,
            strength=0.0,
            current_price=strategy_signal.current_price,
            entry_price=strategy_signal.entry_price,
            stop_loss=None,
            take_profit=None,
            position_size=strategy_signal.position_size,
            risk_ratio=strategy_signal.risk_ratio,
            indicators=strategy_signal.indicators,
            reason=f"Phase 87 H10: 品質フィルタ拒否 ({result.reason})",
            metadata={
                **(strategy_signal.metadata or {}),
                "quality_filtered": True,
                "original_action": strategy_signal.action,
                "ml_quality_score": result.ml_confidence,
                "ml_quality_regime": result.regime,
                "ml_quality_verdict": result.verdict,
            },
        )

    # uncertain
    return StrategySignal(
        strategy_name=strategy_signal.strategy_name,
        timestamp=strategy_signal.timestamp,
        action=strategy_signal.action,
        confidence=strategy_signal.confidence * result.adjusted_confidence_factor,
        strength=strategy_signal.strength,
        current_price=strategy_signal.current_price,
        entry_price=strategy_signal.entry_price,
        stop_loss=strategy_signal.stop_loss,
        take_profit=strategy_signal.take_profit,
        position_size=strategy_signal.position_size,
        risk_ratio=strategy_signal.risk_ratio,
        indicators=strategy_signal.indicators,
        reason=strategy_signal.reason,
        metadata={
            **(strategy_signal.metadata or {}),
            "quality_uncertain": True,
            "ml_quality_score": result.ml_confidence,
            "ml_quality_regime": result.regime,
            "ml_quality_verdict": result.verdict,
        },
    )
