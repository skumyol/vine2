from fastapi import APIRouter, Query

from backend.app.models.result import BatchAnalyzeResponse
from backend.app.models.sku import BatchAnalyzeRequest
from backend.app.services.pipeline_router import run_batch_analysis


router = APIRouter(tags=["batch"])


@router.post("/analyze/batch", response_model=BatchAnalyzeResponse)
def analyze_batch(
    payload: BatchAnalyzeRequest,
    pipeline: str = Query(default="", description="Pipeline variant override"),
) -> BatchAnalyzeResponse:
    return run_batch_analysis(payload, pipeline_name=pipeline or None)
