"""Analysis engine — offline, deterministic, documented scoring.

Visibility score (per answer)
-----------------------------
Let ``mentioned`` be True when the brand (name or any alias) occurs in
the answer text (case-insensitive).

* If not mentioned: ``score = 0``
* If mentioned:

    ratio = first_mention_char_offset / max(1, len(text))   # 0 = very start
    score = 60 + 40 * (1 - ratio)

  So a mention at the very start scores 100, a mention halfway through
  scores 80, and a mention at the very end scores just above 60.
  Presence is worth 60 points; early position is worth up to 40 more.

Aggregate visibility score = arithmetic mean of per-answer scores over
all answers in scope (overall, per-prompt and per-engine use the same
mean over their subset).

Share of voice (per entity)
---------------------------
``sov(entity) = 100 * mentions(entity) / total_mentions`` where
``mentions`` counts every (non-overlapping) occurrence across all
answers and ``total_mentions`` is the sum over the brand and all
competitors. If total is 0, every entity's share is 0.0.

Mention detection
-----------------
Case-insensitive search for each name/alias. Overlapping spans are
resolved by preferring the longest name (so alias "Acme Cloud" wins
over "Acme" at the same position and is counted once). Matches must
not be glued to word characters on either side (``\\w`` boundary),
so "Acme" does not match inside "Acmeville" unless that longer form
is itself a listed name.
"""
from __future__ import annotations

import re
from collections import Counter
from urllib.parse import urlparse

from .models import Answer, AnswerAnalysis, AnalysisResult, Brand

_URL_RE = re.compile(r"https?://[^\s\)\]\}>\"'<>]+", re.IGNORECASE)
_TRAILING_PUNCT = ".,;:!?"


def _find_spans(text: str, names: list[str]) -> list[tuple[int, int, str, str]]:
    """Return non-overlapping (start, end, profile_name, matched_text)."""
    candidates: list[tuple[int, int, str, str]] = []
    for name in names:
        if not name.strip():
            continue
        pattern = re.compile(r"(?<!\w)" + re.escape(name) + r"(?!\w)", re.IGNORECASE)
        for m in pattern.finditer(text):
            candidates.append((m.start(), m.end(), name, m.group(0)))
    # Longest first at same start, then earliest first; greedily keep
    # non-overlapping spans.
    candidates.sort(key=lambda c: (c[0], -(c[1] - c[0])))
    kept: list[tuple[int, int, str, str]] = []
    occupied: list[tuple[int, int]] = []
    for start, end, name, matched in candidates:
        if any(start < o_end and end > o_start for o_start, o_end in occupied):
            continue
        occupied.append((start, end))
        kept.append((start, end, name, matched))
    kept.sort(key=lambda c: c[0])
    return kept


def find_mentions(text: str, names: list[str]) -> list[tuple[int, str, str]]:
    """Public helper: list of (offset, profile_name, matched_text)."""
    return [(s, name, matched) for s, _e, name, matched in _find_spans(text, names)]


def count_mentions(text: str, names: list[str]) -> int:
    return len(_find_spans(text, names))


def extract_citations(text: str) -> tuple[list[str], list[str]]:
    """Extract (urls, domains) from answer text, in order, de-duplicated URLs."""
    urls: list[str] = []
    seen: set[str] = set()
    for m in _URL_RE.finditer(text or ""):
        url = m.group(0).rstrip(_TRAILING_PUNCT)
        # strip a trailing ')' that belongs to surrounding prose is handled
        # by the char class; keep as-is otherwise.
        if url not in seen:
            seen.add(url)
            urls.append(url)
    domains: list[str] = []
    for url in urls:
        host = (urlparse(url).hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
        if host:
            domains.append(host)
    return urls, domains


def position_ratio(offset: int, text_length: int) -> float:
    if text_length <= 0:
        return 0.0
    return offset / text_length


def visibility_score(mentioned: bool, first_offset: int | None, text_length: int) -> float:
    """Documented per-answer formula — see module docstring."""
    if not mentioned or first_offset is None:
        return 0.0
    ratio = position_ratio(first_offset, text_length)
    return round(60.0 + 40.0 * (1.0 - ratio), 2)


def share_of_voice(counts: dict[str, int]) -> dict[str, float]:
    total = sum(counts.values())
    if total == 0:
        return {k: 0.0 for k in counts}
    return {k: round(100.0 * v / total, 2) for k, v in counts.items()}


def _aggregate(analyses: list[AnswerAnalysis]) -> dict:
    total = len(analyses)
    mentioned = sum(1 for a in analyses if a.brand_mentioned)
    score = round(sum(a.visibility_score for a in analyses) / total, 2) if total else 0.0
    return {
        "total_answers": total,
        "mentioned_answers": mentioned,
        "mention_rate": round(mentioned / total, 4) if total else 0.0,
        "visibility_score": score,
    }


def analyze_answers(brand: Brand, answers: list[Answer]) -> AnalysisResult:
    brand_names = brand.all_names()
    per_answer: list[AnswerAnalysis] = []
    sov_counts: dict[str, int] = {brand.name: 0}
    for comp in brand.competitors:
        sov_counts[comp.name] = 0
    domain_counter: Counter[str] = Counter()

    for ans in answers:
        text = ans.text or ""
        brand_spans = _find_spans(text, brand_names)
        mentioned = len(brand_spans) > 0
        first_offset = brand_spans[0][0] if brand_spans else None
        sov_counts[brand.name] += len(brand_spans)

        comp_counts: dict[str, int] = {}
        for comp in brand.competitors:
            c = count_mentions(text, comp.all_names())
            comp_counts[comp.name] = c
            sov_counts[comp.name] += c

        urls, domains = extract_citations(text)
        domain_counter.update(domains)

        per_answer.append(
            AnswerAnalysis(
                answer_id=ans.id,
                prompt=ans.prompt,
                engine=ans.engine,
                brand_mentioned=mentioned,
                brand_mention_count=len(brand_spans),
                brand_first_offset=first_offset,
                brand_position_ratio=(
                    round(position_ratio(first_offset, len(text)), 4)
                    if first_offset is not None
                    else None
                ),
                visibility_score=visibility_score(mentioned, first_offset, len(text)),
                competitor_counts=comp_counts,
                citations=urls,
                cited_domains=domains,
            )
        )

    overall = _aggregate(per_answer)

    per_prompt: dict[str, dict] = {}
    per_engine: dict[str, dict] = {}
    for a in per_answer:
        per_prompt.setdefault(a.prompt, []).append(a)  # type: ignore[arg-type]
        per_engine.setdefault(a.engine, []).append(a)  # type: ignore[arg-type]
    per_prompt_agg = {k: _aggregate(v) for k, v in per_prompt.items()}  # type: ignore[arg-type]
    per_engine_agg = {k: _aggregate(v) for k, v in per_engine.items()}  # type: ignore[arg-type]

    top_domains = [
        {"domain": d, "count": c} for d, c in domain_counter.most_common(20)
    ]

    return AnalysisResult(
        brand_name=brand.name,
        total_answers=overall["total_answers"],
        mentioned_answers=overall["mentioned_answers"],
        mention_rate=overall["mention_rate"],
        overall_score=overall["visibility_score"],
        share_of_voice=share_of_voice(sov_counts),
        per_prompt=per_prompt_agg,
        per_engine=per_engine_agg,
        top_cited_domains=top_domains,
        answers=per_answer,
    )
