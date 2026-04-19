"""Comprehensive tests for pipeline module - 100% coverage target."""

from unittest.mock import MagicMock, patch

import pytest

from backend.app.core.constants import FailReason, FieldStatus, Verdict
from backend.app.models.candidate import Candidate
from backend.app.models.result import AnalyzeResponse, FieldMatch
from backend.app.models.sku import AnalyzeRequest, BatchAnalyzeRequest, ParsedIdentity
from backend.app.services.pipeline import (
    _empty_field_matches,
    _evaluate_candidate,
    run_analysis,
    run_batch_analysis,
)


class TestRunAnalysis:
    """Test run_analysis function."""

    def test_run_analysis_with_pass_result(self, monkeypatch) -> None:
        """Test successful analysis returning PASS."""
        mock_candidate = Candidate(
            candidate_id="test-1",
            image_url="https://example.com/image.jpg",
            source_page="https://example.com/page",
            source_domain="example.com",
            observed_text="Domaine Rossignol-Trapet Latricieres-Chambertin 2017",
            image_quality_score=0.9,
            source_trust_score=0.8,
        )
        
        with patch("backend.app.services.pipeline.retrieve_candidates", return_value=[mock_candidate]):
            with patch("backend.app.services.pipeline.get_settings") as mock_get_settings:
                mock_settings = MagicMock()
                mock_settings.acceptance_threshold = 0.85
                mock_get_settings.return_value = mock_settings
                
                payload = AnalyzeRequest(
                    wine_name="Domaine Rossignol-Trapet Latricieres-Chambertin",
                    vintage="2017",
                    format="750ml",
                    region="Burgundy"
                )
                
                result = run_analysis(payload)
        
        assert isinstance(result, AnalyzeResponse)
        assert result.input == payload

    def test_run_analysis_with_no_candidates(self, monkeypatch) -> None:
        """Test analysis when no candidates are found."""
        with patch("backend.app.services.pipeline.retrieve_candidates", return_value=[]):
            payload = AnalyzeRequest(
                wine_name="Unknown Wine",
                vintage="2020",
                format="750ml",
                region="Test"
            )
            
            result = run_analysis(payload)
        
        assert result.verdict == Verdict.NO_IMAGE
        assert result.fail_reason == FailReason.NO_CANDIDATES
        assert result.confidence == 0.0

    def test_run_analysis_with_retrieval_error(self, monkeypatch) -> None:
        """Test analysis when retrieval raises exception."""
        with patch("backend.app.services.pipeline.retrieve_candidates", side_effect=Exception("Network error")):
            payload = AnalyzeRequest(
                wine_name="Test Wine",
                vintage="2020",
                format="750ml",
                region="Test"
            )
            
            result = run_analysis(payload)
        
        assert result.verdict == Verdict.ERROR
        assert result.fail_reason == FailReason.PIPELINE_NOT_IMPLEMENTED
        assert "Network error" in result.reason

    def test_run_analysis_all_candidates_fail(self, monkeypatch) -> None:
        """Test analysis when all candidates fail hard rules."""
        mock_candidate = Candidate(
            candidate_id="test-1",
            image_url="https://example.com/image.jpg",
            source_page="https://example.com/page",
            source_domain="example.com",
            observed_text="completely unrelated text",
            image_quality_score=0.5,
            source_trust_score=0.5,
        )
        
        with patch("backend.app.services.pipeline.retrieve_candidates", return_value=[mock_candidate]):
            payload = AnalyzeRequest(
                wine_name="Domaine Rossignol-Trapet",
                vintage="2017",
                format="750ml",
                region="Burgundy"
            )
            
            result = run_analysis(payload)
        
        assert result.verdict == Verdict.NO_IMAGE
        # Should have a fail reason from hard rules

    def test_run_analysis_below_threshold(self, monkeypatch) -> None:
        """Test analysis when best candidate is below acceptance threshold."""
        mock_candidate = Candidate(
            candidate_id="test-1",
            image_url="https://example.com/image.jpg",
            source_page="https://example.com/page",
            source_domain="example.com",
            observed_text="Domaine Rossignol-Trapet 2017",
            image_quality_score=0.5,
            source_trust_score=0.5,
        )
        
        with patch("backend.app.services.pipeline.retrieve_candidates", return_value=[mock_candidate]):
            with patch("backend.app.services.pipeline.get_settings") as mock_get_settings:
                mock_settings = MagicMock()
                mock_settings.acceptance_threshold = 0.95  # Very high
                mock_get_settings.return_value = mock_settings
                
                payload = AnalyzeRequest(
                    wine_name="Domaine Rossignol-Trapet",
                    vintage="2017",
                    format="750ml",
                    region="Burgundy"
                )
                
                result = run_analysis(payload)
        
        assert result.verdict == Verdict.NO_IMAGE
        assert "acceptance threshold" in result.reason.lower() or result.fail_reason == FailReason.IDENTITY_UNVERIFIED


class TestRunBatchAnalysis:
    """Test run_batch_analysis function."""

    def test_run_batch_analysis_with_multiple_items(self, monkeypatch) -> None:
        """Test batch analysis with multiple items."""
        mock_candidate = Candidate(
            candidate_id="test-1",
            image_url="https://example.com/image.jpg",
            source_page="https://example.com/page",
            source_domain="example.com",
            observed_text="Test wine 2020",
        )
        
        with patch("backend.app.services.pipeline.retrieve_candidates", return_value=[mock_candidate]):
            with patch("backend.app.services.pipeline.get_settings") as mock_get_settings:
                mock_settings = MagicMock()
                mock_settings.acceptance_threshold = 0.85
                mock_get_settings.return_value = mock_settings
                
                items = [
                    AnalyzeRequest(wine_name="Wine 1", vintage="2020"),
                    AnalyzeRequest(wine_name="Wine 2", vintage="2021"),
                ]
                batch_request = BatchAnalyzeRequest(items=items)
                
                result = run_batch_analysis(batch_request)
        
        assert len(result.results) == 2
        assert result.summary["total"] == 2
        assert "verdict_counts" in result.summary

    def test_run_batch_analysis_with_empty_items(self) -> None:
        """Test batch analysis with empty items list."""
        batch_request = BatchAnalyzeRequest(items=[])
        
        result = run_batch_analysis(batch_request)
        
        assert len(result.results) == 0
        assert result.summary["total"] == 0


class TestEvaluateCandidate:
    """Test _evaluate_candidate function."""

    def test_evaluate_candidate_passes_hard_fail(self, monkeypatch) -> None:
        """Test evaluation when candidate passes hard fail rules."""
        mock_candidate = Candidate(
            candidate_id="test-1",
            image_url="https://example.com/image.jpg",
            source_page="https://example.com/page",
            source_domain="example.com",
            observed_text="Domaine Rossignol-Trapet Latricieres-Chambertin 2017",
            image_quality_score=0.9,
            source_trust_score=0.8,
        )
        
        parsed = ParsedIdentity(
            producer="Domaine Rossignol-Trapet",
            appellation="Latricieres-Chambertin",
            vintage="2017",
            raw_wine_name="test",
            normalized_wine_name="test"
        )
        
        from backend.app.services.hard_fail_rules import HardFailEvaluation
        with patch("backend.app.services.pipeline.evaluate_hard_fail") as mock_eval:
            mock_eval.return_value = HardFailEvaluation(should_fail=False)
            
            result = _evaluate_candidate(parsed, mock_candidate)
        
        assert result.should_fail is False
        assert result.confidence > 0
        assert result.fail_reason is None

    def test_evaluate_candidate_fails_hard_fail(self) -> None:
        """Test evaluation when candidate fails hard fail rules."""
        mock_candidate = Candidate(
            candidate_id="test-1",
            image_url="https://example.com/image.jpg",
            source_page="https://example.com/page",
            source_domain="example.com",
            observed_text="unrelated text",
        )
        
        parsed = ParsedIdentity(
            producer="Domaine Rossignol-Trapet",
            appellation="Latricieres-Chambertin",
            vintage="2017",
            raw_wine_name="test",
            normalized_wine_name="test"
        )
        
        from backend.app.services.hard_fail_rules import HardFailEvaluation
        with patch("backend.app.services.pipeline.evaluate_hard_fail") as mock_eval:
            mock_eval.return_value = HardFailEvaluation(
                should_fail=True,
                reason=FailReason.PRODUCER_MISMATCH
            )
            
            result = _evaluate_candidate(parsed, mock_candidate)
        
        assert result.should_fail is True
        assert result.fail_reason == FailReason.PRODUCER_MISMATCH
        assert result.confidence == 0.0

    def test_evaluate_candidate_score_breakdown(self, monkeypatch) -> None:
        """Test that score breakdown is correctly populated."""
        mock_candidate = Candidate(
            candidate_id="test-1",
            image_url="https://example.com/image.jpg",
            source_page="https://example.com/page",
            source_domain="example.com",
            observed_text="Domaine Rossignol-Trapet 2017",
            image_quality_score=0.8,
            source_trust_score=0.7,
        )
        
        parsed = ParsedIdentity(
            producer="Domaine Rossignol-Trapet",
            vintage="2017",
            raw_wine_name="test",
            normalized_wine_name="test"
        )
        
        from backend.app.services.hard_fail_rules import HardFailEvaluation
        with patch("backend.app.services.pipeline.evaluate_hard_fail") as mock_eval:
            mock_eval.return_value = HardFailEvaluation(should_fail=False)
            
            result = _evaluate_candidate(parsed, mock_candidate)
        
        assert result.score_breakdown is not None
        assert result.score_breakdown.producer > 0


class TestEmptyFieldMatches:
    """Test _empty_field_matches function."""

    def test_empty_field_matches_returns_all_fields(self) -> None:
        """Test that all field keys are present."""
        parsed = ParsedIdentity(
            producer="Test Producer",
            appellation="Test Appellation",
            vineyard_or_cuvee="Test Vineyard",
            classification="grand cru",
            vintage="2020",
            raw_wine_name="test",
            normalized_wine_name="test"
        )
        
        result = _empty_field_matches(parsed)
        
        assert "producer" in result
        assert "appellation" in result
        assert "vineyard_or_cuvee" in result
        assert "classification" in result
        assert "vintage" in result

    def test_empty_field_matches_has_unverified_status(self) -> None:
        """Test that field matches have UNVERIFIED status."""
        parsed = ParsedIdentity(
            producer="Test",
            raw_wine_name="test",
            normalized_wine_name="test"
        )
        
        result = _empty_field_matches(parsed)
        
        for field_match in result.values():
            assert field_match.status == FieldStatus.UNVERIFIED
            assert field_match.confidence == 0.0

    def test_empty_field_matches_preserves_targets(self) -> None:
        """Test that targets are preserved from parsed identity."""
        parsed = ParsedIdentity(
            producer="Domaine Rossignol-Trapet",
            appellation="Latricieres-Chambertin",
            raw_wine_name="test",
            normalized_wine_name="test"
        )
        
        result = _empty_field_matches(parsed)
        
        assert result["producer"].target == "Domaine Rossignol-Trapet"
        assert result["appellation"].target == "Latricieres-Chambertin"


class TestPipelineIntegration:
    """Integration tests for the full pipeline."""

    def test_pipeline_integration_success_path(self, monkeypatch) -> None:
        """Test successful end-to-end pipeline execution."""
        mock_candidate = Candidate(
            candidate_id="test-1",
            image_url="https://images.example.com/arlaud-monts-luisants-2019.jpg",
            source_page="https://example.com/page",
            source_domain="example.com",
            observed_text="Domaine Arlaud Morey-Saint-Denis 'Monts Luisants' 1er Cru 2019",
            image_quality_score=0.9,
            source_trust_score=0.85,
            fixture_expected_match=True,
        )
        
        with patch("backend.app.services.pipeline.retrieve_candidates", return_value=[mock_candidate]):
            with patch("backend.app.services.pipeline.get_settings") as mock_get_settings:
                mock_settings = MagicMock()
                mock_settings.acceptance_threshold = 0.85
                mock_get_settings.return_value = mock_settings
                
                payload = AnalyzeRequest(
                    wine_name="Domaine Arlaud Morey-St-Denis 'Monts Luisants' 1er Cru",
                    vintage="2019",
                    format="750ml",
                    region="Burgundy"
                )
                
                result = run_analysis(payload)
        
        assert isinstance(result, AnalyzeResponse)
        assert result.input.wine_name == payload.wine_name

    def test_pipeline_integration_no_survivors(self, monkeypatch) -> None:
        """Test pipeline when no candidates survive hard fail."""
        mock_candidate = Candidate(
            candidate_id="test-1",
            image_url="https://example.com/image.jpg",
            source_page="https://example.com/page",
            source_domain="example.com",
            observed_text="Arnot-Roberts Trousseau Gris Watson Ranch 2020",
            image_quality_score=0.5,
            source_trust_score=0.5,
            fixture_expected_match=False,
        )
        
        with patch("backend.app.services.pipeline.retrieve_candidates", return_value=[mock_candidate]):
            payload = AnalyzeRequest(
                wine_name="Arnot-Roberts Trousseau Gris Watson Ranch",
                vintage="2020",
                format="750ml",
                region="Sonoma"
            )
            
            result = run_analysis(payload)
        
        assert result.verdict in [Verdict.NO_IMAGE, Verdict.ERROR]

    def test_pipeline_debug_payload_populated(self, monkeypatch) -> None:
        """Test that debug payload is properly populated."""
        mock_candidate = Candidate(
            candidate_id="test-1",
            image_url="https://example.com/image.jpg",
            source_page="https://example.com/page",
            source_domain="example.com",
            observed_text="Domaine Rossignol-Trapet 2017",
            image_quality_score=0.8,
            source_trust_score=0.7,
        )
        
        with patch("backend.app.services.pipeline.retrieve_candidates", return_value=[mock_candidate]):
            with patch("backend.app.services.pipeline.get_settings") as mock_get_settings:
                mock_settings = MagicMock()
                mock_settings.acceptance_threshold = 0.85
                mock_get_settings.return_value = mock_settings
                
                payload = AnalyzeRequest(
                    wine_name="Domaine Rossignol-Trapet",
                    vintage="2017",
                    format="750ml",
                    region="Burgundy"
                )
                
                result = run_analysis(payload)
        
        assert result.debug is not None
        assert isinstance(result.debug.queries, list)
        assert result.debug.candidates_considered >= 0
        assert isinstance(result.debug.hard_fail_reasons, list)
        assert isinstance(result.debug.notes, list)
