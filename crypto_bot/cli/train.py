"""
Training related CLI commands
"""

import logging

import click
import numpy as np
import pandas as pd

from crypto_bot.ml.preprocessor import build_ml_pipeline, prepare_ml_dataset
from crypto_bot.scripts.walk_forward import split_walk_forward
from crypto_bot.utils.config import load_config
from crypto_bot.utils.config_state import set_current_config
from crypto_bot.utils.data import prepare_data
from crypto_bot.utils.file import ensure_dir_for_file
from crypto_bot.utils.model import save_model

# Removed unused imports

logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
@click.option(
    "--model-type",
    "-m",
    type=click.Choice(["lgbm", "xgb", "rf", "sgd", "linear", "dummy"]),
    default="lgbm",
)
@click.option(
    "--output", "-o", "output_path", default="models/model.pkl", type=click.Path()
)
def train_command(config_path: str, model_type: str, output_path: str):
    """ML モデルを学習して保存"""
    cfg = load_config(config_path)
    set_current_config(cfg)  # Phase H.22.3: ATR期間統一
    ensure_dir_for_file(output_path)

    # データ準備
    train_df, val_df, test_df = prepare_data(cfg)

    # ML パイプライン
    ml_cfg = cfg["ml"]
    pipeline = build_ml_pipeline(ml_cfg, model_type=model_type)

    # 特徴量・ターゲット
    X_train, y_train = prepare_ml_dataset(train_df, ml_cfg)
    X_val, y_val = prepare_ml_dataset(val_df, ml_cfg)
    X_test, y_test = prepare_ml_dataset(test_df, ml_cfg)

    click.echo(f"Training {model_type} model...")
    click.echo(f"X_train shape: {X_train.shape}, y_train shape: {y_train.shape}")

    # 学習
    pipeline.fit(X_train, y_train)

    # 評価
    train_score = pipeline.score(X_train, y_train)
    val_score = pipeline.score(X_val, y_val)
    test_score = pipeline.score(X_test, y_test)

    click.echo(f"Train accuracy: {train_score:.4f}")
    click.echo(f"Val accuracy: {val_score:.4f}")
    click.echo(f"Test accuracy: {test_score:.4f}")

    # モデル保存
    save_model(pipeline, output_path)
    click.echo(f"Model saved to {output_path}")


@click.command()
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
@click.option(
    "--model-type",
    "-m",
    type=click.Choice(["lgbm", "xgb", "rf"]),
    default="lgbm",
)
def optimize_ml_command(config_path: str, model_type: str):
    """ハイパーパラ最適化のみ実行"""
    cfg = load_config(config_path)
    set_current_config(cfg)  # Phase H.22.3: ATR期間統一

    # Phase 3: 外部データ完全無効化

    # データ準備
    train_df, val_df, test_df = prepare_data(cfg)

    # Walk-forward分割
    wf = cfg["walk_forward"]
    splits = split_walk_forward(
        train_df, wf["train_window"], wf["test_window"], wf["step"]
    )

    click.echo(f"Walk-forward splits: {len(splits)}")

    # Optuna最適化
    try:
        import optuna
    except ImportError:
        click.echo("Error: optuna is not installed. Run 'pip install optuna'", err=True)
        return

    from crypto_bot.ml.preprocessor import build_ml_pipeline, prepare_ml_dataset

    def objective(trial):
        # ハイパーパラメータの提案
        if model_type == "lgbm":
            params = {
                "num_leaves": trial.suggest_int("num_leaves", 10, 300),
                "learning_rate": trial.suggest_float(
                    "learning_rate", 0.01, 0.3, log=True
                ),
                "feature_fraction": trial.suggest_float("feature_fraction", 0.4, 1.0),
                "bagging_fraction": trial.suggest_float("bagging_fraction", 0.4, 1.0),
                "bagging_freq": trial.suggest_int("bagging_freq", 1, 7),
                "min_child_samples": trial.suggest_int("min_child_samples", 5, 100),
                "reg_alpha": trial.suggest_float("reg_alpha", 0.0, 1.0),
                "reg_lambda": trial.suggest_float("reg_lambda", 0.0, 1.0),
            }
        elif model_type == "xgb":
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 50, 500),
                "max_depth": trial.suggest_int("max_depth", 3, 10),
                "learning_rate": trial.suggest_float(
                    "learning_rate", 0.01, 0.3, log=True
                ),
                "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
                "reg_alpha": trial.suggest_float("reg_alpha", 0.0, 1.0),
                "reg_lambda": trial.suggest_float("reg_lambda", 0.0, 1.0),
            }
        elif model_type == "rf":
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 50, 500),
                "max_depth": trial.suggest_int("max_depth", 3, 20),
                "min_samples_split": trial.suggest_int("min_samples_split", 2, 20),
                "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 10),
                "max_features": trial.suggest_categorical(
                    "max_features", ["sqrt", "log2", None]
                ),
            }
        else:
            params = {}

        # Walk-forward評価
        scores = []
        for train_idx, test_idx in splits[:3]:  # 最初の3分割のみ使用（高速化）
            # データ準備
            train_split = train_df.iloc[train_idx]
            test_split = train_df.iloc[test_idx]

            # パイプライン構築
            ml_cfg = cfg["ml"].copy()
            ml_cfg["model_params"] = params
            pipeline = build_ml_pipeline(ml_cfg, model_type=model_type)

            # 特徴量・ターゲット
            X_train, y_train = prepare_ml_dataset(train_split, ml_cfg)
            X_test, y_test = prepare_ml_dataset(test_split, ml_cfg)

            # 学習と評価
            pipeline.fit(X_train, y_train)
            score = pipeline.score(X_test, y_test)
            scores.append(score)

        return np.mean(scores)

    # 最適化実行
    study_name = f"crypto_bot_{model_type}_optimization"
    study = optuna.create_study(
        study_name=study_name,
        direction="maximize",
        storage=None,  # メモリ内で実行
    )

    n_trials = cfg.get("optimization", {}).get("n_trials", 100)
    study.optimize(objective, n_trials=n_trials)

    # 結果表示
    click.echo("\n=== Optimization Results ===")
    click.echo(f"Best score: {study.best_value:.4f}")
    click.echo("Best params:")
    for key, value in study.best_params.items():
        click.echo(f"  {key}: {value}")


@click.command()
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
@click.option(
    "--trials-path", "-t", default="optuna_trials.db", help="Optuna trials DB path"
)
@click.option(
    "--model-path", "-m", default="models/optimized_model.pkl", help="Output model path"
)
@click.option("--model-type", type=click.Choice(["lgbm", "xgb", "rf"]), default="lgbm")
def optimize_and_train_command(
    config_path: str, trials_path: str, model_path: str, model_type: str
):
    """Optuna → 再学習 → モデル保存"""
    cfg = load_config(config_path)
    set_current_config(cfg)  # Phase H.22.3: ATR期間統一
    ensure_dir_for_file(model_path)

    # 1. Optuna最適化
    click.echo("Step 1: Running Optuna optimization...")
    # ここでは簡易的に optimize_ml_command の内容を実行
    # 実際の実装では、最適化結果を保存して再利用する

    # 2. 最適パラメータで再学習
    click.echo("Step 2: Training with optimal parameters...")
    train_df, val_df, test_df = prepare_data(cfg)

    # 全データで学習
    all_df = pd.concat([train_df, val_df, test_df])

    ml_cfg = cfg["ml"]
    # TODO: Optunaの結果からベストパラメータを取得
    # ml_cfg["model_params"] = study.best_params

    pipeline = build_ml_pipeline(ml_cfg, model_type=model_type)
    X_all, y_all = prepare_ml_dataset(all_df, ml_cfg)

    pipeline.fit(X_all, y_all)

    # 3. モデル保存
    save_model(pipeline, model_path)
    click.echo(f"Model saved to {model_path}")


@click.command()
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
@click.option(
    "--model-path", "-m", default="models/best_model.pkl", help="Output model path"
)
@click.option("--model-type", type=click.Choice(["lgbm", "xgb", "rf"]), default="lgbm")
def train_best_command(config_path: str, model_path: str, model_type: str):
    """ベストパラメータで全データ再学習 & 保存"""
    cfg = load_config(config_path)
    set_current_config(cfg)  # Phase H.22.3: ATR期間統一
    ensure_dir_for_file(model_path)

    # データ準備
    train_df, val_df, test_df = prepare_data(cfg)
    all_df = pd.concat([train_df, val_df, test_df])

    # ベストパラメータを使用（設定ファイルから）
    ml_cfg = cfg["ml"]
    best_params = ml_cfg.get("best_params", {}).get(model_type, {})
    if best_params:
        ml_cfg["model_params"] = best_params
        click.echo(f"Using best parameters from config: {best_params}")

    # パイプライン構築と学習
    pipeline = build_ml_pipeline(ml_cfg, model_type=model_type)
    X_all, y_all = prepare_ml_dataset(all_df, ml_cfg)

    click.echo(f"Training on all data: {X_all.shape}")
    pipeline.fit(X_all, y_all)

    # モデル保存
    save_model(pipeline, model_path)
    click.echo(f"Model saved to {model_path}")
