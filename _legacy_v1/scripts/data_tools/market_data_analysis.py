#!/usr/bin/env python3
"""
市場データ分析・ボラティリティ分布調査・適正閾値決定
Phase 1: 戦略見直しでの実トレードエントリー実現
"""

import json
import logging
import sys
import warnings
from datetime import datetime, timedelta
from pathlib import Path

warnings.filterwarnings("ignore")

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import ccxt
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MarketDataAnalyzer:
    """市場データ分析・適正閾値決定システム"""

    def __init__(self):
        """分析システム初期化"""
        self.exchange = ccxt.bitbank()
        self.analysis_results = {}

        # 結果保存ディレクトリ
        self.output_dir = Path(project_root / "results" / "market_analysis")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 現在の設定値
        self.current_threshold = 0.05  # 5%
        self.target_monthly_trades = 15  # 月15回目標

        logger.info("Market Data Analyzer initialized")

    def run_comprehensive_analysis(self):
        """包括的市場分析実行"""
        print("📊 市場データ分析・ボラティリティ分布調査開始")
        print("=" * 80)

        try:
            # Phase 1: データ収集
            print("\n📈 Phase 1: 過去1ヶ月データ収集")
            print("-" * 50)
            market_data = self._collect_historical_data()

            # Phase 2: ボラティリティ分析
            print("\n📊 Phase 2: ボラティリティ分布分析")
            print("-" * 50)
            volatility_analysis = self._analyze_volatility_distribution(market_data)

            # Phase 3: 適正閾値範囲特定
            print("\n🎯 Phase 3: 適正閾値範囲特定")
            print("-" * 50)
            threshold_analysis = self._determine_optimal_threshold_range(
                market_data, volatility_analysis
            )

            # Phase 4: 取引機会分析
            print("\n💹 Phase 4: 取引機会分析")
            print("-" * 50)
            opportunity_analysis = self._analyze_trading_opportunities(
                market_data, threshold_analysis
            )

            # Phase 5: 推奨閾値決定
            print("\n🎯 Phase 5: 推奨閾値決定")
            print("-" * 50)
            recommendations = self._generate_threshold_recommendations(
                market_data,
                volatility_analysis,
                threshold_analysis,
                opportunity_analysis,
            )

            # 結果統合・保存
            print("\n💾 分析結果保存")
            print("-" * 50)
            self._save_analysis_results(
                {
                    "market_data": market_data,
                    "volatility_analysis": volatility_analysis,
                    "threshold_analysis": threshold_analysis,
                    "opportunity_analysis": opportunity_analysis,
                    "recommendations": recommendations,
                }
            )

            print("\n✅ 市場データ分析完了")

        except Exception as e:
            logger.error(f"Market analysis failed: {e}")
            print(f"\n❌ エラー: {e}")

    def _collect_historical_data(self):
        """過去1ヶ月の履歴データ収集"""
        print("  📥 BTC/JPY 1ヶ月間データ取得中...")

        # 過去30日間のデータ取得
        end_time = datetime.now()
        start_time = end_time - timedelta(days=30)

        # 1時間足データ取得
        since = int(start_time.timestamp() * 1000)
        ohlcv_data = []

        # ページネーション対応
        limit = 500  # Bitbank API制限
        while since < int(end_time.timestamp() * 1000):
            try:
                ohlcv = self.exchange.fetch_ohlcv(
                    "BTC/JPY", "1h", since=since, limit=limit
                )
                if not ohlcv:
                    break

                ohlcv_data.extend(ohlcv)
                since = ohlcv[-1][0] + 3600000  # 1時間追加

                # レート制限対応
                import time

                time.sleep(0.5)

            except Exception as e:
                logger.warning(f"Data fetch error: {e}")
                break

        # DataFrame化
        df = pd.DataFrame(
            ohlcv_data, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.drop_duplicates(subset=["timestamp"]).reset_index(drop=True)

        # 技術指標計算
        df["returns"] = df["close"].pct_change()
        df["volatility_1h"] = df["returns"].abs()  # 絶対値変動率を使用
        df["volatility_6h"] = df["returns"].rolling(window=6).std().fillna(0)
        df["volatility_24h"] = df["returns"].rolling(window=24).std().fillna(0)

        # 価格変動幅
        df["price_range"] = (df["high"] - df["low"]) / df["close"]

        # 移動平均
        df["sma_12"] = df["close"].rolling(window=12).mean()
        df["sma_24"] = df["close"].rolling(window=24).mean()

        # RSI
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df["rsi"] = 100 - (100 / (1 + rs))

        market_data = {
            "df": df,
            "total_hours": len(df),
            "date_range": f"{df['timestamp'].min()} to {df['timestamp'].max()}",
            "avg_price": df["close"].mean(),
            "price_std": df["close"].std(),
            "total_volume": df["volume"].sum(),
        }

        print(f"  ✅ データ取得完了: {len(df)} 時間分")
        print(f"  📅 期間: {market_data['date_range']}")
        print(f"  💰 平均価格: {market_data['avg_price']:,.0f} JPY")

        return market_data

    def _analyze_volatility_distribution(self, market_data):
        """ボラティリティ分布分析"""
        print("  📊 ボラティリティ分析実行中...")

        df = market_data["df"]

        # 基本統計
        volatility_stats = {
            "1h_volatility": {
                "mean": df["volatility_1h"].mean() * 100,
                "std": df["volatility_1h"].std() * 100,
                "min": df["volatility_1h"].min() * 100,
                "max": df["volatility_1h"].max() * 100,
                "median": df["volatility_1h"].median() * 100,
                "q25": df["volatility_1h"].quantile(0.25) * 100,
                "q75": df["volatility_1h"].quantile(0.75) * 100,
                "q90": df["volatility_1h"].quantile(0.90) * 100,
                "q95": df["volatility_1h"].quantile(0.95) * 100,
            },
            "24h_volatility": {
                "mean": df["volatility_24h"].mean() * 100,
                "std": df["volatility_24h"].std() * 100,
                "median": df["volatility_24h"].median() * 100,
                "q75": df["volatility_24h"].quantile(0.75) * 100,
                "q90": df["volatility_24h"].quantile(0.90) * 100,
            },
        }

        # 現在の閾値vs市場実態
        current_vs_market = {
            "current_threshold_pct": self.current_threshold * 100,
            "market_volatility_mean": volatility_stats["1h_volatility"]["mean"],
            "threshold_vs_market_ratio": (self.current_threshold * 100)
            / volatility_stats["1h_volatility"]["mean"],
            "market_exceeds_threshold_pct": (
                df["volatility_1h"] * 100 > self.current_threshold * 100
            ).mean()
            * 100,
        }

        # 高ボラティリティ期間の特定
        high_vol_periods = df[
            df["volatility_1h"] > df["volatility_1h"].quantile(0.9)
        ].copy()

        volatility_analysis = {
            "stats": volatility_stats,
            "current_vs_market": current_vs_market,
            "high_volatility_periods": len(high_vol_periods),
            "high_vol_characteristics": {
                "avg_return": (
                    high_vol_periods["returns"].mean() * 100
                    if len(high_vol_periods) > 0
                    else 0
                ),
                "avg_volume": (
                    high_vol_periods["volume"].mean()
                    if len(high_vol_periods) > 0
                    else 0
                ),
            },
        }

        print(f"  ✅ ボラティリティ分析完了")
        print(f"    📈 平均1h変動: {volatility_stats['1h_volatility']['mean']:.3f}%")
        print(f"    📊 現在閾値: {self.current_threshold*100:.1f}%")
        print(
            f"    ⚖️ 閾値/市場比: {current_vs_market['threshold_vs_market_ratio']:.1f}倍"
        )
        print(
            f"    🎯 閾値超過率: {current_vs_market['market_exceeds_threshold_pct']:.1f}%"
        )

        return volatility_analysis

    def _determine_optimal_threshold_range(self, market_data, volatility_analysis):
        """適正閾値範囲特定"""
        print("  🎯 適正閾値範囲分析中...")

        df = market_data["df"]

        # 候補閾値設定
        candidate_thresholds = [
            0.005,
            0.01,
            0.015,
            0.02,
            0.025,
            0.03,
            0.035,
            0.04,
            0.045,
            0.05,
        ]
        threshold_analysis = {}

        for threshold in candidate_thresholds:
            # 各閾値での取引機会分析
            opportunities = (df["volatility_1h"] > threshold).sum()
            opportunity_rate = opportunities / len(df) * 100
            monthly_trades = opportunities / 30 * 30  # 月換算

            # リスク分析
            high_vol_returns = df[df["volatility_1h"] > threshold]["returns"]
            if len(high_vol_returns) > 0:
                avg_return = high_vol_returns.mean()
                return_std = high_vol_returns.std()
                positive_rate = (high_vol_returns > 0).mean()
            else:
                avg_return = 0
                return_std = 0
                positive_rate = 0

            threshold_analysis[f"{threshold*100:.1f}%"] = {
                "threshold": threshold,
                "opportunities": opportunities,
                "opportunity_rate": opportunity_rate,
                "monthly_trades_estimate": monthly_trades,
                "avg_return": avg_return * 100,
                "return_volatility": return_std * 100,
                "positive_rate": positive_rate * 100,
                "risk_reward_ratio": (
                    abs(avg_return / return_std) if return_std > 0 else 0
                ),
            }

        # 最適閾値候補特定
        optimal_candidates = []
        for key, analysis in threshold_analysis.items():
            if (
                analysis["monthly_trades_estimate"] >= 10
                and analysis["monthly_trades_estimate"] <= 25
                and analysis["positive_rate"] >= 45
            ):
                optimal_candidates.append(
                    {
                        "threshold": analysis["threshold"],
                        "threshold_pct": key,
                        "monthly_trades": analysis["monthly_trades_estimate"],
                        "positive_rate": analysis["positive_rate"],
                        "risk_reward": analysis["risk_reward_ratio"],
                    }
                )

        print(f"  ✅ 閾値分析完了: {len(candidate_thresholds)}パターン検証")
        print(f"  🎯 最適候補: {len(optimal_candidates)}個特定")

        return {
            "candidate_analysis": threshold_analysis,
            "optimal_candidates": optimal_candidates,
            "analysis_summary": {
                "total_analyzed": len(candidate_thresholds),
                "viable_options": len(optimal_candidates),
            },
        }

    def _analyze_trading_opportunities(self, market_data, threshold_analysis):
        """取引機会分析"""
        print("  💹 取引機会詳細分析中...")

        df = market_data["df"]

        # 時間帯別分析
        df["hour"] = df["timestamp"].dt.hour
        hourly_volatility = (
            df.groupby("hour")["volatility_1h"]
            .agg(["mean", "std", "count"])
            .reset_index()
        )
        hourly_volatility["volatility_mean_pct"] = hourly_volatility["mean"] * 100

        # 曜日別分析
        df["weekday"] = df["timestamp"].dt.dayofweek
        daily_volatility = (
            df.groupby("weekday")["volatility_1h"]
            .agg(["mean", "std", "count"])
            .reset_index()
        )
        daily_volatility["volatility_mean_pct"] = daily_volatility["mean"] * 100

        # トレンド方向別分析
        df["trend_direction"] = np.where(
            df["close"] > df["sma_24"], "uptrend", "downtrend"
        )

        # シンプルな集計に変更
        uptrend_data = df[df["trend_direction"] == "uptrend"]
        downtrend_data = df[df["trend_direction"] == "downtrend"]

        trend_analysis = [
            {
                "trend": "uptrend",
                "volatility_mean": (
                    uptrend_data["volatility_1h"].mean() if len(uptrend_data) > 0 else 0
                ),
                "returns_mean": (
                    uptrend_data["returns"].mean() if len(uptrend_data) > 0 else 0
                ),
                "volume_mean": (
                    uptrend_data["volume"].mean() if len(uptrend_data) > 0 else 0
                ),
                "count": len(uptrend_data),
            },
            {
                "trend": "downtrend",
                "volatility_mean": (
                    downtrend_data["volatility_1h"].mean()
                    if len(downtrend_data) > 0
                    else 0
                ),
                "returns_mean": (
                    downtrend_data["returns"].mean() if len(downtrend_data) > 0 else 0
                ),
                "volume_mean": (
                    downtrend_data["volume"].mean() if len(downtrend_data) > 0 else 0
                ),
                "count": len(downtrend_data),
            },
        ]

        opportunity_analysis = {
            "hourly_patterns": hourly_volatility.to_dict("records"),
            "daily_patterns": daily_volatility.to_dict("records"),
            "trend_analysis": trend_analysis,
            "best_trading_hours": hourly_volatility.nlargest(3, "volatility_mean_pct")[
                "hour"
            ].tolist(),
            "best_trading_days": daily_volatility.nlargest(3, "volatility_mean_pct")[
                "weekday"
            ].tolist(),
        }

        print(f"  ✅ 取引機会分析完了")
        print(f"  ⏰ 高ボラ時間帯: {opportunity_analysis['best_trading_hours']}")
        print(f"  📅 高ボラ曜日: {opportunity_analysis['best_trading_days']}")

        return opportunity_analysis

    def _generate_threshold_recommendations(
        self, market_data, volatility_analysis, threshold_analysis, opportunity_analysis
    ):
        """推奨閾値決定"""
        print("  🎯 推奨閾値決定中...")

        optimal_candidates = threshold_analysis["optimal_candidates"]

        if not optimal_candidates:
            # フォールバック: より緩い条件で再検索
            fallback_candidates = []
            for key, analysis in threshold_analysis["candidate_analysis"].items():
                if analysis["monthly_trades_estimate"] >= 5:
                    fallback_candidates.append(
                        {
                            "threshold": analysis["threshold"],
                            "threshold_pct": key,
                            "monthly_trades": analysis["monthly_trades_estimate"],
                            "positive_rate": analysis["positive_rate"],
                            "risk_reward": analysis["risk_reward_ratio"],
                        }
                    )
            optimal_candidates = fallback_candidates

        # 推奨ランキング
        if optimal_candidates:
            # スコアリング: 取引頻度 + 勝率 + リスクリワード
            for candidate in optimal_candidates:
                frequency_score = min(candidate["monthly_trades"] / 20, 1.0) * 30
                winrate_score = candidate["positive_rate"] * 0.4
                risk_reward_score = min(candidate["risk_reward"] * 10, 20)
                candidate["total_score"] = (
                    frequency_score + winrate_score + risk_reward_score
                )

            # ソート
            optimal_candidates.sort(key=lambda x: x["total_score"], reverse=True)

            # Top推奨
            top_recommendation = optimal_candidates[0]
            conservative_option = min(optimal_candidates, key=lambda x: x["threshold"])
            aggressive_option = max(optimal_candidates, key=lambda x: x["threshold"])
        else:
            # デフォルト推奨
            top_recommendation = {
                "threshold": 0.02,
                "threshold_pct": "2.0%",
                "monthly_trades": 10,
                "positive_rate": 50,
                "total_score": 50,
            }
            conservative_option = top_recommendation
            aggressive_option = top_recommendation

        recommendations = {
            "top_recommendation": top_recommendation,
            "conservative_option": conservative_option,
            "aggressive_option": aggressive_option,
            "all_candidates": optimal_candidates,
            "current_vs_recommended": {
                "current_threshold": self.current_threshold,
                "recommended_threshold": top_recommendation["threshold"],
                "improvement_factor": self.current_threshold
                / top_recommendation["threshold"],
                "estimated_trade_increase": top_recommendation["monthly_trades"],
            },
            "implementation_plan": {
                "phase1_threshold": conservative_option["threshold"],
                "phase2_threshold": top_recommendation["threshold"],
                "phase3_threshold": (
                    aggressive_option["threshold"]
                    if aggressive_option != top_recommendation
                    else top_recommendation["threshold"] * 1.2
                ),
            },
        }

        print(f"  ✅ 推奨閾値決定完了")
        print(
            f"  🥇 TOP推奨: {top_recommendation['threshold_pct']} (月{top_recommendation['monthly_trades']:.0f}回)"
        )
        print(f"  🛡️ 保守的: {conservative_option['threshold_pct']}")
        print(f"  🚀 積極的: {aggressive_option['threshold_pct']}")
        print(
            f"  📈 改善倍率: {recommendations['current_vs_recommended']['improvement_factor']:.1f}倍"
        )

        return recommendations

    def _save_analysis_results(self, results):
        """分析結果保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSON保存（numpy対応）
        json_file = self.output_dir / f"market_analysis_{timestamp}.json"
        serializable_results = self._make_serializable(results)

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(
                serializable_results, f, indent=2, ensure_ascii=False, default=str
            )

        # サマリーレポート保存
        report_file = self.output_dir / f"market_analysis_report_{timestamp}.txt"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(self._generate_summary_report(results))

        print(f"  📁 結果保存: {json_file}")
        print(f"  📄 レポート: {report_file}")

    def _make_serializable(self, obj):
        """JSON序列化対応"""
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, pd.DataFrame):
            return obj.to_dict("records")
        elif pd.isna(obj):
            return None
        else:
            return obj

    def _generate_summary_report(self, results):
        """サマリーレポート生成"""
        lines = []
        lines.append("📊 市場データ分析・適正閾値決定レポート")
        lines.append("=" * 80)

        # 基本情報
        lines.append(
            f"\n📅 分析実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        market_data = results["market_data"]
        lines.append(f"📈 分析期間: {market_data['date_range']}")
        lines.append(f"📊 データ量: {market_data['total_hours']} 時間")

        # ボラティリティ分析
        vol_analysis = results["volatility_analysis"]
        lines.append(f"\n📊 ボラティリティ分析:")
        lines.append(
            f"  平均1h変動: {vol_analysis['stats']['1h_volatility']['mean']:.3f}%"
        )
        lines.append(
            f"  現在閾値: {vol_analysis['current_vs_market']['current_threshold_pct']:.1f}%"
        )
        lines.append(
            f"  閾値/市場比: {vol_analysis['current_vs_market']['threshold_vs_market_ratio']:.1f}倍"
        )
        lines.append(
            f"  閾値超過率: {vol_analysis['current_vs_market']['market_exceeds_threshold_pct']:.1f}%"
        )

        # 推奨閾値
        recommendations = results["recommendations"]
        top_rec = recommendations["top_recommendation"]
        lines.append(f"\n🎯 推奨閾値:")
        lines.append(
            f"  TOP推奨: {top_rec['threshold_pct']} (月{top_rec['monthly_trades']:.0f}回)"
        )
        lines.append(f"  勝率予測: {top_rec['positive_rate']:.1f}%")
        lines.append(
            f"  改善倍率: {recommendations['current_vs_recommended']['improvement_factor']:.1f}倍"
        )

        # 実装計画
        impl_plan = recommendations["implementation_plan"]
        lines.append(f"\n🚀 段階的実装計画:")
        lines.append(f"  Phase 1: {impl_plan['phase1_threshold']*100:.1f}% (保守的)")
        lines.append(f"  Phase 2: {impl_plan['phase2_threshold']*100:.1f}% (推奨)")
        lines.append(f"  Phase 3: {impl_plan['phase3_threshold']*100:.1f}% (積極的)")

        lines.append(f"\n" + "=" * 80)
        return "\n".join(lines)


def main():
    """メイン実行関数"""
    try:
        analyzer = MarketDataAnalyzer()
        analyzer.run_comprehensive_analysis()

    except Exception as e:
        logger.error(f"Market analysis execution failed: {e}")
        print(f"\n❌ 分析実行エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
