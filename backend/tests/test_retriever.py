import json

from backend.app.models.sku import AnalyzeRequest
from backend.app.services import retriever


FIXTURE_PATH = retriever.get_settings().fixture_candidates_path


def test_fixture_retriever_returns_seeded_candidates(monkeypatch) -> None:
    monkeypatch.setattr(retriever, "get_settings", lambda: _settings("fixture"))
    payload = AnalyzeRequest(
        wine_name="Domaine Rossignol-Trapet Latricieres-Chambertin Grand Cru",
        vintage="2017",
        format="750ml",
        region="Burgundy",
    )

    candidates = retriever.retrieve_candidates(payload)

    assert len(candidates) >= 1
    assert candidates[0].source_domain == "merchant.example.com"


def test_serpapi_retriever_maps_organic_results(monkeypatch) -> None:
    monkeypatch.setattr(retriever, "get_settings", lambda: _settings("serpapi"))

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {
                    "organic_results": [
                        {
                            "link": "https://merchant.example.com/wine-a",
                            "title": "Wine A",
                            "snippet": "Producer Appellation Vintage",
                            "thumbnail": "https://images.example.com/wine-a.jpg",
                            "displayed_link": "merchant.example.com"
                        }
                    ]
                }
            ).encode("utf-8")

    monkeypatch.setattr(retriever.urllib.request, "urlopen", lambda url: FakeResponse())
    payload = AnalyzeRequest(
        wine_name="Sample Wine",
        vintage="2019",
        format="750ml",
        region="Burgundy",
    )

    candidates = retriever.retrieve_candidates(payload)

    assert len(candidates) == 1
    assert candidates[0].image_url == "https://images.example.com/wine-a.jpg"
    assert "Producer Appellation Vintage" in candidates[0].observed_text


def test_playwright_retriever_falls_back_to_http_search(monkeypatch) -> None:
    monkeypatch.setattr(retriever, "get_settings", lambda: _settings("playwright"))

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b"""
            <html>
              <body>
                <a href="https://merchant.example.com/wine-a">Wine A 2019 bottle</a>
              </body>
            </html>
            """

    def fake_urlopen(request, timeout=None):
        return FakeResponse()

    monkeypatch.setattr(retriever.urllib.request, "urlopen", fake_urlopen)

    real_import = __import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "playwright.sync_api":
            raise ImportError("playwright not installed")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr("builtins.__import__", fake_import)
    payload = AnalyzeRequest(
        wine_name="Sample Wine",
        vintage="2019",
        format="750ml",
        region="Burgundy",
    )

    candidates = retriever.retrieve_candidates(payload)

    assert candidates
    assert candidates[0].source_page == "https://merchant.example.com/wine-a"
    assert "retrieved_via_http_search" in candidates[0].notes


def _settings(backend: str):
    class Settings:
        retrieval_backend = backend
        fixture_candidates_path = FIXTURE_PATH
        serpapi_api_key = "test-key"
        serpapi_engine = "google"
        serpapi_google_domain = "google.com"
        serpapi_num_results = 10
        serpapi_location = ""
        candidate_download_limit = 25
        playwright_search_url_template = "https://www.google.com/search?q={query}"
        playwright_headless = True

    return Settings()
