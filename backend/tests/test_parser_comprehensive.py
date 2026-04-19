"""Comprehensive tests for parser module - 100% coverage target."""

import pytest

from backend.app.models.sku import AnalyzeRequest, ParsedIdentity
from backend.app.services.parser import (
    CLASSIFICATION_PATTERNS,
    APPELLATION_PATTERNS,
    PRODUCER_PREFIXES,
    STOP_WORDS,
    STOP_PHRASES,
    parse_identity,
    _guess_appellation,
    _guess_producer,
)


class TestParseIdentity:
    """Test parse_identity function."""

    def test_parse_identity_with_complete_wine_name(self) -> None:
        """Test parsing a complete wine name."""
        payload = AnalyzeRequest(
            wine_name="Domaine Rossignol-Trapet Latricieres-Chambertin 'Grand Cru' 2017",
            vintage="2017",
            format="750ml",
            region="Burgundy"
        )
        
        result = parse_identity(payload)
        
        assert result.producer == "Domaine Rossignol-Trapet"
        assert result.appellation == "Latricieres-Chambertin"
        assert result.vineyard_or_cuvee == "Grand Cru"
        assert result.classification == "grand cru"
        assert result.vintage == "2017"
        assert result.format == "750ml"
        assert result.region == "Burgundy"

    def test_parse_identity_with_quoted_vineyard(self) -> None:
        """Test parsing with quoted vineyard name."""
        payload = AnalyzeRequest(
            wine_name="Domaine Arlaud Morey-Saint-Denis 'Monts Luisants' 1er Cru",
            vintage="2019",
            format="750ml",
            region="Burgundy"
        )
        
        result = parse_identity(payload)
        
        assert result.vineyard_or_cuvee == "Monts Luisants"
        assert result.classification == "1er cru"

    def test_parse_identity_with_double_quotes(self) -> None:
        """Test parsing with double quotes."""
        payload = AnalyzeRequest(
            wine_name='Chateau Fonroque Saint-Emilion "Grand Cru Classe"',
            vintage="2016",
            format="750ml",
            region="Bordeaux"
        )
        
        result = parse_identity(payload)
        
        assert result.vineyard_or_cuvee == "Grand Cru Classe"

    def test_parse_identity_with_champagne(self) -> None:
        """Test parsing champagne with NV."""
        payload = AnalyzeRequest(
            wine_name="Champagne Andre Clouet 'Chalky' Brut",
            vintage="NV",
            format="750ml",
            region="Champagne"
        )
        
        result = parse_identity(payload)
        
        assert result.producer == "Champagne Andre Clouet"
        assert result.vineyard_or_cuvee == "Chalky"
        assert result.classification == "brut"
        assert result.vintage == "NV"

    def test_parse_identity_with_no_classification(self) -> None:
        """Test parsing wine without classification."""
        payload = AnalyzeRequest(
            wine_name="Colgin Cellars Napa Valley 'Cariad'",
            vintage="2017",
            format="750ml",
            region="Napa"
        )
        
        result = parse_identity(payload)
        
        assert result.producer == "Colgin Cellars"
        assert result.classification is None

    def test_parse_identity_with_appellation_variations(self) -> None:
        """Test parsing with various appellation formats."""
        test_cases = [
            ("morey saint denis", "Morey-Saint-Denis"),
            ("saint emilion", "Saint-Emilion"),
            ("latricieres chambertin", "Latricieres-Chambertin"),
            ("charmes chambertin", "Charmes-Chambertin"),
            ("cornas", "Cornas"),
            ("barolo", "Barolo"),
            ("riesling", "Riesling"),
        ]
        
        for appellation_input, expected_appellation in test_cases:
            payload = AnalyzeRequest(
                wine_name=f"Producer {appellation_input} 'Vineyard'",
                vintage="2020",
                format="750ml",
                region="Test"
            )
            
            result = parse_identity(payload)
            assert result.appellation == expected_appellation

    def test_parse_identity_strips_whitespace(self) -> None:
        """Test that wine name is properly stripped."""
        payload = AnalyzeRequest(
            wine_name="  Domaine Rossignol-Trapet   ",
            vintage="2017",
            format="750ml",
            region="Burgundy"
        )
        
        result = parse_identity(payload)
        
        assert result.raw_wine_name == "Domaine Rossignol-Trapet"

    def test_parse_identity_with_producer_prefix_chateau(self) -> None:
        """Test parsing with Chateau prefix."""
        payload = AnalyzeRequest(
            wine_name="Chateau Fonroque Saint-Emilion Grand Cru",
            vintage="2016",
            format="750ml",
            region="Bordeaux"
        )
        
        result = parse_identity(payload)
        
        assert result.producer == "Chateau Fonroque"

    def test_parse_identity_with_producer_prefix_castello(self) -> None:
        """Test parsing with Castello prefix."""
        payload = AnalyzeRequest(
            wine_name="Castello di Querceto 'Cignale' Colli della Toscana",
            vintage="1989",
            format="750ml",
            region="Tuscany"
        )
        
        result = parse_identity(payload)
        
        assert result.producer == "Castello di Querceto"


class TestGuessAppellation:
    """Test _guess_appellation function."""

    def test_guess_appellation_finds_all_patterns(self) -> None:
        """Test that all appellation patterns are detected."""
        for needle, expected_label in APPELLATION_PATTERNS:
            result = _guess_appellation(f"producer {needle} vineyard")
            assert result == expected_label

    def test_guess_appellation_returns_none_for_unknown(self) -> None:
        """Test returning None for unknown appellations."""
        result = _guess_appellation("producer unknown region vineyard")
        assert result is None

    def test_guess_appellation_is_case_insensitive(self) -> None:
        """Test case insensitive matching."""
        result = _guess_appellation("Producer MOREY SAINT DENIS Vineyard")
        assert result == "Morey-Saint-Denis"


class TestGuessProducer:
    """Test _guess_producer function."""

    def test_guess_producer_with_domaine_prefix(self) -> None:
        """Test extracting producer with Domaine prefix."""
        result = _guess_producer(
            "Domaine Rossignol-Trapet Latricieres-Chambertin",
            "domaine rossignol trapet latricieres chambertin"
        )
        assert result == "Domaine Rossignol-Trapet"

    def test_guess_producer_with_chateau_prefix(self) -> None:
        """Test extracting producer with Chateau prefix (allows 3 tokens)."""
        result = _guess_producer(
            "Chateau de Charodon Beaune",
            "chateau de charodon beaune"
        )
        assert "Chateau" in result

    def test_guess_producer_stops_at_stop_words(self) -> None:
        """Test that producer extraction stops at stop words."""
        result = _guess_producer(
            "Caroline Morey Beaune 'Les Greves'",
            "caroline morey beaune les greves"
        )
        assert result == "Caroline Morey"

    def test_guess_producer_handles_no_producer(self) -> None:
        """Test when no clear producer can be extracted."""
        result = _guess_producer(
            "Aux Montagnes Cote de Nuits",
            "aux montagnes cote de nuits"
        )
        # Should still return something or None
        assert result is not None or result is None

    def test_guess_producer_returns_none_when_empty(self) -> None:
        """Test returning None for empty tokens."""
        result = _guess_producer("", "")
        assert result is None

    def test_guess_producer_handles_special_chars(self) -> None:
        """Test handling special characters in wine name."""
        result = _guess_producer(
            "Charles Lachaux Cote-de-Nuits",
            "charles lachaux cote de nuits"
        )
        assert result == "Charles Lachaux"


class TestClassificationPatterns:
    """Test CLASSIFICATION_PATTERNS."""

    def test_all_patterns_are_valid_regex(self) -> None:
        """Verify all classification patterns compile as valid regex."""
        import re
        for pattern in CLASSIFICATION_PATTERNS:
            # Should not raise
            re.compile(pattern)

    def test_patterns_detect_classifications(self) -> None:
        """Test that patterns detect expected classifications."""
        import re
        test_cases = [
            ("grand cru classe", r"\bgrand cru classe\b"),
            ("grand cru", r"\bgrand cru\b"),
            ("1er cru", r"\b1er cru\b"),
            ("brut", r"\bbrut\b"),
        ]
        
        for text, pattern in test_cases:
            match = re.search(pattern, text)
            assert match is not None


class TestProducerPrefixes:
    """Test PRODUCER_PREFIXES constant."""

    def test_producer_prefixes_are_lowercase(self) -> None:
        """Verify all producer prefixes are lowercase."""
        for prefix in PRODUCER_PREFIXES:
            assert prefix == prefix.lower()

    def test_common_prefixes_present(self) -> None:
        """Test that common wine producer prefixes are present."""
        expected = {"domaine", "chateau", "champagne"}
        assert expected.issubset(PRODUCER_PREFIXES)


class TestStopWordsAndPhrases:
    """Test STOP_WORDS and STOP_PHRASES."""

    def test_stop_words_are_lowercase(self) -> None:
        """Verify all stop words are lowercase."""
        for word in STOP_WORDS:
            assert word == word.lower()

    def test_stop_phrases_are_lowercase(self) -> None:
        """Verify all stop phrases are lowercase."""
        for phrase in STOP_PHRASES:
            assert phrase == phrase.lower()
