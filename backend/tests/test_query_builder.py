"""Comprehensive tests for query_builder module - 100% coverage target."""

import pytest

from backend.app.models.sku import AnalyzeRequest, ParsedIdentity
from backend.app.services.query_builder import build_queries


class TestBuildQueries:
    """Test build_queries function."""

    def test_build_queries_with_complete_payload(self) -> None:
        """Test building queries with all fields present."""
        payload = AnalyzeRequest(
            wine_name="Domaine Rossignol-Trapet Latricieres-Chambertin",
            vintage="2017",
            format="750ml",
            region="Burgundy"
        )
        parsed = ParsedIdentity(
            producer="Domaine Rossignol-Trapet",
            appellation="Latricieres-Chambertin",
            vineyard_or_cuvee="Grand Cru",
            classification="grand cru",
            vintage="2017",
            format="750ml",
            region="Burgundy",
            raw_wine_name="Domaine Rossignol-Trapet Latricieres-Chambertin",
            normalized_wine_name="domaine rossignol trapet latricieres chambertin"
        )
        
        result = build_queries(payload, parsed)
        
        # Should include exact quoted query
        assert any('"Domaine Rossignol-Trapet Latricieres-Chambertin"' in q for q in result)
        # Should include producer + vintage query
        assert any("Domaine Rossignol-Trapet 2017" in q for q in result)
        # Should include vineyard-specific query
        assert any('"Grand Cru"' in q for q in result)

    def test_build_queries_with_minimal_payload(self) -> None:
        """Test building queries with minimal fields."""
        payload = AnalyzeRequest(
            wine_name="Champagne Andre Clouet",
            vintage="NV",
            format="750ml",
            region="Champagne"
        )
        parsed = ParsedIdentity(
            producer="Champagne Andre Clouet",
            vintage="NV",
            format="750ml",
            region="Champagne",
            raw_wine_name="Champagne Andre Clouet",
            normalized_wine_name="champagne andre clouet"
        )
        
        result = build_queries(payload, parsed)
        
        assert len(result) > 0
        # Should always include the wine name
        assert any("Champagne Andre Clouet" in q for q in result)

    def test_build_queries_without_producer(self) -> None:
        """Test building queries when producer is None."""
        payload = AnalyzeRequest(
            wine_name="Colgin Cellars Napa Valley 'Cariad'",
            vintage="2017",
            format="750ml",
            region="Napa"
        )
        parsed = ParsedIdentity(
            producer=None,
            vineyard_or_cuvee="Cariad",
            vintage="2017",
            format="750ml",
            region="Napa",
            raw_wine_name="Colgin Cellars Napa Valley 'Cariad'",
            normalized_wine_name="colgin cellars napa valley cariad"
        )
        
        result = build_queries(payload, parsed)
        
        # Should still create valid queries without producer
        assert len(result) > 0
        # Vineyard query should use wine_name instead of producer
        assert any("Cariad" in q for q in result)

    def test_build_queries_without_vineyard(self) -> None:
        """Test building queries when vineyard is None."""
        payload = AnalyzeRequest(
            wine_name="Domaine Rossignol-Trapet Latricieres-Chambertin",
            vintage="2017",
            format="750ml",
            region="Burgundy"
        )
        parsed = ParsedIdentity(
            producer="Domaine Rossignol-Trapet",
            appellation="Latricieres-Chambertin",
            vineyard_or_cuvee=None,
            vintage="2017",
            format="750ml",
            region="Burgundy",
            raw_wine_name="Domaine Rossignol-Trapet Latricieres-Chambertin",
            normalized_wine_name="domaine rossignol trapet latricieres chambertin"
        )
        
        result = build_queries(payload, parsed)
        
        # Should not include vineyard-specific query
        assert len(result) >= 3

    def test_build_queries_deduplicates(self) -> None:
        """Test that duplicate queries are removed."""
        payload = AnalyzeRequest(
            wine_name="Test Wine",
            vintage="2020",
            format="750ml",
            region="Test"
        )
        parsed = ParsedIdentity(
            producer="Test Wine",  # Same as wine_name in this case
            vintage="2020",
            format="750ml",
            region="Test",
            raw_wine_name="Test Wine",
            normalized_wine_name="test wine"
        )
        
        result = build_queries(payload, parsed)
        
        # Should have no duplicates
        assert len(result) == len(set(result))

    def test_build_queries_cleans_whitespace(self) -> None:
        """Test that extra whitespace is cleaned."""
        payload = AnalyzeRequest(
            wine_name="Test   Wine",
            vintage="2020",
            format="750ml",
            region="Test"
        )
        parsed = ParsedIdentity(
            producer="Test",
            vintage="2020",
            format="750ml",
            region="Test",
            raw_wine_name="Test   Wine",
            normalized_wine_name="test wine"
        )
        
        result = build_queries(payload, parsed)
        
        # No query should have multiple spaces
        for query in result:
            assert "  " not in query

    def test_build_queries_with_special_characters(self) -> None:
        """Test handling special characters in wine name."""
        payload = AnalyzeRequest(
            wine_name="Chateau L'Evangile",
            vintage="2015",
            format="750ml",
            region="Bordeaux"
        )
        parsed = ParsedIdentity(
            producer="Chateau L'Evangile",
            vintage="2015",
            format="750ml",
            region="Bordeaux",
            raw_wine_name="Chateau L'Evangile",
            normalized_wine_name="chateau levangile"
        )
        
        result = build_queries(payload, parsed)
        
        # Should handle apostrophe correctly
        assert any("Chateau L'Evangile" in q for q in result)

    def test_build_queries_order(self) -> None:
        """Test that exact query comes first."""
        payload = AnalyzeRequest(
            wine_name="Domaine Rossignol-Trapet",
            vintage="2017",
            format="750ml",
            region="Burgundy"
        )
        parsed = ParsedIdentity(
            producer="Domaine Rossignol-Trapet",
            vintage="2017",
            format="750ml",
            region="Burgundy",
            raw_wine_name="Domaine Rossignol-Trapet",
            normalized_wine_name="domaine rossignol trapet"
        )
        
        result = build_queries(payload, parsed)
        
        # First query should be the exact quoted query
        assert result[0] == '"Domaine Rossignol-Trapet" 2017 bottle'

    def test_build_queries_with_empty_region(self) -> None:
        """Test building queries with empty region."""
        payload = AnalyzeRequest(
            wine_name="Test Wine",
            vintage="2020",
            format="750ml",
            region=""
        )
        parsed = ParsedIdentity(
            producer="Test Wine",
            vintage="2020",
            format="750ml",
            region="",
            raw_wine_name="Test Wine",
            normalized_wine_name="test wine"
        )
        
        result = build_queries(payload, parsed)
        
        # Should still create valid queries
        assert len(result) > 0

    def test_build_queries_with_wine_bottle_suffix(self) -> None:
        """Test that normalized query includes 'bottle' suffix."""
        payload = AnalyzeRequest(
            wine_name="Test Wine",
            vintage="2020",
            format="750ml",
            region="Test"
        )
        parsed = ParsedIdentity(
            producer="Test Wine",
            vintage="2020",
            format="750ml",
            region="Test",
            raw_wine_name="Test Wine",
            normalized_wine_name="test wine"
        )
        
        result = build_queries(payload, parsed)
        
        # Normalized query should have 'bottle' suffix
        assert any("test wine 2020 bottle" in q for q in result)

    def test_build_queries_include_site_restricted_queries(self) -> None:
        payload = AnalyzeRequest(
            wine_name="Domaine Arlaud Morey-St-Denis 'Monts Luisants' 1er Cru",
            vintage="2019",
            format="750ml",
            region="Burgundy"
        )
        parsed = ParsedIdentity(
            producer="Domaine Arlaud",
            appellation="Morey-Saint-Denis",
            vineyard_or_cuvee="Monts Luisants",
            classification="1er cru",
            vintage="2019",
            format="750ml",
            region="Burgundy",
            raw_wine_name="Domaine Arlaud Morey-St-Denis 'Monts Luisants' 1er Cru",
            normalized_wine_name="domaine arlaud morey saint denis monts luisants 1er cru"
        )

        result = build_queries(payload, parsed)

        assert any("site:wine-searcher.com" in q for q in result)
        assert any('"Domaine Arlaud Morey-St-Denis \'Monts Luisants\' 1er Cru" 2019 label' == q for q in result)
