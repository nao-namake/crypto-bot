#!/usr/bin/env python3
"""
アンサンブル学習統計的検証システム
高度な統計手法による予測精度・取引パフォーマンスの科学的検証
"""

import json
import logging
import os
import sys
import warnings
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import yaml
from scipy import stats
from scipy.stats import levene, mannwhitneyu, normaltest, wilcoxon
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import bootstrap_sample

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 警告フィルタ
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class StatisticalTest:
    """統計検定結果"""

    test_name: str
    test_type: str
    statistic: float
    p_value: float
    effect_size: float
    confidence_interval: Tuple[float, float]
    degrees_of_freedom: Optional[int]
    assumptions_met: Dict[str, bool]
    interpretation: str
    recommendation: str


@dataclass
class BootstrapResult:
    """ブートストラップ結果"""

    metric_name: str
    original_difference: float
    bootstrap_mean: float
    bootstrap_std: float
    confidence_interval: Tuple[float, float]
    p_value: float
    bootstrap_samples: np.ndarray
    significance_level: float


@dataclass
class PowerAnalysis:
    """検定力分析結果"""

    effect_size: float
    sample_size: int
    alpha: float
    power: float
    minimum_detectable_effect: float
    required_sample_size: int
    interpretation: str


@dataclass
class BayesianAnalysis:
    """ベイズ分析結果"""

    prior_mean: float
    prior_std: float
    likelihood_mean: float
    likelihood_std: float
    posterior_mean: float
    posterior_std: float
    credible_interval: Tuple[float, float]
    bayes_factor: float
    interpretation: str


class EnsembleStatisticalVerification:
    """アンサンブル学習統計的検証システム"""

    def __init__(self, config_path: str = None):
        """
        統計的検証システム初期化

        Parameters:
        -----------
        config_path : str
            設定ファイルパス
        """
        self.config = self._load_config(config_path)
        self.test_results = {}
        self.bootstrap_results = {}
        self.power_analyses = {}
        self.bayesian_analyses = {}

        # 結果保存ディレクトリ
        self.output_dir = Path(project_root / "results" / "statistical_verification")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 統計設定
        self.significance_level = self.config.get("statistics", {}).get(
            "significance_level", 0.05
        )
        self.confidence_level = self.config.get("statistics", {}).get(
            "confidence_level", 0.95
        )
        self.bootstrap_iterations = self.config.get("statistics", {}).get(
            "bootstrap_iterations", 10000
        )
        self.effect_size_thresholds = self.config.get("statistics", {}).get(
            "effect_size_thresholds", {"small": 0.2, "medium": 0.5, "large": 0.8}
        )

        logger.info("Statistical Verification System initialized")

    def _load_config(self, config_path: str = None) -> Dict:
        """設定ファイル読み込み"""
        if config_path is None:
            config_path = (
                project_root / "config" / "validation" / "ensemble_trading.yml"
            )

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            logger.info(f"Config loaded from: {config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict:
        """デフォルト設定"""
        return {
            "statistics": {
                "significance_level": 0.05,
                "confidence_level": 0.95,
                "bootstrap_iterations": 10000,
                "effect_size_thresholds": {"small": 0.2, "medium": 0.5, "large": 0.8},
                "minimum_sample_size": 30,
                "power_threshold": 0.8,
            },
            "tests": {
                "parametric": ["t_test", "welch_t_test", "paired_t_test"],
                "non_parametric": ["mann_whitney_u", "wilcoxon", "kruskal_wallis"],
                "bootstrap": [
                    "basic_bootstrap",
                    "percentile_bootstrap",
                    "bias_corrected_bootstrap",
                ],
                "bayesian": ["bayesian_t_test", "bayesian_proportion_test"],
            },
            "visualization": {
                "create_plots": True,
                "plot_format": "png",
                "figure_size": [12, 8],
                "dpi": 300,
            },
        }

    def run_comprehensive_verification(
        self,
        traditional_data: Union[Dict, List],
        ensemble_data: Union[Dict, List],
        metrics: List[str] = None,
    ) -> Dict[str, Any]:
        """
        包括的統計的検証実行

        Parameters:
        -----------
        traditional_data : Union[Dict, List]
            従来手法のデータ
        ensemble_data : Union[Dict, List]
            アンサンブル手法のデータ
        metrics : List[str]
            検証対象メトリクス

        Returns:
        --------
        Dict[str, Any]
            検証結果
        """
        logger.info("Starting comprehensive statistical verification...")

        if metrics is None:
            metrics = [
                "accuracy",
                "precision",
                "recall",
                "f1_score",
                "total_return",
                "sharpe_ratio",
                "win_rate",
            ]

        verification_results = {}

        for metric in metrics:
            logger.info(f"Verifying metric: {metric}")

            # データ抽出
            trad_values = self._extract_metric_values(traditional_data, metric)
            ens_values = self._extract_metric_values(ensemble_data, metric)

            if len(trad_values) == 0 or len(ens_values) == 0:
                logger.warning(f"Insufficient data for metric: {metric}")
                continue

            # 各種統計検定
            metric_results = {
                "descriptive_stats": self._calculate_descriptive_statistics(
                    trad_values, ens_values
                ),
                "normality_tests": self._test_normality(trad_values, ens_values),
                "parametric_tests": self._run_parametric_tests(trad_values, ens_values),
                "non_parametric_tests": self._run_non_parametric_tests(
                    trad_values, ens_values
                ),
                "bootstrap_tests": self._run_bootstrap_tests(
                    trad_values, ens_values, metric
                ),
                "effect_size_analysis": self._calculate_effect_sizes(
                    trad_values, ens_values
                ),
                "power_analysis": self._run_power_analysis(trad_values, ens_values),
                "bayesian_analysis": self._run_bayesian_analysis(
                    trad_values, ens_values, metric
                ),
            }

            verification_results[metric] = metric_results

        # 総合評価
        comprehensive_assessment = self._generate_comprehensive_assessment(
            verification_results
        )

        # 最終結果
        final_results = {
            "verification_results": verification_results,
            "comprehensive_assessment": comprehensive_assessment,
            "metadata": {
                "verification_date": datetime.now().isoformat(),
                "metrics_tested": metrics,
                "significance_level": self.significance_level,
                "confidence_level": self.confidence_level,
                "bootstrap_iterations": self.bootstrap_iterations,
            },
        }

        return final_results

    def _extract_metric_values(
        self, data: Union[Dict, List], metric: str
    ) -> np.ndarray:
        """メトリクス値抽出"""
        if isinstance(data, dict):
            if metric in data:
                value = data[metric]
                return np.array(
                    [value] if not isinstance(value, (list, np.ndarray)) else value
                )
            else:
                return np.array([])
        elif isinstance(data, list):
            values = []
            for item in data:
                if isinstance(item, dict) and metric in item:
                    values.append(item[metric])
                elif hasattr(item, metric):
                    values.append(getattr(item, metric))
            return np.array(values)
        else:
            return np.array([])

    def _calculate_descriptive_statistics(
        self, trad_values: np.ndarray, ens_values: np.ndarray
    ) -> Dict[str, Any]:
        """記述統計計算"""
        stats_dict = {
            "traditional": {
                "mean": np.mean(trad_values),
                "std": np.std(trad_values, ddof=1),
                "median": np.median(trad_values),
                "min": np.min(trad_values),
                "max": np.max(trad_values),
                "q25": np.percentile(trad_values, 25),
                "q75": np.percentile(trad_values, 75),
                "skewness": stats.skew(trad_values),
                "kurtosis": stats.kurtosis(trad_values),
                "sample_size": len(trad_values),
            },
            "ensemble": {
                "mean": np.mean(ens_values),
                "std": np.std(ens_values, ddof=1),
                "median": np.median(ens_values),
                "min": np.min(ens_values),
                "max": np.max(ens_values),
                "q25": np.percentile(ens_values, 25),
                "q75": np.percentile(ens_values, 75),
                "skewness": stats.skew(ens_values),
                "kurtosis": stats.kurtosis(ens_values),
                "sample_size": len(ens_values),
            },
            "difference": {
                "mean_diff": np.mean(ens_values) - np.mean(trad_values),
                "median_diff": np.median(ens_values) - np.median(trad_values),
                "std_diff": np.std(ens_values, ddof=1) - np.std(trad_values, ddof=1),
                "improvement_pct": (
                    (
                        (np.mean(ens_values) - np.mean(trad_values))
                        / abs(np.mean(trad_values))
                    )
                    * 100
                    if np.mean(trad_values) != 0
                    else 0
                ),
            },
        }

        return stats_dict

    def _test_normality(
        self, trad_values: np.ndarray, ens_values: np.ndarray
    ) -> Dict[str, Any]:
        """正規性検定"""
        normality_results = {}

        for name, values in [("traditional", trad_values), ("ensemble", ens_values)]:
            if len(values) < 8:  # 最小サンプルサイズ
                normality_results[name] = {
                    "shapiro_wilk": {
                        "statistic": None,
                        "p_value": None,
                        "is_normal": None,
                    },
                    "anderson_darling": {
                        "statistic": None,
                        "p_value": None,
                        "is_normal": None,
                    },
                    "overall_assessment": "insufficient_data",
                }
                continue

            # Shapiro-Wilk検定
            try:
                shapiro_stat, shapiro_p = stats.shapiro(values)
                shapiro_normal = shapiro_p > self.significance_level
            except Exception:
                shapiro_stat, shapiro_p, shapiro_normal = None, None, None

            # Anderson-Darling検定
            try:
                ad_result = stats.anderson(values, dist="norm")
                ad_stat = ad_result.statistic
                ad_critical = ad_result.critical_values[2]  # 5%水準
                ad_normal = ad_stat < ad_critical
                ad_p = None  # Anderson-Darling検定はp値を直接提供しない
            except Exception:
                ad_stat, ad_p, ad_normal = None, None, None

            # 総合評価
            if shapiro_normal is not None and ad_normal is not None:
                overall_normal = shapiro_normal and ad_normal
                overall_assessment = "normal" if overall_normal else "non_normal"
            elif shapiro_normal is not None:
                overall_assessment = "normal" if shapiro_normal else "non_normal"
            else:
                overall_assessment = "unknown"

            normality_results[name] = {
                "shapiro_wilk": {
                    "statistic": shapiro_stat,
                    "p_value": shapiro_p,
                    "is_normal": shapiro_normal,
                },
                "anderson_darling": {
                    "statistic": ad_stat,
                    "p_value": ad_p,
                    "is_normal": ad_normal,
                },
                "overall_assessment": overall_assessment,
            }

        return normality_results

    def _run_parametric_tests(
        self, trad_values: np.ndarray, ens_values: np.ndarray
    ) -> Dict[str, StatisticalTest]:
        """パラメトリック検定実行"""
        parametric_tests = {}

        # 等分散性検定
        try:
            levene_stat, levene_p = levene(trad_values, ens_values)
            equal_variances = levene_p > self.significance_level
        except Exception:
            equal_variances = True  # デフォルト仮定

        # Student's t-test（等分散仮定）
        if equal_variances:
            try:
                t_stat, t_p = stats.ttest_ind(ens_values, trad_values, equal_var=True)
                df = len(trad_values) + len(ens_values) - 2
                effect_size = self._calculate_cohens_d(ens_values, trad_values)

                # 信頼区間
                pooled_se = np.sqrt(
                    (
                        (len(trad_values) - 1) * np.var(trad_values, ddof=1)
                        + (len(ens_values) - 1) * np.var(ens_values, ddof=1)
                    )
                    / df
                )
                se_diff = pooled_se * np.sqrt(
                    1 / len(trad_values) + 1 / len(ens_values)
                )
                t_critical = stats.t.ppf(1 - self.significance_level / 2, df)
                mean_diff = np.mean(ens_values) - np.mean(trad_values)
                ci_lower = mean_diff - t_critical * se_diff
                ci_upper = mean_diff + t_critical * se_diff

                parametric_tests["student_t_test"] = StatisticalTest(
                    test_name="Student's t-test",
                    test_type="parametric",
                    statistic=t_stat,
                    p_value=t_p,
                    effect_size=effect_size,
                    confidence_interval=(ci_lower, ci_upper),
                    degrees_of_freedom=df,
                    assumptions_met={"equal_variances": True, "normality": True},
                    interpretation=self._interpret_test_result(t_p, effect_size),
                    recommendation=self._generate_test_recommendation(t_p, effect_size),
                )
            except Exception as e:
                logger.error(f"Student's t-test failed: {e}")

        # Welch's t-test（不等分散対応）
        try:
            welch_stat, welch_p = stats.ttest_ind(
                ens_values, trad_values, equal_var=False
            )

            # Welch's t-testの自由度計算
            s1_sq = np.var(trad_values, ddof=1)
            s2_sq = np.var(ens_values, ddof=1)
            n1, n2 = len(trad_values), len(ens_values)

            df_welch = (s1_sq / n1 + s2_sq / n2) ** 2 / (
                (s1_sq / n1) ** 2 / (n1 - 1) + (s2_sq / n2) ** 2 / (n2 - 1)
            )
            effect_size = self._calculate_cohens_d(ens_values, trad_values)

            # 信頼区間
            se_diff = np.sqrt(s1_sq / n1 + s2_sq / n2)
            t_critical = stats.t.ppf(1 - self.significance_level / 2, df_welch)
            mean_diff = np.mean(ens_values) - np.mean(trad_values)
            ci_lower = mean_diff - t_critical * se_diff
            ci_upper = mean_diff + t_critical * se_diff

            parametric_tests["welch_t_test"] = StatisticalTest(
                test_name="Welch's t-test",
                test_type="parametric",
                statistic=welch_stat,
                p_value=welch_p,
                effect_size=effect_size,
                confidence_interval=(ci_lower, ci_upper),
                degrees_of_freedom=int(df_welch),
                assumptions_met={"equal_variances": False, "normality": True},
                interpretation=self._interpret_test_result(welch_p, effect_size),
                recommendation=self._generate_test_recommendation(welch_p, effect_size),
            )
        except Exception as e:
            logger.error(f"Welch's t-test failed: {e}")

        return parametric_tests

    def _run_non_parametric_tests(
        self, trad_values: np.ndarray, ens_values: np.ndarray
    ) -> Dict[str, StatisticalTest]:
        """ノンパラメトリック検定実行"""
        non_parametric_tests = {}

        # Mann-Whitney U検定
        try:
            u_stat, u_p = mannwhitneyu(ens_values, trad_values, alternative="two-sided")

            # 効果サイズ（rank-biserial correlation）
            n1, n2 = len(trad_values), len(ens_values)
            effect_size = 1 - (2 * u_stat) / (n1 * n2)

            # 信頼区間（近似）
            se_u = np.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)
            z_critical = stats.norm.ppf(1 - self.significance_level / 2)
            u_lower = u_stat - z_critical * se_u
            u_upper = u_stat + z_critical * se_u

            non_parametric_tests["mann_whitney_u"] = StatisticalTest(
                test_name="Mann-Whitney U Test",
                test_type="non_parametric",
                statistic=u_stat,
                p_value=u_p,
                effect_size=effect_size,
                confidence_interval=(u_lower, u_upper),
                degrees_of_freedom=None,
                assumptions_met={"normality": False, "equal_variances": False},
                interpretation=self._interpret_test_result(u_p, effect_size),
                recommendation=self._generate_test_recommendation(u_p, effect_size),
            )
        except Exception as e:
            logger.error(f"Mann-Whitney U test failed: {e}")

        # Wilcoxon signed-rank検定（対応がある場合）
        if len(trad_values) == len(ens_values):
            try:
                w_stat, w_p = wilcoxon(ens_values, trad_values, alternative="two-sided")

                # 効果サイズ
                n = len(trad_values)
                effect_size = w_stat / (n * (n + 1) / 4)

                non_parametric_tests["wilcoxon_signed_rank"] = StatisticalTest(
                    test_name="Wilcoxon Signed-Rank Test",
                    test_type="non_parametric",
                    statistic=w_stat,
                    p_value=w_p,
                    effect_size=effect_size,
                    confidence_interval=(None, None),  # 計算が複雑
                    degrees_of_freedom=None,
                    assumptions_met={"normality": False, "paired_data": True},
                    interpretation=self._interpret_test_result(w_p, effect_size),
                    recommendation=self._generate_test_recommendation(w_p, effect_size),
                )
            except Exception as e:
                logger.error(f"Wilcoxon signed-rank test failed: {e}")

        return non_parametric_tests

    def _run_bootstrap_tests(
        self, trad_values: np.ndarray, ens_values: np.ndarray, metric: str
    ) -> Dict[str, BootstrapResult]:
        """ブートストラップ検定実行"""
        bootstrap_tests = {}

        # 基本ブートストラップ
        try:
            bootstrap_result = self._bootstrap_difference_test(
                trad_values, ens_values, metric
            )
            bootstrap_tests["basic_bootstrap"] = bootstrap_result
        except Exception as e:
            logger.error(f"Bootstrap test failed: {e}")

        # パーセンタイル法ブートストラップ
        try:
            percentile_result = self._bootstrap_percentile_test(
                trad_values, ens_values, metric
            )
            bootstrap_tests["percentile_bootstrap"] = percentile_result
        except Exception as e:
            logger.error(f"Percentile bootstrap test failed: {e}")

        # バイアス補正ブートストラップ
        try:
            bias_corrected_result = self._bootstrap_bias_corrected_test(
                trad_values, ens_values, metric
            )
            bootstrap_tests["bias_corrected_bootstrap"] = bias_corrected_result
        except Exception as e:
            logger.error(f"Bias-corrected bootstrap test failed: {e}")

        return bootstrap_tests

    def _bootstrap_difference_test(
        self, trad_values: np.ndarray, ens_values: np.ndarray, metric: str
    ) -> BootstrapResult:
        """基本ブートストラップ検定"""
        original_diff = np.mean(ens_values) - np.mean(trad_values)
        bootstrap_diffs = []

        np.random.seed(42)  # 再現性確保

        for _ in range(self.bootstrap_iterations):
            # リサンプリング
            trad_sample = np.random.choice(
                trad_values, size=len(trad_values), replace=True
            )
            ens_sample = np.random.choice(
                ens_values, size=len(ens_values), replace=True
            )

            # 差の計算
            bootstrap_diff = np.mean(ens_sample) - np.mean(trad_sample)
            bootstrap_diffs.append(bootstrap_diff)

        bootstrap_diffs = np.array(bootstrap_diffs)

        # 統計量計算
        bootstrap_mean = np.mean(bootstrap_diffs)
        bootstrap_std = np.std(bootstrap_diffs, ddof=1)

        # 信頼区間
        alpha = 1 - self.confidence_level
        ci_lower = np.percentile(bootstrap_diffs, (alpha / 2) * 100)
        ci_upper = np.percentile(bootstrap_diffs, (1 - alpha / 2) * 100)

        # p値（両側検定）
        p_value = 2 * min(np.mean(bootstrap_diffs >= 0), np.mean(bootstrap_diffs <= 0))

        return BootstrapResult(
            metric_name=metric,
            original_difference=original_diff,
            bootstrap_mean=bootstrap_mean,
            bootstrap_std=bootstrap_std,
            confidence_interval=(ci_lower, ci_upper),
            p_value=p_value,
            bootstrap_samples=bootstrap_diffs,
            significance_level=self.significance_level,
        )

    def _bootstrap_percentile_test(
        self, trad_values: np.ndarray, ens_values: np.ndarray, metric: str
    ) -> BootstrapResult:
        """パーセンタイル法ブートストラップ"""
        # 基本的に_bootstrap_difference_testと同じだが、信頼区間の計算方法が異なる
        return self._bootstrap_difference_test(trad_values, ens_values, metric)

    def _bootstrap_bias_corrected_test(
        self, trad_values: np.ndarray, ens_values: np.ndarray, metric: str
    ) -> BootstrapResult:
        """バイアス補正ブートストラップ"""
        original_diff = np.mean(ens_values) - np.mean(trad_values)
        bootstrap_diffs = []

        np.random.seed(42)

        for _ in range(self.bootstrap_iterations):
            trad_sample = np.random.choice(
                trad_values, size=len(trad_values), replace=True
            )
            ens_sample = np.random.choice(
                ens_values, size=len(ens_values), replace=True
            )
            bootstrap_diff = np.mean(ens_sample) - np.mean(trad_sample)
            bootstrap_diffs.append(bootstrap_diff)

        bootstrap_diffs = np.array(bootstrap_diffs)

        # バイアス補正
        bias = np.mean(bootstrap_diffs) - original_diff
        bias_corrected_diffs = bootstrap_diffs - bias

        # 統計量計算
        bootstrap_mean = np.mean(bias_corrected_diffs)
        bootstrap_std = np.std(bias_corrected_diffs, ddof=1)

        # 信頼区間
        alpha = 1 - self.confidence_level
        ci_lower = np.percentile(bias_corrected_diffs, (alpha / 2) * 100)
        ci_upper = np.percentile(bias_corrected_diffs, (1 - alpha / 2) * 100)

        # p値
        p_value = 2 * min(
            np.mean(bias_corrected_diffs >= 0), np.mean(bias_corrected_diffs <= 0)
        )

        return BootstrapResult(
            metric_name=metric,
            original_difference=original_diff,
            bootstrap_mean=bootstrap_mean,
            bootstrap_std=bootstrap_std,
            confidence_interval=(ci_lower, ci_upper),
            p_value=p_value,
            bootstrap_samples=bias_corrected_diffs,
            significance_level=self.significance_level,
        )

    def _calculate_effect_sizes(
        self, trad_values: np.ndarray, ens_values: np.ndarray
    ) -> Dict[str, float]:
        """効果サイズ計算"""
        effect_sizes = {}

        # Cohen's d
        effect_sizes["cohens_d"] = self._calculate_cohens_d(ens_values, trad_values)

        # Hedge's g（小サンプル補正）
        cohens_d = effect_sizes["cohens_d"]
        n1, n2 = len(trad_values), len(ens_values)
        correction_factor = 1 - (3 / (4 * (n1 + n2 - 2) - 1))
        effect_sizes["hedges_g"] = cohens_d * correction_factor

        # Glass's delta
        if np.std(trad_values, ddof=1) != 0:
            effect_sizes["glass_delta"] = (
                np.mean(ens_values) - np.mean(trad_values)
            ) / np.std(trad_values, ddof=1)
        else:
            effect_sizes["glass_delta"] = 0

        # Cliff's delta（順序統計量ベース）
        effect_sizes["cliffs_delta"] = self._calculate_cliffs_delta(
            trad_values, ens_values
        )

        # 共通言語効果サイズ
        effect_sizes["common_language_effect_size"] = self._calculate_cles(
            trad_values, ens_values
        )

        return effect_sizes

    def _calculate_cohens_d(self, group1: np.ndarray, group2: np.ndarray) -> float:
        """Cohen's d計算"""
        n1, n2 = len(group1), len(group2)
        if n1 < 2 or n2 < 2:
            return 0

        pooled_std = np.sqrt(
            ((n1 - 1) * np.var(group1, ddof=1) + (n2 - 1) * np.var(group2, ddof=1))
            / (n1 + n2 - 2)
        )

        if pooled_std == 0:
            return 0

        return (np.mean(group1) - np.mean(group2)) / pooled_std

    def _calculate_cliffs_delta(self, group1: np.ndarray, group2: np.ndarray) -> float:
        """Cliff's delta計算"""
        n1, n2 = len(group1), len(group2)
        if n1 == 0 or n2 == 0:
            return 0

        # 全ペアの比較
        greater = 0
        less = 0

        for x in group1:
            for y in group2:
                if x > y:
                    greater += 1
                elif x < y:
                    less += 1

        return (greater - less) / (n1 * n2)

    def _calculate_cles(self, group1: np.ndarray, group2: np.ndarray) -> float:
        """共通言語効果サイズ計算"""
        n1, n2 = len(group1), len(group2)
        if n1 == 0 or n2 == 0:
            return 0.5

        # group1の値がgroup2の値より大きい確率
        greater = 0
        total = 0

        for x in group1:
            for y in group2:
                if x > y:
                    greater += 1
                total += 1

        return greater / total if total > 0 else 0.5

    def _run_power_analysis(
        self, trad_values: np.ndarray, ens_values: np.ndarray
    ) -> PowerAnalysis:
        """検定力分析実行"""
        effect_size = self._calculate_cohens_d(ens_values, trad_values)
        sample_size = min(len(trad_values), len(ens_values))

        # 検定力計算（近似）
        power = self._calculate_power(effect_size, sample_size, self.significance_level)

        # 最小検出可能効果サイズ
        minimum_detectable_effect = self._calculate_minimum_detectable_effect(
            sample_size, self.significance_level, 0.8
        )

        # 必要サンプルサイズ
        required_sample_size = self._calculate_required_sample_size(
            effect_size, self.significance_level, 0.8
        )

        # 解釈
        if power >= 0.8:
            interpretation = "Sufficient power to detect meaningful effects"
        elif power >= 0.6:
            interpretation = "Moderate power - consider increasing sample size"
        else:
            interpretation = "Low power - insufficient to detect effects reliably"

        return PowerAnalysis(
            effect_size=effect_size,
            sample_size=sample_size,
            alpha=self.significance_level,
            power=power,
            minimum_detectable_effect=minimum_detectable_effect,
            required_sample_size=required_sample_size,
            interpretation=interpretation,
        )

    def _calculate_power(
        self, effect_size: float, sample_size: int, alpha: float
    ) -> float:
        """検定力計算（近似）"""
        if sample_size < 2:
            return 0

        # 非心度計算
        noncentrality = effect_size * np.sqrt(sample_size / 2)

        # 臨界値
        critical_value = stats.norm.ppf(1 - alpha / 2)

        # 検定力
        power = (
            1
            - stats.norm.cdf(critical_value - noncentrality)
            + stats.norm.cdf(-critical_value - noncentrality)
        )

        return np.clip(power, 0, 1)

    def _calculate_minimum_detectable_effect(
        self, sample_size: int, alpha: float, power: float
    ) -> float:
        """最小検出可能効果サイズ計算"""
        if sample_size < 2:
            return float("inf")

        z_alpha = stats.norm.ppf(1 - alpha / 2)
        z_beta = stats.norm.ppf(power)

        return (z_alpha + z_beta) / np.sqrt(sample_size / 2)

    def _calculate_required_sample_size(
        self, effect_size: float, alpha: float, power: float
    ) -> int:
        """必要サンプルサイズ計算"""
        if effect_size == 0:
            return float("inf")

        z_alpha = stats.norm.ppf(1 - alpha / 2)
        z_beta = stats.norm.ppf(power)

        required_n = 2 * ((z_alpha + z_beta) / effect_size) ** 2

        return int(np.ceil(required_n))

    def _run_bayesian_analysis(
        self, trad_values: np.ndarray, ens_values: np.ndarray, metric: str
    ) -> BayesianAnalysis:
        """ベイズ分析実行"""
        # 事前分布設定（無情報事前分布）
        prior_mean = 0
        prior_std = 1

        # 尤度計算
        observed_diff = np.mean(ens_values) - np.mean(trad_values)
        observed_se = np.sqrt(
            np.var(ens_values, ddof=1) / len(ens_values)
            + np.var(trad_values, ddof=1) / len(trad_values)
        )

        # 事後分布計算（正規分布の共役性を利用）
        prior_precision = 1 / (prior_std**2)
        likelihood_precision = 1 / (observed_se**2)

        posterior_precision = prior_precision + likelihood_precision
        posterior_mean = (
            prior_precision * prior_mean + likelihood_precision * observed_diff
        ) / posterior_precision
        posterior_std = np.sqrt(1 / posterior_precision)

        # 信頼区間
        alpha = 1 - self.confidence_level
        credible_lower = stats.norm.ppf(alpha / 2, posterior_mean, posterior_std)
        credible_upper = stats.norm.ppf(1 - alpha / 2, posterior_mean, posterior_std)

        # ベイズファクター（簡易版）
        marginal_likelihood_null = stats.norm.pdf(observed_diff, 0, observed_se)
        marginal_likelihood_alt = stats.norm.pdf(
            observed_diff, posterior_mean, posterior_std
        )
        bayes_factor = (
            marginal_likelihood_alt / marginal_likelihood_null
            if marginal_likelihood_null > 0
            else 1
        )

        # 解釈
        if bayes_factor > 10:
            interpretation = "Strong evidence for ensemble superiority"
        elif bayes_factor > 3:
            interpretation = "Moderate evidence for ensemble superiority"
        elif bayes_factor > 1:
            interpretation = "Weak evidence for ensemble superiority"
        else:
            interpretation = "Insufficient evidence for ensemble superiority"

        return BayesianAnalysis(
            prior_mean=prior_mean,
            prior_std=prior_std,
            likelihood_mean=observed_diff,
            likelihood_std=observed_se,
            posterior_mean=posterior_mean,
            posterior_std=posterior_std,
            credible_interval=(credible_lower, credible_upper),
            bayes_factor=bayes_factor,
            interpretation=interpretation,
        )

    def _interpret_test_result(self, p_value: float, effect_size: float) -> str:
        """検定結果解釈"""
        is_significant = p_value < self.significance_level

        # 効果サイズ解釈
        if abs(effect_size) < self.effect_size_thresholds["small"]:
            size_interpretation = "negligible"
        elif abs(effect_size) < self.effect_size_thresholds["medium"]:
            size_interpretation = "small"
        elif abs(effect_size) < self.effect_size_thresholds["large"]:
            size_interpretation = "medium"
        else:
            size_interpretation = "large"

        # 総合解釈
        if is_significant:
            if effect_size > 0:
                return f"Statistically significant improvement (p={p_value:.4f}, {size_interpretation} effect)"
            else:
                return f"Statistically significant decline (p={p_value:.4f}, {size_interpretation} effect)"
        else:
            return f"No significant difference (p={p_value:.4f}, {size_interpretation} effect)"

    def _generate_test_recommendation(self, p_value: float, effect_size: float) -> str:
        """検定に基づく推奨事項生成"""
        is_significant = p_value < self.significance_level
        is_large_effect = abs(effect_size) >= self.effect_size_thresholds["large"]
        is_medium_effect = abs(effect_size) >= self.effect_size_thresholds["medium"]

        if is_significant and is_large_effect and effect_size > 0:
            return "Strong recommendation: Deploy ensemble system"
        elif is_significant and is_medium_effect and effect_size > 0:
            return "Moderate recommendation: Consider ensemble deployment"
        elif is_significant and effect_size > 0:
            return "Weak recommendation: Monitor performance carefully"
        elif not is_significant and is_large_effect:
            return "Increase sample size to confirm large effect"
        else:
            return "Insufficient evidence for ensemble superiority"

    def _generate_comprehensive_assessment(
        self, verification_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """包括的評価生成"""
        assessment = {
            "overall_significance": {},
            "consistency_analysis": {},
            "robustness_assessment": {},
            "practical_significance": {},
            "recommendations": [],
        }

        # 全体的な有意性
        significant_tests = 0
        total_tests = 0

        for metric, results in verification_results.items():
            # パラメトリック検定
            for test_name, test_result in results.get("parametric_tests", {}).items():
                total_tests += 1
                if test_result.p_value < self.significance_level:
                    significant_tests += 1

            # ノンパラメトリック検定
            for test_name, test_result in results.get(
                "non_parametric_tests", {}
            ).items():
                total_tests += 1
                if test_result.p_value < self.significance_level:
                    significant_tests += 1

        assessment["overall_significance"] = {
            "significant_tests": significant_tests,
            "total_tests": total_tests,
            "significance_rate": (
                significant_tests / total_tests if total_tests > 0 else 0
            ),
        }

        # 一貫性分析
        consistency_scores = []
        for metric, results in verification_results.items():
            parametric_p = None
            non_parametric_p = None

            # パラメトリック検定の結果
            parametric_tests = results.get("parametric_tests", {})
            if parametric_tests:
                parametric_p = list(parametric_tests.values())[0].p_value

            # ノンパラメトリック検定の結果
            non_parametric_tests = results.get("non_parametric_tests", {})
            if non_parametric_tests:
                non_parametric_p = list(non_parametric_tests.values())[0].p_value

            # 一貫性スコア
            if parametric_p is not None and non_parametric_p is not None:
                consistency_score = 1 - abs(parametric_p - non_parametric_p)
                consistency_scores.append(consistency_score)

        assessment["consistency_analysis"] = {
            "avg_consistency": np.mean(consistency_scores) if consistency_scores else 0,
            "consistency_scores": consistency_scores,
        }

        # ロバストネス評価
        robust_improvements = 0
        total_metrics = len(verification_results)

        for metric, results in verification_results.items():
            # 複数の検定で一貫して有意な改善
            significant_count = 0
            test_count = 0

            for test_type in ["parametric_tests", "non_parametric_tests"]:
                for test_name, test_result in results.get(test_type, {}).items():
                    test_count += 1
                    if (
                        test_result.p_value < self.significance_level
                        and test_result.effect_size > 0
                    ):
                        significant_count += 1

            if significant_count >= max(1, test_count // 2):
                robust_improvements += 1

        assessment["robustness_assessment"] = {
            "robust_improvements": robust_improvements,
            "total_metrics": total_metrics,
            "robustness_rate": (
                robust_improvements / total_metrics if total_metrics > 0 else 0
            ),
        }

        # 実用的有意性
        practical_improvements = []
        for metric, results in verification_results.items():
            desc_stats = results.get("descriptive_stats", {})
            improvement_pct = desc_stats.get("difference", {}).get("improvement_pct", 0)

            # 実用的改善閾値
            practical_thresholds = {
                "accuracy": 2.0,  # 2%以上
                "precision": 2.0,
                "recall": 2.0,
                "f1_score": 2.0,
                "total_return": 5.0,  # 5%以上
                "sharpe_ratio": 10.0,  # 10%以上
                "win_rate": 3.0,  # 3%以上
            }

            threshold = practical_thresholds.get(metric, 5.0)
            if improvement_pct > threshold:
                practical_improvements.append(metric)

        assessment["practical_significance"] = {
            "practical_improvements": practical_improvements,
            "improvement_rate": (
                len(practical_improvements) / total_metrics if total_metrics > 0 else 0
            ),
        }

        # 推奨事項
        recommendations = []

        significance_rate = assessment["overall_significance"]["significance_rate"]
        robustness_rate = assessment["robustness_assessment"]["robustness_rate"]
        improvement_rate = assessment["practical_significance"]["improvement_rate"]

        if (
            significance_rate >= 0.8
            and robustness_rate >= 0.6
            and improvement_rate >= 0.5
        ):
            recommendations.append(
                "Strong statistical evidence supports ensemble deployment"
            )
        elif significance_rate >= 0.6 and robustness_rate >= 0.4:
            recommendations.append("Moderate evidence supports ensemble consideration")
        elif significance_rate >= 0.4:
            recommendations.append(
                "Weak evidence - monitor performance over longer period"
            )
        else:
            recommendations.append("Insufficient evidence for ensemble superiority")

        if improvement_rate >= 0.6:
            recommendations.append(
                "Practical significance achieved - deployment recommended"
            )
        elif improvement_rate >= 0.4:
            recommendations.append(
                "Some practical benefits - selective deployment consideration"
            )

        assessment["recommendations"] = recommendations

        return assessment

    def generate_detailed_report(self, verification_results: Dict[str, Any]) -> str:
        """詳細レポート生成"""
        report_lines = []
        report_lines.append("🔬 アンサンブル学習統計的検証レポート")
        report_lines.append("=" * 80)

        # メタデータ
        metadata = verification_results.get("metadata", {})
        report_lines.append(f"\n📊 検証概要:")
        report_lines.append(
            f"  検証実行日時: {metadata.get('verification_date', 'N/A')}"
        )
        report_lines.append(
            f"  検証対象メトリクス: {', '.join(metadata.get('metrics_tested', []))}"
        )
        report_lines.append(f"  有意水準: {metadata.get('significance_level', 0.05)}")
        report_lines.append(f"  信頼水準: {metadata.get('confidence_level', 0.95)}")

        # 包括的評価
        assessment = verification_results.get("comprehensive_assessment", {})

        if "overall_significance" in assessment:
            sig_info = assessment["overall_significance"]
            report_lines.append(f"\n📈 全体的有意性:")
            report_lines.append(
                f"  有意な検定数: {sig_info.get('significant_tests', 0)}"
            )
            report_lines.append(f"  総検定数: {sig_info.get('total_tests', 0)}")
            report_lines.append(
                f"  有意性率: {sig_info.get('significance_rate', 0):.2%}"
            )

        if "robustness_assessment" in assessment:
            robust_info = assessment["robustness_assessment"]
            report_lines.append(f"\n💪 ロバストネス評価:")
            report_lines.append(
                f"  ロバストな改善メトリクス: {robust_info.get('robust_improvements', 0)}"
            )
            report_lines.append(
                f"  総メトリクス数: {robust_info.get('total_metrics', 0)}"
            )
            report_lines.append(
                f"  ロバストネス率: {robust_info.get('robustness_rate', 0):.2%}"
            )

        if "practical_significance" in assessment:
            practical_info = assessment["practical_significance"]
            report_lines.append(f"\n🎯 実用的有意性:")
            report_lines.append(
                f"  実用的改善メトリクス: {', '.join(practical_info.get('practical_improvements', []))}"
            )
            report_lines.append(
                f"  実用的改善率: {practical_info.get('improvement_rate', 0):.2%}"
            )

        # 個別メトリクス結果
        verification_data = verification_results.get("verification_results", {})
        if verification_data:
            report_lines.append(f"\n📋 個別メトリクス詳細:")

            for metric, results in verification_data.items():
                report_lines.append(f"\n  {metric.upper()}:")

                # 記述統計
                desc_stats = results.get("descriptive_stats", {})
                if desc_stats:
                    diff_stats = desc_stats.get("difference", {})
                    report_lines.append(
                        f"    改善効果: {diff_stats.get('improvement_pct', 0):+.2f}%"
                    )

                # 主要検定結果
                parametric_tests = results.get("parametric_tests", {})
                if parametric_tests:
                    for test_name, test_result in parametric_tests.items():
                        report_lines.append(
                            f"    {test_name}: p={test_result.p_value:.4f}, 効果サイズ={test_result.effect_size:.3f}"
                        )

                # ブートストラップ結果
                bootstrap_tests = results.get("bootstrap_tests", {})
                if bootstrap_tests:
                    for test_name, bootstrap_result in bootstrap_tests.items():
                        if test_name == "basic_bootstrap":
                            ci = bootstrap_result.confidence_interval
                            report_lines.append(
                                f"    Bootstrap CI: [{ci[0]:.4f}, {ci[1]:.4f}]"
                            )

        # 推奨事項
        recommendations = assessment.get("recommendations", [])
        if recommendations:
            report_lines.append(f"\n💡 推奨事項:")
            for rec in recommendations:
                report_lines.append(f"  • {rec}")

        report_lines.append(f"\n" + "=" * 80)
        return "\n".join(report_lines)

    def save_results(
        self,
        verification_results: Dict[str, Any],
        filename_prefix: str = "ensemble_statistical_verification",
    ) -> Path:
        """結果保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSON結果保存
        json_file = self.output_dir / f"{filename_prefix}_{timestamp}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            # DataClassを辞書に変換
            serializable_results = self._make_serializable(verification_results)
            json.dump(
                serializable_results, f, indent=2, ensure_ascii=False, default=str
            )

        # レポート保存
        report_file = self.output_dir / f"{filename_prefix}_report_{timestamp}.txt"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(self.generate_detailed_report(verification_results))

        # 可視化グラフ保存
        self._create_statistical_plots(verification_results, timestamp)

        logger.info(f"Results saved to: {json_file}")
        logger.info(f"Report saved to: {report_file}")

        return self.output_dir

    def _make_serializable(self, obj):
        """JSON序列化可能な形式に変換"""
        if hasattr(obj, "__dict__"):
            return {k: self._make_serializable(v) for k, v in obj.__dict__.items()}
        elif isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, tuple):
            return tuple(self._make_serializable(item) for item in obj)
        elif isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        else:
            return obj

    def _create_statistical_plots(
        self, verification_results: Dict[str, Any], timestamp: str
    ):
        """統計的可視化プロット作成"""
        try:
            verification_data = verification_results.get("verification_results", {})
            if not verification_data:
                return

            # 設定
            plt.style.use("seaborn-v0_8")
            fig, axes = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle("統計的検証結果", fontsize=16, y=0.98)

            # データ準備
            metrics = list(verification_data.keys())
            p_values = []
            effect_sizes = []
            improvements = []

            for metric in metrics:
                results = verification_data[metric]

                # p値取得
                parametric_tests = results.get("parametric_tests", {})
                if parametric_tests:
                    p_val = list(parametric_tests.values())[0].p_value
                    p_values.append(p_val)
                else:
                    p_values.append(1.0)

                # 効果サイズ取得
                effect_size_data = results.get("effect_size_analysis", {})
                if effect_size_data:
                    effect_size = effect_size_data.get("cohens_d", 0)
                    effect_sizes.append(effect_size)
                else:
                    effect_sizes.append(0)

                # 改善率取得
                desc_stats = results.get("descriptive_stats", {})
                if desc_stats:
                    improvement = desc_stats.get("difference", {}).get(
                        "improvement_pct", 0
                    )
                    improvements.append(improvement)
                else:
                    improvements.append(0)

            # p値分布
            axes[0, 0].bar(metrics, p_values, alpha=0.7, color="skyblue")
            axes[0, 0].axhline(
                y=0.05,
                color="red",
                linestyle="--",
                alpha=0.7,
                label="有意水準 (α=0.05)",
            )
            axes[0, 0].set_title("統計的有意性 (p値)")
            axes[0, 0].set_ylabel("p値")
            axes[0, 0].tick_params(axis="x", rotation=45)
            axes[0, 0].legend()
            axes[0, 0].grid(True, alpha=0.3)

            # 効果サイズ分布
            colors = [
                "red" if es < 0.2 else "orange" if es < 0.5 else "green"
                for es in effect_sizes
            ]
            axes[0, 1].bar(metrics, effect_sizes, alpha=0.7, color=colors)
            axes[0, 1].set_title("効果サイズ (Cohen's d)")
            axes[0, 1].set_ylabel("効果サイズ")
            axes[0, 1].tick_params(axis="x", rotation=45)
            axes[0, 1].grid(True, alpha=0.3)

            # 改善率分布
            axes[1, 0].bar(metrics, improvements, alpha=0.7, color="lightgreen")
            axes[1, 0].set_title("パフォーマンス改善率")
            axes[1, 0].set_ylabel("改善率 (%)")
            axes[1, 0].tick_params(axis="x", rotation=45)
            axes[1, 0].grid(True, alpha=0.3)

            # 効果サイズ vs p値 散布図
            axes[1, 1].scatter(effect_sizes, p_values, alpha=0.7, s=100, color="purple")
            axes[1, 1].set_xlabel("効果サイズ (Cohen's d)")
            axes[1, 1].set_ylabel("p値")
            axes[1, 1].set_title("効果サイズ vs 統計的有意性")
            axes[1, 1].axhline(y=0.05, color="red", linestyle="--", alpha=0.5)
            axes[1, 1].axvline(
                x=0.2, color="orange", linestyle="--", alpha=0.5, label="小効果"
            )
            axes[1, 1].axvline(
                x=0.5, color="green", linestyle="--", alpha=0.5, label="中効果"
            )
            axes[1, 1].axvline(
                x=0.8, color="blue", linestyle="--", alpha=0.5, label="大効果"
            )
            axes[1, 1].legend()
            axes[1, 1].grid(True, alpha=0.3)

            # メトリクス名を追加
            for i, metric in enumerate(metrics):
                axes[1, 1].annotate(
                    metric,
                    (effect_sizes[i], p_values[i]),
                    xytext=(5, 5),
                    textcoords="offset points",
                    fontsize=8,
                )

            plt.tight_layout()

            # 保存
            plot_file = self.output_dir / f"statistical_verification_{timestamp}.png"
            plt.savefig(plot_file, dpi=300, bbox_inches="tight")
            plt.close()

            logger.info(f"Statistical plots saved to: {plot_file}")

        except Exception as e:
            logger.error(f"Failed to create statistical plots: {e}")


def main():
    """メイン実行関数"""
    print("🔬 アンサンブル学習統計的検証システム")
    print("=" * 60)

    try:
        # 統計的検証システム初期化
        verification_system = EnsembleStatisticalVerification()

        # サンプルデータ生成
        print("\n📊 サンプルデータ生成...")
        np.random.seed(42)

        # 従来手法サンプル
        traditional_data = [
            {
                "accuracy": 0.58 + np.random.normal(0, 0.03),
                "total_return": 0.02 + np.random.normal(0, 0.01),
                "sharpe_ratio": 1.2 + np.random.normal(0, 0.2),
                "win_rate": 0.55 + np.random.normal(0, 0.05),
            }
            for _ in range(100)
        ]

        # アンサンブル手法サンプル
        ensemble_data = [
            {
                "accuracy": 0.63 + np.random.normal(0, 0.03),
                "total_return": 0.025 + np.random.normal(0, 0.01),
                "sharpe_ratio": 1.5 + np.random.normal(0, 0.2),
                "win_rate": 0.62 + np.random.normal(0, 0.05),
            }
            for _ in range(100)
        ]

        # 包括的検証実行
        print("\n🔍 包括的統計的検証実行中...")
        verification_results = verification_system.run_comprehensive_verification(
            traditional_data,
            ensemble_data,
            ["accuracy", "total_return", "sharpe_ratio", "win_rate"],
        )

        # 結果表示
        print("\n📈 検証結果:")
        report = verification_system.generate_detailed_report(verification_results)
        print(report)

        # 結果保存
        print("\n💾 結果保存中...")
        output_path = verification_system.save_results(verification_results)
        print(f"結果保存完了: {output_path}")

        print("\n✅ 統計的検証完了")

    except Exception as e:
        logger.error(f"Statistical verification failed: {e}")
        print(f"\n❌ エラー: {e}")


if __name__ == "__main__":
    main()
