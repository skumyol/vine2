"""Comprehensive tests for models module - 100% coverage target."""

import pytest
from pydantic import ValidationError

from backend.app.core.constants import AnalyzerMode, FailReason, FieldStatus, Verdict
from backend.app.models.candidate import Candidate
from backend.app.models.result import (
    AnalyzeResponse,
    BatchAnalyzeResponse,
    CandidateEvaluation,
    DebugPayload,
    FieldMatch,
    ScoreBreakdown,
)
from backend.app.models.sku import AnalyzeRequest, BatchAnalyzeRequest, ParsedIdentity


class TestAnalyzeRequest:
    """Test AnalyzeRequest model."""

    def test_analyze_request_with_valid_data(self) -> None:
        """Test creating AnalyzeRequest with valid data."""
        request = AnalyzeRequest(
            wine_name="Domaine Rossignol-Trapet Latricieres-Chambertin",
            vintage="2017",
            format="750ml",
            region="Burgundy"
        )
        
        assert request.wine_name == "Domaine Rossignol-Trapet Latricieres-Chambertin"
        assert request.vintage == "2017"
        assert request.format == "750ml"
        assert request.region == "Burgundy"
        assert request.analyzer_mode == AnalyzerMode.STRICT  # default

    def test_analyze_request_with_defaults(self) -> None:
        """Test AnalyzeRequest default values."""
        request = AnalyzeRequest(
            wine_name="Test Wine",
            vintage="2020"
        )
        
        assert request.format == "750ml"
        assert request.region == ""
        assert request.analyzer_mode == AnalyzerMode.STRICT

    def test_analyze_request_wine_name_min_length(self) -> None:
        """Test wine_name minimum length validation."""
        with pytest.raises(ValidationError):
            AnalyzeRequest(wine_name="", vintage="2020")

    def test_analyze_request_vintage_min_length(self) -> None:
        """Test vintage minimum length validation."""
        with pytest.raises(ValidationError):
            AnalyzeRequest(wine_name="Test Wine", vintage="")

    def test_analyze_request_with_analyzer_mode(self) -> None:
        """Test setting analyzer_mode."""
        request = AnalyzeRequest(
            wine_name="Test Wine",
            vintage="2020",
            analyzer_mode=AnalyzerMode.BALANCED
        )
        
        assert request.analyzer_mode == AnalyzerMode.BALANCED


class TestParsedIdentity:
    """Test ParsedIdentity model."""

    def test_parsed_identity_with_all_fields(self) -> None:
        """Test creating ParsedIdentity with all fields."""
        identity = ParsedIdentity(
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
        
        assert identity.producer == "Domaine Rossignol-Trapet"
        assert identity.appellation == "Latricieres-Chambertin"

    def test_parsed_identity_with_optional_none(self) -> None:
        """Test ParsedIdentity with optional fields as None."""
        identity = ParsedIdentity(
            producer="Test Producer",
            raw_wine_name="Test Wine",
            normalized_wine_name="test wine"
        )
        
        assert identity.appellation is None
        assert identity.vineyard_or_cuvee is None
        assert identity.classification is None
        assert identity.vintage is None

    def test_parsed_identity_required_fields(self) -> None:
        """Test that raw_wine_name and normalized_wine_name are effectively required."""
        identity = ParsedIdentity(
            raw_wine_name="Test",
            normalized_wine_name="test"
        )
        
        assert identity.raw_wine_name == "Test"
        assert identity.normalized_wine_name == "test"


class TestBatchAnalyzeRequest:
    """Test BatchAnalyzeRequest model."""

    def test_batch_analyze_request_with_items(self) -> None:
        """Test creating BatchAnalyzeRequest with items."""
        items = [
            AnalyzeRequest(wine_name="Wine 1", vintage="2020"),
            AnalyzeRequest(wine_name="Wine 2", vintage="2021"),
        ]
        request = BatchAnalyzeRequest(items=items)
        
        assert len(request.items) == 2

    def test_batch_analyze_request_default_empty(self) -> None:
        """Test BatchAnalyzeRequest default empty list."""
        request = BatchAnalyzeRequest()
        
        assert request.items == []


class TestCandidate:
    """Test Candidate model."""

    def test_candidate_with_all_fields(self) -> None:
        """Test creating Candidate with all fields."""
        candidate = Candidate(
            candidate_id="test-1",
            image_url="https://example.com/image.jpg",
            source_page="https://example.com/page",
            source_domain="example.com",
            observed_text="Domaine Rossignol-Trapet 2017",
            image_quality_score=0.85,
            source_trust_score=0.75,
            notes=["note1", "note2"],
            fixture_expected_match=True
        )
        
        assert candidate.candidate_id == "test-1"
        assert candidate.image_quality_score == 0.85
        assert candidate.fixture_expected_match is True

    def test_candidate_defaults(self) -> None:
        """Test Candidate default values."""
        candidate = Candidate(
            candidate_id="test-1",
            image_url="https://example.com/image.jpg",
            source_page="https://example.com/page",
            source_domain="example.com"
        )
        
        assert candidate.observed_text == ""
        assert candidate.image_quality_score == 0.0
        assert candidate.source_trust_score == 0.0
        assert candidate.notes == []
        assert candidate.fixture_expected_match is None


class TestFieldMatch:
    """Test FieldMatch model."""

    def test_field_match_with_match(self) -> None:
        """Test FieldMatch with successful match."""
        match = FieldMatch(
            target="Domaine Rossignol-Trapet",
            extracted="Domaine Rossignol-Trapet",
            status=FieldStatus.MATCH,
            confidence=0.95
        )
        
        assert match.status == FieldStatus.MATCH
        assert match.confidence == 0.95

    def test_field_match_defaults(self) -> None:
        """Test FieldMatch default values."""
        match = FieldMatch()
        
        assert match.target is None
        assert match.extracted is None
        assert match.status == FieldStatus.UNVERIFIED
        assert match.confidence == 0.0

    def test_field_match_with_no_signal(self) -> None:
        """Test FieldMatch with no signal."""
        match = FieldMatch(status=FieldStatus.NO_SIGNAL)
        
        assert match.status == FieldStatus.NO_SIGNAL


class TestScoreBreakdown:
    """Test ScoreBreakdown model."""

    def test_score_breakdown_defaults(self) -> None:
        """Test ScoreBreakdown default values."""
        breakdown = ScoreBreakdown()
        
        assert breakdown.producer == 0.0
        assert breakdown.appellation == 0.0
        assert breakdown.vineyard_or_cuvee == 0.0
        assert breakdown.classification == 0.0
        assert breakdown.vintage == 0.0
        assert breakdown.ocr_clarity == 0.0
        assert breakdown.image_quality == 0.0
        assert breakdown.source_trust == 0.0

    def test_score_breakdown_with_values(self) -> None:
        """Test ScoreBreakdown with specific values."""
        breakdown = ScoreBreakdown(
            producer=0.2375,
            appellation=0.19,
            vintage=0.095
        )
        
        assert breakdown.producer == 0.2375
        assert breakdown.appellation == 0.19


class TestDebugPayload:
    """Test DebugPayload model."""

    def test_debug_payload_defaults(self) -> None:
        """Test DebugPayload default values."""
        payload = DebugPayload()
        
        assert payload.queries == []
        assert payload.candidates_considered == 0
        assert payload.hard_fail_reasons == []
        assert payload.ocr_snippets == []
        assert payload.notes == []
        assert payload.candidate_summaries == []

    def test_debug_payload_with_data(self) -> None:
        """Test DebugPayload with data."""
        payload = DebugPayload(
            queries=["query1", "query2"],
            candidates_considered=5,
            hard_fail_reasons=["reason1"],
            notes=["note1"]
        )
        
        assert payload.candidates_considered == 5
        assert len(payload.queries) == 2


class TestAnalyzeResponse:
    """Test AnalyzeResponse model."""

    def test_analyze_response_pass(self) -> None:
        """Test creating PASS response."""
        request = AnalyzeRequest(wine_name="Test", vintage="2020")
        parsed = ParsedIdentity(raw_wine_name="Test", normalized_wine_name="test")
        
        response = AnalyzeResponse(
            input=request,
            parsed_identity=parsed,
            verdict=Verdict.PASS,
            confidence=0.92,
            selected_image_url="https://example.com/image.jpg",
            selected_source_page="https://example.com/page",
            reason="Candidate verified successfully",
            fail_reason=None
        )
        
        assert response.verdict == Verdict.PASS
        assert response.confidence == 0.92
        assert response.fail_reason is None

    def test_analyze_response_no_image(self) -> None:
        """Test creating NO_IMAGE response."""
        request = AnalyzeRequest(wine_name="Test", vintage="2020")
        parsed = ParsedIdentity(raw_wine_name="Test", normalized_wine_name="test")
        
        response = AnalyzeResponse(
            input=request,
            parsed_identity=parsed,
            verdict=Verdict.NO_IMAGE,
            confidence=0.0,
            selected_image_url=None,
            selected_source_page=None,
            reason="No candidates found",
            fail_reason=FailReason.NO_CANDIDATES
        )
        
        assert response.verdict == Verdict.NO_IMAGE
        assert response.fail_reason == FailReason.NO_CANDIDATES

    def test_analyze_response_defaults(self) -> None:
        """Test AnalyzeResponse default values."""
        request = AnalyzeRequest(wine_name="Test", vintage="2020")
        parsed = ParsedIdentity(raw_wine_name="Test", normalized_wine_name="test")
        
        response = AnalyzeResponse(
            input=request,
            parsed_identity=parsed,
            verdict=Verdict.PASS,
            reason="Test"
        )
        
        assert response.confidence == 0.0
        assert response.selected_image_url is None
        assert response.fail_reason is None
        assert response.field_matches == {}


class TestBatchAnalyzeResponse:
    """Test BatchAnalyzeResponse model."""

    def test_batch_analyze_response_defaults(self) -> None:
        """Test BatchAnalyzeResponse default values."""
        response = BatchAnalyzeResponse()
        
        assert response.results == []
        assert response.summary == {}

    def test_batch_analyze_response_with_results(self) -> None:
        """Test BatchAnalyzeResponse with results."""
        request = AnalyzeRequest(wine_name="Test", vintage="2020")
        parsed = ParsedIdentity(raw_wine_name="Test", normalized_wine_name="test")
        
        single_response = AnalyzeResponse(
            input=request,
            parsed_identity=parsed,
            verdict=Verdict.PASS,
            reason="Test"
        )
        
        batch_response = BatchAnalyzeResponse(
            results=[single_response],
            summary={"total": 1, "passed": 1}
        )
        
        assert len(batch_response.results) == 1
        assert batch_response.summary["total"] == 1


class TestCandidateEvaluation:
    """Test CandidateEvaluation model."""

    def test_candidate_evaluation_defaults(self) -> None:
        """Test CandidateEvaluation default values."""
        candidate = Candidate(
            candidate_id="test",
            image_url="https://example.com/image.jpg",
            source_page="https://example.com/page",
            source_domain="example.com"
        )
        
        evaluation = CandidateEvaluation(
            candidate=candidate,
            reason="Test"
        )
        
        assert evaluation.should_fail is False
        assert evaluation.confidence == 0.0
        assert evaluation.fail_reason is None
        assert evaluation.field_matches == {}

    def test_candidate_evaluation_with_fail(self) -> None:
        """Test CandidateEvaluation with failure."""
        candidate = Candidate(
            candidate_id="test",
            image_url="https://example.com/image.jpg",
            source_page="https://example.com/page",
            source_domain="example.com"
        )
        
        evaluation = CandidateEvaluation(
            candidate=candidate,
            fail_reason=FailReason.PRODUCER_MISMATCH,
            should_fail=True,
            confidence=0.0,
            reason="Producer mismatch detected"
        )
        
        assert evaluation.should_fail is True
        assert evaluation.fail_reason == FailReason.PRODUCER_MISMATCH


class TestModelSerialization:
    """Test model serialization."""

    def test_analyze_request_json(self) -> None:
        """Test AnalyzeRequest JSON serialization."""
        request = AnalyzeRequest(wine_name="Test Wine", vintage="2020")
        json_str = request.model_dump_json()
        
        assert "Test Wine" in json_str
        assert "2020" in json_str

    def test_analyze_response_json(self) -> None:
        """Test AnalyzeResponse JSON serialization."""
        request = AnalyzeRequest(wine_name="Test", vintage="2020")
        parsed = ParsedIdentity(raw_wine_name="Test", normalized_wine_name="test")
        
        response = AnalyzeResponse(
            input=request,
            parsed_identity=parsed,
            verdict=Verdict.PASS,
            reason="Test"
        )
        
        json_str = response.model_dump_json()
        assert "PASS" in json_str

    def test_candidate_json(self) -> None:
        """Test Candidate JSON serialization."""
        candidate = Candidate(
            candidate_id="test-1",
            image_url="https://example.com/image.jpg",
            source_page="https://example.com/page",
            source_domain="example.com"
        )
        
        json_dict = candidate.model_dump()
        assert json_dict["candidate_id"] == "test-1"
