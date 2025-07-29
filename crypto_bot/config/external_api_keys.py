"""
外部APIキー設定
Phase H.23.4: ファイル直接埋め込み方式・GitHub Secrets代替

外部データ取得用APIキーは流出しても大きな問題にならないため、
デプロイ確実性を優先してファイル直接埋め込み方式を採用。
"""

# Phase H.23.4: 外部APIキー直接設定
EXTERNAL_API_KEYS = {
    # Alpha Vantage API (VIX/株式データ取得用)
    "ALPHA_VANTAGE_API_KEY": "3VY7MFDW0RE0Q520",
    # Polygon.io API (市場データ取得用)
    "POLYGON_API_KEY": "_WnGOxuSYRpNqWyb4G9jBwaizrvONMfW",
    # FRED API (経済指標取得用)
    "FRED_API_KEY": "3a34b6a33d030555dc63428690853ea9",
}


def get_api_key(key_name: str) -> str:
    """
    APIキーを取得

    Args:
        key_name: APIキー名

    Returns:
        APIキー文字列
    """
    return EXTERNAL_API_KEYS.get(key_name, "")


def get_all_api_keys() -> dict:
    """
    全APIキーを取得

    Returns:
        APIキー辞書
    """
    return EXTERNAL_API_KEYS.copy()
