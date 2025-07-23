# =============================================================================
# ファイル名: crypto_bot/execution/factory.py
# 説明:
# 取引所ごとのAPIクライアント（ccxtまたは独自ラッパー）を生成するFactory関数群。
# - Bybitは専用ラッパー（テストネット対応）
# - Bitbank, Bitflyer, OkcoinJP等はccxtラッパー
# - APIキー・シークレットやオプションも柔軟に受け取れる
# - 他のどの層からも「取引所を抽象化」して呼び出せる設計
# =============================================================================

from typing import Any, Dict, Optional

from .bitbank_client import BitbankClient
from .bitflyer_client import BitflyerClient

# 🚫 from .bybit_client import BybitTestnetClient  # 本番に影響しないようコメントアウト
from .okcoinjp_client import OkcoinJpClient


def create_exchange_client(
    exchange_id: str,
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
    testnet: bool = True,
    ccxt_options: Optional[Dict[str, Any]] = None,
    margin_mode: bool = False,
    **kwargs: Any,
):
    """
    Parameters
    ----------
    exchange_id : str
        "bybit", "bitbank", "bitflyer", "okcoinjp", …
    api_key / api_secret : str | None
        環境変数に入れている場合は None で OK
    testnet : bool
        テストネットを使うかどうか（Bybit は True 推奨）
    ccxt_options : dict | None
        CCXT に直接渡す追加オプション
    margin_mode : bool
        信用取引モード（Bitbankのみ対応）
    """
    eid = exchange_id.lower()

    # 🚫 Bybit Testnet - 本番に影響しないようコメントアウト
    # 独自ラッパーなので ccxt_options は渡さない
    # if eid in ("bybit", "bybit-testnet", "bybit_testnet"):
    #     return BybitTestnetClient(api_key, api_secret, testnet=testnet)

    # ── 以降は CCXT ラッパー系 ──────────────────────────────
    if eid == "bitbank":
        return BitbankClient(
            api_key, api_secret, testnet=testnet, margin_mode=margin_mode,
            ccxt_options=ccxt_options or {}  # Phase G.1.1: ccxt_options伝達欠陥修復
        )

    if eid == "bitflyer":
        return BitflyerClient(api_key, api_secret, testnet=testnet)

    if eid in ("okcoinjp", "okj"):
        return OkcoinJpClient(api_key, api_secret, testnet=testnet)

    raise ValueError(f"Unknown exchange_id: {exchange_id}")
