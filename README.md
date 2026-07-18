# MeetupOps

MeetupOps is a real-time operations platform for multilingual community events. It coordinates participant check-in, one-time payment codes, balanced table assignment, event rounds, and table activities from one Streamlit application.

**Live demo:** [meetup-ops.streamlit.app](https://meetup-ops.streamlit.app/)

## Recruiter quick start

Open the live demo to land on the public **Recruiter Tour**. It explains the three user roles and runs the production table-assignment algorithm on fictional data, all on one page and without a login or database write.

For a deeper walkthrough, choose **Staff / Participant Login** in the sidebar:

| Role | Demo access |
| --- | --- |
| Admin | Password: `123456` |
| Cashier | Password: `123456` |
| Participant | Enter any name and choose a language; no payment code required |

Suggested two-minute review: read the role overview, inspect the three simulated rounds, then optionally log in as Admin to see the live operations dashboard.

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
- Automatic cleanup of expired demo-event data

## Technology

- Python and Streamlit
- Firebase Admin SDK and Cloud Firestore
- Signed staff-session cookies
- Streamlit Community Cloud deployment

## Security

Firebase credentials and the cookie-signing secret are supplied through Streamlit Secrets or environment variables. Service-account JSON files, local secrets, generated Python caches, and environment files are excluded from Git.

The application accepts either `FIREBASE_SERVICE_ACCOUNT_JSON` or Google Application Default Credentials, which makes the same code suitable for Streamlit Community Cloud and keyless Google Cloud deployments.

The simple staff password documented above is intentionally limited to this portfolio demo. Production deployments should use unique strong credentials or an identity provider.

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
