import base64
import json
import mimetypes
import urllib.error
import urllib.request
from pathlib import Path

from backend.app.core.config import get_settings
from backend.app.models.sku import ParsedIdentity


class VlmServiceError(RuntimeError):
    pass


def verify_wine_image_with_vlm(
    parsed: ParsedIdentity,
    image_path: str | None,
    *,
    ocr_text: str = "",
    gate_reason: str = "",
) -> dict:
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise VlmServiceError("OPENROUTER_API_KEY is not configured.")
    if not image_path:
        raise VlmServiceError("Image path is required for VLM verification.")

    payload = {
        "model": settings.openrouter_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": _build_prompt(parsed, ocr_text=ocr_text, gate_reason=gate_reason),
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": _build_image_url_payload(image_path),
                        },
                    },
                ],
            }
        ],
        "reasoning": {"enabled": settings.vlm_reasoning_enabled},
        "response_format": {"type": "json_object"},
    }

    request = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
        },
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        data = json.loads(response.read().decode("utf-8"))

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise VlmServiceError("OpenRouter returned an unexpected response shape.") from exc

    try:
        parsed_response = json.loads(content)
    except json.JSONDecodeError as exc:
        raise VlmServiceError("OpenRouter did not return valid JSON content.") from exc
    return _normalize_vlm_response(parsed_response)


def _build_prompt(parsed: ParsedIdentity, *, ocr_text: str = "", gate_reason: str = "") -> str:
    target = {
        "producer": parsed.producer,
        "appellation": parsed.appellation,
        "vineyard_or_cuvee": parsed.vineyard_or_cuvee,
        "classification": parsed.classification,
        "vintage": parsed.vintage,
        "format": parsed.format,
        "region": parsed.region,
    }
    example_response = {
        "producer": {"status": "match", "confidence": 0.98, "observed": "Domaine Arlaud"},
        "appellation": {"status": "match", "confidence": 0.94, "observed": "Morey-Saint-Denis"},
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
        "overall_confidence": 0.95,
        "summary": "Bottle image matches the target SKU with readable label and acceptable product-photo quality.",
    }
    return (
        "You are verifying whether a wine bottle image matches a target SKU. "
        "Be conservative: wrong image is worse than no image. "
        "This is a second-pass label verification task, not generic image description. "
        "Read the producer, appellation, vineyard/cuvee, classification, and vintage from the label if visible. "
        "If OCR evidence is provided, use it as weak supporting evidence but prioritize what you can actually see. "
        "Return JSON only with this exact shape and key names: "
        '{"producer":{"status":"match|conflict|unverified","confidence":0-1,"observed":""},'
        '"appellation":{"status":"match|conflict|unverified","confidence":0-1,"observed":""},'
        '"vineyard_or_cuvee":{"status":"match|conflict|unverified","confidence":0-1,"observed":""},'
        '"classification":{"status":"match|conflict|unverified","confidence":0-1,"observed":""},'
        '"vintage":{"status":"match|conflict|unverified","confidence":0-1,"observed":""},'
        '"image":{"single_bottle":0-1,"clean_background":0-1,"readable_label":0-1,"real_product_photo":0-1},'
        '"overall_pass":true|false,"overall_confidence":0-1,"summary":""}. '
        f"Example valid response: {json.dumps(example_response, ensure_ascii=True)}. "
        "Do not add markdown, code fences, comments, or extra keys. "
        "If a field cannot be verified, set status to 'unverified' and confidence to 0.0 or a low value. "
        f"Target SKU fields: {json.dumps(target, ensure_ascii=True)}. "
        f"Ambiguity gate reason: {gate_reason or 'not provided'}. "
        f"OCR evidence: {ocr_text or 'not provided'}"
    )


def _encode_image_as_data_url(path: Path) -> str:
    mime_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _build_image_url_payload(image_path: str | None) -> str:
    if not image_path:
        raise VlmServiceError("Image path is required for VLM verification.")
    if image_path.startswith(("http://", "https://")):
        return image_path
    return _encode_image_as_data_url(Path(image_path))


def _normalize_vlm_response(payload: dict) -> dict:
    normalized: dict = {}
    for field in ("producer", "appellation", "vineyard_or_cuvee", "classification", "vintage"):
        normalized[field] = _normalize_field_payload(payload.get(field))

    image = payload.get("image") or {}
    normalized["image"] = {
        "single_bottle": _clamp_unit(image.get("single_bottle", 0.0)),
        "clean_background": _clamp_unit(image.get("clean_background", 0.0)),
        "readable_label": _clamp_unit(image.get("readable_label", 0.0)),
        "real_product_photo": _clamp_unit(image.get("real_product_photo", 0.0)),
    }

    summary = str(payload.get("summary", "") or "").strip()
    field_confidences = [normalized[field]["confidence"] for field in ("producer", "appellation", "vineyard_or_cuvee", "classification", "vintage")]
    image_confidences = list(normalized["image"].values())
    evidence_confidence = sum(field_confidences + image_confidences) / max(1, len(field_confidences + image_confidences))

    overall_pass = bool(payload.get("overall_pass"))
    requested_confidence = _clamp_unit(payload.get("overall_confidence", 0.0))

    if not overall_pass:
        requested_confidence = min(requested_confidence, 0.49)
    else:
        core_conflicts = [
            normalized["producer"]["status"] == "conflict",
            normalized["appellation"]["status"] == "conflict",
            normalized["vineyard_or_cuvee"]["status"] == "conflict",
            normalized["vintage"]["status"] == "conflict",
        ]
        if any(core_conflicts):
            overall_pass = False
            requested_confidence = min(requested_confidence, 0.49)

    normalized["overall_pass"] = overall_pass
    normalized["overall_confidence"] = round(
        max(min(requested_confidence, evidence_confidence + 0.15), 0.0),
        4,
    )
    normalized["summary"] = summary
    return normalized


def _normalize_field_payload(payload: dict | None) -> dict:
    payload = payload or {}
    status = str(payload.get("status", "unverified")).strip().lower()
    if status not in {"match", "conflict", "unverified"}:
        status = "unverified"
    confidence = _clamp_unit(payload.get("confidence", 0.0))
    observed = str(payload.get("observed", "") or "").strip()
    if status == "unverified":
        confidence = min(confidence, 0.49)
    return {
        "status": status,
        "confidence": confidence,
        "observed": observed,
    }


def _clamp_unit(value) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    return round(min(max(numeric, 0.0), 1.0), 4)
