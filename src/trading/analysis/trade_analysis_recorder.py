"""
取引判断の事後分析記録 - Phase 69.7

エントリー時の条件（ML信頼度・レジーム・戦略等）と決済結果を記録し、
決済後の価格追跡データを付与して取引判断の妥当性を検証する。

責務:
- エントリー時: ML信頼度・レジーム・戦略名等の判断根拠を記録
- 決済時: 決済理由・PnL・決済価格を更新
- 事後分析: 決済後15分/1時間/4時間の価格を記録し判断評価
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...core.logger import get_logger


class TradeAnalysisRecorder:
    """取引判断の事後分析記録"""

    DB_PATH = "tax/trade_history.db"

    def __init__(self, db_path: str = None):
        self.db_path = Path(db_path or self.DB_PATH)
        self.logger = get_logger()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_table()

    def _init_table(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS trade_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                -- Entry info
                entry_order_id TEXT NOT NULL UNIQUE,
                entry_timestamp TEXT NOT NULL,
                entry_price REAL NOT NULL,
                entry_side TEXT NOT NULL,
                entry_amount REAL NOT NULL,
                -- Entry conditions (judgment basis)
                strategy_name TEXT,
                ml_prediction INTEGER,
                ml_confidence REAL,
                adjusted_confidence REAL,
                regime TEXT,
                take_profit_price REAL,
                stop_loss_price REAL,
                -- Exit details (filled on exit)
                exit_timestamp TEXT,
                exit_price REAL,
                exit_type TEXT,
                pnl REAL,
                -- Post-exit price tracking (filled by analysis)
                price_15min_after REAL,
                price_1h_after REAL,
                price_4h_after REAL,
                -- Metadata
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_ta_entry_order " "ON trade_analysis(entry_order_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_ta_exit_timestamp " "ON trade_analysis(exit_timestamp)"
        )
        conn.commit()
        conn.close()

    def record_entry(
        self,
        order_id: str,
        price: float,
        side: str,
        amount: float,
        strategy_name: str = None,
        ml_prediction: int = None,
        ml_confidence: float = None,
        adjusted_confidence: float = None,
        regime: str = None,
        take_profit: float = None,
        stop_loss: float = None,
    ) -> None:
        """エントリー時の判断根拠を記録"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO trade_analysis
                (entry_order_id, entry_timestamp, entry_price, entry_side,
                 entry_amount, strategy_name, ml_prediction, ml_confidence,
                 adjusted_confidence, regime, take_profit_price, stop_loss_price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    str(order_id),
                    datetime.now(timezone.utc).isoformat(),
                    price,
                    side,
                    amount,
                    strategy_name,
                    ml_prediction,
                    ml_confidence,
                    adjusted_confidence,
                    regime,
                    take_profit,
                    stop_loss,
                ),
            )
            conn.commit()
            conn.close()
            self.logger.info(
                f"📊 Phase 69.7: エントリー分析記録 - {side} {amount:.4f} BTC "
                f"@ {price:.0f}円, 戦略={strategy_name}, "
                f"ML信頼度={ml_confidence}, レジーム={regime}"
            )
        except Exception as e:
            self.logger.warning(f"⚠️ Phase 69.7: エントリー分析記録失敗: {e}")

    def record_exit(
        self,
        entry_order_id: str,
        exit_price: float,
        exit_type: str,
        pnl: float,
        exit_timestamp: str = None,
    ) -> None:
        """決済結果を記録"""
        try:
            if not exit_timestamp:
                exit_timestamp = datetime.now(timezone.utc).isoformat()
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE trade_analysis
                SET exit_timestamp = ?, exit_price = ?, exit_type = ?, pnl = ?
                WHERE entry_order_id = ?
            """,
                (exit_timestamp, exit_price, exit_type, pnl, str(entry_order_id)),
            )
            updated = cursor.rowcount
            conn.commit()
            conn.close()
            if updated > 0:
                self.logger.info(
                    f"📊 Phase 69.7: 決済分析記録 - {exit_type}, "
                    f"PnL={pnl:+.0f}円, 価格={exit_price:.0f}円"
                )
            else:
                self.logger.debug(
                    f"Phase 69.7: 決済記録スキップ（エントリー未記録）- "
                    f"order_id={entry_order_id}"
                )
        except Exception as e:
            self.logger.warning(f"⚠️ Phase 69.7: 決済分析記録失敗: {e}")

    def get_pending_price_checks(self) -> List[Dict[str, Any]]:
        """決済済みで事後価格未取得のレコードを取得"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM trade_analysis
                WHERE exit_timestamp IS NOT NULL
                  AND (price_4h_after IS NULL)
                ORDER BY exit_timestamp DESC
                LIMIT 20
            """
            )
            rows = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return rows
        except Exception as e:
            self.logger.warning(f"⚠️ Phase 69.7: pending取得失敗: {e}")
            return []

    def update_post_exit_prices(
        self,
        entry_order_id: str,
        price_15min: float = None,
        price_1h: float = None,
        price_4h: float = None,
    ) -> None:
        """事後価格を更新"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # 既存値を保持しつつ新しい値で上書き
            updates = []
            params = []
            if price_15min is not None:
                updates.append("price_15min_after = ?")
                params.append(price_15min)
            if price_1h is not None:
                updates.append("price_1h_after = ?")
                params.append(price_1h)
            if price_4h is not None:
                updates.append("price_4h_after = ?")
                params.append(price_4h)
            if not updates:
                conn.close()
                return
            params.append(str(entry_order_id))
            cursor.execute(
                f"UPDATE trade_analysis SET {', '.join(updates)} " f"WHERE entry_order_id = ?",
                params,
            )
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.warning(f"⚠️ Phase 69.7: 事後価格更新失敗: {e}")

    def get_recent_analyses(self, limit: int = 10) -> List[Dict[str, Any]]:
        """直近の分析レコードを取得（表示用）"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM trade_analysis
                WHERE exit_timestamp IS NOT NULL
                ORDER BY exit_timestamp DESC
                LIMIT ?
            """,
                (limit,),
            )
            rows = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return rows
        except Exception as e:
            self.logger.warning(f"⚠️ Phase 69.7: 分析取得失敗: {e}")
            return []

    @staticmethod
    def evaluate_decision(record: Dict[str, Any]) -> Optional[str]:
        """
        決済判断の事後評価

        Returns:
            "good" / "bad" / "neutral" / None
        """
        exit_type = record.get("exit_type", "")
        exit_price = record.get("exit_price") or 0
        entry_side = record.get("entry_side", "")
        price_1h = record.get("price_1h_after")

        if not price_1h or exit_price <= 0:
            return None

        if exit_type == "take_profit":
            # TP後に価格が反転した → TP正解
            if entry_side == "buy":
                return "good" if price_1h < exit_price else "bad"
            else:
                return "good" if price_1h > exit_price else "bad"
        elif "stop_loss" in exit_type:
            # SL後にさらに悪化した → SL正解
            if entry_side == "buy":
                return "good" if price_1h < exit_price else "bad"
            else:
                return "good" if price_1h > exit_price else "bad"

        return "neutral"
