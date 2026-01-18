import streamlit as st
import time
import datetime
import pytz
import extra_streamlit_components as stx
from pathlib import Path
import sys
import hmac
import hashlib

# Ensure local package import works reliably under Streamlit reloader
sys.path.append(str(Path(__file__).parent))
import data  # noqa: F401

from data.firebase_db import login_user, logup_user, get_my_status, checkin_with_optional_payment_code

cookie_manager = stx.CookieManager(key="meetup_manager")
cookie_id = cookie_manager.get(cookie="uuid")
staff_cookie = cookie_manager.get(cookie="staff")

if "u_id" not in st.session_state:
    st.session_state.u_id = None
if "cookie_bootstrap_attempted" not in st.session_state:
    st.session_state.cookie_bootstrap_attempted = False

# CookieManager may return None on the first render (esp. mobile background/foreground).
# A lightweight second attempt reduces false "please log in again" cases.
if (cookie_id is None) and (st.session_state.u_id is None) and (not st.session_state.cookie_bootstrap_attempted):
    st.session_state.cookie_bootstrap_attempted = True
    time.sleep(0.2)
    st.rerun()

tz = pytz.timezone("Pacific/Auckland")
today_str = str(datetime.datetime.now(tz=tz).date())

# Staff cookie format: "{YYYY-MM-DD}|{role}|{sig}"
def _staff_sig(date_part: str, role: str, secret: str) -> str:
    msg = f"{date_part}|{role}".encode("utf-8")
    key = (secret or "").encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()

def _maybe_restore_staff_from_cookie():
    if not staff_cookie:
        return False
    if st.session_state.role != "Select your role":
        return False
    if st.session_state.skip_auto_restore:
        return False
    try:
        parts = str(staff_cookie).split("|")
        if len(parts) != 3:
            return False
        date_part, role_part, sig = parts
        if date_part != today_str:
            return False
        if role_part not in ("Admin", "Cashier"):
            return False
        secret = ADMIN_PASSWORD if role_part == "Admin" else CASHIER_PASSWORD
        if not hmac.compare_digest(sig, _staff_sig(date_part, role_part, secret)):
            return False
        st.session_state.role = role_part
        st.session_state.name = role_part
        return True
    except Exception:
        return False

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

# Auto-restore: if cookie exists and today's status is still Checked In, enter Participant automatically.
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
        # If not found / query failed, stay on the login page.
        pass

ROLES = ["Select your role", "Participant", "Cashier", "Admin"]
ADMIN_PASSWORD = "123456789"
CASHIER_PASSWORD = "987654321"
COOKIE_TTL_DAYS = 2  # Covers Wed->Fri cadence without lasting too long.

ROLE_LABELS = {
    "Select your role": "役割を選択 / Select your role",
    "Participant": "参加者 / Participant",
    "Cashier": "受付 / Cashier",
    "Admin": "管理者 / Admin",
}

# Try staff auto-restore (must run AFTER password constants are defined).
# Cashier/Admin devices typically don't have participant uuid cookie, so do this first.
_maybe_restore_staff_from_cookie()

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
            payment_code = st.text_input("支払いコード / Payment code", help="Front desk will give you a one-time code after payment.")
            submitted = st.form_submit_button("✅ Log in")
            
            if submitted:
                if name and language:
                    # Use one-time payment code unless you are already paid / already checked-in today.
                    try:
                        if current_id:
                            participant_id, final_name = checkin_with_optional_payment_code(
                                current_id, name, language, payment_code
                            )
                        else:
                            participant_id, final_name = checkin_with_optional_payment_code(
                                None, name, language, payment_code
                            )

                        # Refresh cookie expiry to avoid unexpected expiry during the event.
                        cookie_manager.set(
                            "uuid",
                            f"{today_str}|{participant_id}",
                            expires_at=datetime.datetime.now() + datetime.timedelta(days=COOKIE_TTL_DAYS),
                        )

                        st.session_state.role = role
                        st.session_state.name = final_name
                        st.session_state.skip_auto_restore = False
                        st.session_state.u_id = participant_id

                        # Give the browser a moment to persist cookies on some mobile clients.
                        time.sleep(0.2)
                        st.rerun()
                    except ValueError as e:
                        msg = str(e) or "Login failed"
                        if "Payment code is required" in msg:
                            st.error("Payment code is required. / 支払いコードが必要です。")
                        elif "Invalid code" in msg:
                            st.error("Invalid code. Please ask the front desk for a valid code. / 無効なコードです。受付で確認してください。")
                        elif "Code already used" in msg:
                            st.error("Code already used. Please ask the front desk for a new code. / このコードは使用済みです。受付で新しいコードをもらってください。")
                        else:
                            st.error(f"Login failed: {msg} / ログイン失敗: {msg}")
                    except Exception:
                        st.error("Login failed. Please try again. / ログインに失敗しました。もう一度お試しください。")
                else:
                    st.error("名前と言語を選択してください。 / Please enter your name and select a language.")
    elif role == "Cashier":
        password = st.text_input("パスワード / Password", type="password")
        if st.button("ログイン / Log in"):
            if password != CASHIER_PASSWORD:
                st.error("パスワードが違います。 / Incorrect password, try again.")
            else:
                # Save staff cookie for same-day quick access
                cookie_manager.set(
                    "staff",
                    f"{today_str}|Cashier|{_staff_sig(today_str, 'Cashier', CASHIER_PASSWORD)}",
                    expires_at=datetime.datetime.now() + datetime.timedelta(days=COOKIE_TTL_DAYS),
                )
                st.session_state.role = role
                st.session_state.name = "Cashier"
                st.session_state.skip_auto_restore = False
                st.rerun()
    else:
        password = st.text_input("パスワード / Password", type="password")
        if st.button("ログイン / Log in"):
            if password != ADMIN_PASSWORD:
                st.error("パスワードが違います。 / Incorrect password, try again.")
            else:
                # Save staff cookie for same-day quick access
                cookie_manager.set(
                    "staff",
                    f"{today_str}|Admin|{_staff_sig(today_str, 'Admin', ADMIN_PASSWORD)}",
                    expires_at=datetime.datetime.now() + datetime.timedelta(days=COOKIE_TTL_DAYS),
                )
                st.session_state.role = role
                st.session_state.name = "Admin"
                st.session_state.skip_auto_restore = False
                st.rerun()


def logout():
    # Logout: reset session state only; keep cookie for same-day quick restore.
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

cashier = st.Page(
    "admin/cashier.py",
    title="Login Code / QR",
    icon=":material/payments:",
    default=(role == "Cashier"),
)
cashier_manage = st.Page(
    "admin/cashier_manage.py",
    title="Front Desk Tools",
    icon=":material/group:",
)
# admin_test_page = st.Page(
#     "admin/test.py", 
#     title="Test Page", 
#     icon=":material/bug_report:")


account_pages = [logout_page, settings]
participant_pages = [participant, participant_activity]
admin_pages = [admin_1, admin_2, admin_simulate]
cashier_pages = [cashier]
cashier_pages = [cashier, cashier_manage]

if st.session_state.role == "Select your role":
    st.title("ようこそ！Welcome to Auckland Japanese~English Exchange Meetup!")

page_dict = {}
if st.session_state.role == "Participant":
    page_dict["Participant"] = participant_pages
elif st.session_state.role == "Cashier":
    page_dict["Cashier"] = cashier_pages
elif st.session_state.role == "Admin":
    page_dict["Admin"] = admin_pages

if len(page_dict) > 0:
    pg = st.navigation({"Account": account_pages} | page_dict)
else:
    pg = st.navigation([st.Page(login, title="Log in")])

pg.run()
