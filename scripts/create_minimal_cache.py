#!/usr/bin/env python3
"""
最小限の初期データキャッシュを作成（デプロイ用）
API認証情報が利用できない場合やCI環境でのフォールバック用
"""

import json
import pickle
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


def create_minimal_cache():
    """最小限のダミーキャッシュを作成（CI/デプロイ用）"""
    # cacheディレクトリ作成
    cache_dir = Path("cache")
    cache_dir.mkdir(exist_ok=True)
    
    # CI環境用の最小限データを作成（72時間分）
    current_time = pd.Timestamp.now(tz="UTC")
    timestamps = pd.date_range(
        end=current_time,
        periods=72,  # 72時間分（1時間足）
        freq="1H",
        tz="UTC"
    )
    
    # リアリスティックなBTC/JPY価格データを生成
    base_price = 5_000_000  # 500万円
    np.random.seed(42)  # 再現性のためのシード
    
    # ランダムウォークで価格変動を生成
    returns = np.random.normal(0, 0.005, len(timestamps))
    price_series = base_price * np.exp(np.cumsum(returns))
    
    # OHLCVデータを生成
    data = pd.DataFrame({
        "open": price_series * (1 + np.random.uniform(-0.001, 0.001, len(timestamps))),
        "high": price_series * (1 + np.random.uniform(0, 0.01, len(timestamps))),
        "low": price_series * (1 - np.random.uniform(0, 0.01, len(timestamps))),
        "close": price_series,
        "volume": np.random.uniform(100, 1000, len(timestamps))
    }, index=timestamps)
    
    # データの整合性を確保
    data["high"] = data[["open", "high", "close"]].max(axis=1)
    data["low"] = data[["open", "low", "close"]].min(axis=1)
    
    print(f"✅ Created {len(data)} records of minimal data")
    print(f"📈 Price range: {data['close'].min():.0f} - {data['close'].max():.0f} JPY")
    
    # メタデータ
    metadata = {
        "created_at": datetime.now().isoformat(),
        "data_shape": data.shape,
        "symbol": "BTC/JPY",
        "timeframe": "1h",
        "records": len(data),
        "type": "minimal",
        "environment": "CI/Fallback",
        "note": "Minimal cache for CI/deployment - actual data will be fetched in production"
    }
    
    # キャッシュファイルを保存
    cache_path = cache_dir / "initial_data.pkl"
    with open(cache_path, "wb") as f:
        pickle.dump({"data": data, "metadata": metadata}, f)
    print(f"💾 Saved minimal cache to {cache_path}")
    
    # メタデータをJSON形式でも保存
    metadata_path = cache_dir / "initial_data_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2, default=str)
    print(f"📝 Saved metadata to {metadata_path}")
    
    print("📦 Minimal cache files created for deployment")
    return data


if __name__ == "__main__":
    create_minimal_cache()