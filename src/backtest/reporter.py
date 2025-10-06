"""
バックテストレポートシステム - Phase 28完了・Phase 29最適化版・本番同一ロジック対応

Phase 29最適化:
- BacktestEngineとの依存関係を廃止
- 本番と同じ取引ロジック結果のレポート生成
- シンプルで保守しやすいレポート機能
- CSVデータと統合したバックテスト結果出力

主要機能:
- JSON形式レポート生成
- 進捗レポート（時系列バックテスト用）
- エラーレポート（デバッグ用）
- 簡易統計レポート
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from ..core.logger import get_logger


class BacktestReporter:
    """
    バックテストレポート生成システム（Phase 29最適化版）

    本番同一ロジックバックテスト用のシンプルなレポート機能。
    """

    def __init__(self, output_dir: Optional[str] = None):
        self.logger = get_logger(__name__)

        # 出力ディレクトリ設定（Phase 29: バックテスト統合フォルダ）
        if output_dir is None:
            # src/backtest/logs/ 配下に保存（集約済み）
            base_dir = Path(__file__).parent / "logs"
        else:
            base_dir = Path(output_dir)
        self.output_dir = base_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"BacktestReporter初期化完了: {self.output_dir}")

    async def generate_backtest_report(
        self, final_stats: Dict[str, Any], start_date: datetime, end_date: datetime
    ) -> str:
        """
        バックテストレポート生成（Phase 29最適化）

        Args:
            final_stats: バックテスト統計データ
            start_date: バックテスト開始日
            end_date: バックテスト終了日

        Returns:
            生成されたレポートファイルパス
        """
        self.logger.info("バックテストレポート生成開始")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backtest_{timestamp}.json"
        filepath = self.output_dir / filename

        try:
            # レポートデータ構築
            # Phase 35.5: 型チェック追加（文字列/datetime両対応）
            start_date_str = start_date if isinstance(start_date, str) else start_date.isoformat()
            end_date_str = end_date if isinstance(end_date, str) else end_date.isoformat()

            report_data = {
                "backtest_info": {
                    "start_date": start_date_str,
                    "end_date": end_date_str,
                    "duration_days": (
                        (end_date - start_date).days
                        if isinstance(start_date, datetime) and isinstance(end_date, datetime)
                        else 0
                    ),
                    "generated_at": datetime.now().isoformat(),
                    "phase": "Phase_35_最適化版",
                },
                "execution_stats": final_stats,
                "system_info": {
                    "runner_type": "BacktestRunner",
                    "data_source": "CSV",
                    "logic_type": "本番同一ロジック",
                },
            }

            # JSONファイル保存
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"バックテストレポート生成完了: {filepath}")
            return str(filepath)

        except Exception as e:
            self.logger.error(f"レポート生成エラー: {e}")
            raise

    async def save_progress_report(self, progress_stats: Dict[str, Any]) -> str:
        """
        進捗レポート保存（時系列バックテスト用）

        Args:
            progress_stats: 進捗統計データ

        Returns:
            保存されたファイルパス
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"progress_{timestamp}.json"
            filepath = self.output_dir / filename

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(progress_stats, f, ensure_ascii=False, indent=2, default=str)

            self.logger.debug(f"進捗レポート保存: {filepath}")
            return str(filepath)

        except Exception as e:
            self.logger.warning(f"進捗レポート保存エラー: {e}")
            raise

    async def save_error_report(self, error_message: str, context: Dict[str, Any]) -> str:
        """
        エラーレポート保存

        Args:
            error_message: エラーメッセージ
            context: エラーコンテキスト

        Returns:
            保存されたファイルパス
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"error_{timestamp}.json"
            filepath = self.output_dir / filename

            error_data = {
                "error_message": error_message,
                "context": context,
                "timestamp": datetime.now().isoformat(),
                "phase": "Phase_29_BacktestSystem",
            }

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(error_data, f, ensure_ascii=False, indent=2, default=str)

            self.logger.info(f"エラーレポート保存: {filepath}")
            return str(filepath)

        except Exception as e:
            self.logger.error(f"エラーレポート保存失敗: {e}")
            raise
