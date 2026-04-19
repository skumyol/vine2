import os
import urllib.error

import pytest

from backend.app.models.sku import AnalyzeRequest
from backend.app.services import retriever


pytestmark = pytest.mark.live
FIXTURE_PATH = retriever.get_settings().fixture_candidates_path


def test_live_serpapi_retrieval_returns_candidates(monkeypatch) -> None:
    api_key = os.getenv("SERPAPI_API_KEY", "")
    if not api_key:
        pytest.skip("SERPAPI_API_KEY is not set")

    monkeypatch.setattr(retriever, "get_settings", lambda: _settings("serpapi", api_key=api_key))
    payload = AnalyzeRequest(
        wine_name="Domaine Arlaud Morey-St-Denis 'Monts Luisants' 1er Cru",
        vintage="2019",
        format="750ml",
        region="Burgundy",
    )

    try:
        candidates = retriever.retrieve_candidates(payload)
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            pytest.skip("SerpApi quota exhausted or rate limited")
        raise
    except urllib.error.URLError:
        pytest.skip("SerpApi is unreachable in the current environment")

    assert candidates, "SerpApi returned no candidates"
    assert any(candidate.source_page.startswith("http") for candidate in candidates)
    assert any(candidate.observed_text for candidate in candidates)


def test_live_playwright_retrieval_returns_candidates(monkeypatch) -> None:
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError:
        pytest.skip("playwright is not installed in the active environment")

    monkeypatch.setattr(
        retriever,
        "get_settings",
        lambda: _settings(
            "playwright",
            playwright_search_url_template="https://www.bing.com/search?q={query}",
        ),
    )
    payload = AnalyzeRequest(
        wine_name="Brokenwood Graveyard Vineyard Shiraz",
        vintage="2015",
        format="750ml",
        region="Hunter Valley",
    )

    try:
        candidates = retriever.retrieve_candidates(payload)
    except Exception as exc:
        if exc.__class__.__name__ == "TargetClosedError":
            pytest.skip("Playwright browser launch is blocked in the current environment")
        raise

    if not candidates:
        pytest.skip("Playwright/HTTP search returned no live candidates in the current environment")
    assert any(candidate.source_page.startswith("http") for candidate in candidates)


def _settings(
    backend: str,
    *,
    api_key: str = "",
    playwright_search_url_template: str = "https://www.google.com/search?q={query}",
):
    class Settings:
        pass

    settings = Settings()
    settings.retrieval_backend = backend
    settings.fixture_candidates_path = FIXTURE_PATH
    settings.serpapi_api_key = api_key
    settings.serpapi_engine = "google"
    settings.serpapi_google_domain = "google.com"
    settings.serpapi_num_results = 10
    settings.serpapi_location = ""
    settings.candidate_download_limit = 10
    settings.playwright_search_url_template = playwright_search_url_template
    settings.playwright_headless = True
    return settings
