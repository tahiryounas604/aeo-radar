"""Data models for aeo-radar (clean-room, stdlib only)."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Competitor:
    name: str
    aliases: list[str] = field(default_factory=list)

    def all_names(self) -> list[str]:
        names = [self.name] + list(self.aliases)
        # de-duplicate, preserve order, drop empties
        seen: set[str] = set()
        out: list[str] = []
        for n in names:
            key = n.strip().lower()
            if n.strip() and key not in seen:
                seen.add(key)
                out.append(n.strip())
        return out

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Competitor":
        return cls(name=str(d.get("name", "")), aliases=list(d.get("aliases") or []))


@dataclass
class Brand:
    name: str
    aliases: list[str] = field(default_factory=list)
    competitors: list[Competitor] = field(default_factory=list)
    prompts: list[str] = field(default_factory=list)
    id: int | None = None

    def all_names(self) -> list[str]:
        names = [self.name] + list(self.aliases)
        seen: set[str] = set()
        out: list[str] = []
        for n in names:
            key = n.strip().lower()
            if n.strip() and key not in seen:
                seen.add(key)
                out.append(n.strip())
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "aliases": list(self.aliases),
            "competitors": [c.to_dict() for c in self.competitors],
            "prompts": list(self.prompts),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Brand":
        return cls(
            id=d.get("id"),
            name=str(d.get("name", "")),
            aliases=list(d.get("aliases") or []),
            competitors=[Competitor.from_dict(c) for c in (d.get("competitors") or [])],
            prompts=list(d.get("prompts") or []),
        )


@dataclass
class Answer:
    prompt: str
    engine: str
    text: str
    brand_name: str = ""
    id: int | None = None
    imported_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Mention:
    name: str  # matched alias/name as written in the profile
    matched_text: str
    offset: int  # char offset of first/this occurrence


@dataclass
class AnswerAnalysis:
    answer_id: int | None
    prompt: str
    engine: str
    brand_mentioned: bool
    brand_mention_count: int
    brand_first_offset: int | None
    brand_position_ratio: float | None  # offset / len(text), 0..1
    visibility_score: float
    competitor_counts: dict[str, int]
    citations: list[str]  # urls
    cited_domains: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AnalysisResult:
    brand_name: str
    total_answers: int
    mentioned_answers: int
    mention_rate: float  # 0..1
    overall_score: float  # mean visibility_score, 0..100
    share_of_voice: dict[str, float]  # entity -> percent 0..100
    per_prompt: dict[str, dict[str, Any]]
    per_engine: dict[str, dict[str, Any]]
    top_cited_domains: list[dict[str, Any]]
    answers: list[AnswerAnalysis] = field(default_factory=list)
    run_id: int | None = None
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d
