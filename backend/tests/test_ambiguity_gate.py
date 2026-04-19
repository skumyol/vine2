from backend.app.core.constants import FieldStatus
from backend.app.models.result import FieldMatch, ModuleVote
from backend.app.models.sku import ParsedIdentity
from backend.app.services.ambiguity_gate import should_run_vlm


def _parsed() -> ParsedIdentity:
    return ParsedIdentity(
        producer="Domaine Arlaud",
        appellation="Morey-Saint-Denis",
        vineyard_or_cuvee="Monts Luisants",
        classification="1er Cru",
        vintage="2019",
        raw_wine_name="Test",
        normalized_wine_name="test",
    )


def test_gate_runs_for_missing_cuvee_or_vintage_confirmation() -> None:
    vote = ModuleVote(
        module="ocr",
        available=True,
        passed=True,
        confidence=0.88,
        field_matches={
            "producer": FieldMatch(status=FieldStatus.MATCH, confidence=0.95),
            "appellation": FieldMatch(status=FieldStatus.MATCH, confidence=0.95),
            "vineyard_or_cuvee": FieldMatch(status=FieldStatus.UNVERIFIED, confidence=0.0),
            "vintage": FieldMatch(status=FieldStatus.UNVERIFIED, confidence=0.0),
        },
    )

    run_vlm, reason = should_run_vlm(_parsed(), "Domaine Arlaud Morey Saint Denis", vote, {"passed": True, "label_visible": 0.8})

    assert run_vlm is True
    assert "uncertain" in reason.lower()


def test_gate_skips_when_ocr_is_already_strong() -> None:
    vote = ModuleVote(
        module="ocr",
        available=True,
        passed=True,
        confidence=0.95,
        field_matches={
            "producer": FieldMatch(status=FieldStatus.MATCH, confidence=0.95),
            "appellation": FieldMatch(status=FieldStatus.MATCH, confidence=0.95),
            "vineyard_or_cuvee": FieldMatch(status=FieldStatus.MATCH, confidence=0.95),
            "vintage": FieldMatch(status=FieldStatus.MATCH, confidence=0.95),
        },
    )

    run_vlm, reason = should_run_vlm(_parsed(), "Domaine Arlaud Morey Saint Denis Monts Luisants 2019", vote, {"passed": True, "label_visible": 0.9})

    assert run_vlm is False
    assert "strong enough" in reason.lower()


def test_gate_skips_when_ocr_is_too_weak() -> None:
    vote = ModuleVote(module="ocr", available=True, passed=True, confidence=0.55, field_matches={})

    run_vlm, reason = should_run_vlm(_parsed(), "partial text", vote, {"passed": True, "label_visible": 0.2})

    assert run_vlm is False
    assert "too weak" in reason.lower()
