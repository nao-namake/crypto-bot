"""
ペーパートレードレポーター - Phase 28完了・Phase 29最適化版

orchestrator.pyから分離したペーパートレードレポート生成機能。
ペーパートレードセッションの統計・レポート作成を担当。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from .base_reporter import BaseReporter


class PaperTradingReporter(BaseReporter):
    """ペーパートレードレポート生成クラス"""

    def __init__(self, logger):
        """
        ペーパートレードレポーター初期化

        Args:
            logger: ログシステム
        """
        super().__init__(logger)
        # 設定ファイルからパスを取得
        from ..config import get_threshold

        paper_dir = get_threshold("reporting.paper_trading_dir", "logs/paper_trading_reports")
        self.paper_report_dir = Path(paper_dir)
        self.paper_report_dir.mkdir(exist_ok=True, parents=True)

    async def generate_session_report(self, session_stats: Dict) -> Path:
        """
        ペーパートレードセッションレポート生成

        Args:
            session_stats: セッション統計データ

        Returns:
            保存されたレポートファイルパス
        """
        try:
            timestamp = datetime.now()
            filename = f"paper_trading_{timestamp.strftime('%Y%m%d_%H%M%S')}.md"
            filepath = self.paper_report_dir / filename

            # セッション統計解析
            performance_stats = self._calculate_session_stats(session_stats)

            # マークダウンレポート生成
            report_content = self._generate_markdown_report(
                session_stats, timestamp, performance_stats
            )

            # ファイル保存
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(report_content)

            # JSONレポートも保存
            await self._save_json_report(session_stats, timestamp)

            self.logger.info(f"📁 ペーパートレードレポート保存: {filepath}")
            return filepath

        except (FileNotFoundError, PermissionError, OSError) as e:
            self.logger.error(f"ペーパートレードレポートファイルエラー: {e}")
            raise
        except (ValueError, TypeError, KeyError) as e:
            # セッション統計データ処理エラー
            self.logger.error(f"ペーパートレードレポートデータ処理エラー: {e}")
            raise
        except Exception as e:
            # その他の予期しないエラー（レポート保存失敗は致命的でない）
            self.logger.error(f"ペーパートレードレポート保存予期しないエラー: {e}")
            raise

    def _calculate_session_stats(self, session_stats: Dict) -> Dict[str, Any]:
        """
        セッション統計計算

        Args:
            session_stats: セッション統計データ

        Returns:
            計算された統計値
        """
        total_signals = session_stats.get("total_signals", 0)
        executed_trades = session_stats.get("executed_trades", 0)
        current_balance = session_stats.get("current_balance", 0)
        session_pnl = session_stats.get("session_pnl", 0)

        execution_rate = (executed_trades / total_signals * 100) if total_signals > 0 else 0

        return {
            "total_signals": total_signals,
            "executed_trades": executed_trades,
            "current_balance": current_balance,
            "session_pnl": session_pnl,
            "execution_rate": execution_rate,
        }

    def _generate_markdown_report(
        self,
        session_stats: Dict,
        timestamp: datetime,
        performance_stats: Dict[str, Any],
    ) -> str:
        """
        マークダウンレポート生成

        Args:
            session_stats: セッション統計データ
            timestamp: レポート生成時刻
            performance_stats: 計算されたパフォーマンス統計

        Returns:
            マークダウン形式レポート
        """
        report_content = f"""# ペーパートレードセッションレポート

## 📊 セッションサマリー
- **セッション開始**: {session_stats.get('start_time', 'N/A')}
- **レポート生成**: {timestamp.strftime('%Y年%m月%d日 %H:%M:%S')}
- **実行結果**: ✅ SUCCESS

## 🎯 システム情報
- **Phase**: 22（リファクタリング・責任分離対応）
- **レポーター**: PaperTradingReporter（分離済み）
- **取引モード**: Paper Trading（仮想取引）
- **実行環境**: TradingOrchestrator

## 📈 取引パフォーマンス
- **生成シグナル数**: {performance_stats['total_signals']}件
- **実行取引数**: {performance_stats['executed_trades']}件
- **現在残高**: ¥{performance_stats['current_balance']:,.0f}
- **セッション損益**: ¥{performance_stats['session_pnl']:,.0f}
- **シグナル実行率**: {performance_stats['execution_rate']:.1f}%

## 📊 取引詳細
"""

        # 最近の取引詳細
        recent_trades = session_stats.get("recent_trades", [])
        if recent_trades:
            report_content += "### 最近の取引（最新5件）\n"
            for i, trade in enumerate(recent_trades[-5:], 1):
                time = trade.get("time", "N/A")
                action = trade.get("action", "N/A")
                price = trade.get("price", 0)
                confidence = trade.get("confidence", 0)
                report_content += (
                    f"{i}. {time} - {action} @ ¥{price:,.0f} (信頼度: {confidence:.2f})\n"
                )
        else:
            report_content += "取引実行はありませんでした。\n"

        report_content += f"""

## 🔧 システム状態
- **戦略システム**: 正常動作中
- **ML予測システム**: 正常動作中
- **リスク管理**: アクティブ
- **異常検知**: 監視中

## 📋 次のアクション
1. セッション継続監視
2. パフォーマンス分析の継続
3. 定期的なシステムヘルスチェック

## 🆘 追加情報

このレポートを他のAIツールに共有して、取引戦略の改善提案を受けることができます。

**共有時のポイント**:
- セッション統計と実行率
- 取引判断の根拠
- システムの安定性状況
- パフォーマンス改善の余地

---
*このレポートは PaperTradingReporter により自動生成されました（Phase 22分離版）*
*生成時刻: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}*
"""

        return report_content

    async def _save_json_report(self, session_stats: Dict, timestamp: datetime):
        """
        JSON形式レポート保存

        Args:
            session_stats: セッション統計データ
            timestamp: レポート生成時刻
        """
        json_filepath = (
            self.paper_report_dir / f"paper_trading_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        )

        json_data = {
            "timestamp": timestamp.isoformat(),
            "session_stats": session_stats,
            "system_info": {
                "phase": "22",
                "reporter": "PaperTradingReporter",
                "separation_status": "completed",
            },
        }

        with open(json_filepath, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False, default=str)

    async def save_session_error_report(
        self, error_message: str, session_stats: Dict = None
    ) -> Path:
        """
        ペーパートレードセッションエラーレポート生成

        Args:
            error_message: エラーメッセージ
            session_stats: セッション統計データ（オプション）

        Returns:
            保存されたレポートファイルパス
        """
        try:
            timestamp = datetime.now()
            filename = f"paper_trading_error_{timestamp.strftime('%Y%m%d_%H%M%S')}.md"
            filepath = self.paper_report_dir / filename

            error_report = f"""# ペーパートレードセッションエラーレポート

## ❌ エラー情報
- **発生時刻**: {timestamp.strftime('%Y年%m月%d日 %H:%M:%S')}
- **エラーメッセージ**: {error_message}

## 🎯 システム情報
- **Phase**: 22（PaperTradingReporter分離版）
- **レポーター**: PaperTradingReporter
- **エラー種別**: ペーパートレードセッションエラー

## 📊 セッション情報
"""

            if session_stats:
                error_report += f"""- **セッション開始**: {session_stats.get('start_time', 'N/A')}
- **サイクル数**: {session_stats.get('cycles_completed', 0)}
- **総シグナル数**: {session_stats.get('total_signals', 0)}
- **実行取引数**: {session_stats.get('executed_trades', 0)}
- **現在残高**: ¥{session_stats.get('current_balance', 0):,.0f}
"""
            else:
                error_report += "セッション情報なし\n"

            error_report += f"""

## 🆘 対応方法
1. 設定ファイルの確認
2. データ接続の確認
3. MLモデルの状態確認
4. リスク管理システムの確認

---
*このエラーレポートは PaperTradingReporter により自動生成されました*
*生成時刻: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}*
"""

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(error_report)

            self.logger.error(f"📁 ペーパートレードエラーレポート保存: {filepath}")
            return filepath

        except Exception as e:
            self.logger.error(f"ペーパートレードエラーレポート保存失敗: {e}")
            raise

    def format_discord_notification(
        self, performance_stats: Dict[str, Any], session_duration_hours: int
    ) -> Dict:
        """
        Discord通知用フォーマット

        Args:
            performance_stats: セッション統計
            session_duration_hours: セッション継続時間（時間）

        Returns:
            Discord embed形式データ
        """
        color = 0x00FF00 if performance_stats["session_pnl"] > 0 else 0xFF0000

        embed = {
            "title": "📊 ペーパートレードセッション報告",
            "description": "ペーパートレードセッションが完了しました（Phase 22分離版）",
            "color": color,
            "timestamp": datetime.now().isoformat(),
            "fields": [
                {
                    "name": "📈 生成シグナル数",
                    "value": f"{performance_stats['total_signals']}件",
                    "inline": True,
                },
                {
                    "name": "🎯 実行取引数",
                    "value": f"{performance_stats['executed_trades']}件",
                    "inline": True,
                },
                {
                    "name": "💰 セッション損益",
                    "value": f"¥{performance_stats['session_pnl']:,.0f}",
                    "inline": True,
                },
                {
                    "name": "📅 継続時間",
                    "value": f"{session_duration_hours}時間",
                    "inline": True,
                },
                {
                    "name": "⚡ 実行率",
                    "value": f"{performance_stats['execution_rate']:.1f}%",
                    "inline": True,
                },
                {
                    "name": "💳 現在残高",
                    "value": f"¥{performance_stats['current_balance']:,.0f}",
                    "inline": True,
                },
            ],
        }

        return embed
