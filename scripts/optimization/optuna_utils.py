#!/usr/bin/env python3
"""
Optuna最適化共通ユーティリティ - Phase 40

Phase 40全体で使用する共通機能を提供：
- Walk-forward testing実装
- シャープレシオ計算
- 最適化結果の保存・読み込み
- バックテスト実行ヘルパー
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


class OptimizationMetrics:
    """最適化用メトリクス計算クラス"""

    @staticmethod
    def calculate_sharpe_ratio(returns: np.ndarray, risk_free_rate: float = 0.0) -> float:
        """
        シャープレシオ計算

        Args:
            returns: リターン配列
            risk_free_rate: リスクフリーレート（年率）

        Returns:
            float: シャープレシオ
        """
        if len(returns) == 0:
            return 0.0

        # 平均リターン
        mean_return = np.mean(returns)

        # リターンの標準偏差
        std_return = np.std(returns, ddof=1)

        if std_return == 0:
            return 0.0

        # シャープレシオ
        sharpe = (mean_return - risk_free_rate) / std_return

        # 年率換算（日次リターンの場合、sqrt(365)で年率化）
        sharpe_annualized = sharpe * np.sqrt(365)

        return float(sharpe_annualized)

    @staticmethod
    def calculate_max_drawdown(equity_curve: np.ndarray) -> float:
        """
        最大ドローダウン計算

        Args:
            equity_curve: 資産曲線

        Returns:
            float: 最大ドローダウン（負の値）
        """
        if len(equity_curve) == 0:
            return 0.0

        # 累積最大値
        cummax = np.maximum.accumulate(equity_curve)

        # ドローダウン計算
        drawdowns = (equity_curve - cummax) / cummax

        # 最大ドローダウン
        max_dd = np.min(drawdowns)

        return float(max_dd)

    @staticmethod
    def calculate_win_rate(trades: List[Dict[str, Any]]) -> float:
        """
        勝率計算

        Args:
            trades: 取引履歴リスト

        Returns:
            float: 勝率（0-1）
        """
        if len(trades) == 0:
            return 0.0

        wins = sum(1 for trade in trades if trade.get("profit", 0) > 0)
        return wins / len(trades)

    @staticmethod
    def calculate_profit_factor(trades: List[Dict[str, Any]]) -> float:
        """
        プロフィットファクター計算

        Args:
            trades: 取引履歴リスト

        Returns:
            float: プロフィットファクター
        """
        if len(trades) == 0:
            return 0.0

        gross_profit = sum(trade.get("profit", 0) for trade in trades if trade.get("profit", 0) > 0)
        gross_loss = abs(
            sum(trade.get("profit", 0) for trade in trades if trade.get("profit", 0) < 0)
        )

        if gross_loss == 0:
            return float("inf") if gross_profit > 0 else 0.0

        return gross_profit / gross_loss


class WalkForwardTester:
    """Walk-forward testing実装クラス"""

    def __init__(
        self,
        data: pd.DataFrame,
        train_days: int = 120,
        test_days: int = 60,
        step_days: int = 30,
    ):
        """
        Walk-forward tester初期化

        Args:
            data: 全データ（DatetimeIndex必須）
            train_days: 訓練期間（日数）
            test_days: テスト期間（日数）
            step_days: ステップサイズ（日数）
        """
        self.data = data
        self.train_days = train_days
        self.test_days = test_days
        self.step_days = step_days

    def generate_splits(self) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """
        Walk-forward splits生成

        Returns:
            List[Tuple]: (train_data, test_data)のリスト
        """
        splits = []

        # データ範囲
        start_date = self.data.index.min()
        end_date = self.data.index.max()

        # 初期訓練開始日
        train_start = start_date

        while True:
            # 訓練終了日
            train_end = train_start + timedelta(days=self.train_days)

            # テスト開始日
            test_start = train_end
            test_end = test_start + timedelta(days=self.test_days)

            # データ範囲チェック
            if test_end > end_date:
                break

            # データ分割
            train_data = self.data[(self.data.index >= train_start) & (self.data.index < train_end)]
            test_data = self.data[(self.data.index >= test_start) & (self.data.index < test_end)]

            if len(train_data) > 0 and len(test_data) > 0:
                splits.append((train_data, test_data))

            # 次のステップへ
            train_start += timedelta(days=self.step_days)

        return splits


class OptimizationResultManager:
    """最適化結果の保存・読み込みマネージャー"""

    def __init__(self, results_dir: str = "config/optimization/results"):
        """
        結果マネージャー初期化

        Args:
            results_dir: 結果保存ディレクトリ
        """
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def save_results(
        self,
        phase_name: str,
        best_params: Dict[str, Any],
        best_value: float,
        study_stats: Dict[str, Any],
    ) -> Path:
        """
        最適化結果保存

        Args:
            phase_name: Phase名（例: "phase40_1_risk_management"）
            best_params: 最適パラメータ
            best_value: 最適値（シャープレシオ等）
            study_stats: Study統計情報

        Returns:
            Path: 保存先ファイルパス
        """
        results = {
            "phase": phase_name,
            "created_at": datetime.now().isoformat(),
            "best_params": best_params,
            "best_value": float(best_value),
            "study_stats": study_stats,
        }

        filepath = self.results_dir / f"{phase_name}.json"

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        return filepath

    def load_results(self, phase_name: str) -> Optional[Dict[str, Any]]:
        """
        最適化結果読み込み

        Args:
            phase_name: Phase名

        Returns:
            Dict: 最適化結果、存在しない場合None
        """
        filepath = self.results_dir / f"{phase_name}.json"

        if not filepath.exists():
            return None

        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)


def print_optimization_summary(
    study,
    phase_name: str,
    duration_seconds: float,
):
    """
    最適化サマリー表示

    Args:
        study: Optuna Study
        phase_name: Phase名
        duration_seconds: 実行時間（秒）
    """
    print("\n" + "=" * 80)
    print(f"🎯 {phase_name} 最適化完了")
    print("=" * 80)

    print(f"\n⏱️  実行時間: {duration_seconds:.1f}秒 ({duration_seconds / 60:.1f}分)")
    print(f"🔢 試行回数: {len(study.trials)}")
    print(f"✅ 完了試行: {len([t for t in study.trials if t.state.name == 'COMPLETE'])}")
    print(f"❌ 失敗試行: {len([t for t in study.trials if t.state.name == 'FAIL'])}")

    print(f"\n📊 最適値（シャープレシオ）: {study.best_value:.4f}")
    print("\n🎯 最適パラメータ:")
    for key, value in study.best_params.items():
        if isinstance(value, float):
            print(f"  - {key}: {value:.6f}")
        else:
            print(f"  - {key}: {value}")

    print("\n" + "=" * 80)
