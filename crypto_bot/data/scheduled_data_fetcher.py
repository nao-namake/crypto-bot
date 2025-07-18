"""
ScheduledDataFetcher - 定時データ取得システム
Phase 3: 外部API復活実装の最終段階

機能:
- 定時データ取得・キャッシュ管理システム
- リアルタイム取得負荷削減
- 指標毎最適キャッシュ期間管理
- 自動更新・障害時延長利用
- バックグラウンドタスク管理
"""

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional

from ..monitoring.data_quality_monitor import get_quality_monitor
from .multi_source_fetcher import MultiSourceDataFetcher

logger = logging.getLogger(__name__)


class ScheduleType(Enum):
    """スケジュール種別"""

    INTERVAL = "interval"  # 一定間隔
    CRON = "cron"  # Cron式
    ADAPTIVE = "adaptive"  # 適応的間隔


@dataclass
class ScheduleConfig:
    """スケジュール設定"""

    fetcher_type: str
    schedule_type: ScheduleType
    interval_minutes: int = 60
    cron_expression: Optional[str] = None
    adaptive_min_minutes: int = 30
    adaptive_max_minutes: int = 240
    priority: int = 1
    enabled: bool = True

    # 品質ベース調整
    quality_based_adjustment: bool = True
    high_quality_extend_factor: float = 1.5  # 高品質時は間隔を1.5倍に
    low_quality_reduce_factor: float = 0.5  # 低品質時は間隔を0.5倍に

    # 市場時間ベース調整
    market_hours_adjustment: bool = True
    market_hours_factor: float = 0.8  # 市場時間中は間隔を0.8倍に
    off_hours_factor: float = 1.2  # 市場時間外は間隔を1.2倍に


@dataclass
class ScheduledTask:
    """スケジュール済みタスク"""

    task_id: str
    fetcher_type: str
    fetcher_instance: MultiSourceDataFetcher
    config: ScheduleConfig
    next_run: datetime
    last_run: Optional[datetime] = None
    last_success: Optional[datetime] = None
    consecutive_failures: int = 0
    total_runs: int = 0
    successful_runs: int = 0

    def success_rate(self) -> float:
        """成功率計算"""
        if self.total_runs == 0:
            return 0.0
        return self.successful_runs / self.total_runs


class ScheduledDataFetcher:
    """定時データ取得システム"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.schedule_config = self.config.get("scheduled_data_fetcher", {})

        # スケジュール管理
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}
        self.running = False
        self.scheduler_thread = None

        # 実行統計
        self.execution_stats = {
            "total_scheduled_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "quality_adjustments": 0,
            "market_adjustments": 0,
        }

        # 品質監視システム
        self.quality_monitor = get_quality_monitor(config)

        # パフォーマンス設定
        self.max_concurrent_fetches = self.schedule_config.get(
            "max_concurrent_fetches", 3
        )
        self.task_timeout_minutes = self.schedule_config.get("task_timeout_minutes", 10)
        self.health_check_interval = self.schedule_config.get(
            "health_check_interval", 300
        )  # 5分

        # 拡張キャッシュ設定
        self.cache_extension_factor = self.schedule_config.get(
            "cache_extension_factor", 2.0
        )
        self.emergency_cache_hours = self.schedule_config.get(
            "emergency_cache_hours", 48
        )

        logger.info("🔧 ScheduledDataFetcher initialized")
        logger.info(f"  - Max concurrent fetches: {self.max_concurrent_fetches}")
        logger.info(f"  - Task timeout: {self.task_timeout_minutes} minutes")
        logger.info(f"  - Health check interval: {self.health_check_interval} seconds")

    def register_fetcher(
        self,
        fetcher_type: str,
        fetcher_instance: MultiSourceDataFetcher,
        schedule_config: ScheduleConfig,
    ) -> str:
        """フェッチャー登録"""
        task_id = f"{fetcher_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 次回実行時刻計算
        next_run = self._calculate_next_run(schedule_config)

        # タスク作成
        task = ScheduledTask(
            task_id=task_id,
            fetcher_type=fetcher_type,
            fetcher_instance=fetcher_instance,
            config=schedule_config,
            next_run=next_run,
        )

        self.scheduled_tasks[task_id] = task

        logger.info(f"📅 Registered scheduled fetcher: {fetcher_type}")
        logger.info(f"  - Task ID: {task_id}")
        logger.info(f"  - Next run: {next_run}")
        logger.info(f"  - Schedule: {schedule_config.schedule_type.value}")

        return task_id

    def _calculate_next_run(self, schedule_config: ScheduleConfig) -> datetime:
        """次回実行時刻計算"""
        now = datetime.now()

        if schedule_config.schedule_type == ScheduleType.INTERVAL:
            # 一定間隔スケジュール
            base_interval = schedule_config.interval_minutes

            # 品質ベース調整
            if schedule_config.quality_based_adjustment:
                base_interval = self._adjust_interval_by_quality(
                    base_interval, schedule_config.fetcher_type, schedule_config
                )

            # 市場時間ベース調整
            if schedule_config.market_hours_adjustment:
                base_interval = self._adjust_interval_by_market_hours(
                    base_interval, schedule_config
                )

            return now + timedelta(minutes=base_interval)

        elif schedule_config.schedule_type == ScheduleType.ADAPTIVE:
            # 適応的間隔スケジュール
            return self._calculate_adaptive_interval(schedule_config)

        elif schedule_config.schedule_type == ScheduleType.CRON:
            # Cron式スケジュール（簡易実装）
            return self._calculate_cron_next_run(schedule_config)

        # デフォルトは1時間後
        return now + timedelta(hours=1)

    def _adjust_interval_by_quality(
        self, base_interval: int, fetcher_type: str, schedule_config: ScheduleConfig
    ) -> int:
        """品質ベース間隔調整"""
        try:
            # 品質監視システムから最新の品質スコア取得
            quality_summary = self.quality_monitor.get_quality_summary()
            source_stats = quality_summary.get("source_statistics", {})

            # 該当フェッチャーの品質スコア取得
            quality_score = 0.7  # デフォルト
            for source_key, stats in source_stats.items():
                if fetcher_type in source_key:
                    quality_score = stats.get("last_quality_score", 0.7)
                    break

            # 品質スコアに基づく調整
            if quality_score >= 0.9:
                # 高品質：間隔を延長
                adjusted_interval = int(
                    base_interval * schedule_config.high_quality_extend_factor
                )
                self.execution_stats["quality_adjustments"] += 1
                logger.info(
                    "🔍 Quality-based interval extension: %d -> %d minutes "
                    "(quality: %.3f)",
                    base_interval,
                    adjusted_interval,
                    quality_score,
                )
            elif quality_score < 0.6:
                # 低品質：間隔を短縮
                adjusted_interval = int(
                    base_interval * schedule_config.low_quality_reduce_factor
                )
                self.execution_stats["quality_adjustments"] += 1
                logger.info(
                    "🔍 Quality-based interval reduction: %d -> %d minutes "
                    "(quality: %.3f)",
                    base_interval,
                    adjusted_interval,
                    quality_score,
                )
            else:
                # 通常品質：そのまま
                adjusted_interval = base_interval

            return adjusted_interval

        except Exception as e:
            logger.error(f"❌ Quality-based interval adjustment failed: {e}")
            return base_interval

    def _adjust_interval_by_market_hours(
        self, base_interval: int, schedule_config: ScheduleConfig
    ) -> int:
        """市場時間ベース間隔調整"""
        try:
            now = datetime.now()

            # 日本時間での市場時間判定（簡易実装）
            # 平日9:00-15:00を主要な市場時間として扱う
            is_weekday = now.weekday() < 5  # 0=月曜日, 6=日曜日
            is_market_hours = 9 <= now.hour < 15

            if is_weekday and is_market_hours:
                # 市場時間中：間隔を短縮
                adjusted_interval = int(
                    base_interval * schedule_config.market_hours_factor
                )
                self.execution_stats["market_adjustments"] += 1
                logger.info(
                    "🏪 Market hours interval reduction: %d -> %d minutes",
                    base_interval,
                    adjusted_interval,
                )
            else:
                # 市場時間外：間隔を延長
                adjusted_interval = int(
                    base_interval * schedule_config.off_hours_factor
                )
                self.execution_stats["market_adjustments"] += 1
                logger.info(
                    "🌙 Off-hours interval extension: %d -> %d minutes",
                    base_interval,
                    adjusted_interval,
                )

            return adjusted_interval

        except Exception as e:
            logger.error(f"❌ Market hours interval adjustment failed: {e}")
            return base_interval

    def _calculate_adaptive_interval(self, schedule_config: ScheduleConfig) -> datetime:
        """適応的間隔計算"""
        now = datetime.now()

        # 成功率ベースの間隔調整
        # 高成功率 -> 長い間隔
        # 低成功率 -> 短い間隔

        # 簡易実装：中間値を使用
        adaptive_interval = (
            schedule_config.adaptive_min_minutes + schedule_config.adaptive_max_minutes
        ) / 2

        return now + timedelta(minutes=adaptive_interval)

    def _calculate_cron_next_run(self, schedule_config: ScheduleConfig) -> datetime:
        """Cron式次回実行時刻計算（簡易実装）"""
        now = datetime.now()

        # 簡易実装：1時間ごとに実行
        next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        return next_hour

    def start_scheduler(self) -> None:
        """スケジューラー開始"""
        if self.running:
            logger.warning("⚠️ Scheduler is already running")
            return

        self.running = True
        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop, daemon=True
        )
        self.scheduler_thread.start()

        logger.info("🚀 ScheduledDataFetcher started")
        logger.info(f"  - Scheduled tasks: {len(self.scheduled_tasks)}")

    def stop_scheduler(self) -> None:
        """スケジューラー停止"""
        self.running = False

        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)

        logger.info("🛑 ScheduledDataFetcher stopped")

    def _scheduler_loop(self) -> None:
        """スケジューラーメインループ"""
        logger.info("📅 Scheduler loop started")

        while self.running:
            try:
                current_time = datetime.now()

                # 実行すべきタスクを検索
                tasks_to_run = []
                for _task_id, task in self.scheduled_tasks.items():
                    if task.config.enabled and current_time >= task.next_run:
                        tasks_to_run.append(task)

                # 優先度でソート
                tasks_to_run.sort(key=lambda t: t.config.priority)

                # 並行実行制限
                if len(tasks_to_run) > self.max_concurrent_fetches:
                    tasks_to_run = tasks_to_run[: self.max_concurrent_fetches]

                # タスク実行
                for task in tasks_to_run:
                    self._execute_scheduled_task(task)

                # ヘルスチェック
                self._perform_health_check()

                # 短い間隔で再チェック
                time.sleep(30)  # 30秒間隔

            except Exception as e:
                logger.error(f"❌ Scheduler loop error: {e}")
                time.sleep(60)  # エラー時は1分待機

    def _execute_scheduled_task(self, task: ScheduledTask) -> None:
        """スケジュール済みタスク実行"""
        try:
            logger.info(f"🔄 Executing scheduled task: {task.fetcher_type}")

            start_time = time.time()

            # タスク実行
            task.last_run = datetime.now()
            task.total_runs += 1
            self.execution_stats["total_scheduled_runs"] += 1

            # フェッチャーからデータ取得
            data = task.fetcher_instance.get_data()

            execution_time = time.time() - start_time

            if data is not None and not data.empty:
                # 成功処理
                task.last_success = datetime.now()
                task.successful_runs += 1
                task.consecutive_failures = 0
                self.execution_stats["successful_runs"] += 1

                logger.info(
                    f"✅ Scheduled task completed successfully: {task.fetcher_type}"
                )
                logger.info(f"  - Data records: {len(data)}")
                logger.info(f"  - Execution time: {execution_time:.2f}s")
                logger.info(f"  - Success rate: {task.success_rate():.2f}")

                # キャッシュヒット/ミス統計
                if execution_time < 1.0:  # 1秒未満はキャッシュヒットと判定
                    self.execution_stats["cache_hits"] += 1
                else:
                    self.execution_stats["cache_misses"] += 1

            else:
                # 失敗処理
                task.consecutive_failures += 1
                self.execution_stats["failed_runs"] += 1

                logger.warning(f"⚠️ Scheduled task failed: {task.fetcher_type}")
                logger.warning(f"  - Consecutive failures: {task.consecutive_failures}")

                # 連続失敗時の対応
                if task.consecutive_failures >= 3:
                    logger.error(
                        "❌ Task disabled due to consecutive failures: %s",
                        task.fetcher_type,
                    )
                    task.config.enabled = False

            # 次回実行時刻計算
            task.next_run = self._calculate_next_run(task.config)

            logger.info(f"📅 Next run scheduled: {task.next_run}")

        except Exception as e:
            logger.error(
                f"❌ Scheduled task execution failed: {task.fetcher_type} - {e}"
            )
            task.consecutive_failures += 1
            self.execution_stats["failed_runs"] += 1

    def _perform_health_check(self) -> None:
        """ヘルスチェック実行"""
        try:
            current_time = datetime.now()

            # 無効化されたタスクの確認
            disabled_tasks = [
                task
                for task in self.scheduled_tasks.values()
                if not task.config.enabled
            ]

            if disabled_tasks:
                logger.warning(f"⚠️ Health check: {len(disabled_tasks)} tasks disabled")

                # 回復可能性チェック
                for task in disabled_tasks:
                    if task.consecutive_failures >= 5:
                        # 5回連続失敗したタスクは一時的に再有効化を試す
                        logger.info(
                            f"🔄 Attempting to re-enable task: {task.fetcher_type}"
                        )
                        task.config.enabled = True
                        task.consecutive_failures = 0
                        task.next_run = current_time + timedelta(minutes=5)

            # 統計情報ログ
            total_runs = self.execution_stats["total_scheduled_runs"]
            if total_runs > 0:
                success_rate = self.execution_stats["successful_runs"] / total_runs
                cache_hit_rate = self.execution_stats["cache_hits"] / total_runs

                logger.info("📊 Health check stats:")
                logger.info(f"  - Total runs: {total_runs}")
                logger.info(f"  - Success rate: {success_rate:.2f}")
                logger.info(f"  - Cache hit rate: {cache_hit_rate:.2f}")
                logger.info(
                    "  - Quality adjustments: %d",
                    self.execution_stats["quality_adjustments"],
                )
                logger.info(
                    "  - Market adjustments: %d",
                    self.execution_stats["market_adjustments"],
                )

        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")

    def get_task_status(self) -> Dict[str, Any]:
        """タスク状態取得"""
        status = {
            "running": self.running,
            "total_tasks": len(self.scheduled_tasks),
            "enabled_tasks": len(
                [t for t in self.scheduled_tasks.values() if t.config.enabled]
            ),
            "disabled_tasks": len(
                [t for t in self.scheduled_tasks.values() if not t.config.enabled]
            ),
            "execution_stats": self.execution_stats.copy(),
            "tasks": {},
        }

        for task_id, task in self.scheduled_tasks.items():
            status["tasks"][task_id] = {
                "fetcher_type": task.fetcher_type,
                "enabled": task.config.enabled,
                "next_run": task.next_run.isoformat(),
                "last_run": task.last_run.isoformat() if task.last_run else None,
                "last_success": (
                    task.last_success.isoformat() if task.last_success else None
                ),
                "success_rate": task.success_rate(),
                "consecutive_failures": task.consecutive_failures,
                "total_runs": task.total_runs,
                "schedule_type": task.config.schedule_type.value,
                "interval_minutes": task.config.interval_minutes,
            }

        return status

    def get_cache_statistics(self) -> Dict[str, Any]:
        """キャッシュ統計取得"""
        stats = {
            "total_cache_requests": self.execution_stats["cache_hits"]
            + self.execution_stats["cache_misses"],
            "cache_hit_rate": 0.0,
            "cache_miss_rate": 0.0,
            "fetcher_cache_info": {},
        }

        total_requests = stats["total_cache_requests"]
        if total_requests > 0:
            stats["cache_hit_rate"] = (
                self.execution_stats["cache_hits"] / total_requests
            )
            stats["cache_miss_rate"] = (
                self.execution_stats["cache_misses"] / total_requests
            )

        # 各フェッチャーのキャッシュ情報
        for _task_id, task in self.scheduled_tasks.items():
            cache_info = task.fetcher_instance.get_cache_info()
            stats["fetcher_cache_info"][task.fetcher_type] = cache_info

        return stats

    def force_refresh_cache(self, fetcher_type: Optional[str] = None) -> Dict[str, Any]:
        """キャッシュ強制リフレッシュ"""
        results = {}

        target_tasks = []
        if fetcher_type:
            # 特定フェッチャーのみ
            target_tasks = [
                task
                for task in self.scheduled_tasks.values()
                if task.fetcher_type == fetcher_type
            ]
        else:
            # 全フェッチャー
            target_tasks = list(self.scheduled_tasks.values())

        for task in target_tasks:
            try:
                logger.info(f"🔄 Force refreshing cache: {task.fetcher_type}")

                # キャッシュをクリア
                task.fetcher_instance.cache_data = None
                task.fetcher_instance.cache_timestamp = None

                # データ取得
                data = task.fetcher_instance.get_data()

                if data is not None and not data.empty:
                    results[task.fetcher_type] = {
                        "success": True,
                        "records": len(data),
                        "timestamp": datetime.now().isoformat(),
                    }
                    logger.info(
                        f"✅ Cache refreshed: {task.fetcher_type} - {len(data)} records"
                    )
                else:
                    results[task.fetcher_type] = {
                        "success": False,
                        "error": "No data returned",
                        "timestamp": datetime.now().isoformat(),
                    }
                    logger.warning(f"⚠️ Cache refresh failed: {task.fetcher_type}")

            except Exception as e:
                results[task.fetcher_type] = {
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
                logger.error(f"❌ Cache refresh error: {task.fetcher_type} - {e}")

        return results


# グローバルインスタンス
_scheduled_fetcher = None


def get_scheduled_fetcher(
    config: Optional[Dict[str, Any]] = None,
) -> ScheduledDataFetcher:
    """スケジュール済みフェッチャー取得（シングルトン）"""
    global _scheduled_fetcher
    if _scheduled_fetcher is None:
        _scheduled_fetcher = ScheduledDataFetcher(config)
    return _scheduled_fetcher


def initialize_scheduled_fetchers(config: Dict[str, Any]) -> ScheduledDataFetcher:
    """スケジュール済みフェッチャー初期化"""
    scheduler = get_scheduled_fetcher(config)

    # VIXフェッチャー登録
    try:
        from .vix_fetcher import VIXDataFetcher

        vix_fetcher = VIXDataFetcher(config)
        vix_schedule = ScheduleConfig(
            fetcher_type="vix",
            schedule_type=ScheduleType.INTERVAL,
            interval_minutes=60,  # 1時間間隔
            priority=1,
            quality_based_adjustment=True,
            market_hours_adjustment=True,
        )
        scheduler.register_fetcher("vix", vix_fetcher, vix_schedule)
    except ImportError:
        logger.warning("⚠️ VIX fetcher not available for scheduling")

    # Fear&Greedフェッチャー登録
    try:
        from .fear_greed_fetcher import FearGreedDataFetcher

        fg_fetcher = FearGreedDataFetcher(config)
        fg_schedule = ScheduleConfig(
            fetcher_type="fear_greed",
            schedule_type=ScheduleType.INTERVAL,
            interval_minutes=120,  # 2時間間隔
            priority=2,
            quality_based_adjustment=True,
            market_hours_adjustment=True,
        )
        scheduler.register_fetcher("fear_greed", fg_fetcher, fg_schedule)
    except ImportError:
        logger.warning("⚠️ Fear&Greed fetcher not available for scheduling")

    return scheduler
