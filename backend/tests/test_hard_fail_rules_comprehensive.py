"""Comprehensive tests for hard_fail_rules module - 100% coverage target."""

import pytest

from backend.app.core.constants import FailReason, FieldStatus
from backend.app.models.result import FieldMatch
from backend.app.models.sku import ParsedIdentity
from backend.app.services.hard_fail_rules import (
    HardFailEvaluation,
    evaluate_hard_fail,
    _missing_required_field,
)


class TestEvaluateHardFail:
    """Test evaluate_hard_fail function."""

    def test_evaluate_hard_fail_with_producer_mismatch(self) -> None:
        """Test hard fail when producer is missing but text is readable."""
        parsed = ParsedIdentity(
            producer="Domaine Rossignol-Trapet",
            raw_wine_name="test",
            normalized_wine_name="test"
        )
        field_matches = {
            "producer": FieldMatch(target="Domaine Rossignol-Trapet", status=FieldStatus.UNVERIFIED, confidence=0.0),
            "appellation": FieldMatch(target="Latricieres-Chambertin", status=FieldStatus.MATCH, confidence=0.95),
            "vineyard_or_cuvee": FieldMatch(status=FieldStatus.NO_SIGNAL),
            "classification": FieldMatch(status=FieldStatus.NO_SIGNAL),
            "vintage": FieldMatch(target="2017", status=FieldStatus.MATCH, confidence=0.95),
        }
        
        result = evaluate_hard_fail(parsed, field_matches, "some readable text here")
        
        assert result.should_fail is True
        assert result.reason == FailReason.PRODUCER_MISMATCH

    def test_evaluate_hard_fail_with_appellation_mismatch(self) -> None:
        """Test hard fail when appellation is missing but text is readable."""
        parsed = ParsedIdentity(
            producer="Domaine Rossignol-Trapet",
            appellation="Latricieres-Chambertin",
            raw_wine_name="test",
            normalized_wine_name="test"
        )
        field_matches = {
            "producer": FieldMatch(target="Domaine Rossignol-Trapet", status=FieldStatus.MATCH, confidence=0.95),
            "appellation": FieldMatch(target="Latricieres-Chambertin", status=FieldStatus.UNVERIFIED, confidence=0.0),
            "vineyard_or_cuvee": FieldMatch(status=FieldStatus.NO_SIGNAL),
            "classification": FieldMatch(status=FieldStatus.NO_SIGNAL),
            "vintage": FieldMatch(target="2017", status=FieldStatus.MATCH, confidence=0.95),
        }
        
        result = evaluate_hard_fail(parsed, field_matches, "some readable text here")
        
        assert result.should_fail is True
        assert result.reason == FailReason.APPELLATION_MISMATCH

    def test_evaluate_hard_fail_with_vineyard_mismatch(self) -> None:
        """Test hard fail when vineyard is required but missing."""
        parsed = ParsedIdentity(
            producer="Domaine Arlaud",
            appellation="Morey-Saint-Denis",
            vineyard_or_cuvee="Monts Luisants",
            raw_wine_name="test",
            normalized_wine_name="test"
        )
        field_matches = {
            "producer": FieldMatch(target="Domaine Arlaud", status=FieldStatus.MATCH, confidence=0.95),
            "appellation": FieldMatch(target="Morey-Saint-Denis", status=FieldStatus.MATCH, confidence=0.95),
            "vineyard_or_cuvee": FieldMatch(target="Monts Luisants", status=FieldStatus.UNVERIFIED, confidence=0.0),
            "classification": FieldMatch(status=FieldStatus.NO_SIGNAL),
            "vintage": FieldMatch(target="2019", status=FieldStatus.MATCH, confidence=0.95),
        }
        
        result = evaluate_hard_fail(parsed, field_matches, "some readable text here")
        
        assert result.should_fail is True
        assert result.reason == FailReason.VINEYARD_OR_CUVEE_MISMATCH

    def test_evaluate_hard_fail_with_classification_conflict(self) -> None:
        """Test hard fail when classification conflicts."""
        parsed = ParsedIdentity(
            classification="grand cru",
            raw_wine_name="test",
            normalized_wine_name="test"
        )
        field_matches = {
            "producer": FieldMatch(status=FieldStatus.NO_SIGNAL),
            "appellation": FieldMatch(status=FieldStatus.NO_SIGNAL),
            "vineyard_or_cuvee": FieldMatch(status=FieldStatus.NO_SIGNAL),
            "classification": FieldMatch(target="grand cru", status=FieldStatus.CONFLICT, confidence=0.9),
            "vintage": FieldMatch(status=FieldStatus.NO_SIGNAL),
        }
        
        result = evaluate_hard_fail(parsed, field_matches, "some readable text")
        
        assert result.should_fail is True
        assert result.reason == FailReason.CLASSIFICATION_CONFLICT

    def test_evaluate_hard_fail_with_vintage_conflict(self) -> None:
        """Test hard fail when vintage conflicts."""
        parsed = ParsedIdentity(
            vintage="2017",
            raw_wine_name="test",
            normalized_wine_name="test"
        )
        field_matches = {
            "producer": FieldMatch(status=FieldStatus.NO_SIGNAL),
            "appellation": FieldMatch(status=FieldStatus.NO_SIGNAL),
            "vineyard_or_cuvee": FieldMatch(status=FieldStatus.NO_SIGNAL),
            "classification": FieldMatch(status=FieldStatus.NO_SIGNAL),
            "vintage": FieldMatch(target="2017", status=FieldStatus.CONFLICT, confidence=0.95),
        }
        
        result = evaluate_hard_fail(parsed, field_matches, "some readable text")
        
        assert result.should_fail is True
        assert result.reason == FailReason.VINTAGE_MISMATCH

    def test_evaluate_hard_fail_with_unreadable_core_identity(self) -> None:
        """Test hard fail when core identity is unreadable."""
        parsed = ParsedIdentity(
            producer="Domaine Rossignol-Trapet",
            appellation="Latricieres-Chambertin",
            raw_wine_name="test",
            normalized_wine_name="test"
        )
        field_matches = {
            "producer": FieldMatch(target="Domaine Rossignol-Trapet", status=FieldStatus.UNVERIFIED, confidence=0.0),
            "appellation": FieldMatch(target="Latricieres-Chambertin", status=FieldStatus.UNVERIFIED, confidence=0.0),
            "vineyard_or_cuvee": FieldMatch(status=FieldStatus.NO_SIGNAL),
            "classification": FieldMatch(status=FieldStatus.NO_SIGNAL),
            "vintage": FieldMatch(status=FieldStatus.NO_SIGNAL),
        }
        
        # Text with less than 4 tokens (not readable enough)
        result = evaluate_hard_fail(parsed, field_matches, "hi")
        
        assert result.should_fail is True
        assert result.reason == FailReason.UNREADABLE_CORE_IDENTITY

    def test_evaluate_hard_fail_with_successful_match(self) -> None:
        """Test pass when all fields match."""
        parsed = ParsedIdentity(
            producer="Domaine Rossignol-Trapet",
            appellation="Latricieres-Chambertin",
            raw_wine_name="test",
            normalized_wine_name="test"
        )
        field_matches = {
            "producer": FieldMatch(target="Domaine Rossignol-Trapet", status=FieldStatus.MATCH, confidence=0.95),
            "appellation": FieldMatch(target="Latricieres-Chambertin", status=FieldStatus.MATCH, confidence=0.95),
            "vineyard_or_cuvee": FieldMatch(status=FieldStatus.NO_SIGNAL),
            "classification": FieldMatch(target="grand cru", status=FieldStatus.MATCH, confidence=0.9),
            "vintage": FieldMatch(target="2017", status=FieldStatus.MATCH, confidence=0.95),
        }
        
        result = evaluate_hard_fail(parsed, field_matches, "some readable text here")
        
        assert result.should_fail is False
        assert result.reason is None

    def test_evaluate_hard_fail_with_partial_vineyard_no_signal(self) -> None:
        """Test pass when vineyard has no signal (not required)."""
        parsed = ParsedIdentity(
            producer="Domaine Rossignol-Trapet",
            appellation="Latricieres-Chambertin",
            vineyard_or_cuvee=None,  # Not required
            raw_wine_name="test",
            normalized_wine_name="test"
        )
        field_matches = {
            "producer": FieldMatch(target="Domaine Rossignol-Trapet", status=FieldStatus.MATCH, confidence=0.95),
            "appellation": FieldMatch(target="Latricieres-Chambertin", status=FieldStatus.MATCH, confidence=0.95),
            "vineyard_or_cuvee": FieldMatch(status=FieldStatus.NO_SIGNAL),
            "classification": FieldMatch(status=FieldStatus.NO_SIGNAL),
            "vintage": FieldMatch(target="2017", status=FieldStatus.MATCH, confidence=0.95),
        }
        
        result = evaluate_hard_fail(parsed, field_matches, "some readable text here")
        
        assert result.should_fail is False


class TestMissingRequiredField:
    """Test _missing_required_field function."""

    def test_missing_required_field_when_readable_and_not_match(self) -> None:
        """Test returns True when readable and status is not MATCH."""
        match = FieldMatch(target="Test", status=FieldStatus.UNVERIFIED, confidence=0.0)
        assert _missing_required_field(match, True) is True

    def test_missing_required_field_when_not_readable(self) -> None:
        """Test returns False when not readable (can't verify)."""
        match = FieldMatch(target="Test", status=FieldStatus.UNVERIFIED, confidence=0.0)
        assert _missing_required_field(match, False) is False

    def test_missing_required_field_when_match(self) -> None:
        """Test returns False when status is MATCH."""
        match = FieldMatch(target="Test", status=FieldStatus.MATCH, confidence=0.95)
        assert _missing_required_field(match, True) is False

    def test_missing_required_field_with_conflict(self) -> None:
        """Test returns True when status is CONFLICT (not MATCH)."""
        match = FieldMatch(target="Test", status=FieldStatus.CONFLICT, confidence=0.95)
        assert _missing_required_field(match, True) is True

    def test_missing_required_field_with_no_signal(self) -> None:
        """Test returns True when status is NO_SIGNAL (not MATCH)."""
        match = FieldMatch(status=FieldStatus.NO_SIGNAL)
        assert _missing_required_field(match, True) is True


class TestHardFailEvaluationDataclass:
    """Test HardFailEvaluation dataclass."""

    def test_hard_fail_evaluation_defaults(self) -> None:
        """Test default values for HardFailEvaluation."""
        evaluation = HardFailEvaluation(should_fail=False)
        
        assert evaluation.should_fail is False
        assert evaluation.reason is None
        assert evaluation.notes == []

    def test_hard_fail_evaluation_with_all_fields(self) -> None:
        """Test HardFailEvaluation with all fields set."""
        evaluation = HardFailEvaluation(
            should_fail=True,
            reason=FailReason.PRODUCER_MISMATCH,
            notes=["Test note"]
        )
        
        assert evaluation.should_fail is True
        assert evaluation.reason == FailReason.PRODUCER_MISMATCH
        assert evaluation.notes == ["Test note"]
