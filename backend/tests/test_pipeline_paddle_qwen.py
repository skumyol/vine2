from backend.app.core.constants import FailReason, Verdict
from backend.app.models.result import AnalyzeResponse, DebugPayload
from backend.app.models.result import BatchAnalyzeResponse
from backend.app.models.sku import AnalyzeRequest, BatchAnalyzeRequest, ParsedIdentity
from backend.app.services.pipeline_paddle_qwen import run_analysis, run_batch_analysis


def _base_response() -> AnalyzeResponse:
    payload = AnalyzeRequest(wine_name="Test Wine", vintage="2020", format="750ml", region="Test")
    parsed = ParsedIdentity(
        producer="Test Producer",
        appellation="Test Appellation",
        vineyard_or_cuvee="Test Cuvee",
        classification="Test Class",
        vintage="2020",
        raw_wine_name="Test Wine",
        normalized_wine_name="test wine",
    )
    return AnalyzeResponse(
        input=payload,
        parsed_identity=parsed,
        verdict=Verdict.PASS,
        confidence=0.86,
        selected_image_url="https://example.com/wine.jpg",
        selected_source_page="https://example.com/page",
        reason="Initial voter pipeline accepted the candidate.",
        debug=DebugPayload(
            ocr_snippets=["Test Producer Test Appellation 2020"],
            module_votes=[],
        ),
    )


def test_paddle_qwen_rejects_when_prefilter_fails(monkeypatch) -> None:
    response = _base_response()
    monkeypatch.setattr("backend.app.services.pipeline_paddle_qwen.run_voter_analysis", lambda payload, retrieval_backend_override=None: response)
    monkeypatch.setattr(
        "backend.app.services.pipeline_paddle_qwen.passes_visual_prefilter",
        lambda image_url: (False, {"passed": False, "reason": "bad image"}),
    )

    result = run_analysis(AnalyzeRequest(wine_name="Test Wine", vintage="2020"))

    assert result.verdict == Verdict.NO_IMAGE
    assert result.fail_reason == FailReason.QUALITY_FAILED
    assert result.selected_image_url is None


def test_paddle_qwen_does_not_reject_on_prefilter_image_load_failure(monkeypatch) -> None:
    response = _base_response()
    monkeypatch.setattr("backend.app.services.pipeline_paddle_qwen.run_voter_analysis", lambda payload, retrieval_backend_override=None: response)
    monkeypatch.setattr(
        "backend.app.services.pipeline_paddle_qwen.passes_visual_prefilter",
        lambda image_url: (False, {"passed": False, "reason": "OpenCV prefilter image load failed: URLError."}),
    )
    monkeypatch.setattr(
        "backend.app.services.pipeline_paddle_qwen.extract_paddle_ocr",
        lambda image_url, crops=None: {"text": "", "snippets": [], "boxes": [], "engine": "paddleocr", "available": True},
    )

    result = run_analysis(AnalyzeRequest(wine_name="Test Wine", vintage="2020"))

    assert result.verdict == Verdict.PASS
    assert result.fail_reason is None
    assert "opencv_prefilter_soft_skip:true" in result.debug.notes


def test_paddle_qwen_rejects_when_qwen_vetoes(monkeypatch) -> None:
    response = _base_response()
    response.debug.module_votes = [type("V", (), {"passed": True, "confidence": 0.8})()]
    monkeypatch.setattr("backend.app.services.pipeline_paddle_qwen.run_voter_analysis", lambda payload, retrieval_backend_override=None: response)
    monkeypatch.setattr(
        "backend.app.services.pipeline_paddle_qwen.passes_visual_prefilter",
        lambda image_url: (True, {"passed": True, "reason": "ok"}),
    )
    monkeypatch.setattr(
        "backend.app.services.pipeline_paddle_qwen.extract_paddle_ocr",
        lambda image_url, crops=None: {"text": "", "snippets": [], "boxes": [], "engine": "paddleocr", "available": True},
    )
    monkeypatch.setattr(
        "backend.app.services.pipeline_paddle_qwen.should_run_vlm",
        lambda parsed, observed_text, ocr_vote, prefilter: (True, "ambiguous"),
    )
    monkeypatch.setattr(
        "backend.app.services.pipeline_paddle_qwen.verify_with_qwen_vlm",
        lambda parsed, image_url: {"overall_pass": False, "overall_confidence": 0.33, "summary": "wrong label"},
    )

    result = run_analysis(AnalyzeRequest(wine_name="Test Wine", vintage="2020"))

    assert result.verdict == Verdict.NO_IMAGE
    assert result.fail_reason == FailReason.IDENTITY_UNVERIFIED
    assert result.selected_image_url is None
    assert "wrong label" in result.reason


def test_paddle_qwen_can_raise_confidence_when_qwen_confirms(monkeypatch) -> None:
    response = _base_response()
    response.debug.module_votes = [type("V", (), {"passed": True, "confidence": 0.8})()]
    monkeypatch.setattr("backend.app.services.pipeline_paddle_qwen.run_voter_analysis", lambda payload, retrieval_backend_override=None: response)
    monkeypatch.setattr(
        "backend.app.services.pipeline_paddle_qwen.passes_visual_prefilter",
        lambda image_url: (True, {"passed": True, "reason": "ok"}),
    )
    monkeypatch.setattr(
        "backend.app.services.pipeline_paddle_qwen.extract_paddle_ocr",
        lambda image_url, crops=None: {"text": "extra ocr", "snippets": ["extra ocr"], "boxes": [], "engine": "paddleocr", "available": True},
    )
    monkeypatch.setattr(
        "backend.app.services.pipeline_paddle_qwen.should_run_vlm",
        lambda parsed, observed_text, ocr_vote, prefilter: (True, "ambiguous"),
    )
    monkeypatch.setattr(
        "backend.app.services.pipeline_paddle_qwen.verify_with_qwen_vlm",
        lambda parsed, image_url: {"overall_pass": True, "overall_confidence": 0.93, "summary": "confirmed"},
    )

    result = run_analysis(AnalyzeRequest(wine_name="Test Wine", vintage="2020"))

    assert result.verdict == Verdict.PASS
    assert result.confidence == 0.93
    assert "confirmed" in result.reason.lower()


def test_paddle_qwen_batch_uses_pipeline_analysis(monkeypatch) -> None:
    seen: list[str] = []

    def fake_run_analysis(payload, retrieval_backend_override=None):
        seen.append(payload.wine_name)
        result = _base_response()
        result.input = payload
        return result

    monkeypatch.setattr("backend.app.services.pipeline_paddle_qwen.run_analysis", fake_run_analysis)
    monkeypatch.setattr(
        "backend.app.services.pipeline_paddle_qwen.get_settings",
        lambda: type("S", (), {"batch_worker_count": 1})(),
    )

    response = run_batch_analysis(
        BatchAnalyzeRequest(
            items=[
                AnalyzeRequest(wine_name="Wine A", vintage="2020"),
                AnalyzeRequest(wine_name="Wine B", vintage="2021"),
            ]
        )
    )

    assert isinstance(response, BatchAnalyzeResponse)
    assert seen == ["Wine A", "Wine B"]
    assert response.summary["total"] == 2
