# TASKDAWG backend

Python API for the TASKDAWG task manager, built with FastAPI + SQLAlchemy.
It is **not connected to the front-end yet** — `app.js` still uses `localStorage`.

## Run it

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then edit it (see below)
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for interactive API docs where you can try every endpoint.

Run the tests with `pytest`.

## Database

- **Quick start:** leave `DATABASE_URL` as the SQLite default. Tables are created automatically.
- **PostgreSQL** (what `../schema.sql` is written for): set
  `DATABASE_URL=postgresql://user:password@localhost:5432/taskdawg`.
  If you create the tables from `schema.sql` yourself, also run `schema_additions.sql`
  (adds `category`, `position` and the `contact_messages` table), and set `AUTO_CREATE_TABLES=false`.

## Endpoints

All task routes need the header `Authorization: Bearer <access_token>`.

| Method | Path | What it does |
|---|---|---|
| POST | `/api/auth/register` | Create account `{name, email, password}`; returns a token |
| POST | `/api/auth/login` | Log in `{email, password}`; returns a token |
| GET | `/api/auth/me` | The logged-in user |
| GET | `/api/tasks?filter=all\|pending\|in_progress\|completed` | List your tasks (`pending` = not completed, like the To Do filter) |
| POST | `/api/tasks` | Create `{title, priority?, due_date?, category?, description?, status?}` |
| GET | `/api/tasks/{id}` | One task |
| PATCH | `/api/tasks/{id}` | Change any of the fields above (send only what changed) |
| DELETE | `/api/tasks/{id}` | Delete |
| GET | `/api/tasks/stats` | `{total, pending, in_progress, completed, overdue}` for the counters |
| POST | `/api/tasks/reorder` | Save drag-and-drop order `{ids: [...]}` top to bottom |
| POST | `/api/contact` | Contact form `{name, email, subject, message}` |
| GET | `/api/health` | Liveness check |

## Notes for when you connect the front-end

- **Field names:** the API uses `due_date` (snake_case); `app.js` currently uses `dueDate`.
- **Priority:** the form's `Normal / High / Low` are accepted in any letter case; `Normal` is stored as `medium`.
- **Due date:** send `YYYY-MM-DD` (or `""` / `null` to clear). It comes back as a full UTC timestamp, so
  `app.js` should show just the date part.
- **Task ids** are numbers from the database; `app.js` currently compares them as strings.
- **Token storage** is up to the front-end (e.g. `localStorage`); send it on every task request.
- Set `CORS_ORIGINS` to wherever the front-end is served from.

## Not included yet

Login rate limiting, password reset / email verification, and token refresh.
