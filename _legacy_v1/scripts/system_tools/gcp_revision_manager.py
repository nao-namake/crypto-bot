#!/usr/bin/env python3
"""
Phase H.28.4: GCP運用環境完全最適化・リビジョン管理システム
Cloud Runリビジョンライフサイクル管理・現在稼働リビジョン限定監視
"""

import json
import logging
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class GCPRevisionManager:
    """GCP Cloud Runリビジョン管理システム"""

    def __init__(
        self,
        service_name: str = "crypto-bot-service-prod",
        region: str = "asia-northeast1",
    ):
        """
        GCPリビジョン管理システム初期化

        Args:
            service_name: Cloud Runサービス名
            region: GCPリージョン
        """
        self.service_name = service_name
        self.region = region
        self.max_revisions = 3  # Phase H.28.4: 最新3リビジョンまで保持

        logger.info(f"GCP Revision Manager initialized: {service_name} in {region}")

    def get_current_revision_info(self) -> Dict:
        """現在稼働中のリビジョン情報取得"""
        try:
            cmd = [
                "gcloud",
                "run",
                "services",
                "describe",
                self.service_name,
                "--region",
                self.region,
                "--format",
                "json",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            service_info = json.loads(result.stdout)

            # トラフィック情報から現在のリビジョンを特定
            current_revision = None
            for traffic in service_info.get("status", {}).get("traffic", []):
                if traffic.get("percent", 0) > 0:
                    current_revision = traffic.get("revisionName")
                    break

            revision_info = {
                "current_revision": current_revision,
                "service_url": service_info.get("status", {}).get("url"),
                "last_modified": service_info.get("metadata", {})
                .get("annotations", {})
                .get("serving.knative.dev/lastModifier"),
                "traffic_allocation": service_info.get("status", {}).get("traffic", []),
            }

            logger.info(f"Current revision: {current_revision}")
            return revision_info

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get current revision info: {e}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse service info JSON: {e}")
            return {}

    def list_all_revisions(self) -> List[Dict]:
        """全リビジョン一覧取得"""
        try:
            cmd = [
                "gcloud",
                "run",
                "revisions",
                "list",
                "--service",
                self.service_name,
                "--region",
                self.region,
                "--format",
                "json",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            revisions = json.loads(result.stdout)

            # 作成時刻でソート（新しい順）
            revisions.sort(
                key=lambda x: x.get("metadata", {}).get("creationTimestamp", ""),
                reverse=True,
            )

            revision_list = []
            for rev in revisions:
                metadata = rev.get("metadata", {})
                status = rev.get("status", {})

                revision_info = {
                    "name": metadata.get("name"),
                    "creation_time": metadata.get("creationTimestamp"),
                    "ready": any(
                        c.get("status") == "True" for c in status.get("conditions", [])
                    ),
                    "serving": metadata.get("labels", {}).get(
                        "serving.knative.dev/service"
                    )
                    == self.service_name,
                    "age_hours": self._calculate_age_hours(
                        metadata.get("creationTimestamp")
                    ),
                }
                revision_list.append(revision_info)

            logger.info(f"Found {len(revision_list)} revisions")
            return revision_list

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to list revisions: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse revisions JSON: {e}")
            return []

    def cleanup_old_revisions(self) -> Tuple[int, List[str]]:
        """
        Phase H.28.4: 古いリビジョンクリーンアップ
        最新3リビジョンを除いて古いリビジョンを削除

        Returns:
            Tuple[削除されたリビジョン数, 削除されたリビジョン名リスト]
        """
        logger.info("Starting revision cleanup...")

        revisions = self.list_all_revisions()
        current_info = self.get_current_revision_info()
        current_revision = current_info.get("current_revision")

        if not revisions:
            logger.warning("No revisions found")
            return 0, []

        # 現在稼働中のリビジョンを保護
        protected_revisions = {current_revision} if current_revision else set()

        # 最新のリビジョンも保護（上位max_revisionsまで）
        for i, rev in enumerate(revisions[: self.max_revisions]):
            protected_revisions.add(rev["name"])

        # 削除対象のリビジョンを特定
        revisions_to_delete = []
        for rev in revisions[self.max_revisions :]:
            if rev["name"] not in protected_revisions:
                # 24時間以上前のリビジョンのみ削除（安全性確保）
                if rev["age_hours"] >= 24:
                    revisions_to_delete.append(rev["name"])

        logger.info(f"Revisions to delete: {len(revisions_to_delete)}")
        logger.info(f"Protected revisions: {protected_revisions}")

        deleted_revisions = []
        for revision_name in revisions_to_delete:
            if self._delete_revision(revision_name):
                deleted_revisions.append(revision_name)

        logger.info(f"Successfully deleted {len(deleted_revisions)} old revisions")
        return len(deleted_revisions), deleted_revisions

    def _delete_revision(self, revision_name: str) -> bool:
        """個別リビジョン削除"""
        try:
            cmd = [
                "gcloud",
                "run",
                "revisions",
                "delete",
                revision_name,
                "--region",
                self.region,
                "--quiet",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"Deleted revision: {revision_name}")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to delete revision {revision_name}: {e}")
            return False

    def _calculate_age_hours(self, creation_timestamp: str) -> float:
        """リビジョン作成からの経過時間計算（時間単位）"""
        try:
            # ISO形式のタイムスタンプをパース
            creation_time = datetime.fromisoformat(
                creation_timestamp.replace("Z", "+00:00")
            )
            now = datetime.now(creation_time.tzinfo)
            age = now - creation_time
            return age.total_seconds() / 3600
        except Exception as e:
            logger.warning(
                f"Failed to calculate age for timestamp {creation_timestamp}: {e}"
            )
            return 0

    def get_active_revision_metrics(self) -> Dict:
        """
        Phase H.28.4: 現在稼働リビジョン限定監視
        現在稼働中のリビジョンのみのメトリクス取得
        """
        current_info = self.get_current_revision_info()
        current_revision = current_info.get("current_revision")

        if not current_revision:
            logger.error("No current revision found")
            return {}

        try:
            # Cloud Run メトリクス取得（過去1時間）
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=1)

            metrics_data = {
                "revision_name": current_revision,
                "service_url": current_info.get("service_url"),
                "monitoring_period": f"{start_time.isoformat()} to {end_time.isoformat()}",
                "health_check_url": f"{current_info.get('service_url', '')}/health",
                "detailed_health_url": f"{current_info.get('service_url', '')}/health/detailed",
                "resilience_health_url": f"{current_info.get('service_url', '')}/health/resilience",
            }

            logger.info(f"Active revision metrics for: {current_revision}")
            return metrics_data

        except Exception as e:
            logger.error(f"Failed to get active revision metrics: {e}")
            return {}

    def verify_deployment_health(self, timeout_minutes: int = 5) -> Dict:
        """
        Phase H.28.4: デプロイ検証フロー
        新デプロイ後の自動ヘルスチェック・ロールバック判定
        """
        logger.info("Starting deployment health verification...")

        current_info = self.get_current_revision_info()
        current_revision = current_info.get("current_revision")
        service_url = current_info.get("service_url")

        if not service_url:
            return {"status": "FAILED", "reason": "No service URL found"}

        health_checks = {
            "basic_health": f"{service_url}/health",
            "detailed_health": f"{service_url}/health/detailed",
            "resilience_health": f"{service_url}/health/resilience",
        }

        verification_results = {
            "revision_name": current_revision,
            "verification_time": datetime.now().isoformat(),
            "overall_status": "PASSED",
            "health_checks": {},
            "deployment_recommendation": "KEEP",
        }

        failed_checks = 0

        for check_name, check_url in health_checks.items():
            try:
                import requests

                response = requests.get(check_url, timeout=30)

                check_result = {
                    "url": check_url,
                    "status_code": response.status_code,
                    "response_time_ms": response.elapsed.total_seconds() * 1000,
                    "status": "PASSED" if response.status_code == 200 else "FAILED",
                }

                if response.status_code != 200:
                    failed_checks += 1
                    check_result["error"] = f"HTTP {response.status_code}"

                verification_results["health_checks"][check_name] = check_result

            except Exception as e:
                failed_checks += 1
                verification_results["health_checks"][check_name] = {
                    "url": check_url,
                    "status": "FAILED",
                    "error": str(e),
                }

        # 判定ロジック
        if failed_checks == 0:
            verification_results["overall_status"] = "PASSED"
            verification_results["deployment_recommendation"] = "KEEP"
        elif failed_checks <= 1:
            verification_results["overall_status"] = "WARNING"
            verification_results["deployment_recommendation"] = "MONITOR"
        else:
            verification_results["overall_status"] = "FAILED"
            verification_results["deployment_recommendation"] = "ROLLBACK"

        logger.info(
            f"Deployment verification: {verification_results['overall_status']}"
        )
        logger.info(
            f"Recommendation: {verification_results['deployment_recommendation']}"
        )

        return verification_results

    def generate_operational_dashboard(self) -> Dict:
        """
        Phase H.28.4: 統合診断ダッシュボード
        リアルタイム運用状況・包括的システム状態可視化
        """
        logger.info("Generating operational dashboard...")

        try:
            # 各種情報を統合
            current_info = self.get_current_revision_info()
            revisions = self.list_all_revisions()
            metrics = self.get_active_revision_metrics()
            health_status = self.verify_deployment_health()

            dashboard_data = {
                "generated_at": datetime.now().isoformat(),
                "service_name": self.service_name,
                "region": self.region,
                # 現在の稼働状況
                "current_status": {
                    "active_revision": current_info.get("current_revision"),
                    "service_url": current_info.get("service_url"),
                    "health_status": health_status.get("overall_status", "UNKNOWN"),
                    "deployment_recommendation": health_status.get(
                        "deployment_recommendation", "UNKNOWN"
                    ),
                },
                # リビジョン管理状況
                "revision_management": {
                    "total_revisions": len(revisions),
                    "latest_revisions": [rev["name"] for rev in revisions[:3]],
                    "oldest_revision_age_hours": (
                        revisions[-1]["age_hours"] if revisions else 0
                    ),
                    "cleanup_needed": len(revisions) > self.max_revisions,
                },
                # 監視・ヘルスチェック
                "monitoring": {
                    "health_check_endpoints": metrics.get("health_check_url"),
                    "detailed_health": metrics.get("detailed_health_url"),
                    "resilience_check": metrics.get("resilience_health_url"),
                    "monitoring_period": metrics.get("monitoring_period"),
                },
                # 運用推奨事項
                "operational_recommendations": self._generate_operational_recommendations(
                    current_info, revisions, health_status
                ),
            }

            logger.info("Operational dashboard generated successfully")
            return dashboard_data

        except Exception as e:
            logger.error(f"Failed to generate operational dashboard: {e}")
            return {"error": str(e), "generated_at": datetime.now().isoformat()}

    def _generate_operational_recommendations(
        self, current_info: Dict, revisions: List[Dict], health_status: Dict
    ) -> List[str]:
        """運用推奨事項生成"""
        recommendations = []

        # リビジョン管理推奨
        if len(revisions) > self.max_revisions:
            recommendations.append(
                f"古いリビジョンクリーンアップ推奨: {len(revisions) - self.max_revisions}個の古いリビジョンが存在"
            )

        # ヘルスチェック推奨
        if health_status.get("overall_status") == "FAILED":
            recommendations.append("緊急対応必要: ヘルスチェック失敗、ロールバック検討")
        elif health_status.get("overall_status") == "WARNING":
            recommendations.append("注意監視必要: 一部ヘルスチェック異常、継続監視推奨")

        # 運用効率推奨
        if not recommendations:
            recommendations.append("システム正常稼働中: 定期的な監視継続推奨")

        return recommendations

    def run_comprehensive_optimization(self) -> Dict:
        """
        Phase H.28.4: 包括的GCP運用環境最適化実行
        リビジョン管理・監視・診断の統合実行
        """
        logger.info("🚀 Phase H.28.4: GCP運用環境完全最適化開始")
        logger.info("=" * 70)

        optimization_results = {
            "phase": "H.28.4",
            "start_time": datetime.now().isoformat(),
            "service_name": self.service_name,
            "region": self.region,
        }

        try:
            # Step 1: リビジョンクリーンアップ
            logger.info("📋 Step 1: リビジョンライフサイクル管理")
            deleted_count, deleted_revisions = self.cleanup_old_revisions()
            optimization_results["revision_cleanup"] = {
                "deleted_count": deleted_count,
                "deleted_revisions": deleted_revisions,
                "status": "SUCCESS",
            }

            # Step 2: 現在稼働リビジョン監視
            logger.info("🔍 Step 2: 現在稼働リビジョン限定監視")
            active_metrics = self.get_active_revision_metrics()
            optimization_results["active_monitoring"] = {
                "metrics": active_metrics,
                "status": "SUCCESS" if active_metrics else "FAILED",
            }

            # Step 3: デプロイ検証
            logger.info("✅ Step 3: デプロイ検証フロー")
            health_verification = self.verify_deployment_health()
            optimization_results["deployment_verification"] = health_verification

            # Step 4: 統合診断ダッシュボード
            logger.info("📊 Step 4: 統合診断ダッシュボード生成")
            dashboard = self.generate_operational_dashboard()
            optimization_results["operational_dashboard"] = dashboard

            # 総合評価
            optimization_results["end_time"] = datetime.now().isoformat()
            optimization_results["overall_status"] = (
                self._evaluate_optimization_success(optimization_results)
            )

            logger.info("=" * 70)
            logger.info(
                f"✅ Phase H.28.4完了: {optimization_results['overall_status']}"
            )

            return optimization_results

        except Exception as e:
            logger.error(f"❌ Phase H.28.4失敗: {e}")
            optimization_results["error"] = str(e)
            optimization_results["overall_status"] = "FAILED"
            return optimization_results

    def _evaluate_optimization_success(self, results: Dict) -> str:
        """最適化成功評価"""
        success_indicators = [
            results.get("revision_cleanup", {}).get("status") == "SUCCESS",
            results.get("active_monitoring", {}).get("status") == "SUCCESS",
            results.get("deployment_verification", {}).get("overall_status")
            in ["PASSED", "WARNING"],
            "operational_dashboard" in results
            and "error" not in results.get("operational_dashboard", {}),
        ]

        success_count = sum(success_indicators)

        if success_count == 4:
            return "COMPLETE_SUCCESS"
        elif success_count >= 3:
            return "PARTIAL_SUCCESS"
        else:
            return "FAILED"


def main():
    """メイン実行関数"""
    try:
        logger.info("🚀 GCP Revision Manager starting...")

        manager = GCPRevisionManager()
        results = manager.run_comprehensive_optimization()

        # 結果保存
        output_dir = Path(project_root / "results" / "gcp_optimization")
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = output_dir / f"gcp_optimization_{timestamp}.json"

        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"📁 結果保存: {results_file}")

        # 結果サマリー表示
        print("\n📊 GCP運用環境最適化結果サマリー")
        print("=" * 50)
        print(f"総合ステータス: {results['overall_status']}")

        if results.get("revision_cleanup"):
            cleanup = results["revision_cleanup"]
            print(f"リビジョンクリーンアップ: {cleanup['deleted_count']}個削除")

        if results.get("deployment_verification"):
            health = results["deployment_verification"]
            print(f"デプロイヘルス: {health['overall_status']}")
            print(f"推奨アクション: {health['deployment_recommendation']}")

        if results.get("operational_dashboard"):
            dashboard = results["operational_dashboard"]
            if "current_status" in dashboard:
                current = dashboard["current_status"]
                print(f"現在稼働: {current.get('active_revision', 'Unknown')}")
                print(f"ヘルス状態: {current.get('health_status', 'Unknown')}")

        return (
            0
            if results["overall_status"] in ["COMPLETE_SUCCESS", "PARTIAL_SUCCESS"]
            else 1
        )

    except Exception as e:
        logger.error(f"GCP Revision Manager failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
