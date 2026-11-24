# ScamShield backend

API (FastAPI), worker (radar + fetcher + engine), and the database they share. Runs in **mock mode** until the engine and radar are real: 8 demo cases are loaded into an empty database.

## Run with Docker (recommended)

From the repo root:

```bash
cp .env.example .env          # add SERPAPI_KEY when we have one
docker compose up --build     # db + api + worker
```

- API docs: http://localhost:8000/docs
- Postgres: `localhost:5432`, user/password/db `scamshield`
- Logs: `docker compose logs -f worker`
- Code in `backend/app/` is mounted into both containers. The API reloads by itself; after changing worker code run `docker compose restart worker`.
- Reset the database: `docker compose down -v`

## Run without Docker

Uses a local SQLite file (`backend/scamshield.db`), no Postgres needed.

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000     # API
python -m app.workers.runner                  # worker, in a second terminal
```

The worker needs Playwright only once Simon's fetcher uses it: `pip install -r requirements-worker.txt` then `playwright install chromium`.

## Test

```bash
pytest -q        # from backend/ or the repo root
```

## Scripts

| Command (from `backend/`) | What it does |
| --- | --- |
| `python -m scripts.validate_data` | Checks `data/brands.json` and `data/scam_themes.json` (run before committing them) |
| `python -m scripts.export_contract` | Rewrites `docs/api/openapi.json` + `docs/api/mock/*.json` after any API change |

After `export_contract`, regenerate the UI types from the repo root:
`npx openapi-typescript docs/api/openapi.json -o docs/api/scamshield-api.d.ts`

## How a URL flows

1. A **radar source** (`app/workers/radar/`) or `POST /api/scan` creates a case with a URL-only verdict.
2. A `fetch` job is queued in the `jobs` table.
3. The **worker** claims it, checks the URL is public (`safety.py`), runs `fetcher.fetch()` then `enrich.enrich()`.
4. `engine.score()` turns URL + evidence into a Verdict, saved on the case.
5. The UI reads it through the API.

## Who owns what

| Path | Owner | What it is |
| --- | --- | --- |
| `app/contracts.py` | everyone (ask first) | Shared formats: Brand, Candidate, Evidence, Verdict |
| `app/workers/fetcher.py` | **Simon** | Playwright: redirects, screenshot, text, forms |
| `app/workers/enrich.py` | **Simon** | RDAP/WHOIS, DNS, IP → ASN + hosting |
| `app/workers/radar/*.py` | **Simon** | Lookalikes, crt.sh, Google Search, Google Maps |
| `app/workers/safety.py`, `pipeline.py`, `runner.py` | Agegnew | SSRF guard, job handlers, worker loop |
| `app/engine/` | Agegnew + Claude | Detection engine |
| `app/db.py`, `repo.py`, `jobs.py` | Agegnew | Tables, case storage, job queue |
| `app/routes/`, `api_models.py`, `auth.py` | Agegnew | HTTP API |
| `app/graph.py`, `takedown.py`, `messages.py` | Agegnew | Network graph, takedown email, EN/AR text |
| `app/mock/data.py` | Agegnew | Demo cases |
| `../data/brands.json` | **Samri** | Brand registry |
| `../data/scam_themes.json` | **Samri** | Scam types that don't copy one brand: keywords + search queries |

Each of Simon's files starts with a docstring that says exactly what to build. `tests/test_worker.py` shows how to test a source or the fetcher without the network.

## Settings

| Variable | Default |
| --- | --- |
| `SCAMSHIELD_MODE` | `mock` |
| `DATABASE_URL` | SQLite at `backend/scamshield.db` (Postgres in Docker) |
| `SCAMSHIELD_SEED_MOCK` | `1` in mock mode — loads demo cases into an empty DB |
| `SCAMSHIELD_BRANDS` | `../data/brands.json` |
| `SCAMSHIELD_ARTIFACTS` | `backend/artifacts` (screenshots, served at `/artifacts/`) |
| `SCAMSHIELD_CORS` | `http://localhost:3000,http://127.0.0.1:3000` |
| `SCAMSHIELD_WORKER_POLL` | `2` seconds between empty-queue checks |
| `SERPAPI_KEY` | empty — Search and Maps radar stay off |
