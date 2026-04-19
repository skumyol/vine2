"""Comprehensive tests for scorer module - 100% coverage target."""

import pytest

from backend.app.models.result import ScoreBreakdown
from backend.app.services.scorer import (
    WEIGHTS,
    build_score_breakdown,
    normalized_total_score,
    total_score,
)


class TestBuildScoreBreakdown:
    """Test build_score_breakdown function with all input combinations."""

    def test_build_score_breakdown_with_maximum_values(self) -> None:
        """Test with all scores at maximum (1.0)."""
        result = build_score_breakdown(
            producer=1.0,
            appellation=1.0,
            vineyard_or_cuvee=1.0,
            classification=1.0,
            vintage=1.0,
            ocr_clarity=1.0,
            image_quality=1.0,
            source_trust=1.0,
        )
        
        assert result.producer == WEIGHTS["producer"] * 1.0
        assert result.appellation == WEIGHTS["appellation"] * 1.0
        assert result.vineyard_or_cuvee == WEIGHTS["vineyard_or_cuvee"] * 1.0
        assert result.classification == WEIGHTS["classification"] * 1.0
        assert result.vintage == WEIGHTS["vintage"] * 1.0
        assert result.ocr_clarity == WEIGHTS["ocr_clarity"] * 1.0
        assert result.image_quality == WEIGHTS["image_quality"] * 1.0
        assert result.source_trust == WEIGHTS["source_trust"] * 1.0

    def test_build_score_breakdown_with_zero_values(self) -> None:
        """Test with all scores at minimum (0.0)."""
        result = build_score_breakdown(
            producer=0.0,
            appellation=0.0,
            vineyard_or_cuvee=0.0,
            classification=0.0,
            vintage=0.0,
            ocr_clarity=0.0,
            image_quality=0.0,
            source_trust=0.0,
        )
        
        assert all(value == 0.0 for value in [
            result.producer, result.appellation, result.vineyard_or_cuvee,
            result.classification, result.vintage, result.ocr_clarity,
            result.image_quality, result.source_trust
        ])

    def test_build_score_breakdown_with_partial_values(self) -> None:
        """Test with mixed scores."""
        result = build_score_breakdown(
            producer=0.8,
            appellation=0.6,
            vineyard_or_cuvee=0.9,
            classification=0.5,
            vintage=0.7,
            ocr_clarity=0.85,
            image_quality=0.75,
            source_trust=0.9,
        )
        
        assert result.producer == 0.8 * WEIGHTS["producer"]
        assert result.appellation == 0.6 * WEIGHTS["appellation"]
        assert result.vineyard_or_cuvee == 0.9 * WEIGHTS["vineyard_or_cuvee"]
        assert result.classification == 0.5 * WEIGHTS["classification"]
        assert result.vintage == 0.7 * WEIGHTS["vintage"]
        assert result.ocr_clarity == 0.85 * WEIGHTS["ocr_clarity"]
        assert result.image_quality == 0.75 * WEIGHTS["image_quality"]
        assert result.source_trust == 0.9 * WEIGHTS["source_trust"]

    def test_build_score_breakdown_weights_sum_to_one(self) -> None:
        """Verify that weights sum to 1.0 for proper normalization."""
        total_weight = sum(WEIGHTS.values())
        assert total_weight == 1.0


class TestTotalScore:
    """Test total_score function."""

    def test_total_score_with_all_zeros(self) -> None:
        """Test total_score with zero breakdown."""
        breakdown = ScoreBreakdown()
        assert total_score(breakdown) == 0.0

    def test_total_score_with_maximum_breakdown(self) -> None:
        """Test total_score with maximum weighted values."""
        breakdown = build_score_breakdown(
            producer=1.0, appellation=1.0, vineyard_or_cuvee=1.0,
            classification=1.0, vintage=1.0, ocr_clarity=1.0,
            image_quality=1.0, source_trust=1.0
        )
        assert total_score(breakdown) == 1.0

    def test_total_score_rounds_to_four_decimals(self) -> None:
        """Test that total_score rounds to 4 decimal places."""
        breakdown = ScoreBreakdown(
            producer=0.12345678,
            appellation=0.0,
            vineyard_or_cuvee=0.0,
            classification=0.0,
            vintage=0.0,
            ocr_clarity=0.0,
            image_quality=0.0,
            source_trust=0.0,
        )
        result = total_score(breakdown)
        # Should be rounded to 4 decimal places
        assert result == round(0.12345678, 4)


class TestNormalizedTotalScore:
    """Test normalized_total_score function."""

    def test_normalized_total_score_with_normal_active_weight(self) -> None:
        """Test normalization with typical active weight."""
        breakdown = build_score_breakdown(
            producer=1.0, appellation=1.0, vineyard_or_cuvee=1.0,
            classification=0.0, vintage=0.0, ocr_clarity=1.0,
            image_quality=1.0, source_trust=1.0
        )
        # Active weight when producer, appellation, vineyard are present
        active_weight = 0.25 + 0.20 + 0.20 + 0.05 + 0.05 + 0.05  # = 0.80
        result = normalized_total_score(breakdown, active_weight)
        expected = round(total_score(breakdown) / active_weight, 4)
        assert result == expected

    def test_normalized_total_score_with_zero_active_weight(self) -> None:
        """Test normalization with zero active weight returns 0.0."""
        breakdown = build_score_breakdown(
            producer=1.0, appellation=1.0, vineyard_or_cuvee=1.0,
            classification=1.0, vintage=1.0, ocr_clarity=1.0,
            image_quality=1.0, source_trust=1.0
        )
        result = normalized_total_score(breakdown, 0.0)
        assert result == 0.0

    def test_normalized_total_score_with_negative_active_weight(self) -> None:
        """Test normalization with negative active weight returns 0.0."""
        breakdown = build_score_breakdown(
            producer=1.0, appellation=1.0, vineyard_or_cuvee=1.0,
            classification=1.0, vintage=1.0, ocr_clarity=1.0,
            image_quality=1.0, source_trust=1.0
        )
        result = normalized_total_score(breakdown, -0.5)
        assert result == 0.0

    def test_normalized_total_score_with_full_active_weight(self) -> None:
        """Test normalization when active_weight equals sum of all weights."""
        breakdown = build_score_breakdown(
            producer=1.0, appellation=1.0, vineyard_or_cuvee=1.0,
            classification=1.0, vintage=1.0, ocr_clarity=1.0,
            image_quality=1.0, source_trust=1.0
        )
        result = normalized_total_score(breakdown, 1.0)
        assert result == 1.0

    def test_normalized_total_score_rounding(self) -> None:
        """Test that normalized score is rounded to 4 decimals."""
        breakdown = ScoreBreakdown(producer=0.12345678 * WEIGHTS["producer"])
        result = normalized_total_score(breakdown, WEIGHTS["producer"])
        expected = round(0.12345678, 4)
        assert result == expected


class TestWeightsConfiguration:
    """Test WEIGHTS configuration values."""

    def test_weights_has_all_required_keys(self) -> None:
        """Verify all expected weight keys are present."""
        required_keys = [
            "producer", "appellation", "vineyard_or_cuvee", "classification",
            "vintage", "ocr_clarity", "image_quality", "source_trust"
        ]
        for key in required_keys:
            assert key in WEIGHTS

    def test_weights_are_positive(self) -> None:
        """Verify all weights are positive values."""
        for key, value in WEIGHTS.items():
            assert value > 0, f"Weight {key} should be positive"

    def test_identity_weights_sum_to_higher_than_quality_weights(self) -> None:
        """Verify identity weights (producer, appellation, vineyard) are prioritized."""
        identity_weights = WEIGHTS["producer"] + WEIGHTS["appellation"] + WEIGHTS["vineyard_or_cuvee"]
        quality_weights = WEIGHTS["ocr_clarity"] + WEIGHTS["image_quality"] + WEIGHTS["source_trust"]
        assert identity_weights > quality_weights
