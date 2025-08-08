#!/bin/bash
# CI環境用の最小限キャッシュディレクトリ作成スクリプト
# Phase 18: エントリーシグナル正常化対応

set -e

echo "🔧 Creating minimal cache directory for CI environment..."

# cache/ディレクトリ作成
mkdir -p cache

# 最小限のメタデータファイル作成
cat > cache/initial_data_metadata.json << EOF
{
  "generated": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "environment": "CI",
  "records": 0,
  "features": 0,
  "note": "Empty cache for CI build"
}
EOF

# 空のpickleファイル作成（Pythonで空のDataFrameを保存）
python3 -c "
import pandas as pd
import pickle

# 空のDataFrame作成
df = pd.DataFrame()

# pickleファイルとして保存
with open('cache/initial_data.pkl', 'wb') as f:
    pickle.dump(df, f)

print('✅ Created empty cache/initial_data.pkl')
"

echo "✅ CI cache directory created successfully"
ls -la cache/