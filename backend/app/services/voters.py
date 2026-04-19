from backend.app.core.constants import FailReason, FieldStatus
from backend.app.models.candidate import Candidate
from backend.app.models.result import FieldMatch, ModuleVote, ScoreBreakdown
from backend.app.models.sku import ParsedIdentity
from backend.app.services.hard_fail_rules import evaluate_hard_fail
from backend.app.services.matcher import build_field_matches, is_readable_enough
from backend.app.services.scorer import build_score_breakdown, normalized_total_score
from backend.app.services.vlm_service import VlmServiceError, verify_wine_image_with_vlm


VOTE_WEIGHTS = {
    "ocr": 0.20,
    "vlm": 0.60,
    "ocr_vlm": 0.15,
    "source": 0.05,
}


def build_ocr_vote(parsed: ParsedIdentity, candidate: Candidate, quality_score: float) -> ModuleVote:
    field_matches = build_field_matches(parsed, candidate.observed_text)
    hard_fail = evaluate_hard_fail(parsed, field_matches, candidate.observed_text)
    passed = not hard_fail.should_fail
    score_breakdown = build_score_breakdown(
        producer=field_matches["producer"].confidence,
        appellation=field_matches["appellation"].confidence,
        vineyard_or_cuvee=field_matches["vineyard_or_cuvee"].confidence,
        classification=field_matches["classification"].confidence,
        vintage=field_matches["vintage"].confidence,
        ocr_clarity=0.9 if is_readable_enough(candidate.observed_text) else 0.2,
        image_quality=quality_score,
        source_trust=candidate.source_trust_score,
    )
    active_weight = 0.0
    if parsed.producer:
        active_weight += 0.25
    if parsed.appellation:
        active_weight += 0.20
    if parsed.vineyard_or_cuvee:
        active_weight += 0.20
    if parsed.classification:
        active_weight += 0.10
    if parsed.vintage:
        active_weight += 0.10
    active_weight += 0.05 + 0.05 + 0.05
    confidence = normalized_total_score(score_breakdown, active_weight)
    if not passed:
        confidence = 0.0
    return ModuleVote(
        module="ocr",
        passed=passed,
        confidence=round(confidence, 4),
        weight=VOTE_WEIGHTS["ocr"],
        reason="Deterministic OCR verification.",
        field_matches=field_matches,
        raw_payload={"hard_fail_reason": hard_fail.reason.value if hard_fail.reason else None},
    )


def build_vlm_vote(parsed: ParsedIdentity, candidate: Candidate) -> ModuleVote:
    if not candidate.local_image_path:
        return ModuleVote(
            module="vlm",
            available=False,
            passed=False,
            confidence=0.0,
            weight=VOTE_WEIGHTS["vlm"],
            reason="No local image available for VLM verification.",
        )

    try:
        payload = verify_wine_image_with_vlm(parsed, candidate.local_image_path)
    except VlmServiceError as exc:
        return ModuleVote(
            module="vlm",
            available=False,
            passed=False,
            confidence=0.0,
            weight=VOTE_WEIGHTS["vlm"],
            reason=str(exc),
        )

    field_matches = {
        "producer": _field_match_from_vlm(parsed.producer, payload.get("producer")),
        "appellation": _field_match_from_vlm(parsed.appellation, payload.get("appellation")),
        "vineyard_or_cuvee": _field_match_from_vlm(parsed.vineyard_or_cuvee, payload.get("vineyard_or_cuvee")),
        "classification": _field_match_from_vlm(parsed.classification, payload.get("classification")),
        "vintage": _field_match_from_vlm(parsed.vintage, payload.get("vintage")),
    }
    passed = bool(payload.get("overall_pass"))
    return ModuleVote(
        module="vlm",
        passed=passed,
        confidence=round(float(payload.get("overall_confidence", 0.0)), 4),
        weight=VOTE_WEIGHTS["vlm"],
        reason=str(payload.get("summary", "Multimodal verification.")),
        field_matches=field_matches,
        raw_payload=payload,
    )


def build_joint_vote(ocr_vote: ModuleVote, vlm_vote: ModuleVote) -> ModuleVote:
    if not ocr_vote.available or not vlm_vote.available:
        return ModuleVote(
            module="ocr_vlm",
            available=False,
            passed=False,
            confidence=0.0,
            weight=VOTE_WEIGHTS["ocr_vlm"],
            reason="OCR and VLM joint vote requires both modules.",
        )

    merged_matches = {
        key: _merge_field_match(ocr_vote.field_matches.get(key), vlm_vote.field_matches.get(key))
        for key in {"producer", "appellation", "vineyard_or_cuvee", "classification", "vintage"}
    }
    passed = ocr_vote.passed and vlm_vote.passed
    consistency = _consistency_bonus(ocr_vote.field_matches, vlm_vote.field_matches)
    confidence = ((ocr_vote.confidence + vlm_vote.confidence) / 2.0) * consistency
    return ModuleVote(
        module="ocr_vlm",
        passed=passed,
        confidence=round(min(confidence, 1.0), 4) if passed else 0.0,
        weight=VOTE_WEIGHTS["ocr_vlm"],
        reason="Joint OCR and VLM consensus vote.",
        field_matches=merged_matches,
        raw_payload={"consistency_bonus": consistency},
    )


def aggregate_votes(
    parsed: ParsedIdentity,
    candidate: Candidate,
    votes: list[ModuleVote],
    quality_score: float,
) -> tuple[float, dict[str, FieldMatch], ScoreBreakdown, FailReason | None, str]:
    available_votes = [vote for vote in votes if vote.available]
    major_vlm_vote = next((vote for vote in available_votes if vote.module == "vlm"), None)
    if major_vlm_vote and _has_core_conflict(major_vlm_vote.field_matches):
        return 0.0, major_vlm_vote.field_matches, _empty_breakdown(), FailReason.CONFLICTING_FIELDS, (
            "VLM reported a core identity conflict."
        )

    weighted_sum = 0.0
    total_weight = 0.0
    for vote in available_votes:
        weighted_sum += vote.confidence * vote.weight
        total_weight += vote.weight

    source_component = candidate.source_trust_score * VOTE_WEIGHTS["source"]
    total_weight += VOTE_WEIGHTS["source"]
    weighted_sum += source_component
    aggregated_confidence = round(weighted_sum / total_weight, 4) if total_weight else 0.0
    if len(available_votes) == 1 and available_votes[0].module == "ocr" and available_votes[0].passed:
        aggregated_confidence = round(min(1.0, available_votes[0].confidence + 0.07), 4)

    field_matches = _aggregate_field_matches(votes)
    fail_reason = None
    if _has_core_conflict(field_matches):
        aggregated_confidence = 0.0
        fail_reason = FailReason.CONFLICTING_FIELDS

    score_breakdown = build_score_breakdown(
        producer=field_matches["producer"].confidence,
        appellation=field_matches["appellation"].confidence,
        vineyard_or_cuvee=field_matches["vineyard_or_cuvee"].confidence,
        classification=field_matches["classification"].confidence,
        vintage=field_matches["vintage"].confidence,
        ocr_clarity=next((vote.confidence for vote in votes if vote.module == "ocr" and vote.available), 0.0),
        image_quality=quality_score,
        source_trust=candidate.source_trust_score,
    )
    reason = "Weighted voter aggregation completed."
    return aggregated_confidence, field_matches, score_breakdown, fail_reason, reason


def _field_match_from_vlm(target: str | None, payload: dict | None) -> FieldMatch:
    if not target:
        return FieldMatch(status=FieldStatus.NO_SIGNAL, confidence=0.0)
    payload = payload or {}
    status_map = {
        "match": FieldStatus.MATCH,
        "conflict": FieldStatus.CONFLICT,
        "unverified": FieldStatus.UNVERIFIED,
    }
    return FieldMatch(
        target=target,
        extracted=payload.get("observed"),
        status=status_map.get(payload.get("status"), FieldStatus.UNVERIFIED),
        confidence=float(payload.get("confidence", 0.0)),
    )


def _merge_field_match(left: FieldMatch | None, right: FieldMatch | None) -> FieldMatch:
    left = left or FieldMatch()
    right = right or FieldMatch()
    if right.status == FieldStatus.CONFLICT or left.status == FieldStatus.CONFLICT:
        return right if right.status == FieldStatus.CONFLICT else left
    return right if right.confidence >= left.confidence else left


def _consistency_bonus(left: dict[str, FieldMatch], right: dict[str, FieldMatch]) -> float:
    comparable = 0
    matches = 0
    for key in {"producer", "appellation", "vineyard_or_cuvee", "classification", "vintage"}:
        l_item = left.get(key)
        r_item = right.get(key)
        if not l_item or not r_item:
            continue
        if l_item.status == FieldStatus.UNVERIFIED or r_item.status == FieldStatus.UNVERIFIED:
            continue
        comparable += 1
        if l_item.status == r_item.status:
            matches += 1
    if comparable == 0:
        return 1.0
    return 1.0 + (matches / comparable) * 0.1


def _aggregate_field_matches(votes: list[ModuleVote]) -> dict[str, FieldMatch]:
    result: dict[str, FieldMatch] = {}
    for key in {"producer", "appellation", "vineyard_or_cuvee", "classification", "vintage"}:
        candidates = [vote.field_matches.get(key) for vote in votes if vote.available and key in vote.field_matches]
        candidates = [candidate for candidate in candidates if candidate is not None]
        if not candidates:
            result[key] = FieldMatch()
            continue
        conflicts = [candidate for candidate in candidates if candidate.status == FieldStatus.CONFLICT]
        if conflicts:
            result[key] = max(conflicts, key=lambda item: item.confidence)
            continue
        result[key] = max(candidates, key=lambda item: item.confidence)
    return result


def _has_core_conflict(field_matches: dict[str, FieldMatch]) -> bool:
    for key in {"producer", "appellation", "vineyard_or_cuvee", "vintage"}:
        if field_matches.get(key) and field_matches[key].status == FieldStatus.CONFLICT:
            return True
    return False


def _empty_breakdown() -> ScoreBreakdown:
    return ScoreBreakdown()
