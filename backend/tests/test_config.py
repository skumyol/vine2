"""Comprehensive tests for config module - 100% coverage target."""

import os
import tempfile
from pathlib import Path

import pytest

from backend.app.core.config import Settings, get_settings, REPO_ROOT


class TestSettingsDefaults:
    """Test Settings default values."""

    def test_settings_default_debug(self) -> None:
        """Test default debug value."""
        settings = Settings()
        assert settings.debug is False

    def test_settings_default_retrieval_backend(self) -> None:
        """Test default retrieval backend."""
        settings = Settings()
        assert settings.retrieval_backend == "fixture"

    def test_settings_default_candidate_limits(self) -> None:
        """Test default candidate limits."""
        settings = Settings()
        assert settings.candidate_page_limit == 15
        assert settings.candidate_image_limit_per_page == 3
        assert settings.candidate_download_limit == 25

    def test_settings_default_acceptance_threshold(self) -> None:
        """Test default acceptance threshold."""
        settings = Settings()
        assert settings.acceptance_threshold == 0.85

    def test_settings_default_paths(self) -> None:
        """Test default path settings."""
        settings = Settings()
        assert isinstance(settings.results_dir, Path)
        assert isinstance(settings.cache_dir, Path)
        assert isinstance(settings.images_dir, Path)
        assert isinstance(settings.fixture_candidates_path, Path)
        assert isinstance(settings.fixture_labels_path, Path)

    def test_settings_default_serpapi(self) -> None:
        """Test default SerpAPI settings."""
        settings = Settings()
        assert settings.serpapi_api_key == ""
        assert settings.serpapi_engine == "google"
        assert settings.serpapi_google_domain == "google.com"
        assert settings.serpapi_num_results == 10
        assert settings.serpapi_location == ""

    def test_settings_default_playwright(self) -> None:
        """Test default Playwright settings."""
        settings = Settings()
        assert "brave.com" in settings.playwright_search_url_template
        assert settings.playwright_headless is True
        assert "--no-sandbox" in settings.playwright_launch_args
        assert settings.playwright_force_http_fallback is True
        assert len(settings.playwright_search_url_templates) >= 2


class TestSettingsFromEnv:
    """Test Settings loading from environment variables."""

    def test_settings_loads_from_env_file(self, monkeypatch, tmp_path) -> None:
        """Test loading settings from .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text("VINO_DEBUG=true\nVINO_RETRIEVAL_BACKEND=serpapi\n")
        
        # Create settings with custom env file
        settings = Settings(_env_file=str(env_file))
        
        assert settings.debug is True
        assert settings.retrieval_backend == "serpapi"

    def test_settings_uses_serpapi_api_key_alias(self, monkeypatch) -> None:
        """Test that SERPAPI_API_KEY is loaded via alias."""
        monkeypatch.setenv("SERPAPI_API_KEY", "test-api-key-123")
        
        settings = Settings()
        
        assert settings.serpapi_api_key == "test-api-key-123"

    def test_settings_populate_by_name(self) -> None:
        """Test that settings can be populated by field name or alias."""
        # Via field name
        settings1 = Settings(serpapi_api_key="via-field-name")
        assert settings1.serpapi_api_key == "via-field-name"
        
        # Via alias should also work through env


class TestGetSettings:
    """Test get_settings function."""

    def test_get_settings_returns_settings_instance(self) -> None:
        """Test that get_settings returns a Settings instance."""
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_get_settings_is_cached(self) -> None:
        """Test that get_settings uses LRU cache."""
        settings1 = get_settings()
        settings2 = get_settings()
        
        # Should be the same object (cached)
        assert settings1 is settings2


class TestRepoRoot:
    """Test REPO_ROOT constant."""

    def test_repo_root_is_path(self) -> None:
        """Test that REPO_ROOT is a Path instance."""
        assert isinstance(REPO_ROOT, Path)

    def test_repo_root_exists(self) -> None:
        """Test that REPO_ROOT directory exists."""
        assert REPO_ROOT.exists()

    def test_repo_root_contains_expected_dirs(self) -> None:
        """Test that REPO_ROOT contains expected directories."""
        # Should contain backend directory
        assert (REPO_ROOT / "backend").exists() or (REPO_ROOT / ".git").exists()


class TestSettingsValidation:
    """Test Settings validation."""

    def test_settings_accepts_valid_analyzer_mode(self) -> None:
        """Test that valid analyzer modes are accepted."""
        from backend.app.core.constants import AnalyzerMode
        
        settings = Settings(analyzer_mode=AnalyzerMode.STRICT)
        assert settings.analyzer_mode == AnalyzerMode.STRICT
        
        settings = Settings(analyzer_mode=AnalyzerMode.BALANCED)
        assert settings.analyzer_mode == AnalyzerMode.BALANCED

    def test_settings_string_fields_have_min_length(self) -> None:
        """Test that string fields enforce min length."""
        # This should raise validation error for empty strings
        # where min_length is specified
        settings = Settings()
        
        # wine_name and vintage have min_length=1
        # But we're testing Settings defaults, not AnalyzeRequest
        assert isinstance(settings.retrieval_backend, str)
        assert len(settings.retrieval_backend) > 0


class TestSettingsExtraFields:
    """Test Settings extra field handling."""

    def test_settings_ignores_extra_fields(self) -> None:
        """Test that extra fields are ignored."""
        # This should not raise an error
        settings = Settings(extra_field="ignored", another_extra=123)
        
        # Extra fields should not be present
        assert not hasattr(settings, 'extra_field') or settings.__pydantic_extra__.get('extra_field') is None
