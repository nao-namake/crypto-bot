#!/usr/bin/env python3
"""
ライブモード標準分析スクリプト - Phase 58

目的:
  ライブ運用の標準化された分析を実行し、毎回同一の35指標で
  ブレのない診断を実現。

機能:
  - 35項目の固定指標計算
  - JSON/Markdown/CSV出力
  - bitbank API連携（アカウント・ポジション・注文情報）
  - GCPログ連携（システム健全性・稼働率）
  - 履歴CSV追記（変更前後比較用）

使い方:
  # 基本実行（24時間分析）
  python3 scripts/live/standard_analysis.py

  # 期間指定
  python3 scripts/live/standard_analysis.py --hours 48

  # 出力先指定
  python3 scripts/live/standard_analysis.py --output results/live/
"""

import argparse
import asyncio
import csv
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# .envファイルからAPIキー読み込み（ローカル実行用）
from dotenv import load_dotenv

env_path = PROJECT_ROOT / "config" / "secrets" / ".env"
if env_path.exists():
    load_dotenv(env_path)
    # 読み込み確認用ログは後で出力（logger初期化後）

from src.core.logger import get_logger
from src.data.bitbank_client import BitbankClient


@dataclass
class LiveAnalysisResult:
    """ライブモード分析結果（35指標）"""

    # メタ情報
    timestamp: str = ""
    analysis_period_hours: int = 24

    # アカウント状態（5指標）
    margin_ratio: float = 0.0
    available_balance: float = 0.0
    used_margin: float = 0.0
    unrealized_pnl: float = 0.0
    margin_call_status: str = ""

    # ポジション状態（5指標）
    open_position_count: int = 0
    position_details: List[Dict[str, Any]] = field(default_factory=list)
    pending_order_count: int = 0
    order_breakdown: Dict[str, int] = field(default_factory=dict)
    losscut_price: Optional[float] = None

    # 取引履歴分析（12指標）
    trades_count: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    avg_pnl: float = 0.0
    max_profit: float = 0.0
    max_loss: float = 0.0
    strategy_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    tp_triggered_count: int = 0
    sl_triggered_count: int = 0

    # システム健全性（6指標）
    api_response_time_ms: float = 0.0
    recent_error_count: int = 0
    last_trade_time: Optional[str] = None
    service_status: str = ""
    last_deploy_time: Optional[str] = None
    container_restart_count: int = 0

    # TP/SL適切性（4指標）
    tp_distance_pct: Optional[float] = None
    sl_distance_pct: Optional[float] = None
    tp_sl_placement_ok: bool = True
    tp_sl_config_deviation: Optional[float] = None

    # Phase 58.8: 孤児注文検出（2指標）
    orphan_sl_detected: bool = False
    orphan_order_count: int = 0

    # 稼働率（5指標）
    uptime_rate: float = 0.0
    total_downtime_minutes: float = 0.0
    last_incident_time: Optional[str] = None
    actual_cycle_count: int = 0
    expected_cycle_count: int = 0


class LiveAnalyzer:
    """ライブモード標準分析"""

    STRATEGIES = [
        "ATRBased",
        "BBReversal",
        "DonchianChannel",
        "StochasticReversal",
        "ADXTrendStrength",
        "MACDEMACrossover",
    ]

    def __init__(self, period_hours: int = 24):
        self.period_hours = period_hours
        self.logger = get_logger()
        self.result = LiveAnalysisResult(analysis_period_hours=period_hours)
        self.bitbank_client: Optional[BitbankClient] = None
        self.current_price: float = 0.0
        # Phase 59.5: 注文フェッチ一元化（タイミング差による不整合防止）
        self._cached_active_orders: List[Dict[str, Any]] = []

    async def analyze(self) -> LiveAnalysisResult:
        """分析実行"""
        self.result.timestamp = datetime.now().isoformat()
        self.logger.info(f"ライブモード分析開始 - 対象期間: {self.period_hours}時間")

        # .env読み込み確認
        if env_path.exists():
            api_key = os.getenv("BITBANK_API_KEY", "")
            if api_key and len(api_key) > 8:
                self.logger.info(f"✅ .envからAPIキー読み込み成功: {api_key[:8]}...")
            else:
                self.logger.warning("⚠️ .envファイル存在するがAPIキーが空")

        try:
            # bitbankクライアント初期化
            self.bitbank_client = BitbankClient()

            # 現在価格取得
            await self._fetch_current_price()

            # 各分析実行
            await self._fetch_account_status()
            await self._fetch_position_status()
            await self._fetch_trade_history()
            await self._check_system_health()
            await self._check_tp_sl_placement()
            await self._calculate_uptime()

        except Exception as e:
            self.logger.error(f"分析中にエラー発生: {e}")
            raise

        self.logger.info("ライブモード分析完了")
        return self.result

    async def _fetch_current_price(self):
        """現在価格取得"""
        try:
            ticker = self.bitbank_client.fetch_ticker("BTC/JPY")
            self.current_price = ticker.get("last", 0)
            self.logger.info(f"現在価格: ¥{self.current_price:,.0f}")
        except Exception as e:
            self.logger.warning(f"価格取得失敗: {e}")
            self.current_price = 0

    async def _fetch_account_status(self):
        """アカウント状態取得（5指標）"""
        try:
            start_time = time.time()
            margin_status = await self.bitbank_client.fetch_margin_status()
            self.result.api_response_time_ms = (time.time() - start_time) * 1000

            self.result.margin_ratio = margin_status.get("margin_ratio", 0.0)
            self.result.available_balance = margin_status.get("available_balance", 0.0)
            self.result.used_margin = margin_status.get("used_margin", 0.0)
            self.result.unrealized_pnl = margin_status.get("unrealized_pnl", 0.0)
            self.result.margin_call_status = margin_status.get("margin_call_status", "unknown")

            self.logger.info(f"アカウント状態取得完了 - 維持率: {self.result.margin_ratio:.1f}%")
        except Exception as e:
            self.logger.error(f"アカウント状態取得失敗: {e}")
            self.result.margin_call_status = "error"

    async def _fetch_position_status(self):
        """ポジション状態取得（5指標）"""
        try:
            # ポジション取得（Phase 58.4: fetch_margin_positions使用）
            positions = await self.bitbank_client.fetch_margin_positions("BTC/JPY")

            # Phase 58.8: 有効ポジションのみフィルタ（BTC/JPY + Amount > 0）
            # bitbank APIは全通貨ペアのスロットを返却するため、フィルタ必須
            active_positions = [
                p
                for p in positions
                if p.get("amount", 0) > 0
                and p.get("symbol", "").lower().replace("/", "_") == "btc_jpy"
            ]
            self.result.open_position_count = len(active_positions)

            # ポジション詳細（有効ポジションのみ）
            self.result.position_details = []
            for pos in active_positions:
                detail = {
                    "side": pos.get("side", "unknown"),
                    "amount": pos.get("amount", 0),
                    "avg_price": pos.get("average_price", 0),
                    "unrealized_pnl": pos.get("unrealized_pnl", 0),
                }
                self.result.position_details.append(detail)

                # ロスカット価格
                if pos.get("losscut_price"):
                    self.result.losscut_price = pos.get("losscut_price")

            # アクティブ注文取得（Phase 59.5: キャッシュに保存）
            active_orders = self.bitbank_client.fetch_active_orders("BTC/JPY")
            self._cached_active_orders = active_orders  # 他メソッドで再利用
            self.result.pending_order_count = len(active_orders)

            # 注文内訳
            breakdown = {"limit": 0, "stop": 0, "stop_limit": 0}
            for order in active_orders:
                order_type = order.get("type", "limit")
                if order_type in breakdown:
                    breakdown[order_type] += 1
                else:
                    breakdown["limit"] += 1
            self.result.order_breakdown = breakdown

            # Phase 58.8: 孤児SL/TP検出
            # ポジションがないのにstop/stop_limit注文がある場合は孤児
            sl_tp_count = breakdown.get("stop", 0) + breakdown.get("stop_limit", 0)
            if self.result.open_position_count == 0 and sl_tp_count > 0:
                self.result.orphan_sl_detected = True
                self.result.orphan_order_count = sl_tp_count
                self.logger.warning(
                    f"⚠️ Phase 58.8: 孤児SL/TP注文検出 - {sl_tp_count}件 "
                    "(ポジションなしでSL/TP注文が残存)"
                )

            self.logger.info(
                f"ポジション状態取得完了 - ポジション: {self.result.open_position_count}件, "
                f"未約定注文: {self.result.pending_order_count}件"
            )
        except Exception as e:
            self.logger.error(f"ポジション状態取得失敗: {e}")

    async def _fetch_trade_history(self):
        """取引履歴分析（12指標）"""
        try:
            # SQLiteから取引履歴取得
            db_path = Path("tax/trade_history.db")
            if not db_path.exists():
                self.logger.warning("取引履歴DBが存在しません")
                return

            import sqlite3

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 対象期間の開始時刻
            start_time = (datetime.now() - timedelta(hours=self.period_hours)).isoformat()

            cursor.execute(
                """
                SELECT * FROM trades
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
            """,
                (start_time,),
            )
            trades = [dict(row) for row in cursor.fetchall()]
            conn.close()

            self.result.trades_count = len(trades)

            if trades:
                # 勝率・損益計算
                wins = [t for t in trades if (t.get("pnl") or 0) > 0]
                self.result.win_rate = len(wins) / len(trades) * 100 if trades else 0.0

                pnls = [t.get("pnl", 0) or 0 for t in trades]
                self.result.total_pnl = sum(pnls)
                self.result.avg_pnl = self.result.total_pnl / len(trades) if trades else 0.0

                # 最大利益/損失
                if pnls:
                    self.result.max_profit = max(pnls) if max(pnls) > 0 else 0
                    self.result.max_loss = min(pnls) if min(pnls) < 0 else 0

                # TP/SL発動数
                self.result.tp_triggered_count = len(
                    [t for t in trades if t.get("trade_type") == "tp"]
                )
                self.result.sl_triggered_count = len(
                    [t for t in trades if t.get("trade_type") == "sl"]
                )

                # 最終取引時刻
                self.result.last_trade_time = trades[0].get("timestamp")

                # 戦略別統計（notesフィールドから戦略名を抽出）
                for strategy in self.STRATEGIES:
                    strategy_trades = [t for t in trades if strategy in (t.get("notes") or "")]
                    if strategy_trades:
                        s_pnls = [t.get("pnl", 0) or 0 for t in strategy_trades]
                        s_wins = [p for p in s_pnls if p > 0]
                        self.result.strategy_stats[strategy] = {
                            "trades": len(strategy_trades),
                            "win_rate": len(s_wins) / len(strategy_trades) * 100,
                            "pnl": sum(s_pnls),
                        }

            self.logger.info(
                f"取引履歴分析完了 - {self.result.trades_count}件, "
                f"勝率: {self.result.win_rate:.1f}%, 損益: ¥{self.result.total_pnl:,.0f}"
            )
        except Exception as e:
            self.logger.error(f"取引履歴分析失敗: {e}")

    async def _check_system_health(self):
        """システム健全性確認（6指標）"""
        # GCPログからエラー数・Container再起動を取得
        try:
            # サービス状態確認
            result = subprocess.run(
                [
                    "gcloud",
                    "run",
                    "services",
                    "describe",
                    "crypto-bot-service-prod",
                    "--region=asia-northeast1",
                    "--format=json",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                service_info = json.loads(result.stdout)
                conditions = service_info.get("status", {}).get("conditions", [])
                for cond in conditions:
                    if cond.get("type") == "Ready":
                        self.result.service_status = (
                            "Ready" if cond.get("status") == "True" else "NotReady"
                        )
                        break

                # 最新リビジョン時刻
                latest_revision = service_info.get("status", {}).get("latestReadyRevisionName", "")
                if latest_revision:
                    self.result.last_deploy_time = service_info.get("metadata", {}).get(
                        "creationTimestamp", ""
                    )
            else:
                self.result.service_status = "unknown"
                self.logger.warning("GCPサービス状態取得失敗（gcloud未設定?）")

        except subprocess.TimeoutExpired:
            self.logger.warning("GCPサービス確認タイムアウト")
            self.result.service_status = "timeout"
        except FileNotFoundError:
            self.logger.warning("gcloud CLIが見つかりません（ローカル実行?）")
            self.result.service_status = "local"
        except Exception as e:
            self.logger.warning(f"GCPサービス確認失敗: {e}")
            self.result.service_status = "error"

        # エラーログ数取得
        try:
            since_time = (datetime.now() - timedelta(hours=self.period_hours)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            result = subprocess.run(
                [
                    "gcloud",
                    "logging",
                    "read",
                    f'resource.type="cloud_run_revision" AND severity>=ERROR AND timestamp>="{since_time}"',
                    "--format=json",
                    "--limit=100",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                errors = json.loads(result.stdout) if result.stdout.strip() else []
                self.result.recent_error_count = len(errors)
            else:
                self.result.recent_error_count = -1  # 取得失敗

        except Exception as e:
            self.logger.warning(f"エラーログ取得失敗: {e}")
            self.result.recent_error_count = -1

        # Container再起動回数
        try:
            result = subprocess.run(
                [
                    "gcloud",
                    "logging",
                    "read",
                    f'textPayload:"Container called exit" AND timestamp>="{since_time}"',
                    "--format=json",
                    "--limit=100",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                restarts = json.loads(result.stdout) if result.stdout.strip() else []
                self.result.container_restart_count = len(restarts)
        except Exception as e:
            self.logger.warning(f"Container再起動数取得失敗: {e}")

        self.logger.info(
            f"システム健全性確認完了 - 状態: {self.result.service_status}, "
            f"エラー: {self.result.recent_error_count}件"
        )

    async def _check_tp_sl_placement(self):
        """TP/SL設置適切性確認（4指標）- Phase 58.1改善版"""
        try:
            if self.current_price <= 0:
                return

            # Phase 59.5: キャッシュされた注文を使用（API呼び出し削減＆タイミング整合性確保）
            active_orders = self._cached_active_orders or []

            tp_orders = [o for o in active_orders if o.get("type") == "limit"]
            sl_orders = [o for o in active_orders if o.get("type") in ["stop", "stop_limit"]]

            # TP距離計算
            if tp_orders and self.result.position_details:
                tp_price = tp_orders[0].get("price", 0)
                if tp_price:
                    self.result.tp_distance_pct = (
                        abs(tp_price - self.current_price) / self.current_price * 100
                    )

            # SL距離計算
            if sl_orders and self.result.position_details:
                sl_price = sl_orders[0].get("stopPrice") or sl_orders[0].get("triggerPrice", 0)
                if sl_price:
                    self.result.sl_distance_pct = (
                        abs(sl_price - self.current_price) / self.current_price * 100
                    )

            # ポジションがあるのにTP/SLがない場合
            if self.result.open_position_count > 0:
                if not tp_orders or not sl_orders:
                    self.result.tp_sl_placement_ok = False
                    self.logger.warning("ポジションがあるがTP/SLが設定されていません")

            # Phase 58.1: ポジション量とTP/SL注文量の整合性チェック
            if self.result.position_details and self.result.open_position_count > 0:
                # ポジション総量を計算
                total_position_amount = sum(
                    abs(float(pos.get("amount", 0))) for pos in self.result.position_details
                )

                # TP注文総量
                total_tp_amount = sum(
                    abs(float(o.get("amount", 0) or o.get("remaining", 0))) for o in tp_orders
                )

                # SL注文総量
                total_sl_amount = sum(
                    abs(float(o.get("amount", 0) or o.get("remaining", 0))) for o in sl_orders
                )

                # 許容誤差（0.1%）
                tolerance = 0.001

                # TP量不足チェック
                if total_position_amount > 0 and total_tp_amount > 0:
                    tp_coverage = total_tp_amount / total_position_amount
                    if tp_coverage < (1.0 - tolerance):
                        self.result.tp_sl_placement_ok = False
                        tp_pct = tp_coverage * 100
                        self.logger.warning(
                            f"⚠️ TP注文量不足: ポジション{total_position_amount:.4f}BTC vs "
                            f"TP注文{total_tp_amount:.4f}BTC (カバー率: {tp_pct:.1f}%)"
                        )

                # SL量不足チェック
                if total_position_amount > 0 and total_sl_amount > 0:
                    sl_coverage = total_sl_amount / total_position_amount
                    if sl_coverage < (1.0 - tolerance):
                        self.result.tp_sl_placement_ok = False
                        sl_pct = sl_coverage * 100
                        self.logger.warning(
                            f"⚠️ SL注文量不足: ポジション{total_position_amount:.4f}BTC vs "
                            f"SL注文{total_sl_amount:.4f}BTC (カバー率: {sl_pct:.1f}%)"
                        )

                # 注文数の記録（デバッグ用）
                self.logger.info(
                    f"TP/SL詳細 - ポジション: {total_position_amount:.4f}BTC, "
                    f"TP: {len(tp_orders)}件({total_tp_amount:.4f}BTC), "
                    f"SL: {len(sl_orders)}件({total_sl_amount:.4f}BTC)"
                )

            self.logger.info(
                f"TP/SL確認完了 - TP距離: {self.result.tp_distance_pct or 'N/A'}%, "
                f"SL距離: {self.result.sl_distance_pct or 'N/A'}%"
            )
        except Exception as e:
            self.logger.error(f"TP/SL確認失敗: {e}")

    async def _calculate_uptime(self):
        """稼働率計算（5指標）"""
        try:
            # Phase 59.5 Fix: UTC時刻を使用（GCPログはUTC保存）
            from datetime import timezone

            utc_now = datetime.now(timezone.utc)
            since_time = (utc_now - timedelta(hours=self.period_hours)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

            # 取引サイクル開始ログ数から稼働率を推定
            result = subprocess.run(
                [
                    "gcloud",
                    "logging",
                    "read",
                    f'resource.type="cloud_run_revision" AND textPayload:"取引サイクル開始" AND timestamp>="{since_time}"',
                    "--format=json",
                    "--limit=500",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                logs = json.loads(result.stdout) if result.stdout.strip() else []
                actual_runs = len(logs)

                # 期待される実行回数（5分間隔）
                expected_runs = self.period_hours * 12  # 1時間に12回

                # 結果を保存
                self.result.actual_cycle_count = actual_runs
                self.result.expected_cycle_count = expected_runs

                if expected_runs > 0:
                    self.result.uptime_rate = min(100.0, (actual_runs / expected_runs) * 100)
                    missed_runs = max(0, expected_runs - actual_runs)
                    self.result.total_downtime_minutes = missed_runs * 5  # 5分間隔

                self.logger.info(
                    f"稼働率計算完了 - {self.result.uptime_rate:.1f}% "
                    f"(実行{actual_runs}回/期待{expected_runs}回)"
                )

                # コンテナ再起動回数を取得
                restart_result = subprocess.run(
                    [
                        "gcloud",
                        "logging",
                        "read",
                        f'resource.type="cloud_run_revision" AND textPayload:"TradingOrchestrator依存性組み立て開始" AND timestamp>="{since_time}"',
                        "--format=json",
                        "--limit=50",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if restart_result.returncode == 0:
                    restart_logs = (
                        json.loads(restart_result.stdout) if restart_result.stdout.strip() else []
                    )
                    self.result.container_restart_count = len(restart_logs)
                    self.logger.info(f"コンテナ起動回数: {self.result.container_restart_count}回")
            else:
                # GCPログ取得失敗時
                self.result.uptime_rate = -1
                self.logger.warning("稼働率計算不可（GCPログ取得失敗）")

        except FileNotFoundError:
            # ローカル実行時（gcloudコマンドなし）
            self.result.uptime_rate = -1
            self.logger.info("稼働率計算スキップ（ローカル実行）")
        except Exception as e:
            self.logger.error(f"稼働率計算失敗: {e}")
            self.result.uptime_rate = -1


class LiveReportGenerator:
    """レポート生成"""

    def generate_json(self, result: LiveAnalysisResult) -> Dict[str, Any]:
        """JSON形式で出力"""
        return asdict(result)

    def generate_markdown(self, result: LiveAnalysisResult) -> str:
        """Markdown形式で出力"""
        lines = [
            "# ライブモード標準分析レポート",
            "",
            f"**分析日時**: {result.timestamp}",
            f"**対象期間**: 直近{result.analysis_period_hours}時間",
            "",
            "---",
            "",
            "## アカウント状態",
            "",
            "| 指標 | 値 | 状態 |",
            "|------|-----|------|",
        ]

        # 証拠金維持率の状態判定（ノーポジション時は明示的に表示）
        if result.open_position_count == 0 and result.margin_ratio >= 500:
            margin_display = "N/A"
            margin_status = "ポジションなし"
        else:
            margin_display = f"{result.margin_ratio:.1f}%"
            margin_status = (
                "正常"
                if result.margin_ratio >= 100
                else "注意" if result.margin_ratio >= 80 else "危険"
            )
        lines.append(f"| 証拠金維持率 | {margin_display} | {margin_status} |")
        lines.append(f"| 利用可能残高 | ¥{result.available_balance:,.0f} | - |")
        lines.append(f"| 使用中証拠金 | ¥{result.used_margin:,.0f} | - |")
        lines.append(f"| 未実現損益 | ¥{result.unrealized_pnl:+,.0f} | - |")
        lines.append(f"| マージンコール | {result.margin_call_status or 'なし'} | - |")

        lines.extend(
            [
                "",
                "---",
                "",
                "## ポジション状態",
                "",
                "| 指標 | 値 |",
                "|------|-----|",
                f"| オープンポジション | {result.open_position_count}件 |",
                f"| 未約定注文 | {result.pending_order_count}件 |",
            ]
        )

        if result.order_breakdown:
            breakdown_str = ", ".join(
                f"{k}:{v}" for k, v in result.order_breakdown.items() if v > 0
            )
            lines.append(f"| 注文内訳 | {breakdown_str or 'なし'} |")

        if result.losscut_price:
            lines.append(f"| ロスカット価格 | ¥{result.losscut_price:,.0f} |")

        # Phase 58.8: 孤児SL/TP警告
        if result.orphan_sl_detected:
            lines.append(f"| ⚠️ **孤児SL/TP注文** | **{result.orphan_order_count}件検出** |")

        lines.extend(
            [
                "",
                "---",
                "",
                "## 取引履歴分析",
                "",
                "| 指標 | 値 |",
                "|------|-----|",
                f"| 取引数 | {result.trades_count}件 |",
                f"| 勝率 | {result.win_rate:.1f}% |",
                f"| 総損益 | ¥{result.total_pnl:+,.0f} |",
                f"| 平均損益 | ¥{result.avg_pnl:+,.0f} |",
                f"| 最大利益 | ¥{result.max_profit:+,.0f} |",
                f"| 最大損失 | ¥{result.max_loss:+,.0f} |",
                f"| TP発動 | {result.tp_triggered_count}回 |",
                f"| SL発動 | {result.sl_triggered_count}回 |",
            ]
        )

        if result.strategy_stats:
            lines.extend(
                [
                    "",
                    "### 戦略別パフォーマンス",
                    "",
                    "| 戦略 | 取引数 | 勝率 | 損益 |",
                    "|------|--------|------|------|",
                ]
            )
            for strategy, stats in result.strategy_stats.items():
                lines.append(
                    f"| {strategy} | {stats['trades']}件 | {stats['win_rate']:.1f}% | ¥{stats['pnl']:+,.0f} |"
                )

        lines.extend(
            [
                "",
                "---",
                "",
                "## システム健全性",
                "",
                "| 指標 | 値 | 状態 |",
                "|------|-----|------|",
                f"| API応答時間 | {result.api_response_time_ms:.0f}ms | {'正常' if result.api_response_time_ms < 5000 else '遅延'} |",
                f"| サービス状態 | {result.service_status} | {'正常' if result.service_status == 'Ready' else '確認要'} |",
            ]
        )

        if result.recent_error_count >= 0:
            error_status = "正常" if result.recent_error_count < 10 else "注意"
            lines.append(f"| 直近エラー数 | {result.recent_error_count}件 | {error_status} |")

        lines.append(f"| Container再起動 | {result.container_restart_count}回 | - |")

        if result.last_trade_time:
            lines.append(f"| 最終取引 | {result.last_trade_time[:19]} | - |")

        if result.last_deploy_time:
            lines.append(f"| 最終デプロイ | {result.last_deploy_time[:19]} | - |")

        lines.extend(
            [
                "",
                "---",
                "",
                "## TP/SL設置適切性",
                "",
                "| 指標 | 値 | 状態 |",
                "|------|-----|------|",
            ]
        )

        if result.tp_distance_pct is not None:
            lines.append(f"| TP距離 | {result.tp_distance_pct:.2f}% | - |")
        if result.sl_distance_pct is not None:
            lines.append(f"| SL距離 | {result.sl_distance_pct:.2f}% | - |")

        tp_sl_status = "正常" if result.tp_sl_placement_ok else "要確認"
        lines.append(f"| TP/SL設置 | {tp_sl_status} | {tp_sl_status} |")

        lines.extend(
            [
                "",
                "---",
                "",
                "## 稼働率",
                "",
                "| 指標 | 値 | 状態 |",
                "|------|-----|------|",
            ]
        )

        if result.uptime_rate >= 0:
            uptime_status = "達成" if result.uptime_rate >= 90 else "未達"
            lines.append(f"| 稼働時間率 | {result.uptime_rate:.1f}% | {uptime_status} (目標90%) |")
            lines.append(
                f"| 実行回数 | {result.actual_cycle_count}回 / {result.expected_cycle_count}回 | - |"
            )
            lines.append(f"| ダウンタイム | {result.total_downtime_minutes:.0f}分 | - |")
            lines.append(f"| 再起動回数 | {result.container_restart_count}回 | - |")
        else:
            lines.append("| 稼働時間率 | 計測不可 | - |")

        if result.last_incident_time:
            lines.append(f"| 直近障害 | {result.last_incident_time} | - |")

        return "\n".join(lines)

    def append_to_csv(self, result: LiveAnalysisResult, csv_path: str):
        """CSV履歴に追記"""
        file_exists = Path(csv_path).exists()

        # フラット化したデータ
        row = {
            "timestamp": result.timestamp,
            "period_hours": result.analysis_period_hours,
            "margin_ratio": result.margin_ratio,
            "available_balance": result.available_balance,
            "used_margin": result.used_margin,
            "unrealized_pnl": result.unrealized_pnl,
            "open_positions": result.open_position_count,
            "pending_orders": result.pending_order_count,
            "trades_count": result.trades_count,
            "win_rate": result.win_rate,
            "total_pnl": result.total_pnl,
            "tp_triggered": result.tp_triggered_count,
            "sl_triggered": result.sl_triggered_count,
            "api_response_ms": result.api_response_time_ms,
            "error_count": result.recent_error_count,
            "restart_count": result.container_restart_count,
            "uptime_rate": result.uptime_rate,
            "actual_cycles": result.actual_cycle_count,
            "expected_cycles": result.expected_cycle_count,
            "service_status": result.service_status,
            "tp_sl_ok": result.tp_sl_placement_ok,
        }

        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=row.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)


async def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="ライブモード標準分析")
    parser.add_argument("--hours", type=int, default=24, help="分析対象期間（時間）")
    parser.add_argument(
        "--output", type=str, default="docs/検証記録/live", help="出力先ディレクトリ"
    )
    args = parser.parse_args()

    # 出力ディレクトリ作成
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 分析実行
    analyzer = LiveAnalyzer(period_hours=args.hours)
    result = await analyzer.analyze()

    # レポート生成
    generator = LiveReportGenerator()

    # ファイル名生成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON出力
    json_path = output_dir / f"live_analysis_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(generator.generate_json(result), f, ensure_ascii=False, indent=2)
    print(f"JSON出力: {json_path}")

    # Markdown出力
    md_path = output_dir / f"live_analysis_{timestamp}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(generator.generate_markdown(result))
    print(f"Markdown出力: {md_path}")

    # CSV履歴追記
    csv_path = output_dir / "live_analysis_history.csv"
    generator.append_to_csv(result, str(csv_path))
    print(f"CSV履歴追記: {csv_path}")

    # サマリー表示
    print("\n" + "=" * 50)
    print("ライブモード分析サマリー")
    print("=" * 50)
    print(f"分析期間: 直近{args.hours}時間")
    if result.open_position_count == 0 and result.margin_ratio >= 500:
        print("証拠金維持率: N/A (ポジションなし)")
    else:
        print(f"証拠金維持率: {result.margin_ratio:.1f}%")
    print(f"取引数: {result.trades_count}件")
    print(f"勝率: {result.win_rate:.1f}%")
    print(f"総損益: ¥{result.total_pnl:+,.0f}")
    if result.uptime_rate >= 0:
        print(f"稼働率: {result.uptime_rate:.1f}%")
    print(f"サービス状態: {result.service_status}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
