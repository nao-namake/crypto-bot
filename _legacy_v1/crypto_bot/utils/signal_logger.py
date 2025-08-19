"""
構造化シグナルログ出力ユーティリティ

ChatGPT提案採用: 予測値・シグナル・価格をCSV形式で継続記録
デバッグ・分析効率向上、本番動作の可視化を目的とする

既存utils/設計原則に準拠:
- 横断的機能として設計
- 既存ログシステム（logging.py）と協調
- エラー耐性・スレッドセーフ実装
"""

import csv
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

# 既存ログシステムを使用
logger = logging.getLogger(__name__)


class SignalLogger:
    """シグナル生成ログをCSV形式で記録するクラス"""

    def __init__(self, log_dir: str = "logs", filename: str = "trading_signals.csv"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        self.csv_path = self.log_dir / filename
        self._lock = threading.Lock()

        # CSVヘッダー定義
        self.headers = [
            "timestamp",
            "price",
            "prediction",
            "probability",
            "confidence",
            "threshold",
            "signal_type",
            "market_regime",
            "position_exists",
            "strategy_type",
        ]

        self._initialize_csv()

    def _initialize_csv(self) -> None:
        """CSVファイルを初期化（ヘッダー書き込み）"""
        if not self.csv_path.exists():
            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(self.headers)

    def log_signal(
        self,
        price: float,
        prediction: int,
        probability: float,
        confidence: float,
        threshold: float,
        signal_type: str,
        market_regime: str = "unknown",
        position_exists: bool = False,
        strategy_type: str = "ensemble",
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        シグナル情報をCSVに記録

        Parameters:
        -----------
        price : float
            現在価格
        prediction : int
            予測結果 (0: SELL, 1: BUY)
        probability : float
            正例クラス確率
        confidence : float
            信頼度スコア
        threshold : float
            判定閾値
        signal_type : str
            シグナルタイプ (BUY/SELL/EXIT/HOLD)
        market_regime : str
            市場状況
        position_exists : bool
            ポジション存在フラグ
        strategy_type : str
            戦略タイプ
        timestamp : datetime, optional
            タイムスタンプ (None の場合は現在時刻)
        """
        if timestamp is None:
            timestamp = datetime.now()

        row_data = [
            timestamp.isoformat(),
            price,
            prediction,
            probability,
            confidence,
            threshold,
            signal_type,
            market_regime,
            position_exists,
            strategy_type,
        ]

        # スレッドセーフな書き込み
        with self._lock:
            try:
                with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(row_data)
            except Exception as e:
                # ログ出力エラーはメインロジックに影響しないよう警告のみ
                import logging

                logging.getLogger(__name__).warning(f"Signal logging failed: {e}")

    def get_recent_signals(self, hours: int = 1) -> pd.DataFrame:
        """
        直近N時間のシグナル記録を取得

        Parameters:
        -----------
        hours : int
            取得時間範囲（時間）

        Returns:
        --------
        pd.DataFrame
            シグナル記録データ
        """
        if not self.csv_path.exists():
            return pd.DataFrame()

        try:
            df = pd.read_csv(self.csv_path)
            if df.empty:
                return df

            df["timestamp"] = pd.to_datetime(df["timestamp"])
            cutoff = datetime.now() - pd.Timedelta(hours=hours)
            recent_df = df[df["timestamp"] >= cutoff]

            return recent_df
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(f"Failed to read signal log: {e}")
            return pd.DataFrame()

    def count_recent_signals(
        self, hours: int = 1, signal_type: Optional[str] = None
    ) -> int:
        """
        直近N時間のシグナル数をカウント

        Parameters:
        -----------
        hours : int
            取得時間範囲（時間）
        signal_type : str, optional
            特定のシグナルタイプでフィルター

        Returns:
        --------
        int
            シグナル数
        """
        recent_df = self.get_recent_signals(hours)
        if recent_df.empty:
            return 0

        if signal_type:
            recent_df = recent_df[recent_df["signal_type"] == signal_type]

        return len(recent_df)
