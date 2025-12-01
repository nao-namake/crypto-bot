#!/usr/bin/env python3
"""
Optuna最適化結果をプリセットYAMLに変換するスクリプト
Phase 57.6: Phase 57.5プリセットシステムとの連携

使用方法:
  python scripts/optimization/save_as_preset.py \
    --source config/optimization/results/latest_optimization.json \
    --preset-name "optuna_20251201"

出力:
  config/core/strategies/presets/optuna_20251201.yaml
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import yaml

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class PresetConverter:
    """最適化結果→プリセット変換クラス"""

    def __init__(self, source_path: Path, preset_name: str):
        """
        初期化

        Args:
            source_path: 最適化結果JSONファイルパス
            preset_name: プリセット名
        """
        self.source_path = source_path
        self.preset_name = preset_name
        self.presets_dir = PROJECT_ROOT / "config" / "core" / "strategies" / "presets"
        self.presets_dir.mkdir(parents=True, exist_ok=True)

    def convert(self) -> Path:
        """
        最適化結果をプリセットYAMLに変換

        Returns:
            Path: 出力ファイルパス
        """
        # JSONファイル読み込み
        with open(self.source_path, "r", encoding="utf-8") as f:
            optimization_result = json.load(f)

        best_params = optimization_result.get("best_params", {})
        sharpe_ratio = optimization_result.get("sharpe_ratio", 0.0)
        optimization_type = optimization_result.get("optimization_type", "unknown")
        timestamp = optimization_result.get("timestamp", datetime.now().isoformat())

        # プリセットYAML構造を作成
        preset = self._create_preset_structure(
            best_params=best_params,
            sharpe_ratio=sharpe_ratio,
            optimization_type=optimization_type,
            timestamp=timestamp,
        )

        # YAMLファイル出力
        output_path = self.presets_dir / f"{self.preset_name}.yaml"

        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(
                preset,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
                width=120,
            )

        print(f"✅ プリセット保存: {output_path}")
        return output_path

    def _create_preset_structure(
        self,
        best_params: Dict[str, Any],
        sharpe_ratio: float,
        optimization_type: str,
        timestamp: str,
    ) -> Dict[str, Any]:
        """
        プリセットYAML構造を作成

        Args:
            best_params: 最適化パラメータ
            sharpe_ratio: シャープレシオ
            optimization_type: 最適化タイプ
            timestamp: タイムスタンプ

        Returns:
            Dict: プリセット構造
        """
        # 基本構造
        preset = {
            "version": self.preset_name,
            "description": f"Optuna最適化結果 ({optimization_type})",
            "generated_at": timestamp,
            "tested_date": datetime.now().strftime("%Y-%m-%d"),
            "optimization_info": {
                "type": optimization_type,
                "sharpe_ratio": round(sharpe_ratio, 4),
                "source": str(self.source_path),
            },
        }

        # パフォーマンス記録（プレースホルダー）
        preset["performance"] = {
            "win_rate": None,
            "profit_factor": None,
            "total_pnl": None,
            "total_trades": None,
            "max_drawdown": None,
            "note": "バックテスト実施後に更新してください",
        }

        # Phase 56設定をベースとしてコピー
        preset["regime_active_strategies"] = {
            "tight_range": ["ATRBased", "BBReversal", "StochasticReversal"],
            "normal_range": ["ATRBased", "BBReversal", "DonchianChannel"],
            "trending": ["ADXTrendStrength", "MACDEMACrossover", "DonchianChannel"],
            "high_volatility": [],
        }

        preset["regime_strategy_mapping"] = {
            "tight_range": {
                "ATRBased": 0.40,
                "BBReversal": 0.30,
                "DonchianChannel": 0.15,
                "StochasticReversal": 0.15,
                "ADXTrendStrength": 0.0,
                "MACDEMACrossover": 0.0,
            },
            "normal_range": {
                "ATRBased": 0.35,
                "BBReversal": 0.20,
                "DonchianChannel": 0.10,
                "StochasticReversal": 0.15,
                "ADXTrendStrength": 0.15,
                "MACDEMACrossover": 0.05,
            },
            "trending": {
                "ADXTrendStrength": 0.50,
                "MACDEMACrossover": 0.30,
                "ATRBased": 0.15,
                "DonchianChannel": 0.05,
                "BBReversal": 0.0,
                "StochasticReversal": 0.0,
            },
            "high_volatility": {
                "ATRBased": 0.0,
                "BBReversal": 0.0,
                "DonchianChannel": 0.0,
                "StochasticReversal": 0.0,
                "ADXTrendStrength": 0.0,
                "MACDEMACrossover": 0.0,
            },
        }

        # 戦略パラメータ（最適化結果から抽出）
        strategies = self._extract_strategy_params(best_params)
        preset["strategies"] = strategies

        # ML統合設定（最適化結果から抽出またはデフォルト）
        ml_integration = self._extract_ml_params(best_params)
        preset["ml_integration"] = ml_integration

        # 信頼度レベル（Phase 56設定）
        preset["confidence_levels"] = {
            "high": 0.35,
            "medium": 0.18,
            "low": 0.15,
            "min_ml": 0.12,
            "very_high": 0.55,
        }

        return preset

    def _extract_strategy_params(self, best_params: Dict[str, Any]) -> Dict[str, Any]:
        """戦略パラメータを抽出"""
        strategies = {
            "atr_based": {
                "hold_confidence": best_params.get("atr_hold_confidence", 0.10),
                "min_confidence": best_params.get("atr_min_confidence", 0.25),
                "bb_overbought": best_params.get("atr_bb_overbought", 0.7),
                "bb_oversold": best_params.get("atr_bb_oversold", 0.3),
                "rsi_overbought": best_params.get("atr_rsi_overbought", 65),
                "rsi_oversold": best_params.get("atr_rsi_oversold", 35),
            },
            "bb_reversal": {
                "hold_confidence": 0.25,
                "min_confidence": best_params.get("bb_min_confidence", 0.30),
                "bb_width_threshold": best_params.get("bb_width_threshold", 0.025),
                "rsi_overbought": best_params.get("bb_rsi_overbought", 65),
                "rsi_oversold": best_params.get("bb_rsi_oversold", 35),
                "bb_upper_threshold": best_params.get("bb_upper_threshold", 0.85),
                "bb_lower_threshold": best_params.get("bb_lower_threshold", 0.15),
                "adx_range_threshold": best_params.get("bb_adx_threshold", 35),
                "sl_multiplier": 1.5,
            },
            "stochastic_reversal": {
                "hold_confidence": 0.25,
                "min_confidence": best_params.get("stoch_min_confidence", 0.30),
                "stoch_overbought": best_params.get("stoch_overbought", 75),
                "stoch_oversold": best_params.get("stoch_oversold", 25),
                "rsi_overbought": best_params.get("stoch_rsi_overbought", 60),
                "rsi_oversold": best_params.get("stoch_rsi_oversold", 40),
                "adx_range_threshold": best_params.get("stoch_adx_threshold", 35),
                "sl_multiplier": 1.5,
            },
            "donchian_channel": {
                "hold_confidence": best_params.get("donchian_hold_confidence", 0.40),
                "min_confidence": best_params.get("donchian_min_confidence", 0.25),
                "middle_zone_min": best_params.get("donchian_middle_min", 0.40),
                "middle_zone_max": best_params.get("donchian_middle_max", 0.60),
                "reversal_threshold": best_params.get("donchian_reversal_threshold", 0.10),
                "weak_signal_confidence": 0.35,
                "weak_signal_max": 0.70,
            },
            "adx_trend": {
                "hold_confidence": best_params.get("adx_hold_confidence", 0.45),
                "min_confidence": best_params.get("adx_min_confidence", 0.25),
                "di_crossover_threshold": best_params.get("adx_di_crossover", 0.5),
                "strong_trend_threshold": best_params.get("adx_strong_threshold", 25),
                "moderate_trend_min": best_params.get("adx_moderate_min", 15),
                "moderate_trend_max": best_params.get("adx_strong_threshold", 25),
                "weak_trend_threshold": 15,
            },
            "macd_ema_crossover": {
                "hold_confidence": best_params.get("macd_hold_confidence", 0.25),
                "min_confidence": best_params.get("macd_min_confidence", 0.35),
                "adx_trend_threshold": best_params.get("macd_adx_threshold", 25),
                "volume_ratio_threshold": best_params.get("macd_volume_ratio", 1.1),
                "sl_multiplier": 1.5,
            },
        }

        return strategies

    def _extract_ml_params(self, best_params: Dict[str, Any]) -> Dict[str, Any]:
        """ML統合パラメータを抽出"""
        return {
            "hold_conversion_threshold": best_params.get("hold_conversion_threshold", 0.20),
            "min_ml_confidence": best_params.get("min_ml_confidence", 0.35),
            "high_confidence_threshold": best_params.get("high_confidence_threshold", 0.55),
            "disagreement_penalty": best_params.get("disagreement_penalty", 0.90),
            "ml_weight": best_params.get("ml_weight", 0.30),
            "strategy_weight": best_params.get("strategy_weight", 0.70),
            "agreement_bonus": best_params.get("agreement_bonus", 1.2),
        }

    def update_active_preset(self) -> None:
        """active.yamlを更新して新しいプリセットを選択"""
        active_path = self.presets_dir / "active.yaml"

        if active_path.exists():
            with open(active_path, "r", encoding="utf-8") as f:
                active_config = yaml.safe_load(f) or {}
        else:
            active_config = {
                "aliases": {"A": "phase56", "B": "phase57_4"},
            }

        # 新しいプリセットをCエイリアスに設定
        if "aliases" not in active_config:
            active_config["aliases"] = {}

        active_config["aliases"]["C"] = self.preset_name

        # 保存（アクティブプリセットは変更しない - 手動切り替え推奨）
        with open(active_path, "w", encoding="utf-8") as f:
            yaml.dump(
                active_config,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        print(f"✅ active.yaml更新: aliases.C = {self.preset_name}")
        print(f"   手動で active_preset: {self.preset_name} に切り替えてください")


def main():
    """メイン実行"""
    parser = argparse.ArgumentParser(description="Optuna結果をプリセットに変換")
    parser.add_argument(
        "--source",
        type=str,
        default="config/optimization/results/latest_optimization.json",
        help="最適化結果JSONファイルパス",
    )
    parser.add_argument(
        "--preset-name",
        type=str,
        default=None,
        help="プリセット名（デフォルト: optuna_YYYYMMDD）",
    )
    parser.add_argument(
        "--update-active",
        action="store_true",
        help="active.yamlを更新（Cエイリアスに設定）",
    )

    args = parser.parse_args()

    # プリセット名が指定されていない場合は日付から生成
    preset_name = args.preset_name
    if preset_name is None:
        preset_name = f"optuna_{datetime.now().strftime('%Y%m%d')}"

    source_path = PROJECT_ROOT / args.source

    if not source_path.exists():
        print(f"❌ エラー: ソースファイルが見つかりません: {source_path}")
        sys.exit(1)

    # 変換実行
    converter = PresetConverter(source_path, preset_name)
    output_path = converter.convert()

    # active.yaml更新
    if args.update_active:
        converter.update_active_preset()

    print("\n" + "=" * 60)
    print("📋 プリセット変換完了")
    print("=" * 60)
    print(f"   出力: {output_path}")
    print(f"   プリセット名: {preset_name}")
    print("\n使用方法:")
    print("   1. config/core/strategies/presets/active.yaml を編集")
    print(f"   2. active_preset: {preset_name} に変更")
    print("   3. システムを再起動")
    print("=" * 60)


if __name__ == "__main__":
    main()
