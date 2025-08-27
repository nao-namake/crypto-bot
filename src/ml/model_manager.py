"""
モデル管理システム - Phase 12実装・CI/CD統合・手動実行監視・段階的デプロイ対応

機械学習モデルのライフサイクル管理。
バージョン管理、パフォーマンス記録、A/Bテスト機能を提供。

シンプルで実用的な実装を重視。.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd

from ..core.exceptions import DataProcessingError
from ..core.logger import get_logger
from .ensemble.ensemble_model import EnsembleModel


class ModelManager:
    """
    モデル管理システム

    アンサンブルモデルのバージョン管理、保存・読み込み、
    パフォーマンス追跡、A/Bテスト機能を統合管理。.
    """

    def __init__(self, base_path: Union[str, Path] = "models"):
        """
        モデル管理システムの初期化

        Args:
            base_path: モデル保存のベースディレクトリ.
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        self.metadata_file = self.base_path / "model_metadata.json"
        self.logger = get_logger()

        # メタデータの初期化
        self.metadata = self._load_metadata()

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
            bool: 削除成功フラグ.
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

    def compare_models(self, version_names: List[str], metrics: List[str] = None) -> pd.DataFrame:
        """
        複数モデルの性能比較

        Args:
            version_names: 比較するバージョン名リスト
            metrics: 比較するメトリクス名リスト

        Returns:
            pd.DataFrame: 比較結果.
        """
        if metrics is None:
            metrics = ["accuracy", "precision", "recall", "f1_score"]

        comparison_data = []

        for version_name in version_names:
            if version_name not in self.metadata:
                self.logger.warning(f"Version {version_name} not found, skipping")
                continue

            entry = {"version_name": version_name}
            performance = self.metadata[version_name].get("performance_metrics", {})

            for metric in metrics:
                entry[metric] = performance.get(metric, None)

            # 追加情報
            model_info = self.metadata[version_name].get("model_info", {})
            entry["created_at"] = self.metadata[version_name]["created_at"]
            entry["n_models"] = model_info.get("n_models", 0)
            entry["confidence_threshold"] = model_info.get("confidence_threshold", 0)

            comparison_data.append(entry)

        return pd.DataFrame(comparison_data)

    def run_ab_test(
        self,
        model_a_version: str,
        model_b_version: str,
        test_data: pd.DataFrame,
        test_labels: pd.Series,
        test_name: str = "",
    ) -> Dict[str, any]:
        """
        A/Bテストの実行

        Args:
            model_a_version: モデルAのバージョン名
            model_b_version: モデルBのバージョン名
            test_data: テストデータ
            test_labels: テストラベル
            test_name: テスト名

        Returns:
            Dict[str, any]: A/Bテスト結果.
        """
        try:
            # モデルの読み込み
            model_a = self.load_model(model_a_version)
            model_b = self.load_model(model_b_version)

            # 評価の実行
            metrics_a = model_a.evaluate(test_data, test_labels)
            metrics_b = model_b.evaluate(test_data, test_labels)

            # 結果の比較
            comparison = {}
            for metric in metrics_a.keys():
                if metric in metrics_b:
                    diff = metrics_b[metric] - metrics_a[metric]
                    improvement = (diff / metrics_a[metric] * 100) if metrics_a[metric] != 0 else 0
                    comparison[metric] = {
                        "model_a": metrics_a[metric],
                        "model_b": metrics_b[metric],
                        "difference": diff,
                        "improvement_pct": improvement,
                    }

            # テスト結果の記録
            test_result = {
                "test_name": test_name or f"AB_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "conducted_at": datetime.now().isoformat(),
                "model_a_version": model_a_version,
                "model_b_version": model_b_version,
                "test_samples": len(test_data),
                "metrics_comparison": comparison,
                "winner": self._determine_winner(comparison),
            }

            # テスト履歴の保存
            self._save_ab_test_result(test_result)

            self.logger.info(f"✅ A/B test completed: {model_a_version} vs {model_b_version}")
            return test_result

        except Exception as e:
            self.logger.error(f"A/B test failed: {e}")
            raise DataProcessingError(f"A/B test failed: {e}")

    def _determine_winner(self, comparison: Dict[str, Dict]) -> str:
        """A/Bテストの勝者決定."""
        # 主要メトリクスでの勝利数をカウント
        key_metrics = ["accuracy", "f1_score", "precision", "recall"]
        a_wins = 0
        b_wins = 0

        for metric in key_metrics:
            if metric in comparison:
                if comparison[metric]["difference"] > 0:
                    b_wins += 1
                elif comparison[metric]["difference"] < 0:
                    a_wins += 1

        if b_wins > a_wins:
            return "model_b"
        elif a_wins > b_wins:
            return "model_a"
        else:
            return "tie"

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

    def _save_ab_test_result(self, test_result: Dict) -> None:
        """A/Bテスト結果の保存."""
        try:
            ab_test_file = self.base_path / "ab_test_history.json"

            # 既存履歴の読み込み
            if ab_test_file.exists():
                with open(ab_test_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            else:
                history = []

            # 新しい結果を追加
            history.append(test_result)

            # 履歴の保存（最新50件のみ保持）
            history = history[-50:]
            with open(ab_test_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)

        except Exception as e:
            self.logger.error(f"Failed to save A/B test result: {e}")

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
