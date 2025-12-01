#!/usr/bin/env python3
"""
Phase 57.4: 戦略パラメータ最適化スクリプト

ATRBased戦略のパラメータをOptunaで最適化:
- 目標: 勝率とプロフィットファクターの向上
- 軽量バックテスト（7日間）で高速探索
- 最適パラメータをconfig/optimization/results/に保存
"""

import asyncio
import sys
from pathlib import Path

# プロジェクトルートをパス追加
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import optuna
from optuna.samplers import TPESampler

from scripts.optimization.backtest_integration import BacktestIntegration
from scripts.optimization.optuna_utils import OptimizationResultManager, print_optimization_summary


class ATRBasedOptimizer:
    """ATRBased戦略のパラメータ最適化クラス"""

    def __init__(self, n_trials: int = 10, period_days: int = 7, verbose: bool = True):
        """
        初期化

        Args:
            n_trials: 試行回数
            period_days: バックテスト期間（日数）
            verbose: 詳細ログ出力
        """
        self.n_trials = n_trials
        self.period_days = period_days
        self.verbose = verbose

        # バックテスト統合（軽量モード）
        self.backtest = BacktestIntegration(
            period_days=period_days,
            data_sampling_ratio=1.0,  # 100%データ使用（期間が短いため）
            use_lightweight=True,
            verbose=verbose,
        )

        # 結果マネージャー
        self.result_manager = OptimizationResultManager()

    def create_objective(self):
        """Optuna目的関数を作成"""

        async def objective_async(trial: optuna.Trial) -> float:
            """非同期目的関数"""
            # ATRBased戦略パラメータのサンプリング
            params = {
                # ボラティリティベースの信頼度
                "atr_high_vol_base": trial.suggest_float("atr_high_vol_base", 0.4, 0.8),
                "atr_normal_vol_base": trial.suggest_float("atr_normal_vol_base", 0.5, 0.9),
                "atr_low_vol_base": trial.suggest_float("atr_low_vol_base", 0.3, 0.7),
                # RSI閾値
                "atr_rsi_overbought": trial.suggest_int("atr_rsi_overbought", 65, 80),
                "atr_rsi_oversold": trial.suggest_int("atr_rsi_oversold", 20, 35),
                # BB閾値
                "atr_bb_overbought": trial.suggest_float("atr_bb_overbought", 0.7, 0.95),
                "atr_bb_oversold": trial.suggest_float("atr_bb_oversold", 0.05, 0.3),
            }

            # バックテスト実行
            sharpe_ratio = await self.backtest.run_backtest_with_params(
                params, param_type="strategy"
            )

            return sharpe_ratio

        def objective(trial: optuna.Trial) -> float:
            """同期ラッパー"""
            return asyncio.run(objective_async(trial))

        return objective

    def optimize(self) -> optuna.Study:
        """最適化実行"""
        import time

        print("=" * 80)
        print("🎯 Phase 57.4: ATRBased戦略パラメータ最適化")
        print("=" * 80)
        print(f"  試行回数: {self.n_trials}")
        print(f"  バックテスト期間: {self.period_days}日")
        print("=" * 80)

        start_time = time.time()

        # Optuna Study作成（最大化）
        study = optuna.create_study(
            direction="maximize",
            sampler=TPESampler(seed=42),
            study_name="phase57_atr_based_optimization",
        )

        # 最適化実行
        study.optimize(
            self.create_objective(),
            n_trials=self.n_trials,
            show_progress_bar=True,
        )

        duration_seconds = time.time() - start_time

        # 結果表示
        print_optimization_summary(study, "Phase 57.4: ATRBased戦略最適化", duration_seconds)

        # 結果保存
        study_stats = {
            "n_trials": len(study.trials),
            "n_complete": len([t for t in study.trials if t.state.name == "COMPLETE"]),
            "n_fail": len([t for t in study.trials if t.state.name == "FAIL"]),
            "duration_seconds": duration_seconds,
        }

        filepath = self.result_manager.save_results(
            phase_name="phase57_4_atr_based_optimization",
            best_params=study.best_params,
            best_value=study.best_value,
            study_stats=study_stats,
        )

        print(f"\n💾 結果保存先: {filepath}")

        return study


def main():
    """メイン関数"""
    import argparse

    parser = argparse.ArgumentParser(description="Phase 57.4: ATRBased戦略最適化")
    parser.add_argument("--trials", type=int, default=5, help="試行回数（デフォルト: 5）")
    parser.add_argument("--days", type=int, default=7, help="バックテスト期間（デフォルト: 7日）")
    parser.add_argument("--verbose", action="store_true", help="詳細ログ出力")
    args = parser.parse_args()

    optimizer = ATRBasedOptimizer(
        n_trials=args.trials,
        period_days=args.days,
        verbose=args.verbose,
    )

    study = optimizer.optimize()

    # 最終結果表示
    print("\n" + "=" * 80)
    print("📋 最終レポート")
    print("=" * 80)
    print(f"  最適シャープレシオ: {study.best_value:.4f}")
    print("  最適パラメータ:")
    for key, value in study.best_params.items():
        if isinstance(value, float):
            print(f"    {key}: {value:.4f}")
        else:
            print(f"    {key}: {value}")
    print("=" * 80)


if __name__ == "__main__":
    main()
