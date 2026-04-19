import subprocess
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

from backend.app.core.config import get_settings


def extract_ocr_text(image_path: str | None) -> tuple[str, list[str]]:
    if not image_path:
        return "", []

    path = Path(image_path)
    if not path.exists():
        return "", []

    settings = get_settings()
    snippets: list[str] = []
    yolo_regions = detect_label_regions(path, enabled=settings.yolo_enabled)
    snippets.append(_run_tesseract(path))

    with Image.open(path) as image:
        rgb = image.convert("RGB")
        snippets.append(_run_tesseract(_save_temp_variant(rgb, path, "full-enhanced")))
        snippets.append(_run_tesseract(_save_temp_variant(_center_crop(rgb), path, "center-crop")))
        for region_index, region in enumerate(yolo_regions, start=1):
            snippets.append(_run_tesseract(_save_temp_variant(region, path, f"yolo-region-{region_index}")))

    if settings.ocr_easyocr_enabled:
        snippets.extend(_run_easyocr(path))

    merged = " ".join(snippet for snippet in snippets if snippet).strip()
    return merged, [snippet for snippet in snippets if snippet]


def _save_temp_variant(image: Image.Image, original_path: Path, suffix: str) -> Path:
    temp_path = original_path.with_name(f"{original_path.stem}-{suffix}.png")
    processed = ImageOps.autocontrast(image)
    processed = ImageEnhance.Sharpness(processed).enhance(2.0)
    processed = ImageEnhance.Contrast(processed).enhance(1.6)
    processed.save(temp_path)
    return temp_path


def _center_crop(image: Image.Image) -> Image.Image:
    width, height = image.size
    left = int(width * 0.15)
    right = int(width * 0.85)
    top = int(height * 0.35)
    bottom = int(height * 0.78)
    return image.crop((left, top, right, bottom))


def _run_tesseract(path: Path) -> str:
    command = [
        "tesseract",
        str(path),
        "stdout",
        "--psm",
        "6",
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    return " ".join(result.stdout.split())


def _run_easyocr(path: Path) -> list[str]:
    try:
        import easyocr
    except ImportError:
        return []

    try:
        reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        results = reader.readtext(str(path), detail=0, paragraph=True)
    except Exception:
        return []
    return [" ".join(str(item).split()) for item in results if str(item).strip()]


def detect_label_regions(path: Path, *, enabled: bool = False) -> list[Image.Image]:
    if not enabled:
        return []
    return run_yolo_label_detection(path)


def run_yolo_label_detection(path: Path) -> list[Image.Image]:
    """YOLO detector hook placeholder.

    This intentionally returns no regions while YOLO is disabled in the current
    implementation. It exists so a future detector can be added without changing
    the OCR pipeline contract.
    """
    return []
