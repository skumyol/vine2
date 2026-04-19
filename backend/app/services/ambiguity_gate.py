from backend.app.core.constants import FieldStatus
from backend.app.models.result import ModuleVote
from backend.app.models.sku import ParsedIdentity


def should_run_vlm(parsed: ParsedIdentity, candidate_observed_text: str, ocr_vote: ModuleVote, prefilter: dict) -> tuple[bool, str]:
    if not prefilter.get("passed", False):
        return False, "OpenCV prefilter failed."
    if not ocr_vote.passed:
        return False, "OCR vote already rejected the candidate."

    field_matches = ocr_vote.field_matches
    producer_status = field_matches.get("producer").status if field_matches.get("producer") else FieldStatus.UNVERIFIED
    appellation_status = field_matches.get("appellation").status if field_matches.get("appellation") else FieldStatus.UNVERIFIED
    cuvee_status = field_matches.get("vineyard_or_cuvee").status if field_matches.get("vineyard_or_cuvee") else FieldStatus.UNVERIFIED
    vintage_status = field_matches.get("vintage").status if field_matches.get("vintage") else FieldStatus.UNVERIFIED
    readable_label = float(prefilter.get("label_visible", 0.0))

    if producer_status == FieldStatus.MATCH and appellation_status == FieldStatus.MATCH:
        if cuvee_status != FieldStatus.MATCH or vintage_status != FieldStatus.MATCH:
            return True, "Core wine identity is plausible but vineyard/cuvee or vintage remains uncertain."

    if "grand cru" in candidate_observed_text.lower() or "1er cru" in candidate_observed_text.lower():
        if ocr_vote.confidence < 0.95:
            return True, "High-risk classification wine needs VLM confirmation."

    if readable_label < 0.45 and ocr_vote.confidence >= 0.7:
        return True, "OCR saw some matching evidence but the visible label quality is weak."

    if ocr_vote.confidence >= 0.92:
        return False, "OCR vote is already strong enough."
    if ocr_vote.confidence >= 0.78:
        return True, "Candidate is ambiguous enough to benefit from VLM verification."
    return False, "OCR confidence is too weak to justify a VLM escalation."
