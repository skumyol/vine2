"""Comprehensive tests for constants module - 100% coverage target."""

import pytest

from backend.app.core.constants import (
    AnalyzerMode,
    FailReason,
    FieldStatus,
    Verdict,
)


class TestVerdictEnum:
    """Test Verdict enum."""

    def test_verdict_values(self) -> None:
        """Test that Verdict has expected values."""
        assert Verdict.PASS == "PASS"
        assert Verdict.NO_IMAGE == "NO_IMAGE"
        assert Verdict.ERROR == "ERROR"

    def test_verdict_is_str_enum(self) -> None:
        """Test that Verdict inherits from str."""
        assert isinstance(Verdict.PASS, str)
        assert issubclass(Verdict, str)

    def test_verdict_members(self) -> None:
        """Test all Verdict members."""
        assert len(list(Verdict)) == 3
        assert Verdict.PASS in list(Verdict)
        assert Verdict.NO_IMAGE in list(Verdict)
        assert Verdict.ERROR in list(Verdict)

    def test_verdict_comparison(self) -> None:
        """Test Verdict comparison."""
        assert Verdict.PASS == "PASS"
        assert Verdict.NO_IMAGE == "NO_IMAGE"
        assert Verdict.ERROR == "ERROR"


class TestFieldStatusEnum:
    """Test FieldStatus enum."""

    def test_field_status_values(self) -> None:
        """Test that FieldStatus has expected values."""
        assert FieldStatus.MATCH == "match"
        assert FieldStatus.NO_SIGNAL == "no_signal"
        assert FieldStatus.CONFLICT == "conflict"
        assert FieldStatus.UNVERIFIED == "unverified"

    def test_field_status_is_str_enum(self) -> None:
        """Test that FieldStatus inherits from str."""
        assert isinstance(FieldStatus.MATCH, str)
        assert issubclass(FieldStatus, str)

    def test_field_status_members(self) -> None:
        """Test all FieldStatus members."""
        assert len(list(FieldStatus)) == 4
        assert FieldStatus.MATCH in list(FieldStatus)
        assert FieldStatus.NO_SIGNAL in list(FieldStatus)
        assert FieldStatus.CONFLICT in list(FieldStatus)
        assert FieldStatus.UNVERIFIED in list(FieldStatus)

    def test_field_status_comparison(self) -> None:
        """Test FieldStatus comparison."""
        assert FieldStatus.MATCH == "match"
        assert FieldStatus.NO_SIGNAL == "no_signal"
        assert FieldStatus.CONFLICT == "conflict"
        assert FieldStatus.UNVERIFIED == "unverified"


class TestFailReasonEnum:
    """Test FailReason enum."""

    def test_fail_reason_values(self) -> None:
        """Test that FailReason has expected values."""
        assert FailReason.NO_CANDIDATES == "no_candidates"
        assert FailReason.QUALITY_FAILED == "quality_failed"
        assert FailReason.IDENTITY_UNVERIFIED == "identity_unverified"
        assert FailReason.CONFLICTING_FIELDS == "conflicting_fields"
        assert FailReason.PRODUCER_MISMATCH == "producer_mismatch"
        assert FailReason.APPELLATION_MISMATCH == "appellation_mismatch"
        assert FailReason.VINEYARD_OR_CUVEE_MISMATCH == "vineyard_or_cuvee_mismatch"
        assert FailReason.CLASSIFICATION_CONFLICT == "classification_conflict"
        assert FailReason.VINTAGE_MISMATCH == "vintage_mismatch"
        assert FailReason.UNREADABLE_CORE_IDENTITY == "unreadable_core_identity"
        assert FailReason.PIPELINE_NOT_IMPLEMENTED == "pipeline_not_implemented"

    def test_fail_reason_is_str_enum(self) -> None:
        """Test that FailReason inherits from str."""
        assert isinstance(FailReason.NO_CANDIDATES, str)
        assert issubclass(FailReason, str)

    def test_fail_reason_members_count(self) -> None:
        """Test FailReason has expected number of members."""
        assert len(list(FailReason)) == 11

    def test_fail_reason_identity_failures(self) -> None:
        """Test identity-related failure reasons."""
        identity_reasons = [
            FailReason.PRODUCER_MISMATCH,
            FailReason.APPELLATION_MISMATCH,
            FailReason.VINEYARD_OR_CUVEE_MISMATCH,
            FailReason.CLASSIFICATION_CONFLICT,
            FailReason.VINTAGE_MISMATCH,
        ]
        for reason in identity_reasons:
            assert reason in list(FailReason)

    def test_fail_reason_quality_failures(self) -> None:
        """Test quality-related failure reasons."""
        quality_reasons = [
            FailReason.NO_CANDIDATES,
            FailReason.QUALITY_FAILED,
            FailReason.UNREADABLE_CORE_IDENTITY,
        ]
        for reason in quality_reasons:
            assert reason in list(FailReason)

    def test_fail_reason_system_failures(self) -> None:
        """Test system-related failure reasons."""
        system_reasons = [
            FailReason.PIPELINE_NOT_IMPLEMENTED,
            FailReason.IDENTITY_UNVERIFIED,
            FailReason.CONFLICTING_FIELDS,
        ]
        for reason in system_reasons:
            assert reason in list(FailReason)


class TestAnalyzerModeEnum:
    """Test AnalyzerMode enum."""

    def test_analyzer_mode_values(self) -> None:
        """Test that AnalyzerMode has expected values."""
        assert AnalyzerMode.STRICT == "strict"
        assert AnalyzerMode.BALANCED == "balanced"

    def test_analyzer_mode_is_str_enum(self) -> None:
        """Test that AnalyzerMode inherits from str."""
        assert isinstance(AnalyzerMode.STRICT, str)
        assert issubclass(AnalyzerMode, str)

    def test_analyzer_mode_members(self) -> None:
        """Test all AnalyzerMode members."""
        assert len(list(AnalyzerMode)) == 2
        assert AnalyzerMode.STRICT in list(AnalyzerMode)
        assert AnalyzerMode.BALANCED in list(AnalyzerMode)


class TestEnumStringRepresentation:
    """Test string representation of enums."""

    def test_verdict_str(self) -> None:
        """Test Verdict string representation."""
        assert str(Verdict.PASS) == "PASS"
        assert str(Verdict.NO_IMAGE) == "NO_IMAGE"
        assert str(Verdict.ERROR) == "ERROR"

    def test_field_status_str(self) -> None:
        """Test FieldStatus string representation."""
        assert str(FieldStatus.MATCH) == "match"
        assert str(FieldStatus.NO_SIGNAL) == "no_signal"
        assert str(FieldStatus.CONFLICT) == "conflict"
        assert str(FieldStatus.UNVERIFIED) == "unverified"

    def test_fail_reason_str(self) -> None:
        """Test FailReason string representation."""
        assert str(FailReason.NO_CANDIDATES) == "no_candidates"
        assert str(FailReason.QUALITY_FAILED) == "quality_failed"

    def test_analyzer_mode_str(self) -> None:
        """Test AnalyzerMode string representation."""
        assert str(AnalyzerMode.STRICT) == "strict"
        assert str(AnalyzerMode.BALANCED) == "balanced"


class TestEnumValueAccess:
    """Test accessing enum values."""

    def test_verdict_value_attribute(self) -> None:
        """Test Verdict value attribute."""
        assert Verdict.PASS.value == "PASS"
        assert Verdict.NO_IMAGE.value == "NO_IMAGE"

    def test_field_status_value_attribute(self) -> None:
        """Test FieldStatus value attribute."""
        assert FieldStatus.MATCH.value == "match"
        assert FieldStatus.CONFLICT.value == "conflict"

    def test_fail_reason_value_attribute(self) -> None:
        """Test FailReason value attribute."""
        assert FailReason.PRODUCER_MISMATCH.value == "producer_mismatch"
        assert FailReason.VINTAGE_MISMATCH.value == "vintage_mismatch"
