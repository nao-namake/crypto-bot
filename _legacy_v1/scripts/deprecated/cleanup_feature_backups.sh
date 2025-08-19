#!/bin/bash
# Phase H.29.9: feature_order.json バックアップ清理スクリプト（backups/feature_order/対応）

echo "🧹 Phase H.29.9: Cleaning up feature_order.json backups"

# バックアップディレクトリ作成
mkdir -p backups/feature_order

# 直下の古いバックアップファイルを移動
if ls feature_order_backup_*.json 1> /dev/null 2>&1; then
    echo "📦 Moving root backups to backups/feature_order/..."
    mv feature_order_backup_*.json backups/feature_order/
fi

# config/core/の古いバックアップファイルも移動
if ls config/core/feature_order_backup_*.json 1> /dev/null 2>&1; then
    echo "📦 Moving config/core backups to backups/feature_order/..."
    mv config/core/feature_order_backup_*.json backups/feature_order/
fi

# backups/feature_order/内のバックアップ数を確認
BACKUP_DIR="backups/feature_order"
BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/feature_order_backup_*.json 2>/dev/null | wc -l)
echo "📊 Current backups in $BACKUP_DIR: $BACKUP_COUNT files"

if [ "$BACKUP_COUNT" -gt 3 ]; then
    echo "🗑️ Removing old backups (keeping latest 3)..."
    cd "$BACKUP_DIR"
    ls -1t feature_order_backup_*.json | tail -n +4 | xargs rm -f
    cd - > /dev/null
    NEW_COUNT=$(ls -1 "$BACKUP_DIR"/feature_order_backup_*.json 2>/dev/null | wc -l)
    echo "✅ Cleanup complete: $NEW_COUNT files remaining"
else
    echo "✅ No cleanup needed (≤3 backups)"
fi

# 残存ファイル表示
echo "📋 Remaining backups in $BACKUP_DIR:"
ls -la "$BACKUP_DIR"/feature_order_backup_*.json 2>/dev/null || echo "  (none)"