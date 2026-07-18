import html

import streamlit as st
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh
from data.firebase_db import get_my_status, logout_user, get_event_state

ACCENT = "#e5484d"

st.markdown(
    f"""
    <style>
    /* Progress ring: an annulus cut out with a radial mask, so the centre is
       transparent and the page's own background shows through in both themes. */
    .pt-wrap {{
        position: relative;
        width: min(300px, 78vw);
        aspect-ratio: 1;
        margin: 0.6rem auto 1.1rem;
        display: flex;
        align-items: center;
        justify-content: center;
    }}
    .pt-ring {{
        position: absolute;
        inset: 0;
        border-radius: 50%;
        background: conic-gradient({ACCENT} var(--deg), rgba(128, 128, 128, 0.20) 0deg);
        -webkit-mask: radial-gradient(closest-side, transparent 72%, #000 73%);
        mask: radial-gradient(closest-side, transparent 72%, #000 73%);
    }}
    .pt-center {{
        text-align: center;
    }}
    .pt-table-no {{
        font-size: clamp(64px, 18vw, 92px);
        font-weight: 800;
        line-height: 1.05;
    }}
    .pt-label {{
        font-size: 0.82rem;
        opacity: 0.65;
    }}
    .pt-countdown {{
        margin-top: 0.35rem;
        font-size: 1.45rem;
        font-weight: 750;
        letter-spacing: 0.06em;
        font-variant-numeric: tabular-nums;
    }}
    .pt-countdown.pt-over {{
        color: {ACCENT};
    }}
    /* Name-tag mode: phone on the table as a name card. */
    .nametag {{
        text-align: center;
        padding: clamp(2rem, 9vh, 5rem) 0.5rem clamp(1.4rem, 5vh, 3rem);
    }}
    .nametag .nt-name {{
        font-size: clamp(3rem, 15vw, 6.5rem);
        font-weight: 850;
        line-height: 1.1;
        letter-spacing: 0.01em;
    }}
    .nametag .nt-lang {{
        margin-top: 0.9rem;
        font-size: clamp(1.1rem, 4vw, 1.6rem);
        opacity: 0.75;
    }}
    .nametag .nt-table {{
        display: inline-block;
        margin-top: 1.3rem;
        padding: 0.45rem 1.1rem;
        border: 1px solid rgba(128, 128, 128, 0.35);
        border-radius: 999px;
        font-size: clamp(1rem, 3.5vw, 1.3rem);
        font-weight: 700;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


def _go_to_login():
    st.session_state.role = "Select your role"
    st.rerun()


def _lang_flag(language: str) -> str:
    s = str(language)
    if "English" in s and "Japanese" in s:
        return "🇬🇧🇯🇵"
    if "Japanese" in s:
        return "🇯🇵"
    return "🇬🇧"


current_id = st.session_state.u_id
if not current_id:
    st.error("チェックインしていません。もう一度ログインしてください。 / You are not checked in. Please log in again.")
    if st.button("ログインへ / Go to Login"):
        _go_to_login()
else:
    try:
        current_participant = get_my_status(current_id)

        if current_participant.status == "Not Checked In":
            st.error("チェックインしていません。もう一度ログインしてください。 / You are not checked in. Please log in again.")
            if st.button("ログインへ / Go to Login"):
                _go_to_login()
        else:
            name = current_participant.name
            table_number = current_participant.table_number

            # Name-tag mode: fullscreen name + table, for introductions at the table.
            if st.session_state.get("nametag_mode"):
                st.markdown(
                    f"""
                    <div class="nametag">
                        <div class="nt-name">{html.escape(str(name))}</div>
                        <div class="nt-lang">{_lang_flag(current_participant.language)} {html.escape(str(current_participant.language))}</div>
                        <div class="nt-table">Table {html.escape(str(table_number)) if table_number else "-"}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button("戻る / Back", width="stretch"):
                    st.session_state.nametag_mode = False
                    st.rerun()
            else:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"👤 **{name}**")
                with col2:
                    if st.button("ログアウト / Logout", type="secondary", width="stretch"):
                        logout_user(current_id)
                        # Keep cookie for this event; skip auto-restore for this session.
                        st.session_state.skip_auto_restore = True
                        _go_to_login()

                st.divider()

                if table_number:
                    state = get_event_state()
                    started_at = state.get("round_started_at")
                    duration_min = state.get("round_duration_min") or 30
                    remaining_seconds = None
                    deg = 0
                    round_no = int(state.get("current_round") or 0)
                    status_kind = "info"
                    status_text = f"Round {round_no}: Go to your new table / 新しいテーブルへ移動"
                    if started_at:
                        try:
                            started_dt = datetime.fromisoformat(started_at)
                            if started_dt.tzinfo is None:
                                started_dt = started_dt.replace(tzinfo=pytz.timezone("Pacific/Auckland"))
                            now_dt = datetime.now(tz=started_dt.tzinfo)
                            elapsed = (now_dt - started_dt).total_seconds()
                            total = max(1, int(duration_min) * 60)
                            remaining_seconds = max(0, int(total - elapsed))
                            deg = int(remaining_seconds / total * 360)
                            if remaining_seconds > 0:
                                status_text = f"Round {round_no}: In progress / 進行中"
                            else:
                                status_kind = "warning"
                                status_text = (
                                    f"Round {round_no}: Time's up! Wait for the next round. "
                                    "/ 時間終了！次のラウンドをお待ちください。"
                                )
                        except Exception:
                            remaining_seconds = None

                    if remaining_seconds is None:
                        countdown_html = ""
                    else:
                        over = " pt-over" if remaining_seconds == 0 else ""
                        countdown_html = (
                            f'<div class="pt-countdown{over}">'
                            f"{remaining_seconds // 60}:{remaining_seconds % 60:02d}</div>"
                        )

                    st.markdown(
                        f"""
                        <div class="pt-wrap">
                            <div class="pt-ring" style="--deg: {deg}deg;"></div>
                            <div class="pt-center">
                                <div class="pt-table-no">{html.escape(str(table_number))}</div>
                                <div class="pt-label">Table / テーブル</div>
                                {countdown_html}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    if status_kind == "warning":
                        st.warning(status_text)
                    else:
                        st.info(status_text)
                else:
                    st.info(
                        "イベントはまだ開始していません。主催者が開始するまでお待ちください。"
                        "\n The event has not started yet. Please wait for the organizer to begin..."
                    )

                if st.button("🪪 名札モード / Name-tag mode", width="stretch"):
                    st.session_state.nametag_mode = True
                    st.rerun()

        # Refresh every 10 seconds to keep timer/status in sync.
        st_autorefresh(interval=10_000, key="auto_refresh")

    except ValueError:
        _go_to_login()
