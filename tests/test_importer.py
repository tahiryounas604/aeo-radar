from pathlib import Path

from aeo_radar.importer import import_csv, import_file, import_json, import_text

FIX = Path(__file__).parent / "fixtures"


def test_import_json_fixture():
    answers = import_json(FIX / "answers.json")
    assert len(answers) == 3
    assert answers[0].engine == "chatgpt"
    assert answers[0].prompt == "best project tool"
    assert "Acme" in answers[0].text


def test_import_json_answers_wrapper(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"answers": [{"prompt": "p", "engine": "gemini", "text": "hello Acme"}]}')
    answers = import_json(p)
    assert len(answers) == 1 and answers[0].text == "hello Acme"


def test_import_json_skips_empty(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('[{"prompt":"p","engine":"e","answer":""}, {"prompt":"p","engine":"e","answer":"real"}]')
    assert len(import_json(p)) == 1


def test_import_csv_fixture():
    answers = import_csv(FIX / "answers.csv")
    assert len(answers) == 2
    assert answers[0].engine == "gemini"


def test_import_text(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("Acme is mentioned in plain text.")
    answers = import_text(p, default_prompt="p1", default_engine="chatgpt")
    assert len(answers) == 1
    assert answers[0].prompt == "p1" and answers[0].engine == "chatgpt"


def test_import_file_dispatch(tmp_path):
    assert len(import_file(FIX / "answers.json")) == 3
    assert len(import_file(FIX / "answers.csv")) == 2
    p = tmp_path / "note.md"
    p.write_text("plain answer body")
    assert len(import_file(p)) == 1
