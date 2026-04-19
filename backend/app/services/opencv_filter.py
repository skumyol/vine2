import io
import urllib.request
from pathlib import Path

from PIL import Image, ImageStat


def passes_visual_prefilter(image_path: str | None) -> tuple[bool, dict]:
    if not image_path:
        return False, {
            "passed": False,
            "single_bottle": 0.0,
            "clean_background": 0.0,
            "label_visible": 0.0,
            "watermark_suspected": 0.0,
            "lifestyle_suspected": 0.0,
            "reason": "No image available for OpenCV prefilter.",
        }

    try:
        image = _load_image(image_path)
    except Exception as exc:
        return False, {
            "passed": False,
            "single_bottle": 0.0,
            "clean_background": 0.0,
            "label_visible": 0.0,
            "watermark_suspected": 0.0,
            "lifestyle_suspected": 0.0,
            "reason": f"OpenCV prefilter image load failed: {type(exc).__name__}.",
        }

    width, height = image.size
    grayscale = image.convert("L")
    stat = ImageStat.Stat(grayscale)
    mean_brightness = stat.mean[0] / 255.0
    contrast = min((stat.stddev[0] / 64.0), 1.0)
    portrait_score = 1.0 if height >= width * 1.2 else 0.4
    clean_background = 1.0 - min(abs(mean_brightness - 0.92), 0.5) * 2
    label_visible = min(max(contrast, 0.2), 1.0)
    watermark_suspected = 0.1 if contrast > 0.2 else 0.3
    lifestyle_suspected = 0.1 if portrait_score > 0.8 else 0.4
    passed = portrait_score >= 0.4 and label_visible >= 0.2
    return passed, {
        "passed": passed,
        "single_bottle": round(portrait_score, 4),
        "clean_background": round(max(clean_background, 0.0), 4),
        "label_visible": round(label_visible, 4),
        "watermark_suspected": round(watermark_suspected, 4),
        "lifestyle_suspected": round(lifestyle_suspected, 4),
        "reason": "Heuristic visual prefilter completed.",
        "image_size": {"width": width, "height": height},
    }


def _load_image(image_path: str) -> Image.Image:
    if image_path.startswith(("http://", "https://")):
        with urllib.request.urlopen(image_path, timeout=20) as response:
            return Image.open(io.BytesIO(response.read())).convert("RGB")
    return Image.open(Path(image_path)).convert("RGB")
