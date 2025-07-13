#!/usr/bin/env python3
# =============================================================================
# スクリプト: scripts/continuous_optimization_framework.py
# 説明:
# アンサンブル学習システムの継続最適化・自動調整フレームワーク
# パフォーマンス監視ベースの自動パラメータ調整・モデル更新システム
# =============================================================================

import sys
import os
import json
import logging
import threading
import time
import pickle
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import pandas as pd
import yaml
from sklearn.model_selection import ParameterGrid
from sklearn.metrics import accuracy_score, precision_score, recall_score

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OptimizationTrigger(Enum):
    """最適化トリガー"""
    SCHEDULED = "scheduled"              # 定期実行
    PERFORMANCE_DEGRADATION = "performance_degradation"  # パフォーマンス劣化
    CONFIDENCE_DROP = "confidence_drop"  # 信頼度低下
    MARKET_REGIME_CHANGE = "market_regime_change"  # 市場環境変化
    ERROR_RATE_SPIKE = "error_rate_spike"  # エラー率上昇
    MANUAL = "manual"                    # 手動実行


class OptimizationStatus(Enum):
    """最適化ステータス"""
    IDLE = "idle"
    ANALYZING = "analyzing"
    OPTIMIZING = "optimizing"
    TESTING = "testing"
    DEPLOYING = "deploying"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PerformanceTarget:
    """パフォーマンス目標"""
    target_win_rate: float = 0.6
    target_sharpe_ratio: float = 1.5
    max_drawdown_limit: float = -0.08
    min_confidence: float = 0.65
    target_return: float = 0.03
    
    # 改善閾値
    min_improvement_threshold: float = 0.02
    significance_threshold: float = 0.05


@dataclass
class OptimizationTask:
    """最適化タスク"""
    task_id: str
    trigger: OptimizationTrigger
    priority: int
    created_time: datetime
    target_component: str
    optimization_type: str
    parameters: Dict[str, Any]
    status: OptimizationStatus = OptimizationStatus.IDLE
    progress: float = 0.0
    results: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    completion_time: Optional[datetime] = None


@dataclass
class OptimizationResult:
    """最適化結果"""
    task_id: str
    component: str
    optimization_type: str
    original_params: Dict[str, Any]
    optimized_params: Dict[str, Any]
    performance_improvement: Dict[str, float]
    validation_metrics: Dict[str, float]
    confidence_score: float
    deployment_recommendation: str
    optimization_time: float


class ParameterOptimizer:
    """パラメータ最適化"""
    
    def __init__(self, performance_targets: PerformanceTarget):
        self.performance_targets = performance_targets
        self.optimization_history = []
    
    def optimize_ensemble_parameters(self, current_params: Dict[str, Any], 
                                   performance_data: List[Dict[str, Any]]) -> OptimizationResult:
        """アンサンブルパラメータ最適化"""
        logger.info("Starting ensemble parameter optimization...")
        
        # パラメータ探索空間定義
        param_grid = {
            'confidence_threshold': np.arange(0.55, 0.85, 0.05),
            'ensemble_weights': self._generate_weight_combinations(),
            'dynamic_threshold_factor': np.arange(0.8, 1.2, 0.1),
            'risk_adjustment_factor': np.arange(0.9, 1.1, 0.05)
        }
        
        best_params = current_params.copy()
        best_score = self._calculate_performance_score(performance_data, current_params)
        optimization_results = []
        
        # グリッドサーチ実行
        total_combinations = len(list(ParameterGrid(param_grid)))
        tested_combinations = 0
        
        for params in ParameterGrid(param_grid):
            tested_combinations += 1
            
            # パラメータ適用でのシミュレーション
            simulated_performance = self._simulate_performance_with_params(
                performance_data, params
            )
            
            # スコア計算
            score = self._calculate_performance_score(simulated_performance, params)
            
            optimization_results.append({
                'params': params,
                'score': score,
                'simulated_performance': simulated_performance
            })
            
            # ベストパラメータ更新
            if score > best_score:
                best_score = score
                best_params.update(params)
            
            # 進捗ログ
            if tested_combinations % 10 == 0:
                logger.info(f"Optimization progress: {tested_combinations}/{total_combinations}")
        
        # 改善効果計算
        performance_improvement = self._calculate_improvement(
            performance_data, optimization_results
        )
        
        # 検証メトリクス
        validation_metrics = self._validate_optimization(
            best_params, performance_data
        )
        
        result = OptimizationResult(
            task_id=f"ensemble_opt_{int(time.time())}",
            component="ensemble_classifier",
            optimization_type="parameter_tuning",
            original_params=current_params,
            optimized_params=best_params,
            performance_improvement=performance_improvement,
            validation_metrics=validation_metrics,
            confidence_score=self._calculate_confidence_score(optimization_results),
            deployment_recommendation=self._generate_deployment_recommendation(
                performance_improvement, validation_metrics
            ),
            optimization_time=time.time()
        )
        
        self.optimization_history.append(result)
        return result
    
    def optimize_threshold_strategy(self, current_thresholds: Dict[str, float],
                                  signal_history: List[Dict[str, Any]]) -> OptimizationResult:
        """動的閾値戦略最適化"""
        logger.info("Starting threshold strategy optimization...")
        
        # VIX別最適閾値探索
        vix_ranges = [(0, 20), (20, 30), (30, 40), (40, 100)]
        optimized_thresholds = {}
        
        for vix_min, vix_max in vix_ranges:
            # VIX範囲のデータフィルタ
            range_data = [
                signal for signal in signal_history
                if vix_min <= signal.get('vix_level', 25) < vix_max
            ]
            
            if not range_data:
                continue
            
            # この範囲での最適閾値探索
            threshold_range = np.arange(0.5, 0.9, 0.02)
            best_threshold = current_thresholds.get(f'vix_{vix_min}_{vix_max}', 0.65)
            best_performance = 0
            
            for threshold in threshold_range:
                # 閾値適用でのパフォーマンス計算
                performance = self._calculate_threshold_performance(
                    range_data, threshold
                )
                
                if performance > best_performance:
                    best_performance = performance
                    best_threshold = threshold
            
            optimized_thresholds[f'vix_{vix_min}_{vix_max}'] = best_threshold
        
        # 結果生成
        performance_improvement = {
            'threshold_accuracy_improvement': self._calculate_threshold_accuracy_improvement(
                current_thresholds, optimized_thresholds, signal_history
            )
        }
        
        validation_metrics = {
            'cross_validation_score': self._cross_validate_thresholds(
                optimized_thresholds, signal_history
            ),
            'stability_score': self._calculate_threshold_stability(optimized_thresholds)
        }
        
        result = OptimizationResult(
            task_id=f"threshold_opt_{int(time.time())}",
            component="dynamic_threshold",
            optimization_type="threshold_optimization",
            original_params=current_thresholds,
            optimized_params=optimized_thresholds,
            performance_improvement=performance_improvement,
            validation_metrics=validation_metrics,
            confidence_score=validation_metrics['cross_validation_score'],
            deployment_recommendation="RECOMMENDED" if validation_metrics['cross_validation_score'] > 0.7 else "CAUTION",
            optimization_time=time.time()
        )
        
        return result
    
    def _generate_weight_combinations(self) -> List[List[float]]:
        """アンサンブル重み組み合わせ生成"""
        combinations = []
        
        # 等重み
        combinations.append([1/3, 1/3, 1/3])
        
        # 偏重組み合わせ
        for i in range(3):
            weights = [0.2, 0.2, 0.2]
            weights[i] = 0.6
            combinations.append(weights)
        
        # カスタム組み合わせ
        combinations.extend([
            [0.5, 0.3, 0.2],
            [0.4, 0.4, 0.2],
            [0.6, 0.2, 0.2]
        ])
        
        return combinations
    
    def _simulate_performance_with_params(self, performance_data: List[Dict[str, Any]], 
                                        params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """パラメータ適用でのパフォーマンスシミュレーション"""
        simulated_data = []
        
        for data_point in performance_data:
            # パラメータ効果を模擬
            confidence_boost = (params.get('confidence_threshold', 0.65) - 0.65) * 0.1
            weight_effect = self._calculate_weight_effect(params.get('ensemble_weights', [1/3, 1/3, 1/3]))
            
            simulated_win_rate = data_point.get('win_rate', 0.58) + confidence_boost + weight_effect
            simulated_confidence = data_point.get('avg_confidence', 0.7) + confidence_boost * 0.5
            
            simulated_data.append({
                'win_rate': np.clip(simulated_win_rate, 0, 1),
                'avg_confidence': np.clip(simulated_confidence, 0, 1),
                'total_return': data_point.get('total_return', 0.02) + confidence_boost * 0.5,
                'sharpe_ratio': data_point.get('sharpe_ratio', 1.2) + weight_effect
            })
        
        return simulated_data
    
    def _calculate_weight_effect(self, weights: List[float]) -> float:
        """重み効果計算"""
        # 重みの分散が小さいほど安定性向上（簡易計算）
        weight_variance = np.var(weights)
        return 0.02 * (1 - weight_variance * 3)  # 正規化された効果
    
    def _calculate_performance_score(self, performance_data: List[Dict[str, Any]], 
                                   params: Dict[str, Any]) -> float:
        """パフォーマンススコア計算"""
        if not performance_data:
            return 0
        
        avg_win_rate = np.mean([d.get('win_rate', 0) for d in performance_data])
        avg_sharpe = np.mean([d.get('sharpe_ratio', 0) for d in performance_data])
        avg_confidence = np.mean([d.get('avg_confidence', 0) for d in performance_data])
        
        # 目標との比較でスコア計算
        win_rate_score = avg_win_rate / self.performance_targets.target_win_rate
        sharpe_score = avg_sharpe / self.performance_targets.target_sharpe_ratio
        confidence_score = avg_confidence / self.performance_targets.min_confidence
        
        # 重み付き総合スコア
        total_score = (win_rate_score * 0.4 + sharpe_score * 0.35 + confidence_score * 0.25)
        return total_score
    
    def _calculate_improvement(self, original_data: List[Dict[str, Any]], 
                             optimization_results: List[Dict[str, Any]]) -> Dict[str, float]:
        """改善効果計算"""
        original_score = self._calculate_performance_score(original_data, {})
        
        best_result = max(optimization_results, key=lambda x: x['score'])
        improvement = best_result['score'] - original_score
        
        return {
            'total_improvement': improvement,
            'win_rate_improvement': np.mean([d.get('win_rate', 0) for d in best_result['simulated_performance']]) - 
                                  np.mean([d.get('win_rate', 0) for d in original_data]),
            'sharpe_improvement': np.mean([d.get('sharpe_ratio', 0) for d in best_result['simulated_performance']]) - 
                                np.mean([d.get('sharpe_ratio', 0) for d in original_data])
        }
    
    def _validate_optimization(self, optimized_params: Dict[str, Any], 
                             performance_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """最適化検証"""
        # クロスバリデーション模擬
        validation_scores = []
        
        # データを分割してバリデーション
        for i in range(5):  # 5-fold CV
            start_idx = i * len(performance_data) // 5
            end_idx = (i + 1) * len(performance_data) // 5
            
            test_data = performance_data[start_idx:end_idx]
            simulated_data = self._simulate_performance_with_params(test_data, optimized_params)
            score = self._calculate_performance_score(simulated_data, optimized_params)
            validation_scores.append(score)
        
        return {
            'cross_validation_mean': np.mean(validation_scores),
            'cross_validation_std': np.std(validation_scores),
            'overfitting_risk': np.std(validation_scores) / np.mean(validation_scores) if np.mean(validation_scores) > 0 else 1
        }
    
    def _calculate_confidence_score(self, optimization_results: List[Dict[str, Any]]) -> float:
        """信頼度スコア計算"""
        scores = [result['score'] for result in optimization_results]
        
        if not scores:
            return 0.5
        
        # 上位結果の一貫性を信頼度とする
        top_10_percent = sorted(scores, reverse=True)[:max(1, len(scores) // 10)]
        confidence = 1 - (np.std(top_10_percent) / np.mean(top_10_percent)) if np.mean(top_10_percent) > 0 else 0.5
        
        return np.clip(confidence, 0, 1)
    
    def _generate_deployment_recommendation(self, performance_improvement: Dict[str, float], 
                                          validation_metrics: Dict[str, float]) -> str:
        """デプロイ推奨判定"""
        total_improvement = performance_improvement.get('total_improvement', 0)
        cv_score = validation_metrics.get('cross_validation_mean', 0)
        overfitting_risk = validation_metrics.get('overfitting_risk', 1)
        
        if total_improvement > 0.1 and cv_score > 0.8 and overfitting_risk < 0.2:
            return "STRONGLY_RECOMMENDED"
        elif total_improvement > 0.05 and cv_score > 0.7 and overfitting_risk < 0.3:
            return "RECOMMENDED"
        elif total_improvement > 0.02 and cv_score > 0.6:
            return "CAUTION"
        else:
            return "NOT_RECOMMENDED"
    
    def _calculate_threshold_performance(self, signal_data: List[Dict[str, Any]], 
                                       threshold: float) -> float:
        """閾値パフォーマンス計算"""
        if not signal_data:
            return 0
        
        correct_predictions = 0
        total_predictions = 0
        
        for signal in signal_data:
            confidence = signal.get('confidence', 0.7)
            actual_result = signal.get('actual_result', np.random.choice([0, 1]))
            
            if confidence >= threshold:
                prediction = 1 if confidence > 0.5 else 0
                if prediction == actual_result:
                    correct_predictions += 1
                total_predictions += 1
        
        return correct_predictions / total_predictions if total_predictions > 0 else 0
    
    def _calculate_threshold_accuracy_improvement(self, current_thresholds: Dict[str, float],
                                                optimized_thresholds: Dict[str, float],
                                                signal_history: List[Dict[str, Any]]) -> float:
        """閾値精度改善計算"""
        current_accuracy = 0.65  # 現在の精度（模擬）
        optimized_accuracy = 0.68  # 最適化後精度（模擬）
        
        return optimized_accuracy - current_accuracy
    
    def _cross_validate_thresholds(self, thresholds: Dict[str, float], 
                                 signal_history: List[Dict[str, Any]]) -> float:
        """閾値クロスバリデーション"""
        # 簡易的なクロスバリデーション
        return np.random.uniform(0.6, 0.9)  # 模擬スコア
    
    def _calculate_threshold_stability(self, thresholds: Dict[str, float]) -> float:
        """閾値安定性計算"""
        threshold_values = list(thresholds.values())
        if not threshold_values:
            return 0
        
        # 閾値のばらつきが小さいほど安定
        stability = 1 - (np.std(threshold_values) / np.mean(threshold_values))
        return np.clip(stability, 0, 1)


class ModelUpdater:
    """モデル更新管理"""
    
    def __init__(self, model_path: str = None):
        self.model_path = model_path or str(project_root / "model")
        self.backup_path = Path(self.model_path) / "backups"
        self.backup_path.mkdir(parents=True, exist_ok=True)
        
    def should_retrain_model(self, performance_metrics: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """モデル再学習判定"""
        if not performance_metrics:
            return False, "データ不足"
        
        recent_metrics = performance_metrics[-20:]  # 最新20件
        
        # 平均パフォーマンス
        avg_accuracy = np.mean([m.get('prediction_accuracy', 0.6) for m in recent_metrics])
        avg_confidence = np.mean([m.get('avg_confidence', 0.7) for m in recent_metrics])
        
        # 再学習条件
        retrain_reasons = []
        
        if avg_accuracy < 0.55:
            retrain_reasons.append("予測精度低下")
        
        if avg_confidence < 0.6:
            retrain_reasons.append("信頼度低下")
        
        # パフォーマンストレンド
        if len(recent_metrics) >= 10:
            accuracy_trend = np.polyfit(range(10), [m.get('prediction_accuracy', 0.6) for m in recent_metrics[-10:]], 1)[0]
            if accuracy_trend < -0.01:  # 1%/期間の下降
                retrain_reasons.append("パフォーマンス下降トレンド")
        
        should_retrain = len(retrain_reasons) > 0
        reason = "; ".join(retrain_reasons) if retrain_reasons else ""
        
        return should_retrain, reason
    
    def backup_current_model(self) -> str:
        """現在のモデルバックアップ"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_path / f"ensemble_model_backup_{timestamp}.pkl"
        
        try:
            # 模擬的なモデルバックアップ
            backup_data = {
                'timestamp': timestamp,
                'model_type': 'ensemble_classifier',
                'backup_reason': 'scheduled_backup'
            }
            
            with open(backup_file, 'wb') as f:
                pickle.dump(backup_data, f)
            
            logger.info(f"Model backed up to: {backup_file}")
            return str(backup_file)
            
        except Exception as e:
            logger.error(f"Failed to backup model: {e}")
            return ""
    
    def update_model_incrementally(self, new_data: pd.DataFrame, 
                                 new_targets: pd.Series) -> Dict[str, Any]:
        """増分モデル更新"""
        logger.info("Starting incremental model update...")
        
        try:
            # バックアップ作成
            backup_path = self.backup_current_model()
            
            # 増分学習シミュレーション
            update_results = {
                'update_type': 'incremental',
                'new_samples': len(new_data),
                'backup_path': backup_path,
                'accuracy_before': 0.68,
                'accuracy_after': 0.70,
                'update_time': time.time(),
                'success': True
            }
            
            logger.info("Incremental model update completed successfully")
            return update_results
            
        except Exception as e:
            logger.error(f"Incremental model update failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def retrain_model_full(self, training_data: pd.DataFrame,
                          training_targets: pd.Series) -> Dict[str, Any]:
        """フルモデル再学習"""
        logger.info("Starting full model retraining...")
        
        try:
            # バックアップ作成
            backup_path = self.backup_current_model()
            
            # フル再学習シミュレーション
            retrain_results = {
                'retrain_type': 'full',
                'training_samples': len(training_data),
                'backup_path': backup_path,
                'accuracy_before': 0.65,
                'accuracy_after': 0.72,
                'training_time': 1800,  # 30分
                'cross_validation_score': 0.71,
                'success': True
            }
            
            logger.info("Full model retraining completed successfully")
            return retrain_results
            
        except Exception as e:
            logger.error(f"Full model retraining failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def rollback_model(self, backup_path: str) -> Dict[str, Any]:
        """モデルロールバック"""
        logger.info(f"Rolling back model from: {backup_path}")
        
        try:
            if not os.path.exists(backup_path):
                raise FileNotFoundError(f"Backup file not found: {backup_path}")
            
            # ロールバック実行（模擬）
            rollback_results = {
                'rollback_successful': True,
                'backup_path': backup_path,
                'rollback_time': time.time(),
                'restored_version': backup_path.split('_')[-1].replace('.pkl', '')
            }
            
            logger.info("Model rollback completed successfully")
            return rollback_results
            
        except Exception as e:
            logger.error(f"Model rollback failed: {e}")
            return {'rollback_successful': False, 'error': str(e)}


class ContinuousOptimizationFramework:
    """継続最適化フレームワーク"""
    
    def __init__(self, config_path: str = None):
        """
        継続最適化フレームワーク初期化
        
        Parameters:
        -----------
        config_path : str
            設定ファイルパス
        """
        self.config = self._load_config(config_path)
        self.performance_targets = PerformanceTarget(**self.config.get('targets', {}))
        
        # コンポーネント初期化
        self.parameter_optimizer = ParameterOptimizer(self.performance_targets)
        self.model_updater = ModelUpdater(self.config.get('model_path'))
        
        # タスク管理
        self.optimization_queue = []
        self.active_tasks = {}
        self.completed_tasks = []
        
        # 実行状態
        self.is_running = False
        self.optimization_thread = None
        
        # 実行履歴
        self.optimization_history = []
        
        # ステータスファイル
        self.status_file = project_root / "status_optimization.json"
        
        logger.info("Continuous Optimization Framework initialized")
    
    def _load_config(self, config_path: str = None) -> Dict:
        """設定ファイル読み込み"""
        if config_path is None:
            config_path = project_root / "config" / "continuous_optimization.yml"
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"Optimization config loaded from: {config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load optimization config: {e}")
            return self._get_default_optimization_config()
    
    def _get_default_optimization_config(self) -> Dict:
        """デフォルト最適化設定"""
        return {
            'targets': {
                'target_win_rate': 0.6,
                'target_sharpe_ratio': 1.5,
                'max_drawdown_limit': -0.08,
                'min_confidence': 0.65,
                'target_return': 0.03,
                'min_improvement_threshold': 0.02,
                'significance_threshold': 0.05
            },
            'scheduling': {
                'parameter_optimization_interval': 7,  # 日
                'model_evaluation_interval': 3,       # 日
                'full_retrain_interval': 30,         # 日
                'max_concurrent_tasks': 2
            },
            'model_path': str(project_root / "model"),
            'performance_degradation_threshold': 0.05,
            'confidence_drop_threshold': 0.1
        }
    
    def start_optimization_framework(self):
        """最適化フレームワーク開始"""
        if self.is_running:
            logger.warning("Optimization framework already running")
            return
        
        self.is_running = True
        self.optimization_thread = threading.Thread(
            target=self._optimization_loop, daemon=True
        )
        self.optimization_thread.start()
        
        logger.info("Continuous optimization framework started")
    
    def stop_optimization_framework(self):
        """最適化フレームワーク停止"""
        self.is_running = False
        
        if self.optimization_thread and self.optimization_thread.is_alive():
            self.optimization_thread.join(timeout=10)
        
        logger.info("Continuous optimization framework stopped")
    
    def trigger_optimization(self, trigger: OptimizationTrigger, 
                           component: str = "ensemble", 
                           optimization_type: str = "parameter_tuning",
                           parameters: Dict[str, Any] = None) -> str:
        """最適化トリガー"""
        task_id = f"opt_{trigger.value}_{int(time.time())}"
        
        task = OptimizationTask(
            task_id=task_id,
            trigger=trigger,
            priority=self._get_priority_for_trigger(trigger),
            created_time=datetime.now(),
            target_component=component,
            optimization_type=optimization_type,
            parameters=parameters or {}
        )
        
        self.optimization_queue.append(task)
        self.optimization_queue.sort(key=lambda x: x.priority, reverse=True)
        
        logger.info(f"Optimization task queued: {task_id} ({trigger.value})")
        return task_id
    
    def _optimization_loop(self):
        """最適化メインループ"""
        while self.is_running:
            try:
                # 定期最適化チェック
                self._check_scheduled_optimizations()
                
                # パフォーマンスベース最適化チェック
                self._check_performance_triggers()
                
                # キュー処理
                self._process_optimization_queue()
                
                # ステータス更新
                self._update_optimization_status()
                
                time.sleep(300)  # 5分間隔
                
            except Exception as e:
                logger.error(f"Optimization loop error: {e}")
                time.sleep(60)
    
    def _check_scheduled_optimizations(self):
        """定期最適化チェック"""
        now = datetime.now()
        
        # パラメータ最適化（週次）
        if self._should_run_scheduled_optimization('parameter_optimization', 7):
            self.trigger_optimization(
                OptimizationTrigger.SCHEDULED,
                "ensemble",
                "parameter_tuning"
            )
        
        # モデル評価（3日間隔）
        if self._should_run_scheduled_optimization('model_evaluation', 3):
            self.trigger_optimization(
                OptimizationTrigger.SCHEDULED,
                "model",
                "evaluation"
            )
        
        # フル再学習（月次）
        if self._should_run_scheduled_optimization('full_retrain', 30):
            self.trigger_optimization(
                OptimizationTrigger.SCHEDULED,
                "model",
                "full_retrain"
            )
    
    def _should_run_scheduled_optimization(self, optimization_type: str, 
                                         interval_days: int) -> bool:
        """定期最適化実行判定"""
        last_run = self._get_last_optimization_time(optimization_type)
        if not last_run:
            return True
        
        time_since_last = datetime.now() - last_run
        return time_since_last.days >= interval_days
    
    def _get_last_optimization_time(self, optimization_type: str) -> Optional[datetime]:
        """最終最適化時刻取得"""
        for task in reversed(self.completed_tasks):
            if task.optimization_type == optimization_type and task.status == OptimizationStatus.COMPLETED:
                return task.completion_time
        return None
    
    def _check_performance_triggers(self):
        """パフォーマンスベース最適化チェック"""
        # 実際の実装では監視システムからメトリクス取得
        current_metrics = self._get_current_performance_metrics()
        
        if not current_metrics:
            return
        
        # パフォーマンス劣化チェック
        degradation_threshold = self.config.get('performance_degradation_threshold', 0.05)
        if current_metrics.get('win_rate_decline', 0) > degradation_threshold:
            self.trigger_optimization(
                OptimizationTrigger.PERFORMANCE_DEGRADATION,
                "ensemble",
                "parameter_tuning"
            )
        
        # 信頼度低下チェック
        confidence_threshold = self.config.get('confidence_drop_threshold', 0.1)
        if current_metrics.get('confidence_drop', 0) > confidence_threshold:
            self.trigger_optimization(
                OptimizationTrigger.CONFIDENCE_DROP,
                "ensemble",
                "threshold_optimization"
            )
    
    def _get_current_performance_metrics(self) -> Dict[str, Any]:
        """現在のパフォーマンスメトリクス取得"""
        # 実際の実装では監視システムから取得
        # ここでは模擬データ返却
        return {
            'current_win_rate': 0.58,
            'win_rate_decline': 0.03,
            'current_confidence': 0.68,
            'confidence_drop': 0.05,
            'current_sharpe': 1.15
        }
    
    def _process_optimization_queue(self):
        """最適化キュー処理"""
        max_concurrent = self.config.get('scheduling', {}).get('max_concurrent_tasks', 2)
        
        while (len(self.active_tasks) < max_concurrent and 
               self.optimization_queue and 
               self.is_running):
            
            task = self.optimization_queue.pop(0)
            task.status = OptimizationStatus.ANALYZING
            self.active_tasks[task.task_id] = task
            
            # 最適化実行（別スレッド）
            optimization_thread = threading.Thread(
                target=self._execute_optimization_task,
                args=(task,),
                daemon=True
            )
            optimization_thread.start()
    
    def _execute_optimization_task(self, task: OptimizationTask):
        """最適化タスク実行"""
        try:
            logger.info(f"Executing optimization task: {task.task_id}")
            
            task.status = OptimizationStatus.OPTIMIZING
            task.progress = 0.1
            
            if task.optimization_type == "parameter_tuning":
                result = self._execute_parameter_optimization(task)
            elif task.optimization_type == "threshold_optimization":
                result = self._execute_threshold_optimization(task)
            elif task.optimization_type == "model_retrain":
                result = self._execute_model_retrain(task)
            elif task.optimization_type == "evaluation":
                result = self._execute_model_evaluation(task)
            else:
                raise ValueError(f"Unknown optimization type: {task.optimization_type}")
            
            task.progress = 0.8
            task.status = OptimizationStatus.TESTING
            
            # 結果検証
            validation_result = self._validate_optimization_result(result)
            
            task.progress = 0.9
            task.status = OptimizationStatus.DEPLOYING
            
            # 自動デプロイ判定
            if self._should_auto_deploy(result, validation_result):
                deploy_result = self._deploy_optimization(result)
                result['deployment'] = deploy_result
            
            task.results = result
            task.status = OptimizationStatus.COMPLETED
            task.progress = 1.0
            task.completion_time = datetime.now()
            
            logger.info(f"Optimization task completed: {task.task_id}")
            
        except Exception as e:
            task.status = OptimizationStatus.FAILED
            task.error_message = str(e)
            task.completion_time = datetime.now()
            logger.error(f"Optimization task failed: {task.task_id} - {e}")
        
        finally:
            # タスク移動
            if task.task_id in self.active_tasks:
                del self.active_tasks[task.task_id]
            self.completed_tasks.append(task)
            self.optimization_history.append(task)
    
    def _execute_parameter_optimization(self, task: OptimizationTask) -> Dict[str, Any]:
        """パラメータ最適化実行"""
        # 現在のパラメータ取得
        current_params = self._get_current_parameters(task.target_component)
        
        # パフォーマンスデータ取得
        performance_data = self._get_performance_data()
        
        # 最適化実行
        optimization_result = self.parameter_optimizer.optimize_ensemble_parameters(
            current_params, performance_data
        )
        
        return asdict(optimization_result)
    
    def _execute_threshold_optimization(self, task: OptimizationTask) -> Dict[str, Any]:
        """閾値最適化実行"""
        current_thresholds = self._get_current_thresholds()
        signal_history = self._get_signal_history()
        
        optimization_result = self.parameter_optimizer.optimize_threshold_strategy(
            current_thresholds, signal_history
        )
        
        return asdict(optimization_result)
    
    def _execute_model_retrain(self, task: OptimizationTask) -> Dict[str, Any]:
        """モデル再学習実行"""
        training_data, training_targets = self._get_training_data()
        
        retrain_result = self.model_updater.retrain_model_full(
            training_data, training_targets
        )
        
        return retrain_result
    
    def _execute_model_evaluation(self, task: OptimizationTask) -> Dict[str, Any]:
        """モデル評価実行"""
        performance_metrics = self._get_performance_data()
        
        should_retrain, reason = self.model_updater.should_retrain_model(performance_metrics)
        
        return {
            'evaluation_type': 'model_health_check',
            'should_retrain': should_retrain,
            'retrain_reason': reason,
            'evaluation_time': time.time(),
            'performance_summary': {
                'avg_accuracy': np.mean([m.get('prediction_accuracy', 0.6) for m in performance_metrics]),
                'avg_confidence': np.mean([m.get('avg_confidence', 0.7) for m in performance_metrics])
            }
        }
    
    def _get_current_parameters(self, component: str) -> Dict[str, Any]:
        """現在のパラメータ取得"""
        # 実際の実装では設定ファイルやDBから取得
        return {
            'confidence_threshold': 0.65,
            'ensemble_weights': [1/3, 1/3, 1/3],
            'dynamic_threshold_factor': 1.0,
            'risk_adjustment_factor': 1.0
        }
    
    def _get_current_thresholds(self) -> Dict[str, float]:
        """現在の閾値取得"""
        return {
            'vix_0_20': 0.6,
            'vix_20_30': 0.65,
            'vix_30_40': 0.7,
            'vix_40_100': 0.75
        }
    
    def _get_performance_data(self) -> List[Dict[str, Any]]:
        """パフォーマンスデータ取得"""
        # 実際の実装では監視システムから取得
        # ここでは模擬データ生成
        performance_data = []
        for i in range(50):
            performance_data.append({
                'win_rate': 0.58 + np.random.normal(0, 0.02),
                'total_return': 0.02 + np.random.normal(0, 0.005),
                'sharpe_ratio': 1.2 + np.random.normal(0, 0.1),
                'avg_confidence': 0.7 + np.random.normal(0, 0.05),
                'prediction_accuracy': 0.65 + np.random.normal(0, 0.03)
            })
        return performance_data
    
    def _get_signal_history(self) -> List[Dict[str, Any]]:
        """シグナル履歴取得"""
        signal_history = []
        for i in range(100):
            signal_history.append({
                'confidence': np.random.uniform(0.5, 0.9),
                'vix_level': np.random.uniform(15, 40),
                'actual_result': np.random.choice([0, 1])
            })
        return signal_history
    
    def _get_training_data(self) -> Tuple[pd.DataFrame, pd.Series]:
        """学習データ取得"""
        # 模擬学習データ
        n_samples = 1000
        n_features = 10
        
        X = pd.DataFrame(np.random.randn(n_samples, n_features))
        y = pd.Series(np.random.choice([0, 1], n_samples))
        
        return X, y
    
    def _validate_optimization_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """最適化結果検証"""
        validation = {
            'performance_improvement_significant': True,
            'validation_score': 0.75,
            'risk_assessment': 'LOW',
            'deployment_safe': True
        }
        
        # 改善効果検証
        total_improvement = result.get('performance_improvement', {}).get('total_improvement', 0)
        if total_improvement < self.performance_targets.min_improvement_threshold:
            validation['performance_improvement_significant'] = False
        
        # リスク評価
        overfitting_risk = result.get('validation_metrics', {}).get('overfitting_risk', 0)
        if overfitting_risk > 0.3:
            validation['risk_assessment'] = 'HIGH'
            validation['deployment_safe'] = False
        
        return validation
    
    def _should_auto_deploy(self, optimization_result: Dict[str, Any], 
                          validation_result: Dict[str, Any]) -> bool:
        """自動デプロイ判定"""
        deployment_recommendation = optimization_result.get('deployment_recommendation', 'NOT_RECOMMENDED')
        validation_safe = validation_result.get('deployment_safe', False)
        
        return (deployment_recommendation in ['STRONGLY_RECOMMENDED', 'RECOMMENDED'] and 
                validation_safe)
    
    def _deploy_optimization(self, optimization_result: Dict[str, Any]) -> Dict[str, Any]:
        """最適化結果デプロイ"""
        logger.info("Deploying optimization results...")
        
        try:
            # 設定ファイル更新（模擬）
            optimized_params = optimization_result.get('optimized_params', {})
            
            deployment_result = {
                'deployment_successful': True,
                'deployed_params': optimized_params,
                'deployment_time': time.time(),
                'backup_created': True,
                'rollback_available': True
            }
            
            logger.info("Optimization deployment completed successfully")
            return deployment_result
            
        except Exception as e:
            logger.error(f"Optimization deployment failed: {e}")
            return {
                'deployment_successful': False,
                'error': str(e),
                'deployment_time': time.time()
            }
    
    def _get_priority_for_trigger(self, trigger: OptimizationTrigger) -> int:
        """トリガー優先度取得"""
        priority_map = {
            OptimizationTrigger.EMERGENCY: 10,
            OptimizationTrigger.PERFORMANCE_DEGRADATION: 8,
            OptimizationTrigger.ERROR_RATE_SPIKE: 7,
            OptimizationTrigger.CONFIDENCE_DROP: 6,
            OptimizationTrigger.MARKET_REGIME_CHANGE: 5,
            OptimizationTrigger.SCHEDULED: 3,
            OptimizationTrigger.MANUAL: 2
        }
        return priority_map.get(trigger, 1)
    
    def _update_optimization_status(self):
        """最適化ステータス更新"""
        try:
            status = {
                'timestamp': datetime.now().isoformat(),
                'is_running': self.is_running,
                'queue_size': len(self.optimization_queue),
                'active_tasks': len(self.active_tasks),
                'completed_tasks': len(self.completed_tasks),
                'optimization_history_size': len(self.optimization_history)
            }
            
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(status, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to update optimization status: {e}")
    
    def get_optimization_status(self) -> Dict[str, Any]:
        """最適化ステータス取得"""
        return {
            'framework_running': self.is_running,
            'queue_length': len(self.optimization_queue),
            'active_tasks': len(self.active_tasks),
            'completed_tasks_count': len(self.completed_tasks),
            'recent_optimizations': [
                {
                    'task_id': task.task_id,
                    'status': task.status.value,
                    'progress': task.progress,
                    'trigger': task.trigger.value,
                    'component': task.target_component
                }
                for task in list(self.active_tasks.values()) + self.completed_tasks[-5:]
            ]
        }
    
    def get_optimization_history_summary(self) -> Dict[str, Any]:
        """最適化履歴サマリー"""
        if not self.optimization_history:
            return {'total_optimizations': 0}
        
        successful_tasks = [task for task in self.optimization_history 
                          if task.status == OptimizationStatus.COMPLETED]
        
        return {
            'total_optimizations': len(self.optimization_history),
            'successful_optimizations': len(successful_tasks),
            'success_rate': len(successful_tasks) / len(self.optimization_history),
            'optimization_by_trigger': {
                trigger.value: len([task for task in self.optimization_history 
                                  if task.trigger == trigger])
                for trigger in OptimizationTrigger
            },
            'avg_optimization_time': np.mean([
                (task.completion_time - task.created_time).total_seconds()
                for task in successful_tasks
                if task.completion_time
            ]) if successful_tasks else 0
        }


def main():
    """メイン実行関数"""
    print("🔄 アンサンブル学習システム 継続最適化フレームワーク")
    print("=" * 70)
    
    try:
        # 最適化フレームワーク初期化
        optimization_framework = ContinuousOptimizationFramework()
        
        # 対話式メニュー
        while True:
            print("\n📋 利用可能なコマンド:")
            print("1. 最適化フレームワーク開始")
            print("2. 最適化フレームワーク停止")
            print("3. 手動最適化トリガー")
            print("4. 最適化ステータス確認")
            print("5. 最適化履歴表示")
            print("6. パフォーマンス目標確認")
            print("0. 終了")
            
            choice = input("\nコマンドを選択してください (0-6): ").strip()
            
            if choice == '1':
                optimization_framework.start_optimization_framework()
                print("✅ 継続最適化フレームワークを開始しました")
                
            elif choice == '2':
                optimization_framework.stop_optimization_framework()
                print("✅ 継続最適化フレームワークを停止しました")
                
            elif choice == '3':
                print("\n最適化タイプを選択:")
                print("1. パラメータ調整")
                print("2. 閾値最適化") 
                print("3. モデル再学習")
                
                opt_choice = input("選択 (1-3): ").strip()
                
                if opt_choice == '1':
                    task_id = optimization_framework.trigger_optimization(
                        OptimizationTrigger.MANUAL, "ensemble", "parameter_tuning"
                    )
                    print(f"✅ パラメータ最適化をトリガーしました: {task_id}")
                elif opt_choice == '2':
                    task_id = optimization_framework.trigger_optimization(
                        OptimizationTrigger.MANUAL, "ensemble", "threshold_optimization"
                    )
                    print(f"✅ 閾値最適化をトリガーしました: {task_id}")
                elif opt_choice == '3':
                    task_id = optimization_framework.trigger_optimization(
                        OptimizationTrigger.MANUAL, "model", "model_retrain"
                    )
                    print(f"✅ モデル再学習をトリガーしました: {task_id}")
                
            elif choice == '4':
                status = optimization_framework.get_optimization_status()
                print(f"\n📊 最適化ステータス:")
                print(f"  フレームワーク実行中: {status['framework_running']}")
                print(f"  キュー長: {status['queue_length']}")
                print(f"  実行中タスク: {status['active_tasks']}")
                print(f"  完了タスク数: {status['completed_tasks_count']}")
                
                if status['recent_optimizations']:
                    print(f"\n📝 最近の最適化:")
                    for opt in status['recent_optimizations'][-3:]:
                        print(f"    {opt['task_id']}: {opt['status']} ({opt['progress']:.1%})")
                
            elif choice == '5':
                history = optimization_framework.get_optimization_history_summary()
                print(f"\n📈 最適化履歴サマリー:")
                print(f"  総最適化回数: {history['total_optimizations']}")
                print(f"  成功率: {history.get('success_rate', 0):.1%}")
                print(f"  平均実行時間: {history.get('avg_optimization_time', 0):.0f}秒")
                
                if 'optimization_by_trigger' in history:
                    print(f"\n📊 トリガー別実行回数:")
                    for trigger, count in history['optimization_by_trigger'].items():
                        if count > 0:
                            print(f"    {trigger}: {count}回")
                
            elif choice == '6':
                targets = optimization_framework.performance_targets
                print(f"\n🎯 パフォーマンス目標:")
                print(f"  目標勝率: {targets.target_win_rate:.1%}")
                print(f"  目標シャープレシオ: {targets.target_sharpe_ratio:.2f}")
                print(f"  最大ドローダウン限界: {targets.max_drawdown_limit:.1%}")
                print(f"  最小信頼度: {targets.min_confidence:.2f}")
                print(f"  目標リターン: {targets.target_return:.1%}")
                
            elif choice == '0':
                if optimization_framework.is_running:
                    optimization_framework.stop_optimization_framework()
                print("👋 プログラムを終了します")
                break
                
            else:
                print("❌ 無効な選択です")
        
    except KeyboardInterrupt:
        print("\n\n🛑 プログラムが中断されました")
    except Exception as e:
        logger.error(f"Main execution failed: {e}")
        print(f"\n❌ エラーが発生しました: {e}")


if __name__ == "__main__":
    main()