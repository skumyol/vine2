from backend.app.core.constants import FieldStatus
from backend.app.models.sku import AnalyzeRequest
from backend.app.services.matcher import build_field_matches
from backend.app.services.parser import parse_identity


def test_build_field_matches_detects_exact_identity_match() -> None:
    payload = AnalyzeRequest(
        wine_name="Domaine Arlaud Morey-St-Denis 'Monts Luisants' 1er Cru",
        vintage="2019",
        format="750ml",
        region="Burgundy",
    )
    parsed = parse_identity(payload)
    observed_text = "Domaine Arlaud Morey Saint Denis Monts Luisants 1er Cru 2019"

    matches = build_field_matches(parsed, observed_text)

    assert matches["producer"].status == FieldStatus.MATCH
    assert matches["appellation"].status == FieldStatus.MATCH
    assert matches["vineyard_or_cuvee"].status == FieldStatus.MATCH
    assert matches["classification"].status == FieldStatus.MATCH
    assert matches["vintage"].status == FieldStatus.MATCH


def test_build_field_matches_detects_visible_vintage_conflict() -> None:
    payload = AnalyzeRequest(
        wine_name="Domaine Arlaud Morey-St-Denis 'Monts Luisants' 1er Cru",
        vintage="2019",
        format="750ml",
        region="Burgundy",
    )
    parsed = parse_identity(payload)
    observed_text = "Domaine Arlaud Morey Saint Denis Monts Luisants 1er Cru 2018"

    matches = build_field_matches(parsed, observed_text)

    assert matches["vintage"].status == FieldStatus.CONFLICT
