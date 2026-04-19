import argparse
import csv
import json
from pathlib import Path

from backend.app.models.result import BatchAnalyzeResponse
from backend.app.models.sku import AnalyzeRequest, BatchAnalyzeRequest
from backend.app.services.evaluation import (
    evaluate_fixture_dataset,
    evaluate_live_dataset,
    write_live_evaluation,
)
from backend.app.services.ocr_evaluation import evaluate_ocr_accuracy, write_ocr_evaluation
from backend.app.services.pipeline_router import run_analysis, run_batch_analysis
from backend.app.services.retriever_playwright import playwright_self_check


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="VinoBuzz backend CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze", help="Analyze one SKU")
    analyze.add_argument("--wine-name", required=True)
    analyze.add_argument("--vintage", required=True)
    analyze.add_argument("--format", default="750ml")
    analyze.add_argument("--region", default="")
    analyze.add_argument("--pipeline", default="", help="Pipeline variant override")

    batch = subparsers.add_parser("batch", help="Analyze a CSV file of SKUs")
    batch.add_argument("--input", required=True, help="Path to CSV input")
    batch.add_argument("--output", default="", help="Optional JSON output path")
    batch.add_argument("--pipeline", default="", help="Pipeline variant override")

    evaluate = subparsers.add_parser("evaluate", help="Evaluate the pipeline on fixture labels")
    evaluate.add_argument("--output", default="", help="Optional JSON output path for metrics")
    evaluate.add_argument("--pipeline", default="", help="Pipeline variant override")

    evaluate_live = subparsers.add_parser("evaluate-live", help="Evaluate the pipeline on the live assignment SKU CSV")
    evaluate_live.add_argument("--input", default="data/input/test_skus.csv", help="CSV input path")
    evaluate_live.add_argument("--backend", default="hybrid", help="Retrieval backend override")
    evaluate_live.add_argument("--pipeline", default="", help="Pipeline variant override")
    evaluate_live.add_argument("--output", default="", help="Optional JSON output path for live metrics")

    ocr_eval = subparsers.add_parser("ocr-evaluate", help="Evaluate OCR field-level accuracy on fixture dataset")
    ocr_eval.add_argument("--output", default="", help="Optional JSON output path for OCR metrics")
    ocr_eval.add_argument("--pipeline", default="", help="Pipeline variant override")

    subparsers.add_parser("playwright-check", help="Validate Playwright browser launch and page load")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "analyze":
        payload = AnalyzeRequest(
            wine_name=args.wine_name,
            vintage=args.vintage,
            format=args.format,
            region=args.region,
        )
        print(run_analysis(payload, pipeline_name=args.pipeline or None).model_dump_json(indent=2))
        return

    if args.command == "batch":
        response = _run_batch_from_csv(Path(args.input), pipeline_name=args.pipeline or None)
        output = response.model_dump_json(indent=2)
        if args.output:
            Path(args.output).write_text(output + "\n", encoding="utf-8")
        else:
            print(output)
        return

    if args.command == "evaluate":
        metrics = evaluate_fixture_dataset(pipeline_name=args.pipeline or None)
        if args.output:
            path = Path(args.output)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
        else:
            print(json.dumps(metrics, indent=2))
        return

    if args.command == "evaluate-live":
        metrics = evaluate_live_dataset(csv_path=Path(args.input), backend=args.backend, pipeline_name=args.pipeline or None)
        if args.output:
            write_live_evaluation(Path(args.output), csv_path=Path(args.input), backend=args.backend, pipeline_name=args.pipeline or None)
        else:
            print(json.dumps(metrics, indent=2))
        return

    if args.command == "ocr-evaluate":
        metrics = evaluate_ocr_accuracy(pipeline_name=args.pipeline or None)
        if args.output:
            write_ocr_evaluation(Path(args.output), pipeline_name=args.pipeline or None)
        else:
            print(json.dumps(metrics, indent=2))
        return

    if args.command == "playwright-check":
        print(json.dumps(playwright_self_check(), indent=2))
        return


def _run_batch_from_csv(path: Path, pipeline_name: str | None = None) -> BatchAnalyzeResponse:
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
    return run_batch_analysis(BatchAnalyzeRequest(items=items), pipeline_name=pipeline_name)


if __name__ == "__main__":
    main()
