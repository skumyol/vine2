from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from backend.app.core.constants import FailReason, Verdict
from backend.app.core.config import get_settings
from backend.app.models.result import AnalyzeResponse, BatchAnalyzeResponse
from backend.app.models.sku import AnalyzeRequest, BatchAnalyzeRequest
from backend.app.services.ambiguity_gate import should_run_vlm
from backend.app.services.decision_engine import annotate_pipeline
from backend.app.services.label_cropper import build_label_crops
from backend.app.services.opencv_filter import passes_visual_prefilter
from backend.app.services.paddle_ocr_service import extract_paddle_ocr
from backend.app.services.pipeline import run_analysis as run_voter_analysis
from backend.app.services.qwen_vlm_verifier import verify_with_qwen_vlm


def run_analysis(payload: AnalyzeRequest, retrieval_backend_override: str | None = None) -> AnalyzeResponse:
    response = run_voter_analysis(payload, retrieval_backend_override=retrieval_backend_override)
    response.debug.notes.append("pipeline_variant:paddle_qwen")
    if not response.selected_image_url:
        response.debug.notes.append("paddle_qwen_secondary_verification:skipped_no_selected_image")
        return annotate_pipeline(response, "paddle_qwen")

    prefilter_ok, prefilter = passes_visual_prefilter(response.selected_image_url)
    response.debug.notes.append(f"opencv_prefilter_passed:{prefilter_ok}")
    response.debug.notes.append(f"opencv_prefilter_reason:{prefilter.get('reason', '')}")
    prefilter_reason = str(prefilter.get("reason", "") or "")
    prefilter_load_failed = "image load failed" in prefilter_reason.lower()
    if prefilter_load_failed:
        response.debug.notes.append("opencv_prefilter_soft_skip:true")
    if response.verdict == Verdict.PASS and not prefilter_ok and not prefilter_load_failed:
        response.verdict = Verdict.NO_IMAGE
        response.selected_image_url = None
        response.selected_source_page = None
        response.fail_reason = FailReason.QUALITY_FAILED
        response.confidence = 0.0
        response.reason = "OpenCV prefilter rejected the candidate image."
        return annotate_pipeline(response, "paddle_qwen")

    crops = build_label_crops(response.selected_image_url)
    paddle = extract_paddle_ocr(response.selected_image_url, crops=crops)
    response.debug.notes.append(f"paddleocr_available:{paddle.get('available', False)}")
    response.debug.notes.append(f"paddleocr_engine:{paddle.get('engine', 'unknown')}")
    if paddle.get("text"):
        response.debug.notes.append("paddleocr_text_present:true")
        response.debug.ocr_snippets = list(dict.fromkeys(response.debug.ocr_snippets + paddle.get("snippets", [])[:3]))
    else:
        response.debug.notes.append("paddleocr_text_present:false")

    if response.debug.module_votes:
        run_vlm, gate_reason = should_run_vlm(
            response.parsed_identity,
            response.debug.ocr_snippets[0] if response.debug.ocr_snippets else "",
            response.debug.module_votes[0],
            prefilter,
        )
        response.debug.notes.append(f"ambiguity_gate:{run_vlm}")
        response.debug.notes.append(f"ambiguity_gate_reason:{gate_reason}")
        if run_vlm and response.selected_image_url:
            try:
                qwen_result = _invoke_qwen(
                    response.parsed_identity,
                    response.selected_image_url,
                    ocr_text=paddle.get("text", "") or (response.debug.ocr_snippets[0] if response.debug.ocr_snippets else ""),
                    gate_reason=gate_reason,
                )
                response.debug.notes.append("qwen_vlm_invoked:true")
                response.debug.notes.append(f"qwen_vlm_overall_pass:{qwen_result.get('overall_pass')}")
                response.debug.notes.append(f"qwen_vlm_overall_confidence:{qwen_result.get('overall_confidence')}")
                if response.verdict == Verdict.PASS and not qwen_result.get("overall_pass", False):
                    response.verdict = Verdict.NO_IMAGE
                    response.selected_image_url = None
                    response.selected_source_page = None
                    response.fail_reason = FailReason.IDENTITY_UNVERIFIED
                    response.confidence = min(response.confidence, float(qwen_result.get("overall_confidence", 0.0)))
                    response.reason = f"Qwen VLM rejected the candidate: {qwen_result.get('summary', 'no summary')}"
                elif response.verdict == Verdict.PASS and qwen_result.get("overall_pass", False):
                    response.confidence = round(max(response.confidence, float(qwen_result.get("overall_confidence", 0.0))), 4)
                    response.reason = f"{response.reason} Qwen VLM confirmed the candidate."
            except Exception as exc:
                response.debug.notes.append("qwen_vlm_invoked:false")
                response.debug.notes.append(f"qwen_vlm_error:{type(exc).__name__}")
    else:
        response.debug.notes.append("ambiguity_gate:false")
        response.debug.notes.append("ambiguity_gate_reason:no_module_votes_available")
    return annotate_pipeline(response, "paddle_qwen")


def run_batch_analysis(
    payload: BatchAnalyzeRequest,
    retrieval_backend_override: str | None = None,
) -> BatchAnalyzeResponse:
    settings = get_settings()
    if len(payload.items) <= 1:
        results = [run_analysis(item, retrieval_backend_override=retrieval_backend_override) for item in payload.items]
    else:
        configured_workers = getattr(settings, "batch_worker_count", 4)
        if not isinstance(configured_workers, int):
            configured_workers = 4
        max_workers = min(configured_workers, len(payload.items))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(run_analysis, item, retrieval_backend_override)
                for item in payload.items
            ]
            results = [future.result() for future in futures]

    verdict_counts = Counter(result.verdict.value for result in results)
    return BatchAnalyzeResponse(
        results=results,
        summary={
            "total": len(results),
            "verdict_counts": dict(verdict_counts),
        },
    )


def _invoke_qwen(parsed, image_url: str, *, ocr_text: str, gate_reason: str) -> dict:
    try:
        return verify_with_qwen_vlm(
            parsed,
            image_url,
            ocr_text=ocr_text,
            gate_reason=gate_reason,
        )
    except TypeError:
        # Backward-compatible call path for tests or older verifier shims.
        return verify_with_qwen_vlm(parsed, image_url)
