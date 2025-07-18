#!/usr/bin/env python3
"""
複数閾値バックテスト検証システム
推奨閾値1.0%の安全性・収益性・リスク評価
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
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, precision_score, recall_score

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ThresholdBacktestVerifier:
    """複数閾値バックテスト検証システム"""

    def __init__(self):
        """バックテスト検証システム初期化"""
        self.exchange = ccxt.bitbank()
        self.results = {}

        # 結果保存ディレクトリ
        self.output_dir = Path(project_root / "results" / "threshold_backtest")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 検証パラメータ
        self.candidate_thresholds = [0.005, 0.01, 0.015, 0.02, 0.025, 0.03]  # 0.5%-3.0%
        self.initial_capital = 100000  # 10万円相当
        self.risk_per_trade = 0.005  # 0.5%リスク
        self.transaction_cost = 0.0012  # 0.12%取引コスト

        logger.info("Threshold Backtest Verifier initialized")

    def run_comprehensive_backtest(self):
        """包括的バックテスト実行"""
        print("🔬 複数閾値バックテスト検証開始")
        print("=" * 80)

        try:
            # Phase 1: データ準備
            print("\n📊 Phase 1: バックテストデータ準備")
            print("-" * 50)
            market_data = self._prepare_backtest_data()

            # Phase 2: 複数閾値検証
            print("\n🎯 Phase 2: 複数閾値バックテスト実行")
            print("-" * 50)
            backtest_results = self._run_multiple_threshold_tests(market_data)

            # Phase 3: リスク評価
            print("\n🛡️ Phase 3: リスク分析・評価")
            print("-" * 50)
            risk_analysis = self._analyze_risk_metrics(backtest_results)

            # Phase 4: 比較分析
            print("\n📈 Phase 4: 性能比較・推奨決定")
            print("-" * 50)
            comparison_analysis = self._perform_threshold_comparison(
                backtest_results, risk_analysis
            )

            # Phase 5: 安全性検証
            print("\n🔒 Phase 5: 安全性・実用性検証")
            print("-" * 50)
            safety_assessment = self._assess_safety_and_practicality(
                comparison_analysis
            )

            # 結果統合・保存
            print("\n💾 バックテスト結果保存")
            print("-" * 50)
            self._save_backtest_results(
                {
                    "market_data": market_data,
                    "backtest_results": backtest_results,
                    "risk_analysis": risk_analysis,
                    "comparison_analysis": comparison_analysis,
                    "safety_assessment": safety_assessment,
                }
            )

            print("\n✅ 複数閾値バックテスト検証完了")

        except Exception as e:
            logger.error(f"Backtest verification failed: {e}")
            print(f"\n❌ エラー: {e}")

    def _prepare_backtest_data(self):
        """バックテストデータ準備"""
        print("  📥 過去2ヶ月データ取得中...")

        # 過去60日間のデータ取得（より長期間で検証）
        end_time = datetime.now()
        start_time = end_time - timedelta(days=60)

        # 1時間足データ取得
        since = int(start_time.timestamp() * 1000)
        ohlcv_data = []

        # ページネーション対応データ取得
        limit = 500
        while since < int(end_time.timestamp() * 1000):
            try:
                ohlcv = self.exchange.fetch_ohlcv(
                    "BTC/JPY", "1h", since=since, limit=limit
                )
                if not ohlcv:
                    break

                ohlcv_data.extend(ohlcv)
                since = ohlcv[-1][0] + 3600000

                import time

                time.sleep(0.5)  # レート制限対応

            except Exception as e:
                logger.warning(f"Data fetch error: {e}")
                break

        # DataFrame化・前処理
        df = pd.DataFrame(
            ohlcv_data, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.drop_duplicates(subset=["timestamp"]).reset_index(drop=True)

        # 特徴量計算
        df["returns"] = df["close"].pct_change()
        df["volatility"] = df["returns"].abs()
        df["price_change"] = df["close"].pct_change()

        # 簡易シグナル生成（実際のML予測の代替）
        df["sma_short"] = df["close"].rolling(window=12).mean()
        df["sma_long"] = df["close"].rolling(window=24).mean()
        df["rsi"] = self._calculate_rsi(df["close"], 14)

        # 予測信号の代替（トレンドベース）
        df["trend_signal"] = np.where(df["sma_short"] > df["sma_long"], 1, 0)
        df["ml_probability"] = 0.5 + (df["rsi"] - 50) / 200  # RSIベース確率

        # データ品質確認
        df = df.dropna().reset_index(drop=True)

        market_data = {
            "df": df,
            "total_hours": len(df),
            "date_range": f"{df['timestamp'].min()} to {df['timestamp'].max()}",
            "avg_volatility": df["volatility"].mean(),
            "price_range": f"{df['close'].min():,.0f} - {df['close'].max():,.0f} JPY",
        }

        print(f"  ✅ データ準備完了: {len(df)} 時間分")
        print(f"  📅 期間: {market_data['date_range']}")
        print(f"  📊 平均ボラティリティ: {market_data['avg_volatility']:.3f}%")

        return market_data

    def _calculate_rsi(self, prices, window=14):
        """RSI計算"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50)

    def _run_multiple_threshold_tests(self, market_data):
        """複数閾値でのバックテスト実行"""
        print("  🎯 複数閾値バックテスト実行中...")

        df = market_data["df"]
        backtest_results = {}

        for threshold in self.candidate_thresholds:
            print(f"    📊 閾値 {threshold*100:.1f}% テスト中...")

            # 各閾値でのバックテスト実行
            result = self._run_single_threshold_backtest(df, threshold)
            backtest_results[f"{threshold*100:.1f}%"] = result

        print(
            f"  ✅ 複数閾値バックテスト完了: {len(self.candidate_thresholds)}パターン"
        )

        return backtest_results

    def _run_single_threshold_backtest(self, df, threshold):
        """単一閾値でのバックテスト実行"""
        capital = self.initial_capital
        position = 0
        entry_price = 0
        trades = []
        equity_curve = []

        for i, row in df.iterrows():
            current_price = row["close"]
            volatility = row["volatility"]
            ml_prob = row["ml_probability"]

            # エントリー判定（ボラティリティ閾値 + ML確率）
            if position == 0 and volatility > threshold:
                # ロングエントリー条件
                if ml_prob > 0.5 + threshold:
                    position = 1
                    entry_price = current_price
                    trade_size = (
                        capital * self.risk_per_trade / threshold
                    )  # ポジションサイジング
                    trade_size = min(trade_size, capital * 0.1)  # 最大10%リスク

                    trades.append(
                        {
                            "entry_time": row["timestamp"],
                            "entry_price": entry_price,
                            "entry_type": "LONG",
                            "size": trade_size,
                            "volatility": volatility,
                            "ml_prob": ml_prob,
                        }
                    )

                # ショートエントリー条件
                elif ml_prob < 0.5 - threshold:
                    position = -1
                    entry_price = current_price
                    trade_size = capital * self.risk_per_trade / threshold
                    trade_size = min(trade_size, capital * 0.1)

                    trades.append(
                        {
                            "entry_time": row["timestamp"],
                            "entry_price": entry_price,
                            "entry_type": "SHORT",
                            "size": trade_size,
                            "volatility": volatility,
                            "ml_prob": ml_prob,
                        }
                    )

            # エグジット判定
            elif position != 0:
                exit_condition = False
                exit_type = "NONE"

                # 利確条件（2%利益）
                if position == 1 and current_price > entry_price * 1.02:
                    exit_condition = True
                    exit_type = "PROFIT"
                elif position == -1 and current_price < entry_price * 0.98:
                    exit_condition = True
                    exit_type = "PROFIT"

                # 損切条件（1%損失）
                elif position == 1 and current_price < entry_price * 0.99:
                    exit_condition = True
                    exit_type = "STOP_LOSS"
                elif position == -1 and current_price > entry_price * 1.01:
                    exit_condition = True
                    exit_type = "STOP_LOSS"

                # タイムアウト（24時間保有）
                elif len(trades) > 0:
                    entry_time = trades[-1]["entry_time"]
                    if (row["timestamp"] - entry_time).total_seconds() > 24 * 3600:
                        exit_condition = True
                        exit_type = "TIMEOUT"

                # エグジット実行
                if exit_condition and len(trades) > 0:
                    last_trade = trades[-1]

                    # 損益計算
                    if position == 1:
                        pnl = (current_price - entry_price) / entry_price
                    else:
                        pnl = (entry_price - current_price) / entry_price

                    # 取引コスト差し引き
                    pnl -= self.transaction_cost

                    # 資本更新
                    trade_pnl = last_trade["size"] * pnl
                    capital += trade_pnl

                    # 取引記録更新
                    trades[-1].update(
                        {
                            "exit_time": row["timestamp"],
                            "exit_price": current_price,
                            "exit_type": exit_type,
                            "pnl": pnl,
                            "trade_pnl": trade_pnl,
                            "capital_after": capital,
                        }
                    )

                    position = 0
                    entry_price = 0

            # 資本曲線記録
            equity_curve.append(
                {
                    "timestamp": row["timestamp"],
                    "capital": capital,
                    "position": position,
                }
            )

        # 結果分析
        completed_trades = [t for t in trades if "exit_time" in t]

        if completed_trades:
            returns = [t["pnl"] for t in completed_trades]
            positive_returns = [r for r in returns if r > 0]

            total_return = (capital - self.initial_capital) / self.initial_capital
            win_rate = len(positive_returns) / len(returns) if returns else 0
            avg_return = np.mean(returns) if returns else 0
            return_std = np.std(returns) if len(returns) > 1 else 0
            sharpe_ratio = avg_return / return_std if return_std > 0 else 0

            # 最大ドローダウン計算
            equity_values = [e["capital"] for e in equity_curve]
            running_max = np.maximum.accumulate(equity_values)
            drawdown = (equity_values - running_max) / running_max
            max_drawdown = np.min(drawdown)
        else:
            total_return = 0
            win_rate = 0
            avg_return = 0
            return_std = 0
            sharpe_ratio = 0
            max_drawdown = 0

        return {
            "threshold": threshold,
            "total_trades": len(completed_trades),
            "total_return": total_return,
            "win_rate": win_rate,
            "avg_return_per_trade": avg_return,
            "return_volatility": return_std,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "final_capital": capital,
            "trades": completed_trades,
            "equity_curve": equity_curve,
        }

    def _analyze_risk_metrics(self, backtest_results):
        """リスク分析・評価"""
        print("  🛡️ リスク分析実行中...")

        risk_analysis = {}

        for threshold_key, result in backtest_results.items():
            threshold = result["threshold"]

            # リスク指標計算
            risk_metrics = {
                "value_at_risk_95": self._calculate_var(result["trades"], 0.95),
                "expected_shortfall": self._calculate_expected_shortfall(
                    result["trades"], 0.95
                ),
                "maximum_consecutive_losses": self._calculate_max_consecutive_losses(
                    result["trades"]
                ),
                "risk_reward_ratio": self._calculate_risk_reward_ratio(
                    result["trades"]
                ),
                "profit_factor": self._calculate_profit_factor(result["trades"]),
                "recovery_factor": (
                    abs(result["total_return"] / result["max_drawdown"])
                    if result["max_drawdown"] != 0
                    else float("inf")
                ),
                "calmar_ratio": (
                    result["total_return"] / abs(result["max_drawdown"])
                    if result["max_drawdown"] != 0
                    else float("inf")
                ),
            }

            # 安全性評価
            safety_score = self._calculate_safety_score(result, risk_metrics)

            risk_analysis[threshold_key] = {
                "risk_metrics": risk_metrics,
                "safety_score": safety_score,
                "recommendation": (
                    "SAFE"
                    if safety_score > 70
                    else "CAUTION" if safety_score > 50 else "RISKY"
                ),
            }

        print(f"  ✅ リスク分析完了: {len(backtest_results)}閾値評価")

        return risk_analysis

    def _calculate_var(self, trades, confidence_level):
        """VaR計算"""
        if not trades:
            return 0
        returns = [t["pnl"] for t in trades if "pnl" in t]
        if not returns:
            return 0
        return np.percentile(returns, (1 - confidence_level) * 100)

    def _calculate_expected_shortfall(self, trades, confidence_level):
        """期待ショートフォール計算"""
        if not trades:
            return 0
        returns = [t["pnl"] for t in trades if "pnl" in t]
        if not returns:
            return 0
        var = self._calculate_var(trades, confidence_level)
        tail_returns = [r for r in returns if r <= var]
        return np.mean(tail_returns) if tail_returns else 0

    def _calculate_max_consecutive_losses(self, trades):
        """最大連続損失回数計算"""
        if not trades:
            return 0

        consecutive_losses = 0
        max_consecutive = 0

        for trade in trades:
            if "pnl" in trade:
                if trade["pnl"] < 0:
                    consecutive_losses += 1
                    max_consecutive = max(max_consecutive, consecutive_losses)
                else:
                    consecutive_losses = 0

        return max_consecutive

    def _calculate_risk_reward_ratio(self, trades):
        """リスクリワード比計算"""
        if not trades:
            return 0

        winning_trades = [t["pnl"] for t in trades if "pnl" in t and t["pnl"] > 0]
        losing_trades = [t["pnl"] for t in trades if "pnl" in t and t["pnl"] < 0]

        if not winning_trades or not losing_trades:
            return 0

        avg_win = np.mean(winning_trades)
        avg_loss = abs(np.mean(losing_trades))

        return avg_win / avg_loss if avg_loss > 0 else 0

    def _calculate_profit_factor(self, trades):
        """プロフィットファクター計算"""
        if not trades:
            return 0

        gross_profit = sum(t["pnl"] for t in trades if "pnl" in t and t["pnl"] > 0)
        gross_loss = abs(sum(t["pnl"] for t in trades if "pnl" in t and t["pnl"] < 0))

        return gross_profit / gross_loss if gross_loss > 0 else float("inf")

    def _calculate_safety_score(self, result, risk_metrics):
        """安全性スコア計算"""
        score = 0

        # 勝率評価（30点）
        if result["win_rate"] >= 0.6:
            score += 30
        elif result["win_rate"] >= 0.5:
            score += 20
        elif result["win_rate"] >= 0.4:
            score += 10

        # リターン評価（25点）
        if result["total_return"] > 0.1:
            score += 25
        elif result["total_return"] > 0.05:
            score += 15
        elif result["total_return"] > 0:
            score += 10

        # ドローダウン評価（25点）
        if abs(result["max_drawdown"]) < 0.05:
            score += 25
        elif abs(result["max_drawdown"]) < 0.1:
            score += 15
        elif abs(result["max_drawdown"]) < 0.15:
            score += 10

        # シャープレシオ評価（20点）
        if result["sharpe_ratio"] > 1.5:
            score += 20
        elif result["sharpe_ratio"] > 1.0:
            score += 15
        elif result["sharpe_ratio"] > 0.5:
            score += 10

        return score

    def _perform_threshold_comparison(self, backtest_results, risk_analysis):
        """性能比較・推奨決定"""
        print("  📈 性能比較分析中...")

        # 総合スコア計算
        comparison_results = []

        for threshold_key, result in backtest_results.items():
            risk_data = risk_analysis[threshold_key]

            # 総合スコア（リターン + 安全性 + 取引頻度）
            return_score = min(result["total_return"] * 100, 50)  # 最大50点
            safety_score = risk_data["safety_score"]  # 最大100点
            frequency_score = min(result["total_trades"] / 10 * 20, 30)  # 最大30点

            total_score = return_score + safety_score * 0.6 + frequency_score

            comparison_results.append(
                {
                    "threshold": threshold_key,
                    "threshold_value": result["threshold"],
                    "total_score": total_score,
                    "return_score": return_score,
                    "safety_score": safety_score,
                    "frequency_score": frequency_score,
                    "total_return": result["total_return"],
                    "win_rate": result["win_rate"],
                    "max_drawdown": result["max_drawdown"],
                    "total_trades": result["total_trades"],
                    "sharpe_ratio": result["sharpe_ratio"],
                    "recommendation": risk_data["recommendation"],
                }
            )

        # スコア順ソート
        comparison_results.sort(key=lambda x: x["total_score"], reverse=True)

        # Top 3推奨
        top_recommendations = comparison_results[:3]

        comparison_analysis = {
            "all_results": comparison_results,
            "top_recommendations": top_recommendations,
            "best_threshold": top_recommendations[0] if top_recommendations else None,
            "conservative_option": min(
                comparison_results, key=lambda x: abs(x["max_drawdown"])
            ),
            "aggressive_option": max(
                comparison_results, key=lambda x: x["total_return"]
            ),
        }

        print(f"  ✅ 性能比較完了")
        if comparison_analysis["best_threshold"]:
            best = comparison_analysis["best_threshold"]
            print(
                f"  🥇 最優秀: {best['threshold']} (スコア: {best['total_score']:.1f})"
            )
            print(f"  📈 リターン: {best['total_return']:.2%}")
            print(f"  🎯 勝率: {best['win_rate']:.1%}")
            print(f"  📉 ドローダウン: {best['max_drawdown']:.2%}")

        return comparison_analysis

    def _assess_safety_and_practicality(self, comparison_analysis):
        """安全性・実用性検証"""
        print("  🔒 安全性・実用性検証中...")

        best_threshold = comparison_analysis["best_threshold"]

        if not best_threshold:
            return {"assessment": "FAILED", "reason": "No viable threshold found"}

        # 安全性チェックリスト
        safety_checks = {
            "positive_return": best_threshold["total_return"] > 0,
            "acceptable_drawdown": abs(best_threshold["max_drawdown"]) < 0.15,
            "decent_win_rate": best_threshold["win_rate"] > 0.45,
            "sufficient_trades": best_threshold["total_trades"] >= 5,
            "positive_sharpe": best_threshold["sharpe_ratio"] > 0,
        }

        # 実用性チェック
        practicality_checks = {
            "reasonable_frequency": 5 <= best_threshold["total_trades"] <= 50,
            "manageable_risk": abs(best_threshold["max_drawdown"]) < 0.20,
            "scalable": best_threshold["win_rate"] > 0.4,
        }

        # 総合評価
        safety_passed = sum(safety_checks.values()) >= 4
        practicality_passed = sum(practicality_checks.values()) >= 2

        if safety_passed and practicality_passed:
            assessment = "APPROVED"
            confidence = "HIGH"
        elif safety_passed:
            assessment = "CONDITIONAL"
            confidence = "MEDIUM"
        else:
            assessment = "REJECTED"
            confidence = "LOW"

        safety_assessment = {
            "assessment": assessment,
            "confidence": confidence,
            "safety_checks": safety_checks,
            "practicality_checks": practicality_checks,
            "recommended_threshold": best_threshold["threshold_value"],
            "implementation_recommendation": self._generate_implementation_recommendation(
                assessment, best_threshold
            ),
        }

        print(f"  ✅ 安全性検証完了: {assessment}")
        print(f"  🎯 推奨閾値: {best_threshold['threshold']}")
        print(f"  🔒 信頼度: {confidence}")

        return safety_assessment

    def _generate_implementation_recommendation(self, assessment, best_threshold):
        """実装推奨事項生成"""
        if assessment == "APPROVED":
            return {
                "immediate_implementation": True,
                "suggested_threshold": best_threshold["threshold_value"],
                "risk_management": "Standard risk management protocols",
                "monitoring_frequency": "Daily monitoring recommended",
            }
        elif assessment == "CONDITIONAL":
            return {
                "immediate_implementation": False,
                "suggested_threshold": best_threshold["threshold_value"]
                * 0.8,  # より保守的
                "risk_management": "Enhanced risk management required",
                "monitoring_frequency": "Hourly monitoring required",
            }
        else:
            return {
                "immediate_implementation": False,
                "suggested_threshold": 0.02,  # 2%フォールバック
                "risk_management": "Maximum risk management protocols",
                "monitoring_frequency": "Continuous monitoring required",
            }

    def _save_backtest_results(self, results):
        """バックテスト結果保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSON保存
        json_file = self.output_dir / f"threshold_backtest_{timestamp}.json"
        serializable_results = self._make_serializable(results)

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(
                serializable_results, f, indent=2, ensure_ascii=False, default=str
            )

        # レポート保存
        report_file = self.output_dir / f"threshold_backtest_report_{timestamp}.txt"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(self._generate_backtest_report(results))

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
        elif pd.isna(obj):
            return None
        else:
            return obj

    def _generate_backtest_report(self, results):
        """バックテストレポート生成"""
        lines = []
        lines.append("🔬 複数閾値バックテスト検証レポート")
        lines.append("=" * 80)

        lines.append(
            f"\n📅 検証実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        # 市場データ情報
        market_data = results["market_data"]
        lines.append(f"📊 検証期間: {market_data['date_range']}")
        lines.append(f"📈 データ量: {market_data['total_hours']} 時間")

        # 最優秀結果
        if results["safety_assessment"]["assessment"] == "APPROVED":
            best = results["comparison_analysis"]["best_threshold"]
            lines.append(f"\n🏆 推奨閾値: {best['threshold']}")
            lines.append(f"📈 予想リターン: {best['total_return']:.2%}")
            lines.append(f"🎯 勝率: {best['win_rate']:.1%}")
            lines.append(f"📉 最大ドローダウン: {best['max_drawdown']:.2%}")
            lines.append(f"📊 取引頻度: {best['total_trades']}回/2ヶ月")
            lines.append(f"⚡ シャープレシオ: {best['sharpe_ratio']:.2f}")

        # 安全性評価
        safety = results["safety_assessment"]
        lines.append(f"\n🔒 安全性評価: {safety['assessment']}")
        lines.append(f"🎯 信頼度: {safety['confidence']}")
        lines.append(
            f"💡 実装推奨: {safety['implementation_recommendation']['immediate_implementation']}"
        )

        lines.append(f"\n" + "=" * 80)
        return "\n".join(lines)


def main():
    """メイン実行関数"""
    try:
        verifier = ThresholdBacktestVerifier()
        verifier.run_comprehensive_backtest()

    except Exception as e:
        logger.error(f"Threshold backtest verification failed: {e}")
        print(f"\n❌ バックテスト検証エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
