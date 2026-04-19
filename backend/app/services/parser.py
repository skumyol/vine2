import re

from backend.app.models.sku import AnalyzeRequest, ParsedIdentity
from backend.app.utils.text_normalize import normalize_text


CLASSIFICATION_PATTERNS = [
    r"\bgrand cru classe\b",
    r"\bgrand cru\b",
    r"\bpremier cru\b",
    r"\b1er cru\b",
    r"\bblanc de noirs\b",
    r"\bvendanges tardives\b",
    r"\bbrut\b",
]

APPELLATION_PATTERNS = [
    ("morey saint denis", "Morey-Saint-Denis"),
    ("saint emilion", "Saint-Emilion"),
    ("latricieres chambertin", "Latricieres-Chambertin"),
    ("charmes chambertin", "Charmes-Chambertin"),
    ("cornas", "Cornas"),
    ("barolo", "Barolo"),
    ("riesling", "Riesling"),
]

PRODUCER_PREFIXES = {
    "domaine",
    "chateau",
    "champagne",
    "castello",
    "poderi",
    "clos",
    "comtesse",
}

STOP_WORDS = {
    "aux",
    "blanc",
    "brut",
    "bussia",
    "capucins",
    "cariad",
    "chalky",
    "clos",
    "cornas",
    "cuvee",
    "graveyard",
    "grand",
    "gris",
    "la",
    "latricieres",
    "les",
    "monts",
    "premier",
    "reserve",
    "riesling",
    "saint",
    "shiraz",
    "trousseau",
    "vendanges",
    "vin",
    "vineyard",
    "watson",
}

STOP_PHRASES = {
    "morey saint denis",
    "saint emilion",
    "latricieres chambertin",
    "charmes chambertin",
}


def parse_identity(payload: AnalyzeRequest) -> ParsedIdentity:
    raw_name = payload.wine_name.strip()
    normalized_name = normalize_text(raw_name)
    quoted_match = re.search(r"['\"]([^'\"]+)['\"]", raw_name)
    quoted_value = quoted_match.group(1).strip() if quoted_match else None

    classification = None
    for pattern in CLASSIFICATION_PATTERNS:
        match = re.search(pattern, normalized_name)
        if match:
            classification = match.group(0)
            break

    appellation = _guess_appellation(normalized_name)
    producer = _guess_producer(raw_name, normalized_name)
    vineyard_or_cuvee = quoted_value or _guess_vineyard_or_cuvee(
        raw_name,
        normalized_name,
        producer=producer,
        appellation=appellation,
        classification=classification,
    )

    return ParsedIdentity(
        producer=producer,
        appellation=appellation,
        vineyard_or_cuvee=vineyard_or_cuvee,
        classification=classification,
        vintage=payload.vintage.strip(),
        format=payload.format.strip(),
        region=payload.region.strip(),
        raw_wine_name=raw_name,
        normalized_wine_name=normalized_name,
    )


def _guess_appellation(normalized_wine_name: str) -> str | None:
    normalized_wine_name = normalize_text(normalized_wine_name)
    for needle, label in APPELLATION_PATTERNS:
        if needle in normalized_wine_name:
            return label
    return None


def _guess_producer(wine_name: str, normalized_wine_name: str) -> str | None:
    stop_words = set(STOP_WORDS)
    stop_phrases = set(STOP_PHRASES)
    for needle, _ in APPELLATION_PATTERNS:
        stop_phrases.add(needle)

    tokens = wine_name.replace("'", " ").replace('"', " ").split()
    normalized_tokens = [normalize_text(token) for token in tokens]
    if not normalized_tokens:
        return None

    limit = 2
    if normalized_tokens[0] in PRODUCER_PREFIXES:
        limit = 3
    elif len(normalized_tokens) > 1:
        limit = 2

    producer_tokens: list[str] = []
    for index, token in enumerate(tokens):
        cleaned = normalized_tokens[index]
        if index > 0 and (cleaned in stop_words or cleaned in stop_phrases):
            break
        producer_tokens.append(token)
        if len(producer_tokens) >= limit:
            break

    producer = " ".join(producer_tokens).strip("- ").strip()
    if not producer:
        return None

    producer_normalized = normalize_text(producer)
    if producer_normalized == normalized_wine_name:
        return None
    return producer or None


def _guess_vineyard_or_cuvee(
    wine_name: str,
    normalized_wine_name: str,
    *,
    producer: str | None,
    appellation: str | None,
    classification: str | None,
) -> str | None:
    cleaned = wine_name

    if producer:
        cleaned = re.sub(re.escape(producer), "", cleaned, flags=re.IGNORECASE).strip()
    if appellation:
        cleaned = re.sub(re.escape(appellation), "", cleaned, flags=re.IGNORECASE).strip()
    if classification:
        cleaned = re.sub(re.escape(classification), "", cleaned, flags=re.IGNORECASE).strip()

    cleaned = re.sub(r"\b(?:grand cru classe|grand cru|premier cru|1er cru|blanc de noirs|vendanges tardives|brut)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -,'\"")
    if not cleaned:
        return None

    normalized_cleaned = normalize_text(cleaned)
    normalized_appellation = normalize_text(appellation or "")
    normalized_producer = normalize_text(producer or "")
    if normalized_cleaned in {"", normalized_appellation, normalized_producer, normalized_wine_name}:
        return None
    if len(normalized_cleaned.split()) < 1:
        return None
    return cleaned
