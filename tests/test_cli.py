from pathlib import Path

from aeo_radar.cli import main

FIX = Path(__file__).parent / "fixtures"


def _run(tmp_path, *argv):
    return main(["--db", str(tmp_path / "cli.db"), *argv])


def test_cli_full_flow(tmp_path, capsys):
    assert _run(tmp_path, "init") == 0
    assert _run(
        tmp_path, "brand", "add", "--name", "Acme", "--aliases", "Acme Cloud",
        "--competitors", "RivalTool;OtherApp",
        "--prompts", "best project tool,cheapest project tool",
    ) == 0
    assert _run(tmp_path, "brand", "list") == 0
    assert "Acme" in capsys.readouterr().out

    assert _run(tmp_path, "import", "--brand", "Acme", "--file", str(FIX / "answers.json")) == 0
    out = capsys.readouterr().out
    assert "Imported 3" in out

    assert _run(tmp_path, "analyze", "--brand", "Acme") == 0
    out = capsys.readouterr().out
    assert "Overall visibility score:" in out

    report_path = tmp_path / "report.md"
    assert _run(tmp_path, "report", "--brand", "Acme", "--format", "md",
                "--output", str(report_path)) == 0
    text = report_path.read_text()
    assert "AEO Radar Report" in text and "Share of Voice" in text

    json_path = tmp_path / "report.json"
    assert _run(tmp_path, "report", "--brand", "Acme", "--format", "json",
                "--output", str(json_path)) == 0
    assert '"brand_name": "Acme"' in json_path.read_text()

    assert _run(tmp_path, "score", "--brand", "Acme") == 0
    out = capsys.readouterr().out
    assert "Latest score:" in out


def test_cli_brand_show_and_missing(tmp_path, capsys):
    _run(tmp_path, "brand", "add", "--name", "Acme")
    capsys.readouterr()
    assert _run(tmp_path, "brand", "show", "--name", "Acme") == 0
    assert '"name": "Acme"' in capsys.readouterr().out
    assert _run(tmp_path, "brand", "show", "--name", "Ghost") == 1
    assert _run(tmp_path, "import", "--brand", "Ghost", "--file", str(FIX / "answers.json")) == 1
    assert _run(tmp_path, "analyze", "--brand", "Ghost") == 1


def test_cli_score_no_runs(tmp_path, capsys):
    _run(tmp_path, "brand", "add", "--name", "Acme")
    capsys.readouterr()
    assert _run(tmp_path, "score", "--brand", "Acme") == 0
    assert "No analysis runs yet" in capsys.readouterr().out


def test_cli_competitor_alias_parsing(tmp_path):
    from aeo_radar.cli import _parse_competitors
    comps = _parse_competitors("RivalTool:RT|Rival;OtherApp")
    assert comps[0].name == "RivalTool" and comps[0].aliases == ["RT", "Rival"]
    assert comps[1].name == "OtherApp" and comps[1].aliases == []
