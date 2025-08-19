#!/usr/bin/env python3
"""
crypto-bot 新システム稼働状況確認システム（Phase 12-3版・BaseAnalyzer継承）.

CI後/本番運用時の詳細診断ツール。BaseAnalyzer継承により重複コード削除。
4フェーズでの包括的稼働状況確認・問題検出・レポート生成

使用方法:
    python scripts/management/operational_status_checker.py [--verbose] [--save-report]
    python scripts/management/dev_check.py operational  # 統合CLI経由（推奨）

フェーズ構成:
    Phase 1: インフラ・基盤確認（GCP・API・リソース）
    Phase 2: アプリケーション動作確認（ログ・データ・ML）
    Phase 3: 隠れた問題検出（エラーパターン・異常検知）
    Phase 4: 総合判定・レポート生成.
"""

import json
import logging
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# プロジェクト設定
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

# base_analyzer.py活用
sys.path.append(str(Path(__file__).parent.parent))
from analytics.base_analyzer import BaseAnalyzer

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_ROOT / "logs" / "operational_status.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


class NewSystemOperationalStatusChecker(BaseAnalyzer):
    """新システム稼働状況確認システム（Phase 12-3版・BaseAnalyzer継承）."""

    def __init__(self, config_path: str = None):
        """初期化処理（BaseAnalyzer継承版）."""
        # BaseAnalyzer初期化
        super().__init__(output_dir="logs/operational_status")
        self.config_path = config_path or str(
            PROJECT_ROOT / "scripts" / "management" / "status_config.json"
        )
        self.config = self.load_config()
        self.report_dir = PROJECT_ROOT / "logs" / "operational_reports"
        self.report_dir.mkdir(exist_ok=True, parents=True)

        # 実行結果保存
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "system_version": "Phase 10 - 新システム",
            "phases": {},
            "overall_status": "UNKNOWN",
            "overall_score": 0,
            "critical_issues": [],
            "recommendations": [],
        }

        # 新システム用設定
        self.new_system_paths = {
            "core": PROJECT_ROOT / "src" / "core",
            "data": PROJECT_ROOT / "src" / "data",
            "features": PROJECT_ROOT / "src" / "features",
            "strategies": PROJECT_ROOT / "src" / "strategies",
            "ml": PROJECT_ROOT / "src" / "ml",
            "trading": PROJECT_ROOT / "src" / "trading",
            "scripts": PROJECT_ROOT / "scripts",
            "models": PROJECT_ROOT / "models",
            "tests": PROJECT_ROOT / "tests",
        }

    def load_config(self) -> Dict:
        """設定ファイルを読み込み（新システム用）."""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                logger.info(f"✅ Configuration loaded from {self.config_path}")
                return config
        except Exception as e:
            logger.warning(f"⚠️ Config load failed, using defaults: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict:
        """デフォルト設定（新システム用）."""
        return {
            "check_phases": {
                "phase1": {"name": "インフラ・基盤確認", "weight": 25},
                "phase2": {"name": "アプリケーション動作確認", "weight": 30},
                "phase3": {"name": "隠れた問題検出", "weight": 30},
                "phase4": {"name": "総合判定・レポート", "weight": 15},
            },
            "thresholds": {
                "critical_score": 70,
                "warning_score": 85,
                "max_response_time_seconds": 5.0,
                "min_test_success_rate": 0.95,
            },
            "new_system_patterns": {
                "import_errors": ["ModuleNotFoundError", "ImportError"],
                "test_failures": ["FAILED", "ERROR"],
                "ml_issues": ["prediction.*failed", "model.*error"],
            },
        }

    # ===== Phase 1: インフラ・基盤確認システム =====

    def check_project_structure(self) -> Dict[str, Any]:
        """新システムプロジェクト構造確認."""
        logger.info("🔍 Checking new system project structure...")

        try:
            _ = []  # structure_issues - 必要時に使用
            required_paths = [
                "src/core",
                "src/data",
                "src/features",
                "src/strategies",
                "src/ml",
                "src/trading",
                "scripts/management",
                "models/production",
                "tests/unit",
                "config",
            ]

            missing_paths = []
            for path_str in required_paths:
                path = PROJECT_ROOT / path_str
                if not path.exists():
                    missing_paths.append(path_str)

            if missing_paths:
                return {
                    "status": "critical",
                    "missing_paths": missing_paths,
                    "details": f"Missing {len(missing_paths)} required directories",
                }

            # 重要ファイル確認
            critical_files = [
                "src/core/config.py",
                "src/data/data_pipeline.py",
                "scripts/management/dev_check.py",
                "models/production/production_ensemble.pkl",
            ]

            missing_files = []
            for file_str in critical_files:
                file_path = PROJECT_ROOT / file_str
                if not file_path.exists():
                    missing_files.append(file_str)

            if missing_files:
                return {
                    "status": "warning",
                    "missing_files": missing_files,
                    "details": f"Missing {len(missing_files)} critical files",
                }

            return {
                "status": "healthy",
                "paths_checked": len(required_paths),
                "files_checked": len(critical_files),
                "details": "Project structure intact",
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "details": f"Structure check failed: {type(e).__name__}",
            }

    def check_system_imports(self) -> Dict[str, Any]:
        """新システムインポート確認."""
        logger.info("🔍 Checking new system imports...")

        try:
            import_tests = [
                ("src.core.config", "Config"),
                ("src.data.data_pipeline", "DataPipeline"),
                ("src.features.technical", "TechnicalIndicators"),
                ("src.strategies.base.strategy_manager", "StrategyManager"),
                ("src.ml.ensemble.ensemble_model", "EnsembleModel"),
                ("src.trading.risk", "RiskManager"),
            ]

            failed_imports = []
            for module_name, class_name in import_tests:
                try:
                    module = __import__(module_name, fromlist=[class_name])
                    getattr(module, class_name)
                except Exception as e:
                    failed_imports.append(
                        {
                            "module": module_name,
                            "class": class_name,
                            "error": str(e)[:100],
                        }
                    )

            if failed_imports:
                return {
                    "status": "critical",
                    "failed_imports": failed_imports,
                    "success_rate": (len(import_tests) - len(failed_imports)) / len(import_tests),
                    "details": f"{len(failed_imports)} import failures detected",
                }

            return {
                "status": "healthy",
                "imports_tested": len(import_tests),
                "success_rate": 1.0,
                "details": "All system imports successful",
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "details": f"Import check failed: {type(e).__name__}",
            }

    def check_ml_models_availability(self) -> Dict[str, Any]:
        """MLモデル可用性確認."""
        logger.info("🔍 Checking ML models availability...")

        try:
            models_path = PROJECT_ROOT / "models" / "production"

            # 重要モデルファイル確認
            required_models = [
                "production_ensemble.pkl",
                "production_model_metadata.json",
            ]

            missing_models = []
            for model_file in required_models:
                model_path = models_path / model_file
                if not model_path.exists():
                    missing_models.append(model_file)

            if missing_models:
                return {
                    "status": "critical",
                    "missing_models": missing_models,
                    "details": f"Missing {len(missing_models)} production models",
                }

            # ProductionEnsemble読み込みテスト
            try:
                import pickle

                with open(models_path / "production_ensemble.pkl", "rb") as f:
                    model = pickle.load(f)

                # 基本的な動作確認
                import numpy as np

                test_features = np.random.random((1, 12))  # 12特徴量
                _ = model.predict(test_features)  # predictions - テスト実行のみ

                return {
                    "status": "healthy",
                    "models_checked": len(required_models),
                    "model_type": type(model).__name__,
                    "prediction_test": "success",
                    "details": "ML models operational",
                }

            except Exception as model_error:
                return {
                    "status": "warning",
                    "model_load_error": str(model_error)[:100],
                    "details": "Model files exist but loading failed",
                }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "details": f"Model check failed: {type(e).__name__}",
            }

    def check_test_system_health(self) -> Dict[str, Any]:
        """テストシステム健全性確認."""
        logger.info("🔍 Checking test system health...")

        try:
            # 軽量テスト実行（タイムアウト付き）
            cmd = [
                "python",
                "-m",
                "pytest",
                "tests/unit/",
                "--tb=no",
                "-q",
                "--maxfail=5",
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=PROJECT_ROOT,
            )

            if result.returncode == 0:
                # 成功時の解析
                output = result.stdout
                passed_match = re.search(r"(\d+) passed", output)
                passed_count = int(passed_match.group(1)) if passed_match else 0

                return {
                    "status": "healthy",
                    "tests_passed": passed_count,
                    "exit_code": result.returncode,
                    "details": f"{passed_count} tests passed successfully",
                }

            else:
                # 失敗時の解析
                output = result.stdout + result.stderr
                failed_match = re.search(r"(\d+) failed", output)
                failed_count = int(failed_match.group(1)) if failed_match else 0

                if failed_count <= 5:  # 軽微な失敗
                    status = "warning"
                else:  # 重大な失敗
                    status = "critical"

                return {
                    "status": status,
                    "tests_failed": failed_count,
                    "exit_code": result.returncode,
                    "details": f"{failed_count} test failures detected",
                }

        except subprocess.TimeoutExpired:
            return {
                "status": "warning",
                "error": "Test execution timeout",
                "details": "Tests took too long to execute",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "details": f"Test system check failed: {type(e).__name__}",
            }

    def run_phase1_infrastructure_checks(self) -> Dict[str, Any]:
        """Phase 1: インフラ・基盤確認を実行."""
        logger.info("🚀 === Phase 1: インフラ・基盤確認（新システム） ===")

        phase1_results = {
            "phase_name": "インフラ・基盤確認",
            "weight": self.config["check_phases"]["phase1"]["weight"],
            "checks": {},
            "score": 0,
            "status": "unknown",
            "issues": [],
        }

        # 各チェック実行
        checks = {
            "project_structure": self.check_project_structure(),
            "system_imports": self.check_system_imports(),
            "ml_models_availability": self.check_ml_models_availability(),
            "test_system_health": self.check_test_system_health(),
        }

        phase1_results["checks"] = checks

        # Phase 1スコア計算
        check_scores = []
        for check_name, check_result in checks.items():
            status = check_result.get("status", "error")

            if status == "healthy":
                score = 100
            elif status == "warning":
                score = 70
            elif status == "critical":
                score = 30
            else:  # error
                score = 0

            check_scores.append(score)

            # 重大な問題を記録
            if score < 70:
                phase1_results["issues"].append(
                    {
                        "check": check_name,
                        "severity": "CRITICAL" if score <= 30 else "HIGH",
                        "message": check_result.get(
                            "error",
                            check_result.get("details", "Unknown issue"),
                        ),
                        "score": score,
                    }
                )

        # Phase 1総合スコア
        phase1_results["score"] = sum(check_scores) / len(check_scores) if check_scores else 0

        # Phase 1ステータス判定
        if phase1_results["score"] >= 80:
            phase1_results["status"] = "healthy"
        elif phase1_results["score"] >= 60:
            phase1_results["status"] = "warning"
        else:
            phase1_results["status"] = "critical"

        logger.info(
            f"✅ Phase 1 完了: スコア {phase1_results['score']:.1f}/100 ({phase1_results['status']})"
        )

        self.results["phases"]["phase1"] = phase1_results
        return phase1_results

    # ===== Phase 2: アプリケーション動作確認システム =====

    def check_data_pipeline_health(self) -> Dict[str, Any]:
        """データパイプライン健全性確認."""
        logger.info("🔍 Checking data pipeline health...")

        try:
            # DataPipeline基本動作確認
            from src.core.config import Config
            from src.data.data_pipeline import DataPipeline

            config = Config()
            _ = DataPipeline(config)  # pipeline - インスタンス化テストのみ

            # 基本的な接続テスト（軽量）
            # 注意: 実際のAPI呼び出しは避け、クラスのインスタンス化のみ

            return {
                "status": "healthy",
                "pipeline_initialized": True,
                "config_loaded": True,
                "details": "Data pipeline components operational",
            }

        except Exception as e:
            return {
                "status": "critical",
                "error": str(e),
                "details": f"Data pipeline check failed: {type(e).__name__}",
            }

    def check_ml_prediction_system(self) -> Dict[str, Any]:
        """ML予測システム確認."""
        logger.info("🔍 Checking ML prediction system...")

        try:
            # EnsembleModel基本動作確認
            from src.ml.ensemble.ensemble_model import EnsembleModel

            ensemble = EnsembleModel()

            # 12特徴量でのテスト予測
            import numpy as np

            test_features = np.random.random((5, 12))

            # 予測実行テスト
            predictions = ensemble.predict(test_features)
            probabilities = ensemble.predict_proba(test_features)

            # 予測結果の妥当性確認
            if len(predictions) == 5 and len(probabilities) == 5:
                return {
                    "status": "healthy",
                    "predictions_generated": len(predictions),
                    "feature_count": 12,
                    "model_type": type(ensemble).__name__,
                    "details": "ML prediction system operational",
                }
            else:
                return {
                    "status": "warning",
                    "predictions_generated": len(predictions),
                    "details": "ML predictions inconsistent",
                }

        except Exception as e:
            return {
                "status": "critical",
                "error": str(e),
                "details": f"ML prediction check failed: {type(e).__name__}",
            }

    def check_strategy_system_health(self) -> Dict[str, Any]:
        """戦略システム健全性確認."""
        logger.info("🔍 Checking strategy system health...")

        try:
            # StrategyManager基本動作確認
            from src.core.config import Config
            from src.strategies.base.strategy_manager import StrategyManager

            config = Config()
            strategy_manager = StrategyManager(config)

            # 戦略インスタンス化確認
            strategies_count = (
                len(strategy_manager.strategies) if hasattr(strategy_manager, "strategies") else 0
            )

            return {
                "status": "healthy",
                "manager_initialized": True,
                "strategies_loaded": strategies_count,
                "details": f"Strategy system operational with {strategies_count} strategies",
            }

        except Exception as e:
            return {
                "status": "critical",
                "error": str(e),
                "details": f"Strategy system check failed: {type(e).__name__}",
            }

    def check_trading_risk_system(self) -> Dict[str, Any]:
        """取引・リスク管理システム確認."""
        logger.info("🔍 Checking trading risk system...")

        try:
            # RiskManager基本動作確認
            from src.core.config import Config
            from src.trading.risk import RiskManager

            config = Config()
            risk_manager = RiskManager(config)

            # Kelly基準テスト（ダミーデータ）
            test_data = {
                "win_rate": 0.6,
                "avg_win": 1.5,
                "avg_loss": 1.0,
                "current_balance": 10000,
            }

            kelly_fraction = risk_manager.calculate_kelly_criterion(
                test_data["win_rate"],
                test_data["avg_win"],
                test_data["avg_loss"],
            )

            if 0 <= kelly_fraction <= 1:
                return {
                    "status": "healthy",
                    "kelly_calculation": "success",
                    "kelly_fraction": kelly_fraction,
                    "details": "Risk management system operational",
                }
            else:
                return {
                    "status": "warning",
                    "kelly_calculation": "anomaly",
                    "kelly_fraction": kelly_fraction,
                    "details": "Risk calculations producing unusual values",
                }

        except Exception as e:
            return {
                "status": "critical",
                "error": str(e),
                "details": f"Risk system check failed: {type(e).__name__}",
            }

    def run_phase2_application_checks(self) -> Dict[str, Any]:
        """Phase 2: アプリケーション動作確認を実行."""
        logger.info("🚀 === Phase 2: アプリケーション動作確認（新システム） ===")

        phase2_results = {
            "phase_name": "アプリケーション動作確認",
            "weight": self.config["check_phases"]["phase2"]["weight"],
            "checks": {},
            "score": 0,
            "status": "unknown",
            "issues": [],
        }

        # 各チェック実行
        checks = {
            "data_pipeline_health": self.check_data_pipeline_health(),
            "ml_prediction_system": self.check_ml_prediction_system(),
            "strategy_system_health": self.check_strategy_system_health(),
            "trading_risk_system": self.check_trading_risk_system(),
        }

        phase2_results["checks"] = checks

        # Phase 2スコア計算
        check_scores = []
        for check_name, check_result in checks.items():
            status = check_result.get("status", "error")

            if status == "healthy":
                score = 100
            elif status == "warning":
                score = 60
            elif status == "critical":
                score = 20
            else:  # error
                score = 0

            check_scores.append(score)

            # 重大な問題を記録
            if score < 60:
                phase2_results["issues"].append(
                    {
                        "check": check_name,
                        "severity": "CRITICAL" if score <= 20 else "HIGH",
                        "message": check_result.get(
                            "error",
                            check_result.get("details", "Unknown issue"),
                        ),
                        "score": score,
                    }
                )

        # Phase 2総合スコア
        phase2_results["score"] = sum(check_scores) / len(check_scores) if check_scores else 0

        # Phase 2ステータス判定
        if phase2_results["score"] >= 80:
            phase2_results["status"] = "healthy"
        elif phase2_results["score"] >= 60:
            phase2_results["status"] = "warning"
        else:
            phase2_results["status"] = "critical"

        logger.info(
            f"✅ Phase 2 完了: スコア {phase2_results['score']:.1f}/100 ({phase2_results['status']})"
        )

        self.results["phases"]["phase2"] = phase2_results
        return phase2_results

    # ===== Phase 3: 隠れた問題検出システム =====

    def check_critical_error_patterns(self) -> Dict[str, Any]:
        """重要エラーパターン検出（新システム用）."""
        logger.info("🔍 Checking critical error patterns...")

        detected_patterns = []

        try:
            # 新システム用重要パターン（5個に絞る）
            patterns_to_check = [
                {
                    "id": "import_errors",
                    "description": "インポートエラー・モジュール不在",
                    "severity": "CRITICAL",
                    "check_method": self._check_import_error_pattern,
                },
                {
                    "id": "ml_model_failures",
                    "description": "MLモデル予測失敗",
                    "severity": "HIGH",
                    "check_method": self._check_ml_failure_pattern,
                },
                {
                    "id": "test_system_degradation",
                    "description": "テストシステム劣化",
                    "severity": "HIGH",
                    "check_method": self._check_test_degradation_pattern,
                },
                {
                    "id": "config_inconsistency",
                    "description": "設定不整合",
                    "severity": "MEDIUM",
                    "check_method": self._check_config_inconsistency_pattern,
                },
                {
                    "id": "performance_anomaly",
                    "description": "パフォーマンス異常",
                    "severity": "MEDIUM",
                    "check_method": self._check_performance_anomaly_pattern,
                },
            ]

            for pattern in patterns_to_check:
                try:
                    detection_result = pattern["check_method"]()
                    if detection_result:
                        detected_patterns.append(
                            {
                                "id": pattern["id"],
                                "description": pattern["description"],
                                "severity": pattern["severity"],
                                "detection_details": detection_result,
                            }
                        )
                except Exception as e:
                    logger.warning(f"Pattern check failed for {pattern['id']}: {e}")

            if detected_patterns:
                critical_count = len([p for p in detected_patterns if p["severity"] == "CRITICAL"])
                high_count = len([p for p in detected_patterns if p["severity"] == "HIGH"])

                if critical_count > 0:
                    status = "critical"
                elif high_count > 0:
                    status = "warning"
                else:
                    status = "info"

                return {
                    "status": status,
                    "patterns_detected": len(detected_patterns),
                    "critical_patterns": critical_count,
                    "high_patterns": high_count,
                    "detected_patterns": detected_patterns,
                    "details": f"{len(detected_patterns)} error patterns detected",
                }
            else:
                return {
                    "status": "healthy",
                    "patterns_detected": 0,
                    "detected_patterns": [],
                    "details": "No critical error patterns detected",
                }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "details": f"Pattern detection failed: {type(e).__name__}",
            }

    def _check_import_error_pattern(self) -> Optional[Dict]:
        """インポートエラーパターン検出."""
        try:
            # 最近のログからインポートエラーを検索
            log_file = PROJECT_ROOT / "logs" / "operational_status.log"
            if log_file.exists():
                with open(log_file, "r", encoding="utf-8") as f:
                    recent_logs = f.readlines()[-100:]  # 最新100行

                import_errors = []
                for line in recent_logs:
                    if any(
                        pattern in line
                        for pattern in [
                            "ModuleNotFoundError",
                            "ImportError",
                            "cannot import",
                        ]
                    ):
                        import_errors.append(line.strip())

                if import_errors:
                    return {
                        "detected": True,
                        "error_count": len(import_errors),
                        "sample_errors": import_errors[:3],
                    }
        except Exception:
            pass
        return None

    def _check_ml_failure_pattern(self) -> Optional[Dict]:
        """MLモデル失敗パターン検出."""
        try:
            # MLモデルの基本動作テスト
            import numpy as np

            from src.ml.ensemble.ensemble_model import EnsembleModel

            ensemble = EnsembleModel()
            test_features = np.random.random((3, 12))

            try:
                predictions = ensemble.predict(test_features)
                probabilities = ensemble.predict_proba(test_features)

                # 予測値の異常パターンチェック
                if len(set(predictions)) == 1:  # 全て同じ予測
                    return {
                        "detected": True,
                        "anomaly_type": "static_predictions",
                        "evidence": f"All predictions identical: {predictions[0]}",
                    }

                # 確率値の異常チェック
                prob_values = probabilities[:, 1] if probabilities.shape[1] > 1 else probabilities
                if all(p < 0.1 for p in prob_values) or all(p > 0.9 for p in prob_values):
                    return {
                        "detected": True,
                        "anomaly_type": "extreme_probabilities",
                        "evidence": f"Extreme probability values: {prob_values.tolist()}",
                    }

            except Exception as prediction_error:
                return {
                    "detected": True,
                    "anomaly_type": "prediction_failure",
                    "evidence": f"Prediction failed: {str(prediction_error)[:100]}",
                }

        except Exception:
            pass
        return None

    def _check_test_degradation_pattern(self) -> Optional[Dict]:
        """テストシステム劣化パターン検出."""
        try:
            # 簡易テスト実行で失敗率確認
            cmd = [
                "python",
                "-m",
                "pytest",
                "tests/unit/",
                "--tb=no",
                "-q",
                "--maxfail=10",
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=PROJECT_ROOT,
            )

            if result.returncode != 0:
                output = result.stdout + result.stderr
                failed_match = re.search(r"(\d+) failed", output)
                failed_count = int(failed_match.group(1)) if failed_match else 0

                if failed_count >= 10:  # 10個以上の失敗
                    return {
                        "detected": True,
                        "failed_tests": failed_count,
                        "evidence": f"{failed_count} test failures detected",
                    }
        except Exception:
            pass
        return None

    def _check_config_inconsistency_pattern(self) -> Optional[Dict]:
        """設定不整合パターン検出."""
        try:
            # 重要設定ファイルの存在確認
            config_files = [
                PROJECT_ROOT / "config" / "base.yaml",
                PROJECT_ROOT / "config" / "production.yaml",
            ]

            missing_configs = []
            for config_file in config_files:
                if not config_file.exists():
                    missing_configs.append(config_file.name)

            if missing_configs:
                return {
                    "detected": True,
                    "missing_configs": missing_configs,
                    "evidence": f"Missing config files: {missing_configs}",
                }
        except Exception:
            pass
        return None

    def _check_performance_anomaly_pattern(self) -> Optional[Dict]:
        """パフォーマンス異常パターン検出."""
        try:
            # 簡易的なパフォーマンステスト
            import time

            start_time = time.time()

            # 軽量な処理時間測定
            import numpy as np
            import pandas as pd

            from src.features.technical import TechnicalIndicators

            # ダミーデータでテクニカル指標計算
            dummy_data = pd.DataFrame(
                {
                    "close": np.random.random(100),
                    "high": np.random.random(100),
                    "low": np.random.random(100),
                    "volume": np.random.random(100),
                }
            )

            tech_indicators = TechnicalIndicators()
            _ = tech_indicators.calculate_rsi(dummy_data["close"])

            processing_time = time.time() - start_time

            if processing_time > 2.0:  # 2秒以上は異常
                return {
                    "detected": True,
                    "processing_time": processing_time,
                    "evidence": f"Slow processing detected: {processing_time:.2f}s",
                }

        except Exception:
            pass
        return None

    def check_file_system_integrity(self) -> Dict[str, Any]:
        """ファイルシステム整合性確認."""
        logger.info("🔍 Checking file system integrity...")

        try:
            integrity_issues = []

            # 重要ディレクトリのサイズ確認
            important_dirs = ["src", "scripts", "models", "tests", "config"]

            for dir_name in important_dirs:
                dir_path = PROJECT_ROOT / dir_name
                if dir_path.exists():
                    file_count = len(list(dir_path.rglob("*.py")))
                    if file_count == 0:
                        integrity_issues.append(f"{dir_name}: No Python files found")
                else:
                    integrity_issues.append(f"{dir_name}: Directory missing")

            # ログディレクトリ確認
            logs_dir = PROJECT_ROOT / "logs"
            if not logs_dir.exists():
                integrity_issues.append("logs: Directory missing")

            if integrity_issues:
                return {
                    "status": "warning",
                    "integrity_issues": integrity_issues,
                    "issues_count": len(integrity_issues),
                    "details": f"{len(integrity_issues)} file system issues found",
                }

            return {
                "status": "healthy",
                "directories_checked": len(important_dirs),
                "integrity_issues": [],
                "details": "File system integrity OK",
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "details": f"File system check failed: {type(e).__name__}",
            }

    def run_phase3_hidden_issues_detection(self) -> Dict[str, Any]:
        """Phase 3: 隠れた問題検出を実行."""
        logger.info("🚀 === Phase 3: 隠れた問題検出（新システム） ===")

        phase3_results = {
            "phase_name": "隠れた問題検出",
            "weight": self.config["check_phases"]["phase3"]["weight"],
            "checks": {},
            "score": 0,
            "status": "unknown",
            "issues": [],
        }

        # 各チェック実行
        checks = {
            "critical_error_patterns": self.check_critical_error_patterns(),
            "file_system_integrity": self.check_file_system_integrity(),
        }

        phase3_results["checks"] = checks

        # Phase 3スコア計算
        check_scores = []
        for check_name, check_result in checks.items():
            status = check_result.get("status", "error")

            if status == "healthy":
                score = 100
            elif status == "info":
                score = 85
            elif status == "warning":
                score = 50
            elif status == "critical":
                score = 10
            else:  # error
                score = 0

            check_scores.append(score)

            # 重大な問題を記録
            if score < 70:
                severity = "CRITICAL" if score <= 20 else "HIGH" if score <= 50 else "MEDIUM"
                phase3_results["issues"].append(
                    {
                        "check": check_name,
                        "severity": severity,
                        "message": check_result.get(
                            "error",
                            check_result.get("details", "Unknown issue"),
                        ),
                        "score": score,
                    }
                )

        # Phase 3総合スコア
        phase3_results["score"] = sum(check_scores) / len(check_scores) if check_scores else 0

        # Phase 3ステータス判定
        if phase3_results["score"] >= 80:
            phase3_results["status"] = "healthy"
        elif phase3_results["score"] >= 60:
            phase3_results["status"] = "warning"
        else:
            phase3_results["status"] = "critical"

        logger.info(
            f"✅ Phase 3 完了: スコア {phase3_results['score']:.1f}/100 ({phase3_results['status']})"
        )

        self.results["phases"]["phase3"] = phase3_results
        return phase3_results

    # ===== Phase 4: 総合判定・レポート生成システム =====

    def calculate_overall_assessment(self) -> Dict[str, Any]:
        """総合評価計算."""
        logger.info("🔍 Calculating overall assessment...")

        try:
            phase_scores = {}
            total_score = 0
            total_weight = 0

            # 各フェーズのスコア収集
            for phase_name, phase_data in self.results["phases"].items():
                if phase_name != "phase4":
                    weight = phase_data.get("weight", 25)
                    score = phase_data.get("score", 0)
                    status = phase_data.get("status", "unknown")

                    phase_scores[phase_name] = {
                        "score": score,
                        "weight": weight,
                        "status": status,
                        "weighted_score": score * weight,
                    }

                    total_score += score * weight
                    total_weight += weight

            overall_score = total_score / total_weight if total_weight > 0 else 0

            # 総合ステータス判定
            if overall_score >= 90:
                overall_status = "excellent"
            elif overall_score >= 80:
                overall_status = "healthy"
            elif overall_score >= 60:
                overall_status = "warning"
            elif overall_score >= 40:
                overall_status = "degraded"
            else:
                overall_status = "critical"

            # グローバル結果に反映
            self.results["overall_score"] = overall_score
            self.results["overall_status"] = overall_status

            return {
                "status": "healthy",
                "overall_score": overall_score,
                "overall_status": overall_status,
                "phase_scores": phase_scores,
                "total_weight": total_weight,
                "details": f"Overall score: {overall_score:.1f}/100 ({overall_status})",
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "details": f"Assessment calculation failed: {type(e).__name__}",
            }

    def generate_recommendations(self) -> Dict[str, Any]:
        """改善提案生成."""
        logger.info("🔍 Generating recommendations...")

        try:
            recommendations = []
            urgent_actions = []

            # 全フェーズから問題を収集
            all_issues = []
            for phase_name, phase_data in self.results["phases"].items():
                if phase_name != "phase4":
                    phase_issues = phase_data.get("issues", [])
                    for issue in phase_issues:
                        issue["phase"] = phase_name
                        all_issues.append(issue)

            # 問題に応じた推奨事項生成
            for issue in all_issues:
                check = issue.get("check", "")
                severity = issue.get("severity", "")

                actions = self._generate_actions_for_issue(
                    check, severity, issue.get("message", "")
                )

                for action in actions:
                    if severity == "CRITICAL":
                        action["priority"] = "IMMEDIATE"
                        urgent_actions.append(action)
                    else:
                        action["priority"] = severity
                        recommendations.append(action)

            # 重複除去
            unique_urgent = self._deduplicate_actions(urgent_actions)
            unique_recommendations = self._deduplicate_actions(recommendations)

            return {
                "status": "healthy",
                "urgent_actions": unique_urgent,
                "recommendations": unique_recommendations,
                "total_actions": len(unique_urgent) + len(unique_recommendations),
                "details": (
                    f"{len(unique_urgent)} urgent actions, "
                    f"{len(unique_recommendations)} recommendations"
                ),
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "details": (f"Recommendation generation failed: {type(e).__name__}"),
            }

    def _generate_actions_for_issue(self, check: str, severity: str, message: str) -> List[Dict]:
        """問題に対する具体的アクション生成."""
        actions = []

        # 新システム用アクション定義  # noqa: F841
        if "import" in check or "structure" in check:
            actions.append(
                {
                    "action": "Check Python path and module imports",
                    "command": 'python -c "import sys; print(sys.path)"',
                    "category": "System",
                }
            )
        elif "ml" in check or "model" in check:
            actions.append(
                {
                    "action": "Verify ML models and retrain if necessary",
                    "command": "python scripts/management/dev_check.py ml-models",
                    "category": "ML",
                }
            )
        elif "test" in check:
            actions.append(
                {
                    "action": "Run comprehensive test suite",
                    "command": "python scripts/management/dev_check.py validate",
                    "category": "Testing",
                }
            )
        elif "config" in check:
            actions.append(
                {
                    "action": "Check configuration files",
                    "command": "python scripts/management/dev_check.py phase-check",
                    "category": "Configuration",
                }
            )
        else:
            actions.append(
                {
                    "action": f"Investigate {check} issue",
                    "command": f"Review: {message[:50]}...",
                    "category": "General",
                }
            )

        return actions

    def _deduplicate_actions(self, actions: List[Dict]) -> List[Dict]:
        """重複アクション除去."""
        seen = set()
        unique = []

        for action in actions:
            key = (action.get("action", ""), action.get("category", ""))
            if key not in seen:
                seen.add(key)
                unique.append(action)

        return unique

    def generate_summary_report(self) -> Dict[str, Any]:
        """要約レポート生成."""
        logger.info("🔍 Generating summary report...")

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # JSON要約レポート生成
            summary = {
                "execution_timestamp": self.results["timestamp"],
                "system_version": self.results["system_version"],
                "overall_score": self.results["overall_score"],
                "overall_status": self.results["overall_status"],
                "phase_summary": {},
                "total_issues": 0,
                "critical_issues": 0,
                "recommendations_count": 0,
            }

            # フェーズ要約
            total_issues = 0
            critical_issues = 0

            for phase_name, phase_data in self.results["phases"].items():
                if phase_name != "phase4":
                    phase_issues = phase_data.get("issues", [])
                    phase_critical = len(
                        [i for i in phase_issues if i.get("severity") == "CRITICAL"]
                    )

                    summary["phase_summary"][phase_name] = {
                        "score": phase_data.get("score", 0),
                        "status": phase_data.get("status", "unknown"),
                        "issues_count": len(phase_issues),
                        "critical_count": phase_critical,
                    }

                    total_issues += len(phase_issues)
                    critical_issues += phase_critical

            summary["total_issues"] = total_issues
            summary["critical_issues"] = critical_issues

            # Phase 4結果から推奨事項数取得
            phase4_data = self.results["phases"].get("phase4", {})
            recommendations_data = phase4_data.get("checks", {}).get("recommendations", {})
            urgent_count = len(recommendations_data.get("urgent_actions", []))
            rec_count = len(recommendations_data.get("recommendations", []))
            summary["recommendations_count"] = urgent_count + rec_count

            # ファイル保存
            report_path = self.report_dir / f"summary_report_{timestamp}.json"
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, ensure_ascii=False, default=str)

            return {
                "status": "healthy",
                "report_path": str(report_path),
                "summary": summary,
                "details": f"Summary report saved: {report_path}",
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "details": f"Summary report generation failed: {type(e).__name__}",
            }

    def run_phase4_overall_assessment(self) -> Dict[str, Any]:
        """Phase 4: 総合判定・レポート生成を実行."""
        logger.info("🚀 === Phase 4: 総合判定・レポート生成（新システム） ===")

        phase4_results = {
            "phase_name": "総合判定・レポート生成",
            "weight": self.config["check_phases"]["phase4"]["weight"],
            "checks": {},
            "score": 0,
            "status": "unknown",
            "issues": [],
        }

        # 各チェック実行
        checks = {
            "overall_assessment": self.calculate_overall_assessment(),
            "recommendations": self.generate_recommendations(),
            "summary_report": self.generate_summary_report(),
        }

        phase4_results["checks"] = checks

        # Phase 4スコア計算（分析品質ベース）
        check_scores = []
        for check_name, check_result in checks.items():
            status = check_result.get("status", "error")

            if status == "healthy":
                score = 100
            elif status == "warning":
                score = 70
            else:  # error
                score = 50  # 分析エラーでも部分的にスコア付与

            check_scores.append(score)

            # 分析に問題がある場合のみissuesに追加
            if score < 80:
                phase4_results["issues"].append(
                    {
                        "check": check_name,
                        "severity": "MEDIUM",
                        "message": check_result.get(
                            "error",
                            check_result.get("details", "Analysis issue"),
                        ),
                        "score": score,
                    }
                )

        # Phase 4総合スコア
        phase4_results["score"] = sum(check_scores) / len(check_scores) if check_scores else 0

        # Phase 4ステータス判定
        if phase4_results["score"] >= 90:
            phase4_results["status"] = "healthy"
        elif phase4_results["score"] >= 70:
            phase4_results["status"] = "warning"
        else:
            phase4_results["status"] = "degraded"

        logger.info(
            f"✅ Phase 4 完了: スコア {phase4_results['score']:.1f}/100 ({phase4_results['status']})"
        )

        self.results["phases"]["phase4"] = phase4_results
        return phase4_results

    # ===== メイン実行・レポート生成 =====

    def run_comprehensive_check(self, target_phases: List[str] = None) -> Dict[str, Any]:
        """包括的稼働状況確認を実行（新システム版）."""
        logger.info("🎯 === 新システム稼働状況確認開始 ===")
        logger.info(f"📅 実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S JST')}")
        logger.info(f"🎨 システム: {self.results['system_version']}")

        # Phase 1実行
        if not target_phases or "phase1" in target_phases:
            self.run_phase1_infrastructure_checks()

        # Phase 2実行
        if not target_phases or "phase2" in target_phases:
            self.run_phase2_application_checks()

        # Phase 3実行
        if not target_phases or "phase3" in target_phases:
            self.run_phase3_hidden_issues_detection()

        # Phase 4実行
        if not target_phases or "phase4" in target_phases:
            self.run_phase4_overall_assessment()

        self._generate_final_console_report()

        logger.info("🎊 === 新システム稼働状況確認完了 ===")
        return self.results

    def _generate_final_console_report(self):
        """最終コンソールレポートを生成."""
        print("\n" + "=" * 60)
        print("📊 crypto-bot 新システム稼働状況確認結果")
        print("=" * 60)
        print(f"🕐 実行時刻: {self.results['timestamp']}")
        print(f"🎨 システム: {self.results['system_version']}")
        print(f"🎯 総合スコア: {self.results['overall_score']:.1f}/100")
        print(f"🔍 総合状態: {self.results['overall_status']}")

        # 各フェーズ結果表示
        for phase_name, phase_data in self.results["phases"].items():
            phase_title = phase_data.get("phase_name", phase_name)
            score = phase_data.get("score", 0)
            status = phase_data.get("status", "unknown")

            print(f"\n📋 {phase_title}: {score:.1f}/100 ({status})")

            # 各チェック結果表示
            checks = phase_data.get("checks", {})
            for check_name, check_result in checks.items():
                check_status = check_result.get("status", "unknown")
                status_icon = (
                    "✅"
                    if check_status == "healthy"
                    else "⚠️" if check_status in ["warning", "info"] else "❌"
                )
                details = check_result.get("details", "No details")
                print(f"  {status_icon} {check_name}: {details}")

        # 問題があれば表示
        all_issues = []
        for _, phase_data in self.results["phases"].items():
            all_issues.extend(phase_data.get("issues", []))

        if all_issues:
            print(f"\n⚠️ 検出された問題 ({len(all_issues)}件):")
            for issue in all_issues[:10]:  # 最初の10件
                print(f"  🔸 [{issue['severity']}] {issue['check']}: {issue['message']}")
        else:
            print("\n✅ 重大な問題は検出されませんでした")

        # 推奨事項表示
        phase4_data = self.results["phases"].get("phase4", {})
        recommendations_data = phase4_data.get("checks", {}).get("recommendations", {})
        urgent_actions = recommendations_data.get("urgent_actions", [])

        if urgent_actions:
            print(f"\n🚨 緊急対応が必要なアクション ({len(urgent_actions)}件):")
            for action in urgent_actions[:5]:
                print(f"  ⚡ {action.get('action', 'Unknown action')}")
                print(f"     {action.get('command', '')}")

        print("=" * 60)

        # JSONレポート保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = self.report_dir / f"operational_status_{timestamp}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"📁 詳細レポート保存: {json_path}")

    # ===== BaseAnalyzer抽象メソッド実装 =====

    def run_analysis(self, target_phases: List[str] = None) -> Dict:
        """運用診断分析実行（BaseAnalyzer要求）"""
        results = self.run_comprehensive_check(target_phases)
        return {
            "timestamp": datetime.now().isoformat(),
            "analysis_type": "operational_diagnosis",
            "overall_status": results.get("overall_status", "unknown"),
            "overall_score": results.get("overall_score", 0),
            "phases_count": len(results.get("phases", {})),
            "critical_issues": len(results.get("critical_issues", [])),
            "recommendations": len(results.get("recommendations", [])),
            "results": results,
        }

    def generate_report(self, analysis_result: Dict) -> str:
        """運用診断レポート生成（BaseAnalyzer要求）"""
        results = analysis_result.get("results", {})
        return f"""
=== 本番運用診断レポート ===
実行日時: {analysis_result.get('timestamp', '')}
総合状態: {analysis_result.get('overall_status', 'unknown')}
総合スコア: {analysis_result.get('overall_score', 0)}/100
診断フェーズ数: {analysis_result.get('phases_count', 0)}
重大問題数: {analysis_result.get('critical_issues', 0)}
推奨アクション数: {analysis_result.get('recommendations', 0)}
=============================="""


def main():
    """メイン実行関数."""
    import argparse

    parser = argparse.ArgumentParser(description="crypto-bot 新システム稼働状況確認システム")
    parser.add_argument("--verbose", "-v", action="store_true", help="詳細ログ出力")
    parser.add_argument("--save-report", "-s", action="store_true", help="レポートファイル保存")
    parser.add_argument(
        "--phase",
        choices=["phase1", "phase2", "phase3", "phase4"],
        help="特定フェーズのみ実行",
    )
    parser.add_argument("--config", help="設定ファイルパス")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # システム実行
    checker = NewSystemOperationalStatusChecker(config_path=args.config)

    target_phases = [args.phase] if args.phase else None
    results = checker.run_comprehensive_check(target_phases)

    # 終了コード設定
    if results["overall_status"] == "critical":
        sys.exit(2)  # Critical issues
    elif results["overall_status"] in ["warning", "degraded"]:
        sys.exit(1)  # Warning issues
    else:
        sys.exit(0)  # Success


if __name__ == "__main__":
    main()
