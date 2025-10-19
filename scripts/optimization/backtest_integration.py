#!/usr/bin/env python3
"""
Optuna最適化用バックテスト統合モジュール - Phase 40.5

実バックテストシステムとOptuna最適化を統合するためのラッパークラスを提供：
- 軽量バックテスト実行（期間短縮・サンプリング対応）
- シャープレシオ抽出
- パラメータ動的注入
- バックテスト結果解析

ハイブリッド最適化戦略:
- Stage 1: シミュレーション（750試行・高速）
- Stage 2: 軽量バックテスト（上位50試行・30日・10%サンプリング）
- Stage 3: 完全バックテスト（上位10試行・180日・100%データ）
"""

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import yaml

# プロジェクトルートをパス追加
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from src.core.config import load_config
from src.core.logger import get_logger
from src.core.orchestration.orchestrator import TradingOrchestrator, create_trading_orchestrator

from .optuna_utils import OptimizationMetrics


class BacktestIntegration:
    """
    Optuna最適化用バックテスト統合クラス

    機能:
    - 軽量バックテスト実行（期間短縮・サンプリング）
    - パラメータ動的注入（thresholds.yaml一時更新）
    - シャープレシオ抽出
    - エラーハンドリング・ログ管理
    """

    def __init__(
        self,
        period_days: int = 30,
        data_sampling_ratio: float = 1.0,
        use_lightweight: bool = True,
        verbose: bool = False,
    ):
        """
        バックテスト統合初期化

        Args:
            period_days: バックテスト期間（日数）
                - 軽量モード: 30日（約45秒/試行）
                - 完全モード: 180日（約45分/試行）
            data_sampling_ratio: データサンプリング比率（0.0-1.0）
                - 軽量モード: 0.1（10%サンプリング）
                - 完全モード: 1.0（全データ使用）
            use_lightweight: 軽量モード有効化
            verbose: 詳細ログ出力
        """
        self.period_days = period_days
        self.data_sampling_ratio = data_sampling_ratio
        self.use_lightweight = use_lightweight
        self.verbose = verbose

        self.logger = get_logger(__name__)
        self.metrics_calculator = OptimizationMetrics()

        # パフォーマンス統計
        self.execution_count = 0
        self.total_execution_time = 0.0
        self.successful_runs = 0
        self.failed_runs = 0

    async def run_backtest_with_params(
        self, params: Dict[str, Any], param_type: str = "risk"
    ) -> float:
        """
        パラメータを適用してバックテスト実行

        Args:
            params: 最適化パラメータ辞書
            param_type: パラメータタイプ（"risk", "strategy", "ml_integration", "ml_hyperparams"）

        Returns:
            float: シャープレシオ（最適化メトリクス）
        """
        import time

        start_time = time.time()
        self.execution_count += 1

        try:
            # 1. パラメータを一時設定ファイルに注入
            temp_config_path = await self._inject_parameters(params, param_type)

            # 2. バックテスト実行
            if self.verbose:
                self.logger.info(
                    f"🚀 バックテスト開始 "
                    f"(試行#{self.execution_count}, 期間:{self.period_days}日, "
                    f"サンプリング:{self.data_sampling_ratio * 100:.0f}%)"
                )

            sharpe_ratio = await self._execute_backtest(temp_config_path)

            # 3. 統計更新
            execution_time = time.time() - start_time
            self.total_execution_time += execution_time
            self.successful_runs += 1

            if self.verbose:
                avg_time = self.total_execution_time / self.execution_count
                self.logger.info(
                    f"✅ バックテスト完了 (シャープレシオ: {sharpe_ratio:.4f}, "
                    f"実行時間: {execution_time:.1f}秒, 平均: {avg_time:.1f}秒)"
                )

            return sharpe_ratio

        except Exception as e:
            self.failed_runs += 1
            self.logger.error(f"❌ バックテスト実行エラー: {e}")
            # エラー時は非常に低いシャープレシオを返す（Optunaが自動的にスキップ）
            return -999.0

    async def _inject_parameters(self, params: Dict[str, Any], param_type: str) -> Path:
        """
        パラメータを一時設定ファイルに注入

        Args:
            params: 最適化パラメータ
            param_type: パラメータタイプ

        Returns:
            Path: 一時設定ファイルパス
        """
        # メインの設定ファイルを読み込み
        config_path = PROJECT_ROOT / "config" / "core" / "thresholds.yaml"

        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # パラメータタイプに応じて設定を更新
        if param_type == "risk":
            self._update_risk_params(config, params)
        elif param_type == "strategy":
            self._update_strategy_params(config, params)
        elif param_type == "ml_integration":
            self._update_ml_integration_params(config, params)
        elif param_type == "ml_hyperparams":
            self._update_ml_hyperparams(config, params)

        # バックテスト期間設定を追加
        if "execution" not in config:
            config["execution"] = {}
        config["execution"]["backtest_period_days"] = self.period_days

        # データサンプリング設定を追加（Phase 40.5拡張）
        if "backtest" not in config:
            config["backtest"] = {}
        config["backtest"]["data_sampling_ratio"] = self.data_sampling_ratio

        # 一時ファイルに保存
        temp_dir = Path(tempfile.gettempdir())
        temp_path = temp_dir / f"optuna_backtest_config_{os.getpid()}_{self.execution_count}.yaml"

        with open(temp_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True)

        return temp_path

    def _update_risk_params(self, config: Dict, params: Dict) -> None:
        """リスク管理パラメータ更新"""
        if "risk" not in config:
            config["risk"] = {}

        # SL ATR倍率
        if "sl_atr_low_vol" in params:
            if "sl_atr_multiplier" not in config["risk"]:
                config["risk"]["sl_atr_multiplier"] = {}
            config["risk"]["sl_atr_multiplier"]["low"] = params["sl_atr_low_vol"]
            config["risk"]["sl_atr_multiplier"]["normal"] = params["sl_atr_normal_vol"]
            config["risk"]["sl_atr_multiplier"]["high"] = params["sl_atr_high_vol"]

        # SL 最小距離
        if "sl_min_distance_ratio" in params:
            config["risk"]["sl_min_distance_ratio"] = params["sl_min_distance_ratio"]
        if "sl_min_atr_multiplier" in params:
            config["risk"]["sl_min_atr_multiplier"] = params["sl_min_atr_multiplier"]

        # TP設定
        if "tp_default_ratio" in params:
            config["risk"]["tp_default_ratio"] = params["tp_default_ratio"]
        if "tp_min_profit_ratio" in params:
            config["risk"]["tp_min_profit_ratio"] = params["tp_min_profit_ratio"]

        # Kelly基準
        if "kelly_max_position_ratio" in params:
            config["risk"]["kelly_max_position_ratio"] = params["kelly_max_position_ratio"]
        if "kelly_safety_factor" in params:
            if "kelly_criterion" not in config["risk"]:
                config["risk"]["kelly_criterion"] = {}
            config["risk"]["kelly_criterion"]["safety_factor"] = params["kelly_safety_factor"]

        # リスクスコア閾値
        if "risk_conditional" in params:
            if "score_thresholds" not in config["risk"]:
                config["risk"]["score_thresholds"] = {}
            config["risk"]["score_thresholds"]["conditional"] = params["risk_conditional"]
            config["risk"]["score_thresholds"]["deny"] = params["risk_deny"]

    def _update_strategy_params(self, config: Dict, params: Dict) -> None:
        """戦略パラメータ更新"""
        if "strategies" not in config:
            config["strategies"] = {}

        # MochipoyAlert戦略
        if "mochipoy_buy_strong_base" in params:
            if "mochipoy_alert" not in config["strategies"]:
                config["strategies"]["mochipoy_alert"] = {}
            config["strategies"]["mochipoy_alert"].update(
                {
                    "buy_strong_base": params["mochipoy_buy_strong_base"],
                    "buy_weak_base": params["mochipoy_buy_weak_base"],
                    "sell_strong_base": params["mochipoy_sell_strong_base"],
                    "sell_weak_base": params["mochipoy_sell_weak_base"],
                    "neutral_base": params["mochipoy_neutral_base"],
                }
            )

        # MultiTimeframe戦略
        if "mtf_agreement_base" in params:
            if "multi_timeframe" not in config["strategies"]:
                config["strategies"]["multi_timeframe"] = {}
            config["strategies"]["multi_timeframe"].update(
                {
                    "agreement_base": params["mtf_agreement_base"],
                    "partial_agreement_base": params["mtf_partial_agreement_base"],
                    "no_agreement_base": params["mtf_no_agreement_base"],
                    "4h_weight": params["mtf_4h_weight"],
                }
            )

        # DonchianChannel戦略
        if "donchian_breakout_base" in params:
            if "donchian_channel" not in config["strategies"]:
                config["strategies"]["donchian_channel"] = {}
            config["strategies"]["donchian_channel"].update(
                {
                    "breakout_base": params["donchian_breakout_base"],
                    "reversal_base": params["donchian_reversal_base"],
                    "weak_base": params["donchian_weak_base"],
                    "breakout_threshold": params["donchian_breakout_threshold"],
                    "reversal_threshold": params["donchian_reversal_threshold"],
                }
            )

        # ADXTrendStrength戦略
        if "adx_strong_base" in params:
            if "adx_trend_strength" not in config["strategies"]:
                config["strategies"]["adx_trend_strength"] = {}
            config["strategies"]["adx_trend_strength"].update(
                {
                    "strong_base": params["adx_strong_base"],
                    "moderate_base": params["adx_moderate_base"],
                    "weak_base": params["adx_weak_base"],
                    "strong_threshold": params["adx_strong_threshold"],
                    "moderate_min": params["adx_moderate_min"],
                    "di_crossover": params["adx_di_crossover"],
                    "di_confirmation": params["adx_di_confirmation"],
                }
            )

        # ATRBased戦略
        if "atr_high_vol_base" in params:
            if "atr_based" not in config["strategies"]:
                config["strategies"]["atr_based"] = {}
            config["strategies"]["atr_based"].update(
                {
                    "high_vol_base": params["atr_high_vol_base"],
                    "normal_vol_base": params["atr_normal_vol_base"],
                    "low_vol_base": params["atr_low_vol_base"],
                    "rsi_overbought": params["atr_rsi_overbought"],
                    "rsi_oversold": params["atr_rsi_oversold"],
                    "bb_overbought": params["atr_bb_overbought"],
                    "bb_oversold": params["atr_bb_oversold"],
                }
            )

    def _update_ml_integration_params(self, config: Dict, params: Dict) -> None:
        """ML統合パラメータ更新"""
        if "ml" not in config:
            config["ml"] = {}
        if "integration" not in config["ml"]:
            config["ml"]["integration"] = {}

        config["ml"]["integration"].update(
            {
                "weight": params.get("ml_weight", 0.3),
                "high_confidence_threshold": params.get("high_confidence_threshold", 0.8),
                "agreement_bonus": params.get("agreement_bonus", 1.2),
                "disagreement_penalty": params.get("disagreement_penalty", 0.7),
                "min_ml_confidence": params.get("min_ml_confidence", 0.6),
                "hold_conversion_threshold": params.get("hold_conversion_threshold", 0.4),
            }
        )

    def _update_ml_hyperparams(self, config: Dict, params: Dict) -> None:
        """MLハイパーパラメータ更新（モデル再学習は実施しない）"""
        # Phase 40.5: MLハイパーパラメータは学習時に最適化するため、
        # バックテスト時はスキップ（学習済みモデルを使用）
        # 将来的にリアルタイム学習機能追加時に実装
        pass

    async def _execute_backtest(self, config_path: Path) -> float:
        """
        バックテスト実行とシャープレシオ抽出

        Args:
            config_path: 一時設定ファイルパス

        Returns:
            float: シャープレシオ
        """
        try:
            # 環境変数設定（一時設定ファイルを使用）
            os.environ["CONFIG_OVERRIDE_PATH"] = str(config_path)
            os.environ["ENVIRONMENT"] = "backtest"

            # TradingOrchestratorを初期化してバックテスト実行
            logger = get_logger("backtest")
            config = load_config("config/core/unified.yaml", cmdline_mode="backtest")
            orchestrator = await create_trading_orchestrator(config, logger)

            # バックテスト実行
            await orchestrator.initialize()
            await orchestrator.run()

            # Kelly履歴から取引結果を抽出
            sharpe_ratio = self._extract_sharpe_ratio(orchestrator)

            # 一時ファイルクリーンアップ
            if config_path.exists():
                config_path.unlink()

            return sharpe_ratio

        except Exception as e:
            self.logger.error(f"バックテスト実行エラー: {e}")
            # 一時ファイルクリーンアップ
            if config_path.exists():
                config_path.unlink()
            raise

        finally:
            # 環境変数クリア
            if "CONFIG_OVERRIDE_PATH" in os.environ:
                del os.environ["CONFIG_OVERRIDE_PATH"]

    def _extract_sharpe_ratio(self, orchestrator: TradingOrchestrator) -> float:
        """
        オーケストレーターからシャープレシオを抽出

        Args:
            orchestrator: 実行済みTradingOrchestrator

        Returns:
            float: シャープレシオ
        """
        try:
            # IntegratedRiskManager経由でKelly履歴にアクセス
            risk_manager = orchestrator.risk_service
            kelly_criterion = risk_manager.kelly

            # 取引履歴を取得
            trade_history = kelly_criterion.trade_history

            if not trade_history:
                self.logger.warning("取引履歴が空です")
                return 0.0

            # 取引結果からリターン配列を作成
            returns = np.array([trade.profit_loss for trade in trade_history])

            # シャープレシオ計算
            sharpe_ratio = self.metrics_calculator.calculate_sharpe_ratio(returns)

            if self.verbose:
                win_rate = (
                    sum(1 for r in returns if r > 0) / len(returns) if returns.size > 0 else 0
                )
                avg_return = np.mean(returns)
                self.logger.info(
                    f"📊 バックテスト結果: 取引数={len(returns)}, "
                    f"勝率={win_rate:.1%}, 平均リターン={avg_return:.4f}, "
                    f"シャープレシオ={sharpe_ratio:.4f}"
                )

            return sharpe_ratio

        except Exception as e:
            self.logger.error(f"シャープレシオ抽出エラー: {e}")
            return 0.0

    def get_performance_stats(self) -> Dict[str, Any]:
        """
        パフォーマンス統計取得

        Returns:
            Dict: 統計情報
        """
        avg_time = (
            self.total_execution_time / self.execution_count if self.execution_count > 0 else 0
        )

        return {
            "total_executions": self.execution_count,
            "successful_runs": self.successful_runs,
            "failed_runs": self.failed_runs,
            "success_rate": (
                self.successful_runs / self.execution_count if self.execution_count > 0 else 0
            ),
            "total_time_seconds": self.total_execution_time,
            "average_time_seconds": avg_time,
            "period_days": self.period_days,
            "data_sampling_ratio": self.data_sampling_ratio,
        }


# ユーティリティ関数


def create_lightweight_backtest() -> BacktestIntegration:
    """
    軽量バックテスト作成（Phase 40.5最適化: 7日・20%サンプリング・約40秒/試行）

    最適化根拠:
    - 7日間=168時間=672本（15分足）で十分な取引機会を確保
    - サンプリング20%=約134本でも統計的に有意
    - 実行時間: 約40秒/試行（30日・10%から2倍高速化）
    - 50候補で約33分（予定8時間以内に十分収まる）

    Returns:
        BacktestIntegration: 軽量バックテスト
    """
    return BacktestIntegration(period_days=7, data_sampling_ratio=0.2, use_lightweight=True)


def create_full_backtest() -> BacktestIntegration:
    """
    完全バックテスト作成（Phase 40.5最適化: 90日・100%データ・約22.5分/試行）

    最適化根拠:
    - 90日間で十分な統計的有意性を確保
    - 180日の半分で実行時間も半分に短縮
    - 10候補で約3.75時間（8時間目標に十分収まる）

    Returns:
        BacktestIntegration: 完全バックテスト
    """
    return BacktestIntegration(period_days=90, data_sampling_ratio=1.0, use_lightweight=False)


def create_test_backtest() -> BacktestIntegration:
    """
    テスト用バックテスト作成（3日・100%データ・約5秒/試行）

    ユーザー要求対応:
    - 月200回取引目標・1日5-6回エントリー実績 → 3日で15-18回エントリー見込み
    - 動作確認に十分なデータ量を確保しつつ、実行時間を最小化

    Returns:
        BacktestIntegration: テスト用バックテスト（3日間・100%データ）
    """
    return BacktestIntegration(period_days=3, data_sampling_ratio=1.0, use_lightweight=False)


# テスト実行用メイン関数
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="バックテスト統合テスト")
    parser.add_argument("--lightweight", action="store_true", help="軽量モード使用")
    parser.add_argument("--test-mode", action="store_true", help="テストモード（3日間・高速）")
    parser.add_argument("--verbose", action="store_true", help="詳細ログ出力")
    args = parser.parse_args()

    async def test_run():
        """テスト実行"""
        if args.test_mode:
            integration = create_test_backtest()
            print("🚀 テストバックテスト開始（3日・100%データ・Phase 40.5-FIX検証用）")
        elif args.lightweight:
            integration = create_lightweight_backtest()
            print("🚀 軽量バックテストテスト開始（30日・10%サンプリング）")
        else:
            integration = create_full_backtest()
            print("🚀 完全バックテストテスト開始（180日・100%データ）")

        # テストパラメータ（Phase 40.1から取得した最適値）
        test_params = {
            "sl_atr_low_vol": 2.1,
            "sl_atr_normal_vol": 2.0,
            "sl_atr_high_vol": 1.2,
            "sl_min_distance_ratio": 0.009,
            "sl_min_atr_multiplier": 1.3,
            "tp_default_ratio": 1.5,
            "tp_min_profit_ratio": 0.019,
            "kelly_max_position_ratio": 0.05,
            "kelly_safety_factor": 1.0,
            "risk_conditional": 0.7,
            "risk_deny": 0.85,
        }

        # バックテスト実行
        sharpe_ratio = await integration.run_backtest_with_params(test_params, param_type="risk")

        # 結果表示
        print(f"\n✅ テスト完了: シャープレシオ = {sharpe_ratio:.4f}")

        stats = integration.get_performance_stats()
        print("\n📊 パフォーマンス統計:")
        for key, value in stats.items():
            print(f"  - {key}: {value}")

    # 非同期実行
    asyncio.run(test_run())
