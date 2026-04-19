import hashlib
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

from backend.app.core.config import get_settings
from backend.app.models.candidate import Candidate


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class ImageTagParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta_images: list[str] = []
        self.img_urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.lower(): value or "" for key, value in attrs}
        if tag.lower() == "meta":
            prop = attr_map.get("property", "").lower()
            name = attr_map.get("name", "").lower()
            content = attr_map.get("content", "")
            if content and prop in {"og:image", "og:image:url"}:
                self.meta_images.append(content)
            if content and name in {"twitter:image", "twitter:image:src"}:
                self.meta_images.append(content)
        if tag.lower() == "img":
            src = attr_map.get("src") or attr_map.get("data-src") or attr_map.get("data-lazy-src")
            if src:
                self.img_urls.append(src)


def hydrate_candidate_assets(candidate: Candidate) -> Candidate:
    settings = get_settings()
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    settings.images_dir.mkdir(parents=True, exist_ok=True)

    try:
        source_html = _fetch_text(candidate.source_page)
    except Exception as exc:
        candidate.notes.append(f"source_fetch_failed:{type(exc).__name__}")
        return candidate

    source_hash = hashlib.sha1(candidate.source_page.encode("utf-8")).hexdigest()[:16]
    source_path = settings.cache_dir / f"{source_hash}.html"
    source_path.write_text(source_html, encoding="utf-8")
    candidate.local_source_path = str(source_path)

    best_image_url = _resolve_best_image_url(candidate, source_html)
    if not best_image_url:
        candidate.notes.append("no_image_url_resolved")
        return candidate

    try:
        image_bytes, content_type = _fetch_bytes(best_image_url)
        suffix = _infer_extension(best_image_url, content_type)
        image_hash = hashlib.sha1(best_image_url.encode("utf-8")).hexdigest()[:16]
        image_path = settings.images_dir / f"{image_hash}{suffix}"
        image_path.write_bytes(image_bytes)
        candidate.resolved_image_url = best_image_url
        candidate.local_image_path = str(image_path)
        candidate.downloaded = True
    except Exception as exc:
        candidate.notes.append(f"image_download_failed:{type(exc).__name__}")
    return candidate


def _resolve_best_image_url(candidate: Candidate, source_html: str) -> str | None:
    direct = candidate.image_url
    if _looks_like_image_url(direct):
        return direct

    parser = ImageTagParser()
    parser.feed(source_html)
    ranked_urls = parser.meta_images + parser.img_urls
    if not ranked_urls:
        return None

    source_base = candidate.source_page
    normalized = [_absolutize_url(source_base, url) for url in ranked_urls]
    normalized = [url for url in normalized if url.startswith("http")]
    normalized.sort(key=_image_url_rank, reverse=True)
    return normalized[0] if normalized else None


def _image_url_rank(url: str) -> tuple[int, int]:
    lowered = url.lower()
    good = sum(token in lowered for token in ("wine", "bottle", "product", "vintage", "image"))
    bad = sum(token in lowered for token in ("logo", "icon", "sprite", "banner", "avatar"))
    return (good - bad, len(url))


def _fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="ignore")


def _fetch_bytes(url: str) -> tuple[bytes, str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        content_type = response.headers.get("Content-Type", "")
        return response.read(), content_type


def _absolutize_url(base_url: str, value: str) -> str:
    if value.startswith("//"):
        return "https:" + value
    return urllib.parse.urljoin(base_url, value)


def _looks_like_image_url(url: str) -> bool:
    lowered = url.lower()
    return bool(re.search(r"\.(jpg|jpeg|png|webp)(\?|$)", lowered))


def _infer_extension(url: str, content_type: str) -> str:
    lowered = url.lower()
    if ".png" in lowered or "png" in content_type:
        return ".png"
    if ".webp" in lowered or "webp" in content_type:
        return ".webp"
    return ".jpg"
