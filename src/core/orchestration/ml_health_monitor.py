"""ML健全性監視 - Phase 87 C4 (DummyModel サーキットブレーカー)

ProductionEnsemble が連続して predict/predict_proba 失敗 → DummyModel フォールバック
となった場合、品質フィルタモードでは全 reject 状態となり取引が長期停止する。

本クラスは:
1. 失敗回数を Firestore に永続化（Container 再起動でも保護）
2. 閾値（デフォルト3回）連続失敗で `should_emergency_stop()` が True を返す
3. 上位層（DrawdownManager 等）が True を見て EMERGENCY_STOP に遷移できる

期待動作:
- 通常時: 各 predict 成功で `reset_on_success()` → カウント 0
- 異常時: 各失敗で `record_failure(reason)` → カウント増加
- 閾値到達: 上位層が `should_emergency_stop()` を確認し取引停止
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from ..logger import get_logger


class MLHealthMonitor:
    """ML predict 失敗カウントの永続化 + サーキットブレーカー判定"""

    COLLECTION = "ml_health"
    DOC_ID = "main"
    DEFAULT_THRESHOLD = 3

    def __init__(
        self,
        persistence: Any = None,
        threshold: Optional[int] = None,
        auto_load: bool = True,
    ) -> None:
        """
        Args:
            persistence: FirestoreStateClient（テスト用に外部注入可能）
            threshold: 連続失敗回数の閾値（None なら thresholds.yaml から取得、
                デフォルト 3）
            auto_load: True なら __init__ で既存状態をロード
        """
        self.logger = get_logger()
        # Phase 87 Stage 2-R4: threshold を thresholds.yaml から取得（config 化）
        if threshold is None:
            try:
                from ..config import get_threshold

                threshold = get_threshold(
                    "ml.health.consecutive_failure_threshold", self.DEFAULT_THRESHOLD
                )
            except Exception:
                threshold = self.DEFAULT_THRESHOLD
        self.threshold = int(threshold or self.DEFAULT_THRESHOLD)
        self.consecutive_failures: int = 0
        self.last_failure_at: Optional[str] = None
        self.last_reason: Optional[str] = None

        if persistence is not None:
            self.persistence = persistence
        else:
            try:
                from ..persistence import FirestoreStateClient  # type: ignore

                self.persistence = FirestoreStateClient()
            except Exception as e:
                self.logger.warning(
                    f"⚠️ Phase 87 C4: FirestoreStateClient 初期化失敗 "
                    f"→ MLHealthMonitor はインメモリのみ動作: {e}"
                )
                self.persistence = None

        if auto_load:
            self._load_state()

    # ========================================
    # Public API
    # ========================================

    def record_failure(self, reason: str) -> None:
        """ML predict 失敗を記録する。閾値到達後の判定は呼び出し側で行う。"""
        self.consecutive_failures += 1
        self.last_failure_at = datetime.now(timezone.utc).isoformat()
        self.last_reason = reason
        self.logger.critical(
            f"🚨 Phase 87 C4: ML予測失敗記録 - "
            f"reason={reason}, consecutive={self.consecutive_failures}/{self.threshold}"
        )
        self._save_state()

        if self.should_emergency_stop():
            self.logger.critical(
                f"🚨🚨 Phase 87 C4: ML連続失敗閾値到達 "
                f"({self.consecutive_failures}>={self.threshold}) "
                f"→ 上位層は EMERGENCY_STOP 移行を検討してください"
            )

    def reset_on_success(self) -> None:
        """ML predict 成功時に呼ぶ。カウントが 0 でなければリセット + 永続化。"""
        if self.consecutive_failures > 0:
            self.logger.info(
                f"✅ Phase 87 C4: ML予測復旧 (was consecutive={self.consecutive_failures})"
            )
            self.consecutive_failures = 0
            self.last_reason = None
            self._save_state()

    def should_emergency_stop(self) -> bool:
        """連続失敗が閾値以上なら True"""
        return self.consecutive_failures >= self.threshold

    def get_status(self) -> dict:
        return {
            "consecutive_failures": self.consecutive_failures,
            "threshold": self.threshold,
            "last_failure_at": self.last_failure_at,
            "last_reason": self.last_reason,
            "should_emergency_stop": self.should_emergency_stop(),
        }

    # ========================================
    # Internal persistence
    # ========================================

    def _save_state(self) -> None:
        if self.persistence is None:
            return
        try:
            self.persistence.save(
                self.COLLECTION,
                self.DOC_ID,
                {
                    "consecutive_failures": self.consecutive_failures,
                    "last_failure_at": self.last_failure_at,
                    "last_reason": self.last_reason,
                    "threshold": self.threshold,
                },
            )
        except Exception as e:
            self.logger.warning(f"⚠️ Phase 87 C4: MLHealthMonitor save error: {e}")

    def _load_state(self) -> None:
        if self.persistence is None:
            return
        try:
            state = self.persistence.load(self.COLLECTION, self.DOC_ID)
            if not state:
                return
            self.consecutive_failures = int(state.get("consecutive_failures", 0) or 0)
            self.last_failure_at = state.get("last_failure_at")
            self.last_reason = state.get("last_reason")
            if self.consecutive_failures > 0:
                self.logger.info(
                    f"Phase 87 C4: MLHealthMonitor 状態復元 - "
                    f"consecutive={self.consecutive_failures}/{self.threshold}, "
                    f"last_reason={self.last_reason}"
                )
        except Exception as e:
            self.logger.warning(f"⚠️ Phase 87 C4: MLHealthMonitor load error: {e}")
