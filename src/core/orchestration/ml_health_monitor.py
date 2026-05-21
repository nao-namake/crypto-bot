"""ML健全性監視 - Phase 87 C4 (DummyModel サーキットブレーカー) + Phase 89-β Drift 検出

ProductionEnsemble が連続して predict/predict_proba 失敗 → DummyModel フォールバック
となった場合、品質フィルタモードでは全 reject 状態となり取引が長期停止する。

本クラスは:
1. 失敗回数を Firestore に永続化（Container 再起動でも保護）
2. 閾値（デフォルト3回）連続失敗で `should_emergency_stop()` が True を返す
3. 上位層（DrawdownManager 等）が True を見て EMERGENCY_STOP に遷移できる

Phase 89-β:
4. 特徴量分布のドリフト検出（KS テスト + 連続検知ベース）
5. should_emergency_stop に drift OR 条件を統合（連続 3 回の有意 drift で stop）

期待動作:
- 通常時: 各 predict 成功で `reset_on_success()` → カウント 0
- 異常時: 各失敗で `record_failure(reason)` → カウント増加
- 閾値到達: 上位層が `should_emergency_stop()` を確認し取引停止
- Drift: 各サイクルで `record_feature_distribution(df)` → 内部で KS テスト → drift 検知
"""

from __future__ import annotations

import math
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional

from ..logger import get_logger

# Phase 90α: 「persistence 引数省略」と「明示的 None」を区別する sentinel
# - 省略 (デフォルト): FirestoreStateClient を自動生成（本番経路）
# - 明示的 None: インメモリ動作（テスト・ローカル動作確認用）
_PERSISTENCE_DEFAULT = object()


class MLHealthMonitor:
    """ML predict 失敗カウントの永続化 + サーキットブレーカー判定"""

    COLLECTION = "ml_health"
    DOC_ID = "main"
    DEFAULT_THRESHOLD = 3

    def __init__(
        self,
        persistence: Any = _PERSISTENCE_DEFAULT,
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

        # Phase 89-β: Drift 検出用の特徴量分布履歴
        # Phase 89 H4: Bonferroni 補正 + 有意特徴量数下限による偽陽性抑制
        # Phase 90γ-①: Drift 検出の構造的バグ修正
        #   1. exclude_features: 価格絶対値・MA・BB を比較対象から除外
        #   2. reference_reset_hours: reference 分布を定期 reset（古い分布との永続乖離防止）
        try:
            from ..config import get_threshold as _gt

            self._drift_window = int(_gt("ml.drift.window_size", 200))
            self._drift_ks_alpha = float(_gt("ml.drift.ks_alpha", 0.01))
            self._drift_consecutive_threshold = int(_gt("ml.drift.consecutive_threshold", 3))
            self._drift_significant_feature_min = int(_gt("ml.drift.significant_feature_min", 3))
            self._drift_auto_retraining = bool(_gt("ml.drift.enable_auto_retraining", True))
            # Phase 90γ-①: 除外リスト（価格絶対値系を drift 比較から除外）
            exclude_raw = _gt("ml.drift.exclude_features", []) or []
            self._drift_exclude_features = (
                set(str(x) for x in exclude_raw) if isinstance(exclude_raw, list) else set()
            )
            # Phase 90γ-①: reference 分布の定期 reset（古い reference との永続乖離を防止）
            self._drift_reference_reset_hours = float(_gt("ml.drift.reference_reset_hours", 168.0))
        except Exception:
            self._drift_window = 200
            self._drift_ks_alpha = 0.01
            self._drift_consecutive_threshold = 3
            self._drift_significant_feature_min = 3
            self._drift_auto_retraining = True
            self._drift_exclude_features = set()
            self._drift_reference_reset_hours = 168.0
        self._reference_distribution: Dict[str, List[float]] = {}
        self._recent_distribution: Dict[str, Deque[float]] = {}
        self.consecutive_drift_detections: int = 0
        self.last_drift_at: Optional[str] = None
        # Phase 90γ-①: reference 初期化時刻（None = 未初期化）
        self._reference_initialized_at: Optional[datetime] = None

        # Phase 90α: persistence の semantics 修正
        # - 明示的 None: インメモリ動作（test_no_persistence_works_inmemory の意図）
        # - 省略 (_PERSISTENCE_DEFAULT): FirestoreStateClient 自動生成（本番経路）
        # - その他: 渡された値を使用
        if persistence is _PERSISTENCE_DEFAULT:
            try:
                from ..persistence import FirestoreStateClient  # type: ignore

                self.persistence = FirestoreStateClient()
            except Exception as e:
                self.logger.warning(
                    f"⚠️ Phase 87 C4: FirestoreStateClient 初期化失敗 "
                    f"→ MLHealthMonitor はインメモリのみ動作: {e}"
                )
                self.persistence = None
        else:
            # 明示的に渡された値（None 含む）をそのまま使用
            self.persistence = persistence

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
        """連続失敗が閾値以上 OR 連続 drift 検出が閾値以上なら True (Phase 89-β)"""
        return (
            self.consecutive_failures >= self.threshold
            or self.consecutive_drift_detections >= self._drift_consecutive_threshold
        )

    def get_status(self) -> dict:
        return {
            "consecutive_failures": self.consecutive_failures,
            "threshold": self.threshold,
            "last_failure_at": self.last_failure_at,
            "last_reason": self.last_reason,
            "should_emergency_stop": self.should_emergency_stop(),
            # Phase 89-β: drift 関連
            "consecutive_drift_detections": self.consecutive_drift_detections,
            "drift_threshold": self._drift_consecutive_threshold,
            "last_drift_at": self.last_drift_at,
            "reference_features_count": len(self._reference_distribution),
            # Phase 90γ-①: Drift 検出構造修正の状態
            "reference_initialized_at": (
                self._reference_initialized_at.isoformat()
                if self._reference_initialized_at
                else None
            ),
            "drift_exclude_features_count": len(self._drift_exclude_features),
            "drift_reference_reset_hours": self._drift_reference_reset_hours,
        }

    # ========================================
    # Phase 89-β: Drift 検出 (KS テスト + 連続検知)
    # ========================================

    def record_feature_distribution(self, features: Any) -> bool:
        """
        Phase 89-β: 直近サイクルの特徴量分布を蓄積し、reference との KS テストで drift 判定.

        Args:
            features: DataFrame (rows=samples, cols=feature_names) or dict (name -> values)

        Returns:
            この呼び出しで drift が検出されたかどうか
        """
        feature_values = self._extract_feature_values(features)
        if not feature_values:
            return False

        # Phase 90γ-①: reference 分布の期限切れ判定（古い reference との永続乖離を防止）
        now = datetime.now(timezone.utc)
        reference_expired = (
            self._reference_initialized_at is not None
            and self._drift_reference_reset_hours > 0
            and (now - self._reference_initialized_at).total_seconds()
            > self._drift_reference_reset_hours * 3600.0
        )

        # 初回呼び出し or 期限切れ: reference として保存（または reset）
        if not self._reference_distribution or reference_expired:
            action = "reset" if reference_expired else "初期化"
            self._reference_distribution = {}
            self._recent_distribution.clear()
            # Phase 90γ-① fix: reset 時は古い drift カウンタを無効化（新 reference に対しては仕切り直し）
            # 古い reference に対する drift 検出結果は新 reference では意味を持たないため
            if reference_expired and self.consecutive_drift_detections > 0:
                self.logger.warning(
                    f"Phase 90γ-①: reset に伴い drift カウンタクリア "
                    f"(was consecutive={self.consecutive_drift_detections}, "
                    f"last_drift_at={self.last_drift_at})"
                )
                self.consecutive_drift_detections = 0
                self.last_drift_at = None
            for name, values in feature_values.items():
                self._reference_distribution[name] = list(values)[-self._drift_window :]
            self._reference_initialized_at = now
            # Phase 90γ-① fix: reset イベントは本番 LOG_LEVEL=WARNING で観測可能にする
            # 初回起動時の初期化は INFO 維持（本番では取り込まれないが想定通り）
            log_method = self.logger.warning if reference_expired else self.logger.info
            log_method(
                f"Phase 90γ-①: drift 検出用 reference 分布{action} "
                f"(features={len(self._reference_distribution)}, "
                f"window={self._drift_window}, reset_hours={self._drift_reference_reset_hours})"
            )
            # Phase 90γ-①: 初期化時刻を永続化（再起動跨ぎで reset 期限を保持）
            self._save_state()
            return False

        # recent buffer 更新
        for name, values in feature_values.items():
            buf = self._recent_distribution.setdefault(name, deque(maxlen=self._drift_window))
            buf.extend(values)

        # サンプル数が十分か（reference と recent の両方が一定以上）
        if any(len(buf) < self._drift_window // 4 for buf in self._recent_distribution.values()):
            return False

        # KS テストで drift 判定
        # Phase 89 H4: 有意特徴量数 >= significant_feature_min で「真の drift」とみなす
        drift_features = self._detect_drift_with_ks()
        if len(drift_features) >= self._drift_significant_feature_min:
            self.consecutive_drift_detections += 1
            self.last_drift_at = datetime.now(timezone.utc).isoformat()
            self.logger.warning(
                f"⚠️ Phase 89-β: Drift 検出 - features={drift_features[:10]}"
                f"{'...' if len(drift_features) > 10 else ''} "
                f"(count={len(drift_features)}>={self._drift_significant_feature_min}, "
                f"consecutive={self.consecutive_drift_detections}/{self._drift_consecutive_threshold})"
            )
            self._save_state()

            # Phase 89 H10: 連続 drift が閾値到達で Auto Retraining 起動
            if (
                self._drift_auto_retraining
                and self.consecutive_drift_detections >= self._drift_consecutive_threshold
            ):
                try:
                    triggered = self.trigger_retraining(event_type="ml-drift-detected")
                    self.logger.info(
                        f"Phase 89 H10: drift 連続 {self.consecutive_drift_detections}回 → "
                        f"Auto Retraining trigger={'成功' if triggered else 'スキップ/失敗'}"
                    )
                except Exception as e:
                    self.logger.warning(f"Phase 89 H10: Auto Retraining 呼び出し例外: {e}")
            return True

        # 有意特徴量が下限未満（偽陽性 or 局所変動）→ drift 判定せず・カウンタ維持
        if drift_features:
            self.logger.info(
                f"Phase 89 H4: 有意特徴量 {len(drift_features)} 個 "
                f"< {self._drift_significant_feature_min} → drift 未判定（偽陽性抑制）"
            )
            return False

        # drift 解消（連続カウントリセット）
        if self.consecutive_drift_detections > 0:
            self.logger.info(
                f"✅ Phase 89-β: Drift 解消 "
                f"(was consecutive={self.consecutive_drift_detections})"
            )
            self.consecutive_drift_detections = 0
            self._save_state()
        return False

    def _extract_feature_values(self, features: Any) -> Dict[str, List[float]]:
        """DataFrame/dict から特徴量名 -> 値リストの辞書を作る.

        Phase 90γ-①: ``_drift_exclude_features`` に指定された特徴量は除外する.
        価格絶対値（OHLCV）・MA・BB のような「時間と共に変動するのが当然」な特徴量を
        drift 比較対象から外し、市場の自然変動による誤検知を抑制する.
        """
        result: Dict[str, List[float]] = {}
        try:
            import pandas as pd  # 遅延 import

            if isinstance(features, pd.DataFrame):
                result = {
                    col: features[col].dropna().astype(float).tolist()
                    for col in features.columns
                    if features[col].dtype.kind in "fi"  # 数値型のみ
                }
        except ImportError:
            pass

        if not result and isinstance(features, dict):
            for name, values in features.items():
                try:
                    result[name] = [float(v) for v in values]
                except (TypeError, ValueError):
                    continue

        # Phase 90γ-①: 除外リスト適用（価格絶対値系を drift 比較から除外）
        if self._drift_exclude_features and result:
            result = {k: v for k, v in result.items() if k not in self._drift_exclude_features}
        return result

    def _detect_drift_with_ks(self) -> List[str]:
        """reference と recent で 2-sample KS テスト → 有意な特徴量を返す.

        Phase 89 H4: Bonferroni 補正で多重検定の偽陽性を抑制。
        有効有意水準 = ks_alpha / 比較した特徴量数。
        """
        try:
            from scipy.stats import ks_2samp
        except ImportError:
            self.logger.warning("scipy 未インストール → KS テスト不可、drift 検出スキップ")
            return []

        # Bonferroni 補正: 共通分布特徴量数で有意水準を分割
        comparable = [
            name
            for name in self._recent_distribution.keys()
            if len(self._reference_distribution.get(name, [])) >= 10
            and len(self._recent_distribution[name]) >= 10
        ]
        n_tests = max(1, len(comparable))
        effective_alpha = self._drift_ks_alpha / n_tests

        drift_features: List[str] = []
        for name in comparable:
            reference = self._reference_distribution[name]
            recent_buf = self._recent_distribution[name]
            try:
                stat, p_value = ks_2samp(reference, list(recent_buf))
            except Exception:
                continue
            if math.isfinite(p_value) and p_value < effective_alpha:
                drift_features.append(name)
        return drift_features

    def reset_drift_state(self) -> None:
        """テスト用: drift カウントと reference をリセット."""
        self.consecutive_drift_detections = 0
        self.last_drift_at = None
        self._reference_distribution.clear()
        self._recent_distribution.clear()
        # Phase 90γ-①: reference 初期化時刻もクリア
        self._reference_initialized_at = None

    # ========================================
    # Phase 89-γ: Auto Retraining trigger
    # ========================================

    def trigger_retraining(
        self,
        github_owner: Optional[str] = None,
        github_repo: Optional[str] = None,
        github_token: Optional[str] = None,
        cooldown_hours: Optional[int] = None,
        event_type: str = "ml-drift-detected",
    ) -> bool:
        """
        Phase 89-γ: GitHub Actions repository_dispatch でモデル再学習を起動.

        Args:
            github_owner: リポジトリオーナー（None なら env GITHUB_REPO_OWNER）
            github_repo: リポジトリ名（None なら env GITHUB_REPO_NAME）
            github_token: PAT（None なら env GITHUB_REPO_DISPATCH_TOKEN）
            cooldown_hours: 連続トリガ防止クールダウン（None なら config or 24h）
            event_type: dispatch event type

        Returns:
            True: トリガ送信成功 / False: cooldown 中 or 失敗
        """
        import os

        cooldown = cooldown_hours
        if cooldown is None:
            try:
                from ..config import get_threshold as _gt

                cooldown = int(_gt("ml.drift.retrain_cooldown_hours", 24))
            except Exception:
                cooldown = 24

        # クールダウン判定（Firestore に保存された last_retrain_trigger_at と比較）
        last_at_str = self._get_last_retrain_trigger()
        if last_at_str:
            try:
                last_at = datetime.fromisoformat(last_at_str)
                # naive datetime も比較できるよう tz 統一
                if last_at.tzinfo is None:
                    last_at = last_at.replace(tzinfo=timezone.utc)
                elapsed_hours = (datetime.now(timezone.utc) - last_at).total_seconds() / 3600.0
                if elapsed_hours < cooldown:
                    self.logger.info(
                        f"Phase 89-γ Auto Retraining cooldown 中 "
                        f"(経過 {elapsed_hours:.1f}h / 必要 {cooldown}h) → スキップ"
                    )
                    return False
            except (ValueError, TypeError):
                pass

        owner = github_owner or os.environ.get("GITHUB_REPO_OWNER")
        repo = github_repo or os.environ.get("GITHUB_REPO_NAME")
        token = github_token or os.environ.get("GITHUB_REPO_DISPATCH_TOKEN")

        if not owner or not repo or not token:
            self.logger.warning(
                "Phase 89-γ Auto Retraining: GitHub 設定不足 "
                "(owner/repo/token のいずれかが未設定) → スキップ"
            )
            return False

        try:
            import requests

            response = requests.post(
                f"https://api.github.com/repos/{owner}/{repo}/dispatches",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                },
                json={"event_type": event_type},
                timeout=10,
            )
            if 200 <= response.status_code < 300:
                self._save_last_retrain_trigger()
                self.logger.critical(
                    f"🚨 Phase 89-γ Auto Retraining triggered: "
                    f"{owner}/{repo} event_type={event_type}"
                )
                return True
            else:
                self.logger.warning(
                    f"Phase 89-γ Auto Retraining HTTP {response.status_code}: "
                    f"{response.text[:200]}"
                )
                return False
        except Exception as e:
            self.logger.warning(f"Phase 89-γ Auto Retraining 失敗: {e}")
            return False

    def _get_last_retrain_trigger(self) -> Optional[str]:
        """Firestore から最終リトレイン trigger 時刻を取得."""
        if self.persistence is None:
            return getattr(self, "_last_retrain_at", None)
        try:
            state = self.persistence.load(self.COLLECTION, self.DOC_ID) or {}
            return state.get("last_retrain_trigger_at")
        except Exception:
            return None

    def _save_last_retrain_trigger(self) -> None:
        """Firestore に最終リトレイン trigger 時刻を保存."""
        now_iso = datetime.now(timezone.utc).isoformat()
        self._last_retrain_at = now_iso
        if self.persistence is None:
            return
        try:
            # 既存 state を読んで last_retrain_trigger_at を追記
            state = self.persistence.load(self.COLLECTION, self.DOC_ID) or {}
            state["last_retrain_trigger_at"] = now_iso
            self.persistence.save(self.COLLECTION, self.DOC_ID, state)
        except Exception as e:
            self.logger.warning(f"Phase 89-γ trigger 時刻保存失敗: {e}")

    # ========================================
    # Internal persistence
    # ========================================

    def _save_state(self) -> None:
        if self.persistence is None:
            return
        try:
            # 既存 state を読んで Auto Retraining trigger 時刻を保持しつつ merge save
            existing = self.persistence.load(self.COLLECTION, self.DOC_ID) or {}
            merged = dict(existing)
            merged.update(
                {
                    "consecutive_failures": self.consecutive_failures,
                    "last_failure_at": self.last_failure_at,
                    "last_reason": self.last_reason,
                    "threshold": self.threshold,
                    # Phase 89 H1: drift state も永続化（Cloud Run 再起動で reset しない）
                    "consecutive_drift_detections": self.consecutive_drift_detections,
                    "last_drift_at": self.last_drift_at,
                    # Phase 90γ-①: reference 初期化時刻（再起動跨ぎで reset 期限を保持）
                    "reference_initialized_at": (
                        self._reference_initialized_at.isoformat()
                        if self._reference_initialized_at
                        else None
                    ),
                }
            )
            self.persistence.save(self.COLLECTION, self.DOC_ID, merged)
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
            # Phase 89 H1: drift カウンタの復元（再起動跨ぎで保持）
            self.consecutive_drift_detections = int(
                state.get("consecutive_drift_detections", 0) or 0
            )
            self.last_drift_at = state.get("last_drift_at")
            # Phase 90γ-①: reference 初期化時刻の復元（reset 期限を再起動跨ぎで保持）
            ref_init_at = state.get("reference_initialized_at")
            if ref_init_at:
                try:
                    parsed = datetime.fromisoformat(ref_init_at)
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=timezone.utc)
                    self._reference_initialized_at = parsed
                except (ValueError, TypeError):
                    self._reference_initialized_at = None
            last_retrain = state.get("last_retrain_trigger_at")
            if last_retrain:
                self._last_retrain_at = last_retrain
            if self.consecutive_failures > 0:
                self.logger.info(
                    f"Phase 87 C4: MLHealthMonitor 状態復元 - "
                    f"consecutive={self.consecutive_failures}/{self.threshold}, "
                    f"last_reason={self.last_reason}"
                )
            if self.consecutive_drift_detections > 0:
                self.logger.info(
                    f"Phase 89 H1: drift カウンタ復元 - "
                    f"consecutive={self.consecutive_drift_detections}/"
                    f"{self._drift_consecutive_threshold}, "
                    f"last_drift_at={self.last_drift_at}"
                )
        except Exception as e:
            self.logger.warning(f"⚠️ Phase 87 C4: MLHealthMonitor load error: {e}")
