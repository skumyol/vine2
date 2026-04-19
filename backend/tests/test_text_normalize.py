from backend.app.utils.text_normalize import normalize_text


def test_normalize_text_removes_accents_and_normalizes_cru_terms() -> None:
    value = "Saint-Émilion Premier Cru"
    assert normalize_text(value) == "saint emilion 1er cru"
