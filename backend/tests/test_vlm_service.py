from backend.app.models.sku import ParsedIdentity
from backend.app.services.vlm_service import _build_image_url_payload, _build_prompt, _normalize_vlm_response


def test_normalize_vlm_response_clamps_false_positive_confidence() -> None:
    payload = {
        "producer": {"status": "unverified", "confidence": 0.1, "observed": ""},
        "appellation": {"status": "unverified", "confidence": 0.1, "observed": ""},
        "vineyard_or_cuvee": {"status": "match", "confidence": 0.9, "observed": "Monts Luisants"},
        "classification": {"status": "unverified", "confidence": 0.1, "observed": ""},
        "vintage": {"status": "unverified", "confidence": 0.1, "observed": ""},
        "image": {
            "single_bottle": 1.0,
            "clean_background": 0.95,
            "readable_label": 0.9,
            "real_product_photo": 0.95,
        },
        "overall_pass": False,
        "overall_confidence": 0.95,
        "summary": "Looks good but not enough identity evidence.",
    }

    normalized = _normalize_vlm_response(payload)

    assert normalized["overall_pass"] is False
    assert normalized["overall_confidence"] <= 0.49


def test_normalize_vlm_response_forces_unverified_confidence_below_threshold() -> None:
    payload = {
        "producer": {"status": "unverified", "confidence": 0.92, "observed": ""},
        "appellation": {"status": "match", "confidence": 0.88, "observed": "Morey-Saint-Denis"},
        "vineyard_or_cuvee": {"status": "match", "confidence": 0.9, "observed": "Monts Luisants"},
        "classification": {"status": "unverified", "confidence": 0.9, "observed": ""},
        "vintage": {"status": "conflict", "confidence": 0.95, "observed": "2018"},
        "image": {},
        "overall_pass": True,
        "overall_confidence": 0.9,
        "summary": "Badly formatted response.",
    }

    normalized = _normalize_vlm_response(payload)

    assert normalized["producer"]["confidence"] <= 0.49
    assert normalized["classification"]["confidence"] <= 0.49
    assert normalized["overall_pass"] is False
    assert normalized["overall_confidence"] <= 0.49


def test_build_image_url_payload_passthroughs_remote_url() -> None:
    url = "https://example.com/wine.jpg"

    payload = _build_image_url_payload(url)

    assert payload == url


def test_build_prompt_includes_gate_reason_and_ocr_text() -> None:
    parsed = ParsedIdentity(
        producer="Domaine Arlaud",
        appellation="Morey-Saint-Denis",
        vineyard_or_cuvee="Monts Luisants",
        classification="1er Cru",
        vintage="2019",
        raw_wine_name="Test",
        normalized_wine_name="test",
    )

    prompt = _build_prompt(parsed, ocr_text="Domaine Arlaud 2019", gate_reason="vineyard uncertain")

    assert "vineyard uncertain" in prompt
    assert "Domaine Arlaud 2019" in prompt
