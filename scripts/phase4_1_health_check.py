#!/usr/bin/env python3
"""
Phase 4.1a: 本番環境最終確認
本番環境の状態を包括的にチェックします
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Optional

import requests


class ProductionHealthChecker:
    """本番環境ヘルスチェッククラス"""

    def __init__(self):
        self.base_url = (
            "https://crypto-bot-service-prod-11445303925.asia-northeast1.run.app"
        )
        self.check_results = []
        self.start_time = datetime.now()

    def log_check(
        self,
        check_name: str,
        status: str,
        message: str = "",
        data: Optional[Dict] = None,
    ):
        """チェック結果をログに記録"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "check_name": check_name,
            "status": status,
            "message": message,
            "data": data or {},
        }
        self.check_results.append(result)

        status_emoji = (
            "✅" if status == "success" else "❌" if status == "failed" else "⚠️"
        )
        print(f"{status_emoji} {check_name}: {status}")
        if message:
            print(f"   {message}")
        if data:
            print(f"   Data: {json.dumps(data, indent=2)}")
        print()

    def check_basic_health(self) -> bool:
        """基本ヘルスチェック"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log_check(
                    "基本ヘルスチェック",
                    "success",
                    f"Status: {response.status_code}",
                    data,
                )
                return True
            else:
                self.log_check(
                    "基本ヘルスチェック",
                    "failed",
                    f"HTTP {response.status_code}: {response.text}",
                )
                return False
        except Exception as e:
            self.log_check("基本ヘルスチェック", "failed", f"Exception: {str(e)}")
            return False

    def check_detailed_health(self) -> bool:
        """詳細ヘルスチェック"""
        try:
            response = requests.get(f"{self.base_url}/health/detailed", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log_check(
                    "詳細ヘルスチェック",
                    "success",
                    f"Status: {response.status_code}",
                    data,
                )

                # 重要な項目をチェック
                if data.get("margin_mode") == True:
                    self.log_check(
                        "信用取引モード", "success", "信用取引モードが有効です"
                    )
                else:
                    self.log_check(
                        "信用取引モード", "warning", "信用取引モードが無効です"
                    )

                if data.get("exchange") == "bitbank":
                    self.log_check(
                        "取引所設定", "success", "Bitbank取引所が設定されています"
                    )
                else:
                    self.log_check(
                        "取引所設定", "warning", f"取引所: {data.get('exchange')}"
                    )

                if data.get("api_credentials") == "healthy":
                    self.log_check("API認証", "success", "API認証が正常です")
                else:
                    self.log_check(
                        "API認証", "warning", f"API認証: {data.get('api_credentials')}"
                    )

                return True
            else:
                self.log_check(
                    "詳細ヘルスチェック",
                    "failed",
                    f"HTTP {response.status_code}: {response.text}",
                )
                return False
        except Exception as e:
            self.log_check("詳細ヘルスチェック", "failed", f"Exception: {str(e)}")
            return False

    def check_performance_metrics(self) -> bool:
        """パフォーマンスメトリクスチェック"""
        try:
            response = requests.get(f"{self.base_url}/health/performance", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log_check(
                    "パフォーマンスメトリクス",
                    "success",
                    f"Status: {response.status_code}",
                    data,
                )

                # 重要なメトリクスをチェック
                kelly_ratio = data.get("kelly_ratio", 0)
                if kelly_ratio > 0.1:
                    self.log_check("Kelly比率", "success", f"Kelly比率: {kelly_ratio}")
                else:
                    self.log_check(
                        "Kelly比率", "warning", f"Kelly比率が低い: {kelly_ratio}"
                    )

                win_rate = data.get("win_rate", 0)
                if win_rate > 0.5:
                    self.log_check("勝率", "success", f"勝率: {win_rate}")
                else:
                    self.log_check("勝率", "warning", f"勝率が低い: {win_rate}")

                max_drawdown = data.get("max_drawdown", 0)
                if max_drawdown < 0.1:
                    self.log_check(
                        "最大ドローダウン",
                        "success",
                        f"最大ドローダウン: {max_drawdown}",
                    )
                else:
                    self.log_check(
                        "最大ドローダウン",
                        "warning",
                        f"最大ドローダウンが高い: {max_drawdown}",
                    )

                return True
            else:
                self.log_check(
                    "パフォーマンスメトリクス",
                    "failed",
                    f"HTTP {response.status_code}: {response.text}",
                )
                return False
        except Exception as e:
            self.log_check("パフォーマンスメトリクス", "failed", f"Exception: {str(e)}")
            return False

    def check_prometheus_metrics(self) -> bool:
        """Prometheusメトリクスチェック"""
        try:
            response = requests.get(f"{self.base_url}/metrics", timeout=10)
            if response.status_code == 200:
                metrics_text = response.text
                self.log_check(
                    "Prometheusメトリクス",
                    "success",
                    f"Status: {response.status_code}, Metrics lines: {len(metrics_text.split('\\n'))}",
                )

                # 重要なメトリクスの存在確認
                important_metrics = [
                    "crypto_bot_kelly_ratio",
                    "crypto_bot_win_rate",
                    "crypto_bot_max_drawdown",
                    "crypto_bot_sharpe_ratio",
                    "crypto_bot_total_trades",
                ]

                for metric in important_metrics:
                    if metric in metrics_text:
                        self.log_check(
                            f"メトリクス: {metric}",
                            "success",
                            "メトリクスが利用可能です",
                        )
                    else:
                        self.log_check(
                            f"メトリクス: {metric}",
                            "warning",
                            "メトリクスが見つかりません",
                        )

                return True
            else:
                self.log_check(
                    "Prometheusメトリクス",
                    "failed",
                    f"HTTP {response.status_code}: {response.text}",
                )
                return False
        except Exception as e:
            self.log_check("Prometheusメトリクス", "failed", f"Exception: {str(e)}")
            return False

    def check_api_endpoints(self) -> bool:
        """API エンドポイントチェック"""
        endpoints = ["/health", "/health/detailed", "/health/performance", "/metrics"]

        all_success = True
        for endpoint in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                if response.status_code == 200:
                    self.log_check(
                        f"エンドポイント: {endpoint}",
                        "success",
                        f"Status: {response.status_code}",
                    )
                else:
                    self.log_check(
                        f"エンドポイント: {endpoint}",
                        "failed",
                        f"HTTP {response.status_code}",
                    )
                    all_success = False
            except Exception as e:
                self.log_check(
                    f"エンドポイント: {endpoint}", "failed", f"Exception: {str(e)}"
                )
                all_success = False

        return all_success

    def check_response_time(self) -> bool:
        """レスポンス時間チェック"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/health", timeout=10)
            end_time = time.time()

            response_time = end_time - start_time

            if response.status_code == 200 and response_time < 5.0:
                self.log_check(
                    "レスポンス時間",
                    "success",
                    f"レスポンス時間: {response_time:.2f}秒",
                )
                return True
            else:
                self.log_check(
                    "レスポンス時間",
                    "warning",
                    f"レスポンス時間が長い: {response_time:.2f}秒",
                )
                return False
        except Exception as e:
            self.log_check("レスポンス時間", "failed", f"Exception: {str(e)}")
            return False

    def generate_report(self) -> Dict:
        """ヘルスチェックレポートを生成"""
        total_checks = len(self.check_results)
        successful_checks = len(
            [r for r in self.check_results if r["status"] == "success"]
        )
        failed_checks = len([r for r in self.check_results if r["status"] == "failed"])
        warning_checks = len(
            [r for r in self.check_results if r["status"] == "warning"]
        )

        report = {
            "report_timestamp": datetime.now().isoformat(),
            "check_duration": str(datetime.now() - self.start_time),
            "summary": {
                "total_checks": total_checks,
                "successful_checks": successful_checks,
                "failed_checks": failed_checks,
                "warning_checks": warning_checks,
                "success_rate": (
                    f"{(successful_checks / total_checks * 100):.1f}%"
                    if total_checks > 0
                    else "0%"
                ),
            },
            "detailed_results": self.check_results,
        }

        return report

    def run_all_checks(self) -> bool:
        """全てのヘルスチェックを実行"""
        print("🏥 Phase 4.1a: 本番環境最終確認開始")
        print("=" * 50)

        checks = [
            ("基本ヘルスチェック", self.check_basic_health),
            ("詳細ヘルスチェック", self.check_detailed_health),
            ("パフォーマンスメトリクス", self.check_performance_metrics),
            ("Prometheusメトリクス", self.check_prometheus_metrics),
            ("APIエンドポイント", self.check_api_endpoints),
            ("レスポンス時間", self.check_response_time),
        ]

        overall_success = True
        for check_name, check_func in checks:
            print(f"🔍 {check_name} 実行中...")
            success = check_func()
            if not success:
                overall_success = False
            time.sleep(1)  # レート制限対策

        # レポート生成
        report = self.generate_report()

        print("📊 ヘルスチェック完了サマリー")
        print("=" * 50)
        print(f"総チェック数: {report['summary']['total_checks']}")
        print(f"成功: {report['summary']['successful_checks']}")
        print(f"失敗: {report['summary']['failed_checks']}")
        print(f"警告: {report['summary']['warning_checks']}")
        print(f"成功率: {report['summary']['success_rate']}")
        print(f"実行時間: {report['check_duration']}")

        # レポートをファイルに保存
        try:
            with open("phase4_1_health_check_report.json", "w") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print("\\n📄 詳細レポートをphase4_1_health_check_report.jsonに保存しました")
        except Exception as e:
            print(f"\\n⚠️  レポート保存に失敗: {e}")

        if overall_success:
            print("\\n🎉 Phase 4.1a: 本番環境最終確認 - 全てのチェックが成功しました!")
        else:
            print("\\n⚠️  Phase 4.1a: 本番環境最終確認 - 一部のチェックが失敗しました")

        return overall_success


def main():
    """メイン実行関数"""
    checker = ProductionHealthChecker()
    success = checker.run_all_checks()

    if success:
        print("\\n✅ Phase 4.1a完了 - 次のフェーズ（Phase 4.1b）に進むことができます")
        return 0
    else:
        print("\\n❌ Phase 4.1a失敗 - 問題を解決してから次のフェーズに進んでください")
        return 1


if __name__ == "__main__":
    exit(main())
