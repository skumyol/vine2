from backend.app.core.config import get_settings
from backend.app.models.sku import AnalyzeRequest, BatchAnalyzeRequest
from backend.app.services import pipeline as voter_pipeline
from backend.app.services import pipeline_paddle_qwen


def run_analysis(
    payload: AnalyzeRequest,
    retrieval_backend_override: str | None = None,
    pipeline_name: str | None = None,
):
    selected = pipeline_name or get_settings().pipeline_name
    if selected == "paddle_qwen":
        return pipeline_paddle_qwen.run_analysis(payload, retrieval_backend_override=retrieval_backend_override)
    return voter_pipeline.run_analysis(payload, retrieval_backend_override=retrieval_backend_override)


def run_batch_analysis(
    payload: BatchAnalyzeRequest,
    retrieval_backend_override: str | None = None,
    pipeline_name: str | None = None,
):
    selected = pipeline_name or get_settings().pipeline_name
    if selected == "paddle_qwen":
        return pipeline_paddle_qwen.run_batch_analysis(payload, retrieval_backend_override=retrieval_backend_override)
    return voter_pipeline.run_batch_analysis(payload, retrieval_backend_override=retrieval_backend_override)
