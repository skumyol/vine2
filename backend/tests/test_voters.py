from backend.app.core.constants import FailReason, FieldStatus
from backend.app.models.candidate import Candidate
from backend.app.models.result import FieldMatch, ModuleVote
from backend.app.models.sku import ParsedIdentity
from backend.app.services.voters import (
    aggregate_votes,
    build_joint_vote,
    build_ocr_vote,
    build_vlm_vote,
)


def _parsed() -> ParsedIdentity:
    return ParsedIdentity(
        producer="Domaine Arlaud",
        appellation="Morey-Saint-Denis",
        vineyard_or_cuvee="Monts Luisants",
        classification="1er Cru",
        vintage="2019",
        raw_wine_name="Domaine Arlaud Morey-Saint-Denis Monts Luisants 1er Cru",
        normalized_wine_name="domaine arlaud morey saint denis monts luisants 1er cru",
    )


def _candidate() -> Candidate:
    return Candidate(
        candidate_id="c1",
        image_url="https://example.com/wine.jpg",
        source_page="https://example.com/page",
        source_domain="example.com",
        observed_text="Domaine Arlaud Morey-Saint-Denis Monts Luisants 1er Cru 2019",
        source_trust_score=0.5,
        local_image_path="/tmp/wine.jpg",
    )


def test_ocr_vote_returns_pass_for_matching_text() -> None:
    vote = build_ocr_vote(_parsed(), _candidate(), 0.85)

    assert vote.module == "ocr"
    assert vote.available is True
    assert vote.passed is True
    assert vote.confidence > 0.0
    assert vote.field_matches["producer"].status == FieldStatus.MATCH
    assert vote.field_matches["vintage"].status == FieldStatus.MATCH


def test_vlm_vote_uses_multimodal_result(monkeypatch) -> None:
    def fake_verify(parsed, image_path):
        return {
            "producer": {"status": "match", "confidence": 0.98, "observed": "Domaine Arlaud"},
            "appellation": {"status": "match", "confidence": 0.91, "observed": "Morey-Saint-Denis"},
            "vineyard_or_cuvee": {"status": "match", "confidence": 0.96, "observed": "Monts Luisants"},
            "classification": {"status": "match", "confidence": 0.88, "observed": "1er Cru"},
            "vintage": {"status": "match", "confidence": 0.97, "observed": "2019"},
            "image": {
                "single_bottle": 1.0,
                "clean_background": 0.9,
                "readable_label": 0.95,
                "real_product_photo": 1.0,
            },
            "overall_pass": True,
            "overall_confidence": 0.94,
            "summary": "Label matches target wine.",
        }

    monkeypatch.setattr("backend.app.services.voters.verify_wine_image_with_vlm", fake_verify)

    vote = build_vlm_vote(_parsed(), _candidate())

    assert vote.module == "vlm"
    assert vote.available is True
    assert vote.passed is True
    assert vote.confidence == 0.94
    assert vote.field_matches["appellation"].status == FieldStatus.MATCH


def test_joint_vote_requires_both_inputs() -> None:
    ocr_vote = ModuleVote(module="ocr", available=True, passed=True, confidence=0.8, field_matches={})
    vlm_vote = ModuleVote(module="vlm", available=False, passed=False, confidence=0.0, field_matches={})

    joint = build_joint_vote(ocr_vote, vlm_vote)

    assert joint.module == "ocr_vlm"
    assert joint.available is False
    assert joint.confidence == 0.0


def test_joint_vote_combines_ocr_and_vlm() -> None:
    field_matches = {
        "producer": FieldMatch(target="Domaine Arlaud", extracted="Domaine Arlaud", status=FieldStatus.MATCH, confidence=0.9),
        "appellation": FieldMatch(target="Morey-Saint-Denis", extracted="Morey-Saint-Denis", status=FieldStatus.MATCH, confidence=0.9),
        "vineyard_or_cuvee": FieldMatch(target="Monts Luisants", extracted="Monts Luisants", status=FieldStatus.MATCH, confidence=0.9),
        "classification": FieldMatch(target="1er Cru", extracted="1er Cru", status=FieldStatus.MATCH, confidence=0.9),
        "vintage": FieldMatch(target="2019", extracted="2019", status=FieldStatus.MATCH, confidence=0.9),
    }
    ocr_vote = ModuleVote(module="ocr", available=True, passed=True, confidence=0.72, field_matches=field_matches)
    vlm_vote = ModuleVote(module="vlm", available=True, passed=True, confidence=0.92, field_matches=field_matches)

    joint = build_joint_vote(ocr_vote, vlm_vote)

    assert joint.available is True
    assert joint.passed is True
    assert joint.confidence > 0.8


def test_aggregate_votes_respects_vlm_conflict() -> None:
    candidate = _candidate()
    ocr_vote = ModuleVote(
        module="ocr",
        available=True,
        passed=True,
        confidence=0.8,
        field_matches={
            "producer": FieldMatch(target="Domaine Arlaud", extracted="Domaine Arlaud", status=FieldStatus.MATCH, confidence=0.9)
        },
    )
    vlm_vote = ModuleVote(
        module="vlm",
        available=True,
        passed=False,
        confidence=0.2,
        field_matches={
            "producer": FieldMatch(target="Domaine Arlaud", extracted="Wrong Producer", status=FieldStatus.CONFLICT, confidence=0.99),
            "appellation": FieldMatch(status=FieldStatus.UNVERIFIED),
            "vineyard_or_cuvee": FieldMatch(status=FieldStatus.UNVERIFIED),
            "classification": FieldMatch(status=FieldStatus.UNVERIFIED),
            "vintage": FieldMatch(status=FieldStatus.UNVERIFIED),
        },
    )

    confidence, _, _, fail_reason, _ = aggregate_votes(_parsed(), candidate, [ocr_vote, vlm_vote], 0.8)

    assert confidence == 0.0
    assert fail_reason == FailReason.CONFLICTING_FIELDS
