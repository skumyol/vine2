from fastapi import APIRouter

from backend.app.models.ocr import OcrRequest, OcrResponse
from backend.app.services.ocr_service import extract_ocr_text
from backend.app.services.paddle_ocr_service import extract_paddle_ocr


router = APIRouter(tags=["ocr"])


@router.post("/ocr/tesseract", response_model=OcrResponse)
def ocr_tesseract(payload: OcrRequest) -> OcrResponse:
    text, snippets = extract_ocr_text(payload.image_path)
    return OcrResponse(
        engine="tesseract",
        available=True,
        text=text,
        snippets=snippets,
        boxes=[],
    )


@router.post("/ocr/paddle", response_model=OcrResponse)
def ocr_paddle(payload: OcrRequest) -> OcrResponse:
    result = extract_paddle_ocr(payload.image_path)
    return OcrResponse(
        engine=result.get("engine", "paddleocr"),
        available=bool(result.get("available", False)),
        text=result.get("text", ""),
        snippets=result.get("snippets", []),
        boxes=result.get("boxes", []),
    )
