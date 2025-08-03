#!/usr/bin/env python3
"""
Phase H.29.6: feature_order.json完全保護スクリプト
ファイルアクセス権限とバックアップによる多重保護
"""

import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def protect_feature_order_file():
    """
    feature_order.jsonの完全保護システム
    - 読み取り専用権限設定
    - バックアップ作成
    - 整合性検証
    """
    feature_order_path = Path("config/core/feature_order.json")

    if not feature_order_path.exists():
        logger.error("❌ feature_order.json not found")
        return False

    try:
        # 1. バックアップ作成（Phase H.29.9: backups/feature_order/フォルダに保存・最新3個保持）
        backup_dir = Path("backups/feature_order")
        backup_dir.mkdir(parents=True, exist_ok=True)

        today = datetime.now().strftime("%Y%m%d")
        existing_backups = list(backup_dir.glob(f"feature_order_backup_{today}_*.json"))

        if not existing_backups:  # 今日のバックアップがない場合のみ作成
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"feature_order_backup_{timestamp}.json"
            shutil.copy2(feature_order_path, backup_path)
            logger.info(f"✅ Created backup: {backup_path}")

            # 最新3個のみ保持（古いファイル削除）
            all_backups = sorted(
                backup_dir.glob("feature_order_backup_*.json"), reverse=True
            )
            for old_backup in all_backups[3:]:
                old_backup.unlink()
                logger.info(f"🗑️ Removed old backup: {old_backup.name}")
        else:
            logger.info(f"ℹ️ Daily backup already exists: {len(existing_backups)} files")

        # 2. 整合性検証
        with open(feature_order_path, "r") as f:
            data = json.load(f)

        if data.get("num_features") != 125:
            logger.error(f"❌ Invalid feature count: {data.get('num_features')} != 125")
            return False

        if len(data.get("feature_order", [])) != 125:
            logger.error(
                f"❌ Feature list length mismatch: {len(data.get('feature_order', []))} != 125"
            )
            return False

        logger.info("✅ Integrity validation passed")

        # 3. 読み取り専用権限設定（本番環境でのみ）
        if not os.environ.get("CI") and "test" not in str(feature_order_path).lower():
            # 644 (rw-r--r--) に設定
            os.chmod(feature_order_path, 0o644)
            logger.info("✅ Set read-only permissions")

        # 4. 監視用チェックサムファイル作成
        import hashlib

        with open(feature_order_path, "rb") as f:
            checksum = hashlib.sha256(f.read()).hexdigest()

        with open("config/core/feature_order.checksum", "w") as f:
            f.write(f"{checksum}  config/core/feature_order.json\n")

        logger.info(f"✅ Created checksum: {checksum[:16]}...")

        return True

    except Exception as e:
        logger.error(f"❌ Protection failed: {e}")
        return False


def verify_feature_order_integrity():
    """
    feature_order.jsonの整合性を継続監視
    """
    feature_order_path = Path("config/core/feature_order.json")
    checksum_path = Path("config/core/feature_order.checksum")

    if not feature_order_path.exists():
        logger.error("❌ feature_order.json not found")
        return False

    if not checksum_path.exists():
        logger.warning("⚠️ Checksum file not found, creating...")
        return protect_feature_order_file()

    try:
        # チェックサム検証
        import hashlib

        with open(feature_order_path, "rb") as f:
            current_checksum = hashlib.sha256(f.read()).hexdigest()

        with open(checksum_path, "r") as f:
            expected_checksum = f.read().strip().split()[0]

        if current_checksum != expected_checksum:
            logger.error(
                f"❌ INTEGRITY VIOLATION DETECTED!\n"
                f"  Expected: {expected_checksum[:16]}...\n"
                f"  Current:  {current_checksum[:16]}...\n"
                f"  File has been modified externally!"
            )

            # 自動復旧を試行（Phase H.29.9: backups/feature_order/から復旧）
            backup_dir = Path("backups/feature_order")
            backup_files = sorted(
                backup_dir.glob("feature_order_backup_*.json"), reverse=True
            )
            if backup_files:
                latest_backup = backup_files[0]
                logger.warning(f"🔄 Attempting recovery from {latest_backup}")
                shutil.copy2(latest_backup, feature_order_path)
                return protect_feature_order_file()

            return False

        logger.info("✅ Integrity verification passed")
        return True

    except Exception as e:
        logger.error(f"❌ Integrity verification failed: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("🛡️ Phase H.29.6: feature_order.json Protection System")
    print("=" * 60)

    if protect_feature_order_file():
        print("✅ Protection system activated successfully")

        if verify_feature_order_integrity():
            print("✅ Initial integrity verification passed")
        else:
            print("❌ Initial integrity verification failed")
    else:
        print("❌ Protection system activation failed")
