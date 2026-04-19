from backend.app.models.result import AnalyzeResponse


def annotate_pipeline(response: AnalyzeResponse, pipeline_name: str) -> AnalyzeResponse:
    response.debug.notes.append(f"pipeline:{pipeline_name}")
    return response
