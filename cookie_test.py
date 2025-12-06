import streamlit as st
import extra_streamlit_components as stx
import datetime
import time

st.title("🍪 Cookie 实验室")

# 1. 初始化管理器
st.write("正在连接浏览器 Cookie 管理器...")
cookie_manager = stx.CookieManager()

# 2. 读取当前浏览器里的 'test_cookie'
# 注意：第一次运行时这里可能是 None
current_value = cookie_manager.get(cookie="test_cookie")

st.divider()

# --- 显示区 ---
if current_value:
    st.success(f"🔍 读取成功！浏览器里存着的值是： **{current_value}**")
else:
    st.info("🤷‍♂️ 没找到名为 'test_cookie' 的值 (可能是新访客，或已过期/删除)")

st.divider()

# --- 操作区 ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("写入/更新 Cookie")
    new_input = st.text_input("输入你想存的内容", "Hello World")
    
    if st.button("💾 保存到浏览器"):
        # 写入 cookie，有效期 1 天
        expires = datetime.datetime.now() + datetime.timedelta(days=1)
        cookie_manager.set("test_cookie", new_input, expires_at=expires)
        
        st.success("指令已发送！正在刷新...")
        time.sleep(1) # 给浏览器一点时间写入
        st.rerun()    # 刷新页面，让你立刻看到读取结果的变化

with col2:
    st.subheader("删除 Cookie")
    if st.button("🗑️ 清空"):
        cookie_manager.delete("test_cookie")
        
        st.warning("删除指令已发送！正在刷新...")
        time.sleep(1)
        st.rerun()