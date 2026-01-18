import pandas as pd
import streamlit as st


def render_participant_list_table(
    participants,
    active_participants,
    *,
    default_only_checked_in: bool = False,
):
    """
    Reusable Participant List table (same columns/format as admin/admin_2.py).
    """
    st.subheader("📋 Participant List / 参加者一覧")
    only_checked_in = st.checkbox(
        "Only Show Checked-In Participants / チェックインのみ表示",
        value=bool(default_only_checked_in),
    )

    participants_list = active_participants if only_checked_in else participants

    if not participants_list:
        st.info("No data available yet. / まだデータがありません。")
        return

    data = []
    for p in participants_list:
        data.append(
            {
                "Name": p.name,
                "Languages": ", ".join(p.language) if isinstance(p.language, list) else str(p.language),
                "Current Table": p.table_number if p.table_number else "-",
                "Status": p.status,
            }
        )

    df = pd.DataFrame(data)
    st.dataframe(
        df,
        width="stretch",
        hide_index=True,
        column_config={
            "Status": st.column_config.TextColumn("Status"),
        },
    )

