#!/usr/bin/env python3
"""
包括的システムヘルスチェックスクリプト
土曜日早朝問題を含む全ての運用問題を自動検出

使用方法:
python scripts/system_health_check.py [--detailed] [--fix-suggestions]
"""

import json
import logging
import subprocess
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests


class BotHealthChecker:
    def __init__(self):
        self.base_url = (
            "https://crypto-bot-service-prod-11445303925.asia-northeast1.run.app"
        )
        self.issues = []
        self.checks_passed = 0
        self.checks_total = 0

        # 重要度設定
        self.CRITICAL = "🚨 CRITICAL"
        self.WARNING = "⚠️ WARNING"
        self.INFO = "ℹ️ INFO"
        self.SUCCESS = "✅ SUCCESS"

    def log_result(self, status: str, message: str, details: str = None):
        """チェック結果をログ"""
        self.checks_total += 1
        if status == self.SUCCESS:
            self.checks_passed += 1
        else:
            self.issues.append(
                {
                    "severity": status,
                    "message": message,
                    "details": details,
                    "timestamp": datetime.now().isoformat(),
                }
            )

        print(f"{status}: {message}")
        if details:
            print(f"    {details}")

    def check_basic_health(self) -> bool:
        """基本ヘルスチェック"""
        print("\n🔍 === 基本システム状態チェック ===")

        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log_result(
                    self.SUCCESS,
                    "システム基本稼働",
                    f"Mode: {data.get('mode', 'unknown')}",
                )
                return True
            else:
                self.log_result(
                    self.CRITICAL, "システム応答異常", f"Status: {response.status_code}"
                )
                return False
        except Exception as e:
            self.log_result(self.CRITICAL, "システム接続失敗", str(e))
            return False

    def check_detailed_health(self) -> Dict:
        """詳細ヘルスチェック"""
        print("\n🔍 === 詳細システム状態チェック ===")

        try:
            response = requests.get(f"{self.base_url}/health/detailed", timeout=15)
            if response.status_code == 200:
                data = response.json()

                # API認証チェック
                api_status = data.get("dependencies", {}).get("api_credentials", {})
                if api_status.get("status") == "healthy":
                    self.log_result(
                        self.SUCCESS, "API認証正常", api_status.get("details", "")
                    )
                else:
                    self.log_result(self.CRITICAL, "API認証異常", str(api_status))

                # マージンモードチェック
                margin_mode = api_status.get("margin_mode", False)
                if margin_mode:
                    self.log_result(
                        self.SUCCESS, "信用取引モード有効", "margin_mode=true"
                    )
                else:
                    self.log_result(self.WARNING, "信用取引モード無効", "現物取引のみ")

                # 取引状況チェック
                trading_status = data.get("trading", {})
                if trading_status.get("status") == "healthy":
                    self.log_result(
                        self.SUCCESS,
                        "取引システム正常",
                        f"利益: {trading_status.get('total_profit', 0)}",
                    )
                else:
                    self.log_result(
                        self.WARNING,
                        "取引システム状態不明",
                        trading_status.get("details", ""),
                    )

                return data
            else:
                self.log_result(
                    self.CRITICAL,
                    "詳細ヘルスチェック失敗",
                    f"Status: {response.status_code}",
                )
                return {}
        except Exception as e:
            self.log_result(self.CRITICAL, "詳細ヘルスチェック接続失敗", str(e))
            return {}

    def check_data_freshness(self) -> None:
        """データ新鮮度チェック（最重要）"""
        print("\n🔍 === データ新鮮度チェック ===")

        try:
            # Cloud Loggingからデータ取得ログを確認
            cmd = [
                "gcloud",
                "logging",
                "read",
                'resource.type=cloud_run_revision AND textPayload:"latest:"',
                "--limit=3",
                "--format=value(textPayload,timestamp)",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split("\n")
                for line in lines:
                    if "latest:" in line and "ago" in line:
                        # "latest: 2025-07-24 23:00:00+00:00 (20.8h ago)" のような形式を解析
                        if "20.8h ago" in line or "hours ago" in line:
                            hours_ago = self._extract_hours_ago(line)
                            if hours_ago and hours_ago > 2:
                                self.log_result(
                                    self.CRITICAL,
                                    f"データが古すぎます: {hours_ago:.1f}時間前",
                                    "リアルタイム取引に支障",
                                )
                            elif hours_ago and hours_ago > 1:
                                self.log_result(
                                    self.WARNING,
                                    f"データがやや古い: {hours_ago:.1f}時間前",
                                    "注意が必要",
                                )
                            else:
                                self.log_result(
                                    self.SUCCESS,
                                    "データ新鮮度良好",
                                    f"{hours_ago:.1f}時間前",
                                )
                            return

                self.log_result(self.INFO, "データ取得ログ確認", "最新性の詳細不明")
            else:
                self.log_result(
                    self.WARNING,
                    "データ取得ログ取得失敗",
                    "Cloud Loggingアクセス問題の可能性",
                )

        except subprocess.TimeoutExpired:
            self.log_result(
                self.WARNING, "Cloud Loggingタイムアウト", "ネットワーク問題の可能性"
            )
        except Exception as e:
            self.log_result(self.WARNING, "データ新鮮度チェック失敗", str(e))

    def _extract_hours_ago(self, log_line: str) -> Optional[float]:
        """ログから時間を抽出"""
        import re

        # "(20.8h ago)" のようなパターンを抽出
        pattern = r"\((\d+\.?\d*)h ago\)"
        match = re.search(pattern, log_line)
        if match:
            return float(match.group(1))
        return None

    def check_initialization_status(self) -> None:
        """初期化状態チェック"""
        print("\n🔍 === 初期化状態チェック ===")

        try:
            # INIT-5〜INIT-8の状況を確認
            init_stages = ["INIT-5", "INIT-6", "INIT-7", "INIT-8"]

            for stage in init_stages:
                cmd = [
                    "gcloud",
                    "logging",
                    "read",
                    f'resource.type=cloud_run_revision AND textPayload:"{stage}.*success"',
                    "--limit=1",
                    "--format=value(textPayload)",
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

                if result.returncode == 0 and result.stdout.strip():
                    self.log_result(self.SUCCESS, f"{stage}段階完了", "正常初期化")
                else:
                    self.log_result(
                        self.WARNING, f"{stage}段階状態不明", "ログ確認推奨"
                    )

        except Exception as e:
            self.log_result(self.WARNING, "初期化状態チェック失敗", str(e))

    def check_ml_model_status(self) -> None:
        """MLモデル状態チェック"""
        print("\n🔍 === MLモデル状態チェック ===")

        try:
            # model.pkl関連ログを確認
            cmd = [
                "gcloud",
                "logging",
                "read",
                'resource.type=cloud_run_revision AND textPayload:"model.pkl"',
                "--limit=3",
                "--format=value(textPayload)",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split("\n")

                # モデルダウンロード成功確認
                if any("successfully" in line for line in lines):
                    self.log_result(
                        self.SUCCESS,
                        "MLモデル正常ロード",
                        "/app/models/production/model.pkl",
                    )
                else:
                    self.log_result(
                        self.WARNING, "MLモデル状態不明", "ログ詳細確認推奨"
                    )
            else:
                self.log_result(self.WARNING, "MLモデルログ取得失敗", "モデル状態不明")

        except Exception as e:
            self.log_result(self.WARNING, "MLモデルチェック失敗", str(e))

    def check_external_data_sources(self) -> None:
        """外部データソース状態チェック"""
        print("\n🔍 === 外部データソース状態チェック ===")

        external_sources = [
            ("VIX", "VIX fetcher initialized"),
            ("Fear&Greed", "Fear&Greed fetcher initialized"),
            ("Macro", "Macro fetcher initialized"),
        ]

        for source_name, search_pattern in external_sources:
            try:
                cmd = [
                    "gcloud",
                    "logging",
                    "read",
                    f'resource.type=cloud_run_revision AND textPayload:"{search_pattern}"',
                    "--limit=1",
                    "--format=value(textPayload)",
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

                if result.returncode == 0 and result.stdout.strip():
                    self.log_result(
                        self.SUCCESS, f"{source_name}データソース正常", "初期化完了"
                    )
                else:
                    self.log_result(
                        self.WARNING,
                        f"{source_name}データソース状態不明",
                        "ログ確認推奨",
                    )

            except Exception as e:
                self.log_result(self.WARNING, f"{source_name}チェック失敗", str(e))

    def check_data_volume(self) -> None:
        """データ取得件数チェック"""
        print("\n🔍 === データ取得件数チェック ===")

        try:
            # データ取得件数確認
            cmd = [
                "gcloud",
                "logging",
                "read",
                'resource.type=cloud_run_revision AND textPayload:"records"',
                "--limit=5",
                "--format=value(textPayload,timestamp)",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split("\n")

                # 最新のデータ取得件数を解析
                for line in lines:
                    if "records" in line:
                        # "99 records", "500 records"などのパターンを抽出
                        import re

                        record_match = re.search(r"(\d+)\s+records", line)
                        if record_match:
                            record_count = int(record_match.group(1))

                            if record_count >= 100:
                                self.log_result(
                                    self.SUCCESS,
                                    f"データ取得件数良好: {record_count}件",
                                    "十分な学習データ",
                                )
                            elif record_count >= 50:
                                self.log_result(
                                    self.WARNING,
                                    f"データ取得件数やや少ない: {record_count}件",
                                    "ML精度に影響の可能性",
                                )
                            elif record_count >= 10:
                                self.log_result(
                                    self.WARNING,
                                    f"データ取得件数不足: {record_count}件",
                                    "取引判定に支障",
                                )
                            else:
                                self.log_result(
                                    self.CRITICAL,
                                    f"データ取得件数深刻不足: {record_count}件",
                                    "システム機能不全",
                                )
                            break
                else:
                    self.log_result(
                        self.WARNING, "データ取得件数不明", "レコード数情報なし"
                    )
            else:
                self.log_result(self.WARNING, "データ取得ログ取得失敗", "件数確認不可")

        except Exception as e:
            self.log_result(self.WARNING, "データ取得件数チェック失敗", str(e))

    def check_feature_usage_status(self) -> None:
        """特徴量使用状況チェック"""
        print("\n🔍 === 特徴量使用状況チェック ===")

        try:
            # 151特徴量生成状況確認
            cmd = [
                "gcloud",
                "logging",
                "read",
                'resource.type=cloud_run_revision AND textPayload:"features.*generated"',
                "--limit=3",
                "--format=value(textPayload)",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split("\n")

                # 特徴量数の解析
                for line in lines:
                    import re

                    feature_match = re.search(r"(\d+)\s+features", line)
                    if feature_match:
                        feature_count = int(feature_match.group(1))

                        if feature_count >= 140:
                            self.log_result(
                                self.SUCCESS,
                                f"特徴量生成完全: {feature_count}特徴量",
                                "151特徴量システム正常",
                            )
                        elif feature_count >= 100:
                            self.log_result(
                                self.WARNING,
                                f"特徴量やや不足: {feature_count}特徴量",
                                "一部外部データ未取得の可能性",
                            )
                        elif feature_count >= 50:
                            self.log_result(
                                self.WARNING,
                                f"特徴量大幅不足: {feature_count}特徴量",
                                "外部データ系統問題",
                            )
                        else:
                            self.log_result(
                                self.CRITICAL,
                                f"特徴量深刻不足: {feature_count}特徴量",
                                "基本特徴量のみ",
                            )
                        break
                else:
                    self.log_result(self.INFO, "特徴量生成ログ確認", "数値情報なし")
            else:
                # 特徴量警告チェック
                cmd_warning = [
                    "gcloud",
                    "logging",
                    "read",
                    'resource.type=cloud_run_revision AND textPayload:"WARNING.*feature"',
                    "--limit=3",
                    "--format=value(textPayload)",
                ]
                result_warning = subprocess.run(
                    cmd_warning, capture_output=True, text=True, timeout=10
                )

                if result_warning.returncode == 0 and result_warning.stdout.strip():
                    warning_lines = result_warning.stdout.strip().split("\n")
                    self.log_result(
                        self.WARNING,
                        f"特徴量警告検出: {len(warning_lines)}件",
                        "未実装特徴量の可能性",
                    )
                else:
                    self.log_result(self.INFO, "特徴量状態ログなし", "初期化中の可能性")

        except Exception as e:
            self.log_result(self.WARNING, "特徴量使用状況チェック失敗", str(e))

    def check_multiframe_processing(self) -> None:
        """マルチタイムフレーム処理チェック"""
        print("\n🔍 === マルチタイムフレーム処理チェック ===")

        try:
            # マルチタイムフレーム設定確認
            cmd = [
                "gcloud",
                "logging",
                "read",
                'resource.type=cloud_run_revision AND textPayload:"ensemble processor created"',
                "--limit=3",
                "--format=value(textPayload)",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split("\n")
                timeframes = ["15m", "1h", "4h"]

                created_processors = []
                for tf in timeframes:
                    if any(tf in line for line in lines):
                        created_processors.append(tf)
                        self.log_result(
                            self.SUCCESS, f"{tf}プロセッサ正常", "アンサンブル準備完了"
                        )
                    else:
                        self.log_result(
                            self.WARNING, f"{tf}プロセッサ状態不明", "設定確認推奨"
                        )

                # 全体評価
                if len(created_processors) == 3:
                    self.log_result(
                        self.SUCCESS,
                        "マルチタイムフレーム完全準備",
                        "15m/1h/4h統合可能",
                    )
                elif len(created_processors) >= 2:
                    self.log_result(
                        self.WARNING,
                        "マルチタイムフレーム部分準備",
                        f"{'/'.join(created_processors)}のみ",
                    )
                else:
                    self.log_result(
                        self.CRITICAL, "マルチタイムフレーム準備不足", "統合分析不可"
                    )

            else:
                # base_timeframe設定確認
                cmd_base = [
                    "gcloud",
                    "logging",
                    "read",
                    'resource.type=cloud_run_revision AND textPayload:"base_timeframe"',
                    "--limit=2",
                    "--format=value(textPayload)",
                ]
                result_base = subprocess.run(
                    cmd_base, capture_output=True, text=True, timeout=10
                )

                if result_base.returncode == 0 and result_base.stdout.strip():
                    base_lines = result_base.stdout.strip().split("\n")
                    if any("1h" in line for line in base_lines):
                        self.log_result(
                            self.SUCCESS, "ベースタイムフレーム設定正常", "1h基準設定"
                        )
                    else:
                        self.log_result(
                            self.WARNING,
                            "ベースタイムフレーム設定異常",
                            "4h直接取得の可能性",
                        )
                else:
                    self.log_result(
                        self.WARNING, "マルチタイムフレーム状態不明", "ログ確認推奨"
                    )

        except Exception as e:
            self.log_result(self.WARNING, "マルチタイムフレームチェック失敗", str(e))

    def check_data_conversion_status(self) -> None:
        """データ変換状況チェック"""
        print("\n🔍 === データ変換状況チェック ===")

        try:
            # 15m補間・4h集約の動作確認
            conversion_patterns = [
                ("15m補間", "interpolation", "1h→15m変換"),
                ("4h集約", "aggregation", "1h→4h変換"),
                ("データ同期", "data_sync", "タイムフレーム同期"),
            ]

            for conv_name, pattern, description in conversion_patterns:
                cmd = [
                    "gcloud",
                    "logging",
                    "read",
                    f'resource.type=cloud_run_revision AND textPayload:"{pattern}"',
                    "--limit=1",
                    "--format=value(textPayload)",
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

                if result.returncode == 0 and result.stdout.strip():
                    self.log_result(self.SUCCESS, f"{conv_name}処理確認", description)
                else:
                    self.log_result(
                        self.INFO, f"{conv_name}処理ログなし", "動作中の可能性"
                    )

        except Exception as e:
            self.log_result(self.WARNING, "データ変換状況チェック失敗", str(e))

    def check_weekend_trading_schedule(self) -> None:
        """土日取引スケジュールチェック"""
        print("\n🔍 === 土日取引スケジュール状態チェック ===")

        current_time = datetime.now()
        is_weekend = current_time.weekday() >= 5  # 土曜日(5), 日曜日(6)

        if is_weekend:
            self.log_result(
                self.INFO,
                "土日期間中",
                "monitoring_only_periods設定により監視のみ実行中",
            )

            # 土日取引設定確認
            try:
                cmd = [
                    "gcloud",
                    "logging",
                    "read",
                    'resource.type=cloud_run_revision AND textPayload:"weekend"',
                    "--limit=3",
                    "--format=value(textPayload)",
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

                if result.returncode == 0 and result.stdout.strip():
                    self.log_result(self.SUCCESS, "土日設定認識", "週末モード動作中")
                else:
                    self.log_result(self.INFO, "土日設定ログなし", "通常動作の可能性")

            except Exception as e:
                self.log_result(self.WARNING, "土日設定チェック失敗", str(e))
        else:
            self.log_result(self.SUCCESS, "平日期間", "通常取引スケジュール")

    def check_error_patterns(self) -> None:
        """エラーパターンチェック"""
        print("\n🔍 === エラーパターンチェック ===")

        error_patterns = [
            ("API Error 10000", "10000", self.CRITICAL),
            ("認証エラー", "401.*unauthorized", self.CRITICAL),
            ("権限エラー", "403.*forbidden", self.CRITICAL),
            ("タイムアウト", "timeout", self.WARNING),
            ("メモリエラー", "memory.*error", self.WARNING),
            ("レート制限", "rate.*limit", self.WARNING),
        ]

        for error_name, pattern, severity in error_patterns:
            try:
                cmd = [
                    "gcloud",
                    "logging",
                    "read",
                    f'resource.type=cloud_run_revision AND textPayload:"{pattern}"',
                    "--limit=1",
                    "--format=value(textPayload,timestamp)",
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

                if result.returncode == 0 and result.stdout.strip():
                    lines = result.stdout.strip().split("\n")
                    latest_error = lines[0] if lines else "詳細不明"
                    self.log_result(severity, f"{error_name}検出", latest_error[:100])
                else:
                    self.log_result(self.SUCCESS, f"{error_name}なし", "正常")

            except Exception as e:
                self.log_result(self.WARNING, f"{error_name}チェック失敗", str(e))

    def generate_summary_report(self) -> Dict:
        """サマリーレポート生成"""
        print("\n" + "=" * 50)
        print("📊 === システムヘルスチェック結果サマリー ===")
        print("=" * 50)

        success_rate = (
            (self.checks_passed / self.checks_total * 100)
            if self.checks_total > 0
            else 0
        )

        print(
            f"✅ 成功: {self.checks_passed}/{self.checks_total} ({success_rate:.1f}%)"
        )
        print(f"❌ 問題: {len(self.issues)}件")

        # 重要度別集計
        critical_issues = [i for i in self.issues if i["severity"] == self.CRITICAL]
        warning_issues = [i for i in self.issues if i["severity"] == self.WARNING]

        print(f"\n🚨 CRITICAL問題: {len(critical_issues)}件")
        for issue in critical_issues:
            print(f"  - {issue['message']}")
            if issue["details"]:
                print(f"    {issue['details']}")

        print(f"\n⚠️ WARNING問題: {len(warning_issues)}件")
        for issue in warning_issues:
            print(f"  - {issue['message']}")

        # 修正提案
        if critical_issues or warning_issues:
            print(f"\n🚀 === 修正提案 ===")
            self.generate_fix_suggestions(critical_issues, warning_issues)

        return {
            "timestamp": datetime.now().isoformat(),
            "success_rate": success_rate,
            "checks_passed": self.checks_passed,
            "checks_total": self.checks_total,
            "critical_issues": len(critical_issues),
            "warning_issues": len(warning_issues),
            "issues": self.issues,
        }

    def generate_fix_suggestions(
        self, critical_issues: List, warning_issues: List
    ) -> None:
        """修正提案生成"""

        if any("データが古すぎます" in issue["message"] for issue in critical_issues):
            print("1. Phase H.8: 最新データ強制取得システム実装")
            print("   - since=None フォールバック機能追加")
            print("   - 並行データ取得による最新データ確保")

        if any("API認証" in issue["message"] for issue in critical_issues):
            print("2. API認証情報更新")
            print("   - GitHub Secrets確認")
            print("   - Bitbank APIキー有効性確認")

        if any("10000" in issue["message"] for issue in critical_issues):
            print("3. API Error 10000対策")
            print("   - Phase H.3.2修正の再適用")
            print("   - 4時間足直接取得禁止の徹底")

        if any("MLモデル" in issue["message"] for issue in warning_issues):
            print("4. MLモデル状態確認")
            print("   - /app/models/production/model.pkl 存在確認")
            print("   - Cloud Storage同期状態確認")

    def run_all_checks(self, detailed: bool = False) -> Dict:
        """全チェック実行"""
        print("🚀 包括的システムヘルスチェック開始")
        print(f"📅 実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 基本チェック（必須）
        if not self.check_basic_health():
            print("❌ 基本システムが応答しないため、他のチェックをスキップします")
            return self.generate_summary_report()

        # 詳細チェック
        self.check_detailed_health()
        self.check_data_freshness()  # 最重要
        self.check_data_volume()  # データ取得件数
        self.check_initialization_status()
        self.check_ml_model_status()
        self.check_feature_usage_status()  # 特徴量使用状況
        self.check_external_data_sources()
        self.check_multiframe_processing()  # マルチタイムフレーム
        self.check_data_conversion_status()  # データ変換状況
        self.check_weekend_trading_schedule()
        self.check_error_patterns()

        return self.generate_summary_report()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Bot包括的ヘルスチェック")
    parser.add_argument("--detailed", action="store_true", help="詳細ログ出力")
    parser.add_argument("--json", action="store_true", help="JSON形式出力")
    parser.add_argument("--save", type=str, help="結果をファイルに保存")

    args = parser.parse_args()

    checker = BotHealthChecker()
    result = checker.run_all_checks(detailed=args.detailed)

    if args.json:
        print("\n" + "=" * 30)
        print("JSON出力:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

    if args.save:
        with open(args.save, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n結果を保存: {args.save}")

    # 終了コード設定（CI/CD用）
    critical_count = result.get("critical_issues", 0)
    if critical_count > 0:
        sys.exit(1)  # CRITICAL問題がある場合は異常終了
    else:
        sys.exit(0)  # 正常終了


if __name__ == "__main__":
    main()
