import streamlit as st
import time
import datetime
import extra_streamlit_components as stx
from data.firebase_db import login_user, logup_user

cookie_manager = stx.CookieManager(key="meetup_app")
current_id = cookie_manager.get(cookie="uuid")

if "role" not in st.session_state:
    st.session_state.role = "Select your role"
if "started" not in st.session_state:
    st.session_state.started = False

ROLES = ["Select your role", "Participant", "Admin"]
ADMIN_PASSWORD = "123456789"

def login():
    st.header("Log in")
    role = st.selectbox("Choose your role", ROLES)

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

                        st.session_state.role = role
                        st.session_state.name = final_name
                        st.rerun()
                    else:
                        participant_id, final_name = logup_user(name, language)
                        cookie_manager.set("uuid", participant_id, expires_at=datetime.datetime.now() + datetime.timedelta(days=1))
                        time.sleep(1)

                        st.session_state.role = role
                        st.session_state.name = final_name
                        st.rerun()
                else:
                    st.error("请输入名字并选择语言")
    else:
        password = st.text_input("Password", type="password")
        if st.button("Log in"):
            if password != ADMIN_PASSWORD:
                st.error("Incorrect password, try again.")
            else:
                st.session_state.role = role
                st.session_state.name = "Admin"
                st.rerun()


def logout():
    st.session_state.role = "Select your role"
    st.rerun()


role = st.session_state.role

logout_page = st.Page(logout, title="Log out", icon=":material/logout:")
settings = st.Page("settings.py", title="Settings", icon=":material/settings:")

participant = st.Page(
    "participant/participant_1.py",
    title="Participant 1",
    icon=":material/healing:",
    default=(role == "Participant"),
)
participant_test_page = st.Page(
    "participant/test.py", 
    title="Test Page", 
    icon=":material/bug_report:")

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
admin_test_page = st.Page(
    "admin/test.py", 
    title="Test Page", 
    icon=":material/bug_report:")


account_pages = [logout_page, settings]
participant_pages = [participant, participant_test_page]
admin_pages = [admin_1, admin_2, admin_test_page]

if st.session_state.role == "Select your role":
    st.title("Welcome to Auckland Japanese/English Exchange Meetup!")

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
