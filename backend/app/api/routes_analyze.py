from fastapi import APIRouter, Query

from backend.app.models.result import AnalyzeResponse
from backend.app.models.sku import AnalyzeRequest
from backend.app.services.pipeline_router import run_analysis


router = APIRouter(tags=["analyze"])


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_sku(
    payload: AnalyzeRequest,
    pipeline: str = Query(default="", description="Pipeline variant override"),
) -> AnalyzeResponse:
    return run_analysis(payload, pipeline_name=pipeline or None)
