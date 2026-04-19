from dataclasses import dataclass, field

from backend.app.core.constants import FailReason, FieldStatus
from backend.app.models.result import FieldMatch
from backend.app.models.sku import ParsedIdentity
from backend.app.services.matcher import is_readable_enough


@dataclass
class HardFailEvaluation:
    should_fail: bool
    reason: FailReason | None = None
    notes: list[str] = field(default_factory=list)


def evaluate_hard_fail(
    parsed: ParsedIdentity,
    field_matches: dict[str, FieldMatch],
    observed_text: str,
) -> HardFailEvaluation:
    readable = is_readable_enough(observed_text)
    notes: list[str] = []

    producer = field_matches["producer"]
    if parsed.producer and _missing_required_field(producer, readable):
        return HardFailEvaluation(
            should_fail=True,
            reason=FailReason.PRODUCER_MISMATCH,
            notes=["Observed text is readable but producer was not verified."],
        )

    appellation = field_matches["appellation"]
    if parsed.appellation and _missing_required_field(appellation, readable):
        return HardFailEvaluation(
            should_fail=True,
            reason=FailReason.APPELLATION_MISMATCH,
            notes=["Observed text is readable but appellation was not verified."],
        )

    vineyard = field_matches["vineyard_or_cuvee"]
    if parsed.vineyard_or_cuvee and _missing_required_field(vineyard, readable):
        return HardFailEvaluation(
            should_fail=True,
            reason=FailReason.VINEYARD_OR_CUVEE_MISMATCH,
            notes=["Observed text is readable but required vineyard/cuvee was not verified."],
        )

    classification = field_matches["classification"]
    if classification.status == FieldStatus.CONFLICT:
        return HardFailEvaluation(
            should_fail=True,
            reason=FailReason.CLASSIFICATION_CONFLICT,
            notes=["Visible classification conflicted with the target wine."],
        )

    vintage = field_matches["vintage"]
    if vintage.status == FieldStatus.CONFLICT:
        return HardFailEvaluation(
            should_fail=True,
            reason=FailReason.VINTAGE_MISMATCH,
            notes=["Visible vintage conflicted with the target wine."],
        )

    core_statuses = [producer.status, appellation.status]
    if parsed.vineyard_or_cuvee:
        core_statuses.append(vineyard.status)

    if not readable and not any(status == FieldStatus.MATCH for status in core_statuses):
        notes.append("Observed text is too sparse to verify core identity.")
        return HardFailEvaluation(
            should_fail=True,
            reason=FailReason.UNREADABLE_CORE_IDENTITY,
            notes=notes,
        )

    return HardFailEvaluation(should_fail=False, notes=notes)


def _missing_required_field(match: FieldMatch, readable: bool) -> bool:
    return readable and match.status != FieldStatus.MATCH
