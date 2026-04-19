import json
import base64
import urllib.parse
import urllib.request
from functools import lru_cache
from pathlib import Path

from backend.app.core import config as config_module
from backend.app.core.config import get_settings
from backend.app.core.domain_filters import (
    filter_candidates_by_domain,
    get_domain_trust_score,
    is_excluded_domain,
    is_trusted_domain,
)
from backend.app.models.candidate import Candidate
from backend.app.models.sku import AnalyzeRequest
from backend.app.services.parser import parse_identity
from backend.app.services.query_builder import build_queries
from backend.app.services.retriever_playwright import collect_candidates as collect_playwright_candidates
from backend.app.utils.text_normalize import normalize_text


@lru_cache(maxsize=1)
def _load_fixture_candidates() -> dict[str, list[dict]]:
    fixture_path = config_module.REPO_ROOT / "data" / "fixtures" / "retrieval_candidates.json"
    if not fixture_path.exists():
        return {}
    with fixture_path.open(encoding="utf-8") as handle:
        raw = json.load(handle)
    return {normalize_text(key): value for key, value in raw.items()}


def retrieve_candidates(payload: AnalyzeRequest, backend_override: str | None = None) -> list[Candidate]:
    settings = get_settings()
    backend = (backend_override or settings.retrieval_backend).lower()

    if backend == "fixture":
        return _retrieve_fixture_candidates(payload)
    if backend == "serpapi":
        return _retrieve_serpapi_candidates(payload)
    if backend == "playwright":
        return _retrieve_playwright_candidates(payload)
    if backend in {"hybrid", "combined"}:
        return _retrieve_hybrid_candidates(payload)

    raise ValueError(f"Unsupported retrieval backend: {settings.retrieval_backend}")


def _retrieve_fixture_candidates(payload: AnalyzeRequest) -> list[Candidate]:
    fixtures = _load_fixture_candidates()
    key = normalize_text(payload.wine_name)
    raw_candidates = fixtures.get(key, [])
    candidates: list[Candidate] = []

    for index, item in enumerate(raw_candidates, start=1):
        candidates.append(
            Candidate(
                candidate_id=item.get("candidate_id", f"{key}-{index}"),
                image_url=item["image_url"],
                source_page=item["source_page"],
                source_domain=item.get("source_domain", _extract_domain(item["source_page"])),
                observed_text=item.get("observed_text", ""),
                image_quality_score=float(item.get("image_quality_score", 0.0)),
                source_trust_score=float(item.get("source_trust_score", 0.0)),
                notes=list(item.get("notes", [])),
                fixture_expected_match=item.get("fixture_expected_match"),
            )
        )

    return candidates


def _retrieve_serpapi_candidates(payload: AnalyzeRequest) -> list[Candidate]:
    settings = get_settings()
    if not settings.serpapi_api_key:
        raise RuntimeError("SERPAPI_API_KEY is required for the SerpApi retrieval backend.")

    candidates: list[Candidate] = []
    for query_index, query in enumerate(_build_search_queries(payload), start=1):
        params = {
            "engine": settings.serpapi_engine,
            "q": query,
            "api_key": settings.serpapi_api_key,
            "google_domain": settings.serpapi_google_domain,
            "num": str(settings.serpapi_num_results),
        }
        if settings.serpapi_location:
            params["location"] = settings.serpapi_location

        url = "https://serpapi.com/search.json?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url) as response:
            payload_json = json.loads(response.read().decode("utf-8"))

        organic_results = payload_json.get("organic_results", [])
        for index, item in enumerate(organic_results[: settings.candidate_download_limit], start=1):
            link = item.get("link")
            if not link:
                continue
            snippet = item.get("snippet", "") or ""
            title = item.get("title", "") or ""
            displayed_link = item.get("displayed_link", "") or item.get("source", "") or ""
            candidates.append(
                Candidate(
                    candidate_id=f"serpapi-{query_index}-{index}",
                    image_url=item.get("thumbnail") or link,
                    source_page=link,
                    source_domain=_extract_domain(link),
                    observed_text=f"{title} {snippet}".strip(),
                    image_quality_score=0.55,
                    source_trust_score=_source_trust_from_domain(displayed_link or link),
                    notes=["retrieved_via_serpapi", f"query:{query}"],
                )
            )
    return _dedupe_candidates(candidates, settings.candidate_download_limit)


def _retrieve_playwright_candidates(payload: AnalyzeRequest) -> list[Candidate]:
    queries = _build_search_queries(payload)
    candidates = collect_playwright_candidates(queries)
    for candidate in candidates:
        candidate.source_trust_score = max(candidate.source_trust_score, _source_trust_from_domain(candidate.source_domain))
    return _dedupe_candidates(candidates, get_settings().candidate_download_limit)


def _retrieve_hybrid_candidates(payload: AnalyzeRequest) -> list[Candidate]:
    settings = get_settings()
    collected: list[Candidate] = []
    errors: list[str] = []

    for backend_name, fn in (
        ("serpapi", _retrieve_serpapi_candidates),
        ("playwright", _retrieve_playwright_candidates),
    ):
        try:
            collected.extend(fn(payload))
        except Exception as exc:
            errors.append(f"{backend_name}:{type(exc).__name__}")

    merged = _dedupe_candidates(collected, settings.candidate_download_limit)
    if merged:
        return merged
    if errors:
        raise RuntimeError("Hybrid retrieval failed: " + ", ".join(errors))
    return []


def _build_search_query(payload: AnalyzeRequest) -> str:
    wine_name = " ".join(payload.wine_name.split())
    region = " ".join(payload.region.split())
    parts = [wine_name, payload.vintage.strip(), "wine bottle"]
    if payload.region:
        parts.append(region)
    return " ".join(part for part in parts if part).strip()


def _build_search_queries(payload: AnalyzeRequest) -> list[str]:
    parsed = parse_identity(payload)
    queries = build_queries(payload, parsed)
    if not queries:
        return [_build_search_query(payload)]
    return queries[:6]


def _extract_domain(url: str) -> str:
    stripped = url.split("//", 1)[-1]
    return stripped.split("/", 1)[0]


def _source_trust_from_domain(value: str) -> float:
    """Get trust score for a domain using the domain_filters module.
    
    Returns:
        0.90 for trusted wine sites (from TRUSTED_WINE_DOMAINS)
        0.75 for neutral sites (legacy heuristic-based)
        0.00 for excluded sites (stock photos, social media, etc.)
    """
    # First check if domain is explicitly excluded
    if is_excluded_domain(value):
        return 0.00
    
    # Check if domain is in trusted list
    trust_score = get_domain_trust_score(value)
    if trust_score > 0.75:
        return trust_score
    
    # Fall back to legacy heuristics for unknown domains
    lowered = value.lower()
    if any(token in lowered for token in ("winery", "domaine", "chateau", "producer")):
        return 0.85
    if any(token in lowered for token in ("merchant", "wine", "cellar", "auction")):
        return 0.75
    return 0.65


def _normalize_search_result_url(href: str) -> str:
    if not href:
        return ""
    if href.startswith("//"):
        href = "https:" + href

    parsed = urllib.parse.urlparse(href)
    if parsed.scheme not in {"http", "https"}:
        return ""

    query = urllib.parse.parse_qs(parsed.query)
    if "duckduckgo.com" in parsed.netloc and "uddg" in query:
        return urllib.parse.unquote(query["uddg"][0])

    if "bing.com" in parsed.netloc and parsed.path == "/ck/a" and "u" in query:
        value = query["u"][0]
        if value.startswith("a1"):
            decoded = _decode_bing_u(value[2:])
            if decoded:
                return decoded

    return href


def _decode_bing_u(value: str) -> str:
    padding = "=" * (-len(value) % 4)
    try:
        decoded = base64.b64decode(value + padding).decode("utf-8")
    except Exception:
        return ""
    return decoded if decoded.startswith(("http://", "https://")) else ""


def _dedupe_candidates(candidates: list[Candidate], limit: int) -> list[Candidate]:
    # Filter out excluded domains (stock photos, social media, etc.)
    filtered = filter_candidates_by_domain(candidates)
    
    merged: dict[str, Candidate] = {}
    for candidate in filtered:
        key = _candidate_merge_key(candidate)
        if key not in merged:
            merged[key] = candidate
            continue
        existing = merged[key]
        existing.source_trust_score = max(existing.source_trust_score, candidate.source_trust_score)
        existing.image_quality_score = max(existing.image_quality_score, candidate.image_quality_score)
        if candidate.observed_text and candidate.observed_text not in existing.observed_text:
            existing.observed_text = " ".join(
                part for part in [existing.observed_text, candidate.observed_text] if part
            ).strip()
        for note in candidate.notes:
            if note not in existing.notes:
                existing.notes.append(note)
        backends = {note for note in existing.notes if note.startswith("retrieved_via_")}
        if len(backends) > 1:
            existing.source_trust_score = min(1.0, existing.source_trust_score + 0.08)
            if "multi_backend_hit" not in existing.notes:
                existing.notes.append("multi_backend_hit")

    ranked = sorted(
        merged.values(),
        key=lambda candidate: (
            get_domain_trust_score(candidate.source_domain),
            candidate.source_trust_score,
            candidate.image_quality_score,
            len(candidate.observed_text),
        ),
        reverse=True,
    )
    return ranked[:limit]


def _candidate_merge_key(candidate: Candidate) -> str:
    return candidate.source_page or candidate.image_url
