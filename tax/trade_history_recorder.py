"""
取引履歴記録システム - Phase 47.1実装
Cloud Storage同期機能追加 - Phase 56

SQLiteベースの取引履歴永続化システム。
エントリー・エグジット・TP/SL発動を記録し、確定申告用データを保存。
Cloud Storageへの自動同期で週間レポートワークフローと連携。
"""

import os
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.core.logger import get_logger

# Cloud Storage設定
GCS_BUCKET = os.environ.get("GCS_BUCKET", "crypto-bot-trade-data")
GCS_DB_PATH = "tax/trade_history.db"


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
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

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

        Returns:
            int: 記録ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        timestamp = datetime.now().isoformat()

        cursor.execute(
            """
            INSERT INTO trades (timestamp, trade_type, side, amount, price, fee, pnl, order_id, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (timestamp, trade_type, side, amount, price, fee, pnl, order_id, notes),
        )

        record_id = cursor.lastrowid
        conn.commit()
        conn.close()

        self.logger.debug(
            f"📝 取引記録保存: ID={record_id}, type={trade_type}, side={side}, "
            f"amount={amount:.8f} BTC, price={price:.0f}円"
        )

        # Cloud Storageへ自動同期（GCP環境のみ）
        if os.environ.get("CLOUD_RUN", ""):
            self.sync_to_cloud_storage()

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

    def sync_to_cloud_storage(self) -> bool:
        """
        Cloud StorageにDBを同期（アップロード）

        Returns:
            bool: 成功した場合True
        """
        try:
            gcs_uri = f"gs://{GCS_BUCKET}/{GCS_DB_PATH}"
            result = subprocess.run(
                ["gsutil", "cp", str(self.db_path), gcs_uri],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                self.logger.info(f"☁️ Cloud Storage同期完了: {gcs_uri}")
                return True
            else:
                self.logger.warning(
                    f"⚠️ Cloud Storage同期失敗: {result.stderr}"
                )
                return False

        except subprocess.TimeoutExpired:
            self.logger.warning("⚠️ Cloud Storage同期タイムアウト")
            return False
        except FileNotFoundError:
            self.logger.debug("gsutilが利用不可（ローカル環境）")
            return False
        except Exception as e:
            self.logger.warning(f"⚠️ Cloud Storage同期エラー: {e}")
            return False

    def sync_from_cloud_storage(self) -> bool:
        """
        Cloud StorageからDBを同期（ダウンロード）

        Returns:
            bool: 成功した場合True
        """
        try:
            gcs_uri = f"gs://{GCS_BUCKET}/{GCS_DB_PATH}"
            result = subprocess.run(
                ["gsutil", "cp", gcs_uri, str(self.db_path)],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                self.logger.info(f"☁️ Cloud Storageからダウンロード完了: {gcs_uri}")
                return True
            else:
                self.logger.debug(f"Cloud Storageからダウンロード失敗: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.warning("⚠️ Cloud Storageダウンロードタイムアウト")
            return False
        except FileNotFoundError:
            self.logger.debug("gsutilが利用不可（ローカル環境）")
            return False
        except Exception as e:
            self.logger.debug(f"Cloud Storageダウンロードエラー: {e}")
            return False
