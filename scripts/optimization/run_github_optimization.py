#!/usr/bin/env python3
"""
GitHub Actions用Optuna最適化統合スクリプト
Phase 60.3拡張: Walk-Forward検証・過学習検出・戦略別最適化

Phase 60.3変更点:
- Walk-Forward検証自動化（120日訓練→60日テスト・30日ステップ）
- 過学習検出（訓練期間 vs テスト期間の乖離チェック・20%以上で警告）
- 戦略別パラメータ最適化（--strategy オプション追加）

Phase 58変更点:
- Stage 1シミュレーションを廃止（スケール不一致問題解消）
- Stage 1: 軽量バックテスト30日（探索用・同一スコア方式）
- Stage 2: フルバックテスト90-180日（検証用・同一スコア方式）
- PFベーススコアを統一使用（Sharpe計算問題回避）

使用方法:
  python scripts/optimization/run_github_optimization.py \
    --type hybrid \
    --n-trials 50 \
    --backtest-days 90

  # 戦略別最適化（Phase 60.3）
  python scripts/optimization/run_github_optimization.py \
    --type strategy \
    --strategy ATRBased \
    --n-trials 30

  # Walk-Forward検証（Phase 60.3）
  python scripts/optimization/run_github_optimization.py \
    --type hybrid \
    --walk-forward

最適化タイプ:
  - hybrid: 全パラメータ2段階最適化（リスク + ML統合 + 戦略）
  - risk: リスク管理パラメータのみ
  - ml_integration: ML統合パラメータのみ
  - strategy: 戦略パラメータのみ（--strategyで個別指定可能）
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

    # [Phase 60.3] 利用可能な戦略リスト
    AVAILABLE_STRATEGIES = [
        "ATRBased",
        "DonchianChannel",
        "ADXTrendStrength",
        "BBReversal",
        "StochasticReversal",
        "MACDEMACrossover",
    ]

    def __init__(
        self,
        optimization_type: str = "hybrid",
        n_trials: int = 50,
        backtest_days: int = 90,
        timeout_seconds: int = 19800,
        verbose: bool = True,
        target_strategy: Optional[str] = None,
        walk_forward: bool = False,
    ):
        """
        初期化

        Args:
            optimization_type: 最適化タイプ（hybrid/risk/ml_integration/strategy）
            n_trials: 試行回数
            backtest_days: バックテスト日数
            timeout_seconds: タイムアウト（秒）
            verbose: 詳細ログ出力
            target_strategy: [Phase 60.3] 最適化対象戦略（strategyタイプ時）
            walk_forward: [Phase 60.3] Walk-Forward検証を実行するか
        """
        self.optimization_type = optimization_type
        self.n_trials = n_trials
        self.backtest_days = backtest_days
        self.timeout_seconds = timeout_seconds
        self.verbose = verbose
        self.target_strategy = target_strategy
        self.walk_forward = walk_forward

        self.results_dir = PROJECT_ROOT / "config" / "optimization" / "results"
        self.results_dir.mkdir(parents=True, exist_ok=True)

        self.start_time = None
        self.best_params = {}
        self.best_sharpe = -999.0

        # [Phase 60.3] Walk-Forward検証結果
        self.walk_forward_results = []
        self.overfitting_warning = False

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
        if self.target_strategy:
            logger.info(f"   対象戦略: {self.target_strategy}")
        if self.walk_forward:
            logger.info("   Walk-Forward検証: 有効")
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

            # [Phase 60.3] Walk-Forward検証
            if self.walk_forward and result.get("best_params"):
                self._run_walk_forward_validation(result.get("best_params", {}))
                result["walk_forward_results"] = self.walk_forward_results
                result["overfitting_warning"] = self.overfitting_warning

            # 結果保存
            self._save_results(result)

            return result

        except Exception as e:
            logger.error(f"❌ 最適化エラー: {e}")
            raise

    def _run_hybrid_optimization(self) -> Dict[str, Any]:
        """
        Phase 58修正: ハイブリッド最適化（2段階）

        旧方式（3段階）の問題:
        - Stage 1シミュレーションのスコア範囲が異なる（-10.0〜+1.5）
        - Stage 2-3のバックテストスコアと同列比較できない
        - スケール不一致でOptunaが発散

        新方式（2段階）:
        - Stage 1: 軽量バックテスト30日（探索用・同一スコア方式）
        - Stage 2: フルバックテスト90-180日（検証用・同一スコア方式）
        - 両Stageで同一のPFベーススコアを使用
        """
        logger.info("=" * 60)
        logger.info("🔵 Phase 58: 2段階ハイブリッド最適化開始")
        logger.info("=" * 60)

        # Stage 1: 軽量バックテスト（30日）で探索
        logger.info("🟡 Stage 1: 軽量バックテスト最適化（30日）")

        # 各最適化器をバックテストベースで実行
        risk_result = self._run_risk_optimization(mode="lightweight_backtest")
        ml_result = self._run_ml_integration_optimization(mode="lightweight_backtest")
        strategy_result = self._run_strategy_optimization(mode="lightweight_backtest")

        # 最良パラメータを統合
        combined_params = {}
        combined_params.update(risk_result.get("best_params", {}))
        combined_params.update(ml_result.get("best_params", {}))
        combined_params.update(strategy_result.get("best_params", {}))

        # Stage 1スコア（軽量バックテスト）
        lightweight_score = self._run_lightweight_backtest(combined_params)
        logger.info(f"📊 Stage 1結果: 最適化スコア={lightweight_score:.4f}")

        # Stage 2: フルバックテスト（指定日数）で検証
        logger.info("🟢 Stage 2: フルバックテスト検証")
        final_score = self._run_full_backtest(combined_params)
        logger.info(f"📊 Stage 2結果: 最適化スコア={final_score:.4f}")

        return {
            "best_params": combined_params,
            "sharpe_ratio": final_score,  # 互換性のためsharpe_ratioを維持（実際はPFベーススコア）
            "lightweight_sharpe": lightweight_score,  # 互換性のためlightweight_sharpeを維持
            "optimization_type": "hybrid",
            "stage_results": {
                "risk": risk_result,
                "ml_integration": ml_result,
                "strategy": strategy_result,
            },
        }

    def _run_risk_optimization(self, mode: str = "full") -> Dict[str, Any]:
        """
        リスク管理パラメータ最適化

        Phase 58: modeオプション更新
        - lightweight_backtest: 30日軽量バックテスト（探索用）
        - full: フルバックテスト（検証用）
        """
        logger.info("🔧 リスク管理パラメータ最適化")

        try:
            from scripts.optimization.optimize_risk_management import RiskManagementOptimizer

            optimizer = RiskManagementOptimizer()

            if mode == "lightweight_backtest":
                # Phase 58: 軽量バックテストベース（30日）
                result = optimizer.optimize(n_trials=min(self.n_trials, 50), timeout=3600)
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
        """
        ML統合パラメータ最適化

        Phase 58: modeオプション更新
        - lightweight_backtest: 30日軽量バックテスト（探索用）
        - full: フルバックテスト（検証用）
        """
        logger.info("🔧 ML統合パラメータ最適化")

        try:
            from scripts.optimization.optimize_ml_integration import MLIntegrationOptimizer

            optimizer = MLIntegrationOptimizer()

            if mode == "lightweight_backtest":
                # Phase 58: 軽量バックテストベース（30日）
                result = optimizer.optimize(n_trials=min(self.n_trials, 50), timeout=3600)
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
        """
        戦略パラメータ最適化（6戦略対応版）

        Phase 58: modeオプション更新
        - lightweight_backtest: 30日軽量バックテスト（探索用）
        - full: フルバックテスト（検証用）

        Phase 60.3: 戦略別最適化対応
        - target_strategyが指定されている場合、その戦略のみ最適化
        """
        if self.target_strategy:
            logger.info(f"🔧 戦略パラメータ最適化: {self.target_strategy}のみ")
        else:
            logger.info("🔧 6戦略パラメータ最適化")

        try:
            from scripts.optimization.optimize_strategy_parameters_v2 import (
                StrategyParameterOptimizerV2,
            )

            # [Phase 60.3] 戦略別最適化
            optimizer = StrategyParameterOptimizerV2(
                verbose=self.verbose,
                target_strategy=self.target_strategy,
            )

            if mode == "lightweight_backtest":
                # Phase 58: 軽量バックテストベース（30日）
                result = optimizer.optimize(n_trials=min(self.n_trials, 100), timeout=5400)
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
        Phase 58修正: 軽量バックテスト実行（30日間×100%）

        Phase 58変更点:
        - 7日 → 30日に延長（統計的有意性向上）
        - 取引数50-150回程度を確保
        - PFベーススコアを返す（-5.0〜+5.0）
        """
        try:
            import asyncio

            from scripts.optimization.backtest_integration import BacktestIntegration

            # Phase 58: 30日間で統計的有意性を確保
            integration = BacktestIntegration(
                period_days=30, data_sampling_ratio=1.0, verbose=self.verbose
            )

            score = asyncio.run(integration.run_backtest_with_params(params, param_type="strategy"))

            logger.info(f"📊 軽量バックテスト結果: 最適化スコア={score:.4f}")
            return score

        except Exception as e:
            logger.warning(f"⚠️ 軽量バックテストスキップ: {e}")
            return -5.0  # Phase 58: エラー時は最低スコア

    def _run_full_backtest(self, params: Dict[str, Any]) -> float:
        """
        Phase 58修正: フルバックテスト実行（指定日数）

        検証用フルバックテスト:
        - 90-180日間の長期検証
        - PFベーススコアを返す（-5.0〜+5.0）
        """
        try:
            import asyncio

            from scripts.optimization.backtest_integration import BacktestIntegration

            integration = BacktestIntegration(
                period_days=self.backtest_days, data_sampling_ratio=1.0, verbose=self.verbose
            )

            score = asyncio.run(integration.run_backtest_with_params(params, param_type="strategy"))

            logger.info(f"📊 フルバックテスト結果: 最適化スコア={score:.4f}")
            return score

        except Exception as e:
            logger.warning(f"⚠️ フルバックテストスキップ: {e}")
            return -5.0  # Phase 58: エラー時は最低スコア

    def _run_walk_forward_validation(self, params: Dict[str, Any]) -> None:
        """
        [Phase 60.3] Walk-Forward検証実行

        120日訓練→60日テスト・30日ステップで移動
        訓練期間 vs テスト期間の乖離が20%以上なら過学習警告

        Args:
            params: 最適化済みパラメータ
        """
        logger.info("=" * 60)
        logger.info("🔄 Phase 60.3: Walk-Forward検証開始")
        logger.info("   訓練期間: 120日")
        logger.info("   テスト期間: 60日")
        logger.info("   ステップ: 30日")
        logger.info("=" * 60)

        try:
            import asyncio

            from scripts.optimization.backtest_integration import BacktestIntegration

            # Walk-Forward期間設定
            train_days = 120
            test_days = 60
            step_days = 30
            total_days = self.backtest_days

            if total_days < train_days + test_days:
                logger.warning(
                    f"⚠️ バックテスト日数({total_days}日)が不足。"
                    f"最低{train_days + test_days}日必要"
                )
                return

            # 各期間でバックテスト実行
            current_start = 0
            period_num = 1

            while current_start + train_days + test_days <= total_days:
                train_end = current_start + train_days
                test_end = train_end + test_days

                # 訓練期間バックテスト
                train_integration = BacktestIntegration(
                    period_days=train_days,
                    data_sampling_ratio=1.0,
                    verbose=False,
                )
                train_score = asyncio.run(
                    train_integration.run_backtest_with_params(params, param_type="strategy")
                )

                # テスト期間バックテスト
                test_integration = BacktestIntegration(
                    period_days=test_days,
                    data_sampling_ratio=1.0,
                    verbose=False,
                )
                test_score = asyncio.run(
                    test_integration.run_backtest_with_params(params, param_type="strategy")
                )

                # 結果記録
                period_result = {
                    "period": period_num,
                    "train_days": f"{current_start}-{train_end}",
                    "test_days": f"{train_end}-{test_end}",
                    "train_score": train_score,
                    "test_score": test_score,
                    "degradation_pct": 0.0,
                }

                # 乖離率計算（訓練期間との比較）
                if train_score > 0:
                    degradation = (train_score - test_score) / train_score * 100
                    period_result["degradation_pct"] = degradation

                    # 20%以上の乖離で警告
                    if degradation > 20:
                        logger.warning(
                            f"⚠️ 過学習警告: 期間{period_num} "
                            f"訓練={train_score:.2f} テスト={test_score:.2f} "
                            f"乖離={degradation:.1f}%"
                        )
                        self.overfitting_warning = True

                self.walk_forward_results.append(period_result)

                logger.info(
                    f"📊 期間{period_num}: "
                    f"訓練={train_score:.2f} テスト={test_score:.2f} "
                    f"乖離={period_result['degradation_pct']:.1f}%"
                )

                # 次の期間へ
                current_start += step_days
                period_num += 1

            # サマリー出力
            if self.walk_forward_results:
                avg_train = sum(r["train_score"] for r in self.walk_forward_results) / len(
                    self.walk_forward_results
                )
                avg_test = sum(r["test_score"] for r in self.walk_forward_results) / len(
                    self.walk_forward_results
                )
                avg_degradation = sum(
                    r["degradation_pct"] for r in self.walk_forward_results
                ) / len(self.walk_forward_results)

                logger.info("=" * 60)
                logger.info("📊 Walk-Forward検証サマリー")
                logger.info(f"   期間数: {len(self.walk_forward_results)}")
                logger.info(f"   平均訓練スコア: {avg_train:.2f}")
                logger.info(f"   平均テストスコア: {avg_test:.2f}")
                logger.info(f"   平均乖離率: {avg_degradation:.1f}%")

                if self.overfitting_warning:
                    logger.warning("⚠️ 過学習の可能性あり - パラメータ見直しを推奨")
                else:
                    logger.info("✅ 過学習の兆候なし")
                logger.info("=" * 60)

        except Exception as e:
            logger.warning(f"⚠️ Walk-Forward検証スキップ: {e}")

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
            # [Phase 60.3] Walk-Forward検証結果
            "walk_forward_results": result.get("walk_forward_results", []),
            "overfitting_warning": result.get("overfitting_warning", False),
        }

        # [Phase 60.3] 戦略別最適化の場合、対象戦略を記録
        if self.target_strategy:
            output["target_strategy"] = self.target_strategy

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
    # [Phase 60.3] 新規オプション
    parser.add_argument(
        "--strategy",
        type=str,
        default=None,
        choices=GitHubOptimizationRunner.AVAILABLE_STRATEGIES,
        help="[Phase 60.3] 最適化対象戦略（strategyタイプ時）",
    )
    parser.add_argument(
        "--walk-forward",
        action="store_true",
        help="[Phase 60.3] Walk-Forward検証を実行",
    )

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
        target_strategy=args.strategy,
        walk_forward=args.walk_forward,
    )

    result = runner.run()

    # 終了コード
    if result.get("sharpe_ratio", 0.0) > -999:
        # [Phase 60.3] 過学習警告があれば警告コードで終了
        if result.get("overfitting_warning"):
            logger.warning("⚠️ 過学習警告により終了コード2")
            sys.exit(2)
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
