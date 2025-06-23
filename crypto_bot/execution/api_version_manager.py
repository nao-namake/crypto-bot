# =============================================================================
# ファイル名: crypto_bot/execution/api_version_manager.py
# 説明:
# 各取引所のAPI仕様バージョン管理とアップデート対応機能
# - API仕様変更の検知と対応
# - 取引所ごとのAPI version情報管理
# - 後方互換性チェック
# - アップデート通知機能
# =============================================================================

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import ccxt
from packaging import version


class ApiVersionManager:
    """取引所API仕様のバージョン管理とアップデート対応"""

    def __init__(self, config_path: Optional[str] = None):
        """
        Parameters
        ----------
        config_path : str, optional
            API仕様情報を保存するJSONファイルのパス
        """
        self.config_path = Path(config_path or "config/api_versions.json")
        self.supported_exchanges = {
            "bybit": {
                "ccxt_version": ccxt.__version__,
                "api_docs_url": "https://bybit-exchange.github.io/docs/",
                "testnet_url": "https://testnet.bybit.com/",
                "rate_limit": 120,  # requests per minute
                "features": ["spot", "future", "option", "websocket"],
            },
            "bitbank": {
                "ccxt_version": ccxt.__version__,
                "api_docs_url": "https://docs.bitbank.cc/",
                "testnet_url": None,
                "rate_limit": 60,
                "features": ["spot"],
            },
            "bitflyer": {
                "ccxt_version": ccxt.__version__,
                "api_docs_url": "https://lightning.bitflyer.com/docs/api",
                "testnet_url": None,
                "rate_limit": 100,
                "features": ["spot", "future"],
            },
            "okcoinjp": {
                "ccxt_version": ccxt.__version__,
                "api_docs_url": "https://www.okx.com/docs-v5/en/",
                "testnet_url": None,
                "rate_limit": 20,
                "features": ["spot"],
            },
        }
        self._load_version_config()

    def _load_version_config(self) -> None:
        """保存されたAPI仕様情報を読み込み"""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.version_config = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.version_config = {}
        else:
            self.version_config = {}
            self._save_version_config()

    def _save_version_config(self) -> None:
        """API仕様情報をファイルに保存"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.version_config, f, indent=2, ensure_ascii=False)

    def check_ccxt_version_compatibility(self, exchange_id: str) -> Tuple[bool, str]:
        """
        CCXTライブラリのバージョン互換性をチェック

        Returns
        -------
        Tuple[bool, str]
            (互換性があるか, メッセージ)
        """
        if exchange_id not in self.supported_exchanges:
            return False, f"Unsupported exchange: {exchange_id}"

        current_version = ccxt.__version__
        stored_info = self.version_config.get(exchange_id, {})
        last_tested_version = stored_info.get("last_tested_ccxt_version")

        if not last_tested_version:
            # 初回チェック
            self._update_exchange_info(exchange_id, current_version)
            return (
                True,
                f"First time setup for {exchange_id} with CCXT {current_version}",
            )

        try:
            current_ver = version.parse(current_version)
            tested_ver = version.parse(last_tested_version)

            if current_ver > tested_ver:
                # マイナーバージョンアップまでは互換性ありと仮定
                major_current, minor_current, _ = current_ver.release[:3]
                major_tested, minor_tested, _ = tested_ver.release[:3]

                if major_current == major_tested and minor_current <= minor_tested + 1:
                    self._update_exchange_info(exchange_id, current_version)
                    return (
                        True,
                        f"Compatible version upgrade: {last_tested_version} -> "
                        f"{current_version}",
                    )
                else:
                    return (
                        False,
                        f"Major version change detected: {last_tested_version} -> "
                        f"{current_version}. Manual verification required.",
                    )

            return True, f"Using tested version {current_version}"

        except Exception as e:
            return False, f"Version comparison failed: {e}"

    def _update_exchange_info(self, exchange_id: str, ccxt_version: str) -> None:
        """取引所情報を更新"""
        if exchange_id not in self.version_config:
            self.version_config[exchange_id] = {}

        self.version_config[exchange_id].update(
            {
                "last_tested_ccxt_version": ccxt_version,
                "last_checked": datetime.now(timezone.utc).isoformat(),
                "api_features": self.supported_exchanges[exchange_id]["features"],
            }
        )
        self._save_version_config()

    def get_exchange_client_info(self, exchange_id: str) -> Dict[str, Any]:
        """取引所クライアントの詳細情報を取得"""
        try:
            exchange_class = getattr(ccxt, exchange_id.lower())
            exchange_instance = exchange_class()

            client_info = {
                "exchange_id": exchange_id,
                "ccxt_version": ccxt.__version__,
                "api_version": getattr(exchange_instance, "version", "unknown"),
                "has_sandbox": hasattr(exchange_instance, "sandbox"),
                "has_testnet": getattr(exchange_instance, "urls", {}).get("test")
                is not None,
                "supported_methods": [
                    method
                    for method in dir(exchange_instance)
                    if method.startswith("fetch_")
                    or method.startswith("create_")
                    or method.startswith("cancel_")
                ],
                "rate_limits": getattr(exchange_instance, "rateLimit", None),
                "fees": getattr(exchange_instance, "fees", {}),
                "symbols": [],  # 実際の取得は負荷が高いのでオプション
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

            # 基本情報を保存
            self.version_config[exchange_id] = {
                **self.version_config.get(exchange_id, {}),
                **client_info,
            }
            self._save_version_config()

            return client_info

        except Exception as e:
            return {
                "exchange_id": exchange_id,
                "error": str(e),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

    def validate_api_compatibility(self, exchange_id: str) -> Dict[str, Any]:
        """
        API互換性の包括的な検証

        Returns
        -------
        Dict[str, Any]
            検証結果レポート
        """
        validation_result = {
            "exchange_id": exchange_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {},
        }

        # 1. CCXT バージョンチェック
        ccxt_compat, ccxt_msg = self.check_ccxt_version_compatibility(exchange_id)
        validation_result["checks"]["ccxt_compatibility"] = {
            "passed": ccxt_compat,
            "message": ccxt_msg,
        }

        # 2. 基本機能チェック
        try:
            exchange_class = getattr(ccxt, exchange_id.lower())
            exchange_instance = exchange_class()

            required_methods = ["fetch_ticker", "fetch_ohlcv", "fetch_balance"]
            missing_methods = []

            for method in required_methods:
                if not hasattr(exchange_instance, method):
                    missing_methods.append(method)

            validation_result["checks"]["required_methods"] = {
                "passed": len(missing_methods) == 0,
                "missing_methods": missing_methods,
                "message": (
                    "All required methods available"
                    if not missing_methods
                    else f"Missing: {missing_methods}"
                ),
            }

        except Exception as e:
            validation_result["checks"]["required_methods"] = {
                "passed": False,
                "message": f"Failed to instantiate exchange: {e}",
            }

        # 3. 設定ファイルとの整合性チェック
        supported_info = self.supported_exchanges.get(exchange_id, {})

        validation_result["checks"]["configuration"] = {
            "passed": bool(supported_info),
            "message": (
                "Exchange configuration found"
                if supported_info
                else "No configuration for this exchange"
            ),
            "features": supported_info.get("features", []),
            "has_testnet": supported_info.get("testnet_url") is not None,
        }

        # 総合判定
        all_passed = all(
            check.get("passed", False) for check in validation_result["checks"].values()
        )
        validation_result["overall_status"] = "PASS" if all_passed else "FAIL"

        return validation_result

    def get_outdated_exchanges(self, days_threshold: int = 30) -> list:
        """
        指定日数以上チェックされていない取引所を取得

        Parameters
        ----------
        days_threshold : int
            チェック間隔の閾値（日数）

        Returns
        -------
        list
            古いチェック情報を持つ取引所のリスト
        """
        from datetime import timedelta

        outdated = []
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_threshold)

        for exchange_id, info in self.version_config.items():
            last_checked = info.get("last_checked")
            if last_checked:
                try:
                    last_check_date = datetime.fromisoformat(
                        last_checked.replace("Z", "+00:00")
                    )
                    if last_check_date < cutoff_date:
                        outdated.append(
                            {
                                "exchange_id": exchange_id,
                                "last_checked": last_checked,
                                "days_since_check": (
                                    datetime.now(timezone.utc) - last_check_date
                                ).days,
                            }
                        )
                except ValueError:
                    # 無効な日付形式の場合も古いとみなす
                    outdated.append(
                        {
                            "exchange_id": exchange_id,
                            "last_checked": last_checked,
                            "days_since_check": "unknown",
                        }
                    )

        return outdated

    def generate_compatibility_report(self) -> Dict[str, Any]:
        """全取引所の互換性レポートを生成"""
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "ccxt_version": ccxt.__version__,
            "exchanges": {},
            "summary": {
                "total_exchanges": len(self.supported_exchanges),
                "compatible": 0,
                "incompatible": 0,
                "needs_update": 0,
            },
        }

        for exchange_id in self.supported_exchanges.keys():
            validation = self.validate_api_compatibility(exchange_id)
            report["exchanges"][exchange_id] = validation

            if validation["overall_status"] == "PASS":
                report["summary"]["compatible"] += 1
            else:
                report["summary"]["incompatible"] += 1

        # 更新が必要な取引所
        outdated = self.get_outdated_exchanges()
        report["summary"]["needs_update"] = len(outdated)
        report["outdated_exchanges"] = outdated

        return report
