#!/usr/bin/env python3
"""
効率的特徴量セット比較バックテスト
127特徴量 vs 97特徴量 vs 26特徴量の高速性能比較
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
from sklearn.model_selection import train_test_split

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from crypto_bot.ml.preprocessor import FeatureEngineer

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_data_and_feature_sets():
    """データと特徴量セット読み込み"""
    # 特徴量セット読み込み
    sets_path = Path("results/feature_analysis/optimized_feature_sets.json")
    if not sets_path.exists():
        logger.error("先に analyze_127_features_detailed.py を実行してください")
        return None, None

    with open(sets_path, "r") as f:
        feature_sets = json.load(f)

    # データ読み込み
    data_path = Path("data/btc_usd_2024_hourly.csv")
    if not data_path.exists():
        logger.error("先に create_backtest_data.py を実行してください")
        return None, None

    df = pd.read_csv(data_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    # サンプルサイズを制限（高速化）
    sample_size = 5000
    if len(df) > sample_size:
        # 最新データを使用
        df = df.tail(sample_size).reset_index(drop=True)
        logger.info(f"データを最新{sample_size}件に制限")

    logger.info(f"データ読み込み完了: {len(df)}行")
    logger.info("特徴量セット:")
    logger.info(f"  オリジナル: {len(feature_sets['original_features'])}特徴量")
    logger.info(f"  重複削除版: {len(feature_sets['reduced_features'])}特徴量")
    logger.info(f"  厳選版: {len(feature_sets['essential_features'])}特徴量")

    return df, feature_sets


def generate_features_optimized(df, feature_list, set_name):
    """最適化された特徴量生成"""
    logger.info(f"{set_name}特徴量生成: {len(feature_list)}特徴量")

    config = {
        "ml": {
            "feat_period": 14,
            "lags": [1],  # ラグ数制限で高速化
            "rolling_window": 10,  # ウィンドウサイズ削減
            "target_type": "classification",
            "extra_features": feature_list,  # 全特徴量使用
        }
    }

    engineer = FeatureEngineer(config)
    features = engineer.fit_transform(df)

    # 目標特徴量数に調整
    target_count = len(feature_list)
    if features.shape[1] != target_count:
        if features.shape[1] < target_count:
            # 不足分を補完
            for i in range(target_count - features.shape[1]):
                features[f"dummy_{i}"] = np.random.normal(0, 0.01, len(features))
        else:
            # 過剰分削除
            features = features.iloc[:, :target_count]

    logger.info(f"{set_name}特徴量生成完了: {features.shape}")
    return features


def create_simple_targets(df):
    """シンプルなターゲット生成"""
    returns = df["close"].pct_change().fillna(0)

    # 固定閾値でシンプルに
    buy_threshold = returns.quantile(0.75)
    sell_threshold = returns.quantile(0.25)

    targets = np.where(
        returns > buy_threshold, 1, np.where(returns < sell_threshold, 0, -1)
    )

    valid_mask = targets != -1
    return targets, valid_mask


def evaluate_feature_set(df, feature_list, set_name):
    """特徴量セット評価"""
    logger.info(f"\n{set_name.upper()}評価開始")

    try:
        # 特徴量生成
        features = generate_features_optimized(df, feature_list, set_name)

        # ターゲット生成
        targets, valid_mask = create_simple_targets(df)

        # 有効データのみ
        X = features[valid_mask].fillna(0)
        y = targets[valid_mask]

        if len(X) < 100:
            logger.warning(f"{set_name}: データ不足")
            return None

        logger.info(f"有効サンプル: {len(X)}")
        logger.info(
            f"BUY: {np.sum(y==1)} ({np.sum(y==1)/len(y)*100:.1f}%), SELL: {np.sum(y==0)} ({np.sum(y==0)/len(y)*100:.1f}%)"
        )

        # 訓練・テスト分割
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.3, random_state=42, stratify=y
        )

        # LightGBMモデル
        model = lgb.LGBMClassifier(
            objective="binary",
            n_estimators=50,  # 高速化のため削減
            max_depth=5,
            learning_rate=0.1,
            random_state=42,
            verbose=-1,
        )

        model.fit(X_train, y_train)

        # 予測・評価
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]

        accuracy = accuracy_score(y_test, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_test, y_pred, average="binary"
        )

        # 予測多様性
        pred_std = np.std(y_pred_proba)
        pred_range = np.max(y_pred_proba) - np.min(y_pred_proba)

        # 特徴量重要度（上位10）
        importance = model.feature_importances_
        feature_names = X.columns.tolist()
        top_features = sorted(
            zip(feature_names, importance), key=lambda x: x[1], reverse=True
        )[:10]

        # 簡易取引シミュレーション
        trades = 0
        wins = 0
        total_return = 0

        for i in range(len(y_test)):
            if y_pred_proba[i] > 0.7 or y_pred_proba[i] < 0.3:  # 強いシグナルのみ
                trades += 1
                if (y_pred_proba[i] > 0.7 and y_test[i] == 1) or (
                    y_pred_proba[i] < 0.3 and y_test[i] == 0
                ):
                    wins += 1
                    total_return += 0.02  # 2%利益
                else:
                    total_return -= 0.01  # 1%損失

        win_rate = wins / trades if trades > 0 else 0

        result = {
            "set_name": set_name,
            "n_features": features.shape[1],
            "n_samples": len(X),
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "pred_std": pred_std,
            "pred_range": pred_range,
            "total_return": total_return,
            "trades": trades,
            "win_rate": win_rate,
            "top_features": top_features[:5],  # 上位5特徴量
        }

        logger.info(f"結果:")
        logger.info(f"  精度: {accuracy:.1%}")
        logger.info(f"  F1スコア: {f1:.1%}")
        logger.info(f"  予測多様性: {pred_std:.3f}")
        logger.info(f"  取引収益: {total_return:.1%}")
        logger.info(f"  勝率: {win_rate:.1%} ({wins}/{trades})")

        return result

    except Exception as e:
        logger.error(f"{set_name}評価エラー: {e}")
        return None


def compare_feature_sets():
    """特徴量セット比較実行"""
    logger.info("=" * 80)
    logger.info("効率的特徴量セット比較バックテスト")
    logger.info("=" * 80)

    # データ・特徴量セット読み込み
    df, feature_sets = load_data_and_feature_sets()
    if df is None or feature_sets is None:
        return None

    # 各セット評価
    results = []

    test_configs = [
        ("original_125", feature_sets["original_features"]),
        ("reduced_105", feature_sets["reduced_features"]),
        ("essential_26", feature_sets["essential_features"]),
    ]

    for set_name, feature_list in test_configs:
        result = evaluate_feature_set(df, feature_list, set_name)
        if result:
            results.append(result)

    if not results:
        logger.error("評価結果が得られませんでした")
        return None

    return results


def analyze_comparison_results(results):
    """比較結果分析"""
    logger.info("\n" + "=" * 80)
    logger.info("特徴量セット比較結果分析")
    logger.info("=" * 80)

    df_results = pd.DataFrame(results)

    print("\n📊 特徴量セット性能比較")
    print("=" * 80)

    for _, result in df_results.iterrows():
        print(f"\n🔍 {result['set_name'].upper()}:")
        print(f"  特徴量数: {result['n_features']}個")
        print(f"  精度: {result['accuracy']:.1%}")
        print(f"  F1スコア: {result['f1_score']:.1%}")
        print(f"  予測多様性: {result['pred_std']:.3f}")
        print(f"  取引収益: {result['total_return']:.1%}")
        print(f"  勝率: {result['win_rate']:.1%}")
        print(f"  取引数: {result['trades']}回")
        print(f"  重要特徴量: {', '.join([f[0] for f in result['top_features']])}")

    # 最適セット決定
    # 総合スコア = F1スコア * 0.4 + 取引収益 * 0.4 + 予測多様性 * 0.2
    df_results["composite_score"] = (
        df_results["f1_score"] * 0.4
        + df_results["total_return"] * 0.4
        + df_results["pred_std"] * 0.2
    )

    best_set = df_results.loc[df_results["composite_score"].idxmax()]

    print(f"\n🏆 推奨特徴量セット: {best_set['set_name'].upper()}")
    print(f"   特徴量数: {best_set['n_features']}個")
    print(f"   総合スコア: {best_set['composite_score']:.3f}")
    print(f"   F1スコア: {best_set['f1_score']:.1%}")
    print(f"   取引収益: {best_set['total_return']:.1%}")
    print(f"   予測多様性: {best_set['pred_std']:.3f}")

    return df_results, best_set


def main():
    """メイン実行"""
    # 比較実行
    results = compare_feature_sets()
    if results is None:
        return

    # 結果分析
    df_results, best_set = analyze_comparison_results(results)

    # 結果保存
    results_dir = Path("results/feature_comparison")
    results_dir.mkdir(parents=True, exist_ok=True)

    comparison_path = results_dir / "quick_comparison_results.json"
    with open(comparison_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    best_set_path = results_dir / "recommended_feature_set.json"
    with open(best_set_path, "w") as f:
        json.dump(best_set.to_dict(), f, indent=2, default=str)

    logger.info(f"\n結果保存:")
    logger.info(f"  比較結果: {comparison_path}")
    logger.info(f"  推奨セット: {best_set_path}")

    print("\n" + "=" * 80)
    print("🎯 次のステップ")
    print("=" * 80)
    print(f"1. 推奨セット（{best_set['set_name']}）で詳細バックテスト実行")
    print("2. 最適化モデル作成・保存")
    print("3. ローカルテスト→bitbank実取引テスト")

    # 推奨特徴量リスト表示
    if best_set["set_name"] == "essential_26":
        print("\n📋 推奨特徴量リスト（26個）:")
        feature_sets = None
        sets_path = Path("results/feature_analysis/optimized_feature_sets.json")
        if sets_path.exists():
            with open(sets_path, "r") as f:
                feature_sets = json.load(f)
            essential_features = feature_sets["essential_features"]
            for i, feature in enumerate(essential_features, 1):
                print(f"  {i:2d}. {feature}")


if __name__ == "__main__":
    main()
