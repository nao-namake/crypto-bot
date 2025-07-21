#!/usr/bin/env python3
"""
Phase B2.6.2: 機能・品質テスト - 151特徴量整合性・エラーハンドリング検証

包括的テスト内容:
1. 151特徴量完全生成検証
2. バッチ vs レガシーシステム特徴量整合性
3. エラーハンドリング・フォールバック機能検証
4. 外部データ統合品質テスト
5. エッジケース・異常データ処理テスト
6. データ品質・一貫性検証

期待結果:
- 151特徴量すべて生成成功
- バッチ・レガシー間の完全一致
- 堅牢なエラーハンドリング
- 外部データ障害時の適切なフォールバック
"""

import json
import logging
import os
import sys
import time
import traceback
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import Mock, patch

# プロジェクトルートを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import pandas as pd
import yaml

# テスト対象システム
from crypto_bot.ml.feature_engines.batch_calculator import BatchFeatureCalculator
from crypto_bot.ml.feature_engines.technical_engine import TechnicalFeatureEngine
from crypto_bot.ml.feature_engines.external_data_engine import ExternalDataIntegrator
from crypto_bot.ml.preprocessor import FeatureEngineer

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FeatureIntegrityTester:
    """特徴量整合性・品質テスター"""
    
    def __init__(self):
        self.results = {
            "test_metadata": {
                "timestamp": time.time(),
                "python_version": sys.version,
                "test_phase": "B2.6.2"
            },
            "feature_integrity": {},
            "error_handling": {},
            "external_data_quality": {},
            "edge_case_handling": {},
            "overall_assessment": {}
        }
        
        # 設定ファイル読み込み
        self.config = self._load_full_config()
        
        # テストデータ準備
        self.test_data = self._prepare_comprehensive_test_data()
        
        # 期待特徴量リスト
        self.expected_features = self._get_expected_151_features()
        
        logger.info("🧪 FeatureIntegrityTester initialized for Phase B2.6.2")
    
    def _load_full_config(self) -> Dict[str, Any]:
        """完全版151特徴量設定読み込み"""
        config_path = "/Users/nao/Desktop/bot/config/production/production.yml"
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            logger.info(f"📋 Full production config loaded: {len(config.get('ml', {}).get('extra_features', []))} features")
            return config
        except Exception as e:
            logger.error(f"❌ Failed to load production config: {e}")
            # フォールバック設定（151特徴量対応）
            return {
                "ml": {
                    "extra_features": [
                        # 基本テクニカル
                        "rsi_14", "rsi_7", "rsi_21", "sma_20", "sma_50", "sma_100", "sma_200",
                        "ema_12", "ema_26", "ema_50", "ema_100", "macd", "atr_14", "stoch", "adx",
                        # 外部データ
                        "vix", "macro", "dxy", "treasury", "fear_greed", "funding",
                        # Phase 3.2 新特徴量 (65特徴量)
                        "volume_profile_poc", "volume_profile_vah", "volume_profile_val",
                        "volatility_regime", "momentum_signals", "liquidity_indicators",
                        "market_microstructure", "cross_asset_correlation", "sentiment_analysis"
                    ],
                    "feat_period": 14,
                    "lags": [1, 2, 3],
                    "rolling_window": 14
                }
            }
    
    def _prepare_comprehensive_test_data(self) -> pd.DataFrame:
        """包括的テストデータ準備"""
        try:
            # CSVデータロード
            csv_path = "/Users/nao/Desktop/bot/data/btc_usd_2024_hourly.csv"
            
            if os.path.exists(csv_path):
                logger.info("📊 Loading comprehensive test data from CSV...")
                df = pd.read_csv(csv_path)
                
                # timestampカラムをDatetimeIndexに変換
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df.set_index('timestamp', inplace=True)
                elif df.index.name != 'timestamp':
                    # 最初の列をtimestampとして使用
                    df.index = pd.to_datetime(df.iloc[:, 0])
                    df.index.name = 'timestamp'
                
                # 大規模テストデータ（500行で外部データ統合テスト）
                test_size = min(500, len(df))
                test_df = df.tail(test_size).copy()
                
                logger.info(f"✅ Comprehensive test data prepared: {len(test_df)} rows × {len(test_df.columns)} columns")
                return test_df
            else:
                # モックデータ生成（大規模）
                logger.warning("⚠️ CSV not found, generating comprehensive mock data...")
                return self._generate_comprehensive_mock_data()
                
        except Exception as e:
            logger.error(f"❌ Failed to prepare comprehensive test data: {e}")
            return self._generate_comprehensive_mock_data()
    
    def _generate_comprehensive_mock_data(self, n_rows: int = 500) -> pd.DataFrame:
        """包括的モックデータ生成"""
        dates = pd.date_range('2024-01-01', periods=n_rows, freq='H')
        
        # リアルな価格動作（ボラティリティクラスタリング含む）
        base_price = 50000.0
        returns = []
        vol = 0.02
        
        for i in range(n_rows):
            # ボラティリティクラスタリング効果
            vol = 0.95 * vol + 0.05 * np.abs(np.random.normal(0, 0.01))
            vol = max(0.005, min(0.05, vol))  # ボラティリティ制限
            
            ret = np.random.normal(0, vol)
            returns.append(ret)
        
        returns = np.array(returns)
        prices = base_price * np.exp(returns.cumsum())
        
        # 高・低価格の現実的な計算
        highs = prices * (1 + np.abs(np.random.normal(0, 0.003, n_rows)))
        lows = prices * (1 - np.abs(np.random.normal(0, 0.003, n_rows)))
        
        # OHLCV DataFrame作成
        df = pd.DataFrame({
            'timestamp': dates,
            'open': prices * (1 + np.random.normal(0, 0.0005, n_rows)),
            'high': highs,
            'low': lows,
            'close': prices,
            'volume': np.random.lognormal(10, 1.5, n_rows)  # 大きなボリューム変動
        })
        
        df.set_index('timestamp', inplace=True)
        
        logger.info(f"📊 Comprehensive mock data generated: {len(df)} rows with realistic price dynamics")
        return df
    
    def _get_expected_151_features(self) -> Set[str]:
        """期待される151特徴量リスト作成"""
        expected = set()
        
        # 基本カラム（OHLCV: 6個）
        base_columns = {"open", "high", "low", "close", "volume"}
        
        # ML設定から特徴量リストを動的生成
        extra_features = self.config.get("ml", {}).get("extra_features", [])
        feat_period = self.config.get("ml", {}).get("feat_period", 14)
        lags = self.config.get("ml", {}).get("lags", [1, 2, 3])
        rolling_window = self.config.get("ml", {}).get("rolling_window", 14)
        
        # 基本統計特徴量
        expected.add(f"ATR_{feat_period}")
        for lag in lags:
            expected.add(f"close_lag_{lag}")
        expected.add(f"close_mean_{rolling_window}")
        expected.add(f"close_std_{rolling_window}")
        
        # extra_featuresから特徴量を展開
        for feat in extra_features:
            feat_lc = feat.lower()
            
            # RSI系
            if feat_lc.startswith("rsi"):
                if "_" in feat_lc:
                    expected.add(feat_lc)
                else:
                    expected.update([f"rsi_{p}" for p in [7, 14, 21]])
            
            # SMA系
            elif feat_lc.startswith("sma"):
                if "_" in feat_lc:
                    expected.add(feat_lc)
                else:
                    expected.update([f"sma_{p}" for p in [10, 20, 50, 100, 200]])
            
            # EMA系
            elif feat_lc.startswith("ema"):
                if "_" in feat_lc:
                    expected.add(feat_lc)
                else:
                    expected.update([f"ema_{p}" for p in [10, 12, 26, 50, 100]])
            
            # ATR系
            elif feat_lc.startswith("atr"):
                if "_" in feat_lc:
                    expected.add(feat_lc)
                expected.add(f"atr_{feat_period}")
            
            # 複合指標
            elif feat_lc == "macd":
                expected.update(["macd", "macd_signal", "macd_hist"])
            elif feat_lc == "stoch":
                expected.update(["stoch_k", "stoch_d"])
            elif feat_lc == "adx":
                expected.add("adx")
            
            # 外部データ特徴量（フォールバック込み）
            elif feat_lc == "vix":
                expected.update([
                    "vix_level", "vix_change", "vix_zscore", "fear_level", 
                    "vix_spike", "vix_regime_numeric"
                ])
            elif feat_lc in ["macro", "dxy", "treasury"]:
                expected.update([
                    "dxy_level", "dxy_change", "dxy_zscore", "dxy_strength",
                    "treasury_10y_level", "treasury_10y_change", "treasury_10y_zscore", 
                    "treasury_regime", "yield_curve_spread", "risk_sentiment",
                    "usdjpy_level", "usdjpy_change", "usdjpy_volatility", 
                    "usdjpy_zscore", "usdjpy_trend", "usdjpy_strength"
                ])
            elif feat_lc == "fear_greed":
                expected.update([
                    "fg_index", "fg_change_1d", "fg_change_7d", "fg_ma_7", "fg_ma_30",
                    "fg_extreme_fear", "fg_fear", "fg_neutral", "fg_greed", "fg_extreme_greed",
                    "fg_volatility", "fg_momentum", "fg_reversal_signal"
                ])
            elif feat_lc == "funding":
                expected.update([
                    "funding_rate", "funding_rate_change", "funding_rate_ma", 
                    "funding_rate_zscore", "funding_trend", "open_interest",
                    "oi_change", "oi_trend"
                ])
        
        logger.info(f"🎯 Expected features compiled: {len(expected)} features")
        return expected
    
    def test_151_feature_complete_generation(self) -> Dict[str, Any]:
        """151特徴量完全生成テスト"""
        logger.info("🧪 Testing 151 Feature Complete Generation...")
        
        try:
            # バッチシステムでの特徴量生成
            fe_batch = FeatureEngineer(self.config)
            if hasattr(fe_batch, 'batch_engines_enabled'):
                fe_batch.batch_engines_enabled = True
            
            result_df = fe_batch.transform(self.test_data.copy())
            
            if result_df is not None:
                generated_features = set(result_df.columns) - set(self.test_data.columns)
                total_features = len(generated_features)
                
                # 特徴量分析
                missing_features = self.expected_features - generated_features
                extra_features = generated_features - self.expected_features
                
                # カテゴリ別分析
                technical_features = {f for f in generated_features if any(
                    f.startswith(prefix) for prefix in ['rsi_', 'sma_', 'ema_', 'atr_', 'macd', 'stoch', 'adx']
                )}
                external_features = {f for f in generated_features if any(
                    f.startswith(prefix) for prefix in ['vix_', 'dxy_', 'treasury_', 'fg_', 'funding_', 'usdjpy_', 'oi_']
                )}
                basic_features = {f for f in generated_features if any(
                    f.startswith(prefix) for prefix in ['close_lag_', 'close_mean_', 'close_std_', 'ATR_']
                )}
                
                feature_test_results = {
                    "total_features_generated": total_features,
                    "expected_features_count": len(self.expected_features),
                    "target_151_achieved": total_features >= 151,
                    "feature_coverage_percent": (len(generated_features & self.expected_features) / len(self.expected_features)) * 100,
                    "missing_features": list(missing_features),
                    "extra_features": list(extra_features),
                    "missing_count": len(missing_features),
                    "extra_count": len(extra_features),
                    "category_breakdown": {
                        "technical_indicators": len(technical_features),
                        "external_data": len(external_features), 
                        "basic_statistics": len(basic_features),
                        "other_features": total_features - len(technical_features) - len(external_features) - len(basic_features)
                    },
                    "success": total_features >= 151 and len(missing_features) <= 5  # 許容誤差5特徴量
                }
                
                self.results["feature_integrity"]["complete_generation"] = feature_test_results
                
                logger.info(f"📊 Feature Generation Results:")
                logger.info(f"  • Total Features: {total_features} (Target: 151)")
                logger.info(f"  • Missing Features: {len(missing_features)}")
                logger.info(f"  • Extra Features: {len(extra_features)}")
                logger.info(f"  • Technical Indicators: {len(technical_features)}")
                logger.info(f"  • External Data: {len(external_features)}")
                logger.info(f"  • Success: {'✅' if feature_test_results['success'] else '❌'}")
                
                return feature_test_results
            else:
                error_result = {"error": "Feature generation returned None", "success": False}
                self.results["feature_integrity"]["complete_generation"] = error_result
                return error_result
                
        except Exception as e:
            error_result = {
                "error": str(e),
                "traceback": traceback.format_exc(),
                "success": False
            }
            self.results["feature_integrity"]["complete_generation"] = error_result
            logger.error(f"❌ 151 feature generation test failed: {e}")
            return error_result
    
    def test_batch_vs_legacy_consistency(self) -> Dict[str, Any]:
        """バッチ vs レガシーシステム一貫性テスト"""
        logger.info("🔄 Testing Batch vs Legacy System Consistency...")
        
        try:
            # バッチシステム
            fe_batch = FeatureEngineer(self.config)
            if hasattr(fe_batch, 'batch_engines_enabled'):
                fe_batch.batch_engines_enabled = True
            
            batch_result = fe_batch.transform(self.test_data.copy())
            
            # レガシーシステム
            fe_legacy = FeatureEngineer(self.config)
            if hasattr(fe_legacy, 'batch_engines_enabled'):
                fe_legacy.batch_engines_enabled = False
            
            legacy_result = fe_legacy.transform(self.test_data.copy())
            
            if batch_result is not None and legacy_result is not None:
                # 共通特徴量の特定
                batch_features = set(batch_result.columns) - set(self.test_data.columns)
                legacy_features = set(legacy_result.columns) - set(self.test_data.columns)
                
                common_features = batch_features & legacy_features
                batch_only = batch_features - legacy_features
                legacy_only = legacy_features - batch_features
                
                # 数値一致度チェック
                consistency_issues = []
                feature_correlations = {}
                
                for feature in common_features:
                    if feature in batch_result.columns and feature in legacy_result.columns:
                        batch_series = batch_result[feature].dropna()
                        legacy_series = legacy_result[feature].dropna()
                        
                        if len(batch_series) > 0 and len(legacy_series) > 0:
                            # 相関係数計算
                            correlation = batch_series.corr(legacy_series)
                            feature_correlations[feature] = correlation
                            
                            # 許容誤差チェック（相関係数0.99以上を期待）
                            if correlation < 0.99:
                                mean_diff = abs(batch_series.mean() - legacy_series.mean())
                                consistency_issues.append({
                                    "feature": feature,
                                    "correlation": correlation,
                                    "mean_difference": mean_diff
                                })
                
                avg_correlation = np.mean(list(feature_correlations.values())) if feature_correlations else 0
                
                consistency_results = {
                    "batch_features_count": len(batch_features),
                    "legacy_features_count": len(legacy_features),
                    "common_features_count": len(common_features),
                    "batch_only_features": list(batch_only),
                    "legacy_only_features": list(legacy_only),
                    "batch_only_count": len(batch_only),
                    "legacy_only_count": len(legacy_only),
                    "average_correlation": avg_correlation,
                    "consistency_issues_count": len(consistency_issues),
                    "consistency_issues": consistency_issues[:10],  # 最初の10件のみ保存
                    "high_consistency_features": len([c for c in feature_correlations.values() if c >= 0.99]),
                    "success": len(consistency_issues) <= 5 and avg_correlation >= 0.95  # 許容基準
                }
                
                self.results["feature_integrity"]["batch_vs_legacy"] = consistency_results
                
                logger.info(f"🔄 Consistency Test Results:")
                logger.info(f"  • Common Features: {len(common_features)}")
                logger.info(f"  • Avg Correlation: {avg_correlation:.4f}")
                logger.info(f"  • Consistency Issues: {len(consistency_issues)}")
                logger.info(f"  • High Consistency: {consistency_results['high_consistency_features']}")
                logger.info(f"  • Success: {'✅' if consistency_results['success'] else '❌'}")
                
                return consistency_results
            else:
                error_result = {"error": "One or both systems failed to generate features", "success": False}
                self.results["feature_integrity"]["batch_vs_legacy"] = error_result
                return error_result
                
        except Exception as e:
            error_result = {
                "error": str(e),
                "traceback": traceback.format_exc(),
                "success": False
            }
            self.results["feature_integrity"]["batch_vs_legacy"] = error_result
            logger.error(f"❌ Batch vs legacy consistency test failed: {e}")
            return error_result
    
    def test_error_handling_robustness(self) -> Dict[str, Any]:
        """エラーハンドリング堅牢性テスト"""
        logger.info("🛡️ Testing Error Handling Robustness...")
        
        error_scenarios = []
        
        try:
            # シナリオ1: 空データフレーム
            try:
                empty_df = pd.DataFrame()
                fe = FeatureEngineer(self.config)
                if hasattr(fe, 'batch_engines_enabled'):
                    fe.batch_engines_enabled = True
                result = fe.transform(empty_df)
                error_scenarios.append({
                    "scenario": "empty_dataframe",
                    "success": result is not None,
                    "error": None
                })
            except Exception as e:
                error_scenarios.append({
                    "scenario": "empty_dataframe",
                    "success": False,
                    "error": str(e)
                })
            
            # シナリオ2: 不足カラム（closeなし）
            try:
                incomplete_df = self.test_data[['open', 'high', 'low', 'volume']].copy()
                fe = FeatureEngineer(self.config)
                if hasattr(fe, 'batch_engines_enabled'):
                    fe.batch_engines_enabled = True
                result = fe.transform(incomplete_df)
                error_scenarios.append({
                    "scenario": "missing_close_column",
                    "success": result is not None,
                    "error": None
                })
            except Exception as e:
                error_scenarios.append({
                    "scenario": "missing_close_column",
                    "success": False,
                    "error": str(e)
                })
            
            # シナリオ3: NaN値大量データ
            try:
                nan_df = self.test_data.copy()
                # 50%のデータをNaNに
                mask = np.random.rand(*nan_df.shape) < 0.5
                nan_df = nan_df.mask(mask)
                
                fe = FeatureEngineer(self.config)
                if hasattr(fe, 'batch_engines_enabled'):
                    fe.batch_engines_enabled = True
                result = fe.transform(nan_df)
                error_scenarios.append({
                    "scenario": "heavy_nan_data",
                    "success": result is not None and not result.isnull().all().all(),
                    "error": None
                })
            except Exception as e:
                error_scenarios.append({
                    "scenario": "heavy_nan_data",
                    "success": False,
                    "error": str(e)
                })
            
            # シナリオ4: 外部データフェッチャー障害シミュレーション
            try:
                with patch('crypto_bot.data.vix_fetcher.VIXDataFetcher') as mock_vix:
                    mock_vix.side_effect = Exception("Simulated VIX API failure")
                    
                    fe = FeatureEngineer(self.config)
                    if hasattr(fe, 'batch_engines_enabled'):
                        fe.batch_engines_enabled = True
                    result = fe.transform(self.test_data.copy())
                    error_scenarios.append({
                        "scenario": "external_data_failure",
                        "success": result is not None,
                        "error": None
                    })
            except Exception as e:
                error_scenarios.append({
                    "scenario": "external_data_failure",
                    "success": False,
                    "error": str(e)
                })
            
            # 結果集計
            successful_scenarios = [s for s in error_scenarios if s["success"]]
            failed_scenarios = [s for s in error_scenarios if not s["success"]]
            
            error_handling_results = {
                "total_scenarios_tested": len(error_scenarios),
                "successful_scenarios": len(successful_scenarios),
                "failed_scenarios": len(failed_scenarios),
                "success_rate": len(successful_scenarios) / len(error_scenarios) if error_scenarios else 0,
                "scenarios_detail": error_scenarios,
                "robustness_score": len(successful_scenarios) / len(error_scenarios) if error_scenarios else 0,
                "success": len(successful_scenarios) >= len(error_scenarios) * 0.75  # 75%成功率期待
            }
            
            self.results["error_handling"]["robustness"] = error_handling_results
            
            logger.info(f"🛡️ Error Handling Test Results:")
            logger.info(f"  • Scenarios Tested: {len(error_scenarios)}")
            logger.info(f"  • Successful: {len(successful_scenarios)}")
            logger.info(f"  • Failed: {len(failed_scenarios)}")
            logger.info(f"  • Success Rate: {error_handling_results['success_rate']:.2%}")
            logger.info(f"  • Success: {'✅' if error_handling_results['success'] else '❌'}")
            
            return error_handling_results
            
        except Exception as e:
            error_result = {
                "error": str(e),
                "traceback": traceback.format_exc(),
                "success": False
            }
            self.results["error_handling"]["robustness"] = error_result
            logger.error(f"❌ Error handling robustness test failed: {e}")
            return error_result
    
    def test_external_data_quality(self) -> Dict[str, Any]:
        """外部データ品質テスト"""
        logger.info("📡 Testing External Data Quality...")
        
        try:
            # 外部データエンジン初期化
            batch_calc = BatchFeatureCalculator(self.config)
            external_integrator = ExternalDataIntegrator(self.config, batch_calc)
            
            # 外部データ統合テスト
            external_batches = external_integrator.create_external_data_batches(self.test_data.index)
            
            # 各ソース別品質評価
            source_quality = {}
            total_external_features = 0
            
            for batch in external_batches:
                source_name = batch.batch_name.replace('_batch', '')
                features_count = len(batch)
                
                # データ品質評価
                if len(batch) > 0:
                    # NaN率チェック
                    nan_rates = {}
                    for feature_name, feature_series in batch.data.items():
                        if isinstance(feature_series, pd.Series):
                            nan_rate = feature_series.isnull().sum() / len(feature_series)
                            nan_rates[feature_name] = nan_rate
                    
                    avg_nan_rate = np.mean(list(nan_rates.values())) if nan_rates else 0
                    
                    source_quality[source_name] = {
                        "features_count": features_count,
                        "avg_nan_rate": avg_nan_rate,
                        "high_quality_features": len([r for r in nan_rates.values() if r <= 0.1]),
                        "poor_quality_features": len([r for r in nan_rates.values() if r > 0.5]),
                        "quality_score": max(0, 1 - avg_nan_rate),
                        "success": avg_nan_rate <= 0.3  # 30%以下のNaN率を期待
                    }
                else:
                    source_quality[source_name] = {
                        "features_count": 0,
                        "avg_nan_rate": 1.0,
                        "high_quality_features": 0,
                        "poor_quality_features": 0,
                        "quality_score": 0,
                        "success": False
                    }
                
                total_external_features += features_count
            
            # 統合統計取得
            integration_stats = external_integrator.get_integration_stats()
            
            external_data_results = {
                "total_external_features": total_external_features,
                "sources_tested": len(source_quality),
                "successful_sources": len([s for s in source_quality.values() if s["success"]]),
                "source_quality_detail": source_quality,
                "integration_stats": integration_stats,
                "overall_quality_score": np.mean([s["quality_score"] for s in source_quality.values()]) if source_quality else 0,
                "success": len([s for s in source_quality.values() if s["success"]]) >= len(source_quality) * 0.5  # 50%のソース成功期待
            }
            
            self.results["external_data_quality"]["integration_test"] = external_data_results
            
            logger.info(f"📡 External Data Quality Results:")
            logger.info(f"  • Total External Features: {total_external_features}")
            logger.info(f"  • Sources Tested: {len(source_quality)}")
            logger.info(f"  • Successful Sources: {external_data_results['successful_sources']}")
            logger.info(f"  • Overall Quality Score: {external_data_results['overall_quality_score']:.3f}")
            logger.info(f"  • Success: {'✅' if external_data_results['success'] else '❌'}")
            
            return external_data_results
            
        except Exception as e:
            error_result = {
                "error": str(e),
                "traceback": traceback.format_exc(),
                "success": False
            }
            self.results["external_data_quality"]["integration_test"] = error_result
            logger.error(f"❌ External data quality test failed: {e}")
            return error_result
    
    def test_edge_case_handling(self) -> Dict[str, Any]:
        """エッジケース処理テスト"""
        logger.info("🔬 Testing Edge Case Handling...")
        
        edge_cases = []
        
        try:
            # エッジケース1: 極小データセット（10行）
            try:
                tiny_df = self.test_data.head(10).copy()
                fe = FeatureEngineer(self.config)
                if hasattr(fe, 'batch_engines_enabled'):
                    fe.batch_engines_enabled = True
                result = fe.transform(tiny_df)
                edge_cases.append({
                    "case": "tiny_dataset_10_rows",
                    "success": result is not None and len(result) > 0,
                    "features_generated": len(result.columns) - len(tiny_df.columns) if result is not None else 0,
                    "error": None
                })
            except Exception as e:
                edge_cases.append({
                    "case": "tiny_dataset_10_rows",
                    "success": False,
                    "features_generated": 0,
                    "error": str(e)
                })
            
            # エッジケース2: 価格ボラティリティ極大（500%日次変動）
            try:
                extreme_vol_df = self.test_data.copy()
                # 極端なボラティリティ作成
                extreme_returns = np.random.normal(0, 5, len(extreme_vol_df))  # 500%年率ボラティリティ
                extreme_vol_df['close'] = extreme_vol_df['close'].iloc[0] * np.exp(extreme_returns.cumsum())
                extreme_vol_df['high'] = extreme_vol_df['close'] * 1.1
                extreme_vol_df['low'] = extreme_vol_df['close'] * 0.9
                
                fe = FeatureEngineer(self.config)
                if hasattr(fe, 'batch_engines_enabled'):
                    fe.batch_engines_enabled = True
                result = fe.transform(extreme_vol_df)
                
                # 無限大・NaN値チェック
                has_inf = np.isinf(result.select_dtypes(include=[np.number])).any().any() if result is not None else True
                has_extreme_nan = result.isnull().sum().sum() > len(result) * 0.8 if result is not None else True
                
                edge_cases.append({
                    "case": "extreme_volatility",
                    "success": result is not None and not has_inf and not has_extreme_nan,
                    "features_generated": len(result.columns) - len(extreme_vol_df.columns) if result is not None else 0,
                    "has_infinity": has_inf,
                    "extreme_nan_rate": result.isnull().sum().sum() / result.size if result is not None else 1,
                    "error": None
                })
            except Exception as e:
                edge_cases.append({
                    "case": "extreme_volatility",
                    "success": False,
                    "features_generated": 0,
                    "error": str(e)
                })
            
            # エッジケース3: 価格フラット（変動なし）
            try:
                flat_df = self.test_data.copy()
                flat_price = flat_df['close'].mean()
                flat_df['open'] = flat_price
                flat_df['high'] = flat_price
                flat_df['low'] = flat_price
                flat_df['close'] = flat_price
                flat_df['volume'] = flat_df['volume'].mean()  # ボリュームは正常維持
                
                fe = FeatureEngineer(self.config)
                if hasattr(fe, 'batch_engines_enabled'):
                    fe.batch_engines_enabled = True
                result = fe.transform(flat_df)
                edge_cases.append({
                    "case": "flat_prices_no_volatility",
                    "success": result is not None and len(result.columns) > len(flat_df.columns),
                    "features_generated": len(result.columns) - len(flat_df.columns) if result is not None else 0,
                    "error": None
                })
            except Exception as e:
                edge_cases.append({
                    "case": "flat_prices_no_volatility",
                    "success": False,
                    "features_generated": 0,
                    "error": str(e)
                })
            
            # エッジケース4: 混合データ型（文字列混在）
            try:
                mixed_df = self.test_data.copy()
                # 一部の数値を文字列に変更（現実のデータエラーシミュレーション）
                mixed_df.loc[mixed_df.index[::10], 'close'] = 'invalid_price'
                mixed_df.loc[mixed_df.index[5::15], 'volume'] = 'NaN'
                
                fe = FeatureEngineer(self.config)
                if hasattr(fe, 'batch_engines_enabled'):
                    fe.batch_engines_enabled = True
                result = fe.transform(mixed_df)
                edge_cases.append({
                    "case": "mixed_data_types",
                    "success": result is not None,
                    "features_generated": len(result.columns) - len(self.test_data.columns) if result is not None else 0,
                    "error": None
                })
            except Exception as e:
                edge_cases.append({
                    "case": "mixed_data_types",
                    "success": False,
                    "features_generated": 0,
                    "error": str(e)
                })
            
            # 結果集計
            successful_cases = [c for c in edge_cases if c["success"]]
            failed_cases = [c for c in edge_cases if not c["success"]]
            
            edge_case_results = {
                "total_edge_cases_tested": len(edge_cases),
                "successful_cases": len(successful_cases),
                "failed_cases": len(failed_cases),
                "success_rate": len(successful_cases) / len(edge_cases) if edge_cases else 0,
                "cases_detail": edge_cases,
                "avg_features_generated": np.mean([c.get("features_generated", 0) for c in successful_cases]) if successful_cases else 0,
                "robustness_score": len(successful_cases) / len(edge_cases) if edge_cases else 0,
                "success": len(successful_cases) >= len(edge_cases) * 0.75  # 75%成功率期待
            }
            
            self.results["edge_case_handling"]["comprehensive_test"] = edge_case_results
            
            logger.info(f"🔬 Edge Case Handling Results:")
            logger.info(f"  • Cases Tested: {len(edge_cases)}")
            logger.info(f"  • Successful: {len(successful_cases)}")
            logger.info(f"  • Failed: {len(failed_cases)}")
            logger.info(f"  • Success Rate: {edge_case_results['success_rate']:.2%}")
            logger.info(f"  • Avg Features Generated: {edge_case_results['avg_features_generated']:.1f}")
            logger.info(f"  • Success: {'✅' if edge_case_results['success'] else '❌'}")
            
            return edge_case_results
            
        except Exception as e:
            error_result = {
                "error": str(e),
                "traceback": traceback.format_exc(),
                "success": False
            }
            self.results["edge_case_handling"]["comprehensive_test"] = error_result
            logger.error(f"❌ Edge case handling test failed: {e}")
            return error_result
    
    def calculate_overall_assessment(self):
        """総合評価計算"""
        assessments = {
            "feature_integrity": self.results.get("feature_integrity", {}),
            "error_handling": self.results.get("error_handling", {}),
            "external_data_quality": self.results.get("external_data_quality", {}),
            "edge_case_handling": self.results.get("edge_case_handling", {})
        }
        
        # 各テストカテゴリの成功状況
        category_scores = {}
        for category, tests in assessments.items():
            if tests:
                successes = [test.get("success", False) for test in tests.values() if isinstance(test, dict)]
                category_scores[category] = sum(successes) / len(successes) if successes else 0
            else:
                category_scores[category] = 0
        
        # 重み付け評価
        weights = {
            "feature_integrity": 0.4,  # 特徴量整合性が最重要
            "error_handling": 0.2,
            "external_data_quality": 0.2,
            "edge_case_handling": 0.2
        }
        
        overall_score = sum(category_scores[cat] * weights[cat] for cat in weights)
        
        # 品質レベル判定
        if overall_score >= 0.9:
            quality_level = "Excellent"
        elif overall_score >= 0.75:
            quality_level = "Good"
        elif overall_score >= 0.6:
            quality_level = "Acceptable"
        else:
            quality_level = "Needs Improvement"
        
        overall_assessment = {
            "overall_score": overall_score,
            "quality_level": quality_level,
            "category_scores": category_scores,
            "total_tests_run": sum(len(tests) for tests in assessments.values() if tests),
            "total_successful_tests": sum(
                sum(test.get("success", False) for test in tests.values() if isinstance(test, dict))
                for tests in assessments.values() if tests
            ),
            "recommendation": self._generate_recommendation(overall_score, category_scores),
            "ready_for_production": overall_score >= 0.75
        }
        
        self.results["overall_assessment"] = overall_assessment
        
        logger.info(f"🎯 Overall Assessment:")
        logger.info(f"  • Overall Score: {overall_score:.3f}")
        logger.info(f"  • Quality Level: {quality_level}")
        logger.info(f"  • Production Ready: {'✅' if overall_assessment['ready_for_production'] else '❌'}")
        
        return overall_assessment
    
    def _generate_recommendation(self, overall_score: float, category_scores: Dict[str, float]) -> str:
        """推奨事項生成"""
        recommendations = []
        
        if category_scores.get("feature_integrity", 0) < 0.8:
            recommendations.append("特徴量整合性の向上が必要")
        
        if category_scores.get("error_handling", 0) < 0.7:
            recommendations.append("エラーハンドリングの強化が必要")
        
        if category_scores.get("external_data_quality", 0) < 0.6:
            recommendations.append("外部データ統合の安定化が必要")
        
        if category_scores.get("edge_case_handling", 0) < 0.7:
            recommendations.append("エッジケース対応の改善が必要")
        
        if overall_score >= 0.9:
            recommendations.append("システムは本番環境でも安定動作する見込み")
        elif overall_score >= 0.75:
            recommendations.append("軽微な調整後に本番移行が可能")
        else:
            recommendations.append("重要な修正が必要 - 本番移行は要検討")
        
        return "; ".join(recommendations)
    
    def save_results(self, output_path: str = "/Users/nao/Desktop/bot/test_results/feature_integrity_quality_test.json"):
        """結果保存"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"💾 Feature integrity test results saved to: {output_path}")
        except Exception as e:
            logger.error(f"❌ Failed to save results: {e}")
    
    def run_comprehensive_quality_test(self):
        """包括的品質テスト実行"""
        logger.info("🧪 Starting Phase B2.6.2: Feature Integrity & Quality Test...")
        
        # 各テスト実行
        logger.info("=" * 80)
        self.test_151_feature_complete_generation()
        
        logger.info("=" * 80)
        self.test_batch_vs_legacy_consistency()
        
        logger.info("=" * 80)
        self.test_error_handling_robustness()
        
        logger.info("=" * 80)
        self.test_external_data_quality()
        
        logger.info("=" * 80)
        self.test_edge_case_handling()
        
        # 総合評価
        logger.info("=" * 80)
        self.calculate_overall_assessment()
        
        # 結果保存
        self.save_results()
        
        logger.info("🎉 Phase B2.6.2: Feature Integrity & Quality Test Completed!")
        
        return self.results


def main():
    """メイン実行"""
    try:
        tester = FeatureIntegrityTester()
        results = tester.run_comprehensive_quality_test()
        
        # サマリー表示
        print("\n" + "=" * 80)
        print("🎯 PHASE B2.6.2: FEATURE INTEGRITY & QUALITY TEST RESULTS")
        print("=" * 80)
        
        overall = results.get("overall_assessment", {})
        if overall:
            print(f"🎯 Overall Score: {overall.get('overall_score', 0):.3f}")
            print(f"📊 Quality Level: {overall.get('quality_level', 'Unknown')}")
            print(f"🚀 Production Ready: {'✅ YES' if overall.get('ready_for_production', False) else '❌ NO'}")
            print(f"💡 Recommendation: {overall.get('recommendation', 'No recommendation')}")
            
            print("\n📈 Category Scores:")
            for category, score in overall.get("category_scores", {}).items():
                print(f"  • {category.replace('_', ' ').title()}: {score:.3f}")
        else:
            print("❌ TEST FAILED: Could not complete comprehensive assessment")
        
        print("=" * 80)
        return results
        
    except Exception as e:
        logger.error(f"❌ Test execution failed: {e}")
        return None


if __name__ == "__main__":
    main()