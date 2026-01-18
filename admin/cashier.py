import importlib
from pathlib import Path

import streamlit as st

# Streamlit reruns scripts but may keep imported modules cached.
# Reload firebase_db here so newly-added functions are always available without a server restart.
import data.firebase_db as firebase_db

firebase_db = importlib.reload(firebase_db)

st.title("受付 / Front Desk")
st.caption("1) Scan QR to open the app  2) Enter the login code / QRを読み取り→ログインコード入力")

# No-click mode: keep a small buffer so cashier never gets stuck.
firebase_db.ensure_payment_codes(min_unused=5, created_by="auto")

qr_path = Path(__file__).resolve().parents[1] / "qrcode.PNG"
if qr_path.exists():
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.image(str(qr_path), caption="Scan to open the app / アプリを開く", width="stretch")

st.divider()
st.subheader("登录码 / Login code")

code = firebase_db.get_next_unused_payment_code()
if not code:
    st.warning("No available code. Please refresh or contact admin. / コードがありません。更新するか管理者に連絡してください。")
else:
    st.markdown(
        f"""
        <div style="
            padding: 18px 16px;
            border-radius: 14px;
            border: 1px solid rgba(255,255,255,0.12);
            background: rgba(255,255,255,0.04);
            text-align: center;
        ">
          <div style="font-size: 13px; opacity: 0.75;">Tell the participant this code / このコードを伝えてください</div>
          <div style="font-size: 44px; font-weight: 800; letter-spacing: 0.12em; margin-top: 8px;">{code}</div>
          <div style="font-size: 12px; opacity: 0.75; margin-top: 8px;">One-time use / 1回のみ有効</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
