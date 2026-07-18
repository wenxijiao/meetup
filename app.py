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

COOKIE_TTL_DAYS = 2  # Covers Wed->Fri cadence without lasting too long.

ACCENT_RED = "#e5484d"  # Single accent color used across the login screen.


def render_welcome_header():
    """Render the event welcome hero shown above the login flow."""
    st.markdown(
        f"""
        <style>
        /* Keep the login screen narrow and centered even with layout="wide". */
        div[data-testid="stMainBlockContainer"],
        section.main > div.block-container {{
            max-width: 46rem;
            margin: 0 auto;
            padding-top: 2.2rem;
        }}
        .mo-hero {{
            position: relative;
            overflow: hidden;
            margin: 0 0 1.4rem;
            padding: clamp(1.9rem, 5vw, 3rem) clamp(1.4rem, 4vw, 2.6rem);
            border: 1px solid rgba(128, 128, 128, 0.25);
            border-radius: 20px;
            background: var(--secondary-background-color, rgba(128, 128, 128, 0.07));
        }}
        .mo-hero > * {{
            margin: 0;
            padding: 0;
        }}
        .mo-watermark {{
            position: absolute;
            right: -0.04em;
            bottom: -0.3em;
            font-family: "Hiragino Sans", "Yu Gothic", sans-serif;
            font-size: clamp(10rem, 30vw, 15rem);
            font-weight: 700;
            line-height: 1;
            opacity: 0.05;
            pointer-events: none;
            user-select: none;
        }}
        .mo-kicker {{
            display: flex;
            align-items: center;
            gap: 0.55rem;
            margin-bottom: 1.4rem;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.22em;
            text-transform: uppercase;
        }}
        .mo-kicker .mo-dot {{
            width: 9px;
            height: 9px;
            border-radius: 50%;
            background: {ACCENT_RED};
            flex: none;
        }}
        .mo-kicker .mo-kicker-text {{
            opacity: 0.62;
        }}
        .mo-title {{
            font-family: "Hiragino Sans", "Yu Gothic", sans-serif;
            font-size: clamp(2.7rem, 8vw, 4.2rem);
            font-weight: 800;
            letter-spacing: 0.01em;
            line-height: 1.08;
        }}
        .mo-title .mo-period {{
            color: {ACCENT_RED};
        }}
        .mo-sub {{
            margin-top: 1.05rem;
            font-size: clamp(1.1rem, 3vw, 1.45rem);
            font-weight: 700;
            letter-spacing: 0.01em;
        }}
        .mo-sub .mo-x {{
            color: {ACCENT_RED};
            padding: 0 0.12em;
        }}
        .mo-desc {{
            margin-top: 0.9rem;
            max-width: 30rem;
            font-size: 0.95rem;
            line-height: 1.7;
            opacity: 0.68;
        }}
        /* Larger tap targets + calmer look for the login tabs. */
        button[data-testid="stTab"] p {{
            font-size: 0.98rem;
            font-weight: 600;
        }}
        </style>

        <section class="mo-hero" aria-label="Auckland Japanese English Meetup">
            <div class="mo-kicker">
                <span class="mo-dot"></span>
                <span class="mo-kicker-text">Auckland · Language Exchange</span>
            </div>
            <div class="mo-title" role="heading" aria-level="1">ようこそ<span class="mo-period">。</span></div>
            <p class="mo-sub">Japanese <span class="mo-x">×</span> English Meetup</p>
            <p class="mo-desc">気軽に話して、つながりましょう。<br>Come meet, talk and connect.</p>
            <div class="mo-watermark" aria-hidden="true">あ</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


# Try staff auto-restore (must run AFTER password constants are defined).
# Cashier/Admin devices typically don't have participant uuid cookie, so do this first.
_maybe_restore_staff_from_cookie()

def _participant_checkin(name: str, language: str, payment_code: str | None):
    """Check the participant in (payment code is validated server-side when required)."""
    try:
        participant_id, final_name = checkin_with_optional_payment_code(
            current_id, name, language, payment_code
        )

        # Refresh cookie expiry to avoid unexpected expiry during the event.
        cookie_manager.set(
            "uuid",
            f"{today_str}|{participant_id}",
            expires_at=datetime.datetime.now() + datetime.timedelta(days=COOKIE_TTL_DAYS),
        )

        st.session_state.role = "Participant"
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


def _staff_login(role: str, password: str):
    """Shared Cashier/Admin login: verify password, set signed same-day cookie."""
    expected = CASHIER_PASSWORD if role == "Cashier" else ADMIN_PASSWORD
    if not expected or not COOKIE_SIGNING_SECRET:
        st.error("Staff login is not configured. / スタッフログインが設定されていません。")
    elif not hmac.compare_digest(password, expected):
        st.error("パスワードが違います。 / Incorrect password, try again.")
    else:
        # Save staff cookie for same-day quick access
        cookie_manager.set(
            "staff",
            f"{today_str}|{role}|{_staff_sig(today_str, role, COOKIE_SIGNING_SECRET)}",
            expires_at=datetime.datetime.now() + datetime.timedelta(days=COOKIE_TTL_DAYS),
        )
        st.session_state.role = role
        st.session_state.name = role
        st.session_state.skip_auto_restore = False
        st.rerun()


def login():
    tab_join, tab_staff = st.tabs(["チェックイン / Check in", "スタッフ / Staff"])

    with tab_join:
        # Payment code requirement is controlled by Admin and disabled by default.
        try:
            state = get_event_state()
        except Exception:
            state = {}
        payment_required = bool(state.get("payment_code_required", False))

        with st.form("checkin_form"):
            name = st.text_input("お名前 / Your name", placeholder="Alex / ゆき")
            language = st.radio(
                "言語 / Language",
                ["English", "Japanese"],
                horizontal=True,
                format_func=lambda v: "🇬🇧 English" if v == "English" else "🇯🇵 日本語",
            )
            payment_code = None
            if payment_required:
                payment_code = st.text_input(
                    "支払いコード / Payment code",
                    help="受付でお支払い後にコードをお渡しします。 / The front desk gives you a one-time code after payment.",
                )
            submitted = st.form_submit_button(
                "チェックイン / Check in", type="primary", width="stretch"
            )

        if submitted:
            if name.strip():
                _participant_checkin(name, language, payment_code)
            else:
                st.error("名前を入力してください。 / Please enter your name.")

    with tab_staff:
        with st.form("staff_login_form"):
            staff_role = st.radio(
                "役割 / Role",
                ["Cashier", "Admin"],
                horizontal=True,
                format_func=lambda r: "受付 / Cashier" if r == "Cashier" else "管理者 / Admin",
            )
            password = st.text_input("パスワード / Password", type="password")
            staff_submitted = st.form_submit_button("ログイン / Log in", width="stretch")

        if staff_submitted:
            _staff_login(staff_role, password)


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
    icon=":material/table_restaurant:",
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
admin_simulate = st.Page(
    "admin/simulate.py",
    title="Simulator / テスト",
    icon=":material/science:",
)
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
admin_pages = [admin_1, admin_2, admin_simulate]
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
