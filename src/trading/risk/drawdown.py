"""
ドローダウン管理システム - Phase 49完了

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

        # 状態変数
        self.initial_balance = 10000.0
        self.peak_balance = 10000.0
        self.current_balance = 10000.0
        self.consecutive_losses = 0
        self.trading_status = TradingStatus.ACTIVE
        self.cooldown_until: Optional[datetime] = None
        self.trade_history: List[TradeRecord] = []

        self.logger = get_logger()

        # 状態永続化設定
        persistence_config = self.config.get("persistence", {})
        self.local_state_path = persistence_config.get(
            "local_path", "src/core/state/drawdown_state.json"
        )
        self.gcs_bucket = persistence_config.get("gcs_bucket")
        self.gcs_path = persistence_config.get("gcs_path")

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

    def record_trade_result(self, profit_loss: float, strategy: str = "default") -> None:
        """
        取引結果記録

        Args:
            profit_loss: 損益（正値=利益、負値=損失）
            strategy: 戦略名
        """
        try:
            # 取引記録追加
            trade_record = TradeRecord(
                timestamp=datetime.now(),
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
                    self.logger.info(f"連続損失リセット（勝ち取引）")
                self.consecutive_losses = 0

            # ドローダウンチェック
            current_drawdown = self.calculate_current_drawdown()
            if current_drawdown >= self.max_drawdown_ratio:
                self._enter_cooldown(TradingStatus.PAUSED_DRAWDOWN)
            elif self.consecutive_losses >= self.consecutive_loss_limit:
                self._enter_cooldown(TradingStatus.PAUSED_CONSECUTIVE_LOSS)

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

    def check_trading_allowed(self) -> bool:
        """取引許可チェック"""
        # クールダウン期間チェック
        if self.cooldown_until and datetime.now() < self.cooldown_until:
            remaining = (self.cooldown_until - datetime.now()).total_seconds() / 3600
            self.logger.debug(f"クールダウン中: 残り{remaining:.1f}時間")
            return False

        # クールダウン解除
        if self.cooldown_until and datetime.now() >= self.cooldown_until:
            self._exit_cooldown()

        return self.trading_status == TradingStatus.ACTIVE

    def _enter_cooldown(self, status: TradingStatus) -> None:
        """クールダウン開始"""
        self.trading_status = status
        self.cooldown_until = datetime.now() + timedelta(hours=self.cooldown_hours)

        self.logger.warning(
            f"クールダウン開始: {status.value}, "
            f"解除予定: {self.cooldown_until.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        # 状態保存
        self._save_state()

    def _exit_cooldown(self) -> None:
        """クールダウン解除"""
        self.logger.info("クールダウン解除、取引再開")
        self.trading_status = TradingStatus.ACTIVE
        self.cooldown_until = None
        self.consecutive_losses = 0

        # 状態保存
        self._save_state()

    def get_drawdown_statistics(self) -> Dict[str, Any]:
        """ドローダウン統計取得"""
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
        }

    def _save_state(self) -> None:
        """状態保存（ローカル + GCS）"""
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
                "last_updated": datetime.now().isoformat(),
            }

            # ローカル保存
            os.makedirs(os.path.dirname(self.local_state_path), exist_ok=True)
            with open(self.local_state_path, "w") as f:
                json.dump(state, f, indent=2)

            self.logger.debug(f"状態保存完了: {self.local_state_path}")

        except Exception as e:
            self.logger.error(f"状態保存エラー: {e}")

    def _load_state(self) -> None:
        """状態復元（ローカル読み込み）"""
        try:
            # バックテストモードでは復元しない
            if self.mode == "backtest":
                return

            if not os.path.exists(self.local_state_path):
                self.logger.info("状態ファイル未存在、新規作成")
                return

            with open(self.local_state_path, "r") as f:
                state = json.load(f)

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

            self.logger.info(f"状態復元完了: {self.local_state_path}")

        except Exception as e:
            self.logger.error(f"状態復元エラー: {e}")
