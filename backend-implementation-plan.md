# Backend-Only Implementation Plan

## Objective

Build a backend-only wine photo sourcing and verification pipeline for the VinoBuzz assignment that can process the 10 test SKUs and return:

- selected photo URL or `No Image`
- confidence score
- PASS / FAIL verdict
- rejection reason or evidence summary

The system should optimize for precision over recall. A wrong image is worse than no image.

---

## Scope

### In scope for v1

- backend service plus CLI/script entrypoint
- single-SKU analysis pipeline
- batch runner for the 10 assignment SKUs
- candidate retrieval from the web
- image download and deduplication
- image quality screening
- OCR-based field verification
- hard fail rules
- confidence scoring for surviving candidates
- JSON/CSV result export for submission/demo
- logs and evidence artifacts for write-up

### Out of scope for v1

- frontend UI
- persistent database
- auth
- async job queue
- distributed processing
- advanced dashboard/debug UI
- full production hardening for 4,000 SKUs

### Optional only if needed after baseline works

- vision LLM escalation for ambiguous survivors
- richer source trust heuristics
- reverse image lookup
- label embedding similarity

---

## Assignment-Aligned Product Decision

The canonical architecture is:

1. retrieval
2. quality gating
3. OCR extraction
4. deterministic field matching
5. hard fail evaluation
6. confidence scoring on survivors only
7. final decision: best verified image or `No Image`

This replaces the earlier "parallel voter" concept as the primary implementation model.

Reason:

- it is easier to implement correctly inside the assignment window
- it is easier to explain in the write-up
- it is safer for near-duplicate Burgundy wines
- it supports a clean optional escalation path later

If a VLM is added, it should be an ambiguity resolver after deterministic verification, not the core decision engine.

---

## Success Criteria

### Must-have

- every test SKU produces one final outcome
- no accepted image violates producer/appellation/vineyard/vintage hard-fail rules
- `No Image` is returned when verification is insufficient
- results are exportable in submission-ready format

### Strong target

- at least 9 of 10 final outcomes are correct by assignment standards
- pipeline runtime is practical for a 10-SKU batch
- each decision includes enough evidence to defend in the write-up

### Evidence per SKU

- input SKU fields
- query variants used
- candidate URLs considered
- top candidate metrics
- OCR text excerpts
- field-level match table
- hard-fail reason or score breakdown
- final verdict and confidence

---

## Canonical Output Contract

Each SKU should produce a result object shaped roughly like:

```json
{
  "sku_id": "optional-local-id",
  "input": {
    "wine_name": "Domaine Arlaud Morey-St-Denis Monts Luisants 1er Cru",
    "vintage": "2019",
    "format": "750ml",
    "region": "Burgundy"
  },
  "parsed_identity": {
    "producer": "Domaine Arlaud",
    "appellation": "Morey-Saint-Denis",
    "vineyard_or_cuvee": "Monts Luisants",
    "classification": "1er Cru",
    "vintage": "2019",
    "format": "750ml",
    "region": "Burgundy"
  },
  "verdict": "PASS",
  "confidence": 0.93,
  "selected_image_url": "https://...",
  "selected_source_page": "https://...",
  "reason": "All mandatory identity fields verified; vintage visible and matched.",
  "field_matches": {
    "producer": {"status": "match", "confidence": 0.99},
    "appellation": {"status": "match", "confidence": 0.95},
    "vineyard_or_cuvee": {"status": "match", "confidence": 0.96},
    "classification": {"status": "match_if_visible", "confidence": 0.74},
    "vintage": {"status": "match", "confidence": 0.92}
  },
  "debug": {
    "queries": [],
    "candidates_considered": 0,
    "hard_fail_reasons": [],
    "ocr_snippets": [],
    "score_breakdown": {}
  }
}
```

Allowed verdicts:

- `PASS`
- `NO_IMAGE`
- `ERROR`

Avoid a separate `FAIL` final verdict unless the assignment explicitly needs it. For the demo, `NO_IMAGE` is the correct negative business outcome.

---

## Technical Architecture

### 1. Input and parsing

Responsibilities:

- accept raw wine name, vintage, format, region
- normalize accents, punctuation, hyphens, abbreviations
- parse identity fields needed for verification

Critical rules:

- normalize `Saint` and `St`
- normalize `Premier Cru` and `1er Cru`
- preserve vineyard/cuvee tokens as high-importance identity fields
- treat vintage as exact when visible

### 2. Query generation

Generate a small, intentional query set per SKU:

- exact wine name + vintage
- producer + appellation + vineyard/cuvee + vintage
- producer + appellation + bottle
- relaxed no-accent variant
- quoted exact-name variant

Do not generate dozens of weak variants. Keep recall broad enough for rare wines but candidate volume manageable.

Target:

- 4 to 8 queries per SKU

### 3. Retrieval

Initial retrieval strategy:

- search engine result pages via Playwright or a search API if available
- fetch candidate source pages
- collect likely product image URLs from those pages

Preferred source classes:

- producer websites
- merchants
- importers/distributors
- auction/archive pages

General rules:

- keep source page URL with every image
- dedupe by normalized URL first
- dedupe downloaded images by content hash and perceptual hash

Candidate budget:

- max 15 source pages per SKU
- max 3 image candidates per page
- max 25 downloaded candidates per SKU after dedupe

This budget is enough for the assignment while keeping runtime bounded.

### 4. Image quality gating

Reject obvious bad candidates early using deterministic heuristics.

Minimum checks:

- image dimensions above threshold
- blur score
- glare/overexposure score
- background clutter heuristic
- bottle count heuristic
- label-size heuristic
- watermark/text-overlay suspicion

Decision:

- if an image clearly violates marketplace style, reject before OCR

### 5. OCR and crop strategy

For each surviving candidate:

- detect bottle region if possible
- generate three OCR inputs:
  - full image
  - bottle crop
  - central/main label crop
- run OCR on all crops
- merge OCR text into one normalized text blob plus per-crop evidence

Baseline OCR stack:

- Tesseract and/or EasyOCR

Optional later:

- higher-accuracy OCR fallback for hard cases

### 6. Deterministic matching

Field-level matching order:

1. producer
2. appellation
3. vineyard/cuvee
4. classification/cru
5. vintage

Matching policy:

- producer must match
- appellation must match
- vineyard/cuvee must match if SKU includes one
- classification should match if visible
- visible vintage mismatch is an immediate fail

Important:

- absence of unreadable vintage is not a mismatch
- presence of a conflicting vintage is a mismatch
- similarity must never override explicit field conflict

### 7. Hard fail rules

Immediately reject a candidate if any of these occur:

- producer mismatch
- appellation mismatch
- vineyard/cuvee mismatch or missing when required and OCR is otherwise readable
- visible conflicting cru/classification
- visible vintage mismatch
- label unreadable enough that core identity cannot be safely verified
- clear image-quality failure

These rules are the trust boundary of the system.

### 8. Confidence scoring

Score only candidates that survive hard-fail checks.

Suggested weights:

- producer: 0.25
- appellation: 0.20
- vineyard/cuvee: 0.20
- classification/cru: 0.10
- vintage: 0.10
- OCR clarity: 0.05
- image quality: 0.05
- source trust: 0.05

Rules:

- weights can be tuned, but mandatory identity fields should dominate
- score is for ranking eligible candidates, not rescuing failed ones
- if top candidate score is below acceptance threshold, return `No Image`

Initial acceptance threshold:

- `0.85`

Tuning note:

- this threshold should be adjusted against the 10-SKU set only after hard-fail behavior looks correct

### 9. Final decision

Decision ladder:

1. if no candidates survive hard-fail rules -> `NO_IMAGE`
2. if top survivor confidence < threshold -> `NO_IMAGE`
3. if top two survivors are too close and conflict is unresolved -> `NO_IMAGE`
4. otherwise return top survivor as `PASS`

Tie-safety rule:

- if uncertainty remains between near-duplicates, prefer `NO_IMAGE`

---

## Delivery Shape

The implementation should support two ways to run:

### API mode

- `POST /api/analyze`
- `POST /api/analyze/batch`
- `GET /api/health`

### CLI mode

- run one SKU from command line
- run batch CSV for the 10 assignment wines
- export JSON and CSV results

CLI mode matters because it is the fastest way to demo the assignment without a frontend.

---

## Proposed Repository Structure

```text
backend/
  app/
    api/
    core/
    models/
    services/
    utils/
  tests/
data/
  input/
  cache/
  images/
  results/
scripts/
```

Core modules:

- `parser.py`
- `query_builder.py`
- `retriever.py`
- `downloader.py`
- `opencv_filter.py`
- `label_cropper.py`
- `ocr_service.py`
- `matcher.py`
- `hard_fail_rules.py`
- `scorer.py`
- `decision_engine.py`
- `pipeline.py`

Utility modules:

- `text_normalize.py`
- `image_hash.py`
- `csv_io.py`

---

## Implementation Phases

## Phase 0: Lock the spec

Duration:

- half day

Deliverables:

- final verdict enum
- result schema
- hard fail enum list
- confidence formula
- candidate budget constants

Acceptance criteria:

- no core behavior is still "to be decided"

## Phase 1: Backend skeleton

Duration:

- half day

Tasks:

- FastAPI app
- health route
- analyze route
- batch route
- Pydantic request/response schemas
- CLI runner

Acceptance criteria:

- can submit a stub SKU and receive a typed response
- batch runner can read CSV and emit placeholder output

## Phase 2: Identity layer

Duration:

- 1 day

Tasks:

- text normalization
- SKU parser
- field model definitions
- matcher skeleton
- hard fail rule engine

Acceptance criteria:

- parser/matcher tests pass
- obvious near-miss wines are rejected in unit tests

This is the highest-leverage phase.

## Phase 3: Retrieval v1

Duration:

- 1 day

Tasks:

- query generation
- search flow
- source page scraping
- image URL extraction
- download and dedupe

Acceptance criteria:

- each test SKU can gather a non-trivial candidate set
- candidate metadata is stored to disk for inspection

## Phase 4: Image quality + OCR v1

Duration:

- 1 day

Tasks:

- image quality heuristics
- crop generation
- OCR execution
- OCR evidence capture

Acceptance criteria:

- obviously bad images are rejected
- OCR text is captured for at least some viable candidates on the 10-SKU set

## Phase 5: End-to-end decisioning

Duration:

- 1 day

Tasks:

- integrate retrieval, gating, OCR, matching, and scoring
- rank survivors
- return final verdict
- export JSON and CSV

Acceptance criteria:

- batch run completes on all 10 SKUs
- every SKU has a defended final outcome

## Phase 6: Evaluation and tuning

Duration:

- half to one day

Tasks:

- review false positives first
- tighten hard-fail behavior
- tune acceptance threshold
- improve query variants for misses
- add optional ambiguity resolver only if truly needed

Acceptance criteria:

- final result set is stable
- evidence is clean enough for submission write-up

---

## Testing Strategy

### Unit tests

- text normalization
- parser
- matcher
- hard fail rules
- scorer

### Fixture tests

Curate a small set of local images that cover:

- correct wine
- wrong producer with similar name
- correct producer wrong vineyard
- correct producer wrong vintage
- lifestyle shot
- watermarked image
- blurry image

### Pipeline tests

- one easy SKU
- one medium SKU
- one Burgundy hard SKU

### Batch evaluation

- run all 10 test SKUs
- record outcome matrix:
  - accepted and correct
  - accepted and wrong
  - no image but acceptable
  - error

The number to fear most is "accepted and wrong." Optimize against that first.

---

## Risks and Mitigations

### Risk 1: Retrieval finds many wrong but plausible bottles

Mitigation:

- keep field-level hard fails strict
- store source page text and domain
- do not rely on page title alone

### Risk 2: OCR is too weak on angled or low-res labels

Mitigation:

- multiple crops
- image enhancement before OCR
- fallback to `No Image`
- optional later escalation to better OCR/VLM

### Risk 3: Burgundy near-duplicates produce false positives

Mitigation:

- make vineyard/cuvee a mandatory field when present
- treat conflicting visible cru/vineyard text as immediate reject
- prefer `No Image`

### Risk 4: Runtime becomes too slow

Mitigation:

- cap candidate counts
- dedupe aggressively
- gate low-quality images before OCR

### Risk 5: The 10-SKU set exposes too many ambiguous edge cases

Mitigation:

- add an optional ambiguity resolver only after deterministic core works
- keep the write-up honest about `No Image` as trust-preserving behavior

---

## Recommended Execution Order

Build in this exact order:

1. output schema and constants
2. FastAPI skeleton and CLI runner
3. text normalizer
4. SKU parser
5. matcher
6. hard fail rules
7. query builder
8. retriever
9. downloader and dedupe
10. image quality gate
11. OCR service
12. scorer
13. decision engine
14. batch runner and export
15. tuning on the 10 assignment SKUs

Do not start with OCR model shopping or VLM experiments. The core trust logic comes first.

---

## Submission Plan

The final submission package should include:

- backend code
- sample batch input for the 10 SKUs
- JSON and CSV outputs
- short run instructions
- write-up with:
  - architecture
  - verification logic
  - hard-fail philosophy
  - main failure modes
  - runtime notes
  - total time spent

For the write-up, explicitly frame the system as "verification-first" and explain why `No Image` is a correct result when trust is insufficient.

---

## Next Step

The immediate next build step is:

1. create the backend skeleton and result schema
2. implement normalization, parser, matcher, and hard fail rules
3. only then wire retrieval

That sequence gives you a defendable core before you touch the noisiest part of the problem.
