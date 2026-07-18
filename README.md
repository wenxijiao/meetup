# MeetupOps

MeetupOps is a real-time operations platform for multilingual community events, built for a Japanese × English language-exchange meetup in Auckland. It coordinates participant check-in, one-time payment codes, language-balanced table assignment, timed rounds, and synchronized table activities — all from one Streamlit application backed by Cloud Firestore.

**Live application:** [meetup-ops.streamlit.app](https://meetup-ops.streamlit.app/)

## Try it

The login screen has two tabs:

| Role | How to log in | Password |
| --- | --- | --- |
| Participant | **チェックイン / Check in** tab — enter any name, pick a language | none |
| Admin | **スタッフ / Staff** tab — choose 管理者 / Admin | `123456` |
| Cashier | **スタッフ / Staff** tab — choose 受付 / Cashier | `123456` |

Use **ログアウト / Log out** in the sidebar to switch roles. Staff logins are remembered for the day via a signed cookie.

> The shared `123456` password exists only for this public demo instance. A production deployment should use unique strong credentials or an identity provider.

### Test it alone (Simulator)

You don't need real attendees to see the system working. Log in as **Admin** and open **Simulator / テスト**:

1. **Seed** fake checked-in participants (choose how many English/Japanese speakers)
2. Start a round and timer from **Event Operations**
3. **View as a test participant** to see the participant screen (table number, countdown) without a second device
4. **Clear test users** when you're done — only simulated users are deleted

## What it solves

Running a language-exchange night usually means juggling disconnected tasks: front-desk check-in, payment confirmation, table allocation that keeps both languages at every table, round timing, and ice-breaker activities. MeetupOps gives organizers, front-desk staff, and participants role-specific views of the same live event state.

## Features by role

**Participant**
- Check in from your phone (QR code at the front desk opens the app)
- Live table number with a round countdown ring; auto-refreshes as rounds change
- Name-tag mode: fullscreen name + table number for introductions
- Synchronized table activities (Undercover, Story Chain) — everyone at the table sees the same game

**Cashier (front desk)**
- QR code + rotating one-time login/payment codes for arrivals
- Manual check-in for participants without a device
- Participant list with table numbers

**Admin (organizer)**
- Event Operations: live status bar (round · timer · headcount), round settings, one-click round start with automatic timer, per-participant table override, manual check-in, payment-code toggle, guarded event reset
- Live Dashboard: real-time totals and per-table overview with language balance (single-language tables are flagged), force logout, participant management
- Simulator: seed/clear fake participants and impersonate them for end-to-end testing

**Engine**
- Multi-round table assignment that balances English/Japanese speakers per table and minimizes repeat meetings across rounds
- Per-day event data under `meetups/{date}` with automatic cleanup of expired events

## Technology

- Python + Streamlit (`st.navigation` multi-page app, fragments for live-updating sections)
- Firebase Admin SDK + Cloud Firestore
- HMAC-signed same-day staff cookies (`extra_streamlit_components` cookie manager)
- Streamlit Community Cloud deployment

## Project layout

```
app.py                    # entry point: login, roles, navigation
participant/              # participant table view + activities
admin/                    # event operations, dashboard, simulator, front desk
activities/               # activity registry + game implementations
data/                     # Firestore access + table-assignment logic
```

## Local development

1. Install dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

2. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in:
   - `FIREBASE_SERVICE_ACCOUNT_JSON` — a Firebase service-account key (or use Google Application Default Credentials)
   - `auth.cookie_signing_secret` — any long random string, used to sign staff cookies

3. Start the application:

   ```bash
   streamlit run app.py
   ```

## Security notes

- Firebase credentials and the cookie-signing secret are supplied through Streamlit Secrets or environment variables; nothing sensitive is committed to Git (`.streamlit/secrets.toml`, service-account JSON files, and `.env` files are ignored)
- The app accepts either `FIREBASE_SERVICE_ACCOUNT_JSON` or Application Default Credentials, so the same code runs on Streamlit Community Cloud and keyless Google Cloud deployments
- Staff sessions use HMAC-SHA256-signed cookies scoped to the current day
