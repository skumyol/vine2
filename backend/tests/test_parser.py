from backend.app.models.sku import AnalyzeRequest
from backend.app.services.parser import parse_identity


def test_parse_identity_extracts_quoted_cuvee() -> None:
    payload = AnalyzeRequest(
        wine_name="Domaine Arlaud Morey-St-Denis 'Monts Luisants' 1er Cru",
        vintage="2019",
        format="750ml",
        region="Burgundy",
    )
    parsed = parse_identity(payload)
    assert parsed.producer == "Domaine Arlaud"
    assert parsed.appellation == "Morey-Saint-Denis"
    assert parsed.vineyard_or_cuvee == "Monts Luisants"
    assert parsed.classification == "1er cru"
    assert parsed.vintage == "2019"


def test_parse_identity_extracts_appellation_without_quotes() -> None:
    payload = AnalyzeRequest(
        wine_name="Chateau Fonroque Saint-Emilion Grand Cru Classe",
        vintage="2016",
        format="750ml",
        region="Bordeaux",
    )
    parsed = parse_identity(payload)

    assert parsed.producer == "Chateau Fonroque"
    assert parsed.appellation == "Saint-Emilion"
    assert parsed.classification == "grand cru classe"


def test_parse_identity_extracts_unquoted_vineyard_or_cuvee() -> None:
    payload = AnalyzeRequest(
        wine_name="Domaine Rossignol-Trapet Latricieres-Chambertin Grand Cru",
        vintage="2017",
        format="750ml",
        region="Burgundy",
    )
    parsed = parse_identity(payload)

    assert parsed.producer == "Domaine Rossignol-Trapet"
    assert parsed.appellation == "Latricieres-Chambertin"
    assert parsed.vineyard_or_cuvee is None
    assert parsed.classification == "grand cru"


def test_parse_identity_extracts_unquoted_named_cuvee() -> None:
    payload = AnalyzeRequest(
        wine_name="Brokenwood Graveyard Vineyard Shiraz",
        vintage="2015",
        format="750ml",
        region="Hunter Valley",
    )
    parsed = parse_identity(payload)

    assert parsed.producer == "Brokenwood"
    assert parsed.vineyard_or_cuvee == "Graveyard Vineyard Shiraz"
