"""OCR Evaluation - Measure field-level OCR success rates."""

import json
from collections import defaultdict
from pathlib import Path

from backend.app.core.config import get_settings
from backend.app.core.constants import FieldStatus, Verdict
from backend.app.models.result import AnalyzeResponse
from backend.app.models.sku import AnalyzeRequest, BatchAnalyzeRequest
from backend.app.services.pipeline_router import run_batch_analysis


FIELDS = ["producer", "appellation", "vineyard_or_cuvee", "classification", "vintage"]


def evaluate_ocr_accuracy(*, pipeline_name: str | None = None) -> dict:
    """Evaluate OCR field-level accuracy against fixture dataset.

    Returns per-field precision/recall for OCR matches vs expected values.
    """
    settings = get_settings()
    with settings.fixture_labels_path.open(encoding="utf-8") as handle:
        rows = json.load(handle)

    items = [
        AnalyzeRequest(
            wine_name=row["wine_name"],
            vintage=row["vintage"],
            format=row.get("format", "750ml"),
            region=row.get("region", ""),
        )
        for row in rows
    ]
    label_map = {row["wine_name"]: row for row in rows}

    batch_response = run_batch_analysis(
        BatchAnalyzeRequest(items=items),
        pipeline_name=pipeline_name
    )

    # Collect OCR field match statistics
    field_stats = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "total": 0})
    ocr_available_count = 0
    ocr_passed_count = 0

    for result in batch_response.results:
        label = label_map[result.input.wine_name]
        expected_fields = {
            "producer": label.get("expected_producer", ""),
            "appellation": label.get("expected_appellation", ""),
            "vineyard_or_cuvee": label.get("expected_vineyard", ""),
            "classification": label.get("expected_classification", ""),
            "vintage": label.get("expected_vintage", result.input.vintage),
        }

        # Find OCR vote in module_votes
        ocr_vote = None
        for vote in result.debug.module_votes or []:
            if vote.module == "ocr":
                ocr_vote = vote
                break

        if ocr_vote:
            ocr_available_count += 1
            if ocr_vote.passed:
                ocr_passed_count += 1

        # Evaluate each field
        for field in FIELDS:
            expected = expected_fields.get(field, "").strip().lower() if expected_fields.get(field) else ""
            has_expected = bool(expected)

            field_match = None
            if ocr_vote and ocr_vote.field_matches:
                field_match = ocr_vote.field_matches.get(field)

            if field_match:
                status = field_match.status
                extracted = (field_match.extracted or "").strip().lower()

                # Determine correctness
                if status == FieldStatus.MATCH:
                    if has_expected:
                        if extracted and expected in extracted or extracted in expected:
                            field_stats[field]["tp"] += 1
                        else:
                            field_stats[field]["fp"] += 1
                    else:
                        field_stats[field]["fp"] += 1  # Match when no expectation
                elif status == FieldStatus.CONFLICT:
                    if has_expected:
                        field_stats[field]["fn"] += 1  # Missed the correct value
                    else:
                        field_stats[field]["tn"] += 1  # Correctly rejected
                else:  # UNVERIFIED or NO_SIGNAL
                    if has_expected:
                        field_stats[field]["fn"] += 1  # Couldn't verify
                    else:
                        field_stats[field]["tn"] += 1
            else:
                # No field match data
                if has_expected:
                    field_stats[field]["fn"] += 1
                else:
                    field_stats[field]["tn"] += 1

            field_stats[field]["total"] += 1

    # Compute metrics per field
    per_field = {}
    for field in FIELDS:
        stats = field_stats[field]
        tp, fp, fn, tn = stats["tp"], stats["fp"], stats["fn"], stats["tn"]
        total = stats["total"]

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        accuracy = (tp + tn) / total if total > 0 else 0.0

        per_field[field] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "accuracy": round(accuracy, 4),
            "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        }

    # Aggregate across all fields
    all_tp = sum(field_stats[f]["tp"] for f in FIELDS)
    all_fp = sum(field_stats[f]["fp"] for f in FIELDS)
    all_fn = sum(field_stats[f]["fn"] for f in FIELDS)
    all_tn = sum(field_stats[f]["tn"] for f in FIELDS)

    overall_precision = all_tp / (all_tp + all_fp) if (all_tp + all_fp) > 0 else 0.0
    overall_recall = all_tp / (all_tp + all_fn) if (all_tp + all_fn) > 0 else 0.0
    overall_f1 = (2 * overall_precision * overall_recall) / (overall_precision + overall_recall) if (overall_precision + overall_recall) > 0 else 0.0

    return {
        "dataset": "fixture",
        "total_skus": len(batch_response.results),
        "ocr_available": ocr_available_count,
        "ocr_passed": ocr_passed_count,
        "ocr_availability_rate": round(ocr_available_count / len(batch_response.results), 4) if batch_response.results else 0.0,
        "ocr_pass_rate": round(ocr_passed_count / ocr_available_count, 4) if ocr_available_count > 0 else 0.0,
        "per_field": per_field,
        "overall": {
            "precision": round(overall_precision, 4),
            "recall": round(overall_recall, 4),
            "f1": round(overall_f1, 4),
            "confusion": {"tp": all_tp, "fp": all_fp, "fn": all_fn, "tn": all_tn},
        },
        "pipeline": pipeline_name or settings.pipeline_name,
    }


def write_ocr_evaluation(path: Path, *, pipeline_name: str | None = None) -> None:
    """Run OCR evaluation and write results to file."""
    metrics = evaluate_ocr_accuracy(pipeline_name=pipeline_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
