from backend.app.models.sku import ParsedIdentity
from backend.app.services.vlm_service import verify_wine_image_with_vlm


def verify_with_qwen_vlm(
    parsed: ParsedIdentity,
    image_path: str | None,
    *,
    ocr_text: str = "",
    gate_reason: str = "",
) -> dict:
    return verify_wine_image_with_vlm(parsed, image_path, ocr_text=ocr_text, gate_reason=gate_reason)
