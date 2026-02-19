import pandas as pd
import streamlit as st


def _lang_text(lang) -> str:
    return ", ".join(lang) if isinstance(lang, list) else str(lang)


def _table_sort_key(table_no) -> tuple:
    """
    Sort tables numerically when possible, else push to end.
    """
    if table_no is None or table_no == "-":
        return (1, 10**9)
    try:
        return (0, int(str(table_no)))
    except Exception:
        return (0, 10**9)


def render_manual_added_section(participants, active_participants):
    """
    Shows participants added manually by Admin/Cashier (no-device check-in).
    Requires records created after we started tagging them with created_source='manual'.
    """
    manual_all = [p for p in (participants or []) if str(getattr(p, "created_source", "")) == "manual"]
    manual_active = [p for p in (active_participants or []) if str(getattr(p, "created_source", "")) == "manual"]

    if not manual_all:
        st.caption("Manual check-ins: none (or older records not tagged yet). / 手動チェックイン: なし（または過去分は未タグ付け）")
        return

    st.subheader("🧍 Manual Check-ins (No Device) / 手動チェックイン（スマホなし）")
    col_a, col_b, col_c = st.columns([0.48, 0.26, 0.26], vertical_alignment="center")
    with col_a:
        only_checked_in = st.checkbox(
            "Only show checked-in manual users / チェックイン中のみ",
            value=True,
            key="manual_only_checked_in",
        )
    with col_b:
        query = st.text_input("Search name / 名前検索", value="", key="manual_search")
    with col_c:
        st.caption(f"Manual: active={len(manual_active)} total={len(manual_all)}")

    rows = manual_active if only_checked_in else manual_all
    if query.strip():
        q = query.strip().lower()
        rows = [p for p in rows if q in str(p.name).lower()]

    # Sort by table number then name
    rows = sorted(rows, key=lambda p: (_table_sort_key(p.table_number), str(p.name)))

    data = []
    for p in rows:
        data.append(
            {
                "Name": p.name,
                "Languages": _lang_text(p.language),
                "Current Table": p.table_number if p.table_number else "-",
                "Status": p.status,
                "Added By": getattr(p, "created_by_role", None) or "-",
                "Check-in Time": getattr(p, "check_in_time", None) or "-",
            }
        )

    if not data:
        st.info("No manual users match the current filter. / 条件に一致する手動ユーザーはいません。")
        return

    df = pd.DataFrame(data)
    st.dataframe(df, width="stretch", hide_index=True)


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
                "Languages": _lang_text(p.language),
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

