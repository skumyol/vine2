import json
import csv
from pathlib import Path

from backend.app.core.config import get_settings
from backend.app.core.constants import Verdict
from backend.app.models.result import AnalyzeResponse
from backend.app.models.sku import AnalyzeRequest, BatchAnalyzeRequest
from backend.app.services.pipeline_router import run_batch_analysis


def evaluate_fixture_dataset(*, pipeline_name: str | None = None) -> dict:
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
    batch_response = run_batch_analysis(BatchAnalyzeRequest(items=items), pipeline_name=pipeline_name)

    true_positive = 0
    false_positive = 0
    false_negative = 0
    true_negative = 0
    per_sku: list[dict] = []

    for result in batch_response.results:
        label = label_map[result.input.wine_name]
        actual_positive = bool(label["expected_pass"])
        predicted_positive = result.verdict == Verdict.PASS

        if predicted_positive and actual_positive:
            true_positive += 1
        elif predicted_positive and not actual_positive:
            false_positive += 1
        elif not predicted_positive and actual_positive:
            false_negative += 1
        else:
            true_negative += 1

        per_sku.append(_per_sku_result(result, actual_positive))

    total = len(batch_response.results)
    accuracy = (true_positive + true_negative) / total if total else 0.0
    precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) else 0.0
    recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) else 0.0

    return {
        "total": total,
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "confusion_matrix": {
            "tp": true_positive,
            "fp": false_positive,
            "fn": false_negative,
            "tn": true_negative,
        },
        "per_sku": per_sku,
    }


def write_evaluation(path: Path) -> None:
    metrics = evaluate_fixture_dataset()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")


def evaluate_live_dataset(
    *,
    csv_path: Path | None = None,
    backend: str = "hybrid",
    pipeline_name: str | None = None,
) -> dict:
    settings = get_settings()
    input_path = csv_path or (settings.results_dir.parent / "input" / "test_skus.csv")
    label_path = settings.fixture_labels_path

    items = _read_csv_items(input_path)
    with label_path.open(encoding="utf-8") as handle:
        rows = json.load(handle)
    label_map = {row["wine_name"]: row for row in rows}

    batch_response = run_batch_analysis(
        BatchAnalyzeRequest(items=items),
        retrieval_backend_override=backend,
        pipeline_name=pipeline_name,
    )
    metrics = _compute_metrics(batch_response.results, label_map)
    metrics["dataset"] = "live_assignment_skus"
    metrics["retrieval_backend"] = backend
    metrics["pipeline"] = pipeline_name or get_settings().pipeline_name
    return metrics


def write_live_evaluation(path: Path, *, csv_path: Path | None = None, backend: str = "hybrid", pipeline_name: str | None = None) -> None:
    metrics = evaluate_live_dataset(csv_path=csv_path, backend=backend, pipeline_name=pipeline_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")


def _per_sku_result(result: AnalyzeResponse, actual_positive: bool) -> dict:
    return {
        "wine_name": result.input.wine_name,
        "expected_pass": actual_positive,
        "predicted_verdict": result.verdict.value,
        "confidence": result.confidence,
        "fail_reason": result.fail_reason.value if result.fail_reason else None,
        "selected_image_url": result.selected_image_url,
    }


def _read_csv_items(path: Path) -> list[AnalyzeRequest]:
    items: list[AnalyzeRequest] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            items.append(
                AnalyzeRequest(
                    wine_name=row["wine_name"],
                    vintage=row["vintage"],
                    format=row.get("format", "750ml"),
                    region=row.get("region", ""),
                )
            )
    return items


def _compute_metrics(results: list[AnalyzeResponse], label_map: dict[str, dict]) -> dict:
    true_positive = 0
    false_positive = 0
    false_negative = 0
    true_negative = 0
    per_sku: list[dict] = []

    for result in results:
        label = label_map[result.input.wine_name]
        actual_positive = bool(label["expected_pass"])
        predicted_positive = result.verdict == Verdict.PASS

        if predicted_positive and actual_positive:
            true_positive += 1
        elif predicted_positive and not actual_positive:
            false_positive += 1
        elif not predicted_positive and actual_positive:
            false_negative += 1
        else:
            true_negative += 1

        per_sku.append(_per_sku_result(result, actual_positive))

    total = len(results)
    accuracy = (true_positive + true_negative) / total if total else 0.0
    precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) else 0.0
    recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) else 0.0

    return {
        "total": total,
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "confusion_matrix": {
            "tp": true_positive,
            "fp": false_positive,
            "fn": false_negative,
            "tn": true_negative,
        },
        "per_sku": per_sku,
    }
