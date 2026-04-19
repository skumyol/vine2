import re
from typing import Iterable

from backend.app.core.constants import FieldStatus
from backend.app.models.result import FieldMatch
from backend.app.models.sku import ParsedIdentity
from backend.app.utils.text_normalize import normalize_text


KNOWN_CLASSIFICATIONS = [
    "grand cru classe",
    "grand cru",
    "1er cru",
    "blanc de noirs",
    "vendanges tardives",
    "brut",
]


def build_field_matches(parsed: ParsedIdentity, observed_text: str) -> dict[str, FieldMatch]:
    normalized_observed = normalize_text(observed_text)
    years = re.findall(r"\b(19\d{2}|20\d{2}|nv)\b", normalized_observed)

    return {
        "producer": _match_phrase(parsed.producer, normalized_observed),
        "appellation": _match_phrase(parsed.appellation, normalized_observed),
        "vineyard_or_cuvee": _match_phrase(parsed.vineyard_or_cuvee, normalized_observed),
        "classification": _match_classification(parsed.classification, normalized_observed),
        "vintage": _match_vintage(parsed.vintage, years),
    }


def is_readable_enough(observed_text: str) -> bool:
    normalized = normalize_text(observed_text)
    tokens = [token for token in normalized.split() if len(token) > 1]
    return len(tokens) >= 4


def _match_phrase(target: str | None, observed_text: str) -> FieldMatch:
    if not target:
        return FieldMatch(status=FieldStatus.NO_SIGNAL, confidence=0.0)

    normalized_target = normalize_text(target)
    if not observed_text:
        return FieldMatch(target=target, status=FieldStatus.UNVERIFIED, confidence=0.0)

    if normalized_target in observed_text:
        return FieldMatch(
            target=target,
            extracted=target,
            status=FieldStatus.MATCH,
            confidence=_phrase_confidence(normalized_target),
        )

    return FieldMatch(target=target, status=FieldStatus.UNVERIFIED, confidence=0.0)


def _match_classification(target: str | None, observed_text: str) -> FieldMatch:
    if not target:
        return FieldMatch(status=FieldStatus.NO_SIGNAL, confidence=0.0)

    normalized_target = normalize_text(target)
    visible_classes = [label for label in KNOWN_CLASSIFICATIONS if label in observed_text]
    if normalized_target in observed_text:
        return FieldMatch(
            target=target,
            extracted=target,
            status=FieldStatus.MATCH,
            confidence=0.9,
        )

    if visible_classes:
        return FieldMatch(
            target=target,
            extracted=", ".join(visible_classes),
            status=FieldStatus.CONFLICT,
            confidence=0.9,
        )

    return FieldMatch(target=target, status=FieldStatus.UNVERIFIED, confidence=0.0)


def _match_vintage(target: str | None, visible_years: Iterable[str]) -> FieldMatch:
    if not target:
        return FieldMatch(status=FieldStatus.NO_SIGNAL, confidence=0.0)

    years = list(dict.fromkeys(visible_years))
    normalized_target = normalize_text(target)

    if normalized_target in years:
        return FieldMatch(
            target=target,
            extracted=target,
            status=FieldStatus.MATCH,
            confidence=0.95,
        )

    if years:
        return FieldMatch(
            target=target,
            extracted=", ".join(years),
            status=FieldStatus.CONFLICT,
            confidence=0.95,
        )

    return FieldMatch(target=target, status=FieldStatus.UNVERIFIED, confidence=0.0)


def _phrase_confidence(normalized_target: str) -> float:
    token_count = len(normalized_target.split())
    if token_count >= 3:
        return 0.95
    if token_count == 2:
        return 0.9
    return 0.85
