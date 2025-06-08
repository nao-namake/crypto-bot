# monitor.py
import json
from pathlib import Path

import streamlit as st

st.title("📈 CryptoBot Monitor")

status_file = Path("status.json")

if status_file.exists():
    status = json.loads(status_file.read_text())
    st.write("最終更新:", status["last_updated"], "UTC")
    st.metric("累積利益", f"{status['total_profit']:,} 円")
    st.metric("取引回数", status["trade_count"])
    st.metric("ポジション", status["position"] or "なし")
    st.metric("状態", status["state"])
else:
    st.warning("status.json がまだ生成されていません")
