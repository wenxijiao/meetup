# MeetupOps

MeetupOps is a real-time operations platform for multilingual community events. It coordinates participant check-in, one-time payment codes, balanced table assignment, event rounds, and table activities from one Streamlit application.

**Live application:** [meetup-ops.streamlit.app](https://meetup-ops.streamlit.app/)

## Demo walkthrough

The deployed application follows the same role-based workflow used during an event. Start from the normal login screen and choose a role:

| Role | Access | What to review |
| --- | --- | --- |
| Admin | Password: `123456` | Round settings, table assignment, attendance controls, and live dashboards |
| Cashier | Password: `123456` | Front-desk check-in, payment-code tools, and participant management |
| Participant | Enter any name and choose a language | Live table status and synchronized group activities |

Participant payment codes are currently disabled, so the participant workflow can be opened without coordinating with the Cashier view. Use **Log out** in the sidebar to switch roles.

## What it solves

Running a language-exchange event usually involves several disconnected tasks: front-desk check-in, payment confirmation, table allocation, round changes, and participant activities. MeetupOps gives organizers, cashiers, and participants role-specific workflows backed by the same live event state.

## Key features

- Role-based participant, cashier, and administrator experiences
- One-time payment-code issuance and redemption
- Multi-round table assignment with language-balance and repeat-meeting considerations
- Live participant status and language-distribution dashboards
- Manual check-in and table overrides for front-desk staff
- Synchronized table activities, including Undercover and Story Chain
- English and Japanese interface copy
- Automatic cleanup of expired event data

## Technology

- Python and Streamlit
- Firebase Admin SDK and Cloud Firestore
- Signed staff-session cookies
- Streamlit Community Cloud deployment

## Security

Firebase credentials and the cookie-signing secret are supplied through Streamlit Secrets or environment variables. Service-account JSON files, local secrets, generated Python caches, and environment files are excluded from Git.

The application accepts either `FIREBASE_SERVICE_ACCOUNT_JSON` or Google Application Default Credentials, which makes the same code suitable for Streamlit Community Cloud and keyless Google Cloud deployments.

The shared staff password documented above is used only for this publicly accessible project instance. A production deployment should use unique strong credentials or an identity provider.

## Local development

1. Install dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

2. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and replace the placeholders with local values.

3. Start the application:

   ```bash
   streamlit run app.py
   ```

Never commit `.streamlit/secrets.toml` or a downloaded service-account key.
