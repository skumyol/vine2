"""Comprehensive tests for retriever module - 100% coverage target."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.app.models.candidate import Candidate
from backend.app.models.sku import AnalyzeRequest
from backend.app.services.retriever import (
    _build_search_query,
    _extract_domain,
    _load_fixture_candidates,
    _source_trust_from_domain,
    retrieve_candidates,
)


class TestBuildSearchQuery:
    """Test _build_search_query function."""

    def test_build_search_query_with_all_fields(self) -> None:
        """Test building query with all fields."""
        payload = AnalyzeRequest(
            wine_name="Domaine Rossignol-Trapet Latricieres-Chambertin",
            vintage="2017",
            format="750ml",
            region="Burgundy"
        )
        
        result = _build_search_query(payload)
        
        assert "Domaine Rossignol-Trapet Latricieres-Chambertin" in result
        assert "2017" in result
        assert "Burgundy" in result
        assert "wine bottle" in result

    def test_build_search_query_without_region(self) -> None:
        """Test building query without region."""
        payload = AnalyzeRequest(
            wine_name="Domaine Rossignol-Trapet",
            vintage="2017",
            format="750ml",
            region=""
        )
        
        result = _build_search_query(payload)
        
        assert "Domaine Rossignol-Trapet" in result
        assert "2017" in result
        assert "wine bottle" in result
        # Should not have empty region
        assert result.count(" ") == result.strip().count(" ")

    def test_build_search_query_strips_whitespace(self) -> None:
        """Test that query has no extra whitespace."""
        payload = AnalyzeRequest(
            wine_name="  Test Wine  ",
            vintage="2020",
            format="750ml",
            region="  Test  "
        )
        
        result = _build_search_query(payload)
        
        assert result == result.strip()
        assert "  " not in result


class TestExtractDomain:
    """Test _extract_domain function."""

    def test_extract_domain_from_https_url(self) -> None:
        """Test extracting domain from HTTPS URL."""
        result = _extract_domain("https://www.example.com/path/to/page")
        assert result == "www.example.com"

    def test_extract_domain_from_http_url(self) -> None:
        """Test extracting domain from HTTP URL."""
        result = _extract_domain("http://example.com/page")
        assert result == "example.com"

    def test_extract_domain_with_subdomain(self) -> None:
        """Test extracting domain with subdomain."""
        result = _extract_domain("https://subdomain.example.com/path")
        assert result == "subdomain.example.com"

    def test_extract_domain_with_port(self) -> None:
        """Test extracting domain with port."""
        result = _extract_domain("https://example.com:8080/path")
        assert result == "example.com:8080"

    def test_extract_domain_without_protocol(self) -> None:
        """Test extracting domain without protocol."""
        result = _extract_domain("example.com/path")
        assert result == "example.com"


class TestSourceTrustFromDomain:
    """Test _source_trust_from_domain function."""

    def test_source_trust_winery_domain(self) -> None:
        """Test high trust for winery domains."""
        assert _source_trust_from_domain("winery.example.com") == 0.85
        assert _source_trust_from_domain("domaine-example.com") == 0.85
        assert _source_trust_from_domain("chateau-example.com") == 0.85
        assert _source_trust_from_domain("producer-wines.com") == 0.85

    def test_source_trust_merchant_domain(self) -> None:
        """Test medium trust for merchant domains."""
        assert _source_trust_from_domain("wine-merchant.com") == 0.75
        assert _source_trust_from_domain("cellar-wines.com") == 0.75
        assert _source_trust_from_domain("auction-house.com") == 0.75

    def test_source_trust_generic_domain(self) -> None:
        """Test low trust for generic domains."""
        assert _source_trust_from_domain("example.com") == 0.65
        assert _source_trust_from_domain("random-site.org") == 0.65

    def test_source_trust_is_case_insensitive(self) -> None:
        """Test that domain matching is case insensitive."""
        assert _source_trust_from_domain("WINERY.EXAMPLE.COM") == 0.85
        assert _source_trust_from_domain("WINE-Merchant.COM") == 0.75


class TestLoadFixtureCandidates:
    """Test _load_fixture_candidates function."""

    def test_load_fixture_candidates_returns_dict(self, tmp_path, monkeypatch) -> None:
        """Test that fixtures are loaded as dictionary."""
        # Create temporary fixture file
        fixture_data = {
            "domaine rossignol trapet latricieres chambertin": [
                {
                    "candidate_id": "test-1",
                    "image_url": "https://example.com/image.jpg",
                    "source_page": "https://example.com/page",
                    "observed_text": "Test text",
                }
            ]
        }
        
        fixture_file = tmp_path / "fixtures" / "retrieval_candidates.json"
        fixture_file.parent.mkdir(parents=True)
        fixture_file.write_text(json.dumps(fixture_data))
        
        # Mock settings to use temp path
        from backend.app.core import config
        original_repo_root = config.REPO_ROOT
        monkeypatch.setattr(config, "REPO_ROOT", tmp_path)
        
        # Clear cache and load
        _load_fixture_candidates.cache_clear()
        result = _load_fixture_candidates()
        
        # Restore
        monkeypatch.setattr(config, "REPO_ROOT", original_repo_root)
        
        assert isinstance(result, dict)

    def test_load_fixture_candidates_returns_empty_if_no_file(self, tmp_path, monkeypatch) -> None:
        """Test that empty dict is returned if fixture file doesn't exist."""
        from backend.app.core import config
        original_repo_root = config.REPO_ROOT
        monkeypatch.setattr(config, "REPO_ROOT", tmp_path)
        
        _load_fixture_candidates.cache_clear()
        result = _load_fixture_candidates()
        
        monkeypatch.setattr(config, "REPO_ROOT", original_repo_root)
        
        assert result == {}


class TestRetrieveCandidates:
    """Test retrieve_candidates function."""

    def test_retrieve_candidates_with_fixture_backend(self, monkeypatch) -> None:
        """Test retrieval with fixture backend."""
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.retrieval_backend = "fixture"
        mock_settings.fixture_candidates_path = Path("/fake/path.json")
        
        # Mock fixture data
        fixture_data = {
            "test wine": [
                {
                    "candidate_id": "test-1",
                    "image_url": "https://example.com/image.jpg",
                    "source_page": "https://example.com/page",
                    "source_domain": "example.com",
                    "observed_text": "Test wine 2020",
                    "image_quality_score": 0.8,
                    "source_trust_score": 0.7,
                    "notes": ["test"],
                    "fixture_expected_match": True,
                }
            ]
        }
        
        with patch("backend.app.services.retriever.get_settings", return_value=mock_settings):
            with patch("backend.app.services.retriever._load_fixture_candidates", return_value=fixture_data):
                payload = AnalyzeRequest(
                    wine_name="Test Wine",
                    vintage="2020",
                    format="750ml",
                    region="Test"
                )
                
                result = retrieve_candidates(payload)
        
        assert len(result) == 1
        assert result[0].candidate_id == "test-1"
        assert result[0].fixture_expected_match is True

    def test_retrieve_candidates_unsupported_backend(self, monkeypatch) -> None:
        """Test that unsupported backend raises ValueError."""
        mock_settings = MagicMock()
        mock_settings.retrieval_backend = "unsupported"
        
        with patch("backend.app.services.retriever.get_settings", return_value=mock_settings):
            payload = AnalyzeRequest(
                wine_name="Test Wine",
                vintage="2020",
                format="750ml",
                region="Test"
            )
            
            with pytest.raises(ValueError, match="Unsupported retrieval backend"):
                retrieve_candidates(payload)

    def test_retrieve_candidates_serpapi_missing_key(self, monkeypatch) -> None:
        """Test that SerpApi backend raises error without API key."""
        mock_settings = MagicMock()
        mock_settings.retrieval_backend = "serpapi"
        mock_settings.serpapi_api_key = ""
        
        with patch("backend.app.services.retriever.get_settings", return_value=mock_settings):
            payload = AnalyzeRequest(
                wine_name="Test Wine",
                vintage="2020",
                format="750ml",
                region="Test"
            )
            
            with pytest.raises(RuntimeError, match="SERPAPI_API_KEY is required"):
                retrieve_candidates(payload)


class TestFixtureCandidateRetrieval:
    """Test _retrieve_fixture_candidates function."""

    def test_retrieve_fixture_candidates_with_no_match(self, monkeypatch) -> None:
        """Test retrieval when no fixture matches."""
        fixture_data = {"other wine": []}
        
        with patch("backend.app.services.retriever._load_fixture_candidates", return_value=fixture_data):
            payload = AnalyzeRequest(
                wine_name="Unknown Wine",
                vintage="2020",
                format="750ml",
                region="Test"
            )
            
            from backend.app.services.retriever import _retrieve_fixture_candidates
            result = _retrieve_fixture_candidates(payload)
        
        assert result == []

    def test_retrieve_fixture_candidates_extracts_domain(self, monkeypatch) -> None:
        """Test that domain is extracted when not provided."""
        fixture_data = {
            "test wine": [
                {
                    "candidate_id": "test-1",
                    "image_url": "https://example.com/image.jpg",
                    "source_page": "https://wine-shop.com/page",
                    # No source_domain provided
                }
            ]
        }
        
        with patch("backend.app.services.retriever._load_fixture_candidates", return_value=fixture_data):
            payload = AnalyzeRequest(
                wine_name="Test Wine",
                vintage="2020",
                format="750ml",
                region="Test"
            )
            
            from backend.app.services.retriever import _retrieve_fixture_candidates
            result = _retrieve_fixture_candidates(payload)
        
        assert len(result) == 1
        assert result[0].source_domain == "wine-shop.com"


class TestCandidateCreation:
    """Test Candidate model creation from fixtures."""

    def test_candidate_from_fixture_with_defaults(self) -> None:
        """Test that Candidate uses defaults for missing fixture fields."""
        fixture_item = {
            "candidate_id": "test-1",
            "image_url": "https://example.com/image.jpg",
            "source_page": "https://example.com/page",
            # Missing optional fields
        }
        
        candidate = Candidate(
            candidate_id=fixture_item["candidate_id"],
            image_url=fixture_item["image_url"],
            source_page=fixture_item["source_page"],
            source_domain="example.com",
        )
        
        assert candidate.observed_text == ""
        assert candidate.image_quality_score == 0.0
        assert candidate.source_trust_score == 0.0
        assert candidate.notes == []
        assert candidate.fixture_expected_match is None
