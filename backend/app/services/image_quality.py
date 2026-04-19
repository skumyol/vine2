from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageStat, UnidentifiedImageError


@dataclass
class ImageQualityResult:
    score: float
    passed: bool
    reasons: list[str]


def evaluate_image_quality(image_path: str | None) -> ImageQualityResult:
    if not image_path:
        return ImageQualityResult(score=0.0, passed=False, reasons=["missing_image"])

    path = Path(image_path)
    if not path.exists():
        return ImageQualityResult(score=0.0, passed=False, reasons=["missing_image"])

    try:
        with Image.open(path) as image:
            rgb = image.convert("RGB")
            width, height = rgb.size
            gray = rgb.convert("L")
            stat = ImageStat.Stat(gray)
            mean = stat.mean[0]
            variance = stat.var[0]
            bright_pixels = _bright_fraction(gray)
            edge_variance = _edge_variance(gray)
    except (UnidentifiedImageError, OSError):
        return ImageQualityResult(score=0.0, passed=False, reasons=["invalid_image_file"])

    reasons: list[str] = []
    score = 1.0

    if width < 250 or height < 400:
        score -= 0.35
        reasons.append("image_too_small")
    if height <= width:
        score -= 0.2
        reasons.append("not_portrait")
    if bright_pixels > 0.2:
        score -= 0.15
        reasons.append("possible_glare_or_background_blowout")
    if variance < 700:
        score -= 0.2
        reasons.append("low_contrast")
    if edge_variance < 12:
        score -= 0.25
        reasons.append("possible_blur")
    if mean < 40:
        score -= 0.1
        reasons.append("too_dark")

    score = max(0.0, min(score, 1.0))
    return ImageQualityResult(score=round(score, 4), passed=score >= 0.55, reasons=reasons)


def _bright_fraction(gray_image: Image.Image) -> float:
    pixels = list(gray_image.getdata())
    if not pixels:
        return 0.0
    bright = sum(1 for pixel in pixels if pixel >= 245)
    return bright / len(pixels)


def _edge_variance(gray_image: Image.Image) -> float:
    width, height = gray_image.size
    if width < 2 or height < 2:
        return 0.0
    pixels = gray_image.load()
    diffs: list[int] = []
    for y in range(height - 1):
        for x in range(width - 1):
            diffs.append(abs(pixels[x, y] - pixels[x + 1, y]))
            diffs.append(abs(pixels[x, y] - pixels[x, y + 1]))
    if not diffs:
        return 0.0
    mean = sum(diffs) / len(diffs)
    return sum((diff - mean) ** 2 for diff in diffs) / len(diffs)
