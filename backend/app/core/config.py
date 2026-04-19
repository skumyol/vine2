from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.app.core.constants import AnalyzerMode


REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    debug: bool = Field(default=False)
    analyzer_mode: AnalyzerMode = Field(default=AnalyzerMode.STRICT)
    pipeline_name: str = Field(default="voter")
    retrieval_backend: str = Field(default="fixture")
    candidate_page_limit: int = Field(default=15)
    candidate_image_limit_per_page: int = Field(default=3)
    candidate_download_limit: int = Field(default=25)
    candidate_evaluation_limit: int = Field(default=6)
    acceptance_threshold: float = Field(default=0.85)
    batch_worker_count: int = Field(default=4)
    results_dir: Path = Field(default=REPO_ROOT / "data" / "results")
    cache_dir: Path = Field(default=REPO_ROOT / "data" / "cache")
    images_dir: Path = Field(default=REPO_ROOT / "data" / "images")
    fixture_candidates_path: Path = Field(default=REPO_ROOT / "data" / "fixtures" / "retrieval_candidates.json")
    fixture_labels_path: Path = Field(default=REPO_ROOT / "data" / "fixtures" / "evaluation_labels.json")
    serpapi_api_key: str = Field(default="", alias="SERPAPI_API_KEY")
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_model: str = Field(default="qwen/qwen3.5-flash-02-23")
    vlm_reasoning_enabled: bool = Field(default=True)
    ocr_easyocr_enabled: bool = Field(default=False)
    yolo_enabled: bool = Field(default=False)
    serpapi_engine: str = Field(default="google")
    serpapi_google_domain: str = Field(default="google.com")
    serpapi_num_results: int = Field(default=10)
    serpapi_location: str = Field(default="")
    playwright_search_url_template: str = Field(
        default="https://search.brave.com/search?q={query}"
    )
    playwright_search_url_templates: list[str] = Field(
        default_factory=lambda: [
            "https://search.brave.com/search?q={query}",
            "https://www.startpage.com/do/search?q={query}",
            "https://www.mojeek.com/search?q={query}",
            "https://lite.duckduckgo.com/lite/?q={query}",
        ]
    )
    playwright_headless: bool = Field(default=True)
    playwright_launch_args: list[str] = Field(
        default_factory=lambda: [
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--no-sandbox",
        ]
    )
    playwright_force_http_fallback: bool = Field(default=True)
    playwright_http_min_results: int = Field(default=3)
    playwright_http_request_delay_ms: int = Field(default=500)
    playwright_service_url: str = Field(default="")
    cors_origins: str = Field(default="http://localhost:5173,http://127.0.0.1:5173")

    model_config = SettingsConfigDict(
        env_prefix="VINO_",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
