# Backend

Backend implementation for the VinoBuzz wine photo verification assignment.

## What exists now

- FastAPI app with `health`, `analyze`, `analyze/batch`, and OCR routes
- canonical request/response schemas
- CLI runner for single SKU, batch CSV runs, and evaluation
- deterministic parser, matcher, hard-fail rules, scoring, and decisioning
- retrieval backends for `fixture`, `serpapi`, and `playwright`
- selectable pipeline variants: `voter` and `paddle_qwen`
- evaluation harness that computes accuracy, precision, recall, and F1

## Run locally

Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

Run API:

```bash
uvicorn backend.app.main:app --reload
```

OCR endpoints:

```bash
curl -X POST http://127.0.0.1:8000/api/ocr/tesseract \
  -H "Content-Type: application/json" \
  -d '{"image_path":"data/fixtures/images/example.jpg"}'

curl -X POST http://127.0.0.1:8000/api/ocr/paddle \
  -H "Content-Type: application/json" \
  -d '{"image_path":"data/fixtures/images/example.jpg"}'
```

Run one SKU from CLI:

```bash
python3 -m backend.app.cli analyze \
  --wine-name "Domaine Arlaud Morey-St-Denis 'Monts Luisants' 1er Cru" \
  --vintage 2019 \
  --format 750ml \
  --region Burgundy \
  --pipeline voter
```

Run batch CSV:

```bash
python3 -m backend.app.cli batch --input data/input/test_skus.csv --output data/results/test_skus.json --pipeline paddle_qwen
```

Run evaluation:

```bash
python3 -m backend.app.cli evaluate --output data/results/evaluation.json
```

Run tests:

```bash
.venv/bin/python -m pytest backend/tests -q
```

## Notes

- Select the retriever with `VINO_RETRIEVAL_BACKEND=fixture|serpapi|playwright`.
- Select the default pipeline with `VINO_PIPELINE_NAME=voter|paddle_qwen`, or override per request.
- `SERPAPI_API_KEY` is read directly from `.env` for the SerpApi backend.
- Playwright requires the Python package plus browser install: `playwright install`.
- The fixture backend remains available so the system can be tested deterministically in this environment.
- The pipeline is wired end to end: retrieval -> OCR/VLM verification -> hard-fail -> scoring -> final verdict.
- Accuracy and F1 are measured against the labeled fixture dataset in `data/fixtures/`.
