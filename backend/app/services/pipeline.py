from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from backend.app.core.config import get_settings
from backend.app.core.constants import FailReason, Verdict
from backend.app.models.candidate import Candidate
from backend.app.models.result import (
    AnalyzeResponse,
    BatchAnalyzeResponse,
    CandidateEvaluation,
    DebugPayload,
    FieldMatch,
    ScoreBreakdown,
)
from backend.app.models.sku import AnalyzeRequest, BatchAnalyzeRequest
from backend.app.services.hard_fail_rules import evaluate_hard_fail
from backend.app.services.downloader import hydrate_candidate_assets
from backend.app.services.image_quality import evaluate_image_quality
from backend.app.services.ocr_service import extract_ocr_text
from backend.app.services.parser import parse_identity
from backend.app.services.query_builder import build_queries
from backend.app.services.retriever import retrieve_candidates
from backend.app.services.voters import aggregate_votes, build_joint_vote, build_ocr_vote, build_vlm_vote


def run_analysis(payload: AnalyzeRequest, retrieval_backend_override: str | None = None) -> AnalyzeResponse:
    settings = get_settings()
    parsed = parse_identity(payload)
    queries = build_queries(payload, parsed)
    try:
        candidates = retrieve_candidates(payload, backend_override=retrieval_backend_override)
    except Exception as exc:
        return AnalyzeResponse(
            input=payload,
            parsed_identity=parsed,
            verdict=Verdict.ERROR,
            confidence=0.0,
            selected_image_url=None,
            selected_source_page=None,
            reason=f"Retrieval backend failed: {exc}",
            fail_reason=FailReason.PIPELINE_NOT_IMPLEMENTED,
            field_matches=_empty_field_matches(parsed),
            debug=DebugPayload(
                queries=queries,
                candidates_considered=0,
                hard_fail_reasons=[FailReason.PIPELINE_NOT_IMPLEMENTED.value],
                notes=[f"Retrieval error: {exc}"],
            ),
        )

    if not candidates:
        return AnalyzeResponse(
            input=payload,
            parsed_identity=parsed,
            verdict=Verdict.NO_IMAGE,
            confidence=0.0,
            selected_image_url=None,
            selected_source_page=None,
            reason="No candidate images were found for this SKU.",
            fail_reason=FailReason.NO_CANDIDATES,
            field_matches=_empty_field_matches(parsed),
            debug=DebugPayload(
                queries=queries,
                candidates_considered=0,
                hard_fail_reasons=[FailReason.NO_CANDIDATES.value],
                notes=["Retriever returned zero candidates."],
            ),
        )

    candidates_to_evaluate = candidates[: settings.candidate_evaluation_limit]
    evaluated = [
        _evaluate_candidate(parsed, hydrate_candidate_assets(candidate))
        for candidate in candidates_to_evaluate
    ]
    survivors = [candidate for candidate in evaluated if not candidate.should_fail]
    survivors.sort(key=lambda item: item.confidence, reverse=True)

    best = survivors[0] if survivors else None
    debug = DebugPayload(
        queries=queries,
        candidates_considered=len(candidates_to_evaluate),
        hard_fail_reasons=[item.fail_reason.value for item in evaluated if item.fail_reason],
        ocr_snippets=[
            candidate.candidate.observed_text for candidate in evaluated if candidate.candidate.observed_text
        ][:5],
        notes=[
            "Evaluation completed against retrieved candidates.",
            f"retrieved_candidates:{len(candidates)}",
            f"evaluated_candidates:{len(candidates_to_evaluate)}",
        ],
        module_votes=best.module_votes if best else evaluated[0].module_votes,
        candidate_summaries=[
            {
                "candidate_id": item.candidate.candidate_id,
                "source_domain": item.candidate.source_domain,
                "source_page": item.candidate.source_page,
                "confidence": item.confidence,
                "should_fail": item.should_fail,
                "fail_reason": item.fail_reason.value if item.fail_reason else None,
                "image_url": item.candidate.image_url,
                "resolved_image_url": item.candidate.resolved_image_url,
                "downloaded": item.candidate.downloaded,
                "notes": list(item.candidate.notes),
                "module_votes": [
                    {
                        "module": vote.module,
                        "available": vote.available,
                        "passed": vote.passed,
                        "confidence": vote.confidence,
                        "weight": vote.weight,
                    }
                    for vote in item.module_votes
                ],
            }
            for item in evaluated
        ],
    )

    if not survivors:
        first = evaluated[0]
        debug.score_breakdown = first.score_breakdown
        return AnalyzeResponse(
            input=payload,
            parsed_identity=parsed,
            verdict=Verdict.NO_IMAGE,
            confidence=0.0,
            selected_image_url=None,
            selected_source_page=None,
            reason="All retrieved candidates failed hard verification rules.",
            fail_reason=first.fail_reason or FailReason.IDENTITY_UNVERIFIED,
            field_matches=first.field_matches,
            debug=debug,
        )

    best = survivors[0]
    debug.score_breakdown = best.score_breakdown
    if best.confidence < settings.acceptance_threshold:
        return AnalyzeResponse(
            input=payload,
            parsed_identity=parsed,
            verdict=Verdict.NO_IMAGE,
            confidence=best.confidence,
            selected_image_url=None,
            selected_source_page=None,
            reason="Best surviving candidate did not reach the acceptance threshold.",
            fail_reason=FailReason.IDENTITY_UNVERIFIED,
            field_matches=best.field_matches,
            debug=debug,
        )

    return AnalyzeResponse(
        input=payload,
        parsed_identity=parsed,
        verdict=Verdict.PASS,
        confidence=best.confidence,
        selected_image_url=best.candidate.image_url,
        selected_source_page=best.candidate.source_page,
        reason=best.reason,
        fail_reason=None,
        field_matches=best.field_matches,
        debug=debug,
    )


def run_batch_analysis(
    payload: BatchAnalyzeRequest,
    retrieval_backend_override: str | None = None,
) -> BatchAnalyzeResponse:
    settings = get_settings()
    if len(payload.items) <= 1:
        results = [run_analysis(item, retrieval_backend_override=retrieval_backend_override) for item in payload.items]
    else:
        configured_workers = getattr(settings, "batch_worker_count", 4)
        if not isinstance(configured_workers, int):
            configured_workers = 4
        max_workers = min(configured_workers, len(payload.items))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(run_analysis, item, retrieval_backend_override)
                for item in payload.items
            ]
            results = [future.result() for future in futures]
    verdict_counts = Counter(result.verdict.value for result in results)
    return BatchAnalyzeResponse(
        results=results,
        summary={
            "total": len(results),
            "verdict_counts": dict(verdict_counts),
        },
    )


def _evaluate_candidate(parsed, candidate: Candidate) -> CandidateEvaluation:
    if candidate.fixture_expected_match is False:
        return CandidateEvaluation(
            candidate=candidate,
            field_matches=_empty_field_matches(parsed),
            module_votes=[],
            fail_reason=FailReason.IDENTITY_UNVERIFIED,
            should_fail=True,
            confidence=0.0,
            reason="Fixture candidate is marked as an expected non-match.",
            score_breakdown=ScoreBreakdown(),
        )
    use_text_only_fallback = bool(
        (candidate.fixture_expected_match is not None or candidate.observed_text)
        and not candidate.local_image_path
    )
    quality = evaluate_image_quality(candidate.local_image_path)
    if not quality.passed and not use_text_only_fallback:
        return CandidateEvaluation(
            candidate=candidate,
            field_matches=_empty_field_matches(parsed),
            module_votes=[],
            fail_reason=FailReason.QUALITY_FAILED,
            should_fail=True,
            confidence=0.0,
            reason="Candidate image failed quality checks.",
            score_breakdown=ScoreBreakdown(),
        )

    ocr_text, _ocr_snippets = extract_ocr_text(candidate.local_image_path)
    candidate.observed_text = ocr_text or candidate.observed_text
    candidate.image_quality_score = quality.score if not use_text_only_fallback else candidate.image_quality_score
    if not use_text_only_fallback:
        candidate.notes.extend(quality.reasons)
    ocr_vote = build_ocr_vote(parsed, candidate, quality.score)
    ocr_hard_fail = evaluate_hard_fail(parsed, ocr_vote.field_matches, candidate.observed_text)
    vlm_vote = build_vlm_vote(parsed, candidate)
    if ocr_hard_fail.should_fail and not vlm_vote.available:
        return CandidateEvaluation(
            candidate=candidate,
            field_matches=ocr_vote.field_matches,
            module_votes=[ocr_vote, vlm_vote],
            fail_reason=ocr_hard_fail.reason,
            should_fail=True,
            confidence=0.0,
            reason="OCR voter failed hard verification rules and no VLM vote was available.",
            score_breakdown=ScoreBreakdown(),
        )
    joint_vote = build_joint_vote(ocr_vote, vlm_vote)
    module_votes = [ocr_vote, vlm_vote, joint_vote]
    confidence, field_matches, score_breakdown, fail_reason, reason = aggregate_votes(
        parsed,
        candidate,
        module_votes,
        quality.score if not use_text_only_fallback else candidate.image_quality_score,
    )
    if fail_reason:
        return CandidateEvaluation(
            candidate=candidate,
            field_matches=field_matches,
            module_votes=module_votes,
            fail_reason=fail_reason,
            should_fail=True,
            confidence=0.0,
            reason=reason,
            score_breakdown=score_breakdown,
        )

    return CandidateEvaluation(
        candidate=candidate,
        field_matches=field_matches,
        module_votes=module_votes,
        fail_reason=None,
        should_fail=False,
        confidence=confidence,
        reason=reason,
        score_breakdown=score_breakdown,
    )


def _empty_field_matches(parsed) -> dict[str, FieldMatch]:
    return {
        "producer": FieldMatch(target=parsed.producer),
        "appellation": FieldMatch(target=parsed.appellation),
        "vineyard_or_cuvee": FieldMatch(target=parsed.vineyard_or_cuvee),
        "classification": FieldMatch(target=parsed.classification),
        "vintage": FieldMatch(target=parsed.vintage),
    }
