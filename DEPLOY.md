# Deployment

## Quick Start

```bash
cp .env.example .env          # Fill in OPENROUTER_API_KEY
./run_prod.sh                 # Build and start all services
```

Services:
- **Frontend**: http://localhost:3042
- **Backend API**: http://localhost:8042/api/health
- **Playwright service**: http://localhost:8043/health

## Architecture

Three containers orchestrated by `docker-compose.yml`:

| Service     | Image base                                     | Port (host) | Role                                    |
|-------------|-------------------------------------------------|-------------|-----------------------------------------|
| `frontend`  | `nginx:alpine` (multi-stage)                    | 3042        | Serves built React SPA                  |
| `backend`   | `python:3.11-slim`                              | 8042        | FastAPI pipeline (OCR + VLM + voters)   |
| `playwright`| `mcr.microsoft.com/playwright:v1.50.0-noble`    | 8043        | Live retrieval: HTTP search + browser   |

Backend → Playwright: internal `http://playwright:8000`
Frontend → Backend: via nginx proxy (see `nginx.conf`)

## Environment Variables

Required in `.env`:
- `OPENROUTER_API_KEY` — for VLM reasoning

Optional overrides:
- `VINO_RETRIEVAL_BACKEND` — `playwright` (default in prod), `fixture`, `serpapi`, `hybrid`
- `VINO_PIPELINE_NAME` — `voter` (default) or `paddle_qwen`
- `VINO_CORS_ORIGINS` — comma-separated allowed origins

## Operations

```bash
./run_docker.sh build         # Rebuild all images
./run_docker.sh up -d         # Start in background
./run_docker.sh logs -f       # Tail logs
./run_docker.sh down          # Stop and remove containers
./run_docker.sh shell         # Shell into backend
./run_docker.sh test          # Run backend tests in container
./run_prod.sh --check         # Health check
```

## Search Module

The retrieval pipeline (both dev and prod) uses **HTTP-first multi-engine rotation**:

1. Try Brave Search → Startpage → Mojeek → DuckDuckGo Lite
2. Stop at first engine returning ≥ 3 results
3. Fetch each result page, extract `<img>` tags with size/alt scoring
4. Fall back to Playwright browser only if HTTP yields < 3 candidates

Config in `backend/app/core/config.py`:
- `playwright_search_url_templates` — engine rotation list
- `playwright_http_min_results` — min results per engine before rotating
- `playwright_force_http_fallback=True` — HTTP-first mode (default)

## Local Development (no Docker)

```bash
./run_dev.sh                  # Backend: uvicorn on :8000, Frontend: vite on :5173
```

Uses `.venv` Python and pnpm. Set `VINO_RETRIEVAL_BACKEND=playwright` for live retrieval.

## Security

- `.env` is git-ignored and docker-ignored — **never baked into images**
- Backend runs as non-root `appuser`
- Playwright runs as non-root `pwuser`
- Resource limits set in `docker-compose.yml` (2 vCPU / 2GB backend, 1 vCPU / 1GB playwright)

## Troubleshooting

**Playwright `browser_launch_ok=false`**
Usually a playwright Python version / Docker base image mismatch. Pin `playwright==1.50.0` in `playwright-service/requirements.txt` to match `mcr.microsoft.com/playwright:v1.50.0-noble`.

**Backend `ERROR: Playwright service call failed: timed out`**
Microservice took too long to return. Default timeout is 180s. Reduce `candidate_page_limit` or number of queries if consistently timing out.

**No candidates returned**
Search engines may be rate-limiting. The HTTP fallback rotates through 4 engines automatically. If all fail, the system returns `NO_IMAGE` verdict (valid terminal state).
