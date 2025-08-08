#!/usr/bin/env python3
"""
最小限の初期データキャッシュを作成（デプロイ用）
実際のデータ取得は本番環境で行う
"""

import json
import pickle
from datetime import datetime
from pathlib import Path

import pandas as pd


def create_minimal_cache():
    """最小限のダミーキャッシュを作成"""
    # cacheディレクトリ作成
    cache_dir = Path("cache")
    cache_dir.mkdir(exist_ok=True)
    
    # 空のDataFrameを作成（構造だけ）
    data = pd.DataFrame()
    
    # メタデータ
    metadata = {
        "created_at": datetime.now().isoformat(),
        "data_shape": (0, 0),
        "features_shape": (0, 0),
        "symbol": "BTC/JPY",
        "timeframe": "1h",
        "records": 0,
        "note": "Minimal cache for deployment - actual data will be fetched in production"
    }
    
    # キャッシュファイルを保存
    cache_path = cache_dir / "initial_data.pkl"
    with open(cache_path, "wb") as f:
        pickle.dump({"data": data, "metadata": metadata}, f)
    print(f"✅ Created minimal cache at {cache_path}")
    
    # メタデータをJSON形式でも保存
    metadata_path = cache_dir / "initial_data_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2, default=str)
    print(f"✅ Created metadata at {metadata_path}")
    
    print("📦 Minimal cache files created for deployment")


if __name__ == "__main__":
    create_minimal_cache()