#!/usr/bin/env python3
"""
ハイブリッドOptuna最適化システム - Phase 40.5最適化版

3段階最適化戦略（Phase 40.5実行時間最適化済み）:
- Stage 1: シミュレーションベース最適化（750試行・高速・~11秒）
- Stage 2: 軽量バックテスト検証（上位30候補・7日・20%サンプリング・~20分）
- Stage 3: 完全バックテスト検証（上位7候補・90日・100%データ・~2.6時間）

合計実行時間: 約3時間（8時間目標達成）
精度: シミュレーション → 実データ検証の段階的絞り込みにより高精度を実現

Phase 40.5最適化内容:
- サンプリング機能実装（backtest_runner.py）
- Stage 2: 30日10%→7日20%（2倍高速化・候補数50→30）
- Stage 3: 180日→90日（2倍高速化・候補数10→7）
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import optuna
from optuna.samplers import TPESampler
from optuna.trial import Trial

from .backtest_integration import (
    BacktestIntegration,
    create_full_backtest,
    create_lightweight_backtest,
)
from .optuna_utils import OptimizationResultManager, print_optimization_summary


class HybridOptimizer:
    """
    ハイブリッドOptuna最適化オーケストレーター

    3段階最適化プロセスを管理:
    1. シミュレーション（既存実装）: 大量試行で粗い探索
    2. 軽量バックテスト: 有望候補を実データで中間検証
    3. 完全バックテスト: 最終候補を完全実行で精密評価

    利点:
    - 実行時間削減（2.5年 → 8時間）
    - 高精度維持（実バックテスト使用）
    - チェックポイント機能（中断・再開対応）
    """

    def __init__(
        self,
        phase_name: str,
        simulation_objective: Callable,
        param_suggest_func: Callable,
        param_type: str = "risk",
        n_simulation_trials: int = 750,
        n_lightweight_candidates: int = 30,  # Phase 40.5最適化: 50→30（実行時間短縮）
        n_full_candidates: int = 7,  # Phase 40.5最適化: 10→7（実行時間短縮）
        study_name: Optional[str] = None,
        checkpoint_dir: str = "config/optuna_checkpoints",
        verbose: bool = True,
    ):
        """
        ハイブリッド最適化器初期化

        Args:
            phase_name: Phase名（例: "phase40_1_risk_management"）
            simulation_objective: シミュレーション用目的関数
            param_suggest_func: パラメータサジェスト関数
            param_type: パラメータタイプ（"risk", "strategy", "ml_integration", "ml_hyperparams"）
            n_simulation_trials: Stage 1シミュレーション試行数
            n_lightweight_candidates: Stage 2軽量バックテスト候補数
            n_full_candidates: Stage 3完全バックテスト候補数
            study_name: Optunaスタディ名
            checkpoint_dir: チェックポイント保存ディレクトリ
            verbose: 詳細ログ出力
        """
        self.phase_name = phase_name
        self.simulation_objective = simulation_objective
        self.param_suggest_func = param_suggest_func
        self.param_type = param_type
        self.n_simulation_trials = n_simulation_trials
        self.n_lightweight_candidates = n_lightweight_candidates
        self.n_full_candidates = n_full_candidates
        self.study_name = study_name or f"hybrid_{phase_name}"
        self.checkpoint_dir = Path(checkpoint_dir)
        self.verbose = verbose

        # チェックポイントディレクトリ作成
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # 結果マネージャー
        self.result_manager = OptimizationResultManager()

        # Stage別結果保存
        self.stage1_results: Optional[Dict] = None
        self.stage2_results: Optional[List[Dict]] = None
        self.stage3_results: Optional[List[Dict]] = None

    def run(self) -> Dict[str, Any]:
        """
        3段階ハイブリッド最適化実行

        Returns:
            Dict: 最適化結果
        """
        print("\n" + "=" * 80)
        print(f"🎯 {self.phase_name} ハイブリッド最適化開始")
        print("=" * 80)

        total_start_time = time.time()

        try:
            # Stage 1: シミュレーションベース最適化
            print("\n" + "-" * 80)
            print("📊 Stage 1: シミュレーションベース最適化")
            print("-" * 80)
            stage1_result = self._run_stage1_simulation()

            # Stage 2: 軽量バックテスト検証
            print("\n" + "-" * 80)
            print("🔬 Stage 2: 軽量バックテスト検証（上位50候補）")
            print("-" * 80)
            stage2_results = self._run_stage2_lightweight(stage1_result)

            # Stage 3: 完全バックテスト検証
            print("\n" + "-" * 80)
            print("🏆 Stage 3: 完全バックテスト検証（上位10候補）")
            print("-" * 80)
            stage3_results = self._run_stage3_full(stage2_results)

            # 最終結果選択
            best_result = self._select_best_result(stage3_results)

            # 実行時間計算
            total_duration = time.time() - total_start_time

            # 最終結果保存
            final_result = {
                "phase": self.phase_name,
                "created_at": datetime.now().isoformat(),
                "best_params": best_result["params"],
                "best_value": best_result["sharpe_ratio"],
                "optimization_method": "hybrid_3stage",
                "stage1_trials": self.n_simulation_trials,
                "stage2_candidates": len(stage2_results),
                "stage3_candidates": len(stage3_results),
                "total_duration_seconds": total_duration,
            }

            # 結果保存
            self.result_manager.save_results(
                phase_name=f"{self.phase_name}_hybrid",
                best_params=best_result["params"],
                best_value=best_result["sharpe_ratio"],
                study_stats={
                    "total_duration_seconds": total_duration,
                    "stage1_trials": self.n_simulation_trials,
                    "stage2_candidates": len(stage2_results),
                    "stage3_candidates": len(stage3_results),
                },
            )

            # 最終サマリー表示
            self._print_final_summary(final_result, total_duration)

            return final_result

        except Exception as e:
            print(f"\n❌ ハイブリッド最適化エラー: {e}")
            raise

    def _run_stage1_simulation(self) -> Dict[str, Any]:
        """
        Stage 1: シミュレーションベース最適化実行

        Returns:
            Dict: Stage 1結果（Study object含む）
        """
        start_time = time.time()

        # Optunaスタディ作成
        study = optuna.create_study(
            direction="maximize",
            sampler=TPESampler(seed=42),
            study_name=f"{self.study_name}_stage1",
        )

        # 最適化実行
        # Phase 40.5バグ修正: show_progress_bar=TrueでTrial 113ハング問題対策
        def logging_callback(study, trial):
            if trial.number % 50 == 0 or trial.number < 5:
                print(
                    f"Trial {trial.number}/{self.n_simulation_trials} "
                    f"完了: value={trial.value:.4f}, best={study.best_value:.4f}"
                )

        study.optimize(
            self.simulation_objective,
            n_trials=self.n_simulation_trials,
            show_progress_bar=False,
            callbacks=[logging_callback],
        )

        duration = time.time() - start_time

        # 結果サマリー表示
        print_optimization_summary(study, f"{self.phase_name} - Stage 1", duration)

        # 上位候補抽出
        top_trials = sorted(study.trials, key=lambda t: t.value, reverse=True)[
            : self.n_lightweight_candidates
        ]

        result = {
            "study": study,
            "best_params": study.best_params,
            "best_value": study.best_value,
            "top_trials": top_trials,
            "duration_seconds": duration,
        }

        # チェックポイント保存
        self._save_checkpoint("stage1", result)
        self.stage1_results = result

        return result

    def _run_stage2_lightweight(self, stage1_result: Dict) -> List[Dict]:
        """
        Stage 2: 軽量バックテスト検証

        Args:
            stage1_result: Stage 1結果

        Returns:
            List[Dict]: Stage 2検証結果リスト
        """
        start_time = time.time()

        # 軽量バックテスト作成（30日・10%サンプリング）
        backtest = create_lightweight_backtest()

        # 上位候補を軽量バックテストで検証
        results = []

        for i, trial in enumerate(stage1_result["top_trials"]):
            print(
                f"\n🔬 軽量バックテスト {i + 1}/{len(stage1_result['top_trials'])} "
                f"(シミュレーションスコア: {trial.value:.4f})"
            )

            # 非同期バックテスト実行
            sharpe_ratio = asyncio.run(
                backtest.run_backtest_with_params(trial.params, param_type=self.param_type)
            )

            result = {
                "trial_number": trial.number,
                "params": trial.params,
                "simulation_score": trial.value,
                "sharpe_ratio": sharpe_ratio,
            }

            results.append(result)

            print(f"  シャープレシオ: {sharpe_ratio:.4f}")

        # シャープレシオでソート
        results_sorted = sorted(results, key=lambda r: r["sharpe_ratio"], reverse=True)

        duration = time.time() - start_time

        # Stage 2サマリー表示
        self._print_stage2_summary(results_sorted, duration)

        # チェックポイント保存
        self._save_checkpoint("stage2", results_sorted)
        self.stage2_results = results_sorted

        return results_sorted

    def _run_stage3_full(self, stage2_results: List[Dict]) -> List[Dict]:
        """
        Stage 3: 完全バックテスト検証

        Args:
            stage2_results: Stage 2結果

        Returns:
            List[Dict]: Stage 3検証結果リスト
        """
        start_time = time.time()

        # 完全バックテスト作成（180日・100%データ）
        backtest = create_full_backtest()

        # 上位候補を完全バックテストで検証
        top_candidates = stage2_results[: self.n_full_candidates]
        results = []

        for i, candidate in enumerate(top_candidates):
            print(
                f"\n🏆 完全バックテスト {i + 1}/{len(top_candidates)} "
                f"(Stage2シャープレシオ: {candidate['sharpe_ratio']:.4f})"
            )

            # 非同期バックテスト実行
            sharpe_ratio = asyncio.run(
                backtest.run_backtest_with_params(candidate["params"], param_type=self.param_type)
            )

            result = {
                "params": candidate["params"],
                "simulation_score": candidate["simulation_score"],
                "stage2_sharpe": candidate["sharpe_ratio"],
                "stage3_sharpe": sharpe_ratio,
                "final_sharpe": sharpe_ratio,  # 最終評価値
            }

            results.append(result)

            print(f"  最終シャープレシオ: {sharpe_ratio:.4f}")

        # 最終シャープレシオでソート
        results_sorted = sorted(results, key=lambda r: r["final_sharpe"], reverse=True)

        duration = time.time() - start_time

        # Stage 3サマリー表示
        self._print_stage3_summary(results_sorted, duration)

        # チェックポイント保存
        self._save_checkpoint("stage3", results_sorted)
        self.stage3_results = results_sorted

        return results_sorted

    def _select_best_result(self, stage3_results: List[Dict]) -> Dict:
        """
        最終結果選択（Stage 3最高スコア）

        Args:
            stage3_results: Stage 3結果リスト

        Returns:
            Dict: 最適結果
        """
        best_result = stage3_results[0]  # すでにソート済み

        return {
            "params": best_result["params"],
            "sharpe_ratio": best_result["final_sharpe"],
            "simulation_score": best_result["simulation_score"],
            "stage2_sharpe": best_result["stage2_sharpe"],
            "stage3_sharpe": best_result["stage3_sharpe"],
        }

    def _save_checkpoint(self, stage: str, data: Any) -> None:
        """
        チェックポイント保存

        Args:
            stage: ステージ名
            data: 保存データ
        """
        checkpoint_path = self.checkpoint_dir / f"{self.phase_name}_{stage}.json"

        # Study objectは保存できないので除外
        if isinstance(data, dict) and "study" in data:
            data = {k: v for k, v in data.items() if k != "study"}

        # Trial objectをdict化
        if isinstance(data, dict) and "top_trials" in data:
            data["top_trials"] = [
                {"number": t.number, "value": t.value, "params": t.params}
                for t in data["top_trials"]
            ]

        with open(checkpoint_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        if self.verbose:
            print(f"💾 チェックポイント保存: {checkpoint_path}")

    def _print_stage2_summary(self, results: List[Dict], duration: float) -> None:
        """Stage 2サマリー表示"""
        print("\n" + "=" * 80)
        print("📊 Stage 2 完了: 軽量バックテスト検証")
        print("=" * 80)

        print(f"\n⏱️  実行時間: {duration:.1f}秒 ({duration / 60:.1f}分)")
        print(f"🔢 検証候補数: {len(results)}")
        print(f"\n🏆 上位3候補:")

        for i, result in enumerate(results[:3]):
            print(f"\n  {i + 1}位: シャープレシオ = {result['sharpe_ratio']:.4f}")
            print(f"      シミュレーションスコア = {result['simulation_score']:.4f}")

    def _print_stage3_summary(self, results: List[Dict], duration: float) -> None:
        """Stage 3サマリー表示"""
        print("\n" + "=" * 80)
        print("📊 Stage 3 完了: 完全バックテスト検証")
        print("=" * 80)

        print(f"\n⏱️  実行時間: {duration:.1f}秒 ({duration / 60:.1f}分, {duration / 3600:.1f}時間)")
        print(f"🔢 検証候補数: {len(results)}")
        print(f"\n🏆 最終上位3候補:")

        for i, result in enumerate(results[:3]):
            print(f"\n  {i + 1}位: 最終シャープレシオ = {result['final_sharpe']:.4f}")
            print(f"      Stage2 = {result['stage2_sharpe']:.4f}")
            print(f"      シミュレーション = {result['simulation_score']:.4f}")

    def _print_final_summary(self, result: Dict, total_duration: float) -> None:
        """最終サマリー表示"""
        print("\n" + "=" * 80)
        print(f"🎉 {self.phase_name} ハイブリッド最適化完了")
        print("=" * 80)

        print(f"\n⏱️  総実行時間: {total_duration / 3600:.2f}時間")
        print(f"📊 最終シャープレシオ: {result['best_value']:.4f}")

        print(f"\n🎯 最適パラメータ:")
        for key, value in result["best_params"].items():
            if isinstance(value, float):
                print(f"  - {key}: {value:.6f}")
            else:
                print(f"  - {key}: {value}")

        print(f"\n📈 最適化プロセス:")
        print(f"  - Stage 1: {result['stage1_trials']}試行（シミュレーション）")
        print(f"  - Stage 2: {result['stage2_candidates']}候補（軽量バックテスト）")
        print(f"  - Stage 3: {result['stage3_candidates']}候補（完全バックテスト）")

        print("\n" + "=" * 80)


# テスト実行用メイン関数
if __name__ == "__main__":
    print("HybridOptimizer単体テストは各最適化スクリプト経由で実行してください")
    print("例: python3 scripts/optimization/optimize_risk_management.py --use-hybrid-backtest")
