"""
戦略ベースクラス実装 - すべての戦略の基盤

シンプルで理解しやすい戦略実装を提供。

主要コンポーネント:
- StrategySignal: 戦略シグナルデータクラス
- StrategyBase: 全戦略の基底クラス

Phase 52.4-B完了
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from ...core.exceptions import StrategyError
from ...core.logger import get_logger


@dataclass
class StrategySignal:
    """
    戦略シグナルデータクラス

    戦略が生成するエントリー・エグジットシグナルの
    標準化されたデータ構造。.
    """

    # 基本情報
    strategy_name: str  # 戦略名
    timestamp: datetime  # シグナル発生時刻

    # シグナル内容
    action: str  # エントリーアクション (buy/sell/hold/close)
    confidence: float  # 信頼度 (0.0-1.0)
    strength: float  # シグナル強度 (0.0-1.0)

    # 価格情報
    current_price: float  # 現在価格
    entry_price: Optional[float] = None  # 推奨エントリー価格
    stop_loss: Optional[float] = None  # ストップロス価格
    take_profit: Optional[float] = None  # 利確価格

    # リスク管理
    position_size: Optional[float] = None  # ポジションサイズ
    risk_ratio: Optional[float] = None  # リスク比率

    # 詳細情報
    indicators: Optional[Dict[str, float]] = None  # 使用した指標値
    reason: Optional[str] = None  # シグナル理由
    metadata: Optional[Dict[str, Any]] = None  # その他メタデータ

    def to_dict(self) -> Dict[str, Any]:
        """シグナルを辞書形式に変換（ログ・保存用）."""
        return {
            "strategy_name": self.strategy_name,
            "timestamp": self.timestamp.isoformat(),
            "action": self.action,
            "confidence": self.confidence,
            "strength": self.strength,
            "current_price": self.current_price,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "position_size": self.position_size,
            "risk_ratio": self.risk_ratio,
            "indicators": self.indicators,
            "reason": self.reason,
            "metadata": self.metadata,
        }

    def is_entry_signal(self) -> bool:
        """エントリーシグナルかどうかを判定."""
        return self.action in ["buy", "sell"]

    def is_exit_signal(self) -> bool:
        """エグジットシグナルかどうかを判定."""
        return self.action in ["close"]

    def is_hold_signal(self) -> bool:
        """ホールドシグナルかどうかを判定."""
        return self.action == "hold"


class StrategyBase(ABC):
    """
    戦略ベースクラス

    すべての取引戦略が継承する抽象基底クラス。
    共通のインターフェースと基本機能を提供。.
    """

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        戦略の初期化

        Args:
            name: 戦略名
            config: 戦略設定辞書.
        """
        self.name = name
        self.config = config or {}
        self.logger = get_logger()

        # 戦略状態
        self.is_enabled = True
        self.last_signal: Optional[StrategySignal] = None
        self.signal_history: List[StrategySignal] = []

        # パフォーマンス追跡
        self.total_signals = 0
        self.successful_signals = 0
        self.last_update = datetime.now()

        self.logger.info(f"戦略初期化完了: {self.name}")

    @abstractmethod
    def analyze(
        self, df: pd.DataFrame, multi_timeframe_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> StrategySignal:
        """
        市場データを分析してシグナルを生成（抽象メソッド）

        Args:
            df: OHLCV + 特徴量データ（メインタイムフレーム）
            multi_timeframe_data: マルチタイムフレームデータ（Phase 31対応）
                - 形式: {"4h": DataFrame, "15m": DataFrame}
                - Noneの場合は単一タイムフレーム動作（後方互換）

        Returns:
            生成されたシグナル

        Raises:
            StrategyError: 戦略実行エラー.
        """
        pass

    @abstractmethod
    def get_required_features(self) -> List[str]:
        """
        戦略が必要とする特徴量リストを返す（抽象メソッド）

        Returns:
            必要特徴量名のリスト.
        """
        pass

    def generate_signal(
        self, df: pd.DataFrame, multi_timeframe_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> StrategySignal:
        """
        シグナル生成のメインエントリーポイント

        Args:
            df: 市場データ
            multi_timeframe_data: マルチタイムフレームデータ（Phase 31対応）

        Returns:
            生成されたシグナル.
        """
        try:
            self.logger.debug(f"[{self.name}] シグナル生成開始")

            # 前処理チェック
            self._validate_input_data(df)

            # 戦略分析実行（Phase 31: multi_timeframe_data渡し）
            signal = self.analyze(df, multi_timeframe_data=multi_timeframe_data)

            # 後処理
            self._post_process_signal(signal)

            self.logger.debug(
                f"[{self.name}] シグナル生成完了: {signal.action} (信頼度: {signal.confidence:.3f})"
            )

            return signal

        except Exception as e:
            # Phase 35: バックテストモード時はDEBUGレベル（環境変数直接チェック）
            import os

            if os.environ.get("BACKTEST_MODE") == "true":
                self.logger.debug(f"[{self.name}] シグナル生成エラー: {e}")
            else:
                self.logger.error(f"[{self.name}] シグナル生成エラー: {e}")
            raise StrategyError(f"戦略シグナル生成失敗: {e}", strategy_name=self.name)

    def _validate_input_data(self, df: pd.DataFrame) -> None:
        """入力データの検証."""
        if df.empty:
            raise StrategyError("データが空です", strategy_name=self.name)

        # 必要特徴量の存在確認
        required_features = self.get_required_features()
        missing_features = [f for f in required_features if f not in df.columns]

        if missing_features:
            raise StrategyError(
                f"必要特徴量が不足: {missing_features}",
                strategy_name=self.name,
            )

        # 最低データ数確認
        min_data_points = self.config.get("min_data_points", 20)
        if len(df) < min_data_points:
            raise StrategyError(
                f"データ数不足: {len(df)} < {min_data_points}",
                strategy_name=self.name,
            )

    def _post_process_signal(self, signal: StrategySignal) -> None:
        """シグナル後処理."""
        # シグナル履歴に追加
        self.signal_history.append(signal)
        self.last_signal = signal
        self.total_signals += 1
        self.last_update = datetime.now()

        # 履歴サイズ制限（メモリ使用量制御）
        max_history = self.config.get("max_signal_history", 1000)
        if len(self.signal_history) > max_history:
            self.signal_history = self.signal_history[-max_history:]

    def update_performance(self, signal_success: bool) -> None:
        """パフォーマンス更新."""
        if signal_success:
            self.successful_signals += 1

        success_rate = self.get_success_rate()
        self.logger.info(f"[{self.name}] 成功率更新: {success_rate:.1f}%")

    def get_success_rate(self) -> float:
        """成功率取得."""
        if self.total_signals == 0:
            return 0.0
        return (self.successful_signals / self.total_signals) * 100

    def get_signal_stats(self) -> Dict[str, Any]:
        """シグナル統計情報取得."""
        if not self.signal_history:
            return {"total": 0, "by_action": {}, "avg_confidence": 0.0}

        # アクション別カウント
        action_counts: Dict[str, int] = {}
        total_confidence: float = 0.0

        for signal in self.signal_history:
            action = signal.action
            action_counts[action] = action_counts.get(action, 0) + 1
            total_confidence += signal.confidence

        return {
            "total": len(self.signal_history),
            "by_action": action_counts,
            "avg_confidence": total_confidence / len(self.signal_history),
            "success_rate": self.get_success_rate(),
            "last_signal_time": (
                self.last_signal.timestamp.isoformat() if self.last_signal else None
            ),
        }

    def enable(self):
        """戦略を有効化."""
        self.is_enabled = True
        self.logger.info(f"[{self.name}] 戦略有効化")

    def disable(self):
        """戦略を無効化."""
        self.is_enabled = False
        self.logger.info(f"[{self.name}] 戦略無効化")

    def reset_history(self):
        """シグナル履歴をリセット."""
        self.signal_history.clear()
        self.last_signal = None
        self.total_signals = 0
        self.successful_signals = 0
        self.logger.info(f"[{self.name}] 履歴リセット完了")

    def get_info(self) -> Dict[str, Any]:
        """戦略情報取得."""
        return {
            "name": self.name,
            "is_enabled": self.is_enabled,
            "config": self.config,
            "required_features": self.get_required_features(),
            "stats": self.get_signal_stats(),
            "last_update": self.last_update.isoformat(),
        }
