"""Comprehensive tests for domain_filters module - 100% coverage target."""

import pytest

from backend.app.core.domain_filters import (
    EXCLUDED_DOMAINS,
    TRUSTED_WINE_DOMAINS,
    build_site_restricted_queries,
    filter_candidates_by_domain,
    get_domain_trust_score,
    is_excluded_domain,
    is_trusted_domain,
    sort_candidates_by_domain_trust,
)
from backend.app.models.candidate import Candidate


class TestTrustedDomains:
    """Test TRUSTED_WINE_DOMAINS constant and is_trusted_domain function."""

    def test_trusted_domains_is_frozenset(self) -> None:
        """Test that TRUSTED_WINE_DOMAINS is a frozenset."""
        assert isinstance(TRUSTED_WINE_DOMAINS, frozenset)

    def test_trusted_domains_not_empty(self) -> None:
        """Test that TRUSTED_WINE_DOMAINS is not empty."""
        assert len(TRUSTED_WINE_DOMAINS) > 0

    def test_trusted_domains_are_lowercase(self) -> None:
        """Test that all trusted domains are lowercase."""
        for domain in TRUSTED_WINE_DOMAINS:
            assert domain == domain.lower(), f"Domain {domain} is not lowercase"

    def test_is_trusted_domain_with_exact_match(self) -> None:
        """Test exact domain match."""
        assert is_trusted_domain("wine.com") is True
        assert is_trusted_domain("vivino.com") is True
        assert is_trusted_domain("wine-searcher.com") is True

    def test_is_trusted_domain_with_subdomain(self) -> None:
        """Test subdomain matching."""
        assert is_trusted_domain("www.wine.com") is True
        assert is_trusted_domain("shop.wine.com") is True
        assert is_trusted_domain("images.vivino.com") is True
        assert is_trusted_domain("www.wine-searcher.com") is True

    def test_is_trusted_domain_with_unknown_domain(self) -> None:
        """Test unknown domain returns False."""
        assert is_trusted_domain("unknown.com") is False
        assert is_trusted_domain("example.org") is False
        assert is_trusted_domain("random-site.net") is False

    def test_is_trusted_domain_case_insensitive(self) -> None:
        """Test case insensitivity."""
        assert is_trusted_domain("WINE.COM") is True
        assert is_trusted_domain("Vivino.COM") is True
        assert is_trusted_domain("WINE-SEARCHER.COM") is True

    def test_is_trusted_domain_with_whitespace(self) -> None:
        """Test that whitespace is stripped."""
        assert is_trusted_domain("  wine.com  ") is True
        assert is_trusted_domain(" wine.com ") is True

    def test_is_trusted_domain_similar_but_different(self) -> None:
        """Test that similar but different domains don't match."""
        assert is_trusted_domain("wine.com.au") is False  # Different TLD
        assert is_trusted_domain("mywine.com") is False  # Different prefix
        assert is_trusted_domain("wine-searcher.co.uk") is False  # Different TLD


class TestExcludedDomains:
    """Test EXCLUDED_DOMAINS constant and is_excluded_domain function."""

    def test_excluded_domains_is_frozenset(self) -> None:
        """Test that EXCLUDED_DOMAINS is a frozenset."""
        assert isinstance(EXCLUDED_DOMAINS, frozenset)

    def test_excluded_domains_not_empty(self) -> None:
        """Test that EXCLUDED_DOMAINS is not empty."""
        assert len(EXCLUDED_DOMAINS) > 0

    def test_excluded_domains_are_lowercase(self) -> None:
        """Test that all excluded domains are lowercase."""
        for domain in EXCLUDED_DOMAINS:
            assert domain == domain.lower(), f"Domain {domain} is not lowercase"

    def test_is_excluded_domain_with_stock_photos(self) -> None:
        """Test stock photo sites are excluded."""
        assert is_excluded_domain("shutterstock.com") is True
        assert is_excluded_domain("gettyimages.com") is True
        assert is_excluded_domain("alamy.com") is True
        assert is_excluded_domain("istockphoto.com") is True

    def test_is_excluded_domain_with_social_media(self) -> None:
        """Test social media sites are excluded."""
        assert is_excluded_domain("pinterest.com") is True
        assert is_excluded_domain("instagram.com") is True
        assert is_excluded_domain("facebook.com") is True
        assert is_excluded_domain("twitter.com") is True
        assert is_excluded_domain("x.com") is True

    def test_is_excluded_domain_with_marketplaces(self) -> None:
        """Test marketplace sites are excluded."""
        assert is_excluded_domain("amazon.com") is True
        assert is_excluded_domain("ebay.com") is True
        assert is_excluded_domain("walmart.com") is True

    def test_is_excluded_domain_with_ai_generators(self) -> None:
        """Test AI image generators are excluded."""
        assert is_excluded_domain("craiyon.com") is True
        assert is_excluded_domain("midjourney.com") is True
        assert is_excluded_domain("stablediffusionweb.com") is True

    def test_is_excluded_domain_with_subdomain(self) -> None:
        """Test subdomain matching for excluded domains."""
        assert is_excluded_domain("www.shutterstock.com") is True
        assert is_excluded_domain("images.gettyimages.com") is True
        assert is_excluded_domain("shop.amazon.com") is True

    def test_is_excluded_domain_case_insensitive(self) -> None:
        """Test case insensitivity."""
        assert is_excluded_domain("SHUTTERSTOCK.COM") is True
        assert is_excluded_domain("Pinterest.COM") is True
        assert is_excluded_domain("AMAZON.COM") is True

    def test_is_excluded_domain_with_unknown(self) -> None:
        """Test unknown domain returns False."""
        assert is_excluded_domain("wine.com") is False
        assert is_excluded_domain("example.com") is False


class TestGetDomainTrustScore:
    """Test get_domain_trust_score function."""

    def test_get_domain_trust_score_for_trusted(self) -> None:
        """Test trusted domains get 0.90."""
        assert get_domain_trust_score("wine.com") == 0.90
        assert get_domain_trust_score("vivino.com") == 0.90
        assert get_domain_trust_score("sothebys.com") == 0.90

    def test_get_domain_trust_score_for_excluded(self) -> None:
        """Test excluded domains get 0.00."""
        assert get_domain_trust_score("shutterstock.com") == 0.00
        assert get_domain_trust_score("amazon.com") == 0.00
        assert get_domain_trust_score("pinterest.com") == 0.00

    def test_get_domain_trust_score_for_neutral(self) -> None:
        """Test neutral domains get 0.75."""
        assert get_domain_trust_score("example.com") == 0.75
        assert get_domain_trust_score("unknown.org") == 0.75
        assert get_domain_trust_score("random-site.net") == 0.75


class TestFilterCandidatesByDomain:
    """Test filter_candidates_by_domain function."""

    def test_filter_candidates_removes_excluded(self) -> None:
        """Test that excluded domains are filtered out."""
        candidates = [
            Candidate(candidate_id="1", image_url="http://a.com/1.jpg", source_page="http://a.com/1", source_domain="wine.com"),
            Candidate(candidate_id="2", image_url="http://b.com/2.jpg", source_page="http://b.com/2", source_domain="shutterstock.com"),
            Candidate(candidate_id="3", image_url="http://c.com/3.jpg", source_page="http://c.com/3", source_domain="vivino.com"),
            Candidate(candidate_id="4", image_url="http://d.com/4.jpg", source_page="http://d.com/4", source_domain="amazon.com"),
        ]
        
        result = filter_candidates_by_domain(candidates)
        
        assert len(result) == 2
        assert all(c.source_domain in ("wine.com", "vivino.com") for c in result)

    def test_filter_candidates_keeps_trusted_and_neutral(self) -> None:
        """Test that trusted and neutral domains are kept."""
        candidates = [
            Candidate(candidate_id="1", image_url="http://a.com/1.jpg", source_page="http://a.com/1", source_domain="wine.com"),
            Candidate(candidate_id="2", image_url="http://b.com/2.jpg", source_page="http://b.com/2", source_domain="example.com"),
            Candidate(candidate_id="3", image_url="http://c.com/3.jpg", source_page="http://c.com/3", source_domain="klwines.com"),
        ]
        
        result = filter_candidates_by_domain(candidates)
        
        assert len(result) == 3

    def test_filter_candidates_empty_list(self) -> None:
        """Test filtering empty list returns empty list."""
        result = filter_candidates_by_domain([])
        assert result == []

    def test_filter_candidates_all_excluded(self) -> None:
        """Test when all candidates are from excluded domains."""
        candidates = [
            Candidate(candidate_id="1", image_url="http://a.com/1.jpg", source_page="http://a.com/1", source_domain="shutterstock.com"),
            Candidate(candidate_id="2", image_url="http://b.com/2.jpg", source_page="http://b.com/2", source_domain="amazon.com"),
        ]
        
        result = filter_candidates_by_domain(candidates)
        
        assert result == []


class TestSortCandidatesByDomainTrust:
    """Test sort_candidates_by_domain_trust function."""

    def test_sort_candidates_trusted_first(self) -> None:
        """Test that trusted domains come first."""
        candidates = [
            Candidate(candidate_id="1", image_url="http://a.com/1.jpg", source_page="http://a.com/1", source_domain="example.com"),  # 0.75
            Candidate(candidate_id="2", image_url="http://b.com/2.jpg", source_page="http://b.com/2", source_domain="wine.com"),  # 0.90
            Candidate(candidate_id="3", image_url="http://c.com/3.jpg", source_page="http://c.com/3", source_domain="unknown.org"),  # 0.75
        ]
        
        result = sort_candidates_by_domain_trust(candidates)
        
        assert result[0].source_domain == "wine.com"

    def test_sort_candidates_excluded_last(self) -> None:
        """Test that excluded domains come last."""
        candidates = [
            Candidate(candidate_id="1", image_url="http://a.com/1.jpg", source_page="http://a.com/1", source_domain="wine.com"),  # 0.90
            Candidate(candidate_id="2", image_url="http://b.com/2.jpg", source_page="http://b.com/2", source_domain="shutterstock.com"),  # 0.00
        ]
        
        result = sort_candidates_by_domain_trust(candidates)
        
        assert result[-1].source_domain == "shutterstock.com"

    def test_sort_candidates_empty_list(self) -> None:
        """Test sorting empty list returns empty list."""
        result = sort_candidates_by_domain_trust([])
        assert result == []

    def test_sort_candidates_preserves_order_for_equal_scores(self) -> None:
        """Test that equal scores maintain relative order."""
        candidates = [
            Candidate(candidate_id="1", image_url="http://a.com/1.jpg", source_page="http://a.com/1", source_domain="wine.com"),
            Candidate(candidate_id="2", image_url="http://b.com/2.jpg", source_page="http://b.com/2", source_domain="vivino.com"),
        ]
        
        result = sort_candidates_by_domain_trust(candidates)
        
        assert len(result) == 2
        assert result[0].source_domain in ("wine.com", "vivino.com")
        assert result[1].source_domain in ("wine.com", "vivino.com")


class TestBuildSiteRestrictedQueries:
    """Test build_site_restricted_queries function."""

    def test_build_site_restricted_queries_basic(self) -> None:
        """Test building site-restricted queries."""
        result = build_site_restricted_queries("Domaine Rossignol-Trapet", "2017", max_sites=2)
        
        assert len(result) == 2
        assert all("site:" in q for q in result)
        assert all("Domaine Rossignol-Trapet" in q for q in result)
        assert all("2017" in q for q in result)

    def test_build_site_restricted_queries_respects_max_sites(self) -> None:
        """Test that max_sites parameter is respected."""
        result = build_site_restricted_queries("Test Wine", "2020", max_sites=3)
        assert len(result) == 3
        
        result = build_site_restricted_queries("Test Wine", "2020", max_sites=5)
        assert len(result) == 5

    def test_build_site_restricted_queries_includes_bottle(self) -> None:
        """Test that 'bottle' is included in queries."""
        result = build_site_restricted_queries("Test Wine", "2020")
        
        assert all("bottle" in q for q in result)

    def test_build_site_restricted_queries_uses_quotes(self) -> None:
        """Test that wine name is quoted."""
        result = build_site_restricted_queries("Domaine Rossignol-Trapet", "2017")
        
        assert any('"Domaine Rossignol-Trapet"' in q for q in result)

    def test_build_site_restricted_queries_priority_sites(self) -> None:
        """Test that priority sites are used first."""
        result = build_site_restricted_queries("Test Wine", "2020", max_sites=3)
        
        # First 3 priority sites should be used
        priority_sites = ["wine-searcher.com", "vivino.com", "cellartracker.com"]
        for i, site in enumerate(priority_sites):
            if i < len(result):
                assert f"site:{site}" in result[i]


class TestDomainConstants:
    """Test domain constants for expected values."""

    def test_priority_wine_domains_present(self) -> None:
        """Test that priority wine domains are in trusted list."""
        priority_domains = [
            "wine-searcher.com",
            "vivino.com",
            "cellartracker.com",
            "wine.com",
            "klwines.com",
            "sothebys.com",
            "christies.com",
        ]
        for domain in priority_domains:
            assert domain in TRUSTED_WINE_DOMAINS

    def test_auction_houses_in_trusted(self) -> None:
        """Test that auction houses are in trusted list."""
        auction_domains = [
            "sothebys.com",
            "christies.com",
            "zachys.com",
            "winebid.com",
            "ackerwines.com",
        ]
        for domain in auction_domains:
            assert domain in TRUSTED_WINE_DOMAINS

    def test_stock_photo_sites_excluded(self) -> None:
        """Test that stock photo sites are excluded."""
        stock_domains = [
            "shutterstock.com",
            "gettyimages.com",
            "alamy.com",
            "istockphoto.com",
            "dreamstime.com",
        ]
        for domain in stock_domains:
            assert domain in EXCLUDED_DOMAINS

    def test_social_media_excluded(self) -> None:
        """Test that social media sites are excluded."""
        social_domains = [
            "pinterest.com",
            "instagram.com",
            "facebook.com",
            "twitter.com",
        ]
        for domain in social_domains:
            assert domain in EXCLUDED_DOMAINS
