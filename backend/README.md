# ScamShield backend

API (FastAPI), worker (radar + fetcher + engine), and the database they share. Runs in **mock mode** until the engine and radar are real: 8 demo cases are loaded into an empty database.

## Run with Docker (recommended)

From the repo root:

```bash
cp .env.example .env          # add SERPAPI_KEY when we have one
docker compose up --build     # db + api + worker (page fetching) + radar (discovery)
```

- API docs: http://localhost:8000/docs
- Postgres: `localhost:5432`, user/password/db `scamshield`
- Logs: `docker compose logs -f worker` (fetching) and `docker compose logs -f radar` (discovery)
- More fetching capacity: `docker compose up -d --scale worker=3`; user scans always run before radar finds
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
python -m app.workers.runner                  # worker (fetching + radar), in a second terminal
```

The worker needs its own packages and a browser: `pip install -r requirements-worker.txt` then `playwright install chromium` (`requirements-dev.txt` includes both sets). `.ae` WHOIS uses the `whois` command (in the Docker image).

## Test

```bash
pytest -q        # from backend/ or the repo root
```

## Scripts

| Command (from `backend/`) | What it does |
| --- | --- |
| `python -m scripts.validate_data` | Checks `data/brands.json` and `data/scam_themes.json` (run before committing them) |
| `python -m scripts.export_contract` | Rewrites `docs/api/openapi.json` + `docs/api/mock/*.json` after any API change |
| `python -m scripts.build_dataset` | Downloads phishing feeds + Tranco, crawls legit deep pages, writes `data/datasets/{train,test,test_uae_legit}.csv` (~10 min) |
| `python -m scripts.train_url_model` | Trains `models/url_model.joblib` (2 MB) and writes `models/top_domains.txt` (~1 min) |
| `python -m scripts.evaluate [--feeds] [--save]` | Scores the held-out test set; `--save` writes `eval/latest.json`, served by `GET /api/metrics` |

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
| `app/workers/fetcher.py` | **Simon** | Playwright (UAE phone profile): redirects, screenshot, text, form field kinds, remote-access/APK links |
| `app/workers/enrich.py` | **Simon** | RDAP, `.ae` WHOIS, DNS, IP → ASN + hosting + abuse contact, shared-hosting flag |
| `app/workers/radar/*.py` | **Simon** | `lookalikes`, `ct` (crt.sh), `nrd` (new domains), `search`, `maps` (+ `serp.py` helpers) |
| `app/brand_match.py` | **Simon** | Which brand a host names (used by radars and engine) |
| `app/workers/safety.py`, `pipeline.py`, `runner.py` | Agegnew | SSRF guard, job handlers, worker loop |
| `app/engine/` | Agegnew + Claude | Detection engine: `core.py` (score), `checks.py` (rules), `model.py` + `features.py` (URL model), `feeds.py` (PhishTank/OpenPhish, refreshed hourly by the worker), `lists.py` |
| `app/db.py`, `repo.py`, `jobs.py` | Agegnew | Tables, case storage, job queue |
| `app/routes/`, `api_models.py`, `auth.py` | Agegnew | HTTP API |
| `app/graph.py`, `takedown.py`, `messages.py` | Agegnew | Network graph, takedown email, EN/AR text |
| `app/mock/data.py` | Agegnew | Demo cases |
| `../data/brands.json` | **Samri** | Brand registry |
| `../data/scam_themes.json` | **Samri** | Scam types that don't copy one brand: keywords + search queries |

Try one piece on its own: `python -m app.workers.fetcher https://example.com`, `python -m app.workers.enrich https://example.com`, `python -m app.workers.radar.lookalikes tamm` (also `ct`, `nrd`, `search`, `maps`). `tests/test_discovery.py` tests them without the network; `pytest -m live` runs real-network checks.

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
