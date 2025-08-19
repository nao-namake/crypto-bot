"""
ドローダウン管理モジュール

Phase 6リスク管理層の重要コンポーネント。資金保全を最優先とし、
最大ドローダウン20%制限と連続損失時の自動停止機能を提供します。

主要機能:
- リアルタイムドローダウン監視
- 連続損失カウントと自動停止
- Discord通知連携
- 取引許可判定.
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..core.logger import get_logger


class TradingStatus(Enum):
    """取引状態."""

    ACTIVE = "active"
    PAUSED_DRAWDOWN = "paused_drawdown"
    PAUSED_CONSECUTIVE_LOSS = "paused_consecutive_loss"
    PAUSED_MANUAL = "paused_manual"


@dataclass
class DrawdownSnapshot:
    """ドローダウン記録用スナップショット."""

    timestamp: datetime
    current_balance: float
    peak_balance: float
    drawdown_ratio: float
    consecutive_losses: int
    status: TradingStatus


@dataclass
class TradingSession:
    """取引セッション記録."""

    start_time: datetime
    end_time: Optional[datetime]
    reason: str
    initial_balance: float
    final_balance: Optional[float]
    total_trades: int
    profitable_trades: int


class DrawdownManager:
    """
    ドローダウン管理システム

    資金保全を最優先とした取引制御を行います。
    設定可能な制限:
    - 最大ドローダウン率（デフォルト20%）
    - 連続損失限界（デフォルト5回）
    - 停止期間（デフォルト24時間）.
    """

    def __init__(
        self,
        max_drawdown_ratio: float = 0.20,
        consecutive_loss_limit: int = 5,
        cooldown_hours: int = 24,
        persistence_file: str = ".cache/data/drawdown_state.json",
    ):
        """
        ドローダウン管理器初期化

        Args:
            max_drawdown_ratio: 最大ドローダウン率（0.20 = 20%）
            consecutive_loss_limit: 連続損失制限回数
            cooldown_hours: 停止期間（時間）
            persistence_file: 状態永続化ファイル名.
        """
        self.max_drawdown_ratio = max_drawdown_ratio
        self.consecutive_loss_limit = consecutive_loss_limit
        self.cooldown_hours = cooldown_hours
        self.persistence_file = Path(persistence_file)
        # 親ディレクトリを確実に作成
        self.persistence_file.parent.mkdir(parents=True, exist_ok=True)

        # 状態管理
        self.current_balance = 0.0
        self.peak_balance = 0.0
        self.consecutive_losses = 0
        self.last_loss_time: Optional[datetime] = None
        self.trading_status = TradingStatus.ACTIVE
        self.pause_until: Optional[datetime] = None

        # 履歴管理
        self.drawdown_history: List[DrawdownSnapshot] = []
        self.trading_sessions: List[TradingSession] = []
        self.current_session: Optional[TradingSession] = None

        self.logger = get_logger()

        # 状態復元
        self._load_state()

    def initialize_balance(self, initial_balance: float) -> None:
        """
        初期残高設定

        Args:
            initial_balance: 初期残高.
        """
        try:
            if initial_balance <= 0:
                raise ValueError(f"無効な初期残高: {initial_balance}")

            self.current_balance = initial_balance

            # 新しいピークかチェック
            if initial_balance > self.peak_balance:
                self.peak_balance = initial_balance
                self.logger.info(
                    f"新しいピーク残高更新: {self.peak_balance:.2f}"
                )

            # 新セッション開始
            if self.current_session is None:
                self._start_new_session(initial_balance)

            self._save_state()

        except Exception as e:
            self.logger.error(f"初期残高設定エラー: {e}")

    def update_balance(self, new_balance: float) -> Tuple[float, bool]:
        """
        残高更新とドローダウン計算

        Args:
            new_balance: 新しい残高

        Returns:
            (現在のドローダウン率, 取引許可フラグ).
        """
        try:
            if new_balance < 0:
                self.logger.warning(f"残高が負値: {new_balance:.2f}")

            old_balance = self.current_balance
            self.current_balance = new_balance

            # ピーク更新チェック
            if new_balance > self.peak_balance:
                self.peak_balance = new_balance
                # ピーク更新時は連続損失リセット
                if self.consecutive_losses > 0:
                    self.logger.info(
                        f"ピーク更新により連続損失リセット: {self.consecutive_losses} -> 0"
                    )
                    self.consecutive_losses = 0
                    self.last_loss_time = None

            # ドローダウン計算
            current_drawdown = self.calculate_current_drawdown()

            # 取引許可判定
            trading_allowed = self.check_trading_allowed()

            # スナップショット記録
            snapshot = DrawdownSnapshot(
                timestamp=datetime.now(),
                current_balance=new_balance,
                peak_balance=self.peak_balance,
                drawdown_ratio=current_drawdown,
                consecutive_losses=self.consecutive_losses,
                status=self.trading_status,
            )
            self.drawdown_history.append(snapshot)

            # 履歴サイズ制限（直近1000件）
            if len(self.drawdown_history) > 1000:
                self.drawdown_history = self.drawdown_history[-1000:]

            self._save_state()

            self.logger.debug(
                f"残高更新: {old_balance:.2f} -> {new_balance:.2f}, "
                f"ドローダウン: {current_drawdown:.1%}, 取引許可: {trading_allowed}"
            )

            return current_drawdown, trading_allowed

        except Exception as e:
            self.logger.error(f"残高更新エラー: {e}")
            return 0.0, False

    def record_trade_result(
        self,
        profit_loss: float,
        strategy: str = "default",
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        取引結果記録と連続損失管理

        Args:
            profit_loss: 損益（正値=利益、負値=損失）
            strategy: 戦略名
            timestamp: 取引時刻（Noneの場合は現在時刻）.
        """
        try:
            if timestamp is None:
                timestamp = datetime.now()

            is_profitable = profit_loss > 0

            # セッション統計更新
            if self.current_session:
                self.current_session.total_trades += 1
                if is_profitable:
                    self.current_session.profitable_trades += 1

            if is_profitable:
                # 利益の場合は連続損失リセット
                if self.consecutive_losses > 0:
                    self.logger.info(
                        f"利益により連続損失リセット: {self.consecutive_losses} -> 0"
                    )
                    self.consecutive_losses = 0
                    self.last_loss_time = None

                    # 一時停止状態の場合は解除チェック
                    if (
                        self.trading_status
                        == TradingStatus.PAUSED_CONSECUTIVE_LOSS
                    ):
                        self._resume_trading("利益による連続損失解除")
            else:
                # 損失の場合は連続損失カウント
                self.consecutive_losses += 1
                self.last_loss_time = timestamp

                self.logger.warning(
                    f"連続損失カウント: {self.consecutive_losses}/{self.consecutive_loss_limit}, "
                    f"損失額: {profit_loss:.2f}"
                )

                # 連続損失制限チェック
                if self.consecutive_losses >= self.consecutive_loss_limit:
                    self._pause_trading_consecutive_loss()

            # 残高更新（仮想的な更新、実際の残高は外部から設定）
            estimated_balance = self.current_balance + profit_loss

            self.logger.info(
                f"取引結果記録: P&L={profit_loss:.2f}, "
                f"戦略={strategy}, 連続損失={self.consecutive_losses}"
            )

            self._save_state()

        except Exception as e:
            self.logger.error(f"取引結果記録エラー: {e}")

    def calculate_current_drawdown(self) -> float:
        """
        現在のドローダウン率計算

        Returns:
            ドローダウン率（0.0-1.0、0.2 = 20%）.
        """
        try:
            if self.peak_balance <= 0:
                return 0.0

            drawdown = max(
                0.0,
                (self.peak_balance - self.current_balance) / self.peak_balance,
            )
            return drawdown

        except Exception as e:
            self.logger.error(f"ドローダウン計算エラー: {e}")
            return 0.0

    def check_trading_allowed(self) -> bool:
        """
        取引許可チェック

        Returns:
            取引が許可されているかどうか.
        """
        try:
            current_time = datetime.now()

            # 手動停止チェック
            if self.trading_status == TradingStatus.PAUSED_MANUAL:
                return False

            # 一時停止期間チェック
            if self.pause_until and current_time < self.pause_until:
                return False
            elif self.pause_until and current_time >= self.pause_until:
                # 停止期間終了
                self._resume_trading("停止期間終了")

            # ドローダウン制限チェック
            current_drawdown = self.calculate_current_drawdown()
            if current_drawdown >= self.max_drawdown_ratio:
                if self.trading_status != TradingStatus.PAUSED_DRAWDOWN:
                    self._pause_trading_drawdown()
                return False

            # 連続損失チェック
            if self.consecutive_losses >= self.consecutive_loss_limit:
                if (
                    self.trading_status
                    != TradingStatus.PAUSED_CONSECUTIVE_LOSS
                ):
                    self._pause_trading_consecutive_loss()
                return False

            return True

        except Exception as e:
            self.logger.error(f"取引許可チェックエラー: {e}")
            return False

    def get_drawdown_statistics(self) -> Dict:
        """
        ドローダウン統計情報取得

        Returns:
            統計情報辞書.
        """
        try:
            current_drawdown = self.calculate_current_drawdown()
            trading_allowed = self.check_trading_allowed()

            # 履歴統計
            max_historical_drawdown = 0.0
            if self.drawdown_history:
                max_historical_drawdown = max(
                    snapshot.drawdown_ratio
                    for snapshot in self.drawdown_history
                )

            # セッション統計
            session_stats = {}
            if self.current_session:
                win_rate = 0.0
                if self.current_session.total_trades > 0:
                    win_rate = (
                        self.current_session.profitable_trades
                        / self.current_session.total_trades
                    )

                session_stats = {
                    "session_start": self.current_session.start_time.isoformat(),
                    "total_trades": self.current_session.total_trades,
                    "profitable_trades": self.current_session.profitable_trades,
                    "win_rate": win_rate,
                    "initial_balance": self.current_session.initial_balance,
                }

            stats = {
                "current_balance": self.current_balance,
                "peak_balance": self.peak_balance,
                "current_drawdown": current_drawdown,
                "max_drawdown_limit": self.max_drawdown_ratio,
                "max_historical_drawdown": max_historical_drawdown,
                "consecutive_losses": self.consecutive_losses,
                "consecutive_loss_limit": self.consecutive_loss_limit,
                "trading_status": self.trading_status.value,
                "trading_allowed": trading_allowed,
                "last_loss_time": (
                    self.last_loss_time.isoformat()
                    if self.last_loss_time
                    else None
                ),
                "pause_until": (
                    self.pause_until.isoformat() if self.pause_until else None
                ),
                "session_statistics": session_stats,
            }

            return stats

        except Exception as e:
            self.logger.error(f"ドローダウン統計取得エラー: {e}")
            return {"status": "エラー", "error": str(e)}

    def manual_pause_trading(self, reason: str = "手動停止") -> None:
        """
        手動での取引停止

        Args:
            reason: 停止理由.
        """
        try:
            self.trading_status = TradingStatus.PAUSED_MANUAL
            self.logger.warning(f"手動取引停止: {reason}")
            self._save_state()

        except Exception as e:
            self.logger.error(f"手動停止エラー: {e}")

    def manual_resume_trading(self, reason: str = "手動再開") -> None:
        """
        手動での取引再開

        Args:
            reason: 再開理由.
        """
        try:
            # 他の制限が解除されているかチェック
            if self.check_trading_allowed():
                self._resume_trading(reason)
            else:
                self.logger.warning("他の制限により取引再開不可")

        except Exception as e:
            self.logger.error(f"手動再開エラー: {e}")

    def _pause_trading_drawdown(self) -> None:
        """ドローダウン制限による取引停止."""
        self.trading_status = TradingStatus.PAUSED_DRAWDOWN
        current_drawdown = self.calculate_current_drawdown()

        self.logger.critical(
            f"ドローダウン制限到達！取引停止: {current_drawdown:.1%} >= {self.max_drawdown_ratio:.1%}"
        )

        # セッション終了
        if self.current_session:
            self._end_current_session(
                f"ドローダウン制限: {current_drawdown:.1%}"
            )

    def _pause_trading_consecutive_loss(self) -> None:
        """連続損失による取引停止."""
        self.trading_status = TradingStatus.PAUSED_CONSECUTIVE_LOSS
        self.pause_until = datetime.now() + timedelta(
            hours=self.cooldown_hours
        )

        self.logger.critical(
            f"連続損失制限到達！{self.cooldown_hours}時間停止: "
            f"{self.consecutive_losses}回 >= {self.consecutive_loss_limit}回"
        )

        # セッション終了
        if self.current_session:
            self._end_current_session(
                f"連続損失: {self.consecutive_losses}回, "
                f"{self.cooldown_hours}時間停止"
            )

    def _resume_trading(self, reason: str) -> None:
        """取引再開."""
        old_status = self.trading_status
        self.trading_status = TradingStatus.ACTIVE
        self.pause_until = None

        self.logger.info(f"取引再開: {reason} (旧状態: {old_status.value})")

        # 新セッション開始
        self._start_new_session(self.current_balance)

    def _start_new_session(self, initial_balance: float) -> None:
        """新しい取引セッション開始."""
        self.current_session = TradingSession(
            start_time=datetime.now(),
            end_time=None,
            reason="セッション開始",
            initial_balance=initial_balance,
            final_balance=None,
            total_trades=0,
            profitable_trades=0,
        )

        self.logger.info(f"新セッション開始: 初期残高={initial_balance:.2f}")

    def _end_current_session(self, reason: str) -> None:
        """現在の取引セッション終了."""
        if self.current_session:
            self.current_session.end_time = datetime.now()
            self.current_session.reason = reason
            self.current_session.final_balance = self.current_balance

            self.trading_sessions.append(self.current_session)

            self.logger.info(
                f"セッション終了: {reason}, "
                f"取引数={self.current_session.total_trades}, "
                f"利益取引={self.current_session.profitable_trades}"
            )

            self.current_session = None

    def _save_state(self) -> None:
        """状態をファイルに保存."""
        try:
            state = {
                "current_balance": self.current_balance,
                "peak_balance": self.peak_balance,
                "consecutive_losses": self.consecutive_losses,
                "last_loss_time": (
                    self.last_loss_time.isoformat()
                    if self.last_loss_time
                    else None
                ),
                "trading_status": self.trading_status.value,
                "pause_until": (
                    self.pause_until.isoformat() if self.pause_until else None
                ),
                "current_session": (
                    asdict(self.current_session)
                    if self.current_session
                    else None
                ),
            }

            with open(self.persistence_file, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2, default=str)

        except Exception as e:
            self.logger.error(f"状態保存エラー: {e}")

    def _load_state(self) -> None:
        """ファイルから状態を復元."""
        try:
            if not self.persistence_file.exists():
                self.logger.info(
                    "ドローダウン状態ファイルが存在しません（初回起動）"
                )
                return

            with open(self.persistence_file, "r", encoding="utf-8") as f:
                state = json.load(f)

            self.current_balance = state.get("current_balance", 0.0)
            self.peak_balance = state.get("peak_balance", 0.0)
            self.consecutive_losses = state.get("consecutive_losses", 0)

            if state.get("last_loss_time"):
                self.last_loss_time = datetime.fromisoformat(
                    state["last_loss_time"]
                )

            if state.get("trading_status"):
                self.trading_status = TradingStatus(state["trading_status"])

            if state.get("pause_until"):
                self.pause_until = datetime.fromisoformat(state["pause_until"])

            if state.get("current_session"):
                session_data = state["current_session"]
                self.current_session = TradingSession(
                    start_time=datetime.fromisoformat(
                        session_data["start_time"]
                    ),
                    end_time=(
                        datetime.fromisoformat(session_data["end_time"])
                        if session_data.get("end_time")
                        else None
                    ),
                    reason=session_data.get("reason", ""),
                    initial_balance=session_data.get("initial_balance", 0.0),
                    final_balance=session_data.get("final_balance"),
                    total_trades=session_data.get("total_trades", 0),
                    profitable_trades=session_data.get("profitable_trades", 0),
                )

            self.logger.info(
                f"ドローダウン状態復元完了: 残高={self.current_balance:.2f}, 状態={self.trading_status.value}"
            )

        except Exception as e:
            self.logger.error(f"状態復元エラー: {e}")
            # エラー時はデフォルト状態を使用
