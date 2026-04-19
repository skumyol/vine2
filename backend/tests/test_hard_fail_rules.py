from backend.app.core.constants import FailReason
from backend.app.models.sku import AnalyzeRequest
from backend.app.services.hard_fail_rules import evaluate_hard_fail
from backend.app.services.matcher import build_field_matches
from backend.app.services.parser import parse_identity


def test_hard_fail_rejects_missing_required_vineyard_when_text_is_readable() -> None:
    payload = AnalyzeRequest(
        wine_name="Domaine Arlaud Morey-St-Denis 'Monts Luisants' 1er Cru",
        vintage="2019",
        format="750ml",
        region="Burgundy",
    )
    parsed = parse_identity(payload)
    observed_text = "Domaine Arlaud Morey Saint Denis Clos de la Roche 1er Cru 2019"

    result = evaluate_hard_fail(parsed, build_field_matches(parsed, observed_text), observed_text)

    assert result.should_fail is True
    assert result.reason == FailReason.VINEYARD_OR_CUVEE_MISMATCH


def test_hard_fail_rejects_visible_vintage_mismatch() -> None:
    payload = AnalyzeRequest(
        wine_name="Domaine Arlaud Morey-St-Denis 'Monts Luisants' 1er Cru",
        vintage="2019",
        format="750ml",
        region="Burgundy",
    )
    parsed = parse_identity(payload)
    observed_text = "Domaine Arlaud Morey Saint Denis Monts Luisants 1er Cru 2018"

    result = evaluate_hard_fail(parsed, build_field_matches(parsed, observed_text), observed_text)

    assert result.should_fail is True
    assert result.reason == FailReason.VINTAGE_MISMATCH


def test_hard_fail_rejects_unreadable_core_identity() -> None:
    payload = AnalyzeRequest(
        wine_name="Domaine Rossignol-Trapet Latricieres-Chambertin Grand Cru",
        vintage="2017",
        format="750ml",
        region="Burgundy",
    )
    parsed = parse_identity(payload)
    observed_text = "wine bottle"

    result = evaluate_hard_fail(parsed, build_field_matches(parsed, observed_text), observed_text)

    assert result.should_fail is True
    assert result.reason == FailReason.UNREADABLE_CORE_IDENTITY
