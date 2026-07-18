import html
import time

import streamlit as st
from data.firebase_db import get_all_participants, logout_user, get_active_participants
from admin.participant_list_component import render_participant_list_table, render_manual_added_section

ACCENT = "#e5484d"

st.markdown(
    f"""
    <style>
    .tbl-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
        gap: 0.7rem;
        margin-top: 0.4rem;
    }}
    .tbl-card {{
        border: 1px solid rgba(128, 128, 128, 0.25);
        border-radius: 14px;
        padding: 0.7rem 0.85rem;
        background: var(--secondary-background-color, rgba(128, 128, 128, 0.06));
    }}
    .tbl-card.tbl-unbalanced {{
        border-left: 4px solid {ACCENT};
    }}
    .tbl-head {{
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        margin-bottom: 0.35rem;
    }}
    .tbl-no {{
        font-weight: 800;
        font-size: 1.02rem;
    }}
    .tbl-mix {{
        font-size: 0.78rem;
        opacity: 0.75;
    }}
    .tbl-member {{
        font-size: 0.85rem;
        line-height: 1.5;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .tbl-flag-note {{
        font-size: 0.74rem;
        font-weight: 700;
        color: {ACCENT};
        margin-top: 0.3rem;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📊 Live Data Dashboard / ダッシュボード")
st.caption("Real-time monitoring of participants and stats. / 参加者と統計をリアルタイム表示。")


def _flag(language) -> str:
    s = str(language)
    if "English" in s and "Japanese" in s:
        return "🇬🇧🇯🇵"
    if "Japanese" in s:
        return "🇯🇵"
    return "🇬🇧"


@st.fragment(run_every=10)
def render_live_overview():
    """Metrics + per-table overview. Auto-refreshes without touching the widgets below."""
    active = get_active_participants()
    total_count = len(active)
    en_count = sum(1 for p in active if "English" in str(p.language))
    jp_count = sum(1 for p in active if "Japanese" in str(p.language))

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Participants", total_count)
    with col2:
        st.metric("🇬🇧 English Speakers", en_count)
    with col3:
        st.metric("🇯🇵 Japanese Speakers", jp_count)

    tables: dict[str, list] = {}
    waiting = []
    for p in active:
        if p.table_number:
            tables.setdefault(str(p.table_number), []).append(p)
        else:
            waiting.append(p)

    if tables:
        st.subheader("🪑 Tables / テーブル")
        st.caption(
            "Red border = single-language table (rebalance suggestion). "
            "/ 赤枠は片方の言語のみのテーブルです。"
        )

        def _sort_key(t):
            try:
                return int(t)
            except Exception:
                return 10**9

        cards = []
        for tno in sorted(tables.keys(), key=_sort_key):
            plist = tables[tno]
            t_en = sum(1 for p in plist if "English" in str(p.language))
            t_jp = sum(1 for p in plist if "Japanese" in str(p.language))
            unbalanced = len(plist) > 1 and (t_en == 0 or t_jp == 0)
            members = "".join(
                f'<div class="tbl-member">{_flag(p.language)} {html.escape(str(p.name))}</div>'
                for p in plist
            )
            note = '<div class="tbl-flag-note">⚠️ One language only</div>' if unbalanced else ""
            cards.append(
                f'<div class="tbl-card{" tbl-unbalanced" if unbalanced else ""}">'
                f'<div class="tbl-head"><span class="tbl-no">Table {html.escape(tno)}</span>'
                f'<span class="tbl-mix">🇬🇧{t_en} 🇯🇵{t_jp}</span></div>'
                f"{members}{note}</div>"
            )
        st.markdown(f'<div class="tbl-grid">{"".join(cards)}</div>', unsafe_allow_html=True)

    if waiting:
        st.caption(
            "⏳ Not assigned yet / 未割り当て: "
            + ", ".join(html.escape(str(p.name)) for p in waiting)
        )


render_live_overview()

st.divider()

if st.button("🔄 Refresh Data"):
    st.rerun()

participants = get_all_participants()
active_participants = get_active_participants()
total_count = len(active_participants)

render_participant_list_table(participants, active_participants, default_only_checked_in=False)

st.divider()
render_manual_added_section(participants, active_participants)

if total_count > 0:
    st.divider()
    st.subheader("🚫 Manage Users (Logout)")

    active_users = active_participants

    if active_users:
        col_kick_sel, col_kick_btn = st.columns([3, 1])

        with col_kick_sel:
            user_to_kick = st.selectbox(
                "Select a user to force logout:",
                options=active_users,
                format_func=lambda p: f"{p.name} (Table: {p.table_number or '-'})"
            )

        with col_kick_btn:
            st.write("")
            st.write("")
            if st.button("Kick User 👢", type="primary"):
                if user_to_kick:
                    try:
                        logout_user(user_to_kick.id)
                        st.toast(f"User {user_to_kick.name} has been logged out!", icon="✅")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
    else:
        st.info("Everyone is currently logged out.")
