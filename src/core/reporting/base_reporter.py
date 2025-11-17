"""
基底レポートクラス - Phase 52.4

レポート生成の共通機能・インターフェースを提供。
各種レポート生成クラスの基底クラス。

主要機能:
- 統一レポート保存インターフェース（save_report・generate_error_report）
- JSON・Markdown両形式出力
- Discord埋め込み形式生成（format_discord_embed）
- 設定駆動型（thresholds.yaml: reporting.base_dir）
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

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

    def format_markdown(self, data: Dict, title: str = "レポート") -> str:
        """
        マークダウンフォーマット変換

        Args:
            data: レポートデータ
            title: レポートタイトル

        Returns:
            マークダウン形式文字列
        """
        markdown = f"# {title}\n\n"
        markdown += f"**生成日時**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n\n"

        # データをマークダウン形式で出力
        for key, value in data.items():
            if isinstance(value, dict):
                markdown += f"## {key}\n\n"
                for sub_key, sub_value in value.items():
                    markdown += f"- **{sub_key}**: {sub_value}\n"
                markdown += "\n"
            else:
                markdown += f"- **{key}**: {value}\n"

        return markdown

    def format_discord_embed(
        self, data: Dict, title: str = "レポート", color: Optional[int] = None
    ) -> Dict:
        """
        Discord通知用embed生成

        Args:
            data: レポートデータ
            title: embedタイトル
            color: embed色（Noneの場合はthresholds.yamlから取得）

        Returns:
            Discord embed辞書
        """
        # Phase 52.4: 色設定外部化（thresholds.yaml: reporting.discord.colors）
        if color is None:
            from ..config import get_threshold

            color = get_threshold("reporting.discord.colors.success", 0x00FF00)

        embed = {
            "title": title,
            "color": color,
            "timestamp": datetime.now().isoformat(),
            "fields": [],
        }

        # データをembedフィールドに変換
        for key, value in data.items():
            if isinstance(value, dict):
                # ネストしたデータは要約
                summary = ", ".join([f"{k}: {v}" for k, v in value.items()][:3])
                if len(value) > 3:
                    summary += "..."
                embed["fields"].append({"name": key, "value": summary, "inline": True})
            else:
                embed["fields"].append({"name": key, "value": str(value), "inline": True})

        return embed

    async def save_markdown_report(self, data: Dict, report_type: str, title: str) -> Path:
        """
        マークダウンレポート保存

        Args:
            data: レポートデータ
            report_type: レポート種別
            title: レポートタイトル

        Returns:
            保存されたファイルパス
        """
        try:
            # ディレクトリ作成
            report_dir = self.report_base_dir / report_type
            report_dir.mkdir(parents=True, exist_ok=True)

            # マークダウン生成
            markdown_content = self.format_markdown(data, title)

            # ファイル保存
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = report_dir / f"report_{timestamp}.md"

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            self.logger.info(f"📝 {report_type}マークダウンレポート保存: {file_path}")
            return file_path

        except Exception as e:
            self.logger.error(f"❌ マークダウンレポート保存失敗: {e}")
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
            "system_info": {"module": "BaseReporter", "phase": "22"},
        }

        return await self.save_report(error_data, "errors", "error")

    def get_report_summary(self, data: Dict) -> Dict[str, Any]:
        """
        レポートサマリー生成

        Args:
            data: レポートデータ

        Returns:
            サマリー情報
        """
        return {
            "total_fields": len(data),
            "has_nested_data": any(isinstance(v, dict) for v in data.values()),
            "timestamp": datetime.now().isoformat(),
            "data_size_bytes": len(str(data)),
        }
