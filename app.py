import streamlit as st
import time
import datetime
import pytz
import extra_streamlit_components as stx
from pathlib import Path
import sys
import hmac
import hashlib
from app_config import get_auth_secret

st.set_page_config(page_title="MeetupOps", page_icon="🤝", layout="wide")

# Ensure local package import works reliably under Streamlit reloader
sys.path.append(str(Path(__file__).parent))
import data  # noqa: E402, F401

from data.firebase_db import get_my_status, checkin_with_optional_payment_code, get_event_state  # noqa: E402

# Shared staff credential for this hosted instance. Firebase and cookie-signing
# credentials remain private in Streamlit Secrets.
STAFF_PASSWORD = "123456"
ADMIN_PASSWORD = STAFF_PASSWORD
CASHIER_PASSWORD = STAFF_PASSWORD
COOKIE_SIGNING_SECRET = get_auth_secret("cookie_signing_secret")

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
def _staff_sig(date_part: str, role: str, secret: str | None) -> str:
    msg = f"{date_part}|{role}".encode("utf-8")
    key = (secret or "").encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()

def _maybe_restore_staff_from_cookie():
    if not staff_cookie:
        return False
    if not COOKIE_SIGNING_SECRET:
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
        if not hmac.compare_digest(sig, _staff_sig(date_part, role_part, COOKIE_SIGNING_SECRET)):
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
COOKIE_TTL_DAYS = 2  # Covers Wed->Fri cadence without lasting too long.

ROLE_LABELS = {
    "Select your role": "役割を選択 / Select your role",
    "Participant": "参加者 / Participant",
    "Cashier": "受付 / Cashier",
    "Admin": "管理者 / Admin",
}


def render_welcome_header():
    """Render the event welcome banner shown above the normal login flow."""
    st.markdown(
        """
        <style>
        .meetup-welcome {
            position: relative;
            isolation: isolate;
            overflow: hidden;
            margin: 0.25rem 0 1.8rem;
            padding: clamp(1.8rem, 4vw, 3.4rem);
            border: 1px solid rgba(255, 255, 255, 0.18);
            border-radius: 28px;
            background:
                radial-gradient(circle at 12% 8%, rgba(255, 255, 255, 0.15), transparent 24%),
                radial-gradient(circle at 88% 92%, rgba(251, 113, 133, 0.30), transparent 30%),
                linear-gradient(135deg, #172554 0%, #312e81 48%, #9f1239 100%);
            color: #ffffff;
            box-shadow: 0 22px 55px rgba(15, 23, 42, 0.28);
        }
        .meetup-welcome::before,
        .meetup-welcome::after {
            content: "";
            position: absolute;
            z-index: -1;
            border: 1px solid rgba(255, 255, 255, 0.13);
            border-radius: 999px;
        }
        .meetup-welcome::before {
            width: 320px;
            height: 320px;
            top: -210px;
            right: -55px;
        }
        .meetup-welcome::after {
            width: 190px;
            height: 190px;
            bottom: -135px;
            left: 38%;
        }
        .welcome-layout {
            display: grid;
            grid-template-columns: minmax(0, 1fr) 210px;
            gap: clamp(1.4rem, 4vw, 3.6rem);
            align-items: center;
        }
        .welcome-kicker {
            display: inline-flex;
            align-items: center;
            gap: 0.55rem;
            margin-bottom: 1.15rem;
            font-size: 0.76rem;
            font-weight: 750;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            color: rgba(255, 255, 255, 0.76);
        }
        .welcome-kicker::before {
            content: "";
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #fda4af;
            box-shadow: 0 0 0 5px rgba(253, 164, 175, 0.16);
        }
        .welcome-japanese {
            margin: 0;
            font-size: clamp(3.1rem, 7vw, 5.7rem);
            font-weight: 850;
            letter-spacing: -0.055em;
            line-height: 0.95;
            text-shadow: 0 3px 18px rgba(15, 23, 42, 0.22);
        }
        .welcome-english {
            margin: 0.65rem 0 0;
            font-size: clamp(1.05rem, 2.2vw, 1.55rem);
            font-weight: 520;
            letter-spacing: 0.015em;
            color: rgba(255, 255, 255, 0.88);
        }
        .exchange-name {
            display: flex;
            flex-wrap: wrap;
            align-items: baseline;
            gap: 0.35rem 0.7rem;
            margin-top: 1.35rem;
            font-size: clamp(1.05rem, 2vw, 1.35rem);
            font-weight: 760;
        }
        .exchange-name .exchange-x {
            color: #fda4af;
            font-size: 1.15em;
        }
        .exchange-name .exchange-meetup {
            width: 100%;
            font-size: 0.78rem;
            font-weight: 650;
            letter-spacing: 0.17em;
            text-transform: uppercase;
            color: rgba(255, 255, 255, 0.62);
        }
        .welcome-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-top: 1.45rem;
        }
        .welcome-tag {
            padding: 0.36rem 0.72rem;
            border: 1px solid rgba(255, 255, 255, 0.18);
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.08);
            color: rgba(255, 255, 255, 0.80);
            font-size: 0.73rem;
            font-weight: 600;
            backdrop-filter: blur(8px);
        }
        .language-mark {
            position: relative;
            width: 190px;
            height: 190px;
            margin: auto;
            display: grid;
            grid-template-columns: 1fr 1fr;
            align-items: center;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.32);
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.10);
            box-shadow:
                inset 0 0 0 12px rgba(255, 255, 255, 0.035),
                0 18px 42px rgba(15, 23, 42, 0.25);
            backdrop-filter: blur(12px);
        }
        .language-mark::after {
            content: "";
            position: absolute;
            left: 50%;
            top: 22%;
            bottom: 22%;
            width: 1px;
            background: rgba(255, 255, 255, 0.24);
        }
        .language-mark span {
            text-align: center;
            font-size: 3.35rem;
            font-weight: 800;
            line-height: 1;
            text-shadow: 0 4px 16px rgba(15, 23, 42, 0.25);
        }
        .language-mark .mark-jp {
            font-family: "Hiragino Sans", "Yu Gothic", sans-serif;
            color: #fecdd3;
        }
        @media (max-width: 700px) {
            .meetup-welcome {
                padding: 1.7rem 1.35rem;
                border-radius: 22px;
            }
            .welcome-layout {
                grid-template-columns: 1fr;
            }
            .language-mark {
                width: 132px;
                height: 132px;
                margin: 0;
            }
            .language-mark span {
                font-size: 2.35rem;
            }
        }
        </style>

        <section class="meetup-welcome" aria-label="Auckland Japanese English Exchange">
            <div class="welcome-layout">
                <div>
                    <div class="welcome-kicker">Auckland · New Zealand</div>
                    <h1 class="welcome-japanese">ようこそ！</h1>
                    <p class="welcome-english">Welcome — come meet, talk and connect.</p>
                    <div class="exchange-name">
                        <span>Japanese</span>
                        <span class="exchange-x">×</span>
                        <span>English</span>
                        <span class="exchange-meetup">Exchange Meetup</span>
                    </div>
                    <div class="welcome-tags">
                        <span class="welcome-tag">Conversation</span>
                        <span class="welcome-tag">Community</span>
                        <span class="welcome-tag">日本語 &amp; English</span>
                    </div>
                </div>
                <div class="language-mark" aria-hidden="true">
                    <span>A</span>
                    <span class="mark-jp">あ</span>
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


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
            # Payment code requirement is controlled by Admin and disabled by default.
            try:
                state = get_event_state()
            except Exception:
                state = {}
            payment_required = bool(state.get("payment_code_required", False))
            payment_code = None
            if payment_required:
                payment_code = st.text_input(
                    "支払いコード / Payment code",
                    help="Front desk will give you a one-time code after payment.",
                )
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
            if not CASHIER_PASSWORD or not COOKIE_SIGNING_SECRET:
                st.error("Staff login is not configured. / スタッフログインが設定されていません。")
            elif not hmac.compare_digest(password, CASHIER_PASSWORD):
                st.error("パスワードが違います。 / Incorrect password, try again.")
            else:
                # Save staff cookie for same-day quick access
                cookie_manager.set(
                    "staff",
                    f"{today_str}|Cashier|{_staff_sig(today_str, 'Cashier', COOKIE_SIGNING_SECRET)}",
                    expires_at=datetime.datetime.now() + datetime.timedelta(days=COOKIE_TTL_DAYS),
                )
                st.session_state.role = role
                st.session_state.name = "Cashier"
                st.session_state.skip_auto_restore = False
                st.rerun()
    else:
        password = st.text_input("パスワード / Password", type="password")
        if st.button("ログイン / Log in"):
            if not ADMIN_PASSWORD or not COOKIE_SIGNING_SECRET:
                st.error("Staff login is not configured. / スタッフログインが設定されていません。")
            elif not hmac.compare_digest(password, ADMIN_PASSWORD):
                st.error("パスワードが違います。 / Incorrect password, try again.")
            else:
                # Save staff cookie for same-day quick access
                cookie_manager.set(
                    "staff",
                    f"{today_str}|Admin|{_staff_sig(today_str, 'Admin', COOKIE_SIGNING_SECRET)}",
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
cashier = st.Page(
    "admin/cashier.py",
    title="Login Code / QR Code",
    icon=":material/payments:",
    default=(role == "Cashier"),
)
cashier_manage = st.Page(
    "admin/cashier_manage.py",
    title="Front Desk Tools",
    icon=":material/group:",
)


account_pages = [logout_page, settings]
participant_pages = [participant, participant_activity]
admin_pages = [admin_1, admin_2]
cashier_pages = [cashier, cashier_manage]

if st.session_state.role == "Select your role":
    render_welcome_header()

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
    pg = st.navigation(
        [st.Page(login, title="ログイン / Log in", icon=":material/login:", default=True)]
    )

pg.run()
