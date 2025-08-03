#!/usr/bin/env python3
"""
デプロイ問題点検証システム
過去のデプロイで発生した問題をバックテストで事前検出

検証項目:
1. ATR計算問題
2. マルチタイムフレーム問題
3. アンサンブルモデル問題
4. データ取得件数問題
5. データ新鮮度問題
"""

import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from crypto_bot.indicator.calculator import IndicatorCalculator
from crypto_bot.ml.feature_order_manager import FeatureOrderManager
from crypto_bot.ml.preprocessor import FeatureEngineer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DeploymentIssueValidator:
    """デプロイ問題点検証システム"""

    def __init__(self, config_path: str = "config/production/production.yml"):
        self.config_path = config_path
        self.issues_detected = []
        self.validation_results = {}

        # 検証項目定義
        self.validation_items = {
            "atr_calculation": "ATR計算・NaN値・データ不足問題",
            "multi_timeframe": "マルチタイムフレーム・データ同期問題",
            "ensemble_model": "アンサンブルモデル・特徴量不一致問題",
            "data_acquisition": "データ取得件数・API制限問題",
            "data_freshness": "データ新鮮度・タイムスタンプ問題",
        }

    def load_config(self):
        """設定読み込み"""
        import yaml

        with open(self.config_path, "r") as f:
            config = yaml.safe_load(f)

        logger.info(f"✅ Configuration loaded from {self.config_path}")
        return config

    def validate_atr_calculation(self, data_df):
        """ATR計算問題検証"""
        logger.info("🔍 Validating ATR calculation issues...")

        issues = []

        try:
            # 1. データ不足での ATR 計算
            small_data = data_df.head(10)  # 10件の少量データ
            calculator = IndicatorCalculator()

            # ATR期間14での計算テスト
            atr_result = calculator.calculate_atr(small_data, period=14)

            # NaN値チェック
            nan_count = atr_result.isna().sum()
            total_count = len(atr_result)
            nan_ratio = nan_count / total_count if total_count > 0 else 1.0

            if nan_ratio > 0.8:  # 80%以上がNaN
                issues.append(
                    {
                        "type": "atr_high_nan_ratio",
                        "severity": "HIGH",
                        "description": f"ATR計算で{nan_ratio:.2%}がNaN値",
                        "impact": "リスク管理不能・ポジションサイズ計算エラー",
                        "recommendation": "ATR期間短縮またはフォールバック機能実装",
                    }
                )

            # 2. 極端なATR値チェック
            valid_atr = atr_result.dropna()
            if len(valid_atr) > 0:
                max_atr = valid_atr.max()
                mean_price = data_df["close"].mean()

                if max_atr > mean_price * 0.1:  # ATRが価格の10%以上
                    issues.append(
                        {
                            "type": "atr_extreme_values",
                            "severity": "MEDIUM",
                            "description": f"極端なATR値検出: {max_atr:.2f} (価格の{max_atr/mean_price:.2%})",
                            "impact": "過大なストップロス・誤ったリスク計算",
                            "recommendation": "ATR上限制限・異常値フィルタ実装",
                        }
                    )

            # 3. ATR期間vs データ量チェック
            required_data = 20  # ATR_14 + マージン
            available_data = len(data_df)

            if available_data < required_data:
                issues.append(
                    {
                        "type": "atr_insufficient_data",
                        "severity": "HIGH",
                        "description": f"ATR計算に必要なデータ不足: {available_data}/{required_data}",
                        "impact": "ATR計算不可・リスク管理システム機能停止",
                        "recommendation": "データ取得件数増加・最小データ要件確認",
                    }
                )

        except Exception as e:
            issues.append(
                {
                    "type": "atr_calculation_error",
                    "severity": "CRITICAL",
                    "description": f"ATR計算でエラー発生: {str(e)}",
                    "impact": "システム停止・取引不可",
                    "recommendation": "エラーハンドリング強化・フォールバック実装",
                }
            )

        self.validation_results["atr_calculation"] = {
            "status": "FAIL" if issues else "PASS",
            "issues_count": len(issues),
            "issues": issues,
        }

        logger.info(f"📊 ATR検証完了: {len(issues)}個の問題検出")
        return issues

    def validate_multi_timeframe(self, config):
        """マルチタイムフレーム問題検証"""
        logger.info("🔍 Validating multi-timeframe issues...")

        issues = []

        try:
            # 1. タイムフレーム設定確認
            mtf_config = config.get("multi_timeframe", {})
            timeframes = mtf_config.get("timeframes", [])

            if not timeframes:
                issues.append(
                    {
                        "type": "mtf_no_timeframes",
                        "severity": "HIGH",
                        "description": "マルチタイムフレーム設定なし",
                        "impact": "単一タイムフレーム分析・予測精度低下",
                        "recommendation": "15m, 1h, 4hのマルチタイムフレーム設定追加",
                    }
                )

            # 2. 重み設定チェック
            weights = mtf_config.get("weights", [])
            if len(weights) != len(timeframes):
                issues.append(
                    {
                        "type": "mtf_weight_mismatch",
                        "severity": "MEDIUM",
                        "description": f"タイムフレーム数{len(timeframes)}と重み数{len(weights)}が不一致",
                        "impact": "重み計算エラー・アンサンブル予測失敗",
                        "recommendation": "タイムフレーム数と重み数の一致確認",
                    }
                )

            # 3. データ品質閾値確認
            quality_threshold = mtf_config.get("data_quality_threshold", 0)
            if quality_threshold < 0.5:
                issues.append(
                    {
                        "type": "mtf_low_quality_threshold",
                        "severity": "MEDIUM",
                        "description": f"データ品質閾値が低い: {quality_threshold}",
                        "impact": "低品質データでの予測・取引精度低下",
                        "recommendation": "品質閾値を0.6以上に設定",
                    }
                )

        except Exception as e:
            issues.append(
                {
                    "type": "mtf_configuration_error",
                    "severity": "HIGH",
                    "description": f"マルチタイムフレーム設定エラー: {str(e)}",
                    "impact": "MTF機能停止・単一TF分析のみ",
                    "recommendation": "設定ファイル構文確認・必須項目追加",
                }
            )

        self.validation_results["multi_timeframe"] = {
            "status": "FAIL" if issues else "PASS",
            "issues_count": len(issues),
            "issues": issues,
        }

        logger.info(f"📊 MTF検証完了: {len(issues)}個の問題検出")
        return issues

    def validate_ensemble_model(self, config):
        """アンサンブルモデル問題検証"""
        logger.info("🔍 Validating ensemble model issues...")

        issues = []

        try:
            # 1. 特徴量順序管理チェック
            feature_manager = FeatureOrderManager()
            expected_features = feature_manager.FEATURE_ORDER_97

            # 2. モデルファイル存在確認
            model_paths = [
                "models/production/model.pkl",
                "models/validation/lgbm_97_features.pkl",
                "models/validation/xgb_97_features.pkl",
                "models/validation/rf_97_features.pkl",
            ]

            missing_models = []
            for model_path in model_paths:
                if not Path(model_path).exists():
                    missing_models.append(model_path)

            if missing_models:
                issues.append(
                    {
                        "type": "ensemble_missing_models",
                        "severity": "HIGH",
                        "description": f"モデルファイル不足: {len(missing_models)}個",
                        "missing_files": missing_models,
                        "impact": "アンサンブル予測不可・フォールバック動作",
                        "recommendation": "欠損モデルの再学習・ファイルパス確認",
                    }
                )

            # 3. 特徴量数一致確認
            ml_config = config.get("ml", {})
            extra_features = ml_config.get("extra_features", [])

            # Phase 2: 97特徴量システム対応
            # 基本特徴量数 + extra_features
            base_features = (
                5  # OHLCV のみ（lags と returns は extra_features に含まれる）
            )
            total_expected = base_features + len(extra_features)

            if total_expected != len(expected_features):
                issues.append(
                    {
                        "type": "ensemble_feature_count_mismatch",
                        "severity": "CRITICAL",
                        "description": f"特徴量数不一致: 設定{total_expected} vs 期待{len(expected_features)}",
                        "impact": "特徴量数エラー・予測実行不可",
                        "recommendation": "特徴量設定と順序定義の一致確認",
                    }
                )

            # 4. アンサンブル設定確認
            ensemble_config = config.get("ml", {}).get("ensemble", {})
            if not ensemble_config.get("enabled", False):
                issues.append(
                    {
                        "type": "ensemble_disabled",
                        "severity": "MEDIUM",
                        "description": "アンサンブル学習が無効化",
                        "impact": "単一モデル予測・予測精度低下可能性",
                        "recommendation": "アンサンブル学習有効化検討",
                    }
                )

        except Exception as e:
            issues.append(
                {
                    "type": "ensemble_validation_error",
                    "severity": "CRITICAL",
                    "description": f"アンサンブル検証エラー: {str(e)}",
                    "impact": "検証不可・未知のアンサンブル問題残存",
                    "recommendation": "検証システム修正・手動確認実施",
                }
            )

        self.validation_results["ensemble_model"] = {
            "status": "FAIL" if issues else "PASS",
            "issues_count": len(issues),
            "issues": issues,
        }

        logger.info(f"📊 アンサンブル検証完了: {len(issues)}個の問題検出")
        return issues

    def validate_data_acquisition(self, config):
        """データ取得件数問題検証"""
        logger.info("🔍 Validating data acquisition issues...")

        issues = []

        try:
            # 1. データ取得設定確認
            data_config = config.get("data", {})
            limit = data_config.get("limit", 0)
            since_hours = data_config.get("since_hours", 0)

            # 必要データ量計算
            required_for_features = 200  # 特徴量計算に必要
            required_for_ml = 100  # ML学習に必要
            total_required = max(required_for_features, required_for_ml)

            if limit < total_required:
                issues.append(
                    {
                        "type": "data_insufficient_limit",
                        "severity": "HIGH",
                        "description": f"データ取得制限不足: {limit}/{total_required}",
                        "impact": "特徴量計算不可・ML学習データ不足",
                        "recommendation": f"limit値を{total_required}以上に設定",
                    }
                )

            # 2. API制限チェック
            max_attempts = data_config.get("max_attempts", 0)
            if max_attempts < 15:
                issues.append(
                    {
                        "type": "data_low_retry_attempts",
                        "severity": "MEDIUM",
                        "description": f"リトライ回数不足: {max_attempts}",
                        "impact": "API制限時のデータ取得失敗・不完全なデータ",
                        "recommendation": "max_attempts を20以上に設定",
                    }
                )

            # 3. ページネーション設定
            per_page = data_config.get("per_page", 0)
            if per_page < 100:
                issues.append(
                    {
                        "type": "data_small_page_size",
                        "severity": "LOW",
                        "description": f"ページサイズ小: {per_page}",
                        "impact": "API呼び出し回数増加・取得効率低下",
                        "recommendation": "per_page を200に設定（効率化）",
                    }
                )

            # 4. データ保持期間
            if since_hours < 72:
                issues.append(
                    {
                        "type": "data_short_retention",
                        "severity": "MEDIUM",
                        "description": f"データ保持期間短: {since_hours}時間",
                        "impact": "特徴量計算に必要な履歴不足",
                        "recommendation": "since_hours を96時間以上に設定",
                    }
                )

        except Exception as e:
            issues.append(
                {
                    "type": "data_config_error",
                    "severity": "HIGH",
                    "description": f"データ取得設定エラー: {str(e)}",
                    "impact": "データ取得機能停止・システム動作不可",
                    "recommendation": "データ設定構文確認・必須項目追加",
                }
            )

        self.validation_results["data_acquisition"] = {
            "status": "FAIL" if issues else "PASS",
            "issues_count": len(issues),
            "issues": issues,
        }

        logger.info(f"📊 データ取得検証完了: {len(issues)}個の問題検出")
        return issues

    def validate_data_freshness(self, data_df):
        """データ新鮮度問題検証"""
        logger.info("🔍 Validating data freshness issues...")

        issues = []

        try:
            # 1. タイムスタンプ連続性チェック
            if "timestamp" in data_df.columns:
                timestamps = pd.to_datetime(data_df["timestamp"])
                time_diffs = timestamps.diff().dropna()

                # 1時間以上の間隔チェック
                large_gaps = time_diffs[time_diffs > pd.Timedelta(hours=2)]
                if len(large_gaps) > 0:
                    issues.append(
                        {
                            "type": "data_large_time_gaps",
                            "severity": "MEDIUM",
                            "description": f"大きな時間間隔検出: {len(large_gaps)}箇所",
                            "max_gap": str(large_gaps.max()),
                            "impact": "データ欠損・特徴量計算エラー・予測精度低下",
                            "recommendation": "データ補間・欠損値処理実装",
                        }
                    )

                # 2. 未来時刻チェック
                now = pd.Timestamp.now("UTC")
                future_data = timestamps[timestamps > now]
                if len(future_data) > 0:
                    issues.append(
                        {
                            "type": "data_future_timestamps",
                            "severity": "HIGH",
                            "description": f"未来時刻データ検出: {len(future_data)}件",
                            "impact": "タイムスタンプ異常・時系列分析エラー",
                            "recommendation": "タイムスタンプ検証・修正機能実装",
                        }
                    )

                # 3. データ新鮮度チェック
                latest_time = timestamps.max()
                staleness = now - latest_time

                if staleness > pd.Timedelta(hours=6):
                    issues.append(
                        {
                            "type": "data_stale_data",
                            "severity": "HIGH",
                            "description": f"古いデータ: {staleness}前が最新",
                            "impact": "古いデータでの予測・市場変化未反映",
                            "recommendation": "データ取得頻度向上・リアルタイム取得実装",
                        }
                    )

            # 4. 価格データ整合性
            if all(col in data_df.columns for col in ["open", "high", "low", "close"]):
                # OHLC整合性チェック
                invalid_ohlc = (
                    (data_df["high"] < data_df["low"])
                    | (data_df["high"] < data_df["open"])
                    | (data_df["high"] < data_df["close"])
                    | (data_df["low"] > data_df["open"])
                    | (data_df["low"] > data_df["close"])
                )

                invalid_count = invalid_ohlc.sum()
                if invalid_count > 0:
                    issues.append(
                        {
                            "type": "data_invalid_ohlc",
                            "severity": "CRITICAL",
                            "description": f"OHLC整合性エラー: {invalid_count}件",
                            "impact": "価格データ異常・テクニカル指標計算エラー",
                            "recommendation": "データ品質チェック・異常値除去実装",
                        }
                    )

        except Exception as e:
            issues.append(
                {
                    "type": "data_freshness_error",
                    "severity": "HIGH",
                    "description": f"データ新鮮度検証エラー: {str(e)}",
                    "impact": "新鮮度検証不可・データ品質不明",
                    "recommendation": "検証ロジック修正・手動データ確認",
                }
            )

        self.validation_results["data_freshness"] = {
            "status": "FAIL" if issues else "PASS",
            "issues_count": len(issues),
            "issues": issues,
        }

        logger.info(f"📊 データ新鮮度検証完了: {len(issues)}個の問題検出")
        return issues

    def run_comprehensive_validation(self):
        """包括的検証実行"""
        logger.info("🚀 Starting comprehensive deployment issue validation...")

        # 設定読み込み
        config = self.load_config()

        # サンプルデータ読み込み
        try:
            data_df = pd.read_csv("data/btc_usd_2024_hourly.csv")
            if "timestamp" not in data_df.columns and data_df.columns[0].lower() in [
                "timestamp",
                "time",
                "date",
            ]:
                data_df.rename(columns={data_df.columns[0]: "timestamp"}, inplace=True)
        except Exception as e:
            logger.error(f"データ読み込みエラー: {e}")
            data_df = pd.DataFrame()  # 空のDataFrame

        # 各検証項目実行
        all_issues = []

        # 1. ATR計算問題検証
        atr_issues = self.validate_atr_calculation(data_df)
        all_issues.extend(atr_issues)

        # 2. マルチタイムフレーム問題検証
        mtf_issues = self.validate_multi_timeframe(config)
        all_issues.extend(mtf_issues)

        # 3. アンサンブルモデル問題検証
        ensemble_issues = self.validate_ensemble_model(config)
        all_issues.extend(ensemble_issues)

        # 4. データ取得件数問題検証
        data_issues = self.validate_data_acquisition(config)
        all_issues.extend(data_issues)

        # 5. データ新鮮度問題検証
        freshness_issues = self.validate_data_freshness(data_df)
        all_issues.extend(freshness_issues)

        # 結果集計
        self.issues_detected = all_issues

        # 重要度別集計
        critical_issues = [i for i in all_issues if i["severity"] == "CRITICAL"]
        high_issues = [i for i in all_issues if i["severity"] == "HIGH"]
        medium_issues = [i for i in all_issues if i["severity"] == "MEDIUM"]
        low_issues = [i for i in all_issues if i["severity"] == "LOW"]

        # 結果保存
        results = {
            "validation_timestamp": datetime.now().isoformat(),
            "config_path": self.config_path,
            "summary": {
                "total_issues": len(all_issues),
                "critical_issues": len(critical_issues),
                "high_issues": len(high_issues),
                "medium_issues": len(medium_issues),
                "low_issues": len(low_issues),
            },
            "validation_results": self.validation_results,
            "all_issues": all_issues,
            "recommendations": self.generate_recommendations(),
        }

        # 結果保存
        results_dir = Path("results/deployment_validation")
        results_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = results_dir / f"deployment_validation_{timestamp}.json"

        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        # サマリー出力
        logger.info("🎊 Deployment validation completed!")
        logger.info(f"📊 Results summary:")
        logger.info(f"   - Total issues: {len(all_issues)}")
        logger.info(f"   - Critical: {len(critical_issues)}")
        logger.info(f"   - High: {len(high_issues)}")
        logger.info(f"   - Medium: {len(medium_issues)}")
        logger.info(f"   - Low: {len(low_issues)}")
        logger.info(f"📁 Results saved: {results_file}")

        return results

    def generate_recommendations(self):
        """推奨対応策生成"""
        recommendations = []

        critical_count = len(
            [i for i in self.issues_detected if i["severity"] == "CRITICAL"]
        )
        high_count = len([i for i in self.issues_detected if i["severity"] == "HIGH"])

        if critical_count > 0:
            recommendations.append(
                {
                    "priority": "IMMEDIATE",
                    "action": "CRITICAL問題の即座修正",
                    "description": f"{critical_count}個のCRITICAL問題が検出されました。デプロイ前に必ず修正してください。",
                }
            )

        if high_count > 0:
            recommendations.append(
                {
                    "priority": "HIGH",
                    "action": "HIGH問題の修正検討",
                    "description": f"{high_count}個のHIGH問題が検出されました。デプロイ前の修正を強く推奨します。",
                }
            )

        # 具体的推奨策
        if any(i["type"].startswith("atr_") for i in self.issues_detected):
            recommendations.append(
                {
                    "priority": "HIGH",
                    "action": "ATRシステム強化",
                    "description": "ATR計算の堅牢性向上・フォールバック機能実装・異常値フィルタ追加",
                }
            )

        if any(i["type"].startswith("ensemble_") for i in self.issues_detected):
            recommendations.append(
                {
                    "priority": "HIGH",
                    "action": "アンサンブルシステム修正",
                    "description": "特徴量数一致・モデルファイル確認・アンサンブル設定最適化",
                }
            )

        return recommendations


def main():
    """メイン実行"""
    validator = DeploymentIssueValidator()
    results = validator.run_comprehensive_validation()

    # 問題が検出された場合はエラーコードで終了
    critical_count = results["summary"]["critical_issues"]
    high_count = results["summary"]["high_issues"]

    if critical_count > 0:
        print(f"❌ CRITICAL問題 {critical_count}個検出 - デプロイ阻止")
        sys.exit(2)
    elif high_count > 0:
        print(f"⚠️ HIGH問題 {high_count}個検出 - 修正推奨")
        sys.exit(1)
    else:
        print("✅ 検証完了 - デプロイ可能")
        sys.exit(0)


if __name__ == "__main__":
    main()
