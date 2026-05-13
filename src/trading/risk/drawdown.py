"""
ドローダウン管理システム - Phase 64

Phase 26完了・Phase 36 Graceful Degradation統合：
- 最大ドローダウン監視（20%制限）
- 連続損失管理（8回制限・Phase 26最適化）
- クールダウン機能（6時間・Phase 26短縮）
- 状態永続化（Local + GCS）
"""

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from ...core.config import get_threshold
from ...core.logger import get_logger


class TradingStatus(Enum):
    """取引状態."""

    ACTIVE = "active"
    PAUSED_DRAWDOWN = "paused_drawdown"
    PAUSED_CONSECUTIVE_LOSS = "paused_consecutive_loss"
    EMERGENCY_STOP = "emergency_stop"
    # Phase 87 Stage 3 H8: 段階的復帰中（クールダウン解除直後・小サイズで検証取引）
    RECOVERY_TESTING = "recovery_testing"


@dataclass
class TradeRecord:
    """取引記録."""

    timestamp: datetime
    profit_loss: float
    strategy: str


class DrawdownManager:
    """
    ドローダウン管理システム

    機能:
    - 最大ドローダウン監視
    - 連続損失カウント
    - クールダウン期間管理
    - 状態永続化（ローカル + GCS）
    """

    def __init__(
        self,
        max_drawdown_ratio: float = None,
        consecutive_loss_limit: int = None,
        cooldown_hours: float = None,
        config: Dict[str, Any] = None,
        mode: str = "live",
    ):
        """
        ドローダウンマネージャー初期化

        Args:
            max_drawdown_ratio: 最大ドローダウン比率
            consecutive_loss_limit: 連続損失制限
            cooldown_hours: クールダウン時間（時間）
            config: 設定辞書
            mode: 実行モード（paper/live/backtest）
        """
        self.max_drawdown_ratio = max_drawdown_ratio or get_threshold(
            "risk.drawdown_manager.max_drawdown_ratio", 0.2
        )
        self.consecutive_loss_limit = consecutive_loss_limit or get_threshold(
            "risk.drawdown_manager.consecutive_loss_limit", 8
        )
        self.cooldown_hours = cooldown_hours or get_threshold(
            "risk.drawdown_manager.cooldown_hours", 6
        )
        self.mode = mode
        self.config = config or {}

        # 日次/週次損失制限（Phase 70）
        self.daily_loss_limit = get_threshold("risk.daily_loss_limit", 0.05)
        self.weekly_loss_limit = get_threshold("risk.weekly_loss_limit", 0.1)

        # 状態変数
        self.initial_balance = 10000.0
        self.peak_balance = 10000.0
        self.current_balance = 10000.0
        self.consecutive_losses = 0
        self.trading_status = TradingStatus.ACTIVE
        self.cooldown_until: Optional[datetime] = None
        self.trade_history: List[TradeRecord] = []

        # Phase 87 Stage 3 H8: 段階的復帰用カウンタ
        # recovery_win_streak: RECOVERY_TESTING 中の連勝数（required_wins 到達で ACTIVE 復帰）
        # recovery_failure_count: cooldown→RECOVERY_TESTING→cooldown のループ回数
        #   max_recovery_failures 回到達で EMERGENCY_STOP（無限ループ防止）
        self.recovery_win_streak: int = 0
        self.recovery_failure_count: int = 0

        self.logger = get_logger()

        # 状態永続化設定
        persistence_config = self.config.get("persistence", {})
        self.local_state_path = persistence_config.get("local_path", "data/drawdown_state.json")
        self.gcs_bucket = persistence_config.get("gcs_bucket")
        self.gcs_path = persistence_config.get("gcs_path")

        # Phase 87 H5: Firestore 永続化（Cloud Run 再起動時の連敗カウント保護）
        # バックテスト時は無効、ライブ/ペーパー時のみ初期化
        self.firestore_client = None
        if mode != "backtest":
            try:
                from ...core.persistence import FirestoreStateClient  # type: ignore

                self.firestore_client = FirestoreStateClient(
                    local_fallback_dir=os.path.dirname(self.local_state_path) or "data"
                )
            except Exception as e:
                self.logger.warning(f"Phase 87 H5: FirestoreStateClient init failed: {e}")

        # 状態復元
        self._load_state()

    def initialize_balance(self, initial_balance: float) -> None:
        """初期残高設定"""
        self.initial_balance = initial_balance
        self.peak_balance = initial_balance
        self.current_balance = initial_balance
        self.logger.info(f"初期残高設定: ¥{initial_balance:,.0f}")

    def update_balance(self, current_balance: float) -> None:
        """現在残高更新"""
        self.current_balance = current_balance

        # ピーク残高更新
        if current_balance > self.peak_balance:
            self.peak_balance = current_balance
            self.logger.debug(f"ピーク残高更新: ¥{self.peak_balance:,.0f}")

    def record_trade_result(
        self, profit_loss: float, strategy: str = "default", current_time=None
    ) -> None:
        """
        取引結果記録（Phase 52.2: バックテスト時刻対応）
        Phase 87 Stage 3 H8: RECOVERY_TESTING 状態時は record_recovery_trade に委譲

        Args:
            profit_loss: 損益（正値=利益、負値=損失）
            strategy: 戦略名
            current_time: 取引時刻（datetime）。
                         None時はdatetime.now()使用（本番モード）。
                         バックテスト時は取引発生時刻を指定。
        """
        # Phase 87 H8: 段階的復帰中は専用ロジックへ委譲
        if self.trading_status == TradingStatus.RECOVERY_TESTING:
            return self.record_recovery_trade(profit_loss, current_time=current_time)

        try:
            # Phase 52.2: 基準時刻決定（本番時は現在時刻、バックテスト時は指定時刻）
            now = current_time if current_time is not None else datetime.now()

            # 取引記録追加
            trade_record = TradeRecord(
                timestamp=now,
                profit_loss=profit_loss,
                strategy=strategy,
            )
            self.trade_history.append(trade_record)

            # 連続損失カウント更新
            if profit_loss < 0:
                self.consecutive_losses += 1
                self.logger.warning(
                    f"連続損失更新: {self.consecutive_losses}/{self.consecutive_loss_limit}"
                )
            else:
                if self.consecutive_losses > 0:
                    self.logger.info("連続損失リセット（勝ち取引）")
                self.consecutive_losses = 0

            # ドローダウンチェック
            current_drawdown = self.calculate_current_drawdown()
            if current_drawdown >= self.max_drawdown_ratio:
                self._enter_cooldown(TradingStatus.PAUSED_DRAWDOWN, current_time=now)
            elif self.consecutive_losses >= self.consecutive_loss_limit:
                self._enter_cooldown(TradingStatus.PAUSED_CONSECUTIVE_LOSS, current_time=now)

            # 状態保存
            self._save_state()

        except Exception as e:
            self.logger.error(f"取引結果記録エラー: {e}")

    def calculate_current_drawdown(self) -> float:
        """現在のドローダウン比率計算"""
        if self.peak_balance <= 0:
            return 0.0

        drawdown = (self.peak_balance - self.current_balance) / self.peak_balance
        return max(0.0, drawdown)

    def check_trading_allowed(self, current_time=None) -> bool:
        """
        取引許可チェック（Phase 52.2: バックテスト時刻対応）

        Args:
            current_time: 判定基準時刻（datetime）。
                         None時はdatetime.now()使用（本番モード）。
                         バックテスト時は過去のタイムスタンプを指定。

        Returns:
            bool: 取引許可の場合True
        """
        # Phase 52.2: 基準時刻決定（本番時は現在時刻、バックテスト時は指定時刻）
        now = current_time if current_time is not None else datetime.now()

        # クールダウン期間チェック
        if self.cooldown_until and now < self.cooldown_until:
            remaining = (self.cooldown_until - now).total_seconds() / 3600
            self.logger.debug(f"クールダウン中: 残り{remaining:.1f}時間")
            return False

        # クールダウン解除
        if self.cooldown_until and now >= self.cooldown_until:
            self._exit_cooldown()

        # Phase 87 Stage 3-R C: RECOVERY_TESTING も取引許可（サイズは
        # get_position_size_multiplier() で 0.5 倍に縮小される設計）
        return self.trading_status in (TradingStatus.ACTIVE, TradingStatus.RECOVERY_TESTING)

    def _enter_cooldown(self, status: TradingStatus, current_time=None) -> None:
        """
        クールダウン開始（Phase 52.2: バックテスト時刻対応）

        Args:
            status: 取引ステータス
            current_time: 基準時刻（datetime）。
                         None時はdatetime.now()使用（本番モード）。
                         バックテスト時はクールダウン開始時刻を指定。
        """
        # Phase 52.2: 基準時刻決定（本番時は現在時刻、バックテスト時は指定時刻）
        now = current_time if current_time is not None else datetime.now()

        self.trading_status = status
        self.cooldown_until = now + timedelta(hours=self.cooldown_hours)

        self.logger.warning(
            f"クールダウン開始: {status.value}, "
            f"解除予定: {self.cooldown_until.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        # 状態保存
        self._save_state()

    def record_recovery_trade(self, profit_loss: float, current_time=None) -> None:
        """
        Phase 87 Stage 3 H8: RECOVERY_TESTING 中の取引結果記録

        - 利益: recovery_win_streak += 1 → required_wins 到達で ACTIVE 復帰
                + consecutive_losses=0 + recovery_failure_count=0 リセット
        - 損失: recovery_win_streak=0、recovery_failure_count += 1
                → 即 cooldown 再開（PAUSED_CONSECUTIVE_LOSS）
                → max_recovery_failures 到達で EMERGENCY_STOP（無限ループ防止）

        Args:
            profit_loss: 損益（正値=利益、負値=損失）
            current_time: 取引時刻
        """
        try:
            now = current_time if current_time is not None else datetime.now()
            required_wins = int(get_threshold("risk.drawdown_manager.recovery_required_wins", 2))
            max_failures = int(get_threshold("risk.drawdown_manager.max_recovery_failures", 3))

            # 取引履歴に追加（既存 record_trade_result と同等の記録）
            self.trade_history.append(
                TradeRecord(timestamp=now, profit_loss=profit_loss, strategy="recovery")
            )

            if profit_loss > 0:
                self.recovery_win_streak += 1
                self.logger.info(
                    f"✅ Phase 87 H8: RECOVERY 勝利 "
                    f"({self.recovery_win_streak}/{required_wins})"
                )
                if self.recovery_win_streak >= required_wins:
                    # 完全復帰
                    self.logger.info(
                        f"🟢 Phase 87 H8: RECOVERY_TESTING → ACTIVE 復帰 "
                        f"(連勝={self.recovery_win_streak}件)"
                    )
                    self.trading_status = TradingStatus.ACTIVE
                    self.consecutive_losses = 0
                    self.recovery_win_streak = 0
                    self.recovery_failure_count = 0
            else:
                # 損失 → 再 cooldown
                self.recovery_win_streak = 0
                self.recovery_failure_count += 1
                self.logger.warning(
                    f"🚫 Phase 87 H8: RECOVERY 失敗 "
                    f"(failure_count={self.recovery_failure_count}/{max_failures}) → 再cooldown"
                )

                if self.recovery_failure_count >= max_failures:
                    # 無限ループ防止: 連続失敗で EMERGENCY_STOP
                    self.set_emergency_stop(f"recovery_loop_{self.recovery_failure_count}times")
                else:
                    # 通常の再cooldown
                    self._enter_cooldown(TradingStatus.PAUSED_CONSECUTIVE_LOSS, current_time=now)

            self._save_state()
        except Exception as e:
            self.logger.error(f"Phase 87 H8: record_recovery_trade エラー: {e}")

    def set_emergency_stop(self, reason: str) -> None:
        """
        Phase 87 Stage 2-R1: 緊急停止状態へ遷移

        サーキットブレーカー（C4 MLHealthMonitor 等）からの呼び出しで、
        TradingStatus を EMERGENCY_STOP に切り替え状態を永続化する。
        cooldown と異なり時刻ベースの自動解除はせず、手動介入が必要。

        Args:
            reason: 緊急停止の理由（ログ・永続化に記録）
        """
        if self.trading_status == TradingStatus.EMERGENCY_STOP:
            return  # 既に緊急停止中（重複ログ抑制）
        self.trading_status = TradingStatus.EMERGENCY_STOP
        self.logger.critical(f"🚨🚨 Phase 87 Stage 2-R1: 緊急停止状態へ遷移 - reason={reason}")
        self._save_state()

    def _exit_cooldown(self) -> None:
        """クールダウン解除（Phase 87 Stage 3 H8: 段階的復帰へ）

        旧実装は即 ACTIVE + consecutive_losses=0 リセット → 連敗からの即時フル復帰だった。
        Phase 87 H8 では RECOVERY_TESTING 状態を経由し、小サイズで取引検証してから
        ACTIVE に戻る設計に変更。
        - trading_status: RECOVERY_TESTING
        - consecutive_losses: 維持（recovery 失敗時の判定材料）
        - recovery_win_streak: 0 リセット（新しい検証セッションの開始）
        """
        self.trading_status = TradingStatus.RECOVERY_TESTING
        self.cooldown_until = None
        self.recovery_win_streak = 0
        self.logger.info(
            f"クールダウン解除→Phase 87 H8: RECOVERY_TESTING 開始 "
            f"(連敗={self.consecutive_losses}件保持、サイズ縮小で検証取引へ)"
        )

        # 状態保存
        self._save_state()

    def get_daily_pnl(self, current_time: Optional[datetime] = None) -> float:
        """
        Phase 70: 日次PnL計算

        Args:
            current_time: 基準時刻（None時はdatetime.now()）

        Returns:
            float: 本日の累計損益
        """
        now = current_time if current_time is not None else datetime.now()
        today = now.date()
        daily_pnl = sum(t.profit_loss for t in self.trade_history if t.timestamp.date() == today)
        return daily_pnl

    def get_weekly_pnl(self, current_time: Optional[datetime] = None) -> float:
        """
        Phase 70: 週次PnL計算

        Args:
            current_time: 基準時刻（None時はdatetime.now()）

        Returns:
            float: 今週の累計損益
        """
        now = current_time if current_time is not None else datetime.now()
        week_start = now - timedelta(days=now.weekday())
        week_start_date = week_start.date()
        weekly_pnl = sum(
            t.profit_loss for t in self.trade_history if t.timestamp.date() >= week_start_date
        )
        return weekly_pnl

    def check_daily_loss_limit(self, current_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Phase 70: 日次/週次損失上限チェック

        Args:
            current_time: 基準時刻

        Returns:
            Dict: {"allowed": bool, "reason": str, "daily_pnl": float, ...}
        """
        daily_pnl = self.get_daily_pnl(current_time)
        weekly_pnl = self.get_weekly_pnl(current_time)

        # 日次損失上限チェック（初期残高ベース）
        daily_loss_abs = self.initial_balance * self.daily_loss_limit
        if daily_pnl <= -daily_loss_abs:
            return {
                "allowed": False,
                "reason": (
                    f"日次損失上限到達: {daily_pnl:.0f}円 <= -{daily_loss_abs:.0f}円 "
                    f"({self.daily_loss_limit * 100:.0f}%)"
                ),
                "daily_pnl": daily_pnl,
                "weekly_pnl": weekly_pnl,
            }

        # 週次損失上限チェック
        weekly_loss_abs = self.initial_balance * self.weekly_loss_limit
        if weekly_pnl <= -weekly_loss_abs:
            return {
                "allowed": False,
                "reason": (
                    f"週次損失上限到達: {weekly_pnl:.0f}円 <= -{weekly_loss_abs:.0f}円 "
                    f"({self.weekly_loss_limit * 100:.0f}%)"
                ),
                "daily_pnl": daily_pnl,
                "weekly_pnl": weekly_pnl,
            }

        return {
            "allowed": True,
            "reason": "日次/週次損失上限内",
            "daily_pnl": daily_pnl,
            "weekly_pnl": weekly_pnl,
        }

    def get_position_size_multiplier(self) -> float:
        """
        Phase 70: 連敗に応じたポジションサイズ縮小倍率
        Phase 87 Stage 3 H8: RECOVERY_TESTING 中は固定縮小（デフォルト 0.5）

        - 連敗5回: 50%
        - 連敗6回: 40%
        - 連敗7回: 25%
        - 連敗8回以上: 0%（完全停止はcheck_trading_allowedで処理）

        Phase 83C: 閾値跨ぎ時の倍率変化を WARNING ログで記録（運用観測性向上）

        Returns:
            float: ポジションサイズ倍率（0.0-1.0）
        """
        # Phase 87 H8: RECOVERY_TESTING 中は連敗カウントによらず固定倍率
        if self.trading_status == TradingStatus.RECOVERY_TESTING:
            recovery_multiplier = float(
                get_threshold("risk.drawdown_manager.recovery_position_multiplier", 0.5)
            )
            return recovery_multiplier

        if self.consecutive_losses >= 8:
            multiplier = 0.0
        elif self.consecutive_losses >= 7:
            multiplier = 0.25
        elif self.consecutive_losses >= 6:
            multiplier = 0.4
        elif self.consecutive_losses >= 5:
            multiplier = 0.5
        else:
            multiplier = 1.0

        # Phase 83C: 倍率が前回と変わったら WARNING（閾値跨ぎを観測）
        if not hasattr(self, "_last_position_multiplier"):
            self._last_position_multiplier = 1.0
        if multiplier != self._last_position_multiplier:
            self.logger.warning(
                f"⚠️ Phase 83C: ポジションサイズ倍率変化 - "
                f"連敗={self.consecutive_losses}回, "
                f"倍率={self._last_position_multiplier:.2f} → {multiplier:.2f}"
            )
            self._last_position_multiplier = multiplier

        return multiplier

    def get_drawdown_statistics(self) -> Dict[str, Any]:
        """ドローダウン統計取得"""
        daily_loss_check = self.check_daily_loss_limit()
        return {
            "initial_balance": self.initial_balance,
            "peak_balance": self.peak_balance,
            "current_balance": self.current_balance,
            "current_drawdown": self.calculate_current_drawdown(),
            "max_drawdown_ratio": self.max_drawdown_ratio,
            "consecutive_losses": self.consecutive_losses,
            "consecutive_loss_limit": self.consecutive_loss_limit,
            "trading_status": self.trading_status.value,
            "trading_allowed": self.check_trading_allowed(),
            "cooldown_until": (self.cooldown_until.isoformat() if self.cooldown_until else None),
            "daily_pnl": daily_loss_check.get("daily_pnl", 0.0),
            "weekly_pnl": daily_loss_check.get("weekly_pnl", 0.0),
            "position_size_multiplier": self.get_position_size_multiplier(),
        }

    def _save_state(self) -> None:
        """状態保存（Phase 87 H5: Firestore 優先・ローカル JSON はフォールバック）"""
        try:
            # バックテストモードでは保存しない
            if self.mode == "backtest":
                return

            state = {
                "initial_balance": self.initial_balance,
                "peak_balance": self.peak_balance,
                "current_balance": self.current_balance,
                "consecutive_losses": self.consecutive_losses,
                "trading_status": self.trading_status.value,
                "cooldown_until": (
                    self.cooldown_until.isoformat() if self.cooldown_until else None
                ),
                # Phase 87 Stage 3 H8: 段階的復帰カウンタ
                "recovery_win_streak": self.recovery_win_streak,
                "recovery_failure_count": self.recovery_failure_count,
                "last_updated": datetime.now().isoformat(),
            }

            # Phase 87 H5: Firestore に優先保存（Cloud Run ephemeral FS から保護）
            saved_to_firestore = False
            if self.firestore_client is not None and self.firestore_client.enabled:
                try:
                    self.firestore_client.save("drawdown_state", "main", state)
                    saved_to_firestore = True
                    self.logger.debug("Phase 87 H5: Firestore に状態保存完了")
                except Exception as e:
                    self.logger.warning(f"Phase 87 H5: Firestore save 失敗: {e}")

            # ローカル保存（Firestore 不通時のフォールバック + バックアップ）
            # 既存ローカル形式（flat state）を維持してテスト互換
            if not saved_to_firestore:
                os.makedirs(os.path.dirname(self.local_state_path), exist_ok=True)
                with open(self.local_state_path, "w") as f:
                    json.dump(state, f, indent=2)
                self.logger.debug(f"状態保存完了（ローカル）: {self.local_state_path}")

        except Exception as e:
            self.logger.error(f"状態保存エラー: {e}")

    def _load_state(self) -> None:
        """状態復元（Phase 87 H5: Firestore 優先・ローカル JSON はフォールバック）"""
        try:
            # バックテストモードでは復元しない
            if self.mode == "backtest":
                return

            state = None

            # Phase 87 H5: Firestore から優先復元
            if self.firestore_client is not None and self.firestore_client.enabled:
                try:
                    state = self.firestore_client.load("drawdown_state", "main")
                    if state:
                        self.logger.info("Phase 87 H5: Firestore から状態復元成功")
                except Exception as e:
                    self.logger.warning(f"Phase 87 H5: Firestore load 失敗: {e}")

            # ローカルフォールバック
            if state is None:
                if not os.path.exists(self.local_state_path):
                    self.logger.info("状態ファイル未存在、新規作成")
                    return

                with open(self.local_state_path, "r") as f:
                    state = json.load(f)
                self.logger.info(f"状態復元完了（ローカル）: {self.local_state_path}")

            if not state:
                return

            self.initial_balance = state.get("initial_balance", 10000.0)
            self.peak_balance = state.get("peak_balance", 10000.0)
            self.current_balance = state.get("current_balance", 10000.0)
            self.consecutive_losses = state.get("consecutive_losses", 0)
            self.trading_status = TradingStatus(
                state.get("trading_status", TradingStatus.ACTIVE.value)
            )

            cooldown_until_str = state.get("cooldown_until")
            if cooldown_until_str:
                self.cooldown_until = datetime.fromisoformat(cooldown_until_str)

            # Phase 87 Stage 3 H8: 段階的復帰カウンタ復元（後方互換: 旧 state には存在しない）
            # Stage 3-R E: 冗長な `or 0` 削除（state.get(..., 0) で十分）
            self.recovery_win_streak = int(state.get("recovery_win_streak", 0))
            self.recovery_failure_count = int(state.get("recovery_failure_count", 0))

        except Exception as e:
            self.logger.error(f"状態復元エラー: {e}")
