#!/usr/bin/env python3
"""
1ヶ月間ウォークフォワードバックテスト
127特徴量 vs 97特徴量 vs 26特徴量の性能比較
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.model_selection import TimeSeriesSplit

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from crypto_bot.ml.preprocessor import FeatureEngineer

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_feature_sets():
    """最適化特徴量セット読み込み"""
    sets_path = Path("results/feature_analysis/optimized_feature_sets.json")

    if not sets_path.exists():
        logger.error(f"特徴量セットファイルが見つかりません: {sets_path}")
        logger.info("先に analyze_127_features_detailed.py を実行してください")
        return None

    with open(sets_path, "r") as f:
        feature_sets = json.load(f)

    logger.info("特徴量セット読み込み完了:")
    logger.info(f"  オリジナル: {len(feature_sets['original_features'])}特徴量")
    logger.info(f"  重複削除版: {len(feature_sets['reduced_features'])}特徴量")
    logger.info(f"  厳選版: {len(feature_sets['essential_features'])}特徴量")

    return feature_sets


def load_backtest_data():
    """バックテストデータ読み込み"""
    data_path = Path("data/btc_usd_2024_hourly.csv")

    if not data_path.exists():
        logger.error(f"データファイルが見つかりません: {data_path}")
        logger.info("先に create_backtest_data.py を実行してください")
        return None

    df = pd.read_csv(data_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    logger.info(f"データ読み込み完了: {len(df)}行")
    logger.info(f"期間: {df['timestamp'].min()} - {df['timestamp'].max()}")

    return df


def create_monthly_splits(df, n_months=6):
    """月次ウォークフォワード分割作成"""
    df = df.copy()
    df["year_month"] = df["timestamp"].dt.to_period("M")

    unique_months = df["year_month"].unique()
    unique_months = sorted(unique_months)

    logger.info(f"利用可能月: {len(unique_months)}ヶ月")

    splits = []

    # 最初の3ヶ月を学習、次の1ヶ月をテストとして、1ヶ月ずつずらす
    train_months = 3
    test_months = 1

    for i in range(len(unique_months) - train_months):
        if i + train_months + test_months > len(unique_months):
            break

        # 学習期間
        train_start = unique_months[i]
        train_end = unique_months[i + train_months - 1]

        # テスト期間
        test_start = unique_months[i + train_months]
        test_end = unique_months[
            min(i + train_months + test_months - 1, len(unique_months) - 1)
        ]

        # インデックス取得
        train_mask = (df["year_month"] >= train_start) & (df["year_month"] <= train_end)
        test_mask = (df["year_month"] >= test_start) & (df["year_month"] <= test_end)

        train_indices = df[train_mask].index.tolist()
        test_indices = df[test_mask].index.tolist()

        if len(train_indices) > 100 and len(test_indices) > 20:  # 最小データ数確認
            splits.append(
                {
                    "train_indices": train_indices,
                    "test_indices": test_indices,
                    "train_period": f"{train_start} - {train_end}",
                    "test_period": f"{test_start} - {test_end}",
                    "train_size": len(train_indices),
                    "test_size": len(test_indices),
                }
            )

    logger.info(f"ウォークフォワード分割作成: {len(splits)}分割")

    return splits


def generate_features_for_set(df, feature_set, set_name):
    """指定特徴量セットで特徴量生成"""
    logger.info(f"{set_name}特徴量生成開始: {len(feature_set)}特徴量")

    # 設定作成
    config = {
        "ml": {
            "feat_period": 14,
            "lags": [1, 2, 3, 4, 5],
            "rolling_window": 20,
            "target_type": "classification",
            "extra_features": feature_set,
        }
    }

    try:
        engineer = FeatureEngineer(config)
        features = engineer.fit_transform(df)

        # 特徴量数調整
        target_count = len(feature_set)
        if features.shape[1] != target_count:
            logger.warning(
                f"{set_name}: 特徴量数調整 {features.shape[1]} → {target_count}"
            )

            # 不足分補完
            while features.shape[1] < target_count:
                dummy_name = f"dummy_{features.shape[1]}"
                features[dummy_name] = np.random.normal(0, 0.01, len(features))

            # 過剰分削除
            if features.shape[1] > target_count:
                features = features.iloc[:, :target_count]

        logger.info(f"{set_name}特徴量生成完了: {features.shape}")
        return features

    except Exception as e:
        logger.error(f"{set_name}特徴量生成エラー: {e}")
        return None


def create_targets(df):
    """ターゲット生成"""
    returns = df["close"].pct_change().fillna(0)

    # 動的閾値（月次ボラティリティベース）
    rolling_vol = returns.rolling(30 * 24).std().fillna(returns.std())  # 30日間
    buy_threshold = 0.8 * rolling_vol
    sell_threshold = -0.8 * rolling_vol

    targets = np.where(
        returns > buy_threshold, 1, np.where(returns < sell_threshold, 0, -1)
    )

    # 有効なターゲットのみ
    valid_mask = targets != -1

    return targets, valid_mask


def train_and_evaluate_model(X_train, X_test, y_train, y_test, model_name):
    """モデル学習・評価"""
    try:
        # LightGBMモデル
        model = lgb.LGBMClassifier(
            objective="binary",
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42,
            verbose=-1,
        )

        model.fit(X_train, y_train)

        # 予測
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]

        # 評価指標
        accuracy = accuracy_score(y_test, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_test, y_pred, average="binary"
        )

        # 予測多様性
        pred_std = np.std(y_pred_proba)
        pred_range = np.max(y_pred_proba) - np.min(y_pred_proba)

        return {
            "model": model,
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "pred_std": pred_std,
            "pred_range": pred_range,
            "predictions": y_pred,
            "probabilities": y_pred_proba,
        }

    except Exception as e:
        logger.error(f"{model_name}モデル学習エラー: {e}")
        return None


def simulate_trading_performance(y_true, y_pred, y_proba, initial_balance=10000):
    """取引シミュレーション"""
    balance = initial_balance
    positions = []
    trades = 0
    wins = 0

    for i in range(len(y_true)):
        if y_proba[i] > 0.7:  # 強いBUYシグナル
            # ロング取引
            if y_true[i] == 1:  # 実際に上昇
                profit = balance * 0.02  # 2%利益
                balance += profit
                wins += 1
            else:
                loss = balance * 0.01  # 1%損失
                balance -= loss
            trades += 1

        elif y_proba[i] < 0.3:  # 強いSELLシグナル
            # ショート取引
            if y_true[i] == 0:  # 実際に下落
                profit = balance * 0.02  # 2%利益
                balance += profit
                wins += 1
            else:
                loss = balance * 0.01  # 1%損失
                balance -= loss
            trades += 1

    win_rate = wins / trades if trades > 0 else 0
    total_return = (balance - initial_balance) / initial_balance

    return {
        "final_balance": balance,
        "total_return": total_return,
        "trades": trades,
        "wins": wins,
        "win_rate": win_rate,
    }


def run_walkforward_backtest():
    """ウォークフォワードバックテスト実行"""
    logger.info("=" * 80)
    logger.info("1ヶ月間ウォークフォワードバックテスト開始")
    logger.info("=" * 80)

    # データ・特徴量セット読み込み
    feature_sets = load_feature_sets()
    if feature_sets is None:
        return None

    df = load_backtest_data()
    if df is None:
        return None

    # 月次分割作成
    splits = create_monthly_splits(df)
    if len(splits) == 0:
        logger.error("有効な分割が作成できませんでした")
        return None

    # ターゲット生成
    targets, valid_mask = create_targets(df)

    # 結果格納
    results = {"original_127": [], "reduced_97": [], "essential_26": []}

    # 特徴量セット名
    set_configs = {
        "original_127": feature_sets["original_features"],
        "reduced_97": feature_sets["reduced_features"],
        "essential_26": feature_sets["essential_features"],
    }

    # 各分割でテスト
    for split_idx, split in enumerate(splits):
        logger.info(f"\n分割 {split_idx + 1}/{len(splits)}")
        logger.info(f"学習期間: {split['train_period']} ({split['train_size']}件)")
        logger.info(f"テスト期間: {split['test_period']} ({split['test_size']}件)")

        # 各特徴量セットでテスト
        for set_name, feature_list in set_configs.items():
            logger.info(f"\n{set_name}特徴量セット処理中...")

            # 特徴量生成
            features = generate_features_for_set(df, feature_list, set_name)
            if features is None:
                continue

            # 有効インデックス
            train_indices = [
                i
                for i in split["train_indices"]
                if i < len(valid_mask) and valid_mask[i]
            ]
            test_indices = [
                i
                for i in split["test_indices"]
                if i < len(valid_mask) and valid_mask[i]
            ]

            if len(train_indices) < 50 or len(test_indices) < 10:
                logger.warning(f"{set_name}: データ不足のためスキップ")
                continue

            # 訓練・テストデータ作成
            X_train = features.iloc[train_indices].fillna(0)
            X_test = features.iloc[test_indices].fillna(0)
            y_train = targets[train_indices]
            y_test = targets[test_indices]

            # モデル学習・評価
            eval_result = train_and_evaluate_model(
                X_train, X_test, y_train, y_test, set_name
            )
            if eval_result is None:
                continue

            # 取引シミュレーション
            trading_result = simulate_trading_performance(
                y_test, eval_result["predictions"], eval_result["probabilities"]
            )

            # 結果記録
            split_result = {
                "split_idx": split_idx,
                "train_period": split["train_period"],
                "test_period": split["test_period"],
                "train_size": len(X_train),
                "test_size": len(X_test),
                "accuracy": eval_result["accuracy"],
                "f1_score": eval_result["f1_score"],
                "pred_std": eval_result["pred_std"],
                "final_balance": trading_result["final_balance"],
                "total_return": trading_result["total_return"],
                "trades": trading_result["trades"],
                "win_rate": trading_result["win_rate"],
            }

            results[set_name].append(split_result)

            logger.info(f"  精度: {eval_result['accuracy']:.3f}")
            logger.info(f"  F1: {eval_result['f1_score']:.3f}")
            logger.info(f"  取引収益: {trading_result['total_return']:.1%}")
            logger.info(f"  勝率: {trading_result['win_rate']:.1%}")

    return results


def analyze_results(results):
    """結果分析・比較"""
    logger.info("\n" + "=" * 80)
    logger.info("ウォークフォワードバックテスト結果分析")
    logger.info("=" * 80)

    summary = {}

    for set_name, set_results in results.items():
        if not set_results:
            continue

        df_results = pd.DataFrame(set_results)

        summary[set_name] = {
            "n_tests": len(set_results),
            "avg_accuracy": df_results["accuracy"].mean(),
            "std_accuracy": df_results["accuracy"].std(),
            "avg_f1": df_results["f1_score"].mean(),
            "std_f1": df_results["f1_score"].std(),
            "avg_return": df_results["total_return"].mean(),
            "std_return": df_results["total_return"].std(),
            "avg_win_rate": df_results["win_rate"].mean(),
            "avg_trades": df_results["trades"].mean(),
            "best_return": df_results["total_return"].max(),
            "worst_return": df_results["total_return"].min(),
            "consistent_profitable": (df_results["total_return"] > 0).sum()
            / len(df_results),
        }

    # 結果表示
    print("\n" + "=" * 80)
    print("📊 特徴量セット別性能比較")
    print("=" * 80)

    for set_name, stats in summary.items():
        print(f"\n🔍 {set_name.upper()}:")
        print(f"  テスト回数: {stats['n_tests']}回")
        print(f"  平均精度: {stats['avg_accuracy']:.1%} (±{stats['std_accuracy']:.1%})")
        print(f"  平均F1スコア: {stats['avg_f1']:.1%} (±{stats['std_f1']:.1%})")
        print(f"  平均収益率: {stats['avg_return']:.1%} (±{stats['std_return']:.1%})")
        print(f"  平均勝率: {stats['avg_win_rate']:.1%}")
        print(f"  平均取引数: {stats['avg_trades']:.0f}回")
        print(f"  最高収益: {stats['best_return']:.1%}")
        print(f"  最低収益: {stats['worst_return']:.1%}")
        print(f"  利益一貫性: {stats['consistent_profitable']:.1%}")

    # 推奨決定
    if summary:
        best_set = max(summary.keys(), key=lambda x: summary[x]["avg_return"])
        print(f"\n🏆 推奨特徴量セット: {best_set.upper()}")
        print(f"   理由: 最高平均収益率 {summary[best_set]['avg_return']:.1%}")

    return summary


def main():
    """メイン実行"""
    # バックテスト実行
    results = run_walkforward_backtest()
    if results is None:
        return

    # 結果分析
    summary = analyze_results(results)

    # 結果保存
    results_dir = Path("results/walkforward_backtest")
    results_dir.mkdir(parents=True, exist_ok=True)

    # 詳細結果保存
    detailed_path = results_dir / "monthly_walkforward_results.json"
    with open(detailed_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    # サマリー保存
    summary_path = results_dir / "performance_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    logger.info(f"\n結果保存完了:")
    logger.info(f"  詳細: {detailed_path}")
    logger.info(f"  サマリー: {summary_path}")

    print("\n" + "=" * 80)
    print("🎯 結論と推奨アクション")
    print("=" * 80)
    print("1. 最も収益性の高い特徴量セットを本番採用")
    print("2. 安定性（標準偏差）も考慮した最終決定")
    print("3. 選択したセットでfinal_model.pklを作成")
    print("4. ローカルテスト→bitbank実取引テスト実行")


if __name__ == "__main__":
    main()
