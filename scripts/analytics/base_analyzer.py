#!/usr/bin/env python3
"""
Phase 29: 共通分析基盤クラス（Phase 29最適化完了・625テスト品質保証）

Cloud Runログ取得・gcloudコマンド実行・データ読み込み機能の統合基盤クラス。
dev_check.pyから使用され、システム分析・監視機能の共通基盤を提供。

主な機能:
- Cloud Runサービス状態確認・ログ取得
- gcloudコマンド実行ラッパー
- ログ解析・シグナル頻度分析
- CSV/JSONファイル読み込み・保存機能
"""

import json
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd

# ログ設定
logger = logging.getLogger(__name__)


class BaseAnalyzer:
    """分析スクリプト共通基盤クラス"""

    def __init__(
        self,
        project_id: str = "my-crypto-bot-project",
        service_name: str = "crypto-bot-service",
        region: str = "asia-northeast1",
        output_dir: str = "logs",
    ):
        self.project_id = project_id
        self.service_name = service_name
        self.region = region
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)

        logger.info(f"BaseAnalyzer初期化: {service_name}@{region}")

    # ===== 共通gcloudコマンド実行機能 =====

    def run_gcloud_command(
        self, command: List[str], timeout: int = 60, show_output: bool = False
    ) -> Tuple[int, str, str]:
        """gcloudコマンド実行の共通ラッパー"""
        if show_output:
            logger.info(f"gcloudコマンド実行: {' '.join(command)}")

        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)

            if show_output and result.returncode != 0:
                logger.error(f"gcloudコマンドエラー: {result.stderr}")

            return result.returncode, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            logger.error(f"gcloudコマンドタイムアウト: {timeout}秒")
            return 1, "", "Command timeout"
        except Exception as e:
            logger.error(f"gcloudコマンド実行エラー: {e}")
            return 1, "", str(e)

    # ===== 共通Cloud Runログ取得機能 =====

    def fetch_cloud_run_logs(
        self,
        hours: int = 24,
        service_suffix: str = "",
        log_filter: str = "",
        limit: int = 500,
    ) -> Tuple[bool, List[Dict]]:
        """Cloud Runログ取得の共通機能"""
        target_service = f"{self.service_name}{service_suffix}"
        start_time = (datetime.utcnow() - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")

        # デフォルトフィルタ：取引・シグナル関連
        if not log_filter:
            log_filter = (
                f'(jsonPayload.message~"SIGNAL" OR jsonPayload.message~"BUY" OR '
                f'jsonPayload.message~"SELL" OR jsonPayload.message~"HOLD" OR '
                f'textPayload~"SIGNAL" OR textPayload~"BUY" OR '
                f'textPayload~"SELL" OR textPayload~"HOLD")'
            )

        cmd = [
            "gcloud",
            "logging",
            "read",
            f'resource.type="cloud_run_revision" AND '
            f'resource.labels.service_name="{target_service}" AND '
            f"{log_filter} AND "
            f'timestamp >= "{start_time}"',
            "--limit",
            str(limit),
            "--format",
            "json",
        ]

        logger.info(f"Cloud Runログ取得開始: {target_service} (過去{hours}時間)")

        returncode, stdout, stderr = self.run_gcloud_command(cmd)

        if returncode != 0:
            logger.error(f"ログ取得失敗: {stderr}")
            return False, []

        try:
            logs = json.loads(stdout) if stdout.strip() else []
            logger.info(f"ログ取得成功: {len(logs)}件")
            return True, logs
        except json.JSONDecodeError as e:
            logger.error(f"ログJSON解析失敗: {e}")
            return False, []

    def fetch_error_logs(
        self, hours: int = 24, service_suffix: str = ""
    ) -> Tuple[bool, List[Dict]]:
        """エラーログ専用取得"""
        error_filter = "severity >= ERROR"
        return self.fetch_cloud_run_logs(
            hours=hours,
            service_suffix=service_suffix,
            log_filter=error_filter,
            limit=100,
        )

    def fetch_trading_logs(
        self, hours: int = 24, service_suffix: str = ""
    ) -> Tuple[bool, List[Dict]]:
        """取引ログ専用取得"""
        trading_filter = (
            f'(jsonPayload.message~"注文" OR jsonPayload.message~"取引" OR '
            f'jsonPayload.message~"SIGNAL" OR jsonPayload.message~"BUY" OR '
            f'jsonPayload.message~"SELL" OR jsonPayload.message~"HOLD" OR '
            f'textPayload~"SIGNAL" OR textPayload~"BUY" OR '
            f'textPayload~"SELL" OR textPayload~"HOLD")'
        )
        return self.fetch_cloud_run_logs(
            hours=hours,
            service_suffix=service_suffix,
            log_filter=trading_filter,
            limit=300,
        )

    # ===== 共通Cloud Runサービス状態確認 =====

    def check_service_health(self, service_suffix: str = "") -> Dict:
        """Cloud Runサービス状態確認"""
        target_service = f"{self.service_name}{service_suffix}"

        logger.info(f"サービス状態確認: {target_service}")

        cmd = [
            "gcloud",
            "run",
            "services",
            "describe",
            target_service,
            "--region",
            self.region,
            "--format",
            "json",
        ]

        returncode, stdout, stderr = self.run_gcloud_command(cmd)

        if returncode == 0:
            try:
                service_info = json.loads(stdout)

                health_data = {
                    "service_status": "UP",
                    "service_name": target_service,
                    "latest_revision": service_info.get("status", {}).get(
                        "latestReadyRevisionName", "unknown"
                    ),
                    "traffic_allocation": service_info.get("status", {}).get("traffic", []),
                    "url": service_info.get("status", {}).get("url", ""),
                    "last_updated": service_info.get("metadata", {})
                    .get("annotations", {})
                    .get("run.googleapis.com/lastModifier", "unknown"),
                    "cpu": service_info.get("spec", {})
                    .get("template", {})
                    .get("spec", {})
                    .get("containerConcurrency", "unknown"),
                    "memory": service_info.get("spec", {})
                    .get("template", {})
                    .get("spec", {})
                    .get("containers", [{}])[0]
                    .get("resources", {})
                    .get("limits", {})
                    .get("memory", "unknown"),
                }

                logger.info(f"✅ サービス状態: {health_data['service_status']}")
                return health_data

            except json.JSONDecodeError as e:
                logger.error(f"サービス情報JSON解析失敗: {e}")
                return {"service_status": "JSON_ERROR", "error": str(e)}
        else:
            logger.error(f"❌ サービス状態取得失敗: {stderr}")
            return {"service_status": "DOWN", "error": stderr}

    def check_service_endpoint(self, service_suffix: str = "") -> Dict:
        """サービスエンドポイント応答確認"""
        health_data = self.check_service_health(service_suffix)

        if health_data.get("service_status") != "UP":
            return health_data

        service_url = health_data.get("url", "")
        if not service_url:
            return {**health_data, "endpoint_status": "NO_URL"}

        try:
            import urllib.error
            import urllib.request

            with urllib.request.urlopen(f"{service_url}/health", timeout=10) as response:
                if response.status == 200:
                    logger.info("✅ エンドポイント応答OK")
                    return {
                        **health_data,
                        "endpoint_status": "OK",
                        "endpoint_response_code": 200,
                    }
                else:
                    logger.warning(f"⚠️ エンドポイント応答異常: {response.status}")
                    return {
                        **health_data,
                        "endpoint_status": "ERROR",
                        "endpoint_response_code": response.status,
                    }

        except urllib.error.URLError as e:
            logger.error(f"❌ エンドポイント接続失敗: {e}")
            return {
                **health_data,
                "endpoint_status": "CONNECTION_ERROR",
                "endpoint_error": str(e),
            }
        except Exception as e:
            logger.error(f"❌ エンドポイントチェックエラー: {e}")
            return {
                **health_data,
                "endpoint_status": "UNKNOWN_ERROR",
                "endpoint_error": str(e),
            }

    # ===== 共通データファイル読み込み機能 =====

    def load_csv_files(self, pattern: str, directory: str = None) -> List[pd.DataFrame]:
        """CSVファイル読み込み（パターンマッチング）"""
        target_dir = Path(directory) if directory else self.output_dir

        csv_files = list(target_dir.glob(pattern))
        if not csv_files:
            logger.warning(f"CSVファイルが見つかりません: {pattern}")
            return []

        dataframes = []
        for file in csv_files:
            try:
                df = pd.read_csv(file)
                dataframes.append(df)
                logger.info(f"CSV読み込み成功: {file.name} ({len(df)}行)")
            except Exception as e:
                logger.warning(f"CSV読み込み失敗 {file}: {e}")

        return dataframes

    def load_json_files(self, pattern: str, directory: str = None) -> List[Dict]:
        """JSONファイル読み込み（パターンマッチング）"""
        target_dir = Path(directory) if directory else self.output_dir

        json_files = list(target_dir.glob(pattern))
        if not json_files:
            logger.warning(f"JSONファイルが見つかりません: {pattern}")
            return []

        data_list = []
        for file in json_files:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    data_list.append(data)
                    logger.info(f"JSON読み込み成功: {file.name}")
            except Exception as e:
                logger.warning(f"JSON読み込み失敗 {file}: {e}")

        return data_list

    def load_latest_data_collection_results(self, data_dir: str = None) -> Dict:
        """最新のデータ収集結果を読み込み"""
        target_dir = Path(data_dir) if data_dir else self.output_dir / "data_collection"

        if not target_dir.exists():
            logger.warning(f"データ収集ディレクトリが見つかりません: {target_dir}")
            return {"trades": [], "daily_stats": [], "performance_metrics": {}}

        # 取引データ
        trade_dfs = self.load_csv_files("trades_*.csv", str(target_dir))
        trades = trade_dfs[-1].to_dict("records") if trade_dfs else []

        # 日次統計
        stats_dfs = self.load_csv_files("daily_stats_*.csv", str(target_dir))
        daily_stats = stats_dfs[-1].to_dict("records") if stats_dfs else []

        # パフォーマンス指標
        perf_data = self.load_json_files("performance_metrics_*.json", str(target_dir))
        performance_metrics = perf_data[-1] if perf_data else {}

        logger.info(f"データ収集結果読み込み完了: 取引{len(trades)}件, 統計{len(daily_stats)}件")
        return {
            "trades": trades,
            "daily_stats": daily_stats,
            "performance_metrics": performance_metrics,
        }

    def load_ab_test_results(self, ab_test_dir: str = None) -> List[Dict]:
        """A/Bテスト結果読み込み"""
        target_dir = Path(ab_test_dir) if ab_test_dir else self.output_dir / "ab_testing"

        if not target_dir.exists():
            logger.warning(f"A/Bテストディレクトリが見つかりません: {target_dir}")
            return []

        ab_test_results = self.load_json_files("ab_test_*.json", str(target_dir))
        logger.info(f"A/Bテスト結果読み込み完了: {len(ab_test_results)}件")
        return ab_test_results

    # ===== 共通ログ解析機能 =====

    def parse_log_message(self, log_entry: Dict) -> Dict:
        """ログメッセージの共通解析"""
        message = log_entry.get("textPayload") or log_entry.get("jsonPayload", {}).get(
            "message", ""
        )
        timestamp = log_entry.get("timestamp", "")
        severity = log_entry.get("severity", "INFO")

        # シグナル種別判定
        signal_type = "unknown"
        if "BUY" in message.upper():
            signal_type = "buy"
        elif "SELL" in message.upper():
            signal_type = "sell"
        elif "HOLD" in message.upper():
            signal_type = "hold"

        # 信頼度抽出
        confidence = 0.0
        import re

        confidence_match = re.search(r"confidence[:\s]*([0-9.]+)", message.lower())
        if confidence_match:
            try:
                confidence = float(confidence_match.group(1))
            except ValueError:
                pass

        # 戦略タイプ抽出
        strategy_type = "unknown"
        if "atr" in message.lower():
            strategy_type = "atr_based"
        elif "ensemble" in message.lower():
            strategy_type = "ensemble"
        elif "ml" in message.lower():
            strategy_type = "ml_strategy"

        return {
            "timestamp": timestamp,
            "message": message,
            "severity": severity,
            "signal_type": signal_type,
            "confidence": confidence,
            "strategy_type": strategy_type,
        }

    def analyze_signal_frequency(self, logs: List[Dict], hours: int) -> Dict:
        """シグナル頻度分析"""
        parsed_logs = [self.parse_log_message(log) for log in logs]

        # シグナル分類
        signal_counts = {"buy": 0, "sell": 0, "hold": 0, "unknown": 0}
        confidences = []

        for parsed in parsed_logs:
            signal_type = parsed["signal_type"]
            if signal_type in signal_counts:
                signal_counts[signal_type] += 1

            if parsed["confidence"] > 0:
                confidences.append(parsed["confidence"])

        total_signals = sum(signal_counts.values())
        signal_frequency = total_signals / hours if hours > 0 else 0.0
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        high_confidence_count = len([c for c in confidences if c > 0.7])

        return {
            "total_signals": total_signals,
            "signal_breakdown": signal_counts,
            "signal_frequency_per_hour": round(signal_frequency, 2),
            "avg_confidence": round(avg_confidence, 3),
            "high_confidence_count": high_confidence_count,
            "analysis_period_hours": hours,
        }

    # ===== 共通ファイル保存機能 =====

    def save_json_report(self, data: Dict, filename: str) -> str:
        """JSON形式でレポート保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = self.output_dir / f"{filename}_{timestamp}.json"

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"JSONレポート保存完了: {file_path}")
        return str(file_path)

    def save_csv_data(self, data: List[Dict], filename: str) -> str:
        """CSV形式でデータ保存"""
        if not data:
            logger.warning("保存するデータがありません")
            return ""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = self.output_dir / f"{filename}_{timestamp}.csv"

        df = pd.DataFrame(data)
        df.to_csv(file_path, index=False, encoding="utf-8")

        logger.info(f"CSVデータ保存完了: {file_path} ({len(data)}行)")
        return str(file_path)
