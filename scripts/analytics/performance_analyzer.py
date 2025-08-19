#!/usr/bin/env python
"""
Phase 12: パフォーマンス分析ツール（BaseAnalyzer活用版）

レガシーシステムの良い部分を継承・改良:
- signal_monitor.py の監視ロジック
- error_analyzer.py の分析機能
- ops_monitor.py の包括的チェック

BaseAnalyzer活用により約100行のCloud Run重複コードを削除:
- gcloudコマンド実行
- エラーログ取得
- 取引ログ取得
- サービスヘルス確認

機能:
- 実取引データ分析
- システムパフォーマンス評価
- 24時間監視結果サマリー
- 継続的改善レポート生成
"""

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

# base_analyzer.py活用
sys.path.append(str(Path(__file__).parent))
from base_analyzer import BaseAnalyzer

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PerformanceAnalyzer(BaseAnalyzer):
    """システムパフォーマンス分析クラス（BaseAnalyzer活用版・約100行重複コード削除）"""

    def __init__(
        self,
        project_id: str = "my-crypto-bot-project",
        service_name: str = "crypto-bot-service",
        region: str = "asia-northeast1"
    ):
        # base_analyzer.py初期化
        super().__init__(project_id, service_name, region, output_dir="logs/performance_analysis")
        
        # レポート出力ディレクトリ（BaseAnalyzerから継承）
        self.report_dir = self.output_dir
        
        # 分析結果格納
        self.analysis_results = {
            "timestamp": datetime.now().isoformat(),
            "period": "unknown",
            "system_health": {},
            "trading_performance": {},
            "resource_utilization": {},
            "error_analysis": {},
            "recommendations": [],
            "overall_score": 0.0
        }

    def analyze_system_health(self, hours: int = 24) -> Dict:
        """システムヘルス分析（BaseAnalyzer活用版）"""
        logger.info(f"システムヘルス分析開始（過去{hours}時間）")
        
        try:
            # BaseAnalyzerのcheck_service_health()活用
            health_data = self.check_service_health()
            
            if health_data.get("service_status") == "UP":
                logger.info(f"✅ サービス状態: {health_data['service_status']}")
                logger.info(f"📍 URL: {health_data.get('url', '')}")  
            else:
                logger.error(f"❌ サービス状態取得失敗: {health_data.get('error', '')}")                
        except Exception as e:
            health_data = {
                "service_status": "ERROR", 
                "error": str(e)
            }
            logger.error(f"❌ システムヘルス分析エラー: {e}")
        
        self.analysis_results["system_health"] = health_data
        return health_data

    def analyze_error_logs(self, hours: int = 24) -> Dict:
        """エラーログ分析（BaseAnalyzer活用版）"""
        logger.info(f"エラーログ分析開始（過去{hours}時間）")
        
        try:
            # BaseAnalyzerのfetch_error_logs()活用
            success, logs = self.fetch_error_logs(hours)
            
            if success:
                
                # エラーカテゴリ分析（レガシー改良）
                error_categories = {}
                critical_errors = []
                
                for log_entry in logs:
                    severity = log_entry.get("severity", "UNKNOWN")
                    message = log_entry.get("textPayload") or log_entry.get("jsonPayload", {}).get("message", "")
                    timestamp = log_entry.get("timestamp", "")
                    
                    # エラーカテゴリ分類
                    if "API" in message or "auth" in message.lower():
                        category = "API_AUTH_ERROR"
                    elif "timeout" in message.lower() or "connection" in message.lower():
                        category = "NETWORK_ERROR"
                    elif "memory" in message.lower() or "oom" in message.lower():
                        category = "RESOURCE_ERROR"
                    elif "trading" in message.lower() or "order" in message.lower():
                        category = "TRADING_ERROR"
                    else:
                        category = "GENERAL_ERROR"
                    
                    error_categories[category] = error_categories.get(category, 0) + 1
                    
                    # クリティカルエラー特定
                    if severity == "CRITICAL" or "critical" in message.lower():
                        critical_errors.append({
                            "timestamp": timestamp,
                            "message": message[:200],  # 最初の200文字
                            "severity": severity
                        })
                
                error_data = {
                    "total_errors": len(logs),
                    "error_categories": error_categories,
                    "critical_errors": critical_errors[:5],  # 最新5件
                    "error_rate_per_hour": len(logs) / hours,
                    "analysis_period_hours": hours
                }
                
                logger.info(f"📊 エラー総数: {error_data['total_errors']}")
                logger.info(f"📈 エラー率: {error_data['error_rate_per_hour']:.2f}/時間")
                
                if error_categories:
                    logger.info("📋 エラーカテゴリ別:")
                    for category, count in error_categories.items():
                        logger.info(f"  {category}: {count}")
                        
            else:
                error_data = {
                    "total_errors": 0,
                    "error": "ログ取得失敗",
                    "analysis_failed": True
                }
                logger.error("❌ エラーログ取得失敗")
                
        except Exception as e:
            error_data = {
                "total_errors": 0,
                "error": str(e),
                "analysis_failed": True
            }
            logger.error(f"❌ エラーログ分析失敗: {e}")
            
        self.analysis_results["error_analysis"] = error_data
        return error_data

    def analyze_trading_performance(self, hours: int = 24) -> Dict:
        """取引パフォーマンス分析（BaseAnalyzer活用版）"""
        logger.info(f"取引パフォーマンス分析開始（過去{hours}時間）")
        
        try:
            # BaseAnalyzerのfetch_trading_logs()活用
            success, logs = self.fetch_trading_logs(hours)
            
            if success:
                
                # 取引分析（レガシー改良）
                signal_counts = {"BUY": 0, "SELL": 0, "HOLD": 0}
                order_counts = {"SUCCESS": 0, "FAILED": 0}
                signal_timestamps = []
                
                for log_entry in logs:
                    message = log_entry.get("textPayload") or log_entry.get("jsonPayload", {}).get("message", "")
                    timestamp = log_entry.get("timestamp", "")
                    
                    # シグナル分類
                    if "BUY" in message:
                        signal_counts["BUY"] += 1
                    elif "SELL" in message:
                        signal_counts["SELL"] += 1
                    elif "HOLD" in message:
                        signal_counts["HOLD"] += 1
                    
                    # 注文結果分類
                    if "注文実行成功" in message or "order successful" in message.lower():
                        order_counts["SUCCESS"] += 1
                    elif "注文失敗" in message or "order failed" in message.lower():
                        order_counts["FAILED"] += 1
                    
                    if timestamp:
                        signal_timestamps.append(timestamp)
                
                # シグナル頻度分析
                total_signals = sum(signal_counts.values())
                signal_frequency = total_signals / hours if hours > 0 else 0
                
                # 注文成功率
                total_orders = sum(order_counts.values())
                success_rate = (order_counts["SUCCESS"] / total_orders * 100) if total_orders > 0 else 0
                
                trading_data = {
                    "total_signals": total_signals,
                    "signal_breakdown": signal_counts,
                    "signal_frequency_per_hour": round(signal_frequency, 2),
                    "total_orders": total_orders,
                    "order_success_rate": round(success_rate, 2),
                    "order_breakdown": order_counts,
                    "analysis_period_hours": hours,
                    "latest_activity": signal_timestamps[-1] if signal_timestamps else None
                }
                
                logger.info(f"📊 総シグナル数: {trading_data['total_signals']}")
                logger.info(f"📈 シグナル頻度: {trading_data['signal_frequency_per_hour']}/時間")
                logger.info(f"✅ 注文成功率: {trading_data['order_success_rate']}%")
                
            else:
                trading_data = {
                    "total_signals": 0,
                    "error": "取引ログ取得失敗",
                    "analysis_failed": True
                }
                logger.error("❌ 取引ログ取得失敗")
                
        except Exception as e:
            trading_data = {
                "total_signals": 0,
                "error": str(e),
                "analysis_failed": True
            }
            logger.error(f"❌ 取引パフォーマンス分析失敗: {e}")
            
        self.analysis_results["trading_performance"] = trading_data
        return trading_data

    def generate_recommendations(self) -> List[str]:
        """改善推奨事項生成（レガシー改良版）"""
        logger.info("改善推奨事項生成開始")
        
        recommendations = []
        
        # システムヘルス基準
        system_health = self.analysis_results.get("system_health", {})
        if system_health.get("service_status") != "UP":
            recommendations.append("🚨 クリティカル: サービス復旧が必要")
            
        # エラー分析基準
        error_analysis = self.analysis_results.get("error_analysis", {})
        error_rate = error_analysis.get("error_rate_per_hour", 0)
        if error_rate > 5:
            recommendations.append(f"⚠️ エラー率高騰: {error_rate:.1f}/時間 - ログ詳細確認が必要")
        elif error_rate > 1:
            recommendations.append(f"⚠️ エラー率注意: {error_rate:.1f}/時間 - 監視継続推奨")
            
        # 取引パフォーマンス基準
        trading_perf = self.analysis_results.get("trading_performance", {})
        signal_freq = trading_perf.get("signal_frequency_per_hour", 0)
        success_rate = trading_perf.get("order_success_rate", 0)
        
        if signal_freq < 0.5:
            recommendations.append("📡 シグナル頻度低下: 戦略ロジック確認推奨")
        elif signal_freq > 10:
            recommendations.append("📡 シグナル過多: 閾値調整検討")
            
        if success_rate < 90 and trading_perf.get("total_orders", 0) > 0:
            recommendations.append(f"💼 注文成功率低下: {success_rate}% - API設定確認")
            
        # パフォーマンス向上提案
        if not recommendations:
            recommendations.extend([
                "✅ システム正常稼働中",
                "📊 継続的監視推奨",
                "🔧 Phase 13でのML性能向上準備",
                "📈 A/Bテスト実施検討"
            ])
            
        self.analysis_results["recommendations"] = recommendations
        return recommendations

    def calculate_overall_score(self) -> float:
        """総合スコア計算（0-100）"""
        score = 100.0
        
        # システムヘルス (-40点)
        system_health = self.analysis_results.get("system_health", {})
        if system_health.get("service_status") != "UP":
            score -= 40
            
        # エラー率 (-30点)
        error_analysis = self.analysis_results.get("error_analysis", {})
        error_rate = error_analysis.get("error_rate_per_hour", 0)
        if error_rate > 5:
            score -= 30
        elif error_rate > 1:
            score -= 15
            
        # 取引パフォーマンス (-30点)
        trading_perf = self.analysis_results.get("trading_performance", {})
        success_rate = trading_perf.get("order_success_rate", 100)
        if success_rate < 80:
            score -= 30
        elif success_rate < 95:
            score -= 15
            
        score = max(0, score)  # 0以下にはしない
        self.analysis_results["overall_score"] = score
        return score

    def generate_report(self, output_format: str = "json") -> str:
        """分析レポート生成"""
        logger.info(f"分析レポート生成開始（形式: {output_format}）")
        
        # 総合スコア計算
        overall_score = self.calculate_overall_score()
        
        # ファイル名生成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if output_format == "json":
            report_file = self.report_dir / f"performance_analysis_{timestamp}.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(self.analysis_results, f, indent=2, ensure_ascii=False)
                
        elif output_format == "markdown":
            report_file = self.report_dir / f"performance_analysis_{timestamp}.md"
            
            # Markdownレポート生成
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(f"# Phase 12 パフォーマンス分析レポート\n\n")
                f.write(f"**生成日時**: {self.analysis_results['timestamp']}\n")
                f.write(f"**分析期間**: {self.analysis_results['period']}\n")
                f.write(f"**総合スコア**: {overall_score:.1f}/100\n\n")
                
                # システムヘルス
                f.write("## 🏥 システムヘルス\n\n")
                system_health = self.analysis_results.get("system_health", {})
                f.write(f"- **状態**: {system_health.get('service_status', 'UNKNOWN')}\n")
                if "url" in system_health:
                    f.write(f"- **URL**: {system_health['url']}\n")
                f.write("\n")
                
                # エラー分析
                f.write("## 🔍 エラー分析\n\n")
                error_analysis = self.analysis_results.get("error_analysis", {})
                f.write(f"- **総エラー数**: {error_analysis.get('total_errors', 0)}\n")
                f.write(f"- **エラー率**: {error_analysis.get('error_rate_per_hour', 0):.2f}/時間\n")
                
                error_categories = error_analysis.get("error_categories", {})
                if error_categories:
                    f.write("- **カテゴリ別**:\n")
                    for category, count in error_categories.items():
                        f.write(f"  - {category}: {count}\n")
                f.write("\n")
                
                # 取引パフォーマンス
                f.write("## 💼 取引パフォーマンス\n\n")
                trading_perf = self.analysis_results.get("trading_performance", {})
                f.write(f"- **総シグナル数**: {trading_perf.get('total_signals', 0)}\n")
                f.write(f"- **シグナル頻度**: {trading_perf.get('signal_frequency_per_hour', 0)}/時間\n")
                f.write(f"- **注文成功率**: {trading_perf.get('order_success_rate', 0)}%\n")
                f.write("\n")
                
                # 推奨事項
                f.write("## 🔧 改善推奨事項\n\n")
                recommendations = self.analysis_results.get("recommendations", [])
                for rec in recommendations:
                    f.write(f"- {rec}\n")
                f.write("\n")
                
        logger.info(f"✅ レポート生成完了: {report_file}")
        return str(report_file)

    def run_analysis(self, period: str = "24h", output_format: str = "json") -> str:
        """完全分析実行"""
        logger.info(f"Phase 12パフォーマンス分析開始（期間: {period}）")
        
        # 期間解析
        if period.endswith('h'):
            hours = int(period[:-1])
        elif period.endswith('d'):
            hours = int(period[:-1]) * 24
        else:
            hours = 24  # デフォルト
            
        self.analysis_results["period"] = period
        
        # 各分析実行
        self.analyze_system_health(hours)
        self.analyze_error_logs(hours)
        self.analyze_trading_performance(hours)
        self.generate_recommendations()
        
        # レポート生成
        report_file = self.generate_report(output_format)
        
        # サマリー出力
        overall_score = self.analysis_results["overall_score"]
        logger.info(f"🎯 分析完了 - 総合スコア: {overall_score:.1f}/100")
        
        if overall_score >= 90:
            logger.info("✅ システム状態: 優秀")
        elif overall_score >= 70:
            logger.info("🟡 システム状態: 良好")
        elif overall_score >= 50:
            logger.info("🟠 システム状態: 注意")
        else:
            logger.info("🔴 システム状態: 問題あり")
            
        return report_file

    # ===== BaseAnalyzer抽象メソッド実装 =====
    
    def run_analysis(self, **kwargs) -> Dict:
        """パフォーマンス分析実行（BaseAnalyzer要求）"""
        try:
            period = kwargs.get("period", "24h")
            output_format = kwargs.get("output_format", "json")
            
            # 既存のrun_analysisメソッド呼び出し
            report_file = self.run_analysis_detailed(period, output_format)
            
            return {
                "timestamp": datetime.now().isoformat(),
                "analysis_type": "performance_analysis", 
                "period": period,
                "output_format": output_format,
                "report_file": report_file,
                "overall_score": self.analysis_results.get("overall_score", 0),
                "system_health": self.analysis_results.get("system_health", {}),
                "error_analysis": self.analysis_results.get("error_analysis", {}),
                "trading_performance": self.analysis_results.get("trading_performance", {}),
                "recommendations": self.analysis_results.get("recommendations", []),
                "success": True
            }
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "analysis_type": "performance_analysis",
                "error": str(e),
                "success": False
            }
    
    def generate_report(self, analysis_result: Dict) -> str:
        """パフォーマンス分析レポート生成（BaseAnalyzer要求）"""
        if analysis_result.get("success"):
            return f"""
=== Phase 12 パフォーマンス分析レポート ===
生成日時: {analysis_result.get('timestamp', '')}
分析期間: {analysis_result.get('period', '')}
出力形式: {analysis_result.get('output_format', '')}
レポートファイル: {analysis_result.get('report_file', '')}
総合スコア: {analysis_result.get('overall_score', 0):.1f}/100
システム状態: {analysis_result.get('system_health', {}).get('service_status', 'Unknown')}
エラー率: {analysis_result.get('error_analysis', {}).get('error_rate_per_hour', 0):.2f}/時間
推奨事項: {len(analysis_result.get('recommendations', []))}件
======================================"""
        else:
            return f"パフォーマンス分析失敗: {analysis_result.get('error', 'Unknown error')}"
    
    def run_analysis_detailed(self, period: str = "24h", output_format: str = "json") -> str:
        """完全分析実行（既存メソッド名前変更）"""
        logger.info(f"Phase 12パフォーマンス分析開始（期間: {period}）")
        
        # 期間解析
        if period.endswith('h'):
            hours = int(period[:-1])
        elif period.endswith('d'):
            hours = int(period[:-1]) * 24
        else:
            hours = 24  # デフォルト
            
        self.analysis_results["period"] = period
        
        # 各分析実行
        self.analyze_system_health(hours)
        self.analyze_error_logs(hours)
        self.analyze_trading_performance(hours)
        self.generate_recommendations()
        
        # レポート生成
        report_file = self.generate_report(output_format)
        
        # サマリー出力
        overall_score = self.analysis_results["overall_score"]
        logger.info(f"🎯 分析完了 - 総合スコア: {overall_score:.1f}/100")
        
        if overall_score >= 90:
            logger.info("✅ システム状態: 優秀")
        elif overall_score >= 70:
            logger.info("🟡 システム状態: 良好")
        elif overall_score >= 50:
            logger.info("🟠 システム状態: 注意")
        else:
            logger.info("🔴 システム状態: 問題あり")
            
        return report_file


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="Phase 12 パフォーマンス分析ツール")
    parser.add_argument("--period", default="24h", 
                       help="分析期間 (例: 1h, 6h, 24h, 7d)")
    parser.add_argument("--format", choices=["json", "markdown"], default="json",
                       help="出力形式")
    parser.add_argument("--service", default="crypto-bot-service",
                       help="Cloud Runサービス名")
    parser.add_argument("--project", default="my-crypto-bot-project",
                       help="GCPプロジェクトID")
    parser.add_argument("--region", default="asia-northeast1",
                       help="GCPリージョン")
                       
    args = parser.parse_args()
    
    try:
        analyzer = PerformanceAnalyzer(
            project_id=args.project,
            service_name=args.service,
            region=args.region
        )
        
        report_file = analyzer.run_analysis_detailed(
            period=args.period,
            output_format=args.format
        )
        
        print(f"\n📋 分析レポート: {report_file}")
        print("🚀 Phase 12 パフォーマンス分析完了")
        
    except KeyboardInterrupt:
        logger.info("分析中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"分析エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()