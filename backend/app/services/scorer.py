from backend.app.models.result import ScoreBreakdown


WEIGHTS = {
    "producer": 0.25,
    "appellation": 0.20,
    "vineyard_or_cuvee": 0.20,
    "classification": 0.10,
    "vintage": 0.10,
    "ocr_clarity": 0.05,
    "image_quality": 0.05,
    "source_trust": 0.05,
}


def build_score_breakdown(
    *,
    producer: float,
    appellation: float,
    vineyard_or_cuvee: float,
    classification: float,
    vintage: float,
    ocr_clarity: float,
    image_quality: float,
    source_trust: float,
) -> ScoreBreakdown:
    return ScoreBreakdown(
        producer=producer * WEIGHTS["producer"],
        appellation=appellation * WEIGHTS["appellation"],
        vineyard_or_cuvee=vineyard_or_cuvee * WEIGHTS["vineyard_or_cuvee"],
        classification=classification * WEIGHTS["classification"],
        vintage=vintage * WEIGHTS["vintage"],
        ocr_clarity=ocr_clarity * WEIGHTS["ocr_clarity"],
        image_quality=image_quality * WEIGHTS["image_quality"],
        source_trust=source_trust * WEIGHTS["source_trust"],
    )


def total_score(score_breakdown: ScoreBreakdown) -> float:
    return round(
        score_breakdown.producer
        + score_breakdown.appellation
        + score_breakdown.vineyard_or_cuvee
        + score_breakdown.classification
        + score_breakdown.vintage
        + score_breakdown.ocr_clarity
        + score_breakdown.image_quality
        + score_breakdown.source_trust,
        4,
    )


def normalized_total_score(score_breakdown: ScoreBreakdown, active_weight: float) -> float:
    if active_weight <= 0:
        return 0.0
    raw_total = (
        score_breakdown.producer
        + score_breakdown.appellation
        + score_breakdown.vineyard_or_cuvee
        + score_breakdown.classification
        + score_breakdown.vintage
        + score_breakdown.ocr_clarity
        + score_breakdown.image_quality
        + score_breakdown.source_trust
    )
    return round(raw_total / active_weight, 4)
