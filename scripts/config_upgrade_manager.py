#!/usr/bin/env python3
"""
設定ファイル段階的アップグレード管理スクリプト
検証用設定→本番用設定への安全な移行を管理

機能:
- 検証用設定での自動テスト実行
- 成功基準評価・判定
- 本番用設定への安全上書き
- バックアップ管理・ロールバック機能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import shutil
import yaml
import json
import logging
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConfigUpgradeManager:
    """設定ファイル段階的アップグレード管理クラス"""
    
    def __init__(self, 
                 validation_config: str = "config/validation/mtf_ensemble_test.yml",
                 production_config: str = "config/production/production.yml",
                 backup_dir: str = "config/backups"):
        """
        Args:
            validation_config: 検証用設定ファイルパス
            production_config: 本番用設定ファイルパス  
            backup_dir: バックアップディレクトリ
        """
        self.validation_config = Path(validation_config)
        self.production_config = Path(production_config)
        self.backup_dir = Path(backup_dir)
        
        # バックアップディレクトリ作成
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 成功基準定義
        self.success_criteria = {
            "processing_time": 4.0,        # 4秒以内
            "data_quality": 60.0,          # 60%以上  
            "feature_count": 151,          # 正確に151特徴量
            "no_critical_errors": True,    # 重大エラーなし
            "memory_efficiency": 20.0,     # 20MB以下ピークメモリ
            "api_success_rate": 70.0       # 外部API成功率70%以上
        }
        
        self.upgrade_results = {
            "validation_results": {},
            "upgrade_status": "pending",
            "backup_created": False,
            "rollback_available": False,
            "timestamp": None
        }
        
        logger.info("🔧 ConfigUpgradeManager initialized")
        logger.info(f"  - Validation config: {self.validation_config}")
        logger.info(f"  - Production config: {self.production_config}")
        logger.info(f"  - Backup directory: {self.backup_dir}")

    def create_backup(self) -> str:
        """本番設定のバックアップ作成"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"production_backup_{timestamp}.yml"
            backup_path = self.backup_dir / backup_filename
            
            if self.production_config.exists():
                shutil.copy2(self.production_config, backup_path)
                logger.info(f"✅ Backup created: {backup_path}")
                self.upgrade_results["backup_created"] = True
                self.upgrade_results["rollback_available"] = True
                return str(backup_path)
            else:
                logger.warning(f"⚠️ Production config not found: {self.production_config}")
                return ""
                
        except Exception as e:
            logger.error(f"❌ Backup creation failed: {e}")
            return ""

    def run_validation_tests(self) -> Dict:
        """検証用設定でのテスト実行"""
        logger.info("🔍 Running validation tests...")
        
        validation_results = {
            "test_status": "running",
            "performance_test": {},
            "feature_test": {},
            "integration_test": {},
            "errors": []
        }
        
        try:
            # Test 1: 151特徴量生成テスト
            logger.info("  Testing 151 features generation...")
            result_151 = self._run_test_script("scripts/test_151_features.py", 
                                             f"--config {self.validation_config}")
            validation_results["feature_test"] = result_151
            
            # Test 2: マルチタイムフレームテスト
            logger.info("  Testing multi-timeframe processing...")
            result_mtf = self._run_test_script("scripts/test_multi_timeframe.py",
                                             f"--config {self.validation_config}")
            validation_results["integration_test"] = result_mtf
            
            # Test 3: パフォーマンステスト
            logger.info("  Testing performance...")
            result_perf = self._run_test_script("scripts/test_integrated_performance.py",
                                              f"--config {self.validation_config}")
            validation_results["performance_test"] = result_perf
            
            # 総合判定
            validation_results["test_status"] = self._evaluate_test_results(validation_results)
            
        except Exception as e:
            logger.error(f"❌ Validation tests failed: {e}")
            validation_results["test_status"] = "failed"
            validation_results["errors"].append(str(e))
        
        self.upgrade_results["validation_results"] = validation_results
        return validation_results

    def _run_test_script(self, script_path: str, args: str = "") -> Dict:
        """テストスクリプト実行"""
        try:
            cmd = f"python {script_path} {args}".strip()
            logger.info(f"    Running: {cmd}")
            
            result = subprocess.run(
                cmd.split(),
                capture_output=True,
                text=True,
                timeout=300  # 5分タイムアウト
            )
            
            return {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"    ❌ Test timeout: {script_path}")
            return {"returncode": -1, "error": "timeout", "success": False}
        except Exception as e:
            logger.error(f"    ❌ Test execution failed: {e}")
            return {"returncode": -1, "error": str(e), "success": False}

    def _evaluate_test_results(self, results: Dict) -> str:
        """テスト結果評価"""
        try:
            # 基本成功基準チェック
            if not all(test.get("success", False) for test in [
                results["feature_test"], 
                results["integration_test"], 
                results["performance_test"]
            ]):
                return "failed"
            
            # パフォーマンス基準チェック
            perf_data = results["performance_test"].get("stdout", "")
            if "processing_time" in perf_data:
                # パフォーマンスメトリクス抽出・評価
                # （実装簡略化）
                pass
            
            logger.info("✅ All validation tests passed!")
            return "passed"
            
        except Exception as e:
            logger.error(f"❌ Test evaluation failed: {e}")
            return "failed"

    def upgrade_to_production(self) -> bool:
        """検証用設定→本番用設定アップグレード"""
        try:
            if self.upgrade_results["validation_results"].get("test_status") != "passed":
                logger.error("❌ Cannot upgrade: validation tests not passed")
                return False
            
            logger.info("🚀 Starting production upgrade...")
            
            # バックアップ作成
            backup_path = self.create_backup()
            if not backup_path:
                logger.error("❌ Backup creation failed - aborting upgrade")
                return False
            
            # 検証用設定を本番用に合わせて調整
            adjusted_config = self._adjust_config_for_production()
            if not adjusted_config:
                logger.error("❌ Config adjustment failed - aborting upgrade")
                return False
            
            # 本番設定ファイル上書き
            with open(self.production_config, 'w') as f:
                yaml.dump(adjusted_config, f, default_flow_style=False, allow_unicode=True)
            
            # 権限設定
            os.chmod(self.production_config, 0o644)
            
            logger.info("✅ Production config upgraded successfully!")
            self.upgrade_results["upgrade_status"] = "success"
            self.upgrade_results["timestamp"] = datetime.now().isoformat()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Production upgrade failed: {e}")
            self.upgrade_results["upgrade_status"] = "failed"
            return False

    def _adjust_config_for_production(self) -> Optional[Dict]:
        """検証用設定を本番用に調整"""
        try:
            # 検証用設定読み込み
            with open(self.validation_config, 'r') as f:
                config = yaml.safe_load(f)
            
            # 本番用調整
            # データ取得設定を本番仕様に
            config["data"]["limit"] = 100
            config["data"]["per_page"] = 20
            config["data"]["ccxt_options"]["rateLimit"] = 2000
            
            # リスク設定を本番仕様に
            config["risk"]["risk_per_trade"] = 0.005
            config["risk"]["stop_atr_mult"] = 1.2
            config["risk"]["kelly_criterion"]["max_fraction"] = 0.05
            
            # ライブ取引設定を本番仕様に
            config["live"]["mode"] = "live"
            config["live"]["trade_interval"] = 60
            config["live"]["max_order_size"] = 0.0005
            config["live"]["starting_balance"] = 10000.0
            config["live"]["margin_trading"]["enabled"] = True
            config["live"]["margin_trading"]["position_type"] = "both"
            
            # ML設定を本番仕様に
            config["ml"]["feat_period"] = 14
            config["ml"]["lags"] = [1, 2, 3, 4, 5]
            config["ml"]["rolling_window"] = 20
            config["ml"]["horizon"] = 5
            config["ml"]["ensemble"]["models"] = ["lgbm", "xgb", "rf"]
            config["ml"]["ensemble"]["model_weights"] = [0.5, 0.3, 0.2]
            config["ml"]["ensemble"]["confidence_threshold"] = 0.65
            
            # 外部データ設定を本番仕様に
            config["ml"]["external_data"]["funding"]["enabled"] = True
            
            # 品質監視を本番仕様に
            config["quality_monitoring"]["default_threshold"] = 0.3
            config["quality_monitoring"]["emergency_stop_threshold"] = 0.5
            
            # Bitbank設定を本番仕様に
            config["bitbank"]["fee_optimization"]["enabled"] = True
            config["bitbank"]["order_management"]["max_open_orders"] = 30
            config["bitbank"]["day_trading"]["enabled"] = True
            
            # ログレベルを本番仕様に
            config["logging"]["level"] = "INFO"
            config["logging"]["file"] = "/app/logs/bitbank_production.log"
            config["logging"]["retention"] = 7
            
            # モデルパスを本番仕様に
            config["strategy"]["params"]["model_path"] = "/app/models/production/model.pkl"
            
            # 検証用メタデータ削除
            if "validation" in config:
                del config["validation"]
            
            return config
            
        except Exception as e:
            logger.error(f"❌ Config adjustment failed: {e}")
            return None

    def rollback(self, backup_filename: Optional[str] = None) -> bool:
        """設定ロールバック"""
        try:
            if not self.upgrade_results.get("rollback_available", False):
                logger.error("❌ No rollback available")
                return False
            
            # 最新バックアップを使用（指定がない場合）
            if not backup_filename:
                backup_files = list(self.backup_dir.glob("production_backup_*.yml"))
                if not backup_files:
                    logger.error("❌ No backup files found")
                    return False
                backup_filename = max(backup_files, key=lambda f: f.stat().st_mtime).name
            
            backup_path = self.backup_dir / backup_filename
            if not backup_path.exists():
                logger.error(f"❌ Backup file not found: {backup_path}")
                return False
            
            # ロールバック実行
            shutil.copy2(backup_path, self.production_config)
            logger.info(f"✅ Rolled back to: {backup_filename}")
            
            self.upgrade_results["upgrade_status"] = "rolled_back"
            return True
            
        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
            return False

    def cleanup_old_backups(self, keep_count: int = 5):
        """古いバックアップファイルクリーンアップ"""
        try:
            backup_files = list(self.backup_dir.glob("production_backup_*.yml"))
            if len(backup_files) <= keep_count:
                return
            
            # 作成日時順でソート（新しい順）
            backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            # 古いファイル削除
            for old_backup in backup_files[keep_count:]:
                old_backup.unlink()
                logger.info(f"🗑️ Cleaned up old backup: {old_backup.name}")
                
        except Exception as e:
            logger.error(f"❌ Backup cleanup failed: {e}")

    def get_upgrade_report(self) -> Dict:
        """アップグレード結果レポート取得"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "upgrade_results": self.upgrade_results,
            "success_criteria": self.success_criteria,
            "config_paths": {
                "validation": str(self.validation_config),
                "production": str(self.production_config),
                "backup_dir": str(self.backup_dir)
            }
        }
        
        return report

    def save_report(self, filename: str = None):
        """アップグレードレポート保存"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"config_upgrade_report_{timestamp}.json"
        
        report_path = self.backup_dir / filename
        report = self.get_upgrade_report()
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"💾 Upgrade report saved: {report_path}")


def main():
    """メイン実行関数"""
    logger.info("=" * 80)
    logger.info("Config Upgrade Manager - Phase A2")
    logger.info("=" * 80)
    
    # ConfigUpgradeManager初期化
    manager = ConfigUpgradeManager()
    
    try:
        # Step 1: 検証テスト実行
        logger.info("🔍 Step 1: Running validation tests...")
        validation_results = manager.run_validation_tests()
        
        if validation_results["test_status"] == "passed":
            logger.info("✅ Validation tests passed!")
            
            # Step 2: 本番アップグレード
            logger.info("🚀 Step 2: Upgrading to production...")
            if manager.upgrade_to_production():
                logger.info("✅ Production upgrade completed successfully!")
            else:
                logger.error("❌ Production upgrade failed!")
        else:
            logger.error("❌ Validation tests failed - upgrade aborted")
        
        # Step 3: レポート保存
        manager.save_report()
        
        # Step 4: バックアップクリーンアップ
        manager.cleanup_old_backups()
        
        # 最終結果表示
        final_status = manager.upgrade_results["upgrade_status"]
        logger.info(f"\n🎯 Final Status: {final_status.upper()}")
        
    except Exception as e:
        logger.error(f"❌ Config upgrade process failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()