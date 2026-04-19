from backend.app.core.constants import FailReason, Verdict
from backend.app.models.sku import AnalyzeRequest
from backend.app.services.pipeline import run_analysis


def test_pipeline_selects_verified_candidate_for_fixture_backed_sku() -> None:
    payload = AnalyzeRequest(
        wine_name="Domaine Arlaud Morey-St-Denis 'Monts Luisants' 1er Cru",
        vintage="2019",
        format="750ml",
        region="Burgundy",
    )

    result = run_analysis(payload)

    assert result.verdict == Verdict.PASS
    assert result.selected_image_url == "https://images.example.com/arlaud-monts-luisants-2019.jpg"
    assert result.confidence >= 0.85


def test_pipeline_returns_no_image_for_fixture_with_only_bad_candidates() -> None:
    payload = AnalyzeRequest(
        wine_name="Arnot-Roberts Trousseau Gris Watson Ranch",
        vintage="2020",
        format="750ml",
        region="Sonoma",
    )

    result = run_analysis(payload)

    assert result.verdict == Verdict.NO_IMAGE
    assert result.fail_reason in {
        FailReason.VINTAGE_MISMATCH,
        FailReason.VINEYARD_OR_CUVEE_MISMATCH,
        FailReason.UNREADABLE_CORE_IDENTITY,
        FailReason.IDENTITY_UNVERIFIED,
    }
