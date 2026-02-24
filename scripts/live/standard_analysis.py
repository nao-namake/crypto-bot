#!/usr/bin/env python3
"""
ライブモード統合診断スクリプト - Phase 62.10

目的:
  ライブ運用の標準化された分析とインフラ・Bot機能診断を
  統合し、単一スクリプトで完全な診断を実現。

機能:
  - 39項目の固定指標計算（LiveAnalyzer）
  - インフラ基盤診断（InfrastructureChecker）
    - Cloud Run稼働状況
    - Secret Manager権限確認
    - Container安定性
    - Discord通知確認
    - API残高取得確認
    - ポジション復元確認
    - 取引阻害エラー検出
  - Bot機能診断（BotFunctionChecker）
    - 55特徴量システム確認
    - Silent Failure検出
    - 6戦略動作確認
    - ML予測確認
    - レジーム別TP/SL確認
    - Kelly基準確認
    - Atomic Entry Pattern確認
    - Phase 62.9-62.10: Maker戦略確認（エントリー/TP決済）
  - JSON/Markdown/CSV出力
  - 終了コード対応（CI/CD連携用）

使い方:
  # 基本実行（全診断 + 39指標）
  python3 scripts/live/standard_analysis.py

  # 期間指定（48時間）
  python3 scripts/live/standard_analysis.py --hours 48

  # 出力先指定
  python3 scripts/live/standard_analysis.py --output results/live/

  # CI/CD連携（終了コード返却）
  python3 scripts/live/standard_analysis.py --exit-code

  # 簡易チェック（GCPログのみ、API呼び出しなし）
  python3 scripts/live/standard_analysis.py --quick

終了コード:
  0: 正常
  1: 致命的問題（即座対応必須）
  2: 要注意（詳細診断推奨）
  3: 監視継続（軽微な問題）
"""

import argparse
import asyncio
import csv
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# .envファイルからAPIキー読み込み（ローカル実行用）
from dotenv import load_dotenv

env_path = PROJECT_ROOT / "config" / "secrets" / ".env"
if env_path.exists():
    load_dotenv(env_path, override=True)
    # 読み込み確認用ログは後で出力（logger初期化後）

from src.core.logger import get_logger
from src.data.bitbank_client import BitbankClient

# =============================================================================
# インフラ基盤診断（check_infrastructure.sh 移植）
# =============================================================================


@dataclass
class InfrastructureCheckResult:
    """インフラ基盤診断結果"""

    # Cloud Run状態
    cloud_run_status: str = ""  # True/False/Unknown
    latest_revisions: List[str] = field(default_factory=list)

    # Secret Manager
    service_account: str = ""
    bitbank_key_ok: bool = False
    bitbank_secret_ok: bool = False
    discord_ok: bool = False

    # Container安定性
    container_exit_count: int = 0
    runtime_warning_count: int = 0

    # Discord通知
    discord_error_count: int = 0

    # API残高取得
    api_balance_count: int = 0
    fallback_count: int = 0

    # ポジション復元
    position_restore_count: int = 0

    # 取引阻害エラー
    nonetype_error_count: int = 0
    api_error_count: int = 0

    # スコア
    normal_checks: int = 0
    warning_issues: int = 0
    critical_issues: int = 0
    total_score: int = 0


class InfrastructureChecker:
    """インフラ基盤診断クラス"""

    def __init__(self, logger):
        self.logger = logger
        self.result = InfrastructureCheckResult()
        self.deploy_time = self._get_deploy_time()

    def _get_deploy_time(self) -> str:
        """最新CI時刻またはフォールバック時刻を取得"""
        try:
            result = subprocess.run(
                [
                    "gh",
                    "run",
                    "list",
                    "--limit=1",
                    "--workflow=CI/CD Pipeline",
                    "--status=success",
                    "--json=createdAt",
                    "--jq=.[0].createdAt",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass

        # フォールバック: 過去24時間
        from datetime import timezone

        utc_time = datetime.now(timezone.utc) - timedelta(days=1)
        return utc_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    def _count_gcp_logs(self, query: str, limit: int = 50) -> int:
        """GCPログをカウント"""
        if not self.deploy_time:
            return 0

        try:
            full_query = (
                f'resource.type="cloud_run_revision" AND '
                f'resource.labels.service_name="crypto-bot-service-prod" AND '
                f"({query}) AND "
                f'timestamp>="{self.deploy_time}"'
            )
            result = subprocess.run(
                [
                    "gcloud",
                    "logging",
                    "read",
                    full_query,
                    f"--limit={limit}",
                    "--format=value(textPayload)",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                lines = [line for line in result.stdout.strip().split("\n") if line]
                return len(lines)
        except Exception:
            pass
        return 0

    def _fetch_gcp_logs(self, query: str, limit: int = 5) -> List[str]:
        """GCPログを取得"""
        if not self.deploy_time:
            return []

        try:
            full_query = (
                f'resource.type="cloud_run_revision" AND '
                f'resource.labels.service_name="crypto-bot-service-prod" AND '
                f"({query}) AND "
                f'timestamp>="{self.deploy_time}"'
            )
            result = subprocess.run(
                [
                    "gcloud",
                    "logging",
                    "read",
                    full_query,
                    f"--limit={limit}",
                    "--format=value(timestamp.date(tz='Asia/Tokyo'),textPayload)",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                return [line for line in result.stdout.strip().split("\n") if line]
        except Exception:
            pass
        return []

    def check(self) -> InfrastructureCheckResult:
        """インフラ基盤診断実行"""
        self.logger.info("🚀 インフラ基盤診断開始")

        self._check_cloud_run()
        self._check_secret_manager()
        self._check_container_stability()
        self._check_discord()
        self._check_api_balance()
        self._check_position_restore()
        self._check_trade_blocking_errors()

        # 総合スコア計算
        self.result.total_score = (
            self.result.normal_checks * 10
            - self.result.warning_issues * 3
            - self.result.critical_issues * 20
        )

        self.logger.info(
            f"📊 インフラ診断完了 - 正常:{self.result.normal_checks} "
            f"警告:{self.result.warning_issues} 致命的:{self.result.critical_issues}"
        )
        return self.result

    def _check_cloud_run(self):
        """Cloud Runサービス稼働確認"""
        self.logger.info("🔧 Cloud Run サービス稼働確認")
        try:
            result = subprocess.run(
                [
                    "gcloud",
                    "run",
                    "services",
                    "describe",
                    "crypto-bot-service-prod",
                    "--region=asia-northeast1",
                    "--format=value(status.conditions[0].status)",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.result.cloud_run_status = (
                result.stdout.strip() if result.returncode == 0 else "Unknown"
            )
            if self.result.cloud_run_status == "True":
                self.result.normal_checks += 1
            else:
                self.result.critical_issues += 2
        except Exception as e:
            self.logger.warning(f"Cloud Run確認失敗: {e}")
            self.result.cloud_run_status = "Error"

    def _check_secret_manager(self):
        """Secret Manager権限確認"""
        self.logger.info("🔐 Secret Manager 権限確認")
        try:
            # サービスアカウント取得
            result = subprocess.run(
                [
                    "gcloud",
                    "run",
                    "services",
                    "describe",
                    "crypto-bot-service-prod",
                    "--region=asia-northeast1",
                    "--format=value(spec.template.spec.serviceAccountName)",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.result.service_account = result.stdout.strip() if result.returncode == 0 else ""

            if self.result.service_account:
                # 各シークレットの権限確認
                for secret, attr in [
                    ("bitbank-api-key", "bitbank_key_ok"),
                    ("bitbank-api-secret", "bitbank_secret_ok"),
                    ("discord-webhook-url", "discord_ok"),
                ]:
                    check = subprocess.run(
                        [
                            "gcloud",
                            "secrets",
                            "get-iam-policy",
                            secret,
                            "--format=value(bindings[].members)",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    if check.returncode == 0 and self.result.service_account in check.stdout:
                        setattr(self.result, attr, True)

                if (
                    self.result.bitbank_key_ok
                    and self.result.bitbank_secret_ok
                    and self.result.discord_ok
                ):
                    self.result.normal_checks += 1
                else:
                    self.result.critical_issues += 2
        except Exception as e:
            self.logger.warning(f"Secret Manager確認失敗: {e}")

    def _check_container_stability(self):
        """Container安定性確認"""
        self.logger.info("🔥 Container 安定性確認")
        self.result.container_exit_count = self._count_gcp_logs(
            'textPayload:"Container called exit(1)"', 20
        )
        self.result.runtime_warning_count = self._count_gcp_logs(
            'textPayload:"RuntimeWarning" AND textPayload:"never awaited"', 20
        )

        if self.result.container_exit_count < 5 and self.result.runtime_warning_count == 0:
            self.result.normal_checks += 1
        elif self.result.container_exit_count < 10 and self.result.runtime_warning_count < 5:
            self.result.warning_issues += 1
        else:
            self.result.critical_issues += 1

    def _check_discord(self):
        """Discord通知確認"""
        self.logger.info("📨 Discord 通知確認")
        self.result.discord_error_count = self._count_gcp_logs(
            'textPayload:"code: 50027" OR textPayload:"Invalid Webhook Token"', 5
        )
        if self.result.discord_error_count == 0:
            self.result.normal_checks += 1
        else:
            self.result.critical_issues += 1

    def _check_api_balance(self):
        """API残高取得確認"""
        self.logger.info("💰 API 残高取得確認")
        self.result.api_balance_count = self._count_gcp_logs('textPayload:"残高"', 15)
        self.result.fallback_count = self._count_gcp_logs('textPayload:"フォールバック"', 15)

        if self.result.api_balance_count > 0 and self.result.fallback_count < 3:
            self.result.normal_checks += 1
        elif self.result.fallback_count > 5:
            self.result.warning_issues += 1
        else:
            self.result.warning_issues += 1

    def _check_position_restore(self):
        """ポジション復元確認"""
        self.logger.info("📊 ポジション復元確認")
        self.result.position_restore_count = self._count_gcp_logs(
            'textPayload:"ポジション復元" OR textPayload:"Position restored"', 10
        )
        if self.result.position_restore_count > 0:
            self.result.normal_checks += 1

    def _check_trade_blocking_errors(self):
        """取引阻害エラー検出"""
        self.logger.info("🛡️ 取引阻害エラー検出")
        self.result.nonetype_error_count = self._count_gcp_logs('textPayload:"NoneType"', 20)
        self.result.api_error_count = self._count_gcp_logs(
            'textPayload:"bitbank API エラー" OR textPayload:"API.*エラー.*20"', 20
        )

        if self.result.nonetype_error_count == 0 and self.result.api_error_count < 3:
            self.result.normal_checks += 1
        elif self.result.nonetype_error_count < 5 and self.result.api_error_count < 10:
            self.result.warning_issues += 1
        else:
            self.result.critical_issues += 1


# =============================================================================
# Bot機能診断（check_bot_functions.sh 移植）
# =============================================================================


@dataclass
class BotFunctionCheckResult:
    """Bot機能診断結果"""

    # 55特徴量システム
    feature_55_count: int = 0
    feature_49_count: int = 0
    dummy_model_count: int = 0

    # Silent Failure
    signal_count: int = 0
    order_count: int = 0
    success_rate: int = 0

    # 6戦略動作
    strategy_counts: Dict[str, int] = field(default_factory=dict)
    active_strategy_count: int = 0

    # ML予測
    ml_prediction_count: int = 0

    # レジーム別TP/SL
    regime_count: int = 0
    tight_range_count: int = 0
    normal_range_count: int = 0
    trending_count: int = 0

    # Kelly基準
    kelly_count: int = 0

    # Atomic Entry Pattern
    atomic_success_count: int = 0
    atomic_rollback_count: int = 0

    # Phase 62.9-62.10: Maker戦略
    entry_maker_success_count: int = 0
    entry_maker_fallback_count: int = 0
    entry_post_only_cancelled_count: int = 0
    tp_maker_success_count: int = 0
    tp_maker_fallback_count: int = 0
    tp_post_only_cancelled_count: int = 0

    # Phase 62.13: ATRフォールバック検知
    atr_success_count: int = 0  # ATR取得成功数
    atr_fallback_count: int = 0  # フォールバックATR使用数

    # Phase 65/65.2: 設定検証
    config_checks: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    config_check_passed: int = 0
    config_check_failed: int = 0

    # Phase 65.2: GCPログベース動作確認
    phase65_2_log_count: int = 0
    partial_cancel_count: int = 0
    fixed_tp_recovery_count: int = 0
    unified_tp_placement_count: int = 0
    coverage_deficit_count: int = 0

    # スコア
    normal_checks: int = 0
    warning_issues: int = 0
    critical_issues: int = 0
    total_score: int = 0


class BotFunctionChecker:
    """Bot機能診断クラス"""

    STRATEGIES = [
        "ATRBased",
        "BBReversal",
        "StochasticReversal",
        "DonchianChannel",
        "ADXTrendStrength",
        "MACDEMACrossover",
    ]

    def __init__(self, logger, infra_checker: InfrastructureChecker):
        self.logger = logger
        self.infra_checker = infra_checker
        self.result = BotFunctionCheckResult()

    def check(self) -> BotFunctionCheckResult:
        """Bot機能診断実行"""
        self.logger.info("🤖 Bot機能診断開始")

        self._check_feature_system()
        self._detect_silent_failure()
        self._check_strategy_activation()
        self._check_ml_prediction()
        self._check_regime_tp_sl()
        self._check_kelly_criterion()
        self._check_atomic_entry()
        self._check_maker_strategy()  # Phase 62.9-62.10
        self._check_atr_fallback()  # Phase 62.13
        self._verify_phase65_config()  # Phase 65/65.2: 設定検証
        self._check_phase65_2_logs()  # Phase 65.2: GCPログ動作確認

        # 総合スコア計算
        self.result.total_score = (
            self.result.normal_checks * 10
            - self.result.warning_issues * 3
            - self.result.critical_issues * 20
        )

        self.logger.info(
            f"📊 Bot機能診断完了 - 正常:{self.result.normal_checks} "
            f"警告:{self.result.warning_issues} 致命的:{self.result.critical_issues}"
        )
        return self.result

    def _count_logs(self, query: str, limit: int = 50) -> int:
        """GCPログをカウント（InfrastructureCheckerのメソッドを再利用）"""
        return self.infra_checker._count_gcp_logs(query, limit)

    def _check_feature_system(self):
        """55特徴量システム確認"""
        self.logger.info("📊 55特徴量システム確認")
        self.result.feature_55_count = self._count_logs(
            'textPayload:"55特徴量" OR textPayload:"55個の特徴量"', 15
        )
        self.result.feature_49_count = self._count_logs(
            'textPayload:"49特徴量" OR textPayload:"基本特徴量のみ"', 15
        )
        self.result.dummy_model_count = self._count_logs('textPayload:"DummyModel"', 15)

        if self.result.feature_55_count > 0 and self.result.dummy_model_count == 0:
            self.result.normal_checks += 1
        elif self.result.feature_49_count > 0 and self.result.dummy_model_count == 0:
            self.result.warning_issues += 1
        elif self.result.dummy_model_count > 0:
            self.result.critical_issues += 2

    def _detect_silent_failure(self):
        """Silent Failure検出"""
        self.logger.info("🔍 Silent Failure 検出")
        self.result.signal_count = self._count_logs(
            'textPayload:"統合シグナル生成: buy" OR textPayload:"統合シグナル生成: sell"',
            30,
        )
        self.result.order_count = self._count_logs(
            'textPayload:"注文実行" OR textPayload:"order_executed" OR textPayload:"create_order"',
            30,
        )

        if self.result.signal_count == 0:
            self.result.warning_issues += 1
        elif self.result.signal_count > 0 and self.result.order_count == 0:
            # 完全Silent Failure
            self.result.critical_issues += 3
        else:
            self.result.success_rate = int(
                (self.result.order_count / self.result.signal_count) * 100
            )
            if self.result.success_rate >= 40:
                self.result.normal_checks += 1
            elif self.result.success_rate >= 20:
                self.result.warning_issues += 1
            else:
                self.result.critical_issues += 1

    def _check_strategy_activation(self):
        """6戦略動作確認"""
        self.logger.info("🎯 6戦略動作確認")
        for strategy in self.STRATEGIES:
            count = self._count_logs(f'textPayload:"{strategy}"', 10)
            self.result.strategy_counts[strategy] = count
            if count > 0:
                self.result.active_strategy_count += 1

        if self.result.active_strategy_count == 6:
            self.result.normal_checks += 1
        elif self.result.active_strategy_count >= 4:
            self.result.warning_issues += 1
        else:
            self.result.critical_issues += 1

    def _check_ml_prediction(self):
        """ML予測確認"""
        self.logger.info("🤖 ML予測システム確認")
        self.result.ml_prediction_count = self._count_logs(
            'textPayload:"ProductionEnsemble" OR textPayload:"ML予測" OR textPayload:"アンサンブル予測"',
            20,
        )

        if self.result.ml_prediction_count > 0:
            self.result.normal_checks += 1
        else:
            self.result.critical_issues += 1

    def _check_regime_tp_sl(self):
        """レジーム別TP/SL確認"""
        self.logger.info("📈 レジーム別TP/SL確認")
        self.result.regime_count = self._count_logs(
            'textPayload:"市場状況:" OR textPayload:"RegimeType" OR textPayload:"レジーム"',
            10,
        )
        self.result.tight_range_count = self._count_logs(
            'textPayload:"TIGHT_RANGE" OR textPayload:"tight_range"', 10
        )
        self.result.normal_range_count = self._count_logs(
            'textPayload:"NORMAL_RANGE" OR textPayload:"normal_range"', 10
        )
        self.result.trending_count = self._count_logs(
            'textPayload:"TRENDING" OR textPayload:"trending"', 10
        )

        total = (
            self.result.tight_range_count
            + self.result.normal_range_count
            + self.result.trending_count
        )
        if total > 0:
            self.result.normal_checks += 1

    def _check_kelly_criterion(self):
        """Kelly基準確認"""
        self.logger.info("💱 Kelly基準確認")
        self.result.kelly_count = self._count_logs(
            'textPayload:"Kelly計算" OR textPayload:"Kelly履歴"', 15
        )
        if self.result.kelly_count > 0:
            self.result.normal_checks += 1

    def _check_atomic_entry(self):
        """Atomic Entry Pattern確認"""
        self.logger.info("🎯 Atomic Entry Pattern確認")
        self.result.atomic_success_count = self._count_logs('textPayload:"Atomic Entry完了"', 10)
        self.result.atomic_rollback_count = self._count_logs(
            'textPayload:"ロールバック実行" OR textPayload:"Atomic Entry rollback"', 10
        )

        if self.result.atomic_success_count > 0 and self.result.atomic_rollback_count <= 2:
            self.result.normal_checks += 1
        elif self.result.atomic_rollback_count > 5:
            self.result.critical_issues += 1

    def _check_maker_strategy(self):
        """Phase 62.9-62.10: Maker戦略確認"""
        self.logger.info("💰 Phase 62.9-62.10: Maker戦略確認")

        # Phase 62.9: エントリーMaker戦略
        self.result.entry_maker_success_count = self._count_logs(
            'textPayload:"Phase 62.9: Maker注文配置成功"', 20
        )
        self.result.entry_maker_fallback_count = self._count_logs(
            'textPayload:"Phase 62.9: Maker失敗" OR textPayload:"Phase 62.9: Takerフォールバック"',
            20,
        )
        self.result.entry_post_only_cancelled_count = self._count_logs(
            'textPayload:"Phase 62.9: post_onlyキャンセル"', 20
        )

        # Phase 62.10: TP Maker戦略
        self.result.tp_maker_success_count = self._count_logs(
            'textPayload:"Phase 62.10: TP Maker配置成功"', 20
        )
        self.result.tp_maker_fallback_count = self._count_logs(
            'textPayload:"Phase 62.10: TP Maker失敗" OR textPayload:"take_profitフォールバック"',
            20,
        )
        self.result.tp_post_only_cancelled_count = self._count_logs(
            'textPayload:"Phase 62.10: TP post_onlyキャンセル"', 20
        )

        # 評価: Maker戦略が動作していれば正常
        total_entry = self.result.entry_maker_success_count + self.result.entry_maker_fallback_count
        total_tp = self.result.tp_maker_success_count + self.result.tp_maker_fallback_count

        if total_entry > 0 or total_tp > 0:
            # Maker戦略が動作中
            entry_success_rate = (
                self.result.entry_maker_success_count / total_entry * 100 if total_entry > 0 else 0
            )
            tp_success_rate = (
                self.result.tp_maker_success_count / total_tp * 100 if total_tp > 0 else 0
            )

            self.logger.info(
                f"📊 Maker戦略統計 - エントリー: {self.result.entry_maker_success_count}成功/"
                f"{self.result.entry_maker_fallback_count}FB ({entry_success_rate:.0f}%), "
                f"TP: {self.result.tp_maker_success_count}成功/"
                f"{self.result.tp_maker_fallback_count}FB ({tp_success_rate:.0f}%)"
            )

            # 成功率80%以上なら正常
            if entry_success_rate >= 80 or tp_success_rate >= 80:
                self.result.normal_checks += 1
            elif entry_success_rate >= 50 or tp_success_rate >= 50:
                # 50%以上なら警告のみ
                pass
            else:
                # 50%未満なら警告
                self.result.warning_issues += 1
        else:
            # Maker戦略の動作記録なし（まだ取引がない可能性）
            self.logger.info("ℹ️ Maker戦略: 動作記録なし（取引なし or 未有効化）")

    def _check_atr_fallback(self):
        """Phase 62.13: ATRフォールバック検知"""
        self.logger.info("📊 Phase 62.13: ATRフォールバック検知")

        # ATR取得成功数（Phase 62.13の新ログ）
        self.result.atr_success_count = self._count_logs(
            'textPayload:"Phase 62.13: ATR取得成功"', 20
        )

        # フォールバックATR使用数（既存のログ）
        self.result.atr_fallback_count = self._count_logs(
            'textPayload:"Phase 51.5-C: フォールバックATR使用"', 20
        )

        total = self.result.atr_success_count + self.result.atr_fallback_count
        if total > 0:
            success_rate = self.result.atr_success_count / total * 100
            self.logger.info(
                f"📊 ATR取得統計 - 成功: {self.result.atr_success_count}回, "
                f"フォールバック: {self.result.atr_fallback_count}回 ({success_rate:.0f}%成功)"
            )

            # 100%成功なら正常
            if success_rate == 100:
                self.result.normal_checks += 1
            # 80%以上なら警告
            elif success_rate >= 80:
                self.result.warning_issues += 1
            # 80%未満なら致命的
            else:
                self.result.critical_issues += 1
                self.logger.warning(f"⚠️ ATRフォールバック多発: {self.result.atr_fallback_count}回")
        else:
            # 記録なし（まだTP/SL再計算が発生していない）
            self.logger.info("ℹ️ ATR取得: 記録なし（TP/SL再計算未発生）")

    def _verify_phase65_config(self):
        """Phase 65/65.2: 設定値検証"""
        self.logger.info("🔧 Phase 65/65.2: 設定値検証")
        from src.core.config.threshold_manager import get_threshold

        checks = {
            "min_strategy_confidence": {
                "path": "ml.strategy_integration.min_strategy_confidence",
                "expected": 0.22,
                "default": 0.25,
            },
            "BBReversal tight_range重み": {
                "path": "dynamic_strategy_selection.regime_strategy_mapping.tight_range.BBReversal",
                "expected": 0.15,
                "default": 0.0,
            },
            "Maker max_retries": {
                "path": "order_execution.maker_strategy.max_retries",
                "expected": 5,
                "default": 3,
            },
            "Maker retry_interval_ms": {
                "path": "order_execution.maker_strategy.retry_interval_ms",
                "expected": 200,
                "default": 500,
            },
            "固定金額TP有効": {
                "path": "position_management.take_profit.fixed_amount.enabled",
                "expected": True,
                "default": False,
            },
            "固定金額TP目標": {
                "path": "position_management.take_profit.fixed_amount.target_net_profit",
                "expected": 500,
                "default": 1000,
            },
        }

        for name, spec in checks.items():
            actual = get_threshold(spec["path"], spec["default"])
            ok = actual == spec["expected"]
            self.result.config_checks[name] = {
                "path": spec["path"],
                "expected": spec["expected"],
                "actual": actual,
                "ok": ok,
            }
            if ok:
                self.result.config_check_passed += 1
            else:
                self.result.config_check_failed += 1
                self.logger.warning(f"❌ {name}: 期待={spec['expected']} 実際={actual}")

        # スコア反映
        if self.result.config_check_failed == 0:
            self.result.normal_checks += 1
        elif self.result.config_check_failed <= 2:
            self.result.warning_issues += 1
        else:
            self.result.critical_issues += 1

    def _check_phase65_2_logs(self):
        """Phase 65.2: GCPログベース動作確認"""
        self.logger.info("📋 Phase 65.2: TP/SLフルカバー動作確認")

        self.result.phase65_2_log_count = self._count_logs('textPayload:"Phase 65.2:"', 50)
        self.result.partial_cancel_count = self._count_logs(
            'textPayload:"Phase 65.2: 部分TP/SL" AND textPayload:"キャンセル"', 20
        )
        self.result.fixed_tp_recovery_count = self._count_logs(
            'textPayload:"Phase 65.2: 固定金額TP使用"', 20
        )
        self.result.unified_tp_placement_count = self._count_logs(
            'textPayload:"Phase 65.2: 統合TP配置成功"', 20
        )
        self.result.coverage_deficit_count = self._count_logs(
            'textPayload:"Phase 65.2: TP/SLカバレッジ不足検出"', 20
        )

        if self.result.phase65_2_log_count > 0:
            self.logger.info(
                f"📋 Phase 65.2ログ検出: {self.result.phase65_2_log_count}件 "
                f"(部分キャンセル:{self.result.partial_cancel_count} "
                f"固定TP復旧:{self.result.fixed_tp_recovery_count} "
                f"統合TP:{self.result.unified_tp_placement_count})"
            )
        else:
            self.logger.info("ℹ️ Phase 65.2: ログ未検出（TP/SL復旧未発生の可能性）")


@dataclass
class LiveAnalysisResult:
    """ライブモード分析結果（35指標）"""

    # メタ情報
    timestamp: str = ""
    analysis_period_hours: int = 24

    # アカウント状態（5指標）
    margin_ratio: float = 0.0
    available_balance: float = 0.0
    used_margin: float = 0.0
    unrealized_pnl: float = 0.0
    margin_call_status: str = ""

    # ポジション状態（5指標）
    open_position_count: int = 0
    position_details: List[Dict[str, Any]] = field(default_factory=list)
    pending_order_count: int = 0
    order_breakdown: Dict[str, int] = field(default_factory=dict)
    losscut_price: Optional[float] = None

    # 取引履歴分析（12指標）
    trades_count: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    avg_pnl: float = 0.0
    max_profit: float = 0.0
    max_loss: float = 0.0
    strategy_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    tp_triggered_count: int = 0
    sl_triggered_count: int = 0

    # システム健全性（6指標）
    api_response_time_ms: float = 0.0
    recent_error_count: int = 0
    last_trade_time: Optional[str] = None
    service_status: str = ""
    last_deploy_time: Optional[str] = None
    container_restart_count: int = 0

    # TP/SL適切性（4指標）
    tp_distance_pct: Optional[float] = None
    sl_distance_pct: Optional[float] = None
    tp_sl_placement_ok: bool = True
    tp_sl_config_deviation: Optional[float] = None

    # Phase 65.2: TP/SLカバレッジ率
    tp_coverage_ratio: Optional[float] = None
    sl_coverage_ratio: Optional[float] = None
    tp_sl_full_coverage: bool = True

    # Phase 58.8: 孤児注文検出（2指標）
    orphan_sl_detected: bool = False
    orphan_order_count: int = 0

    # 稼働率（5指標）
    uptime_rate: float = 0.0
    total_downtime_minutes: float = 0.0
    last_incident_time: Optional[str] = None
    actual_cycle_count: int = 0
    expected_cycle_count: int = 0

    # MLモデル状態（4指標）- Phase 59.8追加
    ml_model_type: str = ""  # ProductionEnsemble / DummyModel
    ml_model_level: int = -1  # 1=Full, 2=Basic, 3=Dummy
    ml_feature_count: int = 0  # 55 / 49 / 0

    # Phase 62.16: スリッページ分析（6指標）
    slippage_avg: float = 0.0  # 平均スリッページ（円）
    slippage_max: float = 0.0  # 最大スリッページ（円）
    slippage_min: float = 0.0  # 最小スリッページ（円）
    slippage_count: int = 0  # スリッページ記録数
    slippage_entry_avg: float = 0.0  # エントリー時平均スリッページ
    slippage_exit_avg: float = 0.0  # 決済時平均スリッページ

    # Phase 62.18: SLパターン分析（GCPログベース）
    sl_pattern_total_executions: int = 0
    sl_pattern_tp_count: int = 0
    sl_pattern_sl_count: int = 0
    sl_pattern_sl_pnl_total: float = 0.0
    sl_pattern_sl_pnl_avg: float = 0.0
    sl_pattern_tp_pnl_total: float = 0.0
    sl_pattern_tp_pnl_avg: float = 0.0
    sl_pattern_strategy_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    sl_pattern_hourly_stats: Dict[int, int] = field(default_factory=dict)
    sl_pattern_weekday_stats: Dict[str, int] = field(default_factory=dict)


class LiveAnalyzer:
    """ライブモード標準分析"""

    STRATEGIES = [
        "ATRBased",
        "BBReversal",
        "DonchianChannel",
        "StochasticReversal",
        "ADXTrendStrength",
        "MACDEMACrossover",
    ]

    def __init__(self, period_hours: int = 24):
        self.period_hours = period_hours
        self.logger = get_logger()
        self.result = LiveAnalysisResult(analysis_period_hours=period_hours)
        self.bitbank_client: Optional[BitbankClient] = None
        self.current_price: float = 0.0
        # Phase 59.5: 注文フェッチ一元化（タイミング差による不整合防止）
        self._cached_active_orders: List[Dict[str, Any]] = []

    async def analyze(self) -> LiveAnalysisResult:
        """分析実行"""
        self.result.timestamp = datetime.now().isoformat()
        self.logger.info(f"ライブモード分析開始 - 対象期間: {self.period_hours}時間")

        # .env読み込み確認
        if env_path.exists():
            api_key = os.getenv("BITBANK_API_KEY", "")
            if api_key and len(api_key) > 8:
                self.logger.info(f"✅ .envからAPIキー読み込み成功: {api_key[:8]}...")
            else:
                self.logger.warning("⚠️ .envファイル存在するがAPIキーが空")

        try:
            # bitbankクライアント初期化
            self.bitbank_client = BitbankClient()

            # 現在価格取得
            await self._fetch_current_price()

            # 各分析実行
            await self._fetch_account_status()
            await self._fetch_position_status()
            await self._fetch_trade_history()
            await self._check_system_health()
            await self._check_tp_sl_placement()
            await self._calculate_uptime()
            await self._check_ml_model_status()
            # Phase 62.18: SLパターン分析
            await self._analyze_sl_patterns()

        except Exception as e:
            self.logger.error(f"分析中にエラー発生: {e}")
            raise

        self.logger.info("ライブモード分析完了")
        return self.result

    def _count_logs(self, query: str, limit: int = 50) -> int:
        """GCPログをカウント（Phase 61.11追加）"""
        try:
            # デプロイ時刻を取得
            from datetime import timezone

            utc_now = datetime.now(timezone.utc)
            since_time = (utc_now - timedelta(hours=self.period_hours)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

            full_query = (
                f'resource.type="cloud_run_revision" AND '
                f'resource.labels.service_name="crypto-bot-service-prod" AND '
                f"({query}) AND "
                f'timestamp>="{since_time}"'
            )
            result = subprocess.run(
                [
                    "gcloud",
                    "logging",
                    "read",
                    full_query,
                    f"--limit={limit}",
                    "--format=value(textPayload)",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                lines = [line for line in result.stdout.strip().split("\n") if line]
                return len(lines)
        except FileNotFoundError:
            # ローカル実行時（gcloudコマンドなし）
            self.logger.debug("GCPログカウントスキップ（ローカル実行）")
        except Exception as e:
            self.logger.debug(f"GCPログカウント失敗: {e}")
        return 0

    async def _fetch_current_price(self):
        """現在価格取得"""
        try:
            ticker = self.bitbank_client.fetch_ticker("BTC/JPY")
            self.current_price = ticker.get("last", 0)
            self.logger.info(f"現在価格: ¥{self.current_price:,.0f}")
        except Exception as e:
            self.logger.warning(f"価格取得失敗: {e}")
            self.current_price = 0

    async def _fetch_account_status(self):
        """アカウント状態取得（5指標）"""
        try:
            start_time = time.time()
            margin_status = await self.bitbank_client.fetch_margin_status()
            self.result.api_response_time_ms = (time.time() - start_time) * 1000

            self.result.margin_ratio = margin_status.get("margin_ratio", 0.0)
            self.result.available_balance = margin_status.get("available_balance", 0.0)
            self.result.used_margin = margin_status.get("used_margin", 0.0)
            self.result.unrealized_pnl = margin_status.get("unrealized_pnl", 0.0)
            self.result.margin_call_status = margin_status.get("margin_call_status", "unknown")

            self.logger.info(f"アカウント状態取得完了 - 維持率: {self.result.margin_ratio:.1f}%")
        except Exception as e:
            self.logger.error(f"アカウント状態取得失敗: {e}")
            self.result.margin_call_status = "error"

    async def _fetch_position_status(self):
        """ポジション状態取得（5指標）"""
        try:
            # ポジション取得（Phase 58.4: fetch_margin_positions使用）
            positions = await self.bitbank_client.fetch_margin_positions("BTC/JPY")

            # Phase 58.8: 有効ポジションのみフィルタ（BTC/JPY + Amount > 0）
            # bitbank APIは全通貨ペアのスロットを返却するため、フィルタ必須
            active_positions = [
                p
                for p in positions
                if p.get("amount", 0) > 0
                and p.get("symbol", "").lower().replace("/", "_") == "btc_jpy"
            ]
            self.result.open_position_count = len(active_positions)

            # ポジション詳細（有効ポジションのみ）
            self.result.position_details = []
            for pos in active_positions:
                detail = {
                    "side": pos.get("side", "unknown"),
                    "amount": pos.get("amount", 0),
                    "avg_price": pos.get("average_price", 0),
                    "unrealized_pnl": pos.get("unrealized_pnl", 0),
                }
                self.result.position_details.append(detail)

                # ロスカット価格
                if pos.get("losscut_price"):
                    self.result.losscut_price = pos.get("losscut_price")

            # アクティブ注文取得（Phase 59.5: キャッシュに保存）
            active_orders = self.bitbank_client.fetch_active_orders("BTC/JPY")
            self._cached_active_orders = active_orders  # 他メソッドで再利用
            self.result.pending_order_count = len(active_orders)

            # 注文内訳
            breakdown = {"limit": 0, "stop": 0, "stop_limit": 0}
            for order in active_orders:
                order_type = order.get("type", "limit")
                if order_type in breakdown:
                    breakdown[order_type] += 1
                else:
                    breakdown["limit"] += 1
            self.result.order_breakdown = breakdown

            # Phase 58.8: 孤児SL/TP検出
            # ポジションがないのにstop/stop_limit注文がある場合は孤児
            sl_tp_count = breakdown.get("stop", 0) + breakdown.get("stop_limit", 0)
            if self.result.open_position_count == 0 and sl_tp_count > 0:
                self.result.orphan_sl_detected = True
                self.result.orphan_order_count = sl_tp_count
                self.logger.warning(
                    f"⚠️ Phase 58.8: 孤児SL/TP注文検出 - {sl_tp_count}件 "
                    "(ポジションなしでSL/TP注文が残存)"
                )

            self.logger.info(
                f"ポジション状態取得完了 - ポジション: {self.result.open_position_count}件, "
                f"未約定注文: {self.result.pending_order_count}件"
            )
        except Exception as e:
            self.logger.error(f"ポジション状態取得失敗: {e}")

    async def _fetch_trade_history(self):
        """取引履歴分析（12指標）"""
        try:
            # SQLiteから取引履歴取得
            db_path = Path("tax/trade_history.db")
            if not db_path.exists():
                self.logger.warning("取引履歴DBが存在しません")
                return

            import sqlite3

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 対象期間の開始時刻
            start_time = (datetime.now() - timedelta(hours=self.period_hours)).isoformat()

            cursor.execute(
                """
                SELECT * FROM trades
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
            """,
                (start_time,),
            )
            all_rows = [dict(row) for row in cursor.fetchall()]
            conn.close()

            # Phase 65.15: Paper tradeを除外 + order_id重複排除
            # Paper tradeはライブ分析の対象外
            live_rows = [r for r in all_rows if "Paper trade" not in (r.get("notes") or "")]
            # 同一order_idの重複レコードを排除（最新のみ残す）
            seen_order_ids = set()
            trades = []
            for r in live_rows:
                oid = r.get("order_id")
                if oid and oid in seen_order_ids:
                    continue
                if oid:
                    seen_order_ids.add(oid)
                trades.append(r)

            self.result.trades_count = len(trades)
            if len(all_rows) != len(trades):
                self.logger.info(
                    f"📊 Phase 65.15: DB {len(all_rows)}件 → "
                    f"Paper除外・重複排除後 {len(trades)}件"
                )

            # Phase 61.11: GCPログからTP/SL発動数を取得（DBにexit記録がないため）
            # Phase 61.9の自動執行検知ログを使用
            tp_from_logs = self._count_logs('textPayload:"TP自動執行検知"', 50)
            sl_from_logs = self._count_logs('textPayload:"SL自動執行検知"', 50)
            self.result.tp_triggered_count = tp_from_logs
            self.result.sl_triggered_count = sl_from_logs

            if trades:
                # Phase 61.11: pnlがすべてNULLかどうか確認
                pnls_with_value = [t.get("pnl") for t in trades if t.get("pnl") is not None]
                has_pnl_data = len(pnls_with_value) > 0

                if has_pnl_data:
                    # pnlデータがある場合は従来のロジック
                    wins = [t for t in trades if (t.get("pnl") or 0) > 0]
                    self.result.win_rate = len(wins) / len(trades) * 100 if trades else 0.0

                    pnls = [t.get("pnl", 0) or 0 for t in trades]
                    self.result.total_pnl = sum(pnls)
                    self.result.avg_pnl = self.result.total_pnl / len(trades) if trades else 0.0

                    # 最大利益/損失
                    if pnls:
                        self.result.max_profit = max(pnls) if max(pnls) > 0 else 0
                        self.result.max_loss = min(pnls) if min(pnls) < 0 else 0

                    # 戦略別統計（notesフィールドから戦略名を抽出）
                    for strategy in self.STRATEGIES:
                        strategy_trades = [t for t in trades if strategy in (t.get("notes") or "")]
                        if strategy_trades:
                            s_pnls = [t.get("pnl", 0) or 0 for t in strategy_trades]
                            s_wins = [p for p in s_pnls if p > 0]
                            self.result.strategy_stats[strategy] = {
                                "trades": len(strategy_trades),
                                "win_rate": len(s_wins) / len(strategy_trades) * 100,
                                "pnl": sum(s_pnls),
                            }
                else:
                    # Phase 61.11: pnlがすべてNULLの場合はGCPログベースで推定
                    # TP発動=勝ち、SL発動=負けとして推定
                    total_exits = tp_from_logs + sl_from_logs
                    if total_exits > 0:
                        self.result.win_rate = (tp_from_logs / total_exits) * 100
                    else:
                        # 決済記録がない場合は勝率を-1（N/A表示用）に設定
                        self.result.win_rate = -1.0
                    self.result.total_pnl = 0.0
                    self.result.avg_pnl = 0.0
                    self.logger.info("pnlデータなし - GCPログからTP/SL発動数で勝率推定")

                # 最終取引時刻
                self.result.last_trade_time = trades[0].get("timestamp")

                # Phase 62.16: スリッページ分析
                self._analyze_slippage(trades)

            self.logger.info(
                f"取引履歴分析完了 - {self.result.trades_count}件, "
                f"勝率: {self.result.win_rate:.1f}%, 損益: ¥{self.result.total_pnl:,.0f}"
            )
        except Exception as e:
            self.logger.error(f"取引履歴分析失敗: {e}")

    def _analyze_slippage(self, trades: List[Dict[str, Any]]):
        """
        Phase 62.16: スリッページ分析

        Args:
            trades: 取引履歴リスト
        """
        # スリッページデータがある取引をフィルタ
        trades_with_slippage = [t for t in trades if t.get("slippage") is not None]

        if not trades_with_slippage:
            self.logger.info("ℹ️ スリッページデータなし（Phase 62.16以前の取引）")
            return

        self.result.slippage_count = len(trades_with_slippage)
        slippages = [t.get("slippage", 0) for t in trades_with_slippage]

        # 全体統計
        self.result.slippage_avg = sum(slippages) / len(slippages) if slippages else 0.0
        self.result.slippage_max = max(slippages) if slippages else 0.0
        self.result.slippage_min = min(slippages) if slippages else 0.0

        # エントリー/決済別統計
        entry_slippages = [
            t.get("slippage", 0) for t in trades_with_slippage if t.get("trade_type") == "entry"
        ]
        exit_slippages = [
            t.get("slippage", 0)
            for t in trades_with_slippage
            if t.get("trade_type") in ["tp", "sl", "exit"]
        ]

        if entry_slippages:
            self.result.slippage_entry_avg = sum(entry_slippages) / len(entry_slippages)
        if exit_slippages:
            self.result.slippage_exit_avg = sum(exit_slippages) / len(exit_slippages)

        self.logger.info(
            f"📊 Phase 62.16: スリッページ分析 - "
            f"件数: {self.result.slippage_count}, "
            f"平均: ¥{self.result.slippage_avg:.0f}, "
            f"最大: ¥{self.result.slippage_max:.0f}, "
            f"最小: ¥{self.result.slippage_min:.0f}"
        )

    async def _check_system_health(self):
        """システム健全性確認（6指標）"""
        # GCPログからエラー数・Container再起動を取得
        try:
            # サービス状態確認
            result = subprocess.run(
                [
                    "gcloud",
                    "run",
                    "services",
                    "describe",
                    "crypto-bot-service-prod",
                    "--region=asia-northeast1",
                    "--format=json",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                service_info = json.loads(result.stdout)
                conditions = service_info.get("status", {}).get("conditions", [])
                for cond in conditions:
                    if cond.get("type") == "Ready":
                        self.result.service_status = (
                            "Ready" if cond.get("status") == "True" else "NotReady"
                        )
                        break

                # Phase 63.3: Bug 6修正 - 最新リビジョンのタイムスタンプを取得
                # 旧: service metadata.creationTimestamp（サービス作成日）を使用していた
                latest_revision = service_info.get("status", {}).get("latestReadyRevisionName", "")
                if latest_revision:
                    try:
                        rev_result = subprocess.run(
                            [
                                "gcloud",
                                "run",
                                "revisions",
                                "describe",
                                latest_revision,
                                "--region=asia-northeast1",
                                "--format=json",
                            ],
                            capture_output=True,
                            text=True,
                            timeout=30,
                        )
                        if rev_result.returncode == 0:
                            rev_info = json.loads(rev_result.stdout)
                            self.result.last_deploy_time = rev_info.get("metadata", {}).get(
                                "creationTimestamp", ""
                            )
                        else:
                            # フォールバック: サービス作成日
                            self.result.last_deploy_time = service_info.get("metadata", {}).get(
                                "creationTimestamp", ""
                            )
                    except Exception:
                        self.result.last_deploy_time = service_info.get("metadata", {}).get(
                            "creationTimestamp", ""
                        )
            else:
                self.result.service_status = "unknown"
                self.logger.warning("GCPサービス状態取得失敗（gcloud未設定?）")

        except subprocess.TimeoutExpired:
            self.logger.warning("GCPサービス確認タイムアウト")
            self.result.service_status = "timeout"
        except FileNotFoundError:
            self.logger.warning("gcloud CLIが見つかりません（ローカル実行?）")
            self.result.service_status = "local"
        except Exception as e:
            self.logger.warning(f"GCPサービス確認失敗: {e}")
            self.result.service_status = "error"

        # エラーログ数取得
        try:
            since_time = (datetime.now() - timedelta(hours=self.period_hours)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            result = subprocess.run(
                [
                    "gcloud",
                    "logging",
                    "read",
                    f'resource.type="cloud_run_revision" AND severity>=ERROR AND timestamp>="{since_time}"',
                    "--format=json",
                    "--limit=100",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                errors = json.loads(result.stdout) if result.stdout.strip() else []
                self.result.recent_error_count = len(errors)
            else:
                self.result.recent_error_count = -1  # 取得失敗

        except Exception as e:
            self.logger.warning(f"エラーログ取得失敗: {e}")
            self.result.recent_error_count = -1

        # Container再起動回数
        try:
            result = subprocess.run(
                [
                    "gcloud",
                    "logging",
                    "read",
                    f'textPayload:"Container called exit" AND timestamp>="{since_time}"',
                    "--format=json",
                    "--limit=100",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                restarts = json.loads(result.stdout) if result.stdout.strip() else []
                self.result.container_restart_count = len(restarts)
        except Exception as e:
            self.logger.warning(f"Container再起動数取得失敗: {e}")

        self.logger.info(
            f"システム健全性確認完了 - 状態: {self.result.service_status}, "
            f"エラー: {self.result.recent_error_count}件"
        )

    async def _check_tp_sl_placement(self):
        """TP/SL設置適切性確認（4指標）- Phase 58.1改善版"""
        try:
            if self.current_price <= 0:
                return

            # Phase 59.5: キャッシュされた注文を使用（API呼び出し削減＆タイミング整合性確保）
            active_orders = self._cached_active_orders or []

            # Phase 61.8: take_profit/stop_lossタイプに対応（Phase 61.3で追加されたタイプ）
            tp_orders = [o for o in active_orders if o.get("type") in ["limit", "take_profit"]]
            sl_orders = [
                o for o in active_orders if o.get("type") in ["stop", "stop_limit", "stop_loss"]
            ]

            # TP距離計算
            # Phase 61.8: take_profit注文はtrigger_priceを使用
            if tp_orders and self.result.position_details:
                tp_order = tp_orders[0]
                tp_price = (
                    tp_order.get("price")
                    or tp_order.get("info", {}).get("trigger_price")
                    or tp_order.get("triggerPrice")
                    or 0
                )
                if tp_price:
                    tp_price = float(tp_price)
                    self.result.tp_distance_pct = (
                        abs(tp_price - self.current_price) / self.current_price * 100
                    )

            # SL距離計算
            # Phase 61.8: stop_loss注文はtrigger_priceを使用
            if sl_orders and self.result.position_details:
                sl_order = sl_orders[0]
                sl_price = (
                    sl_order.get("stopPrice")
                    or sl_order.get("info", {}).get("trigger_price")
                    or sl_order.get("triggerPrice")
                    or 0
                )
                if sl_price:
                    sl_price = float(sl_price)
                    self.result.sl_distance_pct = (
                        abs(sl_price - self.current_price) / self.current_price * 100
                    )

            # ポジションがあるのにTP/SLがない場合
            if self.result.open_position_count > 0:
                if not tp_orders or not sl_orders:
                    self.result.tp_sl_placement_ok = False
                    self.logger.warning("ポジションがあるがTP/SLが設定されていません")

            # Phase 58.1: ポジション量とTP/SL注文量の整合性チェック
            # Phase 61.8: take_profit/stop_loss注文はamountがNoneの場合があるため、注文存在のみチェック
            if self.result.position_details and self.result.open_position_count > 0:
                # ポジション総量を計算
                total_position_amount = sum(
                    abs(float(pos.get("amount", 0))) for pos in self.result.position_details
                )

                # TP注文総量（NoneやNoneTypeを0として処理）
                total_tp_amount = sum(
                    abs(float(o.get("amount") or o.get("remaining") or 0))
                    for o in tp_orders
                    if o.get("amount") is not None or o.get("remaining") is not None
                )

                # SL注文総量（NoneやNoneTypeを0として処理）
                total_sl_amount = sum(
                    abs(float(o.get("amount") or o.get("remaining") or 0))
                    for o in sl_orders
                    if o.get("amount") is not None or o.get("remaining") is not None
                )

                # Phase 61.8: take_profit/stop_loss注文はamountがないため、注文存在でOKとする
                # 注文量チェックはamountがある場合のみ実行
                tolerance = 0.001

                # TP量不足チェック（amountがある場合のみ）
                if total_position_amount > 0 and total_tp_amount > 0:
                    tp_coverage = total_tp_amount / total_position_amount
                    if tp_coverage < (1.0 - tolerance):
                        self.result.tp_sl_placement_ok = False
                        tp_pct = tp_coverage * 100
                        self.logger.warning(
                            f"⚠️ TP注文量不足: ポジション{total_position_amount:.4f}BTC vs "
                            f"TP注文{total_tp_amount:.4f}BTC (カバー率: {tp_pct:.1f}%)"
                        )

                # SL量不足チェック（amountがある場合のみ）
                if total_position_amount > 0 and total_sl_amount > 0:
                    sl_coverage = total_sl_amount / total_position_amount
                    if sl_coverage < (1.0 - tolerance):
                        self.result.tp_sl_placement_ok = False
                        sl_pct = sl_coverage * 100
                        self.logger.warning(
                            f"⚠️ SL注文量不足: ポジション{total_position_amount:.4f}BTC vs "
                            f"SL注文{total_sl_amount:.4f}BTC (カバー率: {sl_pct:.1f}%)"
                        )

                # Phase 65.2: カバレッジ率をresultに保存
                if total_position_amount > 0:
                    # TP coverage
                    if total_tp_amount > 0:
                        self.result.tp_coverage_ratio = total_tp_amount / total_position_amount
                    elif len(tp_orders) > 0:
                        self.result.tp_coverage_ratio = 1.0  # native注文はamount=None
                    else:
                        self.result.tp_coverage_ratio = 0.0

                    # SL coverage
                    if total_sl_amount > 0:
                        self.result.sl_coverage_ratio = total_sl_amount / total_position_amount
                    elif len(sl_orders) > 0:
                        self.result.sl_coverage_ratio = 1.0
                    else:
                        self.result.sl_coverage_ratio = 0.0

                    self.result.tp_sl_full_coverage = (
                        self.result.tp_coverage_ratio or 0
                    ) >= 0.95 and (self.result.sl_coverage_ratio or 0) >= 0.95

                # 注文数の記録（デバッグ用）
                self.logger.info(
                    f"TP/SL詳細 - ポジション: {total_position_amount:.4f}BTC, "
                    f"TP: {len(tp_orders)}件({total_tp_amount:.4f}BTC), "
                    f"SL: {len(sl_orders)}件({total_sl_amount:.4f}BTC)"
                )

            self.logger.info(
                f"TP/SL確認完了 - TP距離: {self.result.tp_distance_pct or 'N/A'}%, "
                f"SL距離: {self.result.sl_distance_pct or 'N/A'}%"
            )
        except Exception as e:
            self.logger.error(f"TP/SL確認失敗: {e}")

    async def _calculate_uptime(self):
        """稼働率計算（5指標）"""
        try:
            # Phase 59.5 Fix: UTC時刻を使用（GCPログはUTC保存）
            from datetime import timezone

            utc_now = datetime.now(timezone.utc)
            since_time = (utc_now - timedelta(hours=self.period_hours)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

            # 取引サイクル開始ログ数から稼働率を推定
            result = subprocess.run(
                [
                    "gcloud",
                    "logging",
                    "read",
                    f'resource.type="cloud_run_revision" AND textPayload:"取引サイクル開始" AND timestamp>="{since_time}"',
                    "--format=json",
                    "--limit=500",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                logs = json.loads(result.stdout) if result.stdout.strip() else []
                actual_runs = len(logs)

                # 期待される実行回数（7分間隔: 処理時間2分+待機5分）
                # Phase 60.2: 5分→7分に修正（実測値に基づく）
                runs_per_hour = 60 / 7  # 約8.57回/時間
                expected_runs = int(self.period_hours * runs_per_hour)

                # 結果を保存
                self.result.actual_cycle_count = actual_runs
                self.result.expected_cycle_count = expected_runs

                if expected_runs > 0:
                    self.result.uptime_rate = min(100.0, (actual_runs / expected_runs) * 100)
                    missed_runs = max(0, expected_runs - actual_runs)
                    self.result.total_downtime_minutes = missed_runs * 7  # 7分間隔

                self.logger.info(
                    f"稼働率計算完了 - {self.result.uptime_rate:.1f}% "
                    f"(実行{actual_runs}回/期待{expected_runs}回)"
                )

                # コンテナ再起動回数を取得
                restart_result = subprocess.run(
                    [
                        "gcloud",
                        "logging",
                        "read",
                        f'resource.type="cloud_run_revision" AND textPayload:"TradingOrchestrator依存性組み立て開始" AND timestamp>="{since_time}"',
                        "--format=json",
                        "--limit=50",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if restart_result.returncode == 0:
                    restart_logs = (
                        json.loads(restart_result.stdout) if restart_result.stdout.strip() else []
                    )
                    self.result.container_restart_count = len(restart_logs)
                    self.logger.info(f"コンテナ起動回数: {self.result.container_restart_count}回")
            else:
                # GCPログ取得失敗時
                self.result.uptime_rate = -1
                self.logger.warning("稼働率計算不可（GCPログ取得失敗）")

        except FileNotFoundError:
            # ローカル実行時（gcloudコマンドなし）
            self.result.uptime_rate = -1
            self.logger.info("稼働率計算スキップ（ローカル実行）")
        except Exception as e:
            self.logger.error(f"稼働率計算失敗: {e}")
            self.result.uptime_rate = -1

    async def _check_ml_model_status(self):
        """MLモデル使用状況確認（4指標）- Phase 59.8追加"""
        try:
            from src.core.config.threshold_manager import get_threshold
            from src.core.orchestration.ml_loader import MLModelLoader

            # stacking_enabled設定確認
            self.result.stacking_enabled = get_threshold("ensemble.stacking_enabled", False)

            # MLModelLoaderでモデルロード
            loader = MLModelLoader(self.logger)
            model = loader.load_model_with_priority()

            # モデルタイプ判定
            model_type = type(model).__name__
            self.result.ml_model_type = model_type

            # フォールバックレベル判定
            if model_type == "ProductionEnsemble":
                n_features = getattr(model, "n_features_", 0)
                self.result.ml_model_level = 1 if n_features >= 55 else 2
            elif model_type == "DummyModel":
                self.result.ml_model_level = 3
            else:
                self.result.ml_model_level = -1

            # 特徴量数
            self.result.ml_feature_count = getattr(
                model, "n_features_", getattr(model, "n_features_in_", 0)
            )

            self.logger.info(
                f"MLモデル状態確認完了 - {self.result.ml_model_type} "
                f"(Level {self.result.ml_model_level}, {self.result.ml_feature_count}特徴量)"
            )
        except Exception as e:
            self.logger.error(f"MLモデル状態確認失敗: {e}")
            self.result.ml_model_type = "error"

    async def _analyze_sl_patterns(self):
        """Phase 62.18: SLパターン分析（GCPログベース）"""
        import re
        from collections import defaultdict
        from datetime import timezone

        self.logger.info("SLパターン分析開始...")

        try:
            # GCPログから自動執行検知ログを取得
            logs = self._fetch_gcp_logs_json(
                'textPayload:"Phase 61.9" AND textPayload:"自動執行検知"', limit=500
            )

            if not logs:
                self.logger.info("ℹ️ SLパターン分析: 自動執行ログなし")
                return

            # ログをパース
            tp_executions = []
            sl_executions = []
            weekday_names = ["月", "火", "水", "木", "金", "土", "日"]

            for log_entry in logs:
                text = log_entry.get("textPayload", "")
                ts = log_entry.get("timestamp", "")

                # TP自動執行検知
                tp_match = re.search(
                    r"Phase 61\.9: TP自動執行検知 - (\w+) ([\d.]+) BTC @ (\d+)円 "
                    r"\((利益|損益): ([+-]?\d+)円\) 戦略: (\w+)",
                    text,
                )
                if tp_match:
                    tp_executions.append(
                        {
                            "pnl": float(tp_match.group(5)),
                            "strategy": tp_match.group(6),
                            "timestamp": ts,
                        }
                    )
                    continue

                # SL自動執行検知
                sl_match = re.search(
                    r"Phase 61\.9: SL自動執行検知 - (\w+) ([\d.]+) BTC @ (\d+)円 "
                    r"\((損失|損益): ([+-]?\d+)円\) 戦略: (\w+)",
                    text,
                )
                if sl_match:
                    sl_executions.append(
                        {
                            "pnl": float(sl_match.group(5)),
                            "strategy": sl_match.group(6),
                            "timestamp": ts,
                        }
                    )

            # 結果を格納
            self.result.sl_pattern_tp_count = len(tp_executions)
            self.result.sl_pattern_sl_count = len(sl_executions)
            self.result.sl_pattern_total_executions = len(tp_executions) + len(sl_executions)

            # SL損益統計
            if sl_executions:
                sl_pnls = [e["pnl"] for e in sl_executions]
                self.result.sl_pattern_sl_pnl_total = sum(sl_pnls)
                self.result.sl_pattern_sl_pnl_avg = sum(sl_pnls) / len(sl_pnls)

            # TP損益統計
            if tp_executions:
                tp_pnls = [e["pnl"] for e in tp_executions]
                self.result.sl_pattern_tp_pnl_total = sum(tp_pnls)
                self.result.sl_pattern_tp_pnl_avg = sum(tp_pnls) / len(tp_pnls)

            # 戦略別統計
            strategy_data = defaultdict(
                lambda: {"sl_count": 0, "tp_count": 0, "sl_pnl": 0.0, "tp_pnl": 0.0}
            )
            for e in sl_executions:
                strategy_data[e["strategy"]]["sl_count"] += 1
                strategy_data[e["strategy"]]["sl_pnl"] += e["pnl"]
            for e in tp_executions:
                strategy_data[e["strategy"]]["tp_count"] += 1
                strategy_data[e["strategy"]]["tp_pnl"] += e["pnl"]

            for strategy, data in strategy_data.items():
                total = data["sl_count"] + data["tp_count"]
                self.result.sl_pattern_strategy_stats[strategy] = {
                    "sl_count": data["sl_count"],
                    "tp_count": data["tp_count"],
                    "total": total,
                    "sl_rate": (data["sl_count"] / total * 100) if total > 0 else 0,
                    "sl_pnl": data["sl_pnl"],
                    "tp_pnl": data["tp_pnl"],
                }

            # 時間帯・曜日別統計
            hourly = defaultdict(int)
            weekday = defaultdict(int)
            for e in sl_executions:
                try:
                    ts_str = e["timestamp"].replace("Z", "+00:00")
                    ts = datetime.fromisoformat(ts_str)
                    ts_jst = ts + timedelta(hours=9)
                    hourly[ts_jst.hour] += 1
                    weekday[weekday_names[ts_jst.weekday()]] += 1
                except Exception:
                    pass

            self.result.sl_pattern_hourly_stats = dict(hourly)
            self.result.sl_pattern_weekday_stats = dict(weekday)

            self.logger.info(
                f"SLパターン分析完了 - TP:{len(tp_executions)}件, SL:{len(sl_executions)}件"
            )

        except Exception as e:
            self.logger.warning(f"SLパターン分析失敗: {e}")

    def _fetch_gcp_logs_json(self, query: str, limit: int = 500) -> List[Dict[str, Any]]:
        """GCPログをJSON形式で取得"""
        try:
            from datetime import timezone

            utc_now = datetime.now(timezone.utc)
            since_time = (utc_now - timedelta(hours=self.period_hours)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

            full_query = (
                f'resource.type="cloud_run_revision" AND '
                f'resource.labels.service_name="crypto-bot-service-prod" AND '
                f"({query}) AND "
                f'timestamp>="{since_time}"'
            )

            result = subprocess.run(
                [
                    "gcloud",
                    "logging",
                    "read",
                    full_query,
                    f"--limit={limit}",
                    "--format=json",
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout)
            return []

        except subprocess.TimeoutExpired:
            self.logger.warning("GCPログ取得タイムアウト")
            return []
        except json.JSONDecodeError:
            self.logger.warning("GCPログJSONパースエラー")
            return []
        except FileNotFoundError:
            self.logger.debug("GCPログ取得スキップ（ローカル実行）")
            return []
        except Exception as e:
            self.logger.warning(f"GCPログ取得エラー: {e}")
            return []


class LiveReportGenerator:
    """レポート生成"""

    def generate_json(self, result: LiveAnalysisResult) -> Dict[str, Any]:
        """JSON形式で出力"""
        return asdict(result)

    def generate_markdown(self, result: LiveAnalysisResult) -> str:
        """Markdown形式で出力"""
        lines = [
            "# ライブモード標準分析レポート",
            "",
            f"**分析日時**: {result.timestamp}",
            f"**対象期間**: 直近{result.analysis_period_hours}時間",
            "",
            "---",
            "",
            "## アカウント状態",
            "",
            "| 指標 | 値 | 状態 |",
            "|------|-----|------|",
        ]

        # 証拠金維持率の状態判定（ノーポジション時は明示的に表示）
        if result.open_position_count == 0 and result.margin_ratio >= 500:
            margin_display = "N/A"
            margin_status = "ポジションなし"
        else:
            margin_display = f"{result.margin_ratio:.1f}%"
            margin_status = (
                "正常"
                if result.margin_ratio >= 100
                else "注意" if result.margin_ratio >= 80 else "危険"
            )
        lines.append(f"| 証拠金維持率 | {margin_display} | {margin_status} |")
        lines.append(f"| 利用可能残高 | ¥{result.available_balance:,.0f} | - |")
        lines.append(f"| 使用中証拠金 | ¥{result.used_margin:,.0f} | - |")
        lines.append(f"| 未実現損益 | ¥{result.unrealized_pnl:+,.0f} | - |")
        lines.append(f"| マージンコール | {result.margin_call_status or 'なし'} | - |")

        lines.extend(
            [
                "",
                "---",
                "",
                "## ポジション状態",
                "",
                "| 指標 | 値 |",
                "|------|-----|",
                f"| オープンポジション | {result.open_position_count}件 |",
                f"| 未約定注文 | {result.pending_order_count}件 |",
            ]
        )

        if result.order_breakdown:
            breakdown_str = ", ".join(
                f"{k}:{v}" for k, v in result.order_breakdown.items() if v > 0
            )
            lines.append(f"| 注文内訳 | {breakdown_str or 'なし'} |")

        if result.losscut_price:
            lines.append(f"| ロスカット価格 | ¥{result.losscut_price:,.0f} |")

        # Phase 58.8: 孤児SL/TP警告
        if result.orphan_sl_detected:
            lines.append(f"| ⚠️ **孤児SL/TP注文** | **{result.orphan_order_count}件検出** |")

        # Phase 61.11: 勝率がN/A（-1）の場合の表示対応
        win_rate_str = "N/A (pnlデータなし)" if result.win_rate < 0 else f"{result.win_rate:.1f}%"
        # 推定勝率の場合は注記を追加
        if (
            result.win_rate >= 0
            and result.total_pnl == 0
            and (result.tp_triggered_count > 0 or result.sl_triggered_count > 0)
        ):
            win_rate_str += " (TP/SL推定)"

        lines.extend(
            [
                "",
                "---",
                "",
                "## 取引履歴分析",
                "",
                "| 指標 | 値 |",
                "|------|-----|",
                f"| 取引数 | {result.trades_count}件 |",
                f"| 勝率 | {win_rate_str} |",
                f"| 総損益 | ¥{result.total_pnl:+,.0f} |",
                f"| 平均損益 | ¥{result.avg_pnl:+,.0f} |",
                f"| 最大利益 | ¥{result.max_profit:+,.0f} |",
                f"| 最大損失 | ¥{result.max_loss:+,.0f} |",
                f"| TP発動 | {result.tp_triggered_count}回 |",
                f"| SL発動 | {result.sl_triggered_count}回 |",
            ]
        )

        if result.strategy_stats:
            lines.extend(
                [
                    "",
                    "### 戦略別パフォーマンス",
                    "",
                    "| 戦略 | 取引数 | 勝率 | 損益 |",
                    "|------|--------|------|------|",
                ]
            )
            for strategy, stats in result.strategy_stats.items():
                lines.append(
                    f"| {strategy} | {stats['trades']}件 | {stats['win_rate']:.1f}% | ¥{stats['pnl']:+,.0f} |"
                )

        lines.extend(
            [
                "",
                "---",
                "",
                "## システム健全性",
                "",
                "| 指標 | 値 | 状態 |",
                "|------|-----|------|",
                f"| API応答時間 | {result.api_response_time_ms:.0f}ms | {'正常' if result.api_response_time_ms < 5000 else '遅延'} |",
                f"| サービス状態 | {result.service_status} | {'正常' if result.service_status == 'Ready' else '確認要'} |",
            ]
        )

        if result.recent_error_count >= 0:
            error_status = "正常" if result.recent_error_count < 10 else "注意"
            lines.append(f"| 直近エラー数 | {result.recent_error_count}件 | {error_status} |")

        lines.append(f"| Container再起動 | {result.container_restart_count}回 | - |")

        if result.last_trade_time:
            lines.append(f"| 最終取引 | {result.last_trade_time[:19]} | - |")

        if result.last_deploy_time:
            lines.append(f"| 最終デプロイ | {result.last_deploy_time[:19]} | - |")

        lines.extend(
            [
                "",
                "---",
                "",
                "## TP/SL設置適切性",
                "",
                "| 指標 | 値 | 状態 |",
                "|------|-----|------|",
            ]
        )

        if result.tp_distance_pct is not None:
            lines.append(f"| TP距離 | {result.tp_distance_pct:.2f}% | - |")
        if result.sl_distance_pct is not None:
            lines.append(f"| SL距離 | {result.sl_distance_pct:.2f}% | - |")

        tp_sl_status = "正常" if result.tp_sl_placement_ok else "要確認"
        lines.append(f"| TP/SL設置 | {tp_sl_status} | {tp_sl_status} |")

        # Phase 65.2: カバレッジ率
        if result.tp_coverage_ratio is not None:
            tp_cov_s = "正常" if result.tp_coverage_ratio >= 0.95 else "不足"
            lines.append(f"| TPカバレッジ率 | {result.tp_coverage_ratio * 100:.1f}% | {tp_cov_s} |")
        if result.sl_coverage_ratio is not None:
            sl_cov_s = "正常" if result.sl_coverage_ratio >= 0.95 else "不足"
            lines.append(f"| SLカバレッジ率 | {result.sl_coverage_ratio * 100:.1f}% | {sl_cov_s} |")

        lines.extend(
            [
                "",
                "---",
                "",
                "## 稼働率",
                "",
                "| 指標 | 値 | 状態 |",
                "|------|-----|------|",
            ]
        )

        if result.uptime_rate >= 0:
            uptime_status = "達成" if result.uptime_rate >= 90 else "未達"
            lines.append(f"| 稼働時間率 | {result.uptime_rate:.1f}% | {uptime_status} (目標90%) |")
            lines.append(
                f"| 実行回数 | {result.actual_cycle_count}回 / {result.expected_cycle_count}回 | - |"
            )
            lines.append(f"| ダウンタイム | {result.total_downtime_minutes:.0f}分 | - |")
            lines.append(f"| 再起動回数 | {result.container_restart_count}回 | - |")
        else:
            lines.append("| 稼働時間率 | 計測不可 | - |")

        if result.last_incident_time:
            lines.append(f"| 直近障害 | {result.last_incident_time} | - |")

        # Phase 59.8: MLモデル状態セクション追加
        lines.extend(
            [
                "",
                "---",
                "",
                "## MLモデル状態",
                "",
                "| 指標 | 値 | 状態 |",
                "|------|-----|------|",
            ]
        )

        # モデルタイプ
        model_status = "正常" if result.ml_model_type == "ProductionEnsemble" else "要確認"
        lines.append(f"| モデルタイプ | {result.ml_model_type} | {model_status} |")

        # フォールバックレベル
        level_names = {1: "Full(55)", 2: "Basic(49)", 3: "Dummy"}
        level_name = level_names.get(result.ml_model_level, "不明")
        level_status = "正常" if result.ml_model_level <= 1 else "フォールバック中"
        lines.append(
            f"| フォールバックレベル | Level {result.ml_model_level} ({level_name}) | {level_status} |"
        )

        # 特徴量数
        feature_status = "正常" if result.ml_feature_count >= 55 else "縮退"
        lines.append(f"| 特徴量数 | {result.ml_feature_count} | {feature_status} |")

        # Stacking設定
        stacking_status = "有効" if result.stacking_enabled else "無効"
        lines.append(f"| Stacking設定 | {stacking_status} | - |")

        # Phase 62.16: スリッページ分析セクション追加
        if result.slippage_count > 0:
            lines.extend(
                [
                    "",
                    "---",
                    "",
                    "## スリッページ分析 (Phase 62.16)",
                    "",
                    "| 指標 | 値 | 備考 |",
                    "|------|-----|------|",
                    f"| 記録件数 | {result.slippage_count}件 | - |",
                    f"| 平均スリッページ | ¥{result.slippage_avg:+,.0f} | 正=不利方向(buy時) |",
                    f"| 最大スリッページ | ¥{result.slippage_max:+,.0f} | - |",
                    f"| 最小スリッページ | ¥{result.slippage_min:+,.0f} | - |",
                ]
            )
            if result.slippage_entry_avg != 0:
                lines.append(f"| エントリー平均 | ¥{result.slippage_entry_avg:+,.0f} | - |")
            if result.slippage_exit_avg != 0:
                lines.append(f"| 決済平均 | ¥{result.slippage_exit_avg:+,.0f} | - |")

        # Phase 62.18: SLパターン分析セクション追加
        if result.sl_pattern_total_executions > 0:
            total = result.sl_pattern_total_executions
            tp_rate = result.sl_pattern_tp_count / total * 100 if total > 0 else 0
            sl_rate = result.sl_pattern_sl_count / total * 100 if total > 0 else 0

            lines.extend(
                [
                    "",
                    "---",
                    "",
                    "## SLパターン分析 (Phase 62.18)",
                    "",
                    "| 指標 | 値 | 備考 |",
                    "|------|-----|------|",
                    f"| 総執行数 | {total}件 | TP+SL |",
                    f"| TP決済 | {result.sl_pattern_tp_count}件 ({tp_rate:.1f}%) | - |",
                    f"| SL決済 | {result.sl_pattern_sl_count}件 ({sl_rate:.1f}%) | - |",
                ]
            )
            if result.sl_pattern_sl_count > 0:
                lines.append(f"| SL合計損益 | ¥{result.sl_pattern_sl_pnl_total:+,.0f} | - |")
                lines.append(f"| SL平均損益 | ¥{result.sl_pattern_sl_pnl_avg:+,.0f} | - |")
            if result.sl_pattern_tp_count > 0:
                lines.append(f"| TP合計利益 | ¥{result.sl_pattern_tp_pnl_total:+,.0f} | - |")

            # 戦略別統計
            if result.sl_pattern_strategy_stats:
                lines.extend(
                    [
                        "",
                        "### 戦略別SL統計",
                        "",
                        "| 戦略 | SL数 | TP数 | SL率 | SL損益 |",
                        "|------|------|------|------|--------|",
                    ]
                )
                for strategy, stats in sorted(
                    result.sl_pattern_strategy_stats.items(),
                    key=lambda x: x[1]["sl_rate"],
                    reverse=True,
                ):
                    lines.append(
                        f"| {strategy} | {stats['sl_count']} | {stats['tp_count']} | "
                        f"{stats['sl_rate']:.1f}% | ¥{stats['sl_pnl']:+,.0f} |"
                    )

        return "\n".join(lines)

    def append_to_csv(self, result: LiveAnalysisResult, csv_path: str):
        """CSV履歴に追記"""
        file_exists = Path(csv_path).exists()

        # フラット化したデータ
        row = {
            "timestamp": result.timestamp,
            "period_hours": result.analysis_period_hours,
            "margin_ratio": result.margin_ratio,
            "available_balance": result.available_balance,
            "used_margin": result.used_margin,
            "unrealized_pnl": result.unrealized_pnl,
            "open_positions": result.open_position_count,
            "pending_orders": result.pending_order_count,
            "trades_count": result.trades_count,
            "win_rate": result.win_rate,
            "total_pnl": result.total_pnl,
            "tp_triggered": result.tp_triggered_count,
            "sl_triggered": result.sl_triggered_count,
            "api_response_ms": result.api_response_time_ms,
            "error_count": result.recent_error_count,
            "restart_count": result.container_restart_count,
            "uptime_rate": result.uptime_rate,
            "actual_cycles": result.actual_cycle_count,
            "expected_cycles": result.expected_cycle_count,
            "service_status": result.service_status,
            "tp_sl_ok": result.tp_sl_placement_ok,
            # Phase 59.8: MLモデル状態追加
            "ml_model_type": result.ml_model_type,
            "ml_model_level": result.ml_model_level,
            "ml_feature_count": result.ml_feature_count,
            "stacking_enabled": result.stacking_enabled,
        }

        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=row.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)


def determine_exit_code(
    infra_result: InfrastructureCheckResult,
    bot_result: BotFunctionCheckResult,
) -> int:
    """終了コードを決定

    Returns:
        0: 正常
        1: 致命的問題（即座対応必須）
        2: 要注意（詳細診断推奨）
        3: 監視継続（軽微な問題）
    """
    total_critical = infra_result.critical_issues + bot_result.critical_issues
    total_warning = infra_result.warning_issues + bot_result.warning_issues

    # Silent Failure検出（最重要）
    if bot_result.signal_count > 0 and bot_result.order_count == 0:
        return 1

    if total_critical >= 2:
        return 1
    elif total_critical >= 1:
        return 2
    elif total_warning >= 3:
        return 3
    else:
        return 0


async def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="ライブモード統合診断スクリプト")
    parser.add_argument("--hours", type=int, default=24, help="分析対象期間（時間）")
    parser.add_argument(
        "--output", type=str, default="docs/検証記録/live", help="出力先ディレクトリ"
    )
    parser.add_argument(
        "--exit-code",
        action="store_true",
        help="終了コードを返却（CI/CD連携用）",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="簡易チェック（GCPログのみ、API呼び出しなし）",
    )
    args = parser.parse_args()

    logger = get_logger()

    # 出力ディレクトリ作成
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # インフラ基盤診断（常に実行）
    infra_checker = InfrastructureChecker(logger)
    infra_result = infra_checker.check()

    # Bot機能診断（常に実行）
    bot_checker = BotFunctionChecker(logger, infra_checker)
    bot_result = bot_checker.check()

    # 簡易チェックモードの場合はここで終了
    if args.quick:
        print("\n" + "=" * 60)
        print("簡易診断結果")
        print("=" * 60)
        print("\n🔧 インフラ基盤診断:")
        print(f"   ✅ 正常項目: {infra_result.normal_checks}")
        print(f"   ⚠️  警告項目: {infra_result.warning_issues}")
        print(f"   ❌ 致命的問題: {infra_result.critical_issues}")
        print(f"   🏆 スコア: {infra_result.total_score}点")

        print("\n🤖 Bot機能診断:")
        print(f"   ✅ 正常項目: {bot_result.normal_checks}")
        print(f"   ⚠️  警告項目: {bot_result.warning_issues}")
        print(f"   ❌ 致命的問題: {bot_result.critical_issues}")
        print(f"   🏆 スコア: {bot_result.total_score}点")

        # Phase 65/65.2: 設定検証（簡易モード）
        if bot_result.config_checks:
            ng = bot_result.config_check_failed
            total = bot_result.config_check_passed + ng
            status = "全合格" if ng == 0 else f"{ng}件NG"
            print(f"\n🔧 設定検証: {status} ({bot_result.config_check_passed}/{total})")

        # Phase 62.9-62.10: Maker戦略サマリー（簡易モード）
        entry_total = bot_result.entry_maker_success_count + bot_result.entry_maker_fallback_count
        tp_total = bot_result.tp_maker_success_count + bot_result.tp_maker_fallback_count
        if entry_total > 0 or tp_total > 0:
            print("\n💰 Maker戦略:")
            if entry_total > 0:
                entry_rate = bot_result.entry_maker_success_count / entry_total * 100
                print(f"   エントリー: {entry_rate:.0f}%成功")
            if tp_total > 0:
                tp_rate = bot_result.tp_maker_success_count / tp_total * 100
                print(f"   TP決済: {tp_rate:.0f}%成功")

        exit_code = determine_exit_code(infra_result, bot_result)
        status_map = {
            0: "🟢 正常",
            1: "💀 致命的問題",
            2: "🟠 要注意",
            3: "🟡 監視継続",
        }
        print(f"\n🎯 最終判定: {status_map.get(exit_code, '不明')}")
        print("=" * 60)

        if args.exit_code:
            sys.exit(exit_code)
        return

    # 分析実行（API呼び出しあり）
    analyzer = LiveAnalyzer(period_hours=args.hours)
    result = await analyzer.analyze()

    # レポート生成
    generator = LiveReportGenerator()

    # ファイル名生成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON出力（診断結果も含める）
    combined_result = {
        "live_analysis": generator.generate_json(result),
        "infrastructure_check": asdict(infra_result),
        "bot_function_check": asdict(bot_result),
    }
    json_path = output_dir / f"live_analysis_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(combined_result, f, ensure_ascii=False, indent=2)
    print(f"JSON出力: {json_path}")

    # Markdown出力（診断結果も含める）
    md_content = generator.generate_markdown(result)
    md_content += _generate_diagnostic_markdown(infra_result, bot_result)
    md_path = output_dir / f"live_analysis_{timestamp}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Markdown出力: {md_path}")

    # CSV履歴追記
    csv_path = output_dir / "live_analysis_history.csv"
    generator.append_to_csv(result, str(csv_path))
    print(f"CSV履歴追記: {csv_path}")

    # サマリー表示
    print("\n" + "=" * 60)
    print("ライブモード統合診断サマリー")
    print("=" * 60)
    print(f"分析期間: 直近{args.hours}時間")
    if result.open_position_count == 0 and result.margin_ratio >= 500:
        print("証拠金維持率: N/A (ポジションなし)")
    else:
        print(f"証拠金維持率: {result.margin_ratio:.1f}%")
    # Phase 65.15: エントリー数と決済数を分けて表示
    tp_count = getattr(result, "tp_triggered_count", 0)
    sl_count = getattr(result, "sl_triggered_count", 0)
    exit_count = tp_count + sl_count
    print(
        f"取引数: エントリー{result.trades_count}件 / 決済{exit_count}件 (TP:{tp_count} SL:{sl_count})"
    )
    # Phase 61.11: 勝率N/A対応
    if result.win_rate < 0:
        print("勝率: N/A (pnlデータなし)")
    elif result.total_pnl == 0 and (tp_count > 0 or sl_count > 0):
        print(f"勝率: {result.win_rate:.1f}% (TP/SL推定)")
    else:
        print(f"勝率: {result.win_rate:.1f}%")
    print(f"総損益: ¥{result.total_pnl:+,.0f}")
    if result.uptime_rate >= 0:
        print(f"稼働率: {result.uptime_rate:.1f}%")
    print(f"サービス状態: {result.service_status}")
    print(f"MLモデル: {result.ml_model_type} (Level {result.ml_model_level})")

    print("\n🔧 インフラ基盤診断:")
    print(f"   ✅ 正常項目: {infra_result.normal_checks}")
    print(f"   ⚠️  警告項目: {infra_result.warning_issues}")
    print(f"   ❌ 致命的問題: {infra_result.critical_issues}")
    print(f"   🏆 スコア: {infra_result.total_score}点")

    print("\n🤖 Bot機能診断:")
    print(f"   ✅ 正常項目: {bot_result.normal_checks}")
    print(f"   ⚠️  警告項目: {bot_result.warning_issues}")
    print(f"   ❌ 致命的問題: {bot_result.critical_issues}")
    print(f"   🏆 スコア: {bot_result.total_score}点")

    # Phase 62.9-62.10: Maker戦略サマリー
    entry_total = bot_result.entry_maker_success_count + bot_result.entry_maker_fallback_count
    tp_total = bot_result.tp_maker_success_count + bot_result.tp_maker_fallback_count
    if entry_total > 0 or tp_total > 0:
        print("\n💰 Phase 62.9-62.10: Maker戦略:")
        if entry_total > 0:
            entry_rate = bot_result.entry_maker_success_count / entry_total * 100
            print(
                f"   エントリー: {bot_result.entry_maker_success_count}成功/"
                f"{bot_result.entry_maker_fallback_count}FB ({entry_rate:.0f}%)"
            )
        if tp_total > 0:
            tp_rate = bot_result.tp_maker_success_count / tp_total * 100
            print(
                f"   TP決済: {bot_result.tp_maker_success_count}成功/"
                f"{bot_result.tp_maker_fallback_count}FB ({tp_rate:.0f}%)"
            )
        # Phase 62.19: 推定削減額（設定参照で一元化）
        maker_success = bot_result.entry_maker_success_count + bot_result.tp_maker_success_count
        if maker_success > 0:
            from src.core.config.threshold_manager import get_threshold

            taker_rate = get_threshold("trading.fees.taker_rate", 0.001)
            maker_rate = get_threshold("trading.fees.maker_rate", 0.0)
            fee_reduction = taker_rate - maker_rate  # 0.1% - 0% = 0.1%
            estimated = maker_success * 1000000 * fee_reduction
            print(f"   推定手数料削減: ¥{estimated:,.0f}")

    # Phase 65/65.2: 設定検証
    if bot_result.config_checks:
        print("\n🔧 Phase 65/65.2: 設定検証:")
        for name, check in bot_result.config_checks.items():
            mark = "✅" if check["ok"] else "❌"
            print(f"   {mark} {name}: {check['actual']} (期待: {check['expected']})")

    # Phase 65.2: TP/SLフルカバー動作
    if bot_result.phase65_2_log_count > 0:
        print("\n📋 Phase 65.2: TP/SLフルカバー:")
        print(f"   部分キャンセル: {bot_result.partial_cancel_count}回")
        print(f"   固定TP復旧: {bot_result.fixed_tp_recovery_count}回")
        print(f"   統合TP配置: {bot_result.unified_tp_placement_count}回")

    # Phase 62.18: SLパターン分析サマリー
    if result.sl_pattern_total_executions > 0:
        total = result.sl_pattern_total_executions
        tp_rate = result.sl_pattern_tp_count / total * 100 if total > 0 else 0
        sl_rate = result.sl_pattern_sl_count / total * 100 if total > 0 else 0

        print("\n📉 Phase 62.18: SLパターン分析:")
        print(f"   TP決済: {result.sl_pattern_tp_count}件 ({tp_rate:.1f}%)")
        print(f"   SL決済: {result.sl_pattern_sl_count}件 ({sl_rate:.1f}%)")
        if result.sl_pattern_sl_count > 0:
            print(f"   SL合計損益: ¥{result.sl_pattern_sl_pnl_total:+,.0f}")
            print(f"   SL平均損益: ¥{result.sl_pattern_sl_pnl_avg:+,.0f}")
        total_pnl = result.sl_pattern_tp_pnl_total + result.sl_pattern_sl_pnl_total
        print(f"   総損益: ¥{total_pnl:+,.0f}")

        # 高SL率戦略の警告
        high_sl_strategies = [
            (s, d)
            for s, d in result.sl_pattern_strategy_stats.items()
            if d["sl_rate"] > 50 and d["total"] >= 3
        ]
        if high_sl_strategies:
            for strategy, data in high_sl_strategies:
                print(f"   ⚠️ {strategy}: SL率{data['sl_rate']:.1f}%")

    exit_code = determine_exit_code(infra_result, bot_result)
    status_map = {
        0: "🟢 正常",
        1: "💀 致命的問題 - 即座対応必須",
        2: "🟠 要注意 - 詳細診断推奨",
        3: "🟡 監視継続 - 軽微な問題",
    }
    print(f"\n🎯 最終判定: {status_map.get(exit_code, '不明')}")
    print("=" * 60)

    if args.exit_code:
        sys.exit(exit_code)


def _generate_diagnostic_markdown(
    infra_result: InfrastructureCheckResult,
    bot_result: BotFunctionCheckResult,
) -> str:
    """診断結果のMarkdown生成"""
    lines = [
        "",
        "---",
        "",
        "## インフラ基盤診断",
        "",
        "| 項目 | 結果 |",
        "|------|------|",
        f"| Cloud Run状態 | {infra_result.cloud_run_status} |",
        f"| Secret Manager権限 | {'✅ 全正常' if infra_result.bitbank_key_ok and infra_result.bitbank_secret_ok and infra_result.discord_ok else '❌ 欠如あり'} |",
        f"| Container exit(1) | {infra_result.container_exit_count}回 |",
        f"| RuntimeWarning | {infra_result.runtime_warning_count}回 |",
        f"| Discordエラー | {infra_result.discord_error_count}回 |",
        f"| API残高取得 | {infra_result.api_balance_count}回 |",
        f"| フォールバック使用 | {infra_result.fallback_count}回 |",
        f"| NoneTypeエラー | {infra_result.nonetype_error_count}回 |",
        f"| APIエラー | {infra_result.api_error_count}回 |",
        "",
        f"**スコア**: {infra_result.total_score}点 (正常:{infra_result.normal_checks} 警告:{infra_result.warning_issues} 致命的:{infra_result.critical_issues})",
        "",
        "---",
        "",
        "## Bot機能診断",
        "",
        "| 項目 | 結果 |",
        "|------|------|",
        f"| 55特徴量検出 | {bot_result.feature_55_count}回 |",
        f"| 49特徴量（フォールバック） | {bot_result.feature_49_count}回 |",
        f"| DummyModel使用 | {bot_result.dummy_model_count}回 |",
        f"| シグナル生成 | {bot_result.signal_count}回 |",
        f"| 注文実行 | {bot_result.order_count}回 |",
        f"| 成功率 | {bot_result.success_rate}% |",
        f"| アクティブ戦略数 | {bot_result.active_strategy_count}/6 |",
        f"| ML予測実行 | {bot_result.ml_prediction_count}回 |",
        f"| Kelly基準計算 | {bot_result.kelly_count}回 |",
        f"| Atomic Entry成功 | {bot_result.atomic_success_count}回 |",
        f"| ロールバック | {bot_result.atomic_rollback_count}回 |",
        "",
        "### 戦略別検出状況",
        "",
        "| 戦略 | 検出数 |",
        "|------|--------|",
    ]

    for strategy, count in bot_result.strategy_counts.items():
        status = "✅" if count > 0 else "ℹ️ 未検出"
        lines.append(f"| {strategy} | {count} {status} |")

    # Phase 62.9-62.10: Maker戦略セクション
    lines.extend(
        [
            "",
            "### Phase 62.9-62.10: Maker戦略",
            "",
            "| 項目 | 成功 | フォールバック | post_onlyキャンセル |",
            "|------|------|----------------|---------------------|",
        ]
    )

    # エントリーMaker
    entry_total = bot_result.entry_maker_success_count + bot_result.entry_maker_fallback_count
    entry_rate = (
        f"({bot_result.entry_maker_success_count / entry_total * 100:.0f}%)"
        if entry_total > 0
        else ""
    )
    lines.append(
        f"| エントリーMaker | {bot_result.entry_maker_success_count}回 {entry_rate} | "
        f"{bot_result.entry_maker_fallback_count}回 | "
        f"{bot_result.entry_post_only_cancelled_count}回 |"
    )

    # TP Maker
    tp_total = bot_result.tp_maker_success_count + bot_result.tp_maker_fallback_count
    tp_rate = f"({bot_result.tp_maker_success_count / tp_total * 100:.0f}%)" if tp_total > 0 else ""
    lines.append(
        f"| TP Maker | {bot_result.tp_maker_success_count}回 {tp_rate} | "
        f"{bot_result.tp_maker_fallback_count}回 | "
        f"{bot_result.tp_post_only_cancelled_count}回 |"
    )

    # Phase 62.19: 手数料削減効果の推定（設定参照で一元化）
    if entry_total > 0 or tp_total > 0:
        from src.core.config.threshold_manager import get_threshold

        taker_rate = get_threshold("trading.fees.taker_rate", 0.001)
        maker_rate = get_threshold("trading.fees.maker_rate", 0.0)
        fee_reduction = taker_rate - maker_rate  # Taker - Maker = 削減率
        fee_reduction_pct = fee_reduction * 100  # 0.1%表示用
        maker_success_total = (
            bot_result.entry_maker_success_count + bot_result.tp_maker_success_count
        )
        estimated_savings = maker_success_total * 1000000 * fee_reduction
        lines.extend(
            [
                "",
                f"**推定手数料削減効果**: ¥{estimated_savings:,.0f} "
                f"(Maker成功{maker_success_total}回 × {fee_reduction_pct:.2f}% × 100万円)",
            ]
        )

    # Phase 62.13: ATRフォールバック統計
    atr_total = bot_result.atr_success_count + bot_result.atr_fallback_count
    if atr_total > 0:
        atr_success_rate = bot_result.atr_success_count / atr_total * 100
        atr_status = "✅" if atr_success_rate == 100 else ("⚠️" if atr_success_rate >= 80 else "❌")
        lines.extend(
            [
                "",
                "### Phase 62.13: ATR取得状況",
                "",
                f"| 項目 | 回数 | 状態 |",
                f"|------|------|------|",
                f"| ATR取得成功 | {bot_result.atr_success_count}回 | {atr_status} ({atr_success_rate:.0f}%) |",
                f"| フォールバック使用 | {bot_result.atr_fallback_count}回 | - |",
            ]
        )

    # Phase 65/65.2: 設定検証
    if bot_result.config_checks:
        lines.extend(
            [
                "",
                "### Phase 65/65.2: 設定検証",
                "",
                "| 設定項目 | 期待値 | 実際の値 | 状態 |",
                "|---------|--------|---------|------|",
            ]
        )
        for name, check in bot_result.config_checks.items():
            status = "✅" if check["ok"] else "❌"
            lines.append(f"| {name} | {check['expected']} | {check['actual']} | {status} |")

    # Phase 65.2: GCPログ動作確認
    if bot_result.phase65_2_log_count > 0:
        lines.extend(
            [
                "",
                "### Phase 65.2: TP/SLフルカバー動作確認",
                "",
                "| 項目 | 回数 | 備考 |",
                "|------|------|------|",
                f"| Phase 65.2ログ総数 | {bot_result.phase65_2_log_count}回 | - |",
                f"| 部分TP/SLキャンセル | {bot_result.partial_cancel_count}回 | tp_sl_manager.py |",
                f"| 固定金額TP復旧 | {bot_result.fixed_tp_recovery_count}回 | tp_sl_manager.py |",
                f"| 統合TP配置成功 | {bot_result.unified_tp_placement_count}回 | tp_sl_manager.py |",
                f"| カバレッジ不足検出 | {bot_result.coverage_deficit_count}回 | tp_sl_manager.py |",
            ]
        )

    lines.extend(
        [
            "",
            f"**スコア**: {bot_result.total_score}点 (正常:{bot_result.normal_checks} 警告:{bot_result.warning_issues} 致命的:{bot_result.critical_issues})",
            "",
        ]
    )

    return "\n".join(lines)


if __name__ == "__main__":
    asyncio.run(main())
