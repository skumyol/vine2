from pathlib import Path

from PIL import Image

from backend.app.services import ocr_service
from backend.app.services import paddle_ocr_service


def test_detect_label_regions_is_off_by_default(tmp_path: Path) -> None:
    image_path = tmp_path / "sample.png"
    Image.new("RGB", (20, 40), color="white").save(image_path)

    regions = ocr_service.detect_label_regions(image_path, enabled=False)

    assert regions == []


def test_run_yolo_label_detection_placeholder_returns_no_regions(tmp_path: Path) -> None:
    image_path = tmp_path / "sample.png"
    Image.new("RGB", (20, 40), color="white").save(image_path)

    regions = ocr_service.run_yolo_label_detection(image_path)

    assert regions == []


def test_extract_ocr_text_handles_optional_easyocr(monkeypatch, tmp_path: Path) -> None:
    image_path = tmp_path / "sample.png"
    Image.new("RGB", (30, 60), color="white").save(image_path)

    class Settings:
        ocr_easyocr_enabled = True
        yolo_enabled = False

    monkeypatch.setattr(ocr_service, "get_settings", lambda: Settings())
    monkeypatch.setattr(ocr_service, "_run_tesseract", lambda path: "tesseract text")
    monkeypatch.setattr(ocr_service, "_run_easyocr", lambda path: ["easyocr text"])

    merged, snippets = ocr_service.extract_ocr_text(str(image_path))

    assert "tesseract text" in merged
    assert "easyocr text" in merged
    assert "easyocr text" in snippets


def test_paddle_ocr_service_returns_unavailable_without_dependency() -> None:
    result = paddle_ocr_service.extract_paddle_ocr("https://example.com/wine.jpg")

    assert result["available"] is False
    assert result["engine"] in {"paddleocr_unavailable", "paddleocr_error"}
