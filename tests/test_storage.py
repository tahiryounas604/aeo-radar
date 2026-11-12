from aeo_radar.analysis import analyze_answers
from aeo_radar.models import Answer
from aeo_radar.storage import Store


def test_storage_round_trip(tmp_path, brand):
    db = tmp_path / "test.db"
    with Store(db) as store:
        store.init()
        store.add_brand(brand)
        loaded = store.get_brand("Acme")
        assert loaded is not None
        assert loaded.name == "Acme"
        assert loaded.aliases == ["Acme Cloud"]
        assert [c.name for c in loaded.competitors] == ["RivalTool", "OtherApp"]
        assert loaded.prompts == brand.prompts
        assert [b.name for b in store.list_brands()] == ["Acme"]

        store.add_answers("Acme", [Answer(prompt="p", engine="chatgpt", text="Acme wins")])
        answers = store.list_answers("Acme")
        assert len(answers) == 1 and answers[0].text == "Acme wins"
        assert answers[0].id is not None


def test_brand_upsert_updates(tmp_path, brand):
    with Store(tmp_path / "t.db") as store:
        store.init()
        store.add_brand(brand)
        brand.aliases = ["Acme Cloud", "AcmeHQ"]
        store.add_brand(brand)
        assert store.get_brand("Acme").aliases == ["Acme Cloud", "AcmeHQ"]
        assert len(store.list_brands()) == 1


def test_score_history_and_latest(tmp_path, brand):
    with Store(tmp_path / "t.db") as store:
        store.init()
        store.add_brand(brand)
        store.add_answers("Acme", [Answer(prompt="p", engine="e", text="Acme first")])
        r1 = store.save_run(analyze_answers(brand, store.list_answers("Acme")))
        assert r1.run_id is not None
        store.save_run(analyze_answers(brand, store.list_answers("Acme")))
        history = store.score_history("Acme")
        assert len(history) == 2
        assert history[0]["overall_score"] == 100.0
        latest = store.latest_result("Acme")
        assert latest["brand_name"] == "Acme"
        assert latest["overall_score"] == 100.0


def test_missing_brand(tmp_path):
    with Store(tmp_path / "t.db") as store:
        store.init()
        assert store.get_brand("Nope") is None
        assert store.latest_result("Nope") is None
        assert store.score_history("Nope") == []
