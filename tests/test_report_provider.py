import json

import pytest

from aeo_radar.analysis import analyze_answers
from aeo_radar.models import Answer
from aeo_radar.provider import OpenAICompatibleProvider
from aeo_radar.report import render_json, render_markdown


def _result(brand):
    answers = [Answer(prompt="best project tool", engine="chatgpt",
                      text="Acme is best. See https://example.com/guide")]
    return analyze_answers(brand, answers).to_dict()


def test_render_json(brand):
    out = render_json(_result(brand))
    data = json.loads(out)
    assert data["brand_name"] == "Acme"
    assert data["overall_score"] == 100.0


def test_render_markdown(brand):
    md = render_markdown(_result(brand))
    assert "# AEO Radar Report — Acme" in md
    assert "Overall visibility score" in md
    assert "Share of Voice" in md
    assert "example.com" in md
    assert "Per-Engine" in md and "Per-Prompt" in md


def test_provider_mocked_transport():
    captured = {}

    def fake_transport(url, payload, headers):
        captured["url"] = url
        captured["payload"] = payload
        captured["headers"] = headers
        return {"choices": [{"message": {"content": "Acme is great"}}]}

    provider = OpenAICompatibleProvider(
        api_key="test-key", base_url="https://api.example.test/v1",
        model="test-model", transport=fake_transport,
    )
    assert provider.query("best tool?") == "Acme is great"
    assert captured["url"] == "https://api.example.test/v1/chat/completions"
    assert captured["payload"]["model"] == "test-model"
    assert captured["headers"]["Authorization"] == "Bearer test-key"


def test_provider_requires_key(monkeypatch):
    monkeypatch.delenv("AEO_PROVIDER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = OpenAICompatibleProvider(api_key="", transport=lambda *a: {})
    with pytest.raises(RuntimeError, match="No API key"):
        provider.query("hi")


def test_provider_bad_response_shape():
    provider = OpenAICompatibleProvider(
        api_key="k", transport=lambda url, payload, headers: {"nope": True}
    )
    with pytest.raises(RuntimeError, match="Unexpected provider response"):
        provider.query("hi")
