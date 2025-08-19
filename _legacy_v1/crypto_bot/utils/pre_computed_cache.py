"""
Phase 12.3: ローカル事前計算キャッシュシステム
14時間ゼロトレード問題の根本解決のため、重い計算をローカルで事前実行
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

import pandas as pd

logger = logging.getLogger(__name__)


class PreComputedCache:
    """事前計算データのキャッシュ管理"""

    def __init__(self, cache_dir: str = "cache"):
        """
        Args:
            cache_dir: キャッシュディレクトリパス
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

        # キャッシュファイルパス
        self.market_data_path = self.cache_dir / "market_data_cache.pkl"
        self.features_path = self.cache_dir / "features_97_cache.pkl"
        self.technical_path = self.cache_dir / "technical_cache.json"
        self.metadata_path = self.cache_dir / "cache_metadata.json"

    def has_valid_cache(self, max_age_hours: int = 24) -> bool:
        """有効なキャッシュが存在するかチェック"""
        if not self.metadata_path.exists():
            return False

        try:
            with open(self.metadata_path, "r") as f:
                metadata = json.load(f)

            created_at = datetime.fromisoformat(metadata["created_at"])
            age = datetime.now() - created_at

            if age > timedelta(hours=max_age_hours):
                logger.info(
                    f"⏰ Cache is too old: {age.total_seconds()/3600:.1f} hours"
                )
                return False

            # 必要なファイルが全て存在するかチェック
            required_files = [
                self.market_data_path,
                self.features_path,
                self.technical_path,
            ]

            for file_path in required_files:
                if not file_path.exists():
                    logger.warning(f"❌ Missing cache file: {file_path}")
                    return False

            return True

        except Exception as e:
            logger.error(f"❌ Cache validation error: {e}")
            return False

    def save_market_data(self, data: pd.DataFrame) -> None:
        """市場データを保存"""
        try:
            data.to_pickle(self.market_data_path)
            logger.info(f"✅ Saved market data: {len(data)} records")
        except Exception as e:
            logger.error(f"❌ Failed to save market data: {e}")

    def save_features(self, features: pd.DataFrame) -> None:
        """97特徴量データを保存"""
        try:
            features.to_pickle(self.features_path)
            logger.info(f"✅ Saved features: shape={features.shape}")
        except Exception as e:
            logger.error(f"❌ Failed to save features: {e}")

    def save_technical(self, technical: Dict[str, Any]) -> None:
        """テクニカル指標を保存"""
        try:
            # numpy/pandas型をシリアライズ可能な形式に変換
            serializable = {}
            for key, value in technical.items():
                if hasattr(value, "tolist"):
                    serializable[key] = value.tolist()
                elif isinstance(value, pd.Series):
                    serializable[key] = value.to_list()
                else:
                    serializable[key] = value

            with open(self.technical_path, "w") as f:
                json.dump(serializable, f, indent=2)
            logger.info(f"✅ Saved technical indicators: {list(technical.keys())}")
        except Exception as e:
            logger.error(f"❌ Failed to save technical indicators: {e}")

    def save_metadata(self) -> None:
        """メタデータを保存"""
        metadata = {
            "created_at": datetime.now().isoformat(),
            "version": "1.0",
            "phase": "12.3",
        }

        try:
            with open(self.metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
            logger.info("✅ Saved cache metadata")
        except Exception as e:
            logger.error(f"❌ Failed to save metadata: {e}")

    def load_all(self) -> Dict[str, Any]:
        """全てのキャッシュデータを読み込み"""
        result = {}

        try:
            # 市場データ
            if self.market_data_path.exists():
                result["market_data"] = pd.read_pickle(self.market_data_path)
                logger.info(
                    f"✅ Loaded market data: {len(result['market_data'])} records"
                )

            # 特徴量
            if self.features_path.exists():
                result["features"] = pd.read_pickle(self.features_path)
                logger.info(f"✅ Loaded features: shape={result['features'].shape}")

            # テクニカル指標
            if self.technical_path.exists():
                with open(self.technical_path, "r") as f:
                    result["technical"] = json.load(f)
                logger.info(f"✅ Loaded technical: {list(result['technical'].keys())}")

        except Exception as e:
            logger.error(f"❌ Failed to load cache: {e}")

        return result

    def clear_cache(self) -> None:
        """キャッシュをクリア"""
        cache_files = [
            self.market_data_path,
            self.features_path,
            self.technical_path,
            self.metadata_path,
        ]

        for file_path in cache_files:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"🗑️ Deleted: {file_path}")
