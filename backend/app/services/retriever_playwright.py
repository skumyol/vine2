import asyncio
import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser

from backend.app.core.config import get_settings
from backend.app.core.domain_filters import filter_candidates_by_domain
from backend.app.models.candidate import Candidate


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def _call_playwright_service(queries: list[str], settings) -> list[Candidate]:
    """Call the external Playwright microservice via HTTP."""
    import urllib.error

    service_url = settings.playwright_service_url.rstrip("/")
    # Cap queries sent to service to keep latency under timeout budget
    capped_queries = list(queries)[:3]
    payload = {
        "queries": capped_queries,
        "search_url_template": settings.playwright_search_url_template,
        "search_url_templates": list(settings.playwright_search_url_templates or []),
        "candidate_limit": settings.candidate_download_limit,
        "http_first": True,
        "min_results_per_engine": max(1, settings.playwright_http_min_results),
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    request = urllib.request.Request(
        f"{service_url}/search",
        data=data,
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Playwright service error: {exc.code} {exc.reason}") from exc
    except Exception as exc:
        raise RuntimeError(f"Playwright service call failed: {exc}") from exc

    candidates = []
    for item in result.get("candidates", []):
        candidates.append(
            Candidate(
                candidate_id=item.get("candidate_id", ""),
                image_url=item.get("image_url", ""),
                source_page=item.get("source_page", ""),
                source_domain=item.get("source_domain", ""),
                observed_text=item.get("observed_text", ""),
                image_quality_score=float(item.get("image_quality_score", 0.0)),
                source_trust_score=float(item.get("source_trust_score", 0.0)),
                notes=list(item.get("notes", [])),
            )
        )
    return candidates

NAV_TIMEOUT_MS = 15000
MAX_SEARCH_RESULTS = 8
MAX_IMAGES_PER_PAGE = 12
MAX_CONCURRENT_PAGES = 4

BAD_IMAGE_PATTERNS = (
    "placeholder",
    "no-image",
    "no_image",
    "default",
    "sprite",
    "icon",
    "logo",
    "avatar",
    "banner",
    "thumb",
)

BAD_IMAGE_EXTENSIONS = (".svg",)
PREFERRED_IMAGE_HINTS = ("product", "bottle", "wine", "vin", "image", "photo")


@dataclass
class SearchResult:
    title: str
    url: str
    domain: str
    rank: int
    query: str


def collect_candidates(queries: list[str]) -> list[Candidate]:
    if not queries:
        return []

    settings = get_settings()

    # Use HTTP service if configured
    if settings.playwright_service_url:
        return _call_playwright_service(queries, settings)

    # Fall back to local Playwright execution
    try:
        return asyncio.run(_collect_candidates_async(queries))
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_collect_candidates_async(queries))
        finally:
            loop.close()


def playwright_self_check() -> dict:
    settings = get_settings()

    # Use HTTP service if configured
    if settings.playwright_service_url:
        import urllib.error

        service_url = settings.playwright_service_url.rstrip("/")
        request = urllib.request.Request(
            f"{service_url}/self-check",
            headers={"Accept": "application/json"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return {"error": f"Playwright service error: {exc.code} {exc.reason}"}
        except Exception as exc:
            return {"error": f"Playwright service call failed: {exc}"}

    # Fall back to local Playwright execution
    return asyncio.run(_playwright_self_check_async())


async def _collect_candidates_async(queries: list[str]) -> list[Candidate]:
    settings = get_settings()
    if settings.playwright_force_http_fallback:
        return _collect_candidates_http_fallback(queries)

    try:
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError
        from playwright.async_api import async_playwright
    except ImportError:
        return _collect_candidates_http_fallback(queries)

    candidates: list[Candidate] = []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=settings.playwright_headless,
                args=list(settings.playwright_launch_args),
            )
            context = await browser.new_context()
            try:
                for query in queries:
                    search_page = await context.new_page()
                    try:
                        search_results = await _collect_search_results(
                            search_page,
                            query,
                            timeout_error_cls=PlaywrightTimeoutError,
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
    except Exception:
        return _collect_candidates_http_fallback(queries)

    return _dedupe_candidates(candidates)


async def _playwright_self_check_async() -> dict:
    settings = get_settings()
    details = {
        "playwright_imported": False,
        "browser_launch_ok": False,
        "page_load_ok": False,
        "http_fallback_forced": settings.playwright_force_http_fallback,
        "launch_args": list(settings.playwright_launch_args),
        "search_url_template": settings.playwright_search_url_template,
    }

    if settings.playwright_force_http_fallback:
        details["reason"] = "HTTP fallback is forced by configuration."
        return details

    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        details["reason"] = f"Playwright import failed: {type(exc).__name__}"
        return details

    details["playwright_imported"] = True
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=settings.playwright_headless,
                args=list(settings.playwright_launch_args),
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


async def _collect_search_results(page, query: str, *, timeout_error_cls) -> list[SearchResult]:
    settings = get_settings()
    search_url = settings.playwright_search_url_template.format(query=urllib.parse.quote_plus(query))
    try:
        await page.goto(search_url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
    except timeout_error_cls:
        return []
    except Exception:
        return []

    await _dismiss_common_popups(page)
    anchors = page.locator("a[href^='http']")
    count = min(await anchors.count(), 80)
    results: list[SearchResult] = []
    seen: set[str] = set()

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
            results.append(
                SearchResult(
                    title=title[:300],
                    url=href,
                    domain=domain,
                    rank=len(results) + 1,
                    query=query,
                )
            )
            if len(results) >= MAX_SEARCH_RESULTS:
                break
        except Exception:
            continue
    return results


async def _extract_from_one_result(context, sem: asyncio.Semaphore, result: SearchResult, timeout_error_cls) -> list[Candidate]:
    async with sem:
        page = await context.new_page()
        try:
            return await _extract_images_from_source_page(page, result, timeout_error_cls)
        finally:
            await page.close()


async def _extract_images_from_source_page(page, result: SearchResult, timeout_error_cls) -> list[Candidate]:
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
    raw_candidates: list[tuple[Candidate, int]] = []

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
            candidate = Candidate(
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
    seen: set[str] = set()
    selected: list[Candidate] = []
    for candidate, _score in raw_candidates:
        if candidate.image_url in seen:
            continue
        seen.add(candidate.image_url)
        selected.append(candidate)
        if len(selected) >= MAX_IMAGES_PER_PAGE:
            break
    return selected


SEARCH_ENGINE_DOMAINS = (
    "bing.com",
    "microsoft.com",
    "msn.com",
    "duckduckgo.com",
    "duck.com",
    "brave.com",
    "search.brave",
    "startpage.com",
    "ixquick.com",
    "mojeek.com",
    "google.com",
    "googleusercontent.com",
    "googleadservices.com",
    "youtube.com/redirect",
    "aka.ms",
    "mastodon.social",
    "t.co",
    "facebook.com/sharer",
    "twitter.com/share",
)


def _is_search_chrome_domain(domain: str) -> bool:
    domain = (domain or "").lower()
    return any(chrome in domain for chrome in SEARCH_ENGINE_DOMAINS)


def _search_templates(settings) -> list[str]:
    templates = list(settings.playwright_search_url_templates or [])
    primary = settings.playwright_search_url_template
    if primary and primary not in templates:
        templates.insert(0, primary)
    return templates or [primary]


def _fetch_search_html(url: str, *, timeout: int = 15) -> str | None:
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


def _extract_search_result_links(html: str) -> list[dict[str, str]]:
    parser = _SearchLinkParser()
    parser.feed(html)
    results: list[dict[str, str]] = []
    seen: set[str] = set()
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


class _ImageTagParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.images: list[dict[str, str]] = []
        self._title_parts: list[str] = []
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_l = tag.lower()
        if tag_l == "title":
            self._in_title = True
            return
        if tag_l != "img":
            return
        attr_map = {key.lower(): value or "" for key, value in attrs}
        src = (
            attr_map.get("src")
            or attr_map.get("data-src")
            or attr_map.get("data-original")
            or attr_map.get("data-lazy-src")
            or ""
        ).strip()
        if not src:
            srcset = attr_map.get("srcset", "")
            if srcset:
                src = srcset.split(",")[0].strip().split(" ")[0].strip()
        if not src:
            return
        self.images.append({
            "src": src,
            "alt": attr_map.get("alt", ""),
            "width": attr_map.get("width", ""),
            "height": attr_map.get("height", ""),
        })

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)

    @property
    def title(self) -> str:
        return "".join(self._title_parts).strip()


def _extract_images_from_html(html: str, base_url: str) -> tuple[list[dict[str, str]], str]:
    parser = _ImageTagParser()
    try:
        parser.feed(html)
    except Exception:
        return [], ""
    resolved: list[dict[str, str]] = []
    seen: set[str] = set()
    for img in parser.images:
        normalized = _normalize_image_url(img["src"], base_url)
        if not normalized or _looks_like_bad_image(normalized):
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        width_raw = img.get("width") or ""
        height_raw = img.get("height") or ""
        width = int(width_raw) if width_raw.isdigit() else None
        height = int(height_raw) if height_raw.isdigit() else None
        resolved.append({
            "src": normalized,
            "alt": img.get("alt", ""),
            "score": _score_image_hint(normalized, img.get("alt", ""), width, height),
        })
    resolved.sort(key=lambda item: item["score"], reverse=True)
    return resolved, parser.title


def _collect_candidates_http_fallback(queries: list[str]) -> list[Candidate]:
    settings = get_settings()
    templates = _search_templates(settings)
    delay_s = max(0, settings.playwright_http_request_delay_ms) / 1000.0
    min_results = max(1, settings.playwright_http_min_results)
    candidates: list[Candidate] = []
    import time

    for query_index, query in enumerate(queries, start=1):
        encoded = urllib.parse.quote_plus(query)
        per_query_links: list[tuple[str, dict[str, str]]] = []
        for template in templates:
            search_url = template.format(query=encoded)
            html = _fetch_search_html(search_url)
            if not html:
                continue
            extracted = _extract_search_result_links(html)
            for link in extracted:
                per_query_links.append((template, link))
            if len(extracted) >= min_results:
                break
            if delay_s:
                time.sleep(delay_s)

        for index, (template, link) in enumerate(per_query_links[:MAX_SEARCH_RESULTS], start=1):
            engine_domain = _extract_domain(template)
            page_html = _fetch_search_html(link["href"], timeout=12)
            images: list[dict[str, str]] = []
            page_title = ""
            if page_html:
                images, page_title = _extract_images_from_html(page_html, link["href"])
            if not images:
                # Degraded fallback: emit the source URL itself as a candidate so
                # downstream pipeline still gets something to evaluate.
                candidates.append(
                    Candidate(
                        candidate_id=f"http-search-{query_index}-{index}",
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
                            f"source_rank:{index}",
                        ],
                    )
                )
                if len(candidates) >= settings.candidate_download_limit * len(queries):
                    break
                if delay_s:
                    time.sleep(delay_s)
                continue
            observed = " ".join(part for part in [link.get("text", ""), page_title] if part).strip()
            for img_index, img in enumerate(images[:MAX_IMAGES_PER_PAGE], start=1):
                candidates.append(
                    Candidate(
                        candidate_id=f"http-search-{query_index}-{index}-{img_index}",
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
                            f"source_rank:{index}",
                        ],
                    )
                )
                if len(candidates) >= settings.candidate_download_limit * len(queries):
                    break
            if len(candidates) >= settings.candidate_download_limit * len(queries):
                break
            if delay_s:
                time.sleep(delay_s)
        if len(candidates) >= settings.candidate_download_limit * len(queries):
            break
    return _dedupe_candidates(candidates)


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


class _SearchLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str]] = []
        self._current_href = ""
        self._current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attr_map = {key.lower(): value or "" for key, value in attrs}
        self._current_href = attr_map.get("href", "")
        self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_href:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or not self._current_href:
            return
        text = " ".join(part.strip() for part in self._current_text if part.strip()).strip()
        if self._current_href and text:
            self.links.append({"href": self._current_href, "text": text})
        self._current_href = ""
        self._current_text = []


def _normalize_image_url(src: str | None, base_url: str) -> str | None:
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


def _score_image_hint(src: str, alt_text: str, width: int | None, height: int | None) -> int:
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


def _dedupe_candidates(candidates: list[Candidate]) -> list[Candidate]:
    settings = get_settings()
    filtered = filter_candidates_by_domain(candidates)
    seen: set[str] = set()
    unique: list[Candidate] = []
    for candidate in filtered:
        key = candidate.source_page or candidate.image_url
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique[: settings.candidate_download_limit]


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


def _is_http_url(url: str | None) -> bool:
    return bool(url and url.startswith(("http://", "https://")))
