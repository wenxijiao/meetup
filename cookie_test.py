import streamlit as st
import extra_streamlit_components as stx
import datetime
import time

st.title("🍪 Cookie Lab / Cookie テスト")

# 1) Initialize manager
st.write("Connecting to Cookie Manager... / Cookie Manager に接続中...")
cookie_manager = stx.CookieManager()

# 2) Read current browser cookie "test_cookie"
# Note: may be None on the first run
current_value = cookie_manager.get(cookie="test_cookie")

st.divider()

# --- Display ---
if current_value:
    st.success(f"🔍 Read OK / 読み取り成功: **{current_value}**")
else:
    st.info("No 'test_cookie' found (new visitor or expired/deleted). / 'test_cookie' が見つかりません。")

st.divider()

# --- Actions ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Write / Update Cookie / 書き込み・更新")
    new_input = st.text_input("Value to store / 保存する値", "Hello World")
    
    if st.button("💾 Save to browser / 保存"):
        # Write cookie, valid for 1 day
        expires = datetime.datetime.now() + datetime.timedelta(days=1)
        cookie_manager.set("test_cookie", new_input, expires_at=expires)
        
        st.success("Saved. Refreshing... / 保存しました。更新中…")
        time.sleep(1)  # Give the browser time to persist
        st.rerun()

with col2:
    st.subheader("Delete Cookie / 削除")
    if st.button("🗑️ Delete / 削除"):
        cookie_manager.delete("test_cookie")
        
        st.warning("Deleted. Refreshing... / 削除しました。更新中…")
        time.sleep(1)
        st.rerun()