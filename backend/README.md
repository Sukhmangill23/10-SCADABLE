# Live SWOT backend

## Run locally

```bash
cd backend
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt   # macOS/Linux: .venv/bin/pip
cp .env.example .env   # set DATABASE_URL
uvicorn app.main:app --reload
```

Interactive docs: http://localhost:8000/docs

## Docker

```bash
docker build -t live-swot-api backend
docker run --env-file backend/.env -p 8000:8000 live-swot-api
```

The container creates any missing tables (`app.db.init_db`) and then starts
uvicorn on `$PORT` (default 8000). On Railway, set the service root directory
to `backend` and add `DATABASE_URL` and `CORS_ORIGINS` as variables.

## API

Responses use camelCase keys and string IDs to match `frontend/lib/api/types.ts`.
Errors are always `{"detail": "<message>"}`.

| Method | Path | Returns | Errors |
|---|---|---|---|
| GET | `/health` | `{"status": "ok"}` | |
| GET | `/competitors?skip=&limit=` | `CompetitorSummary[]` | 422 bad pagination |
| GET | `/competitors/{id}` | `CompetitorProfile` | 404 |
| POST | `/competitors` body `{name, dataSources[]}` | 201 `{competitor, queuedRunId}` | 409 duplicate site, 422 invalid input |
| DELETE | `/competitors/{id}` | 204 | 404 |
| POST | `/competitors/{id}/rerun` | 202 `CompetitorProfile` (status `pending`) | 404, 409 already pending/running |
| GET | `/runs?competitorId=&limit=` | `AgentRun[]` (newest first) | 422 |
| GET | `/runs/{id}` | `AgentRun` | 404 |
| GET | `/swot?competitorId=` | `SwotOverview` (one competitor's latest SWOT, or the overview without `competitorId`) | 404, 422 |
| GET | `/swot/overview` | `SwotOverview` | |
| GET | `/company` | `CompanyProfile` | |

Notes:
- Research status `completed` in the DB is returned as `success`.
- Only the first entry of `dataSources` is stored (as the website) for now.
- `trend`, `chartSeries`, `openRoles`, `costUsd` are placeholders until the
  pipeline produces that data.
- `/swot/overview` uses the overall SWOT when one exists, otherwise it combines
  each competitor's latest SWOT.

## Tests

```bash
cd backend && .venv/Scripts/python -m pytest
```
