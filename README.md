# SplitSmart

Snap a restaurant bill, tick who had what, and SplitSmart works out exactly what everyone owes.

- **Frontend:** React + Vite (`frontend/`)
- **Backend:** Flask JSON API (`backend/`, Vercel entry in `api/index.py`)
- **Database:** PostgreSQL (SQLAlchemy). Falls back to a local SQLite file if `DATABASE_URL` is not set.
- **OCR:** Google Gemini reads the bill photo

## How the split works

- An item ticked for some people is divided equally between them.
- An item ticked for nobody is shared by everyone.
- Taxes, service charge and round off (minus any discount) are split **equally** between everyone.
- Maths is done in paise, so the shares always add up to the bill total exactly.

The logic is in `backend/split.py` and covered by `tests/`.

## Run locally

```bash
# database: local Postgres in Docker on port 5433 (set POSTGRES_PASSWORD and DATABASE_URL in .env first)
docker compose up -d

# backend
python -m venv .venv
.venv\Scripts\activate          # Windows (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt pytest
copy .env.example .env          # then fill in GEMINI_API_KEY (DATABASE_URL optional)
flask --app backend.app:create_app run --port 5000

# frontend (second terminal)
cd frontend
npm install
npm run dev                     # http://localhost:5173 (proxies /api to :5000)
```

Run the tests with `pytest` (uses SQLite). To run them on Postgres, create a `splitsmart_test`
database and set `TEST_DATABASE_URL` to it. Its tables are wiped on every run.

## Deploy to Vercel

1. Create a free Postgres database on [Neon](https://neon.tech) (or Vercel > Storage > Postgres) and copy its connection string.
2. Import this repo in Vercel. `vercel.json` already sets the build, output folder and `/api` routing.
3. In Project Settings > Environment Variables add:
   - `DATABASE_URL` - the Postgres connection string
   - `SECRET_KEY` - a long random string (`python -c "import secrets; print(secrets.token_hex(32))"`)
   - `GEMINI_API_KEY` - from https://aistudio.google.com/apikey
4. Deploy. Tables are created automatically on first request.

Bill photos are sent to Gemini and not stored, because Vercel has no permanent disk.
