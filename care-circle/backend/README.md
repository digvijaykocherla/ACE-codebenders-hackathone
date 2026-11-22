# Care Circle – Backend (FastAPI)

Organises shared care information for an elderly family member: records, timeline,
tasks, refills, appointments and an activity log. It does not give medical advice.
All seed data is SYNTHETIC.

## Windows setup

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python seed.py
python -m uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs  (health check: `/api/health`)

Run tests: `python -m pytest`

## Switching to PostgreSQL
Change `DATABASE_URL` in `.env` only (and install a driver such as `psycopg`).
