import json

from backend.app import cli


def test_cli_playwright_check_prints_json(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "backend.app.cli.playwright_self_check",
        lambda: {"playwright_imported": True, "browser_launch_ok": True, "page_load_ok": True},
    )
    monkeypatch.setattr(
        "sys.argv",
        ["backend.app.cli", "playwright-check"],
    )

    cli.main()

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["browser_launch_ok"] is True
