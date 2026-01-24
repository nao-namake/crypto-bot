#!/usr/bin/env python3
"""
Walk-Forward Validation スクリプト - Phase 61

過学習を排除したバックテスト検証システム。
ローリングウィンドウ方式で訓練・テストを分離し、
真のML予測力を評価する。

使用方法:
    # 実行
    python scripts/backtest/walk_forward_validation.py

    # ドライラン（ウィンドウ確認のみ）
    python scripts/backtest/walk_forward_validation.py --dry-run

    # 詳細ログ
    python scripts/backtest/walk_forward_validation.py --verbose

    # CIの最新Walk-Forward結果を取得して分析
    python scripts/backtest/walk_forward_validation.py --from-ci
"""

import argparse
import asyncio
import json
import logging
import os
import pickle
import shutil
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yaml

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.logger import get_logger


class WalkForwardValidator:
    """
    Walk-Forward検証クラス

    ローリングウィンドウ方式で以下を実行:
    1. 訓練期間のデータでMLモデルを訓練
    2. テスト期間でバックテスト実行
    3. 全ウィンドウの結果を集計・評価
    """

    def __init__(self, config_path: str = None, verbose: bool = False):
        """
        初期化

        Args:
            config_path: 設定ファイルパス
            verbose: 詳細ログ出力
        """
        self.logger = get_logger(__name__)
        self.verbose = verbose

        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)

        # 設定読み込み
        if config_path is None:
            config_path = project_root / "config/core/wf_config.yaml"
        self.config = self._load_config(config_path)

        # ウィンドウ設定
        wf_config = self.config.get("walk_forward", {})
        self.train_days = wf_config.get("train_days", 60)
        self.test_days = wf_config.get("test_days", 30)
        self.step_days = wf_config.get("step_days", 30)

        # データ期間
        self.data_start = datetime.strptime(wf_config.get("data_start", "2025-07-01"), "%Y-%m-%d")
        self.data_end = datetime.strptime(wf_config.get("data_end", "2025-12-31"), "%Y-%m-%d")

        # ML設定
        ml_config = wf_config.get("ml_training", {})
        self.n_classes = ml_config.get("n_classes", 3)
        self.use_smote = ml_config.get("use_smote", True)
        self.optimize = ml_config.get("optimize", False)
        self.n_trials = ml_config.get("n_trials", 10)
        self.target_threshold = ml_config.get("target_threshold", 0.0005)

        # バックテスト設定
        bt_config = wf_config.get("backtest", {})
        self.symbol = bt_config.get("symbol", "BTC/JPY")
        self.timeframes = bt_config.get("timeframes", ["15m", "4h"])
        self.initial_balance = bt_config.get("initial_balance", 500000)

        # 出力設定
        output_config = wf_config.get("output", {})
        self.output_dir = Path(output_config.get("dir", "docs/検証記録"))
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 安定性閾値
        stability = wf_config.get("stability_thresholds", {})
        self.min_pf = stability.get("min_pf", 1.0)
        self.max_pf_std = stability.get("max_pf_std", 0.3)
        self.min_win_rate = stability.get("min_win_rate", 0.45)
        self.max_wf_vs_full_diff = stability.get("max_wf_vs_full_diff", 0.20)

        # 結果格納
        self.window_results: List[Dict] = []
        self.full_backtest_result: Optional[Dict] = None

        self.logger.info("=" * 60)
        self.logger.info("Walk-Forward Validation 初期化完了")
        self.logger.info(f"  訓練期間: {self.train_days}日")
        self.logger.info(f"  テスト期間: {self.test_days}日")
        self.logger.info(f"  ステップ: {self.step_days}日")
        self.logger.info(f"  データ期間: {self.data_start.date()} ~ {self.data_end.date()}")
        self.logger.info("=" * 60)

    def _load_config(self, config_path: str) -> Dict:
        """設定ファイル読み込み"""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"設定ファイル読み込みエラー: {e}")
            return {}

    def generate_windows(self) -> List[Dict]:
        """
        ローリングウィンドウ生成

        Returns:
            ウィンドウリスト [{"window_id": 1, "train_start": ..., "train_end": ..., "test_start": ..., "test_end": ...}, ...]
        """
        windows = []
        window_id = 1

        # 最初のウィンドウ開始位置
        train_start = self.data_start

        while True:
            train_end = train_start + timedelta(days=self.train_days)
            test_start = train_end + timedelta(days=1)
            test_end = test_start + timedelta(days=self.test_days - 1)

            # データ期間を超えたら終了
            if test_end > self.data_end:
                break

            windows.append(
                {
                    "window_id": window_id,
                    "train_start": train_start,
                    "train_end": train_end,
                    "test_start": test_start,
                    "test_end": test_end,
                }
            )

            self.logger.info(
                f"Window {window_id}: "
                f"Train {train_start.date()} ~ {train_end.date()} | "
                f"Test {test_start.date()} ~ {test_end.date()}"
            )

            # 次のウィンドウへ
            train_start = train_start + timedelta(days=self.step_days)
            window_id += 1

        self.logger.info(f"合計 {len(windows)} ウィンドウ生成")
        return windows

    async def run_window(self, window: Dict) -> Dict:
        """
        単一ウィンドウの訓練・テスト実行

        Args:
            window: ウィンドウ情報

        Returns:
            ウィンドウ結果
        """
        window_id = window["window_id"]
        self.logger.info("=" * 60)
        self.logger.info(f"Window {window_id} 開始")
        self.logger.info("=" * 60)

        result = {
            "window_id": window_id,
            "train_period": {
                "start": window["train_start"].isoformat(),
                "end": window["train_end"].isoformat(),
            },
            "test_period": {
                "start": window["test_start"].isoformat(),
                "end": window["test_end"].isoformat(),
            },
            "ml_training": {},
            "backtest": {},
            "status": "pending",
        }

        try:
            # Step 1: MLモデル訓練
            self.logger.info(f"[Window {window_id}] Step 1: MLモデル訓練開始")
            ml_result = await self._train_ml_model(window)
            result["ml_training"] = ml_result

            if ml_result.get("status") != "success":
                result["status"] = "ml_training_failed"
                return result

            # Step 2: バックテスト実行
            self.logger.info(f"[Window {window_id}] Step 2: バックテスト実行開始")
            bt_result = await self._run_backtest(window)
            result["backtest"] = bt_result

            if bt_result.get("status") != "success":
                result["status"] = "backtest_failed"
                return result

            result["status"] = "success"
            self.logger.info(
                f"[Window {window_id}] 完了: PF={bt_result.get('profit_factor', 'N/A')}"
            )

        except Exception as e:
            self.logger.error(f"[Window {window_id}] エラー: {e}")
            result["status"] = "error"
            result["error"] = str(e)

        return result

    async def _train_ml_model(self, window: Dict) -> Dict:
        """
        MLモデル訓練（ウィンドウ別）

        Args:
            window: ウィンドウ情報

        Returns:
            訓練結果
        """
        window_id = window["window_id"]
        train_start = window["train_start"]
        train_end = window["train_end"]

        result = {
            "status": "pending",
            "train_period": f"{train_start.date()} ~ {train_end.date()}",
        }

        try:
            # NewSystemMLModelCreatorを使用してモデル訓練
            from scripts.ml.create_ml_models import NewSystemMLModelCreator

            # 訓練日数計算
            train_days = (train_end - train_start).days

            self.logger.info(
                f"  訓練期間: {train_days}日 ({train_start.date()} ~ {train_end.date()})"
            )

            # モデル作成インスタンス
            creator = NewSystemMLModelCreator(
                verbose=self.verbose,
                target_threshold=self.target_threshold,
                n_classes=self.n_classes,
                use_smote=self.use_smote,
                optimize=self.optimize,
                n_trials=self.n_trials,
                models_to_train=["full"],  # fullモデルのみ
                stacking=False,
            )

            # 訓練データ準備（期間フィルタはcreator内部で実施）
            # 一時的にthresholds.yamlの日付を上書き
            original_thresholds = self._backup_thresholds()
            self._set_training_period(train_start, train_end)

            try:
                # モデル訓練実行
                # Note: days=365で全期間データを取得（cutoff_dateフィルタ対策）
                # 実際のフィルタリングは下のmaskで行う
                features, target = await creator.prepare_training_data_async(days=365)

                # 期間でフィルタリング
                if hasattr(features, "index") and len(features) > 0:
                    mask = (features.index >= train_start) & (features.index <= train_end)
                    features = features[mask]
                    target = target[mask]

                self.logger.info(f"  訓練データ: {len(features)}サンプル")

                if len(features) < 100:
                    self.logger.warning(f"  訓練データ不足: {len(features)}サンプル")
                    result["status"] = "insufficient_data"
                    return result

                # モデル訓練
                training_result = creator.train_models(features, target)

                # 一時モデル保存（Window別）
                temp_model_path = Path(f"models/walk_forward/window_{window_id}")
                temp_model_path.mkdir(parents=True, exist_ok=True)

                # ProductionEnsembleとして保存
                ensemble = creator._create_ensemble(creator.models)
                ensemble_path = temp_model_path / "ensemble_full.pkl"
                with open(ensemble_path, "wb") as f:
                    pickle.dump(ensemble, f)

                result["status"] = "success"
                result["model_path"] = str(ensemble_path)
                result["samples"] = len(features)
                result["metrics"] = training_result.get("evaluation", {})

            finally:
                # thresholds.yaml復元
                self._restore_thresholds(original_thresholds)

        except Exception as e:
            self.logger.error(f"  ML訓練エラー: {e}")
            import traceback

            self.logger.error(traceback.format_exc())
            result["status"] = "error"
            result["error"] = str(e)

        return result

    async def _run_backtest(self, window: Dict) -> Dict:
        """
        バックテスト実行（ウィンドウ別）

        Args:
            window: ウィンドウ情報

        Returns:
            バックテスト結果
        """
        window_id = window["window_id"]
        test_start = window["test_start"]
        test_end = window["test_end"]

        result = {
            "status": "pending",
            "test_period": f"{test_start.date()} ~ {test_end.date()}",
        }

        try:
            # Window別モデルを本番ディレクトリにコピー
            temp_model_path = Path(f"models/walk_forward/window_{window_id}/ensemble_full.pkl")
            prod_model_path = Path("models/production/ensemble_full.pkl")

            if not temp_model_path.exists():
                result["status"] = "model_not_found"
                return result

            # 本番モデルをバックアップ
            prod_backup_path = Path("models/production/ensemble_full.pkl.backup")
            if prod_model_path.exists():
                shutil.copy(prod_model_path, prod_backup_path)

            # Window別モデルを本番にコピー
            shutil.copy(temp_model_path, prod_model_path)

            try:
                # バックテスト期間設定
                self._set_backtest_period(test_start, test_end)

                # バックテスト実行（main.py --mode backtest相当）
                # Phase 61.1: バックテストモード設定を正しく行う
                from src.core.config import (
                    load_config,
                    set_backtest_log_level,
                    set_backtest_mode,
                )
                from src.core.orchestration import create_trading_orchestrator

                # バックテストモード設定（main.pyと同じ方法）
                os.environ["LOG_LEVEL"] = "WARNING"
                os.environ["BACKTEST_MODE"] = "true"
                set_backtest_mode(True)
                set_backtest_log_level("WARNING")

                # cmdline_mode="backtest"でconfig.mode=backtestになる
                config = load_config("config/core/unified.yaml", cmdline_mode="backtest")
                orchestrator = await create_trading_orchestrator(config=config, logger=self.logger)

                # バックテスト実行
                success = await orchestrator.runner.run()

                if success:
                    # 結果取得
                    bt_result = self._extract_backtest_result(window_id)
                    result.update(bt_result)
                    result["status"] = "success"
                else:
                    result["status"] = "backtest_failed"

            finally:
                # 本番モデル復元
                if prod_backup_path.exists():
                    shutil.copy(prod_backup_path, prod_model_path)
                    prod_backup_path.unlink()

        except Exception as e:
            self.logger.error(f"  バックテストエラー: {e}")
            import traceback

            self.logger.error(traceback.format_exc())
            result["status"] = "error"
            result["error"] = str(e)

        return result

    def _extract_backtest_result(self, window_id: int) -> Dict:
        """バックテスト結果を抽出"""
        result = {}

        try:
            # 最新のバックテスト結果JSONを取得
            log_dir = Path("src/backtest/logs")
            json_files = sorted(
                log_dir.glob("backtest_*.json"), key=lambda x: x.stat().st_mtime, reverse=True
            )

            if json_files:
                with open(json_files[0], "r", encoding="utf-8") as f:
                    bt_data = json.load(f)

                # 主要指標を抽出
                summary = bt_data.get("summary", {})
                result["total_trades"] = summary.get("total_trades", 0)
                result["win_rate"] = summary.get("win_rate", 0)
                result["profit_factor"] = summary.get("profit_factor", 0)
                result["total_pnl"] = summary.get("total_pnl", 0)
                result["max_drawdown"] = summary.get("max_drawdown_pct", 0)

        except Exception as e:
            self.logger.warning(f"バックテスト結果抽出エラー: {e}")

        return result

    def _backup_thresholds(self) -> Dict:
        """thresholds.yamlのバックアップ"""
        try:
            with open("config/core/thresholds.yaml", "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception:
            return {}

    def _restore_thresholds(self, original: Dict):
        """thresholds.yamlの復元"""
        try:
            with open("config/core/thresholds.yaml", "w", encoding="utf-8") as f:
                yaml.dump(original, f, default_flow_style=False, allow_unicode=True)
        except Exception as e:
            self.logger.warning(f"thresholds.yaml復元エラー: {e}")

    def _set_training_period(self, start: datetime, end: datetime):
        """訓練期間の設定（thresholds.yaml更新）"""
        # 訓練データ収集のためにthresholds.yamlを更新する必要がある場合
        pass  # NewSystemMLModelCreatorが内部で処理

    def _set_backtest_period(self, start: datetime, end: datetime):
        """バックテスト期間の設定"""
        try:
            with open("config/core/thresholds.yaml", "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if "execution" not in config:
                config["execution"] = {}

            config["execution"]["backtest_use_fixed_dates"] = True
            config["execution"]["backtest_start_date"] = start.strftime("%Y-%m-%d")
            config["execution"]["backtest_end_date"] = end.strftime("%Y-%m-%d")

            with open("config/core/thresholds.yaml", "w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

        except Exception as e:
            self.logger.error(f"バックテスト期間設定エラー: {e}")

    async def run_all(self) -> Dict:
        """
        全ウィンドウ実行・集計

        Returns:
            集計結果
        """
        self.logger.info("=" * 60)
        self.logger.info("Walk-Forward Validation 開始")
        self.logger.info("=" * 60)

        start_time = datetime.now()

        # ウィンドウ生成
        windows = self.generate_windows()

        if not windows:
            self.logger.error("ウィンドウが生成されませんでした")
            return {"status": "error", "message": "No windows generated"}

        # 本番thresholds.yamlバックアップ
        original_thresholds = self._backup_thresholds()

        try:
            # 各ウィンドウを順次実行
            for window in windows:
                result = await self.run_window(window)
                self.window_results.append(result)

                # 進捗表示
                completed = len(self.window_results)
                total = len(windows)
                self.logger.info(f"進捗: {completed}/{total} ウィンドウ完了")

        finally:
            # thresholds.yaml復元
            self._restore_thresholds(original_thresholds)

        # 集計・レポート生成
        elapsed = datetime.now() - start_time
        self.logger.info(f"全ウィンドウ完了: 実行時間 {elapsed}")

        aggregate_result = self._aggregate_results()
        self._generate_report(aggregate_result)

        return aggregate_result

    def _aggregate_results(self) -> Dict:
        """結果集計"""
        successful_windows = [
            w
            for w in self.window_results
            if w.get("status") == "success" and w.get("backtest", {}).get("profit_factor", 0) > 0
        ]

        if not successful_windows:
            return {
                "status": "no_successful_windows",
                "window_results": self.window_results,
            }

        # PF統計
        pfs = [w["backtest"]["profit_factor"] for w in successful_windows]
        win_rates = [w["backtest"]["win_rate"] for w in successful_windows]
        pnls = [w["backtest"]["total_pnl"] for w in successful_windows]

        aggregate = {
            "status": "success",
            "execution_time": datetime.now().isoformat(),
            "total_windows": len(self.window_results),
            "successful_windows": len(successful_windows),
            "failed_windows": len(self.window_results) - len(successful_windows),
            "aggregate_metrics": {
                "mean_pf": float(np.mean(pfs)),
                "std_pf": float(np.std(pfs)),
                "min_pf": float(np.min(pfs)),
                "max_pf": float(np.max(pfs)),
                "mean_win_rate": float(np.mean(win_rates)),
                "std_win_rate": float(np.std(win_rates)),
                "total_pnl": float(np.sum(pnls)),
                "mean_pnl_per_window": float(np.mean(pnls)),
            },
            "stability_assessment": self._assess_stability(pfs, win_rates),
            "window_details": self.window_results,
        }

        return aggregate

    def _assess_stability(self, pfs: List[float], win_rates: List[float]) -> Dict:
        """安定性評価"""
        std_pf = np.std(pfs)
        all_positive = all(pf > self.min_pf for pf in pfs)
        low_variance = std_pf < self.max_pf_std

        # 安定性判定
        if all_positive and low_variance:
            stability = "stable"
            risk = "low"
        elif all_positive or low_variance:
            stability = "moderate"
            risk = "medium"
        else:
            stability = "unstable"
            risk = "high"

        return {
            "is_stable": stability == "stable",
            "stability_level": stability,
            "overfitting_risk": risk,
            "all_windows_profitable": all_positive,
            "low_variance": low_variance,
            "criteria": {
                "min_pf_threshold": self.min_pf,
                "max_std_threshold": self.max_pf_std,
            },
        }

    def _generate_report(self, aggregate: Dict):
        """レポート生成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSON保存
        json_path = self.output_dir / f"walk_forward_{timestamp}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(aggregate, f, indent=2, ensure_ascii=False, default=str)
        self.logger.info(f"JSONレポート保存: {json_path}")

        # Markdownレポート生成
        md_path = self.output_dir / f"walk_forward_{timestamp}.md"
        md_content = self._generate_markdown_report(aggregate)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        self.logger.info(f"Markdownレポート保存: {md_path}")

    def _generate_markdown_report(self, aggregate: Dict) -> str:
        """Markdownレポート生成"""
        metrics = aggregate.get("aggregate_metrics", {})
        stability = aggregate.get("stability_assessment", {})

        md = f"""# Walk-Forward Validation レポート

**実行日時**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## サマリー

| 項目 | 値 |
|------|-----|
| 総ウィンドウ数 | {aggregate.get('total_windows', 0)} |
| 成功ウィンドウ | {aggregate.get('successful_windows', 0)} |
| 失敗ウィンドウ | {aggregate.get('failed_windows', 0)} |

---

## 集計指標

| 指標 | 値 |
|------|-----|
| 平均PF | {metrics.get('mean_pf', 0):.2f} |
| PF標準偏差 | {metrics.get('std_pf', 0):.3f} |
| 最小PF | {metrics.get('min_pf', 0):.2f} |
| 最大PF | {metrics.get('max_pf', 0):.2f} |
| 平均勝率 | {metrics.get('mean_win_rate', 0) * 100:.1f}% |
| 総損益 | ¥{metrics.get('total_pnl', 0):,.0f} |

---

## 安定性評価

| 項目 | 結果 |
|------|------|
| 安定性レベル | {stability.get('stability_level', 'N/A')} |
| 過学習リスク | {stability.get('overfitting_risk', 'N/A')} |
| 全ウィンドウ黒字 | {'Yes' if stability.get('all_windows_profitable') else 'No'} |
| 低分散 | {'Yes' if stability.get('low_variance') else 'No'} |

---

## ウィンドウ別結果

| Window | 訓練期間 | テスト期間 | PF | 勝率 | 損益 | 状態 |
|--------|---------|----------|-----|------|------|------|
"""
        for w in aggregate.get("window_details", []):
            train_period = w.get("train_period", {})
            test_period = w.get("test_period", {})
            bt = w.get("backtest", {})

            train_str = f"{train_period.get('start', '')[:10]} ~ {train_period.get('end', '')[:10]}"
            test_str = f"{test_period.get('start', '')[:10]} ~ {test_period.get('end', '')[:10]}"

            md += f"| {w.get('window_id', 'N/A')} | {train_str} | {test_str} | {bt.get('profit_factor', 0):.2f} | {bt.get('win_rate', 0) * 100:.1f}% | ¥{bt.get('total_pnl', 0):,.0f} | {w.get('status', 'N/A')} |\n"

        md += f"""
---

## 評価基準

| 指標 | 良好 | 注意 | 危険 |
|------|------|------|------|
| PF標準偏差 | < 0.2 | 0.2-0.4 | > 0.4 |
| 全Window PF | 全て > 1.0 | 1つ < 1.0 | 複数 < 1.0 |
| WF vs Full差 | < 10% | 10-20% | > 20% |

---

**生成日時**: {datetime.now().isoformat()}
"""
        return md

    def dry_run(self):
        """ドライラン（ウィンドウ確認のみ）"""
        self.logger.info("=" * 60)
        self.logger.info("Walk-Forward Validation ドライラン")
        self.logger.info("=" * 60)

        windows = self.generate_windows()

        self.logger.info("")
        self.logger.info("ウィンドウ構成:")
        for w in windows:
            self.logger.info(
                f"  Window {w['window_id']}: "
                f"Train {w['train_start'].date()} ~ {w['train_end'].date()} | "
                f"Test {w['test_start'].date()} ~ {w['test_end'].date()}"
            )

        self.logger.info("")
        self.logger.info(f"合計: {len(windows)} ウィンドウ")
        self.logger.info(f"予想実行時間: {len(windows) * 30}分 ~ {len(windows) * 60}分")


class CIIntegration:
    """GitHub Actions CI連携クラス"""

    WORKFLOW_NAME = "walk_forward.yml"
    ARTIFACT_NAME = "walk-forward-results"
    DOWNLOAD_DIR = Path("docs/検証記録/ci_downloads/walk_forward")

    @classmethod
    def fetch_latest_result(cls) -> Tuple[Optional[str], Optional[str]]:
        """
        最新のCI Walk-Forward結果を取得

        Returns:
            (json_path, run_info): JSONファイルパスと実行情報のタプル
            失敗時は (None, error_message)
        """
        import subprocess

        print("🔍 CI最新Walk-Forward結果を検索中...")

        # gh CLI確認
        if not cls._check_gh_cli():
            return None, "gh CLI がインストールされていません"

        # 最新の成功した実行を取得
        run_id, run_info = cls._get_latest_successful_run()
        if not run_id:
            return None, run_info

        print(f"✅ 最新実行を検出: Run ID {run_id}")
        print(f"   {run_info}")

        # artifactダウンロード
        json_path = cls._download_artifact(run_id)
        if not json_path:
            return None, "artifactのダウンロードに失敗しました"

        return json_path, run_info

    @classmethod
    def _check_gh_cli(cls) -> bool:
        """gh CLI インストール確認"""
        import subprocess

        try:
            result = subprocess.run(
                ["gh", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    @classmethod
    def _get_latest_successful_run(cls) -> Tuple[Optional[str], str]:
        """最新の成功した実行を取得"""
        import subprocess

        try:
            result = subprocess.run(
                [
                    "gh",
                    "run",
                    "list",
                    "--workflow",
                    cls.WORKFLOW_NAME,
                    "--status",
                    "success",
                    "--limit",
                    "1",
                    "--json",
                    "databaseId,createdAt,displayTitle",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return None, f"gh run list 失敗: {result.stderr}"

            runs = json.loads(result.stdout)
            if not runs:
                return None, "成功したWalk-Forward実行が見つかりません"

            run = runs[0]
            run_id = str(run["databaseId"])
            created_at = run["createdAt"]
            title = run.get("displayTitle", "Walk-Forward Validation")

            return run_id, f"実行日時: {created_at}, タイトル: {title}"

        except subprocess.TimeoutExpired:
            return None, "gh run list タイムアウト"
        except json.JSONDecodeError:
            return None, "gh run list の出力パースに失敗"
        except Exception as e:
            return None, f"予期せぬエラー: {e}"

    @classmethod
    def _download_artifact(cls, run_id: str) -> Optional[str]:
        """artifactをダウンロードしてJSONパスを返す"""
        import subprocess

        # ダウンロードディレクトリ準備
        cls.DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

        # 既存のファイルをクリア
        for f in cls.DOWNLOAD_DIR.glob("*"):
            if f.is_file():
                f.unlink()
            elif f.is_dir():
                shutil.rmtree(f)

        print(f"📥 artifact ダウンロード中 (Run ID: {run_id})...")

        try:
            result = subprocess.run(
                [
                    "gh",
                    "run",
                    "download",
                    run_id,
                    "--name",
                    cls.ARTIFACT_NAME,
                    "--dir",
                    str(cls.DOWNLOAD_DIR),
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                print(f"❌ ダウンロード失敗: {result.stderr}")
                return None

            # JSONファイルを探す
            json_files = list(cls.DOWNLOAD_DIR.glob("**/walk_forward_*.json"))
            if not json_files:
                print("❌ JSONファイルが見つかりません")
                return None

            # 最新のJSONファイルを選択
            json_path = max(json_files, key=lambda p: p.stat().st_mtime)
            print(f"✅ JSONファイル取得: {json_path}")

            return str(json_path)

        except subprocess.TimeoutExpired:
            print("❌ ダウンロードタイムアウト")
            return None
        except Exception as e:
            print(f"❌ ダウンロードエラー: {e}")
            return None


def analyze_ci_result(json_path: str):
    """CI結果を分析して表示"""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("\n" + "=" * 60)
    print("📊 Walk-Forward Validation 分析レポート")
    print("=" * 60)

    # 基本情報
    print(f"\n実行日時: {data.get('execution_time', 'N/A')}")
    print(f"総ウィンドウ数: {data.get('total_windows', 0)}")
    print(f"成功ウィンドウ: {data.get('successful_windows', 0)}")
    print(f"失敗ウィンドウ: {data.get('failed_windows', 0)}")

    # 集計指標
    metrics = data.get("aggregate_metrics", {})
    if metrics:
        print("\n【集計指標】")
        print(f"  平均PF: {metrics.get('mean_pf', 0):.2f} (±{metrics.get('std_pf', 0):.3f})")
        print(f"  最小PF: {metrics.get('min_pf', 0):.2f}")
        print(f"  最大PF: {metrics.get('max_pf', 0):.2f}")
        print(f"  平均勝率: {metrics.get('mean_win_rate', 0) * 100:.1f}%")
        print(f"  総損益: ¥{metrics.get('total_pnl', 0):,.0f}")
        print(f"  ウィンドウ平均損益: ¥{metrics.get('mean_pnl_per_window', 0):,.0f}")

    # 安定性評価
    stability = data.get("stability_assessment", {})
    if stability:
        print("\n【安定性評価】")
        print(f"  安定性レベル: {stability.get('stability_level', 'N/A')}")
        print(f"  過学習リスク: {stability.get('overfitting_risk', 'N/A')}")
        print(f"  全ウィンドウ黒字: {'Yes' if stability.get('all_windows_profitable') else 'No'}")
        print(f"  低分散: {'Yes' if stability.get('low_variance') else 'No'}")

    # ウィンドウ別結果
    window_details = data.get("window_details", [])
    if window_details:
        print("\n【ウィンドウ別結果】")
        print("-" * 60)
        for w in window_details:
            bt = w.get("backtest", {})
            test_period = w.get("test_period", {})
            test_str = f"{test_period.get('start', '')[:10]} ~ {test_period.get('end', '')[:10]}"
            status_emoji = "✅" if w.get("status") == "success" else "❌"
            print(
                f"  {status_emoji} Window {w.get('window_id', 'N/A')}: "
                f"PF={bt.get('profit_factor', 0):.2f}, "
                f"勝率={bt.get('win_rate', 0) * 100:.1f}%, "
                f"¥{bt.get('total_pnl', 0):+,.0f} "
                f"({test_str})"
            )

    # 評価サマリー
    print("\n" + "=" * 60)
    print("💡 評価サマリー")
    print("=" * 60)

    if stability.get("is_stable"):
        print("  ✅ 安定性: 良好 - 過学習リスクは低いと評価")
    elif stability.get("stability_level") == "moderate":
        print("  ⚠️ 安定性: 中程度 - 一部ウィンドウで不安定")
    else:
        print("  ❌ 安定性: 不安定 - 過学習の可能性あり")

    if metrics.get("mean_pf", 0) >= 1.5:
        print("  ✅ 収益性: 優良 (平均PF ≥ 1.5)")
    elif metrics.get("mean_pf", 0) >= 1.0:
        print("  ⚠️ 収益性: 許容範囲 (平均PF ≥ 1.0)")
    else:
        print("  ❌ 収益性: 要改善 (平均PF < 1.0)")

    print("=" * 60 + "\n")


async def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="Walk-Forward Validation - Phase 61")
    parser.add_argument("--dry-run", action="store_true", help="ドライラン（ウィンドウ確認のみ）")
    parser.add_argument("--verbose", "-v", action="store_true", help="詳細ログ出力")
    parser.add_argument("--config", type=str, help="設定ファイルパス")
    parser.add_argument(
        "--from-ci",
        action="store_true",
        help="CIの最新Walk-Forward結果を自動取得して分析",
    )
    parser.add_argument(
        "json_path",
        nargs="?",
        help="分析するJSONファイルパス（--from-ci時は不要）",
    )
    args = parser.parse_args()

    # CI連携モード or ローカルJSON分析モード
    if args.from_ci or args.json_path:
        json_path = args.json_path

        if args.from_ci:
            json_path, run_info = CIIntegration.fetch_latest_result()
            if not json_path:
                print(f"❌ CIからの取得に失敗: {run_info}")
                sys.exit(1)
            print(f"📊 CI実行情報: {run_info}")

        if json_path:
            analyze_ci_result(json_path)
            print("✅ Walk-Forward 分析完了")
        return

    # 通常実行モード
    validator = WalkForwardValidator(config_path=args.config, verbose=args.verbose)

    if args.dry_run:
        validator.dry_run()
    else:
        result = await validator.run_all()

        # 最終結果表示
        print("\n" + "=" * 60)
        print("Walk-Forward Validation 完了")
        print("=" * 60)

        if result.get("status") == "success":
            metrics = result.get("aggregate_metrics", {})
            stability = result.get("stability_assessment", {})

            print(f"平均PF: {metrics.get('mean_pf', 0):.2f} (±{metrics.get('std_pf', 0):.3f})")
            print(f"総損益: ¥{metrics.get('total_pnl', 0):,.0f}")
            print(f"安定性: {stability.get('stability_level', 'N/A')}")
            print(f"過学習リスク: {stability.get('overfitting_risk', 'N/A')}")
        else:
            print(f"ステータス: {result.get('status', 'unknown')}")


if __name__ == "__main__":
    asyncio.run(main())
