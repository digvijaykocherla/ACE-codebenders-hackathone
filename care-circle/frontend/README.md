# Care Circle – Frontend

React 18 + Vite + react-router-dom. Plain CSS. No TypeScript.

The backend (FastAPI) must be running first on **http://127.0.0.1:8000**.

## Run on Windows (PowerShell or Command Prompt)

```bat
cd frontend
copy .env.example .env
npm install
npm run dev
```

Then open **http://localhost:5173** in your browser.

Vite proxies every request starting with `/api` to the backend on port 8000, so no CORS setup is needed.

## Demo accounts (SYNTHETIC data)

| Email | Password |
|---|---|
| priya@demo-family.com | Demo@1234 |
| arjun@demo-family.com | Demo@1234 |
| meera@demo-family.com | Demo@1234 |

All demo data is synthetic. The app organises care logistics only and never gives medical advice.

## Roles

- **coordinator** – full access, can manage the team.
- **caregiver** – can create and update appointments, prescriptions, reports, and tasks.
- **viewer** – read only; create and update controls are hidden.
