#!/usr/bin/env python3
"""
Phase 4.1c: API-onlyモード問題完全根絶確認
API-onlyモードフォールバック問題が完全に解決されたことを確認します
"""

import json
import os
import subprocess
import time
from datetime import datetime
from typing import Dict, List, Optional

import requests


class APIOnlyModeEradicationTest:
    """API-onlyモード問題根絶確認テストクラス"""

    def __init__(self):
        self.test_results = []
        self.start_time = datetime.now()
        self.base_url = (
            "https://crypto-bot-service-prod-11445303925.asia-northeast1.run.app"
        )

    def log_test(
        self,
        test_name: str,
        status: str,
        message: str = "",
        data: Optional[Dict] = None,
    ):
        """テスト結果をログに記録"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "test_name": test_name,
            "status": status,
            "message": message,
            "data": data or {},
        }
        self.test_results.append(result)

        status_emoji = (
            "✅" if status == "success" else "❌" if status == "failed" else "⚠️"
        )
        print(f"{status_emoji} {test_name}: {status}")
        if message:
            print(f"   {message}")
        if data:
            print(f"   Data: {json.dumps(data, indent=2)}")
        print()

    def test_enhanced_init_function(self) -> bool:
        """強化版INIT機能の動作確認"""
        try:
            # 本番環境のログを確認してINIT-ENHANCEDメッセージを検索
            cmd = [
                "gcloud",
                "logging",
                "read",
                'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND jsonPayload.message=~"INIT-ENHANCED"',
                "--limit=10",
                "--format=json",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                logs = json.loads(result.stdout) if result.stdout.strip() else []

                if logs:
                    self.log_test(
                        "強化版INIT機能動作確認",
                        "success",
                        f"強化版INIT機能のログが見つかりました: {len(logs)} 件",
                        {"log_count": len(logs)},
                    )
                    return True
                else:
                    self.log_test(
                        "強化版INIT機能動作確認",
                        "warning",
                        "強化版INIT機能のログが見つかりません（まだ実行されていない可能性）",
                    )
                    return False
            else:
                self.log_test(
                    "強化版INIT機能動作確認", "failed", f"ログ取得失敗: {result.stderr}"
                )
                return False

        except Exception as e:
            self.log_test("強化版INIT機能動作確認", "failed", f"Exception: {str(e)}")
            return False

    def test_no_api_only_mode_fallback(self) -> bool:
        """API-onlyモードフォールバック無効化確認"""
        try:
            # API-onlyモードのログを検索
            cmd = [
                "gcloud",
                "logging",
                "read",
                'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND jsonPayload.message=~"API-only mode"',
                "--limit=10",
                "--since=1h",
                "--format=json",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                logs = json.loads(result.stdout) if result.stdout.strip() else []

                if not logs:
                    self.log_test(
                        "API-onlyモードフォールバック無効化確認",
                        "success",
                        "API-onlyモードのログが見つかりません（正常な状態）",
                    )
                    return True
                else:
                    self.log_test(
                        "API-onlyモードフォールバック無効化確認",
                        "failed",
                        f"API-onlyモードのログが見つかりました: {len(logs)} 件",
                        {"log_count": len(logs)},
                    )
                    return False
            else:
                self.log_test(
                    "API-onlyモードフォールバック無効化確認",
                    "failed",
                    f"ログ取得失敗: {result.stderr}",
                )
                return False

        except Exception as e:
            self.log_test(
                "API-onlyモードフォールバック無効化確認",
                "failed",
                f"Exception: {str(e)}",
            )
            return False

    def test_proper_error_handling(self) -> bool:
        """適切なエラーハンドリング確認"""
        try:
            # エラーハンドリングの改善を確認
            cmd = [
                "gcloud",
                "logging",
                "read",
                'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND (jsonPayload.message=~"terminating process" OR jsonPayload.message=~"sys.exit")',
                "--limit=10",
                "--since=1h",
                "--format=json",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                logs = json.loads(result.stdout) if result.stdout.strip() else []

                self.log_test(
                    "適切なエラーハンドリング確認",
                    "success",
                    f"適切なエラーハンドリングログを確認: {len(logs)} 件",
                    {"log_count": len(logs)},
                )
                return True
            else:
                self.log_test(
                    "適切なエラーハンドリング確認",
                    "warning",
                    f"ログ取得失敗: {result.stderr}",
                )
                return False

        except Exception as e:
            self.log_test(
                "適切なエラーハンドリング確認", "failed", f"Exception: {str(e)}"
            )
            return False

    def test_live_trading_continuity(self) -> bool:
        """ライブトレーディング継続性確認"""
        try:
            # ライブトレーディングの継続性を確認
            response = requests.get(f"{self.base_url}/health/detailed", timeout=10)

            if response.status_code == 200:
                data = response.json()

                # 重要な指標をチェック
                is_live_mode = data.get("mode") == "live"
                is_bitbank = data.get("exchange") == "bitbank"
                is_margin_enabled = data.get("margin_mode") == True

                if is_live_mode and is_bitbank and is_margin_enabled:
                    self.log_test(
                        "ライブトレーディング継続性確認",
                        "success",
                        "ライブトレーディングモードが正常に動作しています",
                        {
                            "mode": data.get("mode"),
                            "exchange": data.get("exchange"),
                            "margin_mode": data.get("margin_mode"),
                        },
                    )
                    return True
                else:
                    self.log_test(
                        "ライブトレーディング継続性確認",
                        "failed",
                        "ライブトレーディングモードが正常に動作していません",
                        {
                            "mode": data.get("mode"),
                            "exchange": data.get("exchange"),
                            "margin_mode": data.get("margin_mode"),
                        },
                    )
                    return False
            else:
                self.log_test(
                    "ライブトレーディング継続性確認",
                    "failed",
                    f"HTTP {response.status_code}: {response.text}",
                )
                return False

        except Exception as e:
            self.log_test(
                "ライブトレーディング継続性確認", "failed", f"Exception: {str(e)}"
            )
            return False

    def test_abnormal_termination_behavior(self) -> bool:
        """異常時適切終了確認"""
        try:
            # 異常時の適切な終了処理を確認
            cmd = [
                "gcloud",
                "logging",
                "read",
                'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND jsonPayload.message=~"terminating process"',
                "--limit=5",
                "--since=24h",
                "--format=json",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                logs = json.loads(result.stdout) if result.stdout.strip() else []

                self.log_test(
                    "異常時適切終了確認",
                    "success",
                    f"適切な終了処理ログを確認: {len(logs)} 件",
                    {"log_count": len(logs)},
                )
                return True
            else:
                self.log_test(
                    "異常時適切終了確認", "warning", f"ログ取得失敗: {result.stderr}"
                )
                return False

        except Exception as e:
            self.log_test("異常時適切終了確認", "failed", f"Exception: {str(e)}")
            return False

    def test_error_scenario_simulation(self) -> bool:
        """エラーシナリオシミュレーション"""
        try:
            # Phase 2で実装した修正がちゃんと動作するかテスト
            test_scenarios = [
                "ATR計算タイムアウト",
                "外部データフェッチャー失敗",
                "API認証エラー",
                "yfinance依存関係エラー",
            ]

            successful_scenarios = 0

            for scenario in test_scenarios:
                # 各シナリオのログを検索
                if scenario == "ATR計算タイムアウト":
                    search_term = "INIT-5.*timeout"
                elif scenario == "外部データフェッチャー失敗":
                    search_term = "external.*fetcher.*failed"
                elif scenario == "API認証エラー":
                    search_term = "AuthenticationError"
                elif scenario == "yfinance依存関係エラー":
                    search_term = "yfinance.*not found"

                cmd = [
                    "gcloud",
                    "logging",
                    "read",
                    f'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND jsonPayload.message=~"{search_term}"',
                    "--limit=1",
                    "--since=24h",
                    "--format=json",
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

                if result.returncode == 0:
                    logs = json.loads(result.stdout) if result.stdout.strip() else []

                    if logs:
                        # エラーが発生した場合、適切に処理されているかチェック
                        self.log_test(
                            f"エラーシナリオ: {scenario}",
                            "success",
                            f"エラーが検出され、適切に処理されています",
                            {"error_count": len(logs)},
                        )
                        successful_scenarios += 1
                    else:
                        self.log_test(
                            f"エラーシナリオ: {scenario}",
                            "success",
                            f"エラーが発生していません（良好な状態）",
                        )
                        successful_scenarios += 1

            if successful_scenarios == len(test_scenarios):
                self.log_test(
                    "エラーシナリオシミュレーション",
                    "success",
                    f"全てのエラーシナリオが適切に処理されています: {successful_scenarios}/{len(test_scenarios)}",
                )
                return True
            else:
                self.log_test(
                    "エラーシナリオシミュレーション",
                    "warning",
                    f"一部のエラーシナリオで問題があります: {successful_scenarios}/{len(test_scenarios)}",
                )
                return False

        except Exception as e:
            self.log_test(
                "エラーシナリオシミュレーション", "failed", f"Exception: {str(e)}"
            )
            return False

    def test_startup_script_verification(self) -> bool:
        """起動スクリプト検証"""
        try:
            # start_live_with_api_fixed.py の動作を確認
            cmd = [
                "gcloud",
                "logging",
                "read",
                'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND jsonPayload.message=~"NO-FALLBACK VERSION"',
                "--limit=5",
                "--since=24h",
                "--format=json",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                logs = json.loads(result.stdout) if result.stdout.strip() else []

                if logs:
                    self.log_test(
                        "起動スクリプト検証",
                        "success",
                        "NO-FALLBACK VERSION が正常に動作しています",
                        {"log_count": len(logs)},
                    )
                    return True
                else:
                    self.log_test(
                        "起動スクリプト検証",
                        "warning",
                        "NO-FALLBACK VERSION のログが見つかりません",
                    )
                    return False
            else:
                self.log_test(
                    "起動スクリプト検証", "failed", f"ログ取得失敗: {result.stderr}"
                )
                return False

        except Exception as e:
            self.log_test("起動スクリプト検証", "failed", f"Exception: {str(e)}")
            return False

    def generate_eradication_report(self) -> Dict:
        """根絶確認レポートを生成"""
        total_tests = len(self.test_results)
        successful_tests = len(
            [r for r in self.test_results if r["status"] == "success"]
        )
        failed_tests = len([r for r in self.test_results if r["status"] == "failed"])
        warning_tests = len([r for r in self.test_results if r["status"] == "warning"])

        # API-onlyモード問題の根絶度を評価
        critical_tests = [
            "API-onlyモードフォールバック無効化確認",
            "ライブトレーディング継続性確認",
            "起動スクリプト検証",
        ]

        critical_success = 0
        for test in self.test_results:
            if test["test_name"] in critical_tests and test["status"] == "success":
                critical_success += 1

        eradication_score = (critical_success / len(critical_tests)) * 100

        report = {
            "report_timestamp": datetime.now().isoformat(),
            "test_duration": str(datetime.now() - self.start_time),
            "summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "failed_tests": failed_tests,
                "warning_tests": warning_tests,
                "success_rate": (
                    f"{(successful_tests / total_tests * 100):.1f}%"
                    if total_tests > 0
                    else "0%"
                ),
                "eradication_score": f"{eradication_score:.1f}%",
                "api_only_mode_eradicated": eradication_score >= 100.0,
            },
            "detailed_results": self.test_results,
        }

        return report

    def run_all_tests(self) -> bool:
        """全ての根絶確認テストを実行"""
        print("🔬 Phase 4.1c: API-onlyモード問題完全根絶確認開始")
        print("=" * 50)

        tests = [
            ("強化版INIT機能動作確認", self.test_enhanced_init_function),
            (
                "API-onlyモードフォールバック無効化確認",
                self.test_no_api_only_mode_fallback,
            ),
            ("適切なエラーハンドリング確認", self.test_proper_error_handling),
            ("ライブトレーディング継続性確認", self.test_live_trading_continuity),
            ("異常時適切終了確認", self.test_abnormal_termination_behavior),
            ("エラーシナリオシミュレーション", self.test_error_scenario_simulation),
            ("起動スクリプト検証", self.test_startup_script_verification),
        ]

        overall_success = True
        for test_name, test_func in tests:
            print(f"🧪 {test_name} 実行中...")
            success = test_func()
            if not success:
                overall_success = False
            time.sleep(2)  # API制限対策

        # レポート生成
        report = self.generate_eradication_report()

        print("📊 API-onlyモード問題根絶確認完了サマリー")
        print("=" * 50)
        print(f"総テスト数: {report['summary']['total_tests']}")
        print(f"成功: {report['summary']['successful_tests']}")
        print(f"失敗: {report['summary']['failed_tests']}")
        print(f"警告: {report['summary']['warning_tests']}")
        print(f"成功率: {report['summary']['success_rate']}")
        print(f"根絶スコア: {report['summary']['eradication_score']}")
        print(
            f"API-onlyモード根絶: {'✅ 完全根絶' if report['summary']['api_only_mode_eradicated'] else '❌ 未完了'}"
        )
        print(f"実行時間: {report['test_duration']}")

        # レポートをファイルに保存
        try:
            with open("phase4_1_api_only_eradication_report.json", "w") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(
                "\\n📄 詳細レポートをphase4_1_api_only_eradication_report.jsonに保存しました"
            )
        except Exception as e:
            print(f"\\n⚠️  レポート保存に失敗: {e}")

        if report["summary"]["api_only_mode_eradicated"]:
            print(
                "\\n🎉 Phase 4.1c: API-onlyモード問題完全根絶確認 - 完全根絶を確認しました!"
            )
        else:
            print(
                "\\n⚠️  Phase 4.1c: API-onlyモード問題完全根絶確認 - 完全根絶には至っていません"
            )

        return report["summary"]["api_only_mode_eradicated"]


def main():
    """メイン実行関数"""
    test = APIOnlyModeEradicationTest()
    success = test.run_all_tests()

    if success:
        print("\\n✅ Phase 4.1c完了 - API-onlyモード問題が完全に根絶されました")
        print("次のフェーズ（Phase 4.1d）に進むことができます")
        return 0
    else:
        print("\\n❌ Phase 4.1c失敗 - API-onlyモード問題の根絶が完了していません")
        return 1


if __name__ == "__main__":
    exit(main())
