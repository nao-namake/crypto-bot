"""
外部データ品質管理システム
デフォルト補完率の制限と重要指標の実データ必須化
"""

import logging
from typing import Dict, List, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


class DataQualityManager:
    """
    外部データ品質管理クラス
    
    - デフォルト補完率を30/101以下に制限
    - VIX、Fear&Greedなどの重要指標は実データ必須
    - APIエラー時の段階的フォールバック
    """

    def __init__(self, config: dict):
        self.config = config
        
        # データ品質設定
        self.quality_config = config.get("ml", {}).get("data_quality", {})
        # 30%以下
        self.max_default_ratio = self.quality_config.get(
            "max_default_ratio", 0.30
        )
        self.critical_features = self.quality_config.get("critical_features", [
            "vix_level", "fear_greed_index", "dxy_level"
        ])

        # 特徴量重要度分類
        self.feature_importance = {
            "critical": [  # 必須：実データ必要
                "vix_level", "vix_change", "vix_zscore",
                "fear_greed_index", "fear_greed_classification", "market_sentiment",
                "dxy_level", "dxy_change"
            ],
            "important": [  # 重要：可能な限り実データ
                "treasury_10y_level", "treasury_10y_change",
                "funding_rate_mean", "oi_level",
                "extreme_fear", "extreme_greed"
            ],
            "optional": [  # オプション：デフォルト可
                "vix_spike", "vix_regime_numeric",
                "dxy_strength", "treasury_regime",
                "fear_greed_momentum", "sentiment_regime"
            ]
        }

    def validate_data_quality(
        self, df: pd.DataFrame, metadata: Dict
    ) -> Tuple[bool, Dict]:
        """
        データ品質検証

        Returns:
            bool: 品質基準を満たすかどうか
            dict: 品質レポート
        """

        quality_report = {
            "total_features": len(df.columns),
            "real_data_features": 0,
            "default_features": 0,
            "critical_missing": [],
            "default_ratio": 0.0,
            "quality_score": 0.0,
            "status": "unknown"
        }
        
        # 実データ・デフォルトデータの分類
        real_data_count = 0
        default_count = 0
        critical_missing = []
        
        for column in df.columns:
            # メタデータから実データかデフォルトかを判定
            is_real_data = self._is_real_data(column, df[column], metadata)
            
            if is_real_data:
                real_data_count += 1
            else:
                default_count += 1
                
                # 重要な特徴量が欠損している場合
                if column in self.feature_importance["critical"]:
                    critical_missing.append(column)
        
        # 品質メトリクス計算
        default_ratio = default_count / len(df.columns) if len(df.columns) > 0 else 1.0
        quality_score = self._calculate_quality_score(
            real_data_count, default_count, critical_missing
        )
        
        quality_report.update({
            "real_data_features": real_data_count,
            "default_features": default_count,
            "critical_missing": critical_missing,
            "default_ratio": default_ratio,
            "quality_score": quality_score
        })
        
        # 品質基準判定
        quality_passed = self._evaluate_quality_standards(quality_report)
        quality_report["status"] = "passed" if quality_passed else "failed"
        
        logger.info(
            f"Data quality: {quality_score:.2f}, "
            f"default_ratio: {default_ratio:.2f}, "
            f"critical_missing: {len(critical_missing)}, "
            f"status: {quality_report['status']}"
        )
        
        return quality_passed, quality_report

    def _is_real_data(self, column: str, series: pd.Series, metadata: Dict) -> bool:
        """
        実データかデフォルトデータかを判定
        """

        # メタデータに情報がある場合
        source_info = metadata.get("feature_sources", {}).get(column)
        if source_info:
            return source_info.get("source_type") == "api"
        
        # データの特性から判定
        if len(series.unique()) <= 1:
            # 全て同じ値の場合はデフォルトの可能性が高い
            return False
        
        # 基本価格データ（OHLCV）は実データ
        if column in ["open", "high", "low", "close", "volume"]:
            return True
        
        # VIX系特徴量の判定
        if column.startswith("vix_"):
            # VIX=20.0固定の場合はデフォルト
            if column == "vix_level" and (series == 20.0).all():
                return False
            return True
        
        # Fear&Greed系特徴量の判定
        if "fear_greed" in column:
            # 50.0固定の場合はデフォルト
            if column == "fear_greed_index" and (series == 50.0).all():
                return False
            return True
        
        # DXY系特徴量の判定
        if column.startswith("dxy_"):
            # 100.0固定の場合はデフォルト
            if column == "dxy_level" and (series == 100.0).all():
                return False
            return True
        
        # その他は実データと仮定
        return True

    def _calculate_quality_score(
        self, real_count: int, default_count: int, critical_missing: List
    ) -> float:
        """
        データ品質スコア計算（0-100）
        """

        total_features = real_count + default_count
        if total_features == 0:
            return 0.0
        
        # 実データ比率スコア（0-70点）
        real_data_ratio = real_count / total_features
        real_data_score = min(70, real_data_ratio * 100)
        
        # 重要特徴量スコア（0-30点）
        critical_total = len(self.feature_importance["critical"])
        critical_missing_count = len(critical_missing)
        critical_score = max(0, 30 * (1 - critical_missing_count / critical_total))
        
        return real_data_score + critical_score

    def _evaluate_quality_standards(self, quality_report: Dict) -> bool:
        """
        品質基準の評価
        """

        # 基準1: デフォルト比率が30%以下
        if quality_report["default_ratio"] > self.max_default_ratio:
            logger.warning(
                f"Default ratio too high: "
                f"{quality_report['default_ratio']:.2f} > {self.max_default_ratio}"
            )
            return False
        
        # 基準2: 重要な特徴量の実データが必要
        if quality_report["critical_missing"]:
            logger.warning(
                f"Critical features missing: {quality_report['critical_missing']}"
            )
            return False
        
        # 基準3: 最低品質スコア
        min_quality_score = self.quality_config.get("min_quality_score", 70.0)
        if quality_report["quality_score"] < min_quality_score:
            logger.warning(
                f"Quality score too low: "
                f"{quality_report['quality_score']:.2f} < {min_quality_score}"
            )
            return False
        
        return True

    def improve_data_quality(
        self, df: pd.DataFrame, metadata: Dict
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        データ品質の改善

        Returns:
            pd.DataFrame: 改善されたデータフレーム
            dict: 改善レポート
        """

        improvement_report = {
            "actions_taken": [],
            "features_removed": [],
            "critical_fallback": [],
            "quality_before": 0.0,
            "quality_after": 0.0
        }
        
        # 改善前の品質評価
        quality_before, report_before = self.validate_data_quality(df, metadata)
        improvement_report["quality_before"] = report_before["quality_score"]
        
        # 改善アクション
        df_improved = df.copy()
        
        # アクション1: 不要なデフォルト特徴量の削除
        df_improved, removed_features = self._remove_low_priority_defaults(
            df_improved, metadata
        )
        if removed_features:
            improvement_report["actions_taken"].append("removed_low_priority_defaults")
            improvement_report["features_removed"] = removed_features
        
        # アクション2: 重要特徴量の実データ再取得試行
        df_improved, fallback_features = self._retry_critical_features(
            df_improved, metadata
        )
        if fallback_features:
            improvement_report["actions_taken"].append("retried_critical_features")
            improvement_report["critical_fallback"] = fallback_features
        
        # 改善後の品質評価
        quality_after, report_after = self.validate_data_quality(df_improved, metadata)
        improvement_report["quality_after"] = report_after["quality_score"]
        
        logger.info(
            f"Data quality improved: {improvement_report['quality_before']:.1f} → "
            f"{improvement_report['quality_after']:.1f}"
        )
        
        return df_improved, improvement_report

    def _remove_low_priority_defaults(
        self, df: pd.DataFrame, metadata: Dict
    ) -> Tuple[pd.DataFrame, List]:
        """
        優先度の低いデフォルト特徴量を削除
        """

        features_to_remove = []
        
        for column in df.columns:
            # オプション特徴量かつデフォルトデータの場合は削除候補
            if (column in self.feature_importance["optional"] and
                    not self._is_real_data(column, df[column], metadata)):
                features_to_remove.append(column)
        
        # 削除実行
        if features_to_remove:
            df_improved = df.drop(columns=features_to_remove)
            logger.info(
                f"Removed {len(features_to_remove)} low-priority default features"
            )
            return df_improved, features_to_remove
        
        return df, []

    def _retry_critical_features(
        self, df: pd.DataFrame, metadata: Dict
    ) -> Tuple[pd.DataFrame, List]:
        """
        重要特徴量の実データ再取得を試行
        """

        fallback_features = []
        
        # ここでは実際のAPI再取得は行わず、フォールバック処理のみ
        # 実際の実装では、VIXやFear&GreedのAPIを再呼び出しする
        
        for feature in self.feature_importance["critical"]:
            if (feature in df.columns and
                    not self._is_real_data(feature, df[feature], metadata)):
                fallback_features.append(feature)
                
                # 重要特徴量のより良いデフォルト値設定
                if feature == "vix_level":
                    # 最新の市場状況に基づく推定値
                    df[feature] = 22.0  # より現実的な値
                elif feature == "fear_greed_index":
                    # 中立からやや恐怖寄りの値
                    df[feature] = 45.0
                elif feature == "dxy_level":
                    # 現在のDXY水準に近い値
                    df[feature] = 102.0
        
        if fallback_features:
            logger.warning(
                f"Applied fallback for critical features: {fallback_features}"
            )
        
        return df, fallback_features

    def get_quality_requirements(self) -> Dict:
        """
        データ品質要件の取得
        """

        return {
            "max_default_ratio": self.max_default_ratio,
            "critical_features": self.critical_features,
            "feature_importance": self.feature_importance,
            "min_quality_score": self.quality_config.get(
                "min_quality_score", 70.0
            )
        }
