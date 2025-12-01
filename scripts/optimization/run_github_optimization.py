#!/usr/bin/env python3
"""
GitHub Actions用Optuna最適化統合スクリプト
Phase 57.6: 3段階ハイブリッド最適化

使用方法:
  python scripts/optimization/run_github_optimization.py \
    --type hybrid \
    --n-trials 50 \
    --backtest-days 90

最適化タイプ:
  - hybrid: 全パラメータ3段階最適化（リスク + ML統合 + 戦略）
  - risk: リスク管理パラメータのみ
  - ml_integration: ML統合パラメータのみ
  - strategy: 戦略パラメータのみ
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.logger import get_logger

logger = get_logger(__name__)


class GitHubOptimizationRunner:
    """GitHub Actions用最適化実行クラス"""

    def __init__(
        self,
        optimization_type: str = "hybrid",
        n_trials: int = 50,
        backtest_days: int = 90,
        timeout_seconds: int = 19800,
        verbose: bool = True,
    ):
        """
        初期化

        Args:
            optimization_type: 最適化タイプ（hybrid/risk/ml_integration/strategy）
            n_trials: 試行回数
            backtest_days: バックテスト日数
            timeout_seconds: タイムアウト（秒）
            verbose: 詳細ログ出力
        """
        self.optimization_type = optimization_type
        self.n_trials = n_trials
        self.backtest_days = backtest_days
        self.timeout_seconds = timeout_seconds
        self.verbose = verbose

        self.results_dir = PROJECT_ROOT / "config" / "optimization" / "results"
        self.results_dir.mkdir(parents=True, exist_ok=True)

        self.start_time = None
        self.best_params = {}
        self.best_sharpe = -999.0

    def run(self) -> Dict[str, Any]:
        """
        最適化実行

        Returns:
            Dict: 最適化結果
        """
        self.start_time = time.time()

        logger.info("=" * 60)
        logger.info("🚀 GitHub Actions Optuna最適化開始")
        logger.info(f"   タイプ: {self.optimization_type}")
        logger.info(f"   試行数: {self.n_trials}")
        logger.info(f"   バックテスト日数: {self.backtest_days}")
        logger.info(f"   タイムアウト: {self.timeout_seconds}秒")
        logger.info("=" * 60)

        try:
            if self.optimization_type == "hybrid":
                result = self._run_hybrid_optimization()
            elif self.optimization_type == "risk":
                result = self._run_risk_optimization()
            elif self.optimization_type == "ml_integration":
                result = self._run_ml_integration_optimization()
            elif self.optimization_type == "strategy":
                result = self._run_strategy_optimization()
            else:
                raise ValueError(f"Unknown optimization type: {self.optimization_type}")

            # 結果保存
            self._save_results(result)

            return result

        except Exception as e:
            logger.error(f"❌ 最適化エラー: {e}")
            raise

    def _run_hybrid_optimization(self) -> Dict[str, Any]:
        """
        ハイブリッド最適化（3段階）

        Stage 1: シミュレーション（高速スクリーニング）
        Stage 2: 軽量バックテスト（7日間）
        Stage 3: フルバックテスト（指定日数）
        """
        logger.info("🔵 Stage 1: シミュレーション最適化")

        # Stage 1: 各最適化器のシミュレーション実行
        risk_result = self._run_risk_optimization(mode="simulation")
        ml_result = self._run_ml_integration_optimization(mode="simulation")
        strategy_result = self._run_strategy_optimization(mode="simulation")

        # 最良パラメータを統合
        combined_params = {}
        combined_params.update(risk_result.get("best_params", {}))
        combined_params.update(ml_result.get("best_params", {}))
        combined_params.update(strategy_result.get("best_params", {}))

        logger.info("🟡 Stage 2: 軽量バックテスト検証")

        # Stage 2: 軽量バックテスト（7日間）
        lightweight_sharpe = self._run_lightweight_backtest(combined_params)

        logger.info("🟢 Stage 3: フルバックテスト検証")

        # Stage 3: フルバックテスト（指定日数）
        final_sharpe = self._run_full_backtest(combined_params)

        return {
            "best_params": combined_params,
            "sharpe_ratio": final_sharpe,
            "lightweight_sharpe": lightweight_sharpe,
            "optimization_type": "hybrid",
            "stage_results": {
                "risk": risk_result,
                "ml_integration": ml_result,
                "strategy": strategy_result,
            },
        }

    def _run_risk_optimization(self, mode: str = "full") -> Dict[str, Any]:
        """リスク管理パラメータ最適化"""
        logger.info("🔧 リスク管理パラメータ最適化")

        try:
            from scripts.optimization.optimize_risk_management import RiskManagementOptimizer

            optimizer = RiskManagementOptimizer()

            if mode == "simulation":
                result = optimizer.optimize(n_trials=min(self.n_trials, 100), timeout=1800)
            else:
                result = optimizer.optimize(n_trials=self.n_trials, timeout=self.timeout_seconds)

            return {
                "best_params": result.get("best_params", {}),
                "best_value": result.get("best_value", 0.0),
            }

        except Exception as e:
            logger.warning(f"⚠️ リスク最適化スキップ: {e}")
            return {"best_params": {}, "best_value": 0.0}

    def _run_ml_integration_optimization(self, mode: str = "full") -> Dict[str, Any]:
        """ML統合パラメータ最適化"""
        logger.info("🔧 ML統合パラメータ最適化")

        try:
            from scripts.optimization.optimize_ml_integration import MLIntegrationOptimizer

            optimizer = MLIntegrationOptimizer()

            if mode == "simulation":
                result = optimizer.optimize(n_trials=min(self.n_trials, 100), timeout=1800)
            else:
                result = optimizer.optimize(n_trials=self.n_trials, timeout=self.timeout_seconds)

            return {
                "best_params": result.get("best_params", {}),
                "best_value": result.get("best_value", 0.0),
            }

        except Exception as e:
            logger.warning(f"⚠️ ML統合最適化スキップ: {e}")
            return {"best_params": {}, "best_value": 0.0}

    def _run_strategy_optimization(self, mode: str = "full") -> Dict[str, Any]:
        """戦略パラメータ最適化（6戦略対応版）"""
        logger.info("🔧 6戦略パラメータ最適化")

        try:
            from scripts.optimization.optimize_strategy_parameters_v2 import (
                StrategyParameterOptimizerV2,
            )

            optimizer = StrategyParameterOptimizerV2(verbose=self.verbose)

            if mode == "simulation":
                result = optimizer.optimize(n_trials=min(self.n_trials, 200), timeout=3600)
            else:
                result = optimizer.optimize(n_trials=self.n_trials, timeout=self.timeout_seconds)

            return {
                "best_params": result.get("best_params", {}),
                "best_value": result.get("best_value", 0.0),
            }

        except Exception as e:
            logger.warning(f"⚠️ 戦略最適化スキップ: {e}")
            return {"best_params": {}, "best_value": 0.0}

    def _run_lightweight_backtest(self, params: Dict[str, Any]) -> float:
        """
        軽量バックテスト実行（7日間×100%）

        Phase 57.7: サンプリングなしで十分な取引数を確保
        - 7日間 × 100%データ → 約4分/試行、約25-30取引
        """
        try:
            import asyncio

            from scripts.optimization.backtest_integration import BacktestIntegration

            # Phase 57.7: 100%データで十分な取引数を確保（20%→100%）
            integration = BacktestIntegration(
                period_days=7, data_sampling_ratio=1.0, verbose=self.verbose
            )

            sharpe = asyncio.run(
                integration.run_backtest_with_params(params, param_type="strategy")
            )

            logger.info(f"📊 軽量バックテスト結果: シャープレシオ={sharpe:.4f}")
            return sharpe

        except Exception as e:
            logger.warning(f"⚠️ 軽量バックテストスキップ: {e}")
            return 0.0

    def _run_full_backtest(self, params: Dict[str, Any]) -> float:
        """フルバックテスト実行（指定日数）"""
        try:
            import asyncio

            from scripts.optimization.backtest_integration import BacktestIntegration

            integration = BacktestIntegration(
                period_days=self.backtest_days, data_sampling_ratio=1.0, verbose=self.verbose
            )

            sharpe = asyncio.run(
                integration.run_backtest_with_params(params, param_type="strategy")
            )

            logger.info(f"📊 フルバックテスト結果: シャープレシオ={sharpe:.4f}")
            return sharpe

        except Exception as e:
            logger.warning(f"⚠️ フルバックテストスキップ: {e}")
            return 0.0

    def _save_results(self, result: Dict[str, Any]) -> Path:
        """結果をJSONファイルに保存"""
        elapsed = time.time() - self.start_time

        output = {
            "timestamp": datetime.now().isoformat(),
            "optimization_type": self.optimization_type,
            "n_trials": self.n_trials,
            "backtest_days": self.backtest_days,
            "elapsed_seconds": elapsed,
            "best_params": result.get("best_params", {}),
            "sharpe_ratio": result.get("sharpe_ratio", 0.0),
            "lightweight_sharpe": result.get("lightweight_sharpe", 0.0),
        }

        # 最新結果を保存
        latest_path = self.results_dir / "latest_optimization.json"
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        # タイムスタンプ付きで保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = self.results_dir / f"optimization_{timestamp}.json"
        with open(archive_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ 結果保存: {latest_path}")
        logger.info(f"✅ アーカイブ: {archive_path}")

        # サマリー表示
        logger.info("=" * 60)
        logger.info("📊 最適化完了サマリー")
        logger.info("=" * 60)
        logger.info(f"   タイプ: {self.optimization_type}")
        logger.info(f"   シャープレシオ: {result.get('sharpe_ratio', 0.0):.4f}")
        logger.info(f"   実行時間: {elapsed / 60:.1f}分")
        logger.info(f"   パラメータ数: {len(result.get('best_params', {}))}")
        logger.info("=" * 60)

        return latest_path


def main():
    """メイン実行"""
    parser = argparse.ArgumentParser(description="GitHub Actions用Optuna最適化")
    parser.add_argument(
        "--type",
        type=str,
        default="hybrid",
        choices=["hybrid", "risk", "ml_integration", "strategy"],
        help="最適化タイプ",
    )
    parser.add_argument(
        "--n-trials",
        type=int,
        default=50,
        help="試行回数",
    )
    parser.add_argument(
        "--backtest-days",
        type=int,
        default=90,
        help="バックテスト日数",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="タイムアウト（秒）- 環境変数OPTUNA_TIMEOUT_SECONDSも使用可",
    )
    parser.add_argument("--verbose", action="store_true", help="詳細ログ出力")

    args = parser.parse_args()

    # タイムアウト設定（環境変数優先）
    timeout = args.timeout
    if timeout is None:
        timeout = int(os.environ.get("OPTUNA_TIMEOUT_SECONDS", 19800))

    # 最適化実行
    runner = GitHubOptimizationRunner(
        optimization_type=args.type,
        n_trials=args.n_trials,
        backtest_days=args.backtest_days,
        timeout_seconds=timeout,
        verbose=args.verbose,
    )

    result = runner.run()

    # 終了コード
    if result.get("sharpe_ratio", 0.0) > -999:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
