"""Comprehensive tests for matcher module - 100% coverage target."""

import pytest

from backend.app.core.constants import FieldStatus
from backend.app.models.result import FieldMatch
from backend.app.models.sku import ParsedIdentity
from backend.app.services.matcher import (
    KNOWN_CLASSIFICATIONS,
    build_field_matches,
    is_readable_enough,
    _match_classification,
    _match_phrase,
    _match_vintage,
    _phrase_confidence,
)


class TestBuildFieldMatches:
    """Test build_field_matches function."""

    def test_build_field_matches_with_complete_match(self) -> None:
        """Test with all fields matching observed text."""
        parsed = ParsedIdentity(
            producer="Domaine Rossignol-Trapet",
            appellation="Latricieres-Chambertin",
            vineyard_or_cuvee="Grand Cru",
            classification="grand cru",
            vintage="2017",
            raw_wine_name="test",
            normalized_wine_name="test"
        )
        observed_text = "Domaine Rossignol-Trapet Latricieres-Chambertin Grand Cru 2017"
        
        result = build_field_matches(parsed, observed_text)
        
        assert result["producer"].status == FieldStatus.MATCH
        assert result["appellation"].status == FieldStatus.MATCH
        assert result["vineyard_or_cuvee"].status == FieldStatus.MATCH
        assert result["classification"].status == FieldStatus.MATCH
        assert result["vintage"].status == FieldStatus.MATCH

    def test_build_field_matches_with_partial_match(self) -> None:
        """Test with some fields matching."""
        parsed = ParsedIdentity(
            producer="Domaine Rossignol-Trapet",
            appellation="Latricieres-Chambertin",
            vineyard_or_cuvee=None,
            classification=None,
            vintage="2017",
            raw_wine_name="test",
            normalized_wine_name="test"
        )
        observed_text = "Domaine Rossignol-Trapet 2018"
        
        result = build_field_matches(parsed, observed_text)
        
        assert result["producer"].status == FieldStatus.MATCH
        assert result["appellation"].status == FieldStatus.UNVERIFIED
        assert result["vineyard_or_cuvee"].status == FieldStatus.NO_SIGNAL
        assert result["classification"].status == FieldStatus.NO_SIGNAL
        assert result["vintage"].status == FieldStatus.CONFLICT

    def test_build_field_matches_with_no_match(self) -> None:
        """Test with no fields matching."""
        parsed = ParsedIdentity(
            producer="Domaine Rossignol-Trapet",
            appellation="Latricieres-Chambertin",
            vineyard_or_cuvee="Grand Cru",
            classification="grand cru",
            vintage="2017",
            raw_wine_name="test",
            normalized_wine_name="test"
        )
        observed_text = "Some completely unrelated text about apples"
        
        result = build_field_matches(parsed, observed_text)
        
        assert result["producer"].status == FieldStatus.UNVERIFIED
        assert result["appellation"].status == FieldStatus.UNVERIFIED
        assert result["vineyard_or_cuvee"].status == FieldStatus.UNVERIFIED
        assert result["classification"].status == FieldStatus.UNVERIFIED
        assert result["vintage"].status == FieldStatus.UNVERIFIED

    def test_build_field_matches_extracts_years_from_text(self) -> None:
        """Test that years are correctly extracted from observed text."""
        parsed = ParsedIdentity(
            producer="Test Producer",
            vintage="2019",
            raw_wine_name="test",
            normalized_wine_name="test"
        )
        observed_text = "Multiple years 1990 2005 2019 2020"
        
        result = build_field_matches(parsed, observed_text)
        
        assert result["vintage"].status == FieldStatus.MATCH
        assert result["vintage"].extracted == "2019"

    def test_build_field_matches_handles_nv_vintage(self) -> None:
        """Test handling of NV (non-vintage) designation."""
        parsed = ParsedIdentity(
            producer="Champagne Andre Clouet",
            vintage="nv",
            raw_wine_name="test",
            normalized_wine_name="test"
        )
        observed_text = "Champagne Andre Clouet NV Brut"
        
        result = build_field_matches(parsed, observed_text)
        
        assert result["vintage"].status == FieldStatus.MATCH


class TestIsReadableEnough:
    """Test is_readable_enough function."""

    def test_is_readable_enough_with_long_text(self) -> None:
        """Test with text having sufficient tokens."""
        text = "Domaine Rossignol-Trapet Latricieres-Chambertin Grand Cru 2017"
        assert is_readable_enough(text) is True

    def test_is_readable_enough_with_exactly_four_tokens(self) -> None:
        """Test with exactly 4 tokens (boundary condition)."""
        text = "One two three four"
        assert is_readable_enough(text) is True

    def test_is_readable_enough_with_three_tokens(self) -> None:
        """Test with 3 tokens (below threshold)."""
        text = "One two three"
        assert is_readable_enough(text) is False

    def test_is_readable_enough_with_empty_text(self) -> None:
        """Test with empty string."""
        assert is_readable_enough("") is False

    def test_is_readable_enough_with_single_char_tokens(self) -> None:
        """Test that single character tokens are filtered out."""
        text = "a b c d e f g h"  # 8 single-char tokens, should be filtered
        assert is_readable_enough(text) is False

    def test_is_readable_enough_with_mixed_tokens(self) -> None:
        """Test with mix of single and multi-char tokens."""
        text = "a big test here"  # 'a' filtered, 3 multi-char tokens
        assert is_readable_enough(text) is False


class TestMatchPhrase:
    """Test _match_phrase function."""

    def test_match_phrase_with_exact_match(self) -> None:
        """Test exact phrase match."""
        result = _match_phrase("Domaine Rossignol-Trapet", "domaine rossignol trapet grand cru")
        
        assert result.status == FieldStatus.MATCH
        assert result.confidence == 0.95  # 3+ tokens = 0.95
        assert result.extracted == "Domaine Rossignol-Trapet"

    def test_match_phrase_with_two_token_phrase(self) -> None:
        """Test 2-token phrase match."""
        result = _match_phrase("Rossignol-Trapet", "domaine rossignol trapet")
        
        assert result.status == FieldStatus.MATCH
        assert result.confidence == 0.9  # 2 tokens = 0.9

    def test_match_phrase_with_single_token(self) -> None:
        """Test single token match."""
        result = _match_phrase("Trapet", "domaine rossignol trapet")
        
        assert result.status == FieldStatus.MATCH
        assert result.confidence == 0.85  # 1 token = 0.85

    def test_match_phrase_with_no_target(self) -> None:
        """Test with None target."""
        result = _match_phrase(None, "some observed text")
        
        assert result.status == FieldStatus.NO_SIGNAL
        assert result.confidence == 0.0

    def test_match_phrase_with_empty_observed(self) -> None:
        """Test with empty observed text."""
        result = _match_phrase("Domaine Rossignol-Trapet", "")
        
        assert result.status == FieldStatus.UNVERIFIED
        assert result.confidence == 0.0

    def test_match_phrase_with_no_match(self) -> None:
        """Test when phrase is not in observed text."""
        result = _match_phrase("Domaine Rossignol-Trapet", "some unrelated text")
        
        assert result.status == FieldStatus.UNVERIFIED
        assert result.confidence == 0.0


class TestMatchClassification:
    """Test _match_classification function."""

    def test_match_classification_with_exact_match(self) -> None:
        """Test exact classification match."""
        result = _match_classification("grand cru", "domaine rossignol trapet grand cru 2017")
        
        assert result.status == FieldStatus.MATCH
        assert result.confidence == 0.9

    def test_match_classification_with_conflict(self) -> None:
        """Test when different classification is found."""
        result = _match_classification("grand cru", "1er cru monts luisants 2019")
        
        assert result.status == FieldStatus.CONFLICT
        assert result.extracted == "1er cru"

    def test_match_classification_with_no_target(self) -> None:
        """Test with None target."""
        result = _match_classification(None, "some text")
        
        assert result.status == FieldStatus.NO_SIGNAL

    def test_match_classification_with_no_classification_in_text(self) -> None:
        """Test when no known classification in observed text."""
        result = _match_classification("grand cru", "some text without classification")
        
        assert result.status == FieldStatus.UNVERIFIED

    def test_match_classification_detects_all_known_classifications(self) -> None:
        """Test that all known classifications can be detected."""
        for classification in KNOWN_CLASSIFICATIONS:
            result = _match_classification(classification, f"wine {classification} 2019")
            assert result.status == FieldStatus.MATCH


class TestMatchVintage:
    """Test _match_vintage function."""

    def test_match_vintage_with_exact_match(self) -> None:
        """Test exact vintage match."""
        result = _match_vintage("2017", ["2017"])
        
        assert result.status == FieldStatus.MATCH
        assert result.confidence == 0.95

    def test_match_vintage_with_conflict(self) -> None:
        """Test when different vintage is found."""
        result = _match_vintage("2017", ["2018", "2019"])
        
        assert result.status == FieldStatus.CONFLICT
        assert result.extracted == "2018, 2019"

    def test_match_vintage_with_no_years_found(self) -> None:
        """Test when no years in observed text."""
        result = _match_vintage("2017", [])
        
        assert result.status == FieldStatus.UNVERIFIED

    def test_match_vintage_with_no_target(self) -> None:
        """Test with None target."""
        result = _match_vintage(None, ["2017"])
        
        assert result.status == FieldStatus.NO_SIGNAL

    def test_match_vintage_removes_duplicates(self) -> None:
        """Test that duplicate years are removed."""
        result = _match_vintage("2017", ["2017", "2017", "2018"])
        
        assert result.status == FieldStatus.MATCH

    def test_match_vintage_handles_nv(self) -> None:
        """Test handling of NV (non-vintage)."""
        result = _match_vintage("nv", ["nv"])
        
        assert result.status == FieldStatus.MATCH


class TestPhraseConfidence:
    """Test _phrase_confidence function."""

    def test_phrase_confidence_with_three_plus_tokens(self) -> None:
        """Test confidence for 3+ token phrases."""
        assert _phrase_confidence("one two three") == 0.95
        assert _phrase_confidence("one two three four five") == 0.95

    def test_phrase_confidence_with_two_tokens(self) -> None:
        """Test confidence for 2 token phrases."""
        assert _phrase_confidence("one two") == 0.9

    def test_phrase_confidence_with_one_token(self) -> None:
        """Test confidence for single token phrases."""
        assert _phrase_confidence("one") == 0.85


class TestKnownClassifications:
    """Test KNOWN_CLASSIFICATIONS constant."""

    def test_known_classifications_is_non_empty(self) -> None:
        """Verify classifications list is not empty."""
        assert len(KNOWN_CLASSIFICATIONS) > 0

    def test_known_classifications_are_lowercase(self) -> None:
        """Verify all classifications are lowercase for matching."""
        for classification in KNOWN_CLASSIFICATIONS:
            assert classification == classification.lower()
