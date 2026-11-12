"""Markdown + JSON report rendering from an analysis result dict."""
from __future__ import annotations

import json
from typing import Any


def render_json(result: dict[str, Any]) -> str:
    return json.dumps(result, indent=2, ensure_ascii=False)


def render_markdown(result: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# AEO Radar Report — {result.get('brand_name','')}")
    lines.append("")
    if result.get("created_at"):
        lines.append(f"Run: {result['created_at']}  (run_id: {result.get('run_id')})")
        lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Overall visibility score: **{result.get('overall_score', 0)} / 100**")
    lines.append(f"- Answers analysed: {result.get('total_answers', 0)}")
    lines.append(f"- Answers mentioning the brand: {result.get('mentioned_answers', 0)}")
    lines.append(f"- Mention rate: {result.get('mention_rate', 0)}")
    lines.append("")
    lines.append("## Share of Voice")
    lines.append("")
    lines.append("| Entity | Share % |")
    lines.append("|---|---|")
    for entity, pct in (result.get("share_of_voice") or {}).items():
        lines.append(f"| {entity} | {pct} |")
    lines.append("")
    lines.append("## Per-Engine Visibility")
    lines.append("")
    lines.append("| Engine | Answers | Mentioned | Score |")
    lines.append("|---|---|---|---|")
    for engine, agg in (result.get("per_engine") or {}).items():
        lines.append(f"| {engine} | {agg.get('total_answers')} | {agg.get('mentioned_answers')} | {agg.get('visibility_score')} |")
    lines.append("")
    lines.append("## Per-Prompt Visibility")
    lines.append("")
    lines.append("| Prompt | Answers | Mentioned | Score |")
    lines.append("|---|---|---|---|")
    for prompt, agg in (result.get("per_prompt") or {}).items():
        label = prompt if prompt else "(no prompt)"
        lines.append(f"| {label} | {agg.get('total_answers')} | {agg.get('mentioned_answers')} | {agg.get('visibility_score')} |")
    lines.append("")
    lines.append("## Top Cited Domains")
    lines.append("")
    domains = result.get("top_cited_domains") or []
    if domains:
        lines.append("| Domain | Citations |")
        lines.append("|---|---|")
        for d in domains:
            lines.append(f"| {d.get('domain')} | {d.get('count')} |")
    else:
        lines.append("No citations found in the analysed answers.")
    lines.append("")
    lines.append("## Scoring")
    lines.append("")
    lines.append("Per-answer score: 0 if not mentioned, else "
                 "`60 + 40 * (1 - first_mention_offset / len(text))`. "
                 "Overall / per-prompt / per-engine scores are means of per-answer scores. "
                 "Share of voice = entity mentions / all tracked mentions x 100.")
    lines.append("")
    return "\n".join(lines)
