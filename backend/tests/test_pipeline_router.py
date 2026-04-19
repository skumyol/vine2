from backend.app.models.sku import AnalyzeRequest, BatchAnalyzeRequest
from backend.app.services import pipeline_router


def test_router_defaults_to_voter_pipeline(monkeypatch) -> None:
    called = {}

    def fake_run_analysis(payload, retrieval_backend_override=None):
        called["path"] = "voter"
        return {"ok": True}

    monkeypatch.setattr("backend.app.services.pipeline_router.voter_pipeline.run_analysis", fake_run_analysis)
    monkeypatch.setattr("backend.app.services.pipeline_router.get_settings", lambda: type("S", (), {"pipeline_name": "voter"})())

    result = pipeline_router.run_analysis(AnalyzeRequest(wine_name="Test Wine", vintage="2020"))

    assert called["path"] == "voter"
    assert result == {"ok": True}


def test_router_can_select_paddle_qwen_pipeline(monkeypatch) -> None:
    called = {}

    def fake_run_analysis(payload, retrieval_backend_override=None):
        called["path"] = "paddle_qwen"
        return {"ok": True}

    monkeypatch.setattr("backend.app.services.pipeline_router.pipeline_paddle_qwen.run_analysis", fake_run_analysis)

    result = pipeline_router.run_analysis(
        AnalyzeRequest(wine_name="Test Wine", vintage="2020"),
        pipeline_name="paddle_qwen",
    )

    assert called["path"] == "paddle_qwen"
    assert result == {"ok": True}


def test_router_batch_can_select_paddle_qwen_pipeline(monkeypatch) -> None:
    called = {}

    def fake_run_batch(payload, retrieval_backend_override=None):
        called["path"] = "paddle_qwen"
        return {"ok": True}

    monkeypatch.setattr("backend.app.services.pipeline_router.pipeline_paddle_qwen.run_batch_analysis", fake_run_batch)

    result = pipeline_router.run_batch_analysis(
        BatchAnalyzeRequest(items=[AnalyzeRequest(wine_name="Test Wine", vintage="2020")]),
        pipeline_name="paddle_qwen",
    )

    assert called["path"] == "paddle_qwen"
    assert result == {"ok": True}
