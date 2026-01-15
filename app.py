import streamlit as st
import time
import datetime
import pytz
import extra_streamlit_components as stx
from pathlib import Path
import sys

# Ensure local package import works reliably under Streamlit reloader
sys.path.append(str(Path(__file__).parent))
import data  # noqa: F401

from data.firebase_db import login_user, logup_user, get_my_status

cookie_manager = stx.CookieManager(key="meetup_manager")
cookie_id = cookie_manager.get(cookie="uuid")

if "u_id" not in st.session_state:
    st.session_state.u_id = None
if "cookie_bootstrap_attempted" not in st.session_state:
    st.session_state.cookie_bootstrap_attempted = False

# CookieManager 在某些新会话/移动端切后台后，第一次渲染可能拿不到 cookie；
# 做一次轻量的“二次尝试”可以显著减少误判为需要重新登录的情况。
if (cookie_id is None) and (st.session_state.u_id is None) and (not st.session_state.cookie_bootstrap_attempted):
    st.session_state.cookie_bootstrap_attempted = True
    time.sleep(0.2)
    st.rerun()

tz = pytz.timezone("Pacific/Auckland")
today_str = str(datetime.datetime.now(tz=tz).date())

# Cookie format: "{YYYY-MM-DD}|{uuid}"
if cookie_id and (st.session_state.u_id is None):
    if "|" in str(cookie_id):
        date_part, uuid_part = str(cookie_id).split("|", 1)
        if date_part == today_str:
            st.session_state.u_id = uuid_part
    else:
        # Legacy cookie (uuid only): treat as today's user, then refresh on login
        st.session_state.u_id = str(cookie_id)
current_id = st.session_state.u_id

if "role" not in st.session_state:
    st.session_state.role = "Select your role"
if "started" not in st.session_state:
    st.session_state.started = False
if "name" not in st.session_state:
    st.session_state.name = None
if "skip_auto_restore" not in st.session_state:
    st.session_state.skip_auto_restore = False

# 自动恢复：如果有 cookie，并且当日仍是 Checked In，则自动进入 Participant
if (
    st.session_state.role == "Select your role"
    and st.session_state.u_id
    and not st.session_state.skip_auto_restore
):
    try:
        p = get_my_status(st.session_state.u_id)
        if p.status == "Checked In":
            st.session_state.role = "Participant"
            st.session_state.name = p.name
    except Exception:
        # 找不到/查询失败就保持在登录页
        pass

ROLES = ["Select your role", "Participant", "Admin"]
ADMIN_PASSWORD = "123456789"
COOKIE_TTL_DAYS = 3  # 覆盖周三->周五活动间隔；不会跨太久造成困扰

ROLE_LABELS = {
    "Select your role": "役割を選択 / Select your role",
    "Participant": "参加者 / Participant",
    "Admin": "管理者 / Admin",
}

def login():
    st.header("ログイン / Log in")
    role = st.selectbox(
        "役割を選択 / Choose your role",
        ROLES,
        format_func=lambda r: ROLE_LABELS.get(r, str(r)),
    )

    st.divider()

    if role == "Select your role":
        pass
    elif role == "Participant":
        with st.form("checkin_form"):
            name = st.text_input("君の名前 / Your Name")
            language = st.selectbox(
                "言語 / Language", 
                ["English", "Japanese"]
            )
            submitted = st.form_submit_button("✅ Log in")
            
            if submitted:
                if name and language:
                    if current_id:
                        participant_id, final_name = login_user(current_id, name, language)
                        # 刷新 cookie 的过期时间，避免用户隔天回来突然失效
                        cookie_manager.set(
                            "uuid",
                            f"{today_str}|{participant_id}",
                            expires_at=datetime.datetime.now() + datetime.timedelta(days=COOKIE_TTL_DAYS),
                        )

                        st.session_state.role = role
                        st.session_state.name = final_name
                        st.session_state.skip_auto_restore = False

                        st.session_state.u_id = participant_id
                        st.rerun()
                    else:
                        participant_id, final_name = logup_user(name, language)
                        cookie_manager.set(
                            "uuid",
                            f"{today_str}|{participant_id}",
                            expires_at=datetime.datetime.now() + datetime.timedelta(days=COOKIE_TTL_DAYS),
                        )
                        st.session_state.u_id = participant_id
                        time.sleep(1)

                        st.session_state.role = role
                        st.session_state.name = final_name
                        st.session_state.skip_auto_restore = False
                        st.rerun()
                else:
                    st.error("名前と言語を選択してください。 / Please enter your name and select a language.")
    else:
        password = st.text_input("パスワード / Password", type="password")
        if st.button("ログイン / Log in"):
            if password != ADMIN_PASSWORD:
                st.error("パスワードが違います。 / Incorrect password, try again.")
            else:
                st.session_state.role = role
                st.session_state.name = "Admin"
                st.rerun()


def logout():
    # 显式登出：仅重置会话态，不删除 cookie（便于同一活动内快速恢复）
    st.session_state.name = None
    st.session_state.u_id = None
    st.session_state.skip_auto_restore = True
    st.session_state.role = "Select your role"
    st.rerun()


role = st.session_state.role

logout_page = st.Page(logout, title="ログアウト / Log out", icon=":material/logout:")
settings = st.Page("settings.py", title="設定 / Settings", icon=":material/settings:")

participant = st.Page(
    "participant/participant_1.py",
    title="参加者 / Participant",
    icon=":material/healing:",
    default=(role == "Participant"),
)
participant_activity = st.Page(
    "participant/participant_2.py",
    title="活動 / Activities",
    icon=":material/forum:",
)
# participant_test_page = st.Page(
#     "participant/test.py", 
#     title="テスト / Test", 
#     icon=":material/bug_report:")

admin_1 = st.Page(
    "admin/admin_1.py",
    title="Admin 1",
    icon=":material/person_add:",
    default=(role == "Admin"),
)
admin_2 = st.Page(
    "admin/admin_2.py", 
    title="Admin 2", 
    icon=":material/security:")
admin_simulate = st.Page(
    "admin/simulate.py",
    title="Simulate / Debug",
    icon=":material/biotech:",
)
# admin_test_page = st.Page(
#     "admin/test.py", 
#     title="Test Page", 
#     icon=":material/bug_report:")


account_pages = [logout_page, settings]
participant_pages = [participant, participant_activity]
admin_pages = [admin_1, admin_2, admin_simulate]

if st.session_state.role == "Select your role":
    st.title("ようこそ！Welcome to Auckland Japanese~English Exchange Meetup!")

page_dict = {}
if st.session_state.role == "Participant":
    page_dict["Participant"] = participant_pages
elif st.session_state.role == "Admin":
    page_dict["Admin"] = admin_pages

if len(page_dict) > 0:
    pg = st.navigation({"Account": account_pages} | page_dict)
else:
    pg = st.navigation([st.Page(login, title="Log in")])

pg.run()
