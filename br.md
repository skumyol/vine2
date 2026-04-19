# VinoBuzz Wine Photo Sourcing Pipeline — Brainstorming Results

## Session Overview

**Topic:** Automated Wine Photo Sourcing Pipeline — 90% Accuracy Challenge  
**Date:** 2026-04-18  
**Facilitator:** serkan  
**Approach:** Progressive Brainstorming (Exploration → Pattern Recognition → Development → Action Planning)

## Core Architecture Decisions

| Parameter | Decision |
|-----------|----------|
| **Voting type** | Weighted by confidence — modules with higher certainty count more |
| **Consensus threshold** | 75% (3/4 supermajority) — balanced for 90% accuracy target |
| **Module failure handling** | Degrade gracefully with retry + OpenRouter fallback — Retry once, then fallback to backup model (Qwen 3.5 VL, Gemma, etc.) |
| **Tie-breaking** | Vision LLM as tie-breaker — When weighted votes hit exactly 75%, vision model's vote gets 1.5× weight to break tie |

## Key Concepts

### 1. Ensemble Verification Pipeline
Parallel multi-signal verification with 8+ specialized verifiers: OCR, Vision Model, Metadata, Bottle Shape, Label Pattern, Vintage Era, Cross-Reference, Source Credibility, Reverse Image Check, Text Embedding, Multi-Language OCR.

Each verifier returns: `match_score`, `confidence`, `rejection_reasons`  
Weighted ensemble voter produces final confidence 0-1.

**Analogy:** Art forgery detection — multiple authentication signals running in parallel.

### 2. GPU-Progressive Architecture
- **Phase 1 (Now):** Cloud APIs for GPU-required tasks (vision models, deep OCR)
- **Phase 2 (Later):** Migrate to local open-source models (LLaVA via Ollama, RolmOCR)
- **Always local:** CPU tasks (Tesseract, EasyOCR, OpenCV quality checks)

### 3. Two-Stage OCR Hybrid (Local + API)
- **Stage 1:** Fast local OCR (Tesseract/EasyOCR) filters candidates cheaply
- **Stage 2:** GPT-4V deep verification only on survivors
- **Cost reduction:** 6.7× (20 candidates → 3 survivors)

### 4. LEGO-Block Pipeline Design
Each verifier is an independent module with standard interface:
```
input: image + wine_metadata
output: {match_score, confidence, reasoning}
```
Swap Tesseract → RolmOCR → GPT-4V without changing pipeline logic.

## Open-Source Components

### OCR Options
- **Tesseract** — CPU, established, 100+ languages
- **EasyOCR** — lightweight, multilingual
- **PaddleOCR** — GPU-accelerated
- **RolmOCR** — fine-tuned Qwen 7B, Apache-2.0, 10× faster than larger VLMs

### Vision Models (GPT-4V alternatives)
- **LLaVA / LLaVA-OneVision** — fully open, Ollama-compatible
- **Qwen2.5-VL** — Alibaba, Apache-2.0 variants
- **InternVL 2.5** — 1B-78B variants, MIT license
- **Pixtral 12B** — Mistral, strong instruction following

### Visual Similarity
- **OpenCLIP** — zero-shot classification
- **Image hash similarity** — perceptual hashing
- **FAISS** — vector search for label design matching

### Quality/Security
- **BRISQUE/NIQE** — no-reference image quality assessment
- **OpenCV** — frequency domain watermark detection
- **Stable Signature/SynthID** — AI-generated image detection

## Implementation Milestones (48-hour window)

| Milestone | Hours | Deliverable |
|-----------|-------|-------------|
| **M1** | 0-4 | Search + OCR pipeline working |
| **M2** | 4-12 | Vision verifier via OpenRouter |
| **M3** | 12-20 | Weighted voting + 75% threshold |
| **M4** | 20-30 | Test on 10 SKUs, tune thresholds |
| **M5** | 30-36 | Add negative verifier if needed |
| **M6** | 36-42 | Final polish, error handling |
| **M7** | 42-48 | Write-up + submission |

## Pipeline Architecture Diagram

```
┌──────────────────────────────────────────┐
│     MODULE VOTER (Parallel execution)    │
├──────────────────────────────────────────┤
│  OCR Verifier (EasyOCR/Tesseract)        │
│  Vision Verifier (GPT-4V via OpenRouter) │
│  Metadata Checker (source quality)       │
│  Bottle Shape Classifier                 │
│  Label Pattern Matcher (OpenCLIP)        │
│  Reverse Image Checker                   │
│  Negative Verifier (Devil's Advocate)    │
└────────────────┬─────────────────────────┘
                 │
        ┌────────▼────────┐
        │  WEIGHTED VOTE  │
        │  sum(vote × confidence) |
        │  / sum(confidence)       │
        └────────┬────────┘
                 │
           ≥ 75%? ──► ACCEPT
           < 75%? ──► REJECT
           = 75%? ──► Vision LLM tie-break (1.5× weight)
```

## Assignment Context

**VinoBuzz Requirements:**
- Current accuracy at 50% — need to reach 90%
- 4,000+ SKUs in wine marketplace
- Core problem: finding photos is easy, finding the RIGHT photo is hard
- Burgundy wines especially challenging (similar names, different climats)
- Photo standards: single bottle, upright, clean background, no watermarks, readable label
- Evaluation: 40% accuracy, 25% verification logic, 20% architecture, 15% speed

**Core Questions Answered:**
1. ✅ How do you confirm the label text matches exactly? → OCR + fuzzy matching + vision verification
2. ✅ How do you automatically filter out low quality, watermarked, or lifestyle images? → Quality filters + ensemble rejection
3. ✅ What's your confidence scoring mechanism? → Weighted voting with 75% threshold
4. ✅ What's your fallback when no verified photo can be found? → "No Image" with detailed rejection reasons
5. ✅ How do you handle wines with near-zero online photo coverage? → Graceful degradation, transparent confidence reporting
