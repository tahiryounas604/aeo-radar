"""Optional live provider: OpenAI-compatible chat completions client.

This is the ONLY network-touching module, and it is never used by the
offline analysis path or by the tests (tests inject a fake transport).

Configuration via environment:
  AEO_PROVIDER_API_KEY  (or OPENAI_API_KEY)
  AEO_PROVIDER_BASE_URL (default https://api.openai.com/v1)
  AEO_PROVIDER_MODEL    (default gpt-4o-mini)
"""
from __future__ import annotations

import json
import os
import urllib.request
from typing import Callable

Transport = Callable[[str, dict, dict], dict]  # (url, payload, headers) -> parsed json


def _default_transport(url: str, payload: dict, headers: dict) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 - user-configured endpoint
        return json.loads(resp.read().decode("utf-8"))


class OpenAICompatibleProvider:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        transport: Transport | None = None,
    ):
        self.api_key = api_key or os.environ.get("AEO_PROVIDER_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = (base_url or os.environ.get("AEO_PROVIDER_BASE_URL")
                         or "https://api.openai.com/v1").rstrip("/")
        self.model = model or os.environ.get("AEO_PROVIDER_MODEL") or "gpt-4o-mini"
        self._transport = transport or _default_transport

    def query(self, prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError(
                "No API key: set AEO_PROVIDER_API_KEY (or OPENAI_API_KEY) to use live querying"
            )
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        data = self._transport(f"{self.base_url}/chat/completions", payload, headers)
        try:
            return str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected provider response shape: {data!r:.200}") from exc
