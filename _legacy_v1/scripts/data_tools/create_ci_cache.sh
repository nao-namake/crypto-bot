#!/bin/bash
# =============================================================================
# CI環境用の軽量キャッシュ作成スクリプト
# Python依存関係なしで動作し、Terraformデプロイに必要な最小限のキャッシュを作成
# =============================================================================

set -e

echo "🔧 Creating CI cache directory..."
mkdir -p cache

# メタデータファイルを作成
echo '{"generated": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'", "environment": "CI", "records": 300}' > cache/initial_data_metadata.json

# ダミーのキャッシュファイルを作成（Terraformデプロイでは実際には不要だが、警告を防ぐため）
touch cache/initial_data.pkl
touch cache/initial_features.pkl

# キャッシュ情報をJSONで作成
cat > cache/cache_info.json << EOF
{
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "environment": "CI",
  "type": "minimal",
  "description": "CI environment cache placeholder",
  "python_required": false
}
EOF

echo "✅ CI cache directory created successfully"
ls -la cache/

# 成功を返す
exit 0