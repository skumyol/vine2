import tempfile
import urllib.request
from pathlib import Path


def extract_paddle_ocr(image_path: str | None, crops: list[str] | None = None) -> dict:
    crop_paths = crops or []
    if not image_path:
        return {
            "text": "",
            "snippets": [],
            "boxes": [],
            "engine": "paddleocr_placeholder",
            "available": False,
        }

    try:
        from paddleocr import PaddleOCR
    except ImportError:
        return {
            "text": "",
            "snippets": [],
            "boxes": [],
            "engine": "paddleocr_unavailable",
            "available": False,
        }

    temp_path = None
    candidate_path = image_path
    if image_path.startswith(("http://", "https://")):
        temp_path = _download_to_tempfile(image_path)
        candidate_path = temp_path

    try:
        ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
        snippets, boxes = _run_ocr_pass(ocr, candidate_path)
        for crop in crop_paths:
            crop_snippets, crop_boxes = _run_ocr_pass(ocr, crop)
            snippets.extend(crop_snippets)
            boxes.extend(crop_boxes)
        text = " ".join(snippets).strip()
        return {
            "text": text,
            "snippets": snippets,
            "boxes": boxes,
            "engine": "paddleocr",
            "available": True,
        }
    except Exception:
        return {
            "text": "",
            "snippets": [],
            "boxes": [],
            "engine": "paddleocr_error",
            "available": False,
        }
    finally:
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)


def _download_to_tempfile(url: str) -> str:
    suffix = Path(url).suffix or ".jpg"
    with urllib.request.urlopen(url, timeout=20) as response:
        data = response.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
        handle.write(data)
        return handle.name


def _run_ocr_pass(ocr, image_path: str) -> tuple[list[str], list]:
    raw = ocr.ocr(image_path, cls=True) or []
    snippets: list[str] = []
    boxes: list = []
    for page in raw:
        if not page:
            continue
        for entry in page:
            if len(entry) < 2:
                continue
            boxes.append(entry[0])
            text_conf = entry[1]
            if isinstance(text_conf, (list, tuple)) and text_conf:
                snippets.append(str(text_conf[0]).strip())
    return snippets, boxes
