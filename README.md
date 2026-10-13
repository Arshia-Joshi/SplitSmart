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

