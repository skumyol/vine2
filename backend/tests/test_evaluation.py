from backend.app.services.evaluation import evaluate_fixture_dataset


def test_fixture_evaluation_reports_accuracy_and_f1() -> None:
    metrics = evaluate_fixture_dataset()

    assert metrics["total"] == 10
    assert metrics["accuracy"] == 1.0
    assert metrics["f1"] == 1.0
    assert metrics["confusion_matrix"] == {"tp": 9, "fp": 0, "fn": 0, "tn": 1}
