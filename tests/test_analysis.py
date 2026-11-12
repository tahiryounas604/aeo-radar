from aeo_radar.analysis import (
    analyze_answers, count_mentions, extract_citations, find_mentions,
    share_of_voice, visibility_score,
)
from aeo_radar.models import Answer


def test_mention_detection_alias_aware(brand):
    text = "We recommend Acme Cloud for teams, and acme for solo users."
    mentions = find_mentions(text, brand.all_names())
    # "Acme Cloud" counted once (longest wins), "acme" once
    assert len(mentions) == 2
    assert mentions[0][0] == text.index("Acme Cloud")


def test_mention_no_partial_word_match():
    assert count_mentions("Acmeville is a place", ["Acme"]) == 0
    assert count_mentions("Try Acme, it works", ["Acme"]) == 1


def test_mention_case_insensitive():
    assert count_mentions("ACME and AcMe", ["Acme"]) == 2


def test_mention_absent():
    assert count_mentions("Nothing relevant here", ["Acme"]) == 0


def test_position_scoring():
    # Mention at offset 0 in 100-char text -> 100
    assert visibility_score(True, 0, 100) == 100.0
    # Halfway -> 80
    assert visibility_score(True, 50, 100) == 80.0
    # At the end -> just above 60
    assert visibility_score(True, 100, 100) == 60.0
    # Not mentioned -> 0 regardless
    assert visibility_score(False, None, 100) == 0.0
    assert visibility_score(False, 0, 100) == 0.0


def test_share_of_voice_math():
    sov = share_of_voice({"Acme": 3, "RivalTool": 1, "OtherApp": 0})
    assert sov == {"Acme": 75.0, "RivalTool": 25.0, "OtherApp": 0.0}
    assert share_of_voice({"A": 0, "B": 0}) == {"A": 0.0, "B": 0.0}
    assert round(sum(share_of_voice({"A": 1, "B": 2}).values()), 2) == 100.0


def test_citation_extraction():
    text = ("See https://acme.example.com/guide, and "
            "https://www.example.org/list. Also http://reviews.example.net/a?x=1.")
    urls, domains = extract_citations(text)
    assert urls[0] == "https://acme.example.com/guide"
    assert "example.org" in domains  # www. stripped
    assert "reviews.example.net" in domains
    assert len(urls) == 3


def test_citation_none():
    urls, domains = extract_citations("no links here")
    assert urls == [] and domains == []


def test_analyze_end_to_end(brand):
    answers = [
        Answer(prompt="best project tool", engine="chatgpt",
               text="Acme is best. RivalTool is ok. https://example.com/x"),
        Answer(prompt="best project tool", engine="perplexity",
               text="RivalTool wins, OtherApp second."),
        Answer(prompt="cheapest project tool", engine="chatgpt",
               text="OtherApp is cheapest."),
    ]
    result = analyze_answers(brand, answers)
    assert result.total_answers == 3
    assert result.mentioned_answers == 1
    assert result.mention_rate == round(1 / 3, 4)
    # first answer: mention at 0 -> 100; others 0 -> mean 33.33
    assert result.overall_score == 33.33
    # SoV: Acme 1, RivalTool 2, OtherApp 2 -> total 5
    assert result.share_of_voice == {"Acme": 20.0, "RivalTool": 40.0, "OtherApp": 40.0}
    assert result.per_engine["chatgpt"]["total_answers"] == 2
    assert result.per_prompt["best project tool"]["mentioned_answers"] == 1
    assert result.top_cited_domains == [{"domain": "example.com", "count": 1}]


def test_analyze_empty(brand):
    result = analyze_answers(brand, [])
    assert result.total_answers == 0
    assert result.overall_score == 0.0
    assert result.share_of_voice == {"Acme": 0.0, "RivalTool": 0.0, "OtherApp": 0.0}


def test_scoring_formula_documented_value(brand):
    # 200-char text, first mention at char 100 -> ratio .5 -> 60+40*.5=80
    text = (" " * 100) + "Acme" + (" " * 96)
    assert len(text) == 200
    result = analyze_answers(brand, [Answer(prompt="p", engine="e", text=text)])
    assert result.answers[0].visibility_score == 80.0
    assert result.answers[0].brand_position_ratio == 0.5
