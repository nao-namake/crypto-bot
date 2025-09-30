"""
バックテストランナー - Phase 28完了・Phase 29最適化版

Phase 28完了・Phase 29最適化：
- ペーパートレードと同じアプローチでCSVデータからバックテスト実行
- 本番と同一のtrading_cycle_managerを使用
- CSVデータを時系列で順次処理し、各時点で取引判定を実行
- リアルタイム処理をシミュレートし、ルックアヘッドを防止

設計原則:
- 本番とペーパートレードの同一ロジック使用
- CSVデータによる高速・安定したデータ供給
- 時刻シミュレーションによる正確な時系列処理
- BacktestReporterによる詳細なレポート生成
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd

from ..config import get_threshold
from .base_runner import BaseRunner


class BacktestRunner(BaseRunner):
    """バックテストモード実行クラス（Phase 28完了・Phase 29最適化版）"""

    def __init__(self, orchestrator_ref, logger):
        """
        バックテストランナー初期化

        Args:
            orchestrator_ref: TradingOrchestratorへの参照
            logger: ログシステム
        """
        super().__init__(orchestrator_ref, logger)

        # バックテスト状態管理
        self.backtest_start = None
        self.backtest_end = None
        self.current_timestamp = None
        self.csv_data = {}  # タイムフレーム別CSVデータ
        self.data_index = 0  # 現在の処理位置
        self.total_data_points = 0

        # バックテスト設定（Phase 28完了・Phase 29最適化）
        self.symbol = get_threshold("backtest.symbol", "BTC/JPY")
        self.timeframes = get_threshold("backtest.timeframes", ["15m", "4h"])
        self.lookback_window = get_threshold(
            "backtest.lookback_window", 100
        )  # 各時点で過去N件のデータを供給

        # 統計情報
        self.cycle_count = 0
        self.processed_timestamps = []
        self.session_stats = {}

    async def run(self) -> bool:
        """
        バックテストモード実行

        Returns:
            実行成功・失敗
        """
        try:
            self.logger.info("📊 バックテストモード開始（Phase 22・ハードコード排除版）")

            # 1. バックテスト期間設定
            await self._setup_backtest_period()

            # 2. CSVデータ読み込み
            await self._load_csv_data()

            # 3. データ検証
            if not await self._validate_data():
                self.logger.error("❌ CSVデータが不十分です")
                return False

            # 4. 時系列バックテスト実行
            await self._run_time_series_backtest()

            # 5. 最終レポート生成
            await self._generate_final_backtest_report()

            self.logger.info("✅ バックテスト実行完了", discord_notify=True)
            return True

        except Exception as e:
            self.logger.error(f"❌ バックテスト実行エラー: {e}", discord_notify=True)
            await self._save_error_report(str(e))
            raise

    async def _setup_backtest_period(self):
        """バックテスト期間設定"""
        # 外部設定から期間を取得
        backtest_days = get_threshold("execution.backtest_period_days", 30)

        self.backtest_end = datetime.now()
        self.backtest_start = self.backtest_end - timedelta(days=backtest_days)

        self.logger.info(
            f"📅 バックテスト期間: {self.backtest_start.strftime('%Y-%m-%d')} "
            f"~ {self.backtest_end.strftime('%Y-%m-%d')} ({backtest_days}日間)"
        )

    async def _load_csv_data(self):
        """CSVデータ読み込み"""
        try:
            # CSV データローダーを使用
            from ...backtest.data.csv_data_loader import get_csv_loader

            csv_loader = get_csv_loader()

            # マルチタイムフレームデータ読み込み
            self.csv_data = csv_loader.load_multi_timeframe(
                symbol=self.symbol,
                timeframes=self.timeframes,
                start_date=self.backtest_start,
                end_date=self.backtest_end,
                limit=get_threshold("backtest.data_limit", 10000),  # 十分な量を確保
            )

            # 設定からメインタイムフレームを取得
            main_timeframe = self.timeframes[0] if self.timeframes else "4h"

            if (
                not self.csv_data
                or main_timeframe not in self.csv_data
                or self.csv_data[main_timeframe].empty
            ):
                raise ValueError(f"主要データ（{main_timeframe}）が不足: {self.symbol}")

            # データ統計
            self.total_data_points = len(self.csv_data[main_timeframe])

            # タイムフレーム別データ統計を動的に生成
            timeframe_stats = []
            for tf in self.timeframes:
                count = len(self.csv_data.get(tf, []))
                timeframe_stats.append(f"{tf}:{count}件")

            self.logger.info(f"📈 CSVデータ読み込み完了: {', '.join(timeframe_stats)}")

        except Exception as e:
            self.logger.error(f"❌ CSVデータ読み込みエラー: {e}")
            raise

    async def _validate_data(self) -> bool:
        """データ検証"""
        min_data_points = get_threshold("backtest.min_data_points", 50)

        if self.total_data_points < min_data_points:
            self.logger.warning(
                f"⚠️ データが不足: {self.total_data_points}件 " f"（最小{min_data_points}件必要）"
            )
            return False

        # データ品質チェック
        main_timeframe = self.timeframes[0] if self.timeframes else "4h"
        main_data = self.csv_data[main_timeframe]
        if main_data.isnull().any().any():
            self.logger.warning("⚠️ データに欠損値が含まれています")

        if not main_data.index.is_monotonic_increasing:
            self.logger.warning("⚠️ データが時系列順序になっていません")

        return True

    async def _run_time_series_backtest(self):
        """時系列バックテスト実行"""
        main_timeframe = self.timeframes[0] if self.timeframes else "4h"
        main_data = self.csv_data[main_timeframe]

        # データを時系列順で処理
        for i in range(self.lookback_window, len(main_data)):
            self.data_index = i
            self.current_timestamp = main_data.index[i]

            # 進捗表示
            progress_interval = get_threshold("backtest.progress_interval", 50)
            if i % progress_interval == 0:
                progress = (i / len(main_data)) * 100
                self.logger.info(
                    f"📊 バックテスト進行中: {progress:.1f}% "
                    f"({i}/{len(main_data)}) - {self.current_timestamp.strftime('%Y-%m-%d %H:%M')}"
                )

            # 現在時点のデータを準備
            await self._setup_current_market_data()

            # 取引サイクル実行（本番と同じロジック）
            try:
                await self.orchestrator.run_trading_cycle()
                self.cycle_count += 1
                self.processed_timestamps.append(self.current_timestamp)

            except Exception as e:
                self.logger.warning(f"⚠️ 取引サイクルエラー ({self.current_timestamp}): {e}")
                continue

            # バックテスト専用の進捗保存（定期的）
            report_interval = get_threshold("backtest.report_interval", 100)
            if i % report_interval == 0:
                await self._save_progress_report()

    async def _setup_current_market_data(self):
        """現在時点の市場データを準備"""
        # グローバル時刻をバックテスト時刻に設定
        await self._set_simulated_time(self.current_timestamp)

        # 各タイムフレームのデータを準備
        current_market_data = {}

        for timeframe, df in self.csv_data.items():
            if df.empty:
                continue

            # 現在時刻以前のデータのみ使用（ルックアヘッド防止）
            available_data = df[df.index <= self.current_timestamp]

            if len(available_data) >= self.lookback_window:
                current_market_data[timeframe] = available_data.tail(self.lookback_window)
            else:
                current_market_data[timeframe] = available_data

        # データサービスにバックテスト用データを設定
        self.orchestrator.data_service.set_backtest_data(current_market_data)

    async def _set_simulated_time(self, timestamp: datetime):
        """シミュレーション時刻設定"""
        # グローバル時刻管理クラスがあれば設定
        # 現在は実装せず、将来的に時刻シミュレーションを追加
        pass

    async def _save_progress_report(self):
        """進捗レポート保存"""
        try:
            progress_stats = {
                "current_timestamp": self.current_timestamp,
                "progress_percentage": (self.data_index / self.total_data_points) * 100,
                "cycles_completed": self.cycle_count,
                "processed_data_points": len(self.processed_timestamps),
            }

            # バックテストレポーターに進捗保存
            await self.orchestrator.backtest_reporter.save_progress_report(progress_stats)

        except Exception as e:
            self.logger.warning(f"⚠️ 進捗レポート保存エラー: {e}")

    async def _generate_final_backtest_report(self):
        """最終バックテストレポート生成"""
        try:
            # 最終統計収集
            final_stats = {
                "backtest_period": {
                    "start": self.backtest_start,
                    "end": self.backtest_end,
                    "duration_days": (self.backtest_end - self.backtest_start).days,
                },
                "data_processing": {
                    "total_data_points": self.total_data_points,
                    "processed_cycles": self.cycle_count,
                    "processed_timestamps": len(self.processed_timestamps),
                    "success_rate": len(self.processed_timestamps) / self.total_data_points * 100,
                },
                "timeframes": list(self.csv_data.keys()),
                "symbol": self.symbol,
            }

            # バックテストレポーター経由で詳細レポート生成
            await self.orchestrator.backtest_reporter.generate_backtest_report(
                final_stats, self.backtest_start, self.backtest_end
            )

        except Exception as e:
            self.logger.error(f"❌ 最終レポート生成エラー: {e}")

    async def _save_error_report(self, error_message: str):
        """エラーレポート保存"""
        try:
            context = {
                "backtest_runner": "Phase22_BacktestRunner",
                "current_timestamp": self.current_timestamp,
                "data_index": self.data_index,
                "cycle_count": self.cycle_count,
            }

            await self.orchestrator.backtest_reporter.save_error_report(error_message, context)

        except Exception as e:
            self.logger.warning(f"⚠️ エラーレポート保存失敗: {e}")
