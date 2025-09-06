"""
モデル管理システム - Phase 18リファクタリング

機械学習モデルのライフサイクル管理（簡素化版）。
バージョン管理、保存・読み込み、基本的な評価機能を提供。

重複機能を削除し、実用性を重視した実装。
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

import pandas as pd

from ..core.exceptions import DataProcessingError
from ..core.logger import get_logger
from .ensemble import EnsembleModel


class ModelManager:
    """
    モデル管理システム（簡素化版）

    アンサンブルモデルのバージョン管理、保存・読み込み、
    基本的な評価機能を提供。
    """

    def __init__(self, base_path: Union[str, Path] = "models"):
        """
        モデル管理システムの初期化

        Args:
            base_path: モデル保存のベースディレクトリ
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        self.metadata_file = self.base_path / "model_metadata.json"
        self.logger = get_logger()

        # メタデータの初期化
        self.metadata = self._load_metadata()

        # 現在読み込まれているモデル
        self.current_model: Optional[EnsembleModel] = None
        self.current_version: Optional[str] = None

        self.logger.info(f"✅ ModelManager initialized with base path: {self.base_path}")

    def save_model(
        self,
        model: EnsembleModel,
        version_name: Optional[str] = None,
        description: str = "",
        performance_metrics: Optional[Dict[str, float]] = None,
    ) -> str:
        """
        モデルの保存とバージョン管理

        Args:
            model: 保存するアンサンブルモデル
            version_name: バージョン名（指定しない場合は自動生成）
            description: モデルの説明
            performance_metrics: パフォーマンスメトリクス

        Returns:
            str: 保存されたバージョン名.
        """
        try:
            # バージョン名の生成
            if version_name is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                version_name = f"ensemble_v{timestamp}"

            # 保存ディレクトリの作成
            version_path = self.base_path / version_name
            version_path.mkdir(parents=True, exist_ok=True)

            # モデルの保存
            model.save(version_path)

            # メタデータの更新
            model_info = model.get_model_info()
            metadata_entry = {
                "version_name": version_name,
                "created_at": datetime.now().isoformat(),
                "description": description,
                "performance_metrics": performance_metrics or {},
                "model_info": model_info,
                "file_path": str(version_path),
            }

            self.metadata[version_name] = metadata_entry
            self._save_metadata()

            self.logger.info(f"✅ Model saved as version: {version_name}")
            return version_name

        except Exception as e:
            self.logger.error(f"Failed to save model: {e}")
            raise DataProcessingError(f"Model save failed: {e}")

    def load_model(self, version_name: str) -> EnsembleModel:
        """
        指定バージョンのモデル読み込み

        Args:
            version_name: 読み込むバージョン名

        Returns:
            EnsembleModel: 読み込んだアンサンブルモデル.
        """
        try:
            if version_name not in self.metadata:
                raise ValueError(f"Version {version_name} not found")

            version_path = Path(self.metadata[version_name]["file_path"])

            if not version_path.exists():
                raise FileNotFoundError(f"Model files not found: {version_path}")

            model = EnsembleModel.load(version_path)

            # 現在のモデルとして保存
            self.current_model = model
            self.current_version = version_name

            self.logger.info(f"✅ Model loaded: {version_name}")
            return model

        except Exception as e:
            self.logger.error(f"Failed to load model {version_name}: {e}")
            raise DataProcessingError(f"Model load failed: {e}")

    def get_latest_model(self) -> Tuple[str, EnsembleModel]:
        """
        最新バージョンのモデル取得

        Returns:
            Tuple[str, EnsembleModel]: (バージョン名, モデル).
        """
        if not self.metadata:
            raise ValueError("No models found")

        # 最新の作成日時を基準に選択
        latest_version = max(self.metadata.keys(), key=lambda v: self.metadata[v]["created_at"])

        model = self.load_model(latest_version)
        return latest_version, model

    async def predict(self, X: pd.DataFrame) -> Dict[str, Union[int, float]]:
        """
        現在読み込まれているモデルで予測実行

        Args:
            X: 特徴量データ

        Returns:
            Dict[str, Union[int, float]]: 予測結果
        """
        if self.current_model is None:
            # モデルが読み込まれていない場合は最新モデルを読み込み
            self.logger.info("モデル未読み込み - 最新モデルを読み込みます")
            try:
                self.get_latest_model()
            except Exception as e:
                self.logger.warning(f"モデル読み込み失敗: {e}")
                # フォールバック: ダミー予測を返す
                return {"prediction": 0, "confidence": 0.5, "action": "hold"}

        if self.current_model is None:
            # それでもモデルが読み込めない場合はフォールバック
            self.logger.warning("モデルが利用できません - ダミー予測を返します")
            return {"prediction": 0, "confidence": 0.5, "action": "hold"}

        try:
            # 予測実行
            predictions = self.current_model.predict(X)
            probabilities = self.current_model.predict_proba(X)

            # 結果の整形
            if len(predictions) > 0:
                prediction = int(predictions[-1])  # 最新の予測
                confidence = float(probabilities[-1].max()) if len(probabilities) > 0 else 0.5
                action = "buy" if prediction == 1 else "sell" if prediction == 0 else "hold"
            else:
                prediction = 0
                confidence = 0.5
                action = "hold"

            return {
                "prediction": prediction,
                "confidence": confidence,
                "action": action,
            }

        except Exception as e:
            self.logger.error(f"予測実行エラー: {e}")
            # エラー時はフォールバック
            return {"prediction": 0, "confidence": 0.5, "action": "hold"}

    def list_models(self) -> pd.DataFrame:
        """
        保存されているモデル一覧の取得

        Returns:
            pd.DataFrame: モデル一覧.
        """
        if not self.metadata:
            return pd.DataFrame()

        model_list = []
        for version_name, metadata in self.metadata.items():
            entry = {
                "version_name": version_name,
                "created_at": metadata["created_at"],
                "description": metadata.get("description", ""),
                "n_models": metadata.get("model_info", {}).get("n_models", 0),
                "is_fitted": metadata.get("model_info", {}).get("is_fitted", False),
                "accuracy": metadata.get("performance_metrics", {}).get("accuracy", None),
                "f1_score": metadata.get("performance_metrics", {}).get("f1_score", None),
            }
            model_list.append(entry)

        df = pd.DataFrame(model_list)
        if not df.empty:
            df = df.sort_values("created_at", ascending=False)

        return df

    def delete_model(self, version_name: str) -> bool:
        """
        指定バージョンのモデル削除

        Args:
            version_name: 削除するバージョン名

        Returns:
            bool: 削除成功フラグ
        """
        try:
            if version_name not in self.metadata:
                self.logger.warning(f"Version {version_name} not found")
                return False

            # ファイルの削除
            version_path = Path(self.metadata[version_name]["file_path"])
            if version_path.exists():
                shutil.rmtree(version_path)

            # メタデータから削除
            del self.metadata[version_name]
            self._save_metadata()

            self.logger.info(f"✅ Model deleted: {version_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to delete model {version_name}: {e}")
            return False

    def _load_metadata(self) -> Dict:
        """メタデータの読み込み."""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {}
        except Exception as e:
            self.logger.warning(f"Failed to load metadata: {e}")
            return {}

    def _save_metadata(self) -> None:
        """メタデータの保存."""
        try:
            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump(self.metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to save metadata: {e}")

    def get_storage_info(self) -> Dict[str, any]:
        """ストレージ使用量情報の取得."""
        try:
            total_size = 0
            model_count = 0

            for _version_name, metadata in self.metadata.items():
                version_path = Path(metadata["file_path"])
                if version_path.exists():
                    for file_path in version_path.rglob("*"):
                        if file_path.is_file():
                            total_size += file_path.stat().st_size
                    model_count += 1

            return {
                "total_models": len(self.metadata),
                "valid_models": model_count,
                "total_size_mb": total_size / (1024 * 1024),
                "avg_size_mb": (
                    (total_size / model_count / (1024 * 1024)) if model_count > 0 else 0
                ),
                "base_path": str(self.base_path),
            }

        except Exception as e:
            self.logger.error(f"Failed to get storage info: {e}")
            return {}

    def cleanup_old_models(self, keep_latest: int = 5) -> int:
        """古いモデルの削除."""
        if len(self.metadata) <= keep_latest:
            return 0

        # 作成日時でソート
        sorted_versions = sorted(
            self.metadata.keys(),
            key=lambda v: self.metadata[v]["created_at"],
            reverse=True,
        )

        # 古いモデルを削除
        deleted_count = 0
        for version_name in sorted_versions[keep_latest:]:
            if self.delete_model(version_name):
                deleted_count += 1

        self.logger.info(f"✅ Cleaned up {deleted_count} old models")
        return deleted_count
