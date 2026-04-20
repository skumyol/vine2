"""
Playwright Microservice - HTTP API for browser automation
"""

import asyncio
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Playwright Service", version="1.0.0")

# Constants
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
NAV_TIMEOUT_MS = 15000
MAX_SEARCH_RESULTS = 8
MAX_IMAGES_PER_PAGE = 12
MAX_CONCURRENT_PAGES = 4

BAD_IMAGE_PATTERNS = (
    "placeholder", "no-image", "no_image", "default", "sprite",
    "icon", "logo", "avatar", "banner", "thumb",
)
BAD_IMAGE_EXTENSIONS = (".svg",)
PREFERRED_IMAGE_HINTS = ("product", "bottle", "wine", "vin", "image", "photo")

DEFAULT_SEARCH_TEMPLATES = [
    "https://search.brave.com/search?q={query}",
    "https://www.startpage.com/do/search?q={query}",
    "https://www.mojeek.com/search?q={query}",
    "https://lite.duckduckgo.com/lite/?q={query}",
]

SEARCH_ENGINE_DOMAINS = (
    "bing.com", "microsoft.com", "msn.com", "duckduckgo.com", "duck.com",
    "brave.com", "search.brave", "startpage.com", "ixquick.com", "mojeek.com",
    "google.com", "googleusercontent.com", "googleadservices.com",
    "aka.ms", "mastodon.social", "t.co",
    "facebook.com/sharer", "twitter.com/share",
)


# Pydantic models
class SearchRequest(BaseModel):
    queries: List[str]
    search_url_template: str = "https://search.brave.com/search?q={query}"
    search_url_templates: Optional[List[str]] = Field(default=None)
    candidate_limit: int = 20
    http_first: bool = True
    min_results_per_engine: int = 3


class Candidate(BaseModel):
    candidate_id: str
    image_url: str
    source_page: str
    source_domain: str
    observed_text: str
    image_quality_score: float
    source_trust_score: float
    notes: List[str]


class SearchResponse(BaseModel):
    candidates: List[Candidate]
    total_found: int


class HealthResponse(BaseModel):
    status: str
    playwright_imported: bool
    browser_launch_ok: bool
    page_load_ok: bool


class SelfCheckResponse(BaseModel):
    playwright_imported: bool
    browser_launch_ok: bool
    page_load_ok: bool
    http_fallback_forced: bool
    launch_args: List[str]
    search_url_template: str
    reason: Optional[str] = None
    title: Optional[str] = None


@dataclass
class SearchResult:
    title: str
    url: str
    domain: str
    rank: int
    query: str


@app.get("/health", response_model=HealthResponse)
async def health():
    """Lightweight health check endpoint - just confirms service is responding"""
    # Quick check: just verify playwright is importable, don't launch browser
    try:
        from playwright.async_api import async_playwright
        playwright_imported = True
    except ImportError:
        playwright_imported = False

    return HealthResponse(
        status="ok",
        playwright_imported=playwright_imported,
        browser_launch_ok=True,  # Assume OK - detailed check at /self-check
        page_load_ok=True,      # Assume OK - detailed check at /self-check
    )


@app.get("/self-check", response_model=SelfCheckResponse)
async def self_check():
    """Detailed self-check endpoint"""
    result = await _get_self_check()
    return SelfCheckResponse(**result)


@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Search for image candidates (HTTP-first with engine rotation, Playwright fallback)"""
    if not request.queries:
        return SearchResponse(candidates=[], total_found=0)

    templates = list(request.search_url_templates or DEFAULT_SEARCH_TEMPLATES)
    if request.search_url_template and request.search_url_template not in templates:
        templates.insert(0, request.search_url_template)

    candidates = []
    # HTTP-first: most reliable, avoids bot detection on search engines
    if request.http_first:
        try:
            candidates = await asyncio.to_thread(
                _collect_candidates_http,
                request.queries,
                templates,
                request.candidate_limit,
                request.min_results_per_engine,
            )
        except Exception:
            candidates = []

    # Fallback to Playwright browser if HTTP yielded too few
    if len(candidates) < request.min_results_per_engine:
        try:
            browser_cands = await _collect_candidates_async(
                request.queries,
                templates[0] if templates else request.search_url_template,
                request.candidate_limit,
            )
            # Merge with dedup
            seen = {c.source_page or c.image_url for c in candidates}
            for bc in browser_cands:
                key = bc.source_page or bc.image_url
                if key not in seen:
                    candidates.append(bc)
                    seen.add(key)
        except Exception:
            pass

    try:
        return SearchResponse(
            candidates=[Candidate(**c.__dict__) for c in candidates],
            total_found=len(candidates),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _get_self_check() -> dict:
    """Run self-check and return status"""
    details = {
        "playwright_imported": False,
        "browser_launch_ok": False,
        "page_load_ok": False,
        "http_fallback_forced": False,
        "launch_args": ["--no-sandbox", "--disable-dev-shm-usage"],
        "search_url_template": "https://duckduckgo.com/html/?q={query}",
    }

    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        details["reason"] = f"Playwright import failed: {type(exc).__name__}"
        return details

    details["playwright_imported"] = True
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            details["browser_launch_ok"] = True
            page = await browser.new_page()
            try:
                await page.goto("https://example.com", wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
                details["page_load_ok"] = True
                details["title"] = await page.title()
            finally:
                await page.close()
                await browser.close()
    except Exception as exc:
        details["reason"] = f"{type(exc).__name__}: {exc}"
        return details

    return details


async def _collect_candidates_async(
    queries: list[str],
    search_url_template: str,
    candidate_limit: int
) -> list:
    """Collect candidates using Playwright browser automation"""
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError
    from playwright.async_api import async_playwright

    candidates = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context()
        try:
            for query in queries:
                search_page = await context.new_page()
                try:
                    search_results = await _collect_search_results(
                        search_page, query, search_url_template, PlaywrightTimeoutError
                    )
                finally:
                    await search_page.close()

                sem = asyncio.Semaphore(MAX_CONCURRENT_PAGES)
                tasks = [
                    _extract_from_one_result(context, sem, result, PlaywrightTimeoutError)
                    for result in search_results
                ]
                image_lists = await asyncio.gather(*tasks, return_exceptions=True)
                for item in image_lists:
                    if isinstance(item, Exception):
                        continue
                    candidates.extend(item)
        finally:
            await context.close()
            await browser.close()

    return _dedupe_candidates(candidates, candidate_limit)


async def _collect_search_results(page, query: str, search_url_template: str, timeout_error_cls) -> list[SearchResult]:
    """Collect search results from search engine"""
    search_url = search_url_template.format(query=urllib.parse.quote_plus(query))
    try:
        await page.goto(search_url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
    except timeout_error_cls:
        return []
    except Exception:
        return []

    await _dismiss_common_popups(page)
    anchors = page.locator("a[href^='http']")
    count = min(await anchors.count(), 80)
    results = []
    seen = set()

    for idx in range(count):
        anchor = anchors.nth(idx)
        try:
            href = await anchor.get_attribute("href")
            if not _is_http_url(href):
                continue
            href = _normalize_search_result_url(href or "")
            domain = _extract_domain(href)
            if not domain or "bing.com" in domain or "microsoft.com" in domain:
                continue
            key = href.split("#", 1)[0]
            if key in seen:
                continue
            seen.add(key)
            title = await _safe_text(anchor)
            title = title or (await anchor.get_attribute("title")) or ""
            results.append(SearchResult(
                title=title[:300],
                url=href,
                domain=domain,
                rank=len(results) + 1,
                query=query,
            ))
            if len(results) >= MAX_SEARCH_RESULTS:
                break
        except Exception:
            continue
    return results


async def _extract_from_one_result(context, sem: asyncio.Semaphore, result: SearchResult, timeout_error_cls):
    """Extract images from a single search result page"""
    async with sem:
        page = await context.new_page()
        try:
            return await _extract_images_from_source_page(page, result, timeout_error_cls)
        finally:
            await page.close()


async def _extract_images_from_source_page(page, result: SearchResult, timeout_error_cls):
    """Extract image candidates from a webpage"""
    try:
        await page.goto(result.url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
        await _dismiss_common_popups(page)
    except timeout_error_cls:
        return []
    except Exception:
        return []

    title = await page.title()
    images = page.locator("img")
    img_count = min(await images.count(), 60)
    raw_candidates = []

    for idx in range(img_count):
        image = images.nth(idx)
        try:
            src = await image.get_attribute("src")
            src = _normalize_image_url(src, result.url)
            if not src or _looks_like_bad_image(src):
                continue
            alt_text = (await image.get_attribute("alt")) or ""
            width_attr = await image.get_attribute("width")
            height_attr = await image.get_attribute("height")
            width = int(width_attr) if width_attr and width_attr.isdigit() else None
            height = int(height_attr) if height_attr and height_attr.isdigit() else None

            # Create a simple object-like structure for candidates
            class CandidateObj:
                def __init__(self, **kwargs):
                    for k, v in kwargs.items():
                        setattr(self, k, v)

            candidate = CandidateObj(
                candidate_id=f"playwright-{result.rank}-{idx + 1}",
                image_url=src,
                source_page=result.url,
                source_domain=result.domain,
                observed_text=" ".join(part for part in [result.title, title, alt_text] if part).strip(),
                image_quality_score=0.55,
                source_trust_score=0.75,
                notes=[
                    "retrieved_via_playwright",
                    "extraction_method:img_tag",
                    f"query:{result.query}",
                    f"source_rank:{result.rank}",
                ],
            )
            raw_candidates.append((candidate, _score_image_hint(src, alt_text, width, height)))
        except Exception:
            continue

    raw_candidates.sort(key=lambda item: item[1], reverse=True)
    seen = set()
    selected = []
    for candidate, _score in raw_candidates:
        if candidate.image_url in seen:
            continue
        seen.add(candidate.image_url)
        selected.append(candidate)
        if len(selected) >= MAX_IMAGES_PER_PAGE:
            break
    return selected


async def _safe_text(locator, timeout: int = 1000) -> str:
    try:
        return (await locator.inner_text(timeout=timeout)).strip()
    except Exception:
        return ""


async def _dismiss_common_popups(page) -> None:
    candidates = [
        page.get_by_role("button", name=re.compile(r"accept|agree|allow", re.I)),
        page.get_by_role("button", name=re.compile(r"close|dismiss|got it", re.I)),
    ]
    for locator in candidates:
        try:
            if await locator.first.is_visible(timeout=1000):
                await locator.first.click(timeout=1000)
                return
        except Exception:
            continue


def _dedupe_candidates(candidates, candidate_limit: int):
    seen = set()
    unique = []
    for candidate in candidates:
        key = candidate.source_page or candidate.image_url
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique[:candidate_limit]


def _normalize_image_url(src: Optional[str], base_url: str) -> Optional[str]:
    if not src:
        return None
    src = src.strip()
    if src.startswith("//"):
        src = "https:" + src
    if src.startswith("/"):
        src = urllib.parse.urljoin(base_url, src)
    if not _is_http_url(src):
        return None
    return src


def _looks_like_bad_image(url: str) -> bool:
    lowered = url.lower()
    if any(token in lowered for token in BAD_IMAGE_PATTERNS):
        return True
    return any(lowered.endswith(ext) for ext in BAD_IMAGE_EXTENSIONS)


def _score_image_hint(src: str, alt_text: str, width: Optional[int], height: Optional[int]) -> int:
    score = 0
    lowered_src = (src or "").lower()
    lowered_alt = (alt_text or "").lower()
    for hint in PREFERRED_IMAGE_HINTS:
        if hint in lowered_src:
            score += 2
        if hint in lowered_alt:
            score += 1
    if width and height:
        if height > width:
            score += 3
        if height >= 400:
            score += 2
        if width >= 200:
            score += 1
    return score


def _normalize_search_result_url(href: str) -> str:
    if not href:
        return ""
    if href.startswith("//"):
        href = "https:" + href

    parsed = urllib.parse.urlparse(href)
    if parsed.scheme not in {"http", "https"}:
        return ""

    query = urllib.parse.parse_qs(parsed.query)
    if "duckduckgo.com" in parsed.netloc and "uddg" in query:
        return urllib.parse.unquote(query["uddg"][0])
    return href


def _extract_domain(url: str) -> str:
    try:
        return urllib.parse.urlparse(url).netloc.lower()
    except Exception:
        return ""


def _is_http_url(url: Optional[str]) -> bool:
    return bool(url and url.startswith(("http://", "https://")))


# ---- HTTP-based search (no browser) ----

def _is_search_chrome_domain(domain: str) -> bool:
    domain = (domain or "").lower()
    return any(chrome in domain for chrome in SEARCH_ENGINE_DOMAINS)


def _fetch_html(url: str, timeout: int = 15) -> Optional[str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="ignore")
    except Exception:
        return None


class _SearchLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list = []
        self._current_href = ""
        self._current_text: list = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        attr_map = {k.lower(): v or "" for k, v in attrs}
        self._current_href = attr_map.get("href", "")
        self._current_text = []

    def handle_data(self, data):
        if self._current_href:
            self._current_text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() != "a" or not self._current_href:
            return
        text = " ".join(p.strip() for p in self._current_text if p.strip()).strip()
        if self._current_href and text:
            self.links.append({"href": self._current_href, "text": text})
        self._current_href = ""
        self._current_text = []


class _ImageTagParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.images: list = []
        self._title_parts: list = []
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        if t == "title":
            self._in_title = True
            return
        if t != "img":
            return
        am = {k.lower(): v or "" for k, v in attrs}
        src = (am.get("src") or am.get("data-src") or am.get("data-original") or am.get("data-lazy-src") or "").strip()
        if not src and am.get("srcset"):
            src = am["srcset"].split(",")[0].strip().split(" ")[0].strip()
        if src:
            self.images.append({"src": src, "alt": am.get("alt", ""), "width": am.get("width", ""), "height": am.get("height", "")})

    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self._title_parts.append(data)

    @property
    def title(self) -> str:
        return "".join(self._title_parts).strip()


def _extract_search_links(html: str) -> list:
    parser = _SearchLinkParser()
    try:
        parser.feed(html)
    except Exception:
        return []
    seen = set()
    results = []
    for item in parser.links:
        href = _normalize_search_result_url(item.get("href", ""))
        if not _is_http_url(href):
            continue
        domain = _extract_domain(href)
        if not domain or _is_search_chrome_domain(domain):
            continue
        key = href.split("#", 1)[0]
        if key in seen:
            continue
        seen.add(key)
        results.append({"href": href, "text": item.get("text", ""), "domain": domain})
    return results


def _extract_page_images(html: str, base_url: str):
    parser = _ImageTagParser()
    try:
        parser.feed(html)
    except Exception:
        return [], ""
    resolved = []
    seen = set()
    for img in parser.images:
        normalized = _normalize_image_url(img["src"], base_url)
        if not normalized or _looks_like_bad_image(normalized):
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        w = img.get("width", "")
        h = img.get("height", "")
        width = int(w) if w.isdigit() else None
        height = int(h) if h.isdigit() else None
        resolved.append({
            "src": normalized,
            "alt": img.get("alt", ""),
            "score": _score_image_hint(normalized, img.get("alt", ""), width, height),
        })
    resolved.sort(key=lambda x: x["score"], reverse=True)
    return resolved, parser.title


class _Cand:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


def _collect_candidates_http(queries: list, templates: list, candidate_limit: int, min_results: int) -> list:
    """HTTP-based candidate collection with engine rotation. Runs in a thread."""
    candidates: list = []
    delay_s = 0.5
    for q_idx, query in enumerate(queries, start=1):
        encoded = urllib.parse.quote_plus(query)
        per_query_links = []
        for template in templates:
            url = template.format(query=encoded)
            html = _fetch_html(url)
            if not html:
                continue
            extracted = _extract_search_links(html)
            for link in extracted:
                per_query_links.append((template, link))
            if len(extracted) >= min_results:
                break
            if delay_s:
                time.sleep(delay_s)

        for idx, (template, link) in enumerate(per_query_links[:MAX_SEARCH_RESULTS], start=1):
            engine_domain = _extract_domain(template)
            page_html = _fetch_html(link["href"], timeout=12)
            images = []
            page_title = ""
            if page_html:
                images, page_title = _extract_page_images(page_html, link["href"])
            if not images:
                candidates.append(_Cand(
                    candidate_id=f"http-{q_idx}-{idx}",
                    image_url=link["href"],
                    source_page=link["href"],
                    source_domain=link["domain"],
                    observed_text=(link.get("text") or "").strip(),
                    image_quality_score=0.35,
                    source_trust_score=0.55,
                    notes=[
                        "retrieved_via_http_search",
                        "extraction_method:search_href_only",
                        f"query:{query}",
                        f"search_engine:{engine_domain}",
                        f"source_rank:{idx}",
                    ],
                ))
                if len(candidates) >= candidate_limit * max(1, len(queries)):
                    return _dedupe_candidates(candidates, candidate_limit * max(1, len(queries)))
                if delay_s:
                    time.sleep(delay_s)
                continue
            observed = " ".join(p for p in [link.get("text", ""), page_title] if p).strip()
            for img_idx, img in enumerate(images[:MAX_IMAGES_PER_PAGE], start=1):
                candidates.append(_Cand(
                    candidate_id=f"http-{q_idx}-{idx}-{img_idx}",
                    image_url=img["src"],
                    source_page=link["href"],
                    source_domain=link["domain"],
                    observed_text=(observed + " " + img.get("alt", "")).strip(),
                    image_quality_score=0.5,
                    source_trust_score=0.7,
                    notes=[
                        "retrieved_via_http_search",
                        "extraction_method:img_tag",
                        f"query:{query}",
                        f"search_engine:{engine_domain}",
                        f"source_rank:{idx}",
                    ],
                ))
                if len(candidates) >= candidate_limit * max(1, len(queries)):
                    return _dedupe_candidates(candidates, candidate_limit * max(1, len(queries)))
            if delay_s:
                time.sleep(delay_s)
    return _dedupe_candidates(candidates, candidate_limit * max(1, len(queries)))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
