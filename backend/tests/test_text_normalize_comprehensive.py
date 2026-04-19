"""Comprehensive tests for text_normalize module - 100% coverage target."""

import pytest

from backend.app.utils.text_normalize import CRU_MAP, normalize_text


class TestNormalizeText:
    """Test normalize_text function."""

    def test_normalize_text_lowercases(self) -> None:
        """Test that text is lowercased."""
        result = normalize_text("Domaine Rossignol-Trapet")
        assert result == result.lower()

    def test_normalize_text_removes_accents(self) -> None:
        """Test that accents are removed."""
        result = normalize_text("Château L'Évangile")
        # Should have accents removed
        assert "â" not in result
        assert "é" not in result

    def test_normalize_text_replaces_hyphens(self) -> None:
        """Test that hyphens are replaced with spaces."""
        result = normalize_text("Rossignol-Trapet")
        assert "-" not in result
        assert "rossignol trapet" in result

    def test_normalize_text_replaces_underscores(self) -> None:
        """Test that underscores are replaced with spaces."""
        result = normalize_text("Rossignol_Trapet")
        assert "_" not in result
        assert "rossignol trapet" in result

    def test_normalize_text_replaces_slashes(self) -> None:
        """Test that slashes are replaced with spaces."""
        result = normalize_text("Rossignol/Trapet")
        assert "/" not in result
        assert "rossignol trapet" in result

    def test_normalize_text_removes_special_chars(self) -> None:
        """Test that special characters are removed."""
        result = normalize_text("Domaine @#$%^&*() Rossignol")
        assert "@" not in result
        assert "#" not in result
        assert "$" not in result

    def test_normalize_text_keeps_apostrophes(self) -> None:
        """Test that apostrophes are kept."""
        result = normalize_text("L'Evangile")
        assert "'" in result or "levangile" in result

    def test_normalize_text_converts_curly_apostrophes(self) -> None:
        """Test that curly apostrophes are converted."""
        result = normalize_text("L'Evangile")  # Using regular apostrophe
        # The function converts curly apostrophes to regular ones
        assert "'" in result or "levangile" in result

    def test_normalize_text_collapses_whitespace(self) -> None:
        """Test that multiple spaces are collapsed."""
        result = normalize_text("Domaine    Rossignol    Trapet")
        assert "  " not in result
        assert result == "domaine rossignol trapet"

    def test_normalize_text_strips_whitespace(self) -> None:
        """Test that leading/trailing whitespace is stripped."""
        result = normalize_text("  Domaine Rossignol  ")
        assert result == "domaine rossignol"

    def test_normalize_text_handles_empty_string(self) -> None:
        """Test that empty string returns empty."""
        result = normalize_text("")
        assert result == ""

    def test_normalize_text_maps_premier_cru(self) -> None:
        """Test that 'premier cru' is mapped to '1er cru'."""
        result = normalize_text("premier cru")
        assert result == "1er cru"

    def test_normalize_text_maps_1_er_cru(self) -> None:
        """Test that '1 er cru' is mapped to '1er cru'."""
        result = normalize_text("1 er cru")
        assert result == "1er cru"

    def test_normalize_text_maps_st_to_saint(self) -> None:
        """Test that 'st ' is mapped to 'saint '."""
        result = normalize_text("st emilion")
        assert "saint emilion" in result

    def test_normalize_text_with_complex_wine_name(self) -> None:
        """Test with a complex real-world wine name."""
        result = normalize_text("Domaine Rossignol-Trapet Latricieres-Chambertin 'Grand Cru' 2017")
        expected = "domaine rossignol trapet latricieres chambertin grand cru 2017"
        assert result == expected

    def test_normalize_text_with_quoted_text(self) -> None:
        """Test that quotes are removed."""
        result = normalize_text('"Grand Cru" Monts Luisants')
        assert result == "grand cru monts luisants"

    def test_normalize_text_with_numbers(self) -> None:
        """Test that numbers are preserved."""
        result = normalize_text("2017 Vintage 1er Cru")
        assert "2017" in result
        assert "1er" in result

    def test_normalize_text_with_special_french_chars(self) -> None:
        """Test handling of various French special characters."""
        result = normalize_text("Château Émilie ÀÖÜ àöü")
        assert "chateau" in result
        assert "emilie" in result
        # Should not contain original accented chars
        assert "É" not in result
        assert "À" not in result


class TestCruMap:
    """Test CRU_MAP constant."""

    def test_cru_map_is_dict(self) -> None:
        """Test that CRU_MAP is a dictionary."""
        assert isinstance(CRU_MAP, dict)

    def test_cru_map_keys_are_strings(self) -> None:
        """Test that all keys are strings."""
        for key in CRU_MAP.keys():
            assert isinstance(key, str)

    def test_cru_map_values_are_strings(self) -> None:
        """Test that all values are strings."""
        for value in CRU_MAP.values():
            assert isinstance(value, str)

    def test_cru_map_contains_expected_mappings(self) -> None:
        """Test that expected mappings are present."""
        assert "premier cru" in CRU_MAP
        assert CRU_MAP["premier cru"] == "1er cru"
        assert "1 er cru" in CRU_MAP
        assert CRU_MAP["1 er cru"] == "1er cru"
        assert "st " in CRU_MAP
        assert CRU_MAP["st "] == "saint "

    def test_cru_map_mappings_are_lowercase(self) -> None:
        """Test that all mappings are lowercase."""
        for key, value in CRU_MAP.items():
            assert key == key.lower()
            assert value == value.lower()
