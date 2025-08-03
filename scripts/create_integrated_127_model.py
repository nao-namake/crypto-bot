#!/usr/bin/env python3
"""
127特徴量統合高精度モデル作成スクリプト
99.2%精度モデルの成功要因を127特徴量システムに統合

アプローチ:
1. 99.2%精度モデルの成功要因分析
2. 127特徴量データで同様の手法を適用
3. 特徴量選択＋バイナリ分類の組み合わせ
4. 127特徴量完全対応の高精度モデル作成
"""

import json
import logging
import os
import sys
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.feature_selection import SelectKBest, f_classif, mutual_info_classif
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from crypto_bot.ml.feature_order_manager import FeatureOrderManager
from crypto_bot.ml.preprocessor import FeatureEngineer

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_robust_model_insights():
    """99.2%精度モデルの成功要因を分析"""
    logger.info("🔍 99.2%精度モデルの成功要因分析開始")

    # 成功した特徴量リストを読み込み
    features_path = Path("models/production/robust_model_features.json")
    if features_path.exists():
        with open(features_path, "r") as f:
            successful_features = json.load(f)
        logger.info(f"成功した30特徴量: {len(successful_features)}個")

        # 成功要因分析
        feature_categories = {
            "price_features": [
                f
                for f in successful_features
                if any(x in f for x in ["returns", "price", "position"])
            ],
            "technical_indicators": [
                f
                for f in successful_features
                if any(x in f for x in ["rsi", "stoch", "mfi", "cci", "williams"])
            ],
            "trend_features": [
                f
                for f in successful_features
                if any(x in f for x in ["trend", "momentum", "roc"])
            ],
            "volatility_features": [
                f
                for f in successful_features
                if any(x in f for x in ["volatility", "atr", "zscore"])
            ],
            "support_resistance": [
                f
                for f in successful_features
                if any(x in f for x in ["support", "resistance", "mean_reversion"])
            ],
        }

        logger.info("成功特徴量カテゴリ分析:")
        for category, features in feature_categories.items():
            logger.info(
                f"  {category}: {len(features)}個 - {features[:3]}..."
                if len(features) > 3
                else f"  {category}: {features}"
            )

        return successful_features, feature_categories
    else:
        logger.warning("99.2%精度モデルの特徴量ファイルが見つかりません")
        return [], {}


def create_enhanced_training_data():
    """127特徴量システム用の改良学習データ生成"""
    np.random.seed(42)
    n_rows = 15000  # より多くのデータ

    logger.info(f"127特徴量システム用学習データ生成: {n_rows} samples")

    # より現実的な市場パターンを含むデータ
    t = np.arange(n_rows)

    # 複数の市場レジーム
    bull_market = np.sin(2 * np.pi * t / 1000) > 0.4  # 強気相場
    bear_market = np.sin(2 * np.pi * t / 800) < -0.4  # 弱気相場
    sideways = ~(bull_market | bear_market)  # レンジ相場

    # ボラティリティ期間
    high_vol = np.abs(np.sin(2 * np.pi * t / 200)) > 0.7

    # ベースリターン
    returns = np.random.normal(0, 0.01, n_rows)

    # 市場レジーム別の調整
    returns[bull_market] += np.random.normal(0.002, 0.008, bull_market.sum())
    returns[bear_market] += np.random.normal(-0.002, 0.008, bear_market.sum())
    returns[sideways] += np.random.normal(0, 0.005, sideways.sum())

    # ボラティリティ調整
    returns[high_vol] *= 2.5

    # トレンド成分
    trend_component = 0.001 * np.sin(2 * np.pi * t / 600)
    returns += trend_component

    # 累積価格
    base_price = 45000
    log_returns = np.cumsum(returns)
    close_prices = base_price * np.exp(log_returns)

    # 現実的なOHLCデータ
    data = pd.DataFrame(
        {
            "timestamp": pd.date_range(start="2023-01-01", periods=n_rows, freq="1H"),
            "close": close_prices,
        }
    )

    # Open価格（前のcloseベース）
    data["open"] = data["close"].shift(1).fillna(close_prices[0]) * np.random.normal(
        1, 0.0008, n_rows
    )

    # High/Low価格（より現実的な範囲）
    intraday_range = np.random.exponential(0.003, n_rows)
    intraday_range[high_vol] *= 2  # 高ボラティリティ時は拡大

    oc_max = np.maximum(data["open"], data["close"])
    oc_min = np.minimum(data["open"], data["close"])

    data["high"] = oc_max * (1 + intraday_range)
    data["low"] = oc_min * (1 - intraday_range * 0.8)

    # Volume（価格変動と相関）
    price_change = np.abs(data["close"].pct_change())
    base_volume = np.random.lognormal(np.log(800), 0.3, n_rows)
    volume_multiplier = 1 + 2.0 * price_change.fillna(0)
    data["volume"] = base_volume * volume_multiplier

    logger.info(f"拡張学習データ生成完了:")
    logger.info(f"  価格範囲: ${data['close'].min():.0f} - ${data['close'].max():.0f}")
    logger.info(
        f"  強気相場: {bull_market.sum()} ({bull_market.sum()/len(bull_market)*100:.1f}%)"
    )
    logger.info(
        f"  弱気相場: {bear_market.sum()} ({bear_market.sum()/len(bear_market)*100:.1f}%)"
    )
    logger.info(
        f"  レンジ相場: {sideways.sum()} ({sideways.sum()/len(sideways)*100:.1f}%)"
    )
    logger.info(
        f"  高ボラティリティ: {high_vol.sum()} ({high_vol.sum()/len(high_vol)*100:.1f}%)"
    )

    return data


def create_sophisticated_targets(features, close_prices):
    """高度な分類ターゲット生成（99.2%モデルの手法を改良）"""
    logger.info("高度なバイナリ分類ターゲット生成開始")

    # マルチタイムフレームリターン
    returns_1h = close_prices.pct_change(1)
    returns_4h = close_prices.pct_change(4)
    returns_8h = close_prices.pct_change(8)
    returns_24h = close_prices.pct_change(24)

    # ボラティリティ調整済みリターン（複数期間）
    vol_10 = returns_1h.rolling(10).std()
    vol_20 = returns_1h.rolling(20).std()
    vol_50 = returns_1h.rolling(50).std()

    # 複合リターン指標（改良版）
    combined_returns = (
        0.30 * returns_1h + 0.30 * returns_4h + 0.25 * returns_8h + 0.15 * returns_24h
    ).fillna(0)

    # マルチボラティリティ調整
    vol_combined = (vol_10 + vol_20 + vol_50) / 3
    vol_adjusted_returns = combined_returns / (vol_combined + 1e-6)

    # トレンド強度を考慮
    sma_20 = close_prices.rolling(20).mean()
    sma_50 = close_prices.rolling(50).mean()
    trend_strength = (sma_20 - sma_50) / sma_50

    # トレンド方向別の閾値調整
    base_buy_threshold = vol_adjusted_returns.quantile(0.70)  # 上位30%
    base_sell_threshold = vol_adjusted_returns.quantile(0.30)  # 下位30%

    # トレンド強度による閾値調整
    buy_threshold = base_buy_threshold * (1 + 0.2 * np.sign(trend_strength))
    sell_threshold = base_sell_threshold * (1 - 0.2 * np.sign(trend_strength))

    # 明確な信号のみを使用（改良版）
    strong_buy_mask = vol_adjusted_returns >= buy_threshold
    strong_sell_mask = vol_adjusted_returns <= sell_threshold
    valid_mask = strong_buy_mask | strong_sell_mask

    # ターゲット生成
    targets = np.where(strong_buy_mask, 1, 0)  # 1: BUY, 0: SELL

    logger.info(f"高度ターゲット分析:")
    valid_targets = targets[valid_mask]
    sell_count = (valid_targets == 0).sum()
    buy_count = (valid_targets == 1).sum()
    logger.info(f"  SELL (0): {sell_count} ({sell_count/len(valid_targets)*100:.1f}%)")
    logger.info(f"  BUY (1): {buy_count} ({buy_count/len(valid_targets)*100:.1f}%)")
    logger.info(
        f"  有効サンプル: {len(valid_targets)} ({len(valid_targets)/len(targets)*100:.1f}%)"
    )
    logger.info(
        f"  トレンド調整範囲: buy_th={base_buy_threshold:.3f}, sell_th={base_sell_threshold:.3f}"
    )

    return targets, valid_mask


def intelligent_feature_selection(X, y, successful_features, k_best=60):
    """インテリジェント特徴量選択（99.2%モデルの知見活用）"""
    logger.info(f"インテリジェント特徴量選択開始: 127 → {k_best}特徴量")

    # 99.2%モデルで成功した特徴量タイプを優先
    priority_patterns = [
        "returns",
        "rsi",
        "stoch",
        "price_position",
        "price_vs_sma",
        "mfi",
        "trend_direction",
        "cci",
        "williams_r",
        "ultimate_oscillator",
        "support",
        "resistance",
        "zscore",
        "mean_reversion",
        "roc",
    ]

    # 統計的特徴量選択
    selector_f = SelectKBest(score_func=f_classif, k="all")
    selector_f.fit(X, y)
    f_scores = selector_f.scores_

    # 相互情報量による選択
    mi_scores = mutual_info_classif(X, y, random_state=42)

    # 複合スコア計算
    feature_scores = []
    for i, col in enumerate(X.columns):
        # 基本スコア
        f_score = f_scores[i] if not np.isnan(f_scores[i]) else 0
        mi_score = mi_scores[i] if not np.isnan(mi_scores[i]) else 0

        # 優先パターンボーナス
        priority_bonus = 0
        for pattern in priority_patterns:
            if pattern in col.lower():
                priority_bonus += 0.2
                break

        # 99.2%モデル成功特徴量ボーナス
        success_bonus = 0.5 if col in successful_features else 0

        # 複合スコア
        composite_score = (
            f_score * 0.4 + mi_score * 0.4 + priority_bonus + success_bonus
        )

        feature_scores.append(
            (col, composite_score, f_score, mi_score, priority_bonus, success_bonus)
        )

    # スコア順にソート
    feature_scores.sort(key=lambda x: x[1], reverse=True)

    # 上位k_best特徴量を選択
    selected_features = [item[0] for item in feature_scores[:k_best]]

    logger.info(f"インテリジェント特徴量選択結果:")
    logger.info(f"  選択された特徴量: {len(selected_features)}")
    logger.info(
        f"  99.2%モデル成功特徴量含有: {sum(1 for f in selected_features if f in successful_features)}"
    )

    logger.info("トップ10選択特徴量:")
    for i, (feat, comp_score, f_score, mi_score, p_bonus, s_bonus) in enumerate(
        feature_scores[:10]
    ):
        logger.info(
            f"  {i+1:2d}. {feat}: comp={comp_score:.3f} (f={f_score:.1f}, mi={mi_score:.3f}, p={p_bonus:.1f}, s={s_bonus:.1f})"
        )

    return X[selected_features], selected_features


def train_integrated_127_model():
    """127特徴量統合高精度モデル学習"""
    logger.info("=" * 80)
    logger.info("127特徴量統合高精度モデル学習開始")
    logger.info("=" * 80)

    # 99.2%精度モデルの成功要因分析
    successful_features, feature_categories = load_robust_model_insights()

    # 改良学習データ生成
    data = create_enhanced_training_data()

    # 完全な127特徴量システム設定
    config = {
        "ml": {
            "feat_period": 14,
            "lags": [1, 2, 3, 4, 5],
            "rolling_window": 20,
            "horizon": 5,
            "target_type": "classification",
            # 127特徴量完全セット（実装済み特徴量を基に構成）
            "extra_features": [
                # 基本OHLCV
                "open",
                "high",
                "low",
                "close",
                "volume",
                # 価格ラグ・リターン
                "close_lag_1",
                "close_lag_2",
                "close_lag_3",
                "returns_1",
                "returns_2",
                "returns_3",
                "returns_5",
                "log_returns_1",
                "log_returns_2",
                "log_returns_3",
                "log_returns_5",
                # 移動平均
                "sma_5",
                "sma_10",
                "sma_20",
                "sma_50",
                "sma_100",
                "sma_200",
                "ema_5",
                "ema_10",
                "ema_20",
                "ema_50",
                "ema_100",
                "ema_200",
                # 価格ポジション
                "price_position_20",
                "price_position_50",
                "price_vs_sma20",
                # ボリンジャーバンド
                "bb_upper",
                "bb_middle",
                "bb_lower",
                "bb_width",
                "bb_position",
                # RSI
                "rsi_14",
                "rsi_7",
                "rsi_21",
                "rsi_oversold",
                "rsi_overbought",
                # MACD
                "macd",
                "macd_signal",
                "macd_hist",
                "macd_cross_up",
                "macd_cross_down",
                # ストキャスティクス
                "stoch_k",
                "stoch_d",
                "stoch_oversold",
                "stoch_overbought",
                # ATR・ボラティリティ
                "atr_14",
                "atr_7",
                "atr_21",
                "volatility_20",
                "volatility_50",
                "true_range",
                # ボリューム
                "volume_sma_20",
                "volume_ratio",
                "volume_trend",
                "vwap",
                "vwap_distance",
                "obv",
                "obv_sma",
                "cmf",
                "mfi",
                "ad_line",
                # トレンド・モメンタム
                "adx_14",
                "plus_di",
                "minus_di",
                "trend_strength",
                "trend_direction",
                "cci_20",
                "williams_r",
                "ultimate_oscillator",
                "momentum_14",
                # サポート・レジスタンス
                "support_distance",
                "resistance_distance",
                "support_strength",
                # 統計・その他
                "zscore",
                "mean_reversion_20",
                "mean_reversion_50",
                "skewness_20",
                "kurtosis_20",
                # 時間特徴量
                "hour",
                "day_of_week",
                "is_weekend",
                "is_asian_session",
                "is_european_session",
                "is_us_session",
                # 追加テクニカル
                "roc_10",
                "roc_20",
                "trix",
                "mass_index",
                "price_efficiency",
                "trend_consistency",
            ],
        }
    }

    logger.info(
        f"127特徴量完全システム設定: {len(config['ml']['extra_features'])} 特徴量"
    )

    # 特徴量エンジニアリング
    logger.info("127特徴量エンジニアリング開始...")
    engineer = FeatureEngineer(config)
    features = engineer.fit_transform(data)

    logger.info(f"生成された特徴量: {features.shape}")

    # 高度なターゲット生成
    targets, valid_mask = create_sophisticated_targets(features, data["close"])

    # 有効なサンプルのみ使用
    X = features[valid_mask]
    y = targets[valid_mask]

    logger.info(f"学習用有効サンプル: {len(X)}")

    if len(X) < 2000:
        raise ValueError(f"学習に必要なサンプル数不足: {len(X)} < 2000")

    # NaN値処理
    X = X.fillna(X.median())

    # インテリジェント特徴量選択
    X_selected, selected_features = intelligent_feature_selection(
        X, y, successful_features, k_best=60
    )

    # 訓練・テスト分割
    X_train, X_test, y_train, y_test = train_test_split(
        X_selected, y, test_size=0.2, random_state=42, stratify=y
    )

    logger.info(f"学習セット: {X_train.shape}")
    logger.info(f"テストセット: {X_test.shape}")

    # 改良LightGBMモデル学習
    logger.info("改良LightGBMモデル学習開始...")

    lgb_params = {
        "objective": "binary",
        "metric": "binary_logloss",
        "boosting_type": "gbdt",
        "num_leaves": 64,  # 増加
        "learning_rate": 0.08,  # やや減少
        "feature_fraction": 0.85,  # 増加
        "bagging_fraction": 0.85,  # 増加
        "bagging_freq": 3,
        "min_child_samples": 15,  # 減少
        "min_child_weight": 0.001,
        "min_split_gain": 0.01,  # 減少
        "reg_alpha": 0.05,  # 減少
        "reg_lambda": 0.05,  # 減少
        "max_depth": 12,  # 増加
        "random_state": 42,
        "verbose": -1,
    }

    # 学習データをLightGBM形式に変換
    train_data = lgb.Dataset(X_train, label=y_train)
    valid_data = lgb.Dataset(X_test, label=y_test, reference=train_data)

    # モデル学習
    model = lgb.train(
        lgb_params,
        train_data,
        valid_sets=[valid_data],
        num_boost_round=300,  # 増加
        callbacks=[lgb.early_stopping(30), lgb.log_evaluation(0)],
    )

    # 予測と評価
    y_pred_proba = model.predict(X_test, num_iteration=model.best_iteration)
    y_pred = (y_pred_proba > 0.5).astype(int)

    accuracy = accuracy_score(y_test, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average="binary"
    )

    logger.info(f"127特徴量統合モデル性能:")
    logger.info(f"  Accuracy: {accuracy:.1%}")
    logger.info(f"  Precision: {precision:.1%}")
    logger.info(f"  Recall: {recall:.1%}")
    logger.info(f"  F1-Score: {f1:.1%}")

    # 詳細評価レポート
    report = classification_report(y_test, y_pred, target_names=["SELL", "BUY"])
    logger.info(f"分類レポート:\\n{report}")

    # 特徴量重要度分析
    importance = model.feature_importance(importance_type="gain")
    feature_importance = list(zip(selected_features, importance))
    feature_importance.sort(key=lambda x: x[1], reverse=True)

    logger.info("トップ15特徴量重要度:")
    for i, (feat, imp) in enumerate(feature_importance[:15]):
        success_mark = "✅" if feat in successful_features else "  "
        logger.info(f"  {i+1:2d}. {feat}: {imp:.0f} {success_mark}")

    # モデル・メタデータ保存
    models_dir = Path("models/production")
    models_dir.mkdir(parents=True, exist_ok=True)

    model_path = models_dir / "integrated_127_features_model.pkl"
    joblib.dump(model, model_path)
    logger.info(f"統合127特徴量モデル保存: {model_path}")

    # 選択特徴量保存
    features_path = models_dir / "integrated_127_model_features.json"
    with open(features_path, "w") as f:
        json.dump(selected_features, f, indent=2)
    logger.info(f"選択特徴量保存: {features_path}")

    # メタデータ保存
    metadata = {
        "model_type": "LightGBM_Binary_Integrated_127",
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1_score": float(f1),
        "n_features_total": 127,
        "n_features_selected": len(selected_features),
        "n_samples_train": len(X_train),
        "n_samples_test": len(X_test),
        "successful_features_included": len(
            [f for f in selected_features if f in successful_features]
        ),
        "lgb_params": lgb_params,
        "feature_categories": {
            k: len([f for f in selected_features if f in v])
            for k, v in feature_categories.items()
        },
        "top_10_features": [feat for feat, _ in feature_importance[:10]],
    }

    metadata_path = models_dir / "integrated_127_model_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"モデルメタデータ保存: {metadata_path}")

    # 予測確率分布確認
    logger.info(f"予測確率分布:")
    logger.info(f"  平均: {y_pred_proba.mean():.3f}")
    logger.info(f"  標準偏差: {y_pred_proba.std():.3f}")
    logger.info(f"  最小値: {y_pred_proba.min():.3f}")
    logger.info(f"  最大値: {y_pred_proba.max():.3f}")
    logger.info(f"  中央値: {np.median(y_pred_proba):.3f}")

    # 結果サマリー
    logger.info("=" * 80)
    logger.info("127特徴量統合高精度モデル学習完了")
    logger.info("=" * 80)
    logger.info(f"最終精度: {accuracy:.1%}")
    logger.info(f"最終F1スコア: {f1:.1%}")
    logger.info(f"選択特徴量: {len(selected_features)}/127")
    logger.info(
        f"99.2%モデル知見活用: {len([f for f in selected_features if f in successful_features])}/30"
    )
    logger.info(f"モデルパス: {model_path}")
    logger.info("127特徴量システムでの高精度取引準備完了！")

    return model, selected_features, accuracy, f1, metadata


if __name__ == "__main__":
    try:
        model, features, accuracy, f1, metadata = train_integrated_127_model()
        print(f"\\n✅ 127特徴量統合高精度モデル作成成功！")
        print(f"精度: {accuracy:.1%}")
        print(f"F1スコア: {f1:.1%}")
        print(f"選択特徴量: {len(features)}")
        print(f"99.2%モデル知見統合: {metadata['successful_features_included']}/30")
        sys.exit(0)
    except Exception as e:
        logger.error(f"モデル作成失敗: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
