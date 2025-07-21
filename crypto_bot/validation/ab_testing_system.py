# =============================================================================
# ファイル名: crypto_bot/validation/ab_testing_system.py
# 説明:
# Phase C2: A/Bテスト・統計的検証システム
# 動的重み調整vs固定重み・戦略比較・統計的有意性検定・実験管理
# 科学的検証・効果測定・意思決定支援システム
# =============================================================================

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import json
import os
import uuid

import numpy as np
import pandas as pd
from collections import deque, defaultdict
from scipy import stats
from scipy.stats import chi2_contingency, mannwhitneyu, ttest_ind, wilcoxon
import matplotlib.pyplot as plt
try:
    import seaborn as sns
    SEABORN_AVAILABLE = True
except ImportError:
    SEABORN_AVAILABLE = False
    sns = None

logger = logging.getLogger(__name__)


class ExperimentStatus(Enum):
    """実験ステータス"""
    PLANNED = "planned"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    STOPPED = "stopped"


class TreatmentGroup(Enum):
    """処理グループ"""
    CONTROL = "control"
    TREATMENT = "treatment"
    CONTROL_A = "control_a"
    TREATMENT_B = "treatment_b"


@dataclass
class ExperimentConfig:
    """実験設定"""
    experiment_id: str
    name: str
    description: str
    hypothesis: str
    
    # 実験設計
    control_config: Dict[str, Any]
    treatment_config: Dict[str, Any]
    traffic_allocation: float  # treatment群への割り当て比率
    
    # 統計設定
    significance_level: float = 0.05
    power: float = 0.8
    minimum_effect_size: float = 0.1
    min_sample_size: int = 100
    max_duration_days: int = 30
    
    # 評価指標
    primary_metrics: List[str] = None
    secondary_metrics: List[str] = None
    
    # その他
    metadata: Dict[str, Any] = None


@dataclass
class ExperimentResult:
    """実験結果"""
    timestamp: datetime
    user_id: str
    group: TreatmentGroup
    metrics: Dict[str, float]
    metadata: Dict[str, Any] = None


@dataclass
class StatisticalTestResult:
    """統計検定結果"""
    test_name: str
    statistic: float
    p_value: float
    effect_size: float
    confidence_interval: Tuple[float, float]
    is_significant: bool
    interpretation: str


class ABTestingSystem:
    """
    Phase C2: A/Bテスト・統計的検証システム
    
    機能:
    - 包括的A/Bテスト実験管理・実行・分析
    - 動的重み調整vs固定重み比較テスト
    - 統計的有意性検定（t検定・Mann-Whitney U・Wilcoxon等）
    - 効果サイズ・信頼区間・統計的検出力計算
    - リアルタイム実験監視・早期停止判定
    - 多変量テスト・複数指標同時評価
    - 実験結果可視化・レポート生成
    """

    def __init__(self, config: Dict[str, Any]):
        """
        A/Bテストシステム初期化
        
        Parameters:
        -----------
        config : Dict[str, Any]
            A/Bテスト設定辞書
        """
        self.config = config
        
        # 基本設定
        ab_config = config.get("ab_testing", {})
        self.enable_ab_testing = ab_config.get("enabled", False)
        self.max_concurrent_experiments = ab_config.get("max_concurrent", 3)
        self.default_significance_level = ab_config.get("significance_level", 0.05)
        self.default_power = ab_config.get("statistical_power", 0.8)
        self.monitoring_interval = ab_config.get("monitoring_interval", 3600)  # 秒
        
        # 統計設定
        stats_config = ab_config.get("statistics", {})
        self.enable_sequential_testing = stats_config.get("sequential_testing", True)
        self.multiple_testing_correction = stats_config.get("multiple_testing_correction", "bonferroni")
        self.effect_size_methods = stats_config.get("effect_size_methods", ["cohen_d", "hedges_g"])
        
        # データ管理
        self.active_experiments: Dict[str, ExperimentConfig] = {}
        self.experiment_results: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self.experiment_analytics: Dict[str, Dict] = {}
        
        # 統計結果キャッシュ
        self.statistical_results: Dict[str, List[StatisticalTestResult]] = defaultdict(list)
        self.last_analysis_time: Dict[str, datetime] = {}
        
        # 監視・アラート
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_monitoring = threading.Event()
        
        # 統計追跡
        self.ab_stats = {
            "total_experiments": 0,
            "active_experiments": 0,
            "completed_experiments": 0,
            "significant_results": 0,
            "statistical_tests_performed": 0,
            "users_assigned": 0,
            "results_recorded": 0,
        }
        
        # ランダム化・ハッシュ
        self.hash_seed = ab_config.get("hash_seed", 42)
        
        # 結果保存
        self.enable_persistence = ab_config.get("persistence", {}).get("enabled", False)
        self.persistence_path = ab_config.get("persistence", {}).get("path", "data/ab_testing")
        
        # 可視化設定
        self.enable_visualization = ab_config.get("visualization", {}).get("enabled", True)
        self.plot_style = ab_config.get("visualization", {}).get("style", "seaborn")
        
        logger.info("🧪 ABTestingSystem initialized")
        logger.info(f"   A/B testing enabled: {self.enable_ab_testing}")
        logger.info(f"   Max concurrent experiments: {self.max_concurrent_experiments}")
        logger.info(f"   Sequential testing: {self.enable_sequential_testing}")

    def create_experiment(
        self,
        name: str,
        description: str,
        hypothesis: str,
        control_config: Dict[str, Any],
        treatment_config: Dict[str, Any],
        primary_metrics: List[str],
        secondary_metrics: Optional[List[str]] = None,
        traffic_allocation: float = 0.5,
        significance_level: float = None,
        min_sample_size: int = 100,
        max_duration_days: int = 30
    ) -> str:
        """
        A/Bテスト実験作成
        
        Parameters:
        -----------
        name : str
            実験名
        description : str
            実験説明
        hypothesis : str
            仮説
        control_config : Dict[str, Any]
            コントロール群設定
        treatment_config : Dict[str, Any]
            処理群設定
        primary_metrics : List[str]
            主要評価指標
        secondary_metrics : List[str], optional
            副次評価指標
        traffic_allocation : float
            処理群への割り当て比率
        significance_level : float, optional
            有意水準
        min_sample_size : int
            最小サンプルサイズ
        max_duration_days : int
            最大実験期間
            
        Returns:
        --------
        str
            実験ID
        """
        try:
            # 実験ID生成
            experiment_id = str(uuid.uuid4())
            
            # 実験設定作成
            experiment = ExperimentConfig(
                experiment_id=experiment_id,
                name=name,
                description=description,
                hypothesis=hypothesis,
                control_config=control_config,
                treatment_config=treatment_config,
                traffic_allocation=traffic_allocation,
                significance_level=significance_level or self.default_significance_level,
                power=self.default_power,
                min_sample_size=min_sample_size,
                max_duration_days=max_duration_days,
                primary_metrics=primary_metrics,
                secondary_metrics=secondary_metrics or [],
                metadata={
                    "created_at": datetime.now(),
                    "status": ExperimentStatus.PLANNED.value
                }
            )
            
            # 実験登録
            self.active_experiments[experiment_id] = experiment
            self.ab_stats["total_experiments"] += 1
            
            logger.info(f"🧪 Created experiment: {name} (ID: {experiment_id})")
            
            return experiment_id
            
        except Exception as e:
            logger.error(f"❌ Failed to create experiment: {e}")
            return ""

    def start_experiment(self, experiment_id: str) -> bool:
        """実験開始"""
        try:
            if experiment_id not in self.active_experiments:
                logger.error(f"Experiment not found: {experiment_id}")
                return False
                
            # 同時実行制限チェック
            running_count = sum(1 for exp in self.active_experiments.values() 
                              if exp.metadata.get("status") == ExperimentStatus.RUNNING.value)
            
            if running_count >= self.max_concurrent_experiments:
                logger.error(f"Max concurrent experiments reached: {running_count}")
                return False
                
            # 実験開始
            experiment = self.active_experiments[experiment_id]
            experiment.metadata["status"] = ExperimentStatus.RUNNING.value
            experiment.metadata["started_at"] = datetime.now()
            
            self.ab_stats["active_experiments"] += 1
            
            # 監視開始
            if not self.monitoring_active:
                self.start_monitoring()
                
            logger.info(f"🚀 Started experiment: {experiment.name}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start experiment {experiment_id}: {e}")
            return False

    def assign_user_to_group(self, experiment_id: str, user_id: str) -> Optional[TreatmentGroup]:
        """ユーザーのグループ割り当て"""
        try:
            if experiment_id not in self.active_experiments:
                return None
                
            experiment = self.active_experiments[experiment_id]
            
            # 実験が実行中かチェック
            if experiment.metadata.get("status") != ExperimentStatus.RUNNING.value:
                return None
                
            # ハッシュベース一貫的割り当て
            hash_input = f"{experiment_id}_{user_id}_{self.hash_seed}"
            hash_value = hash(hash_input) % 10000 / 10000  # 0-1の値
            
            if hash_value < experiment.traffic_allocation:
                group = TreatmentGroup.TREATMENT
            else:
                group = TreatmentGroup.CONTROL
                
            self.ab_stats["users_assigned"] += 1
            
            return group
            
        except Exception as e:
            logger.error(f"User assignment failed for {experiment_id}: {e}")
            return None

    def record_result(
        self,
        experiment_id: str,
        user_id: str,
        group: TreatmentGroup,
        metrics: Dict[str, float],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """実験結果記録"""
        try:
            if experiment_id not in self.active_experiments:
                logger.warning(f"Recording result for unknown experiment: {experiment_id}")
                return
                
            result = ExperimentResult(
                timestamp=datetime.now(),
                user_id=user_id,
                group=group,
                metrics=metrics,
                metadata=metadata
            )
            
            self.experiment_results[experiment_id].append(result)
            self.ab_stats["results_recorded"] += 1
            
            # 定期分析トリガー
            if len(self.experiment_results[experiment_id]) % 50 == 0:
                self._trigger_interim_analysis(experiment_id)
                
        except Exception as e:
            logger.error(f"Result recording failed for {experiment_id}: {e}")

    def _trigger_interim_analysis(self, experiment_id: str):
        """中間分析実行"""
        try:
            # 最小サンプルサイズチェック
            experiment = self.active_experiments[experiment_id]
            results = list(self.experiment_results[experiment_id])
            
            if len(results) < experiment.min_sample_size:
                return
                
            # 統計分析実行
            analysis_results = self.analyze_experiment(experiment_id)
            
            if analysis_results:
                # 早期停止判定
                self._evaluate_early_stopping(experiment_id, analysis_results)
                
        except Exception as e:
            logger.error(f"Interim analysis failed for {experiment_id}: {e}")

    def analyze_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """実験統計分析"""
        try:
            if experiment_id not in self.active_experiments:
                return None
                
            experiment = self.active_experiments[experiment_id]
            results = list(self.experiment_results[experiment_id])
            
            if len(results) < 10:  # 最小データ要件
                return None
                
            # グループ別データ分離
            control_results = [r for r in results if r.group == TreatmentGroup.CONTROL]
            treatment_results = [r for r in results if r.group == TreatmentGroup.TREATMENT]
            
            if len(control_results) < 5 or len(treatment_results) < 5:
                return None
                
            analysis_results = {
                "experiment_id": experiment_id,
                "analysis_timestamp": datetime.now(),
                "sample_sizes": {
                    "control": len(control_results),
                    "treatment": len(treatment_results)
                },
                "statistical_tests": {},
                "summary": {}
            }
            
            # 主要指標分析
            for metric in experiment.primary_metrics:
                metric_analysis = self._analyze_metric(
                    metric, control_results, treatment_results, experiment.significance_level
                )
                analysis_results["statistical_tests"][metric] = metric_analysis
                
            # 副次指標分析
            for metric in experiment.secondary_metrics:
                metric_analysis = self._analyze_metric(
                    metric, control_results, treatment_results, experiment.significance_level,
                    apply_correction=True
                )
                analysis_results["statistical_tests"][metric] = metric_analysis
                
            # サマリー生成
            analysis_results["summary"] = self._generate_analysis_summary(analysis_results)
            
            # 結果キャッシュ
            self.statistical_results[experiment_id].append(analysis_results)
            self.last_analysis_time[experiment_id] = datetime.now()
            self.ab_stats["statistical_tests_performed"] += 1
            
            return analysis_results
            
        except Exception as e:
            logger.error(f"Experiment analysis failed for {experiment_id}: {e}")
            return None

    def _analyze_metric(
        self,
        metric_name: str,
        control_results: List[ExperimentResult],
        treatment_results: List[ExperimentResult],
        significance_level: float,
        apply_correction: bool = False
    ) -> Dict[str, Any]:
        """指標別統計分析"""
        try:
            # データ抽出
            control_values = [r.metrics.get(metric_name, 0) for r in control_results 
                            if metric_name in r.metrics]
            treatment_values = [r.metrics.get(metric_name, 0) for r in treatment_results 
                              if metric_name in r.metrics]
            
            if len(control_values) < 3 or len(treatment_values) < 3:
                return {"error": "Insufficient data"}
                
            control_array = np.array(control_values)
            treatment_array = np.array(treatment_values)
            
            metric_analysis = {
                "metric_name": metric_name,
                "descriptive_stats": {
                    "control": {
                        "mean": np.mean(control_array),
                        "std": np.std(control_array),
                        "count": len(control_array),
                        "median": np.median(control_array)
                    },
                    "treatment": {
                        "mean": np.mean(treatment_array),
                        "std": np.std(treatment_array),
                        "count": len(treatment_array),
                        "median": np.median(treatment_array)
                    }
                },
                "statistical_tests": {}
            }
            
            # 多重検定補正
            alpha = significance_level
            if apply_correction and self.multiple_testing_correction == "bonferroni":
                alpha = significance_level / max(1, len(self.active_experiments))
                
            # 1. Welch's t-test (不等分散t検定)
            try:
                t_stat, p_value = ttest_ind(treatment_array, control_array, equal_var=False)
                
                # Cohen's d (効果サイズ)
                pooled_std = np.sqrt(((len(control_array) - 1) * np.var(control_array) + 
                                    (len(treatment_array) - 1) * np.var(treatment_array)) / 
                                   (len(control_array) + len(treatment_array) - 2))
                cohens_d = (np.mean(treatment_array) - np.mean(control_array)) / pooled_std if pooled_std > 0 else 0
                
                # 信頼区間 (差の平均)
                mean_diff = np.mean(treatment_array) - np.mean(control_array)
                se_diff = np.sqrt(np.var(treatment_array)/len(treatment_array) + 
                                np.var(control_array)/len(control_array))
                t_critical = stats.t.ppf(1 - alpha/2, len(control_array) + len(treatment_array) - 2)
                ci_lower = mean_diff - t_critical * se_diff
                ci_upper = mean_diff + t_critical * se_diff
                
                metric_analysis["statistical_tests"]["t_test"] = StatisticalTestResult(
                    test_name="Welch's t-test",
                    statistic=t_stat,
                    p_value=p_value,
                    effect_size=cohens_d,
                    confidence_interval=(ci_lower, ci_upper),
                    is_significant=p_value < alpha,
                    interpretation=self._interpret_t_test(p_value, cohens_d, alpha)
                )
                
            except Exception as t_error:
                logger.warning(f"t-test failed for {metric_name}: {t_error}")
                
            # 2. Mann-Whitney U test (ノンパラメトリック)
            try:
                u_stat, p_value_mw = mannwhitneyu(treatment_array, control_array, alternative='two-sided')
                
                # 効果サイズ (r = Z / sqrt(N))
                z_score = stats.norm.ppf(1 - p_value_mw/2)
                n_total = len(control_array) + len(treatment_array)
                r_effect_size = abs(z_score) / np.sqrt(n_total)
                
                metric_analysis["statistical_tests"]["mann_whitney"] = StatisticalTestResult(
                    test_name="Mann-Whitney U",
                    statistic=u_stat,
                    p_value=p_value_mw,
                    effect_size=r_effect_size,
                    confidence_interval=(0, 0),  # MWUでは簡単に計算できない
                    is_significant=p_value_mw < alpha,
                    interpretation=self._interpret_mann_whitney(p_value_mw, r_effect_size, alpha)
                )
                
            except Exception as mw_error:
                logger.warning(f"Mann-Whitney test failed for {metric_name}: {mw_error}")
                
            # 3. 実用的有意性判定
            practical_significance = self._assess_practical_significance(
                control_array, treatment_array, metric_name
            )
            metric_analysis["practical_significance"] = practical_significance
            
            return metric_analysis
            
        except Exception as e:
            logger.error(f"Metric analysis failed for {metric_name}: {e}")
            return {"error": str(e)}

    def _interpret_t_test(self, p_value: float, effect_size: float, alpha: float) -> str:
        """t検定結果解釈"""
        if p_value < alpha:
            if abs(effect_size) > 0.8:
                magnitude = "large"
            elif abs(effect_size) > 0.5:
                magnitude = "medium"
            elif abs(effect_size) > 0.2:
                magnitude = "small"
            else:
                magnitude = "negligible"
                
            direction = "positive" if effect_size > 0 else "negative"
            return f"Significant {direction} effect with {magnitude} magnitude (p={p_value:.4f}, d={effect_size:.3f})"
        else:
            return f"No significant effect detected (p={p_value:.4f}, d={effect_size:.3f})"

    def _interpret_mann_whitney(self, p_value: float, effect_size: float, alpha: float) -> str:
        """Mann-Whitney検定結果解釈"""
        if p_value < alpha:
            if effect_size > 0.5:
                magnitude = "large"
            elif effect_size > 0.3:
                magnitude = "medium"
            elif effect_size > 0.1:
                magnitude = "small"
            else:
                magnitude = "negligible"
                
            return f"Significant difference detected with {magnitude} effect size (p={p_value:.4f}, r={effect_size:.3f})"
        else:
            return f"No significant difference detected (p={p_value:.4f}, r={effect_size:.3f})"

    def _assess_practical_significance(
        self, control_values: np.ndarray, treatment_values: np.ndarray, metric_name: str
    ) -> Dict[str, Any]:
        """実用的有意性評価"""
        try:
            control_mean = np.mean(control_values)
            treatment_mean = np.mean(treatment_values)
            
            # 相対変化率
            if control_mean != 0:
                relative_change = (treatment_mean - control_mean) / abs(control_mean)
            else:
                relative_change = 0
                
            # 絶対変化
            absolute_change = treatment_mean - control_mean
            
            # 実用的重要性判定
            practical_thresholds = {
                "accuracy": 0.05,      # 5%改善
                "win_rate": 0.03,      # 3%改善
                "sharpe_ratio": 0.2,   # 0.2改善
                "profit_factor": 0.1,  # 0.1改善
                "default": 0.1         # デフォルト10%改善
            }
            
            threshold = practical_thresholds.get(metric_name, practical_thresholds["default"])
            is_practically_significant = abs(relative_change) >= threshold
            
            return {
                "is_practically_significant": is_practically_significant,
                "relative_change": relative_change,
                "absolute_change": absolute_change,
                "threshold_used": threshold,
                "interpretation": self._get_practical_interpretation(
                    relative_change, is_practically_significant, metric_name
                )
            }
            
        except Exception as e:
            logger.error(f"Practical significance assessment failed: {e}")
            return {"error": str(e)}

    def _get_practical_interpretation(
        self, relative_change: float, is_significant: bool, metric_name: str
    ) -> str:
        """実用的意義解釈"""
        if is_significant:
            direction = "improvement" if relative_change > 0 else "degradation"
            magnitude = abs(relative_change) * 100
            return f"Practically significant {direction} of {magnitude:.1f}% in {metric_name}"
        else:
            return f"No practically significant change in {metric_name} ({relative_change*100:.1f}%)"

    def _generate_analysis_summary(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """分析サマリー生成"""
        try:
            summary = {
                "overall_significance": False,
                "significant_metrics": [],
                "effect_sizes": {},
                "recommendations": []
            }
            
            # 各指標の有意性チェック
            for metric_name, metric_analysis in analysis_results["statistical_tests"].items():
                if isinstance(metric_analysis, dict) and "statistical_tests" in metric_analysis:
                    # t検定結果優先
                    if "t_test" in metric_analysis["statistical_tests"]:
                        test_result = metric_analysis["statistical_tests"]["t_test"]
                        if test_result.is_significant:
                            summary["significant_metrics"].append(metric_name)
                            summary["effect_sizes"][metric_name] = test_result.effect_size
                            
            # 全体的有意性判定
            summary["overall_significance"] = len(summary["significant_metrics"]) > 0
            
            # 推奨事項生成
            if summary["overall_significance"]:
                summary["recommendations"].append("Continue with treatment configuration")
                if any(abs(es) > 0.5 for es in summary["effect_sizes"].values()):
                    summary["recommendations"].append("Strong evidence for treatment superiority")
            else:
                summary["recommendations"].append("No strong evidence for treatment superiority")
                summary["recommendations"].append("Consider extending experiment duration or increasing sample size")
                
            return summary
            
        except Exception as e:
            logger.error(f"Analysis summary generation failed: {e}")
            return {"error": str(e)}

    def _evaluate_early_stopping(self, experiment_id: str, analysis_results: Dict[str, Any]):
        """早期停止判定"""
        try:
            experiment = self.active_experiments[experiment_id]
            summary = analysis_results.get("summary", {})
            
            # 停止条件チェック
            should_stop = False
            stop_reason = ""
            
            # 1. 強い統計的有意性
            if summary.get("overall_significance", False):
                significant_metrics = summary.get("significant_metrics", [])
                effect_sizes = summary.get("effect_sizes", {})
                
                # 主要指標での大きな効果
                primary_significant = any(m in significant_metrics for m in experiment.primary_metrics)
                large_effects = any(abs(es) > 0.8 for es in effect_sizes.values())
                
                if primary_significant and large_effects:
                    should_stop = True
                    stop_reason = "Strong statistical significance with large effect sizes"
                    
            # 2. サンプルサイズ十分性
            total_samples = sum(analysis_results["sample_sizes"].values())
            if total_samples >= experiment.min_sample_size * 3:  # 十分なサンプル
                should_stop = True
                stop_reason = "Sufficient sample size reached"
                
            # 3. 期間制限
            if "started_at" in experiment.metadata:
                start_time = experiment.metadata["started_at"]
                if datetime.now() - start_time > timedelta(days=experiment.max_duration_days):
                    should_stop = True
                    stop_reason = "Maximum experiment duration reached"
                    
            # 早期停止実行
            if should_stop:
                self.stop_experiment(experiment_id, reason=stop_reason)
                
        except Exception as e:
            logger.error(f"Early stopping evaluation failed for {experiment_id}: {e}")

    def stop_experiment(self, experiment_id: str, reason: str = "Manual stop"):
        """実験停止"""
        try:
            if experiment_id not in self.active_experiments:
                return False
                
            experiment = self.active_experiments[experiment_id]
            experiment.metadata["status"] = ExperimentStatus.COMPLETED.value
            experiment.metadata["stopped_at"] = datetime.now()
            experiment.metadata["stop_reason"] = reason
            
            self.ab_stats["active_experiments"] -= 1
            self.ab_stats["completed_experiments"] += 1
            
            # 最終分析実行
            final_analysis = self.analyze_experiment(experiment_id)
            if final_analysis and final_analysis["summary"].get("overall_significance", False):
                self.ab_stats["significant_results"] += 1
                
            logger.info(f"🛑 Stopped experiment: {experiment.name} - Reason: {reason}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop experiment {experiment_id}: {e}")
            return False

    def start_monitoring(self):
        """実験監視開始"""
        try:
            if self.monitoring_active:
                return
                
            self.monitoring_active = True
            self.stop_monitoring.clear()
            
            self.monitor_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True,
                name="ABTestMonitor"
            )
            self.monitor_thread.start()
            
            logger.info("🔍 A/B test monitoring started")
            
        except Exception as e:
            logger.error(f"Failed to start A/B test monitoring: {e}")

    def stop_monitoring(self):
        """実験監視停止"""
        try:
            if not self.monitoring_active:
                return
                
            self.stop_monitoring.set()
            self.monitoring_active = False
            
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=5.0)
                
            logger.info("🛑 A/B test monitoring stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop A/B test monitoring: {e}")

    def _monitoring_loop(self):
        """監視メインループ"""
        try:
            while not self.stop_monitoring.wait(self.monitoring_interval):
                try:
                    self._perform_monitoring_cycle()
                except Exception as e:
                    logger.error(f"Monitoring cycle error: {e}")
        except Exception as e:
            logger.error(f"Monitoring loop failed: {e}")

    def _perform_monitoring_cycle(self):
        """監視サイクル実行"""
        try:
            for experiment_id in list(self.active_experiments.keys()):
                experiment = self.active_experiments[experiment_id]
                
                if experiment.metadata.get("status") == ExperimentStatus.RUNNING.value:
                    # 定期分析実行
                    self._trigger_interim_analysis(experiment_id)
                    
        except Exception as e:
            logger.error(f"Monitoring cycle failed: {e}")

    def get_experiment_status(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """実験ステータス取得"""
        try:
            if experiment_id not in self.active_experiments:
                return None
                
            experiment = self.active_experiments[experiment_id]
            results = list(self.experiment_results[experiment_id])
            
            # グループ別統計
            control_count = sum(1 for r in results if r.group == TreatmentGroup.CONTROL)
            treatment_count = sum(1 for r in results if r.group == TreatmentGroup.TREATMENT)
            
            status = {
                "experiment_id": experiment_id,
                "name": experiment.name,
                "status": experiment.metadata.get("status"),
                "hypothesis": experiment.hypothesis,
                "sample_sizes": {
                    "control": control_count,
                    "treatment": treatment_count,
                    "total": len(results)
                },
                "progress": {
                    "current_samples": len(results),
                    "minimum_required": experiment.min_sample_size,
                    "progress_percentage": min(100, (len(results) / experiment.min_sample_size) * 100)
                },
                "duration": {},
                "latest_analysis": None
            }
            
            # 期間情報
            if "started_at" in experiment.metadata:
                start_time = experiment.metadata["started_at"]
                status["duration"]["days_running"] = (datetime.now() - start_time).days
                status["duration"]["max_days"] = experiment.max_duration_days
                
            # 最新分析結果
            if experiment_id in self.statistical_results:
                latest = self.statistical_results[experiment_id][-1]
                status["latest_analysis"] = {
                    "timestamp": latest["analysis_timestamp"].isoformat(),
                    "significant_metrics": latest["summary"].get("significant_metrics", []),
                    "overall_significant": latest["summary"].get("overall_significance", False)
                }
                
            return status
            
        except Exception as e:
            logger.error(f"Failed to get experiment status for {experiment_id}: {e}")
            return None

    def generate_experiment_report(self, experiment_id: str) -> Optional[str]:
        """実験レポート生成"""
        try:
            if experiment_id not in self.statistical_results:
                return None
                
            experiment = self.active_experiments[experiment_id]
            latest_analysis = self.statistical_results[experiment_id][-1]
            
            report = []
            report.append(f"# A/B Test Experiment Report")
            report.append(f"## Experiment: {experiment.name}")
            report.append(f"**Hypothesis:** {experiment.hypothesis}")
            report.append(f"**Status:** {experiment.metadata.get('status')}")
            report.append("")
            
            # サンプルサイズ
            sample_sizes = latest_analysis["sample_sizes"]
            report.append(f"## Sample Sizes")
            report.append(f"- Control: {sample_sizes['control']}")
            report.append(f"- Treatment: {sample_sizes['treatment']}")
            report.append(f"- Total: {sum(sample_sizes.values())}")
            report.append("")
            
            # 統計結果
            report.append(f"## Statistical Results")
            for metric_name, metric_analysis in latest_analysis["statistical_tests"].items():
                if "statistical_tests" in metric_analysis:
                    report.append(f"### {metric_name}")
                    
                    # 記述統計
                    desc_stats = metric_analysis["descriptive_stats"]
                    report.append(f"**Control:** Mean={desc_stats['control']['mean']:.4f}, "
                                f"SD={desc_stats['control']['std']:.4f}")
                    report.append(f"**Treatment:** Mean={desc_stats['treatment']['mean']:.4f}, "
                                f"SD={desc_stats['treatment']['std']:.4f}")
                    
                    # t検定結果
                    if "t_test" in metric_analysis["statistical_tests"]:
                        t_test = metric_analysis["statistical_tests"]["t_test"]
                        report.append(f"**t-test:** p={t_test.p_value:.4f}, "
                                    f"effect_size={t_test.effect_size:.3f}")
                        report.append(f"*{t_test.interpretation}*")
                        
                    report.append("")
                    
            # サマリー
            summary = latest_analysis["summary"]
            report.append(f"## Summary")
            report.append(f"**Overall Significant:** {summary.get('overall_significance', False)}")
            report.append(f"**Significant Metrics:** {', '.join(summary.get('significant_metrics', []))}")
            report.append("")
            
            # 推奨事項
            recommendations = summary.get("recommendations", [])
            if recommendations:
                report.append(f"## Recommendations")
                for rec in recommendations:
                    report.append(f"- {rec}")
                    
            return "\n".join(report)
            
        except Exception as e:
            logger.error(f"Report generation failed for {experiment_id}: {e}")
            return None

    def create_dynamic_vs_static_experiment(
        self,
        name: str = "Dynamic vs Static Weights",
        traffic_allocation: float = 0.5,
        min_sample_size: int = 200,
        max_duration_days: int = 14
    ) -> str:
        """動的vs固定重み実験作成（Phase C2特化）"""
        try:
            hypothesis = ("Dynamic weight adjustment will outperform static weights "
                        "in terms of accuracy, win rate, and risk-adjusted returns")
            
            control_config = {
                "weight_adjustment_type": "static",
                "use_dynamic_weights": False,
                "base_weights": [0.3, 0.5, 0.2],  # 15m, 1h, 4h
                "confidence_threshold": 0.65
            }
            
            treatment_config = {
                "weight_adjustment_type": "dynamic", 
                "use_dynamic_weights": True,
                "enable_online_learning": True,
                "enable_market_adaptation": True,
                "learning_rate": 0.01
            }
            
            primary_metrics = ["accuracy", "win_rate", "sharpe_ratio"]
            secondary_metrics = ["max_drawdown", "profit_factor", "total_return"]
            
            experiment_id = self.create_experiment(
                name=name,
                description="Comparison of dynamic weight adjustment vs static weights in ensemble trading",
                hypothesis=hypothesis,
                control_config=control_config,
                treatment_config=treatment_config,
                primary_metrics=primary_metrics,
                secondary_metrics=secondary_metrics,
                traffic_allocation=traffic_allocation,
                min_sample_size=min_sample_size,
                max_duration_days=max_duration_days
            )
            
            logger.info(f"🧪 Created dynamic vs static weights experiment: {experiment_id}")
            return experiment_id
            
        except Exception as e:
            logger.error(f"Failed to create dynamic vs static experiment: {e}")
            return ""

    def get_ab_testing_summary(self) -> Dict[str, Any]:
        """A/Bテストサマリー取得"""
        try:
            summary = {
                "timestamp": datetime.now(),
                "system_status": {
                    "ab_testing_enabled": self.enable_ab_testing,
                    "monitoring_active": self.monitoring_active,
                },
                "statistics": self.ab_stats.copy(),
                "active_experiments": [],
                "completed_experiments": []
            }
            
            # 実験詳細
            for exp_id, experiment in self.active_experiments.items():
                exp_status = self.get_experiment_status(exp_id)
                if exp_status:
                    if exp_status["status"] == ExperimentStatus.RUNNING.value:
                        summary["active_experiments"].append(exp_status)
                    elif exp_status["status"] in [ExperimentStatus.COMPLETED.value, ExperimentStatus.STOPPED.value]:
                        summary["completed_experiments"].append(exp_status)
                        
            return summary
            
        except Exception as e:
            logger.error(f"A/B testing summary generation failed: {e}")
            return {"error": str(e)}

    def reset_statistics(self):
        """統計リセット"""
        try:
            for key in self.ab_stats:
                self.ab_stats[key] = 0
                
            self.experiment_results.clear()
            self.statistical_results.clear()
            self.last_analysis_time.clear()
            
            logger.info("📊 A/B testing system statistics reset")
            
        except Exception as e:
            logger.error(f"Statistics reset failed: {e}")


# ファクトリー関数

def create_ab_testing_system(config: Dict[str, Any]) -> ABTestingSystem:
    """
    A/Bテストシステム作成
    
    Parameters:
    -----------
    config : Dict[str, Any]
        設定辞書
        
    Returns:
    --------
    ABTestingSystem
        初期化済みA/Bテストシステム
    """
    return ABTestingSystem(config)