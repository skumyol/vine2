# VinoBuzz Assignment Demo

This repo contains a backend-first wine photo verification system and a frontend demo for the assignment in [`assignment.md`](./assignment.md).

## What the demo does

- Single job mode: enter a wine manually, choose a pipeline, and run a real backend analysis.
- Batch job mode: run the full 10-SKU assignment set and return:
  - photo URL found, or `No Image`
  - confidence score per SKU
  - pass or fail verdict per SKU
- Architecture page: explains how the system answers the assignment questions and how each pipeline works.

## Pipeline options

- `voter`: OCR + VLM + joint evidence + source-trust weighted voting
- `paddle_qwen`: OpenCV prefilter + PaddleOCR + ambiguity gate + OpenRouter-hosted Qwen multimodal verification

Both pipelines record module-level confidence and aggregated final confidence.

## Backend

Main API routes:

- `GET /health`
- `POST /api/analyze`
- `POST /api/analyze/batch`
- `POST /api/ocr/tesseract`
- `POST /api/ocr/paddle`

Pipeline selection is supported with the `pipeline` query parameter:

- `POST /api/analyze?pipeline=voter`
- `POST /api/analyze?pipeline=paddle_qwen`

Run the backend:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

## Frontend

Run the frontend:

```bash
cd frontend
pnpm install
pnpm run dev
```

The frontend expects the FastAPI backend locally and shows real backend results.

## Local Dev Default

`./run_dev.sh` now starts the backend through Docker by default so Playwright runs in the containerized backend path for local development too.

Use:

```bash
./run_dev.sh
```

If you explicitly want the native local backend instead of Docker:

```bash
USE_LOCAL_BACKEND=1 ./run_dev.sh
```

Validate container Playwright directly:

```bash
./run_docker.sh build
./run_docker.sh up -d
./run_docker.sh playwright-check
```

## Evaluation

Fixture-based evaluation artifacts are written under `data/results/` and include accuracy, precision, recall, and F1.

Run backend tests:

```bash
.venv/bin/python -m pytest backend/tests -q -m 'not live'
```

Run frontend build:

```bash
cd frontend
npm run build
```
