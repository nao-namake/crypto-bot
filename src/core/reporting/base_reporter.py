"""
基底レポートクラス

レポート生成の共通機能・インターフェースを提供。
統一レポート保存インターフェース（save_report・save_error_report）。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from ..logger import CryptoBotLogger


class BaseReporter:
    """レポート生成の基底クラス"""

    def __init__(self, logger: CryptoBotLogger):
        """
        基底レポーター初期化

        Args:
            logger: ログシステム
        """
        self.logger = logger
        # 設定ファイルからパスを取得
        from ..config import get_threshold

        base_dir = get_threshold("reporting.base_dir", "logs/reports")
        self.report_base_dir = Path(base_dir)
        self.report_base_dir.mkdir(parents=True, exist_ok=True)

    async def save_report(self, data: Dict, report_type: str, file_prefix: str = "") -> Path:
        """
        統一レポート保存インターフェース

        Args:
            data: レポートデータ
            report_type: レポート種別（backtest/paper_trading/error）
            file_prefix: ファイル名プレフィックス

        Returns:
            保存されたファイルパス
        """
        try:
            # ディレクトリ作成
            report_dir = self.report_base_dir / report_type
            report_dir.mkdir(parents=True, exist_ok=True)

            # ファイル名生成
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            prefix = f"{file_prefix}_" if file_prefix else ""
            file_path = report_dir / f"{prefix}report_{timestamp}.json"

            # JSON保存
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)

            self.logger.info(f"📊 {report_type}レポート保存: {file_path}")
            return file_path

        except Exception as e:
            self.logger.error(f"❌ レポート保存失敗: {e}")
            raise

    async def save_error_report(self, error_message: str, context: Optional[Dict] = None) -> Path:
        """
        エラーレポート生成・保存

        Args:
            error_message: エラーメッセージ
            context: エラーコンテキスト

        Returns:
            保存されたファイルパス
        """
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "error_message": error_message,
            "context": context or {},
            "system_info": {"module": "BaseReporter", "phase": "64"},
        }

        return await self.save_report(error_data, "errors", "error")
