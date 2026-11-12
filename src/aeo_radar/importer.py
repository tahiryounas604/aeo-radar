"""Import collected AI answers from JSON / CSV / plain-text files.

JSON formats accepted:
  * a list of objects: [{"prompt": ..., "engine": ..., "answer": ...}, ...]
  * an object with an "answers" list in the same shape
  Field aliases: answer text may be under "answer" or "text" or "response";
  engine may be under "engine" or "source" (default "unknown").

CSV: header row with prompt / engine / answer (or text) columns.

Text: the whole file is a single answer; prompt/engine come from the
caller's defaults.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from .models import Answer


def _coerce(obj: dict, default_prompt: str = "", default_engine: str = "unknown") -> Answer | None:
    text = obj.get("answer") or obj.get("text") or obj.get("response") or ""
    text = str(text).strip()
    if not text:
        return None
    return Answer(
        prompt=str(obj.get("prompt") or default_prompt),
        engine=str(obj.get("engine") or obj.get("source") or default_engine),
        text=text,
    )


def import_json(path: str | Path, default_prompt: str = "", default_engine: str = "unknown") -> list[Answer]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    items = data.get("answers") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError("JSON must be a list of answers or an object with an 'answers' list")
    out = []
    for item in items:
        if isinstance(item, str):
            if item.strip():
                out.append(Answer(prompt=default_prompt, engine=default_engine, text=item.strip()))
        elif isinstance(item, dict):
            a = _coerce(item, default_prompt, default_engine)
            if a:
                out.append(a)
    return out


def import_csv(path: str | Path, default_prompt: str = "", default_engine: str = "unknown") -> list[Answer]:
    out = []
    with Path(path).open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            return out
        for row in reader:
            a = _coerce({k.strip().lower(): (v or "") for k, v in row.items() if k},
                        default_prompt, default_engine)
            if a:
                out.append(a)
    return out


def import_text(path: str | Path, default_prompt: str = "", default_engine: str = "unknown") -> list[Answer]:
    text = Path(path).read_text(encoding="utf-8").strip()
    if not text:
        return []
    return [Answer(prompt=default_prompt, engine=default_engine, text=text)]


def import_file(path: str | Path, default_prompt: str = "", default_engine: str = "unknown") -> list[Answer]:
    suffix = Path(path).suffix.lower()
    if suffix == ".json":
        return import_json(path, default_prompt, default_engine)
    if suffix == ".csv":
        return import_csv(path, default_prompt, default_engine)
    return import_text(path, default_prompt, default_engine)
