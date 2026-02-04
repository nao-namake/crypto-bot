"""
取引履歴記録システム - Phase 47.1実装

SQLiteベースの取引履歴永続化システム。
エントリー・エグジット・TP/SL発動を記録し、確定申告用データを保存。
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.core.logger import get_logger


class TradeHistoryRecorder:
    """
    取引履歴記録システム

    SQLiteデータベースに取引履歴を永続化し、確定申告用データを提供。
    """

    def __init__(self, db_path: str = "tax/trade_history.db"):
        """
        TradeHistoryRecorder初期化

        Args:
            db_path: SQLiteデータベースファイルパス（デフォルト: tax/trade_history.db）
        """
        self.logger = get_logger()
        self.db_path = Path(db_path)

        # データベースディレクトリ作成
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # データベース初期化
        self._init_database()

        self.logger.info(f"✅ TradeHistoryRecorder初期化完了: {self.db_path}")

    def _init_database(self):
        """データベーステーブル初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # tradesテーブル作成
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                trade_type TEXT NOT NULL,
                side TEXT NOT NULL,
                amount REAL NOT NULL,
                price REAL NOT NULL,
                fee REAL,
                pnl REAL,
                order_id TEXT,
                notes TEXT,
                slippage REAL,
                expected_price REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Phase 62.16: 既存テーブルにslippage, expected_price列がなければ追加
        try:
            cursor.execute("ALTER TABLE trades ADD COLUMN slippage REAL")
        except sqlite3.OperationalError:
            pass  # 既に存在する場合は無視
        try:
            cursor.execute("ALTER TABLE trades ADD COLUMN expected_price REAL")
        except sqlite3.OperationalError:
            pass  # 既に存在する場合は無視

        # インデックス作成
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON trades(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trade_type ON trades(trade_type)")

        conn.commit()
        conn.close()

    def record_trade(
        self,
        trade_type: str,
        side: str,
        amount: float,
        price: float,
        fee: float = 0.0,
        pnl: Optional[float] = None,
        order_id: Optional[str] = None,
        notes: Optional[str] = None,
        slippage: Optional[float] = None,
        expected_price: Optional[float] = None,
    ) -> int:
        """
        取引記録

        Args:
            trade_type: 取引種別 ('entry', 'exit', 'tp', 'sl')
            side: 売買方向 ('buy', 'sell')
            amount: 取引数量 (BTC)
            price: 取引価格 (JPY)
            fee: 手数料 (JPY)
            pnl: 損益 (JPY) - exit時のみ
            order_id: 注文ID
            notes: 備考
            slippage: スリッページ (JPY) - Phase 62.16追加
            expected_price: 期待約定価格 (JPY) - Phase 62.16追加

        Returns:
            int: 記録ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        timestamp = datetime.now().isoformat()

        cursor.execute(
            """
            INSERT INTO trades (timestamp, trade_type, side, amount, price, fee, pnl, order_id, notes, slippage, expected_price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (timestamp, trade_type, side, amount, price, fee, pnl, order_id, notes, slippage, expected_price),
        )

        record_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # Phase 62.16: スリッページ情報があればログ出力
        slippage_info = ""
        if slippage is not None:
            slippage_info = f", slippage={slippage:.0f}円"

        self.logger.debug(
            f"📝 取引記録保存: ID={record_id}, type={trade_type}, side={side}, "
            f"amount={amount:.8f} BTC, price={price:.0f}円{slippage_info}"
        )

        return record_id

    def get_trades(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        trade_type: Optional[str] = None,
    ) -> list:
        """
        取引履歴取得

        Args:
            start_date: 開始日 (YYYY-MM-DD形式)
            end_date: 終了日 (YYYY-MM-DD形式)
            trade_type: 取引種別フィルター

        Returns:
            list: 取引履歴リスト（辞書形式）
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM trades WHERE 1=1"
        params = []

        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)

        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)

        if trade_type:
            query += " AND trade_type = ?"
            params.append(trade_type)

        query += " ORDER BY timestamp ASC"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        trades = [dict(row) for row in rows]

        conn.close()

        return trades

    def get_trade_count(self) -> int:
        """総取引回数取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM trades")
        count = cursor.fetchone()[0]

        conn.close()

        return count

    def clear_trades(self, before_date: Optional[str] = None):
        """
        取引履歴削除（データベースメンテナンス用）

        Args:
            before_date: この日付以前のデータを削除 (YYYY-MM-DD形式)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if before_date:
            cursor.execute("DELETE FROM trades WHERE timestamp < ?", (before_date,))
            self.logger.info(f"🗑️ {before_date}以前の取引履歴を削除しました")
        else:
            cursor.execute("DELETE FROM trades")
            self.logger.warning("⚠️ 全取引履歴を削除しました")

        conn.commit()
        conn.close()
