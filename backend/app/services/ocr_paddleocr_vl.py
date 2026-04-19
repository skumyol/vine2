"""Alternative OCR service using PaddleOCR-VL via LangChain.

This is a cloud-based VLM approach for comparison with the local Tesseract/EasyOCR stack.
Requires:
    pip install langchain-paddleocr
    PADDLEOCR_API_URL and PADDLEOCR_ACCESS_TOKEN env vars

Docs: https://docs.langchain.com/oss/python/integrations/document_loaders/paddleocr_vl
"""

import os
from pathlib import Path


def extract_ocr_text_paddleocr_vl(image_path: str | None) -> tuple[str, list[str]]:
    """Extract OCR text using PaddleOCR-VL (cloud VLM approach).

    Returns:
        tuple of (merged_text, snippets_list)
    """
    if not image_path:
        return "", []

    path = Path(image_path)
    if not path.exists():
        return "", []

    api_url = os.getenv("PADDLEOCR_API_URL")
    access_token = os.getenv("PADDLEOCR_ACCESS_TOKEN")

    if not api_url:
        return "", ["PADDLEOCR_API_URL not set"]

    try:
        from langchain_paddleocr import PaddleOCRVLLoader
        from pydantic import SecretStr
    except ImportError:
        return "", ["langchain-paddleocr not installed"]

    try:
        loader = PaddleOCRVLLoader(
            file_path=str(path),
            api_url=api_url,
            access_token=SecretStr(access_token) if access_token else None,
            file_type="image",
            use_doc_orientation_classify=True,
            use_doc_unwarping=True,
            use_layout_detection=True,
            use_ocr_for_image_block=True,
            prettify_markdown=True,
            timeout=60,
        )

        docs = loader.load()

        snippets: list[str] = []
        for doc in docs:
            content = doc.page_content.strip()
            if content:
                snippets.append(content)

        merged = "\n".join(snippets).strip()
        return merged, snippets

    except Exception as exc:
        return "", [f"PaddleOCR-VL error: {exc}"]


def compare_ocr_approaches(image_path: str) -> dict:
    """Run both OCR approaches and return comparison.

    Useful for evaluating which approach works better for wine labels.
    """
    from backend.app.services.ocr_service import extract_ocr_text as local_ocr

    local_text, local_snippets = local_ocr(image_path)
    paddle_text, paddle_snippets = extract_ocr_text_paddleocr_vl(image_path)

    return {
        "image_path": image_path,
        "local": {
            "text": local_text[:1000] if local_text else "",
            "length": len(local_text),
            "snippets_count": len(local_snippets),
        },
        "paddleocr_vl": {
            "text": paddle_text[:1000] if paddle_text else "",
            "length": len(paddle_text),
            "snippets_count": len(paddle_snippets),
        },
    }
