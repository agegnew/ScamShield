# ScamShield backend

FastAPI app serving the API the UI uses. Currently in **mock mode**: realistic fake cases, same shapes as the live system.

## Run it

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open http://127.0.0.1:8000/docs. The UI at http://localhost:3000 is allowed by CORS (change with `SCAMSHIELD_CORS`).

## Test it

```bash
pytest -q
```

## Regenerate the contract files for the UI

After changing any model or mock case:

```bash
python -m scripts.export_contract
```

This rewrites `docs/api/openapi.json` and `docs/api/mock/*.json`.

## Layout

| Path | What it is |
| --- | --- |
| `app/contracts.py` | **Shared formats** — Brand, Candidate, Evidence, Verdict. Workers and engine use these |
| `app/api_models.py` | Request/response shapes for the UI |
| `app/routes/` | Endpoints: `system`, `cases`, `scan`, `citizen` |
| `app/mock/` | Fake cases + in-memory store (replaced by the database at Gate 1) |
| `app/graph.py` | Links risky cases that share IP, registration day or final host |
| `app/takedown.py` | Takedown email (EN + AR) for registrar and host |
| `app/brands.py` | Loads `data/brands.json`; official-domain and helpline lookups |
| `app/messages.py` | Citizen-checker text in English and Arabic |
| `../data/brands.json` | Brand registry (Samri owns it) |

## Settings

| Variable | Default |
| --- | --- |
| `SCAMSHIELD_MODE` | `mock` |
| `SCAMSHIELD_BRANDS` | `../data/brands.json` |
| `SCAMSHIELD_ARTIFACTS` | `backend/artifacts` (screenshots, served at `/artifacts/`) |
| `SCAMSHIELD_CORS` | `http://localhost:3000,http://127.0.0.1:3000` |
